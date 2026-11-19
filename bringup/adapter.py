"""One "++" adapter on a serial port: a GPiBridge (a real one, or firmware/test/sim_board
behind its pseudo-terminal) or the bench's Prologix.

    with Adapter('/dev/serial/by-id/usb-GPiBridge_...-if00') as a:
        print(a.ask('++ver'))
        print(a.json('++t status')['bus'])
        a.write(10, b'*IDN?'); print(a.read_eoi())

Python's standard library only, as lab-instrument-control's scpi_link is: the port is
opened raw, no baud rate matters (it is USB), and nothing depends on DTR.
"""
import json
import os
import select
import termios
import time
import tty

VID, PID = 0x1209, 0x0001                 # pid.codes' test PID, until GPiBridge has its own
BOOT_VID, BOOT_PID = 0x2E8A, 0x000F       # the RP2350's ROM bootloader
BY_ID = '/dev/serial/by-id'

# the sixteen lines, in the order of the masks "++t raw" and "++t selftest" answer with
LINES = ['DIO1', 'DIO2', 'DIO3', 'DIO4', 'DIO5', 'DIO6', 'DIO7', 'DIO8',
         'EOI', 'DAV', 'NRFD', 'NDAC', 'IFC', 'REN', 'ATN', 'SRQ']
# which IEEE-488 contact carries each (docs/PINOUT.md)
CONTACT = {'DIO1': 1, 'DIO2': 2, 'DIO3': 3, 'DIO4': 4, 'EOI': 5, 'DAV': 6, 'NRFD': 7, 'NDAC': 8,
           'IFC': 9, 'SRQ': 10, 'ATN': 11, 'DIO5': 13, 'DIO6': 14, 'DIO7': 15, 'DIO8': 16, 'REN': 17}


def names(mask):
    """The lines in a mask, by name: 0x0201 -> ['DIO1', 'DAV']."""
    return [n for i, n in enumerate(LINES) if mask >> i & 1]


def mask_of(*line_names):
    return sum(1 << LINES.index(n) for n in line_names)


class AdapterError(IOError):
    pass


class Adapter:
    def __init__(self, port, timeout=2.0):
        self.port, self.timeout = port, timeout
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
        tty.setraw(self.fd)
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        self.pending = b''

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- bytes ---------------------------------------------------------------------
    def send(self, data):
        if os.environ.get('GPIBRIDGE_WIRE_LOG'):             # every byte sent, for comparing two runs
            with open(os.environ['GPIBRIDGE_WIRE_LOG'], 'a') as f:
                f.write('%.3f %s %r\n' % (time.time(), os.path.basename(self.port), data))
        while data:
            _, w, _ = select.select([], [self.fd], [], self.timeout + 10)
            if not w:
                raise AdapterError(f'{self.port}: took no data for {self.timeout + 10:.0f} s')
            data = data[os.write(self.fd, data):]

    def recv(self, seconds):
        r, _, _ = select.select([self.fd], [], [], max(0.0, seconds))
        return os.read(self.fd, 1 << 16) if r else b''

    def drain(self, quiet=0.05):
        """Drop whatever is still arriving."""
        self.pending = b''
        while self.recv(quiet):
            pass

    def line(self, timeout=None):
        """One line of text from the adapter, without its line end; '' on a timeout."""
        t_end = time.time() + (self.timeout if timeout is None else timeout)
        while b'\n' not in self.pending:
            left = t_end - time.time()
            if left <= 0:
                return ''
            self.pending += self.recv(left)
        raw, self.pending = self.pending.split(b'\n', 1)
        return raw.decode(errors='replace').strip('\r')

    # -- "++" commands ---------------------------------------------------------------
    def cmd(self, text):
        self.send(text.encode() + b'\n')

    def ask(self, text, timeout=None):
        self.drain(0.0)
        self.cmd(text)
        return self.line(timeout)

    def json(self, text, timeout=None):
        reply = self.ask(text, timeout)
        try:
            return json.loads(reply)
        except ValueError:
            raise AdapterError(f'{self.port}: {text!r} answered {reply!r}, not JSON') from None

    def json_until(self, text, key, value, timeout=10.0):
        """Every JSON line a command answers with, up to and including the one whose
        `key` is `value` (the last line of "++t selftest" has "selftest":"done")."""
        self.drain(0.0)
        self.cmd(text)
        out, t_end = [], time.time() + timeout
        while time.time() < t_end:
            reply = self.line(t_end - time.time())
            if not reply:
                continue
            try:
                d = json.loads(reply)
            except ValueError:
                raise AdapterError(f'{self.port}: {text!r} answered {reply!r}, not JSON') from None
            out.append(d)
            if d.get(key) == value:
                return out
        raise AdapterError(f'{self.port}: {text!r} did not finish in {timeout:.0f} s; it said {out}')

    # -- the instrument behind it ----------------------------------------------------
    @staticmethod
    def escape(data):
        """CR, LF, ESC and '+' in data, each behind an ESC: the adapter would take them for itself."""
        out = bytearray()
        for b in data:
            if b in (10, 13, 27, 43):
                out.append(27)
            out.append(b)
        return bytes(out)

    def write(self, addr, data):
        """One message to the instrument at `addr` (the adapter adds its ++eos terminator and EOI)."""
        self.cmd(f'++addr {addr}')
        self.send(self.escape(data) + b'\n')

    def read_eoi(self, timeout=None):
        """++read eoi: everything up to the instrument's EOI.  The adapter marks the end
        with its ++eot_char (set up by controller()), which is then taken off."""
        self.drain(0.0)
        self.cmd('++read eoi')
        out, t_end = b'', time.time() + (self.timeout if timeout is None else timeout)
        while time.time() < t_end:
            out += self.recv(min(0.05, t_end - time.time()))
            # the mark, and then silence: a binary answer may hold the mark's byte itself
            if out.endswith(EOT) and not (more := self.recv(0.03)):
                return out[:-1]
            elif out.endswith(EOT):
                out += more
        return out

    def controller(self):
        """The settings every step here assumes (as scpi_link sets a Prologix up), with
        an end mark after each EOI so that a binary answer's end is known."""
        for c in ('++savecfg 0', '++mode 1', '++auto 0', '++eoi 1', '++eos 2', '++eot_enable 1',
                  f'++eot_char {EOT[0]}', '++read_tmo_ms 1000'):
            self.cmd(c)

    def query(self, addr, text, timeout=None):
        self.write(addr, text.encode())
        return self.read_eoi(timeout).decode(errors='replace').strip()


EOT = b'\x04'                              # what the adapter appends after EOI (++eot_char 4)


# -- finding them --------------------------------------------------------------------------
def _usb(dev):
    """vendor, product, serial number and interface number of a tty, from sysfs."""
    base = f'/sys/class/tty/{os.path.basename(os.path.realpath(dev))}/device'
    try:
        itf = os.path.realpath(base)
        usb = os.path.dirname(itf)
        read = lambda p: open(p).read().strip()
        return (int(read(f'{usb}/idVendor'), 16), int(read(f'{usb}/idProduct'), 16), read(f'{usb}/serial'),
                int(read(f'{itf}/bInterfaceNumber'), 16), read(f'{usb}/product'))
    except (OSError, ValueError):
        return None


def gpibridges():
    """{serial number: {'gpib': port, 'console': port or None, 'product': str}} of every GPiBridge on USB."""
    found = {}
    if not os.path.isdir(BY_ID):
        return found
    for name in sorted(os.listdir(BY_ID)):
        port = os.path.join(BY_ID, name)
        u = _usb(port)
        if not u or (u[0], u[1]) != (VID, PID):
            continue
        d = found.setdefault(u[2], {'gpib': None, 'console': None, 'product': u[4]})
        d['gpib' if u[3] == 0 else 'console'] = port
    return found


def prologix_ports():
    """The bench Prologix adapters' ports (FTDI chips that name themselves)."""
    if not os.path.isdir(BY_ID):
        return []
    return [os.path.join(BY_ID, n) for n in sorted(os.listdir(BY_ID)) if 'Prologix' in n]


def usb_devices(vid, pid):
    """sysfs paths of the USB devices with these IDs (the RP2350s waiting in BOOTSEL, say)."""
    out, root = [], '/sys/bus/usb/devices'
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        try:
            if (int(open(f'{root}/{d}/idVendor').read(), 16), int(open(f'{root}/{d}/idProduct').read(), 16)) \
                    == (vid, pid):
                out.append(f'{root}/{d}')
        except (OSError, ValueError):
            pass
    return out


def usb_by_serial(serial):
    """Each USB device with this serial number: ((bus, device number), (vid, pid)). A
    GPiBridge and its RP2350 in the ROM bootloader report the same one, the chip's ID.
    The device number is new at every enumeration, so a board that went and came back
    between two looks is still seen to have gone."""
    out, root = [], '/sys/bus/usb/devices'
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        try:
            if open(f'{root}/{d}/serial').read().strip() == serial:
                out.append(((int(open(f'{root}/{d}/busnum').read()), int(open(f'{root}/{d}/devnum').read())),
                            (int(open(f'{root}/{d}/idVendor').read(), 16), int(open(f'{root}/{d}/idProduct').read(), 16))))
        except (OSError, ValueError):
            pass
    return out
