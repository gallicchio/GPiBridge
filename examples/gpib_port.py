"""GPIB through a GPiBridge, with Python and pyserial alone: the smallest useful layer.

A GPiBridge is a USB serial port that takes the Prologix GPIB-USB controller's "++"
commands, so this works with a Prologix too (give its port). Each method below is one or
two of those commands: read them to see exactly what goes over the wire.

    from gpib_port import GpibPort
    with GpibPort() as bus:                        # the GPiBridge plugged in
        print(bus.query(10, '*IDN?'))              # the instrument at GPIB address 10
        bus.write(10, 'APPLy:SINusoid 1E3,0.1,0')
        bus.local(10)                              # its front panel works again

Needs Python 3.6+ and pyserial (`pip install pyserial`), on Linux, macOS or Windows.
For drivers of whole instruments, timeouts that recover, and the LAN and USB
instruments beside GPIB ones, see lab-instrument-control:
https://github.com/QuantumQuasars/lab-instrument-control
"""
import json
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit('needs pyserial: pip install pyserial')

VID, PID = 0x1209, 0x0001                  # GPiBridge's USB IDs (pid.codes)


def find_port(serial_number=None):
    """The GPIB port of the GPiBridge plugged in (Linux /dev/ttyACM0, macOS
    /dev/cu.usbmodem..., Windows COM5). Its USB interface 0 is the GPIB port; a second
    port, interface 2, appears only when its console is switched on."""
    found = []
    for p in list_ports.comports():
        if (p.vid, p.pid) != (VID, PID) or (serial_number and p.serial_number != serial_number):
            continue
        if 'console' in (p.interface or '').lower():
            continue
        if not p.interface and p.location and not p.location.endswith('.0'):
            continue                       # no interface names given: interface 0 is the GPIB port
        found.append(p.device)
    if not found:
        raise IOError('no GPiBridge found (USB 1209:0001): is it plugged in? Or name its port')
    if len(found) > 1:
        raise IOError('several GPiBridges (%s): name one by its port' % ', '.join(found))
    return found[0]


def escape(data):
    """In a data line, CR, LF, ESC and '+' go to the instrument only after an ESC (27);
    without one, the adapter takes them for itself."""
    out = bytearray()
    for b in data:
        if b in b'\r\n\x1b+':
            out.append(27)
        out.append(b)
    return bytes(out)


class GpibPort:
    """One GPiBridge (or Prologix), and the instruments on its bus, each by address."""

    def __init__(self, port=None, read_timeout=5.0):
        self.s = serial.Serial(port or find_port(), timeout=read_timeout)
        self.s.reset_input_buffer()
        # This session's settings, not saved to the adapter's flash (++savecfg 0), set every
        # time whatever another program left: controller; no read after each write; EOI
        # on the last byte and a line feed after it; nothing added to answers; a read
        # gives up 500 ms after the last byte.
        for c in ('++savecfg 0', '++mode 1', '++auto 0', '++eoi 1', '++eos 2', '++eot_enable 0',
                  '++read_tmo_ms 500'):
            self.cmd(c)
        self.version = self.ask('++ver')
        if self.version.startswith('GPiBridge'):
            # A board can be set to stay off the bus until told (++t autostart 0).
            if json.loads(self.ask('++t status')).get('bus') == 'off':
                print('the GPiBridge was off the bus: switching it on (++t power 1)', file=sys.stderr)
                self.cmd('++t power 1')
                time.sleep(0.2)

    def cmd(self, line):
        """A line for the adapter itself ("++...") or, after ++addr, data for the instrument."""
        self.s.write(line.encode() + b'\n')

    def ask(self, line):
        """An adapter command that answers ("++ver", "++spoll"): its one-line answer."""
        self.s.reset_input_buffer()
        self.cmd(line)
        return self.s.readline().decode(errors='replace').strip()

    def write(self, address, message):
        """A message (text, or bytes for binary blocks) to the instrument at `address`."""
        if isinstance(message, str):
            message = message.encode()
        self.cmd('++addr %d' % address)
        self.s.write(escape(message) + b'\n')

    def read(self, address, end=None):
        """The instrument's answer (text, stripped): up to the byte it sends with EOI, or with
        end='\\n', up to its line feed. Some instruments never send EOI (an HP 5370B ends its
        answers in CR LF alone): without `end`, the read then ends only when the adapter's
        500 ms timeout passes, and a counter that keeps talking keeps it going."""
        self.cmd('++addr %d' % address)
        self.s.reset_input_buffer()
        self.cmd('++read eoi' if end is None else '++read %d' % ord(end))
        line = self.s.readline()
        if not line:
            raise IOError('GPIB %d: no answer within %g s' % (address, self.s.timeout))
        return line.decode(errors='replace').strip()

    def query(self, address, message, end=None):
        self.write(address, message)
        return self.read(address, end)

    def serial_poll(self, address):
        """The instrument's status byte (bit 6, 64: it asked for service)."""
        return int(self.ask('++spoll %d' % address))

    def clear(self, address):
        """Selected Device Clear: the instrument drops what it was given and has queued."""
        self.cmd('++addr %d' % address)
        self.cmd('++clr')

    def local(self, address):
        """Go To Local: the instrument's front panel works again."""
        self.cmd('++addr %d' % address)
        self.cmd('++loc')

    def close(self):
        self.s.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
