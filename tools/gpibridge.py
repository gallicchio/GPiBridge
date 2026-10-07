#!/usr/bin/env python3
"""Talk to a GPiBridge from the computer it is plugged into.

    python3 tools/gpibridge.py list                  every GPiBridge and its serial ports
    python3 tools/gpibridge.py status                its status (JSON)
    python3 tools/gpibridge.py idn ADDR              *IDN? of the instrument at GPIB address ADDR
    python3 tools/gpibridge.py ask ADDR "MEAS:VOLT?" one query
    python3 tools/gpibridge.py send ADDR "VOLT 1.0"  one command
    python3 tools/gpibridge.py test ADDR             a short check against a real instrument
    python3 tools/gpibridge.py capture ADDR "Q?" F   record the bus during one query: F.vcd,
                                                     for PulseView (and its IEEE-488 decoder)
    python3 tools/gpibridge.py bootsel               reboot into the ROM's USB bootloader
    python3 tools/gpibridge.py flash FILE.uf2        bootsel, then load and run FILE.uf2 (picotool)
    python3 tools/gpibridge.py console-port on|off   the second serial port (JSON log); it reconnects
    python3 tools/gpibridge.py console               follow that log (Ctrl-C to stop)

--serial S picks one adapter when several are plugged in.

The adapter is one USB serial port, "GPiBridge GPIB", which speaks the
Prologix "++" commands, as a Prologix does.  "console-port on" adds a second
one, "GPiBridge console", which prints JSON lines (the same lines always come
out of the UART debug connector, J4).  This tool finds the ports by those
names (USB 1209:0001), so it never talks to the wrong one.  Needs pyserial;
`flash` needs picotool on the PATH (the firmware build makes one in
firmware/build/_deps/picotool/); `capture` uses sigrok-cli if it is there, to
print what it decoded.
"""
import json, os, shutil, subprocess, sys, time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("gpibridge.py needs pyserial (pip install pyserial)")

VID, PID = 0x1209, 0x0001
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GPIB_CHANNELS = ["DIO%d" % i for i in range(1, 9)] + ["EOI", "DAV", "NRFD", "NDAC", "IFC", "SRQ", "ATN", "REN"]


def ports(serial_number=None):
    """{serial number: {"gpib": device, "console": device (if it is on)}}"""
    found = {}
    for p in list_ports.comports():
        if p.vid != VID or p.pid != PID:
            continue
        if serial_number and p.serial_number != serial_number:
            continue
        kind = "console" if "console" in (p.interface or "").lower() else "gpib"
        if not p.interface:                       # no interface names: CDC 0 is the GPIB port
            kind = "gpib" if p.location and p.location.endswith(".0") else "console"
        found.setdefault(p.serial_number, {})[kind] = p.device
    return found


def one(serial_number=None):
    found = ports(serial_number)
    if not found:
        sys.exit("no GPiBridge found (USB %04x:%04x)" % (VID, PID))
    if len(found) > 1:
        sys.exit("several GPiBridges: pick one with --serial (%s)" % ", ".join(sorted(found)))
    return next(iter(found.items()))


class Gpib:
    """The Prologix port: write a line, read until EOI."""

    def __init__(self, device):
        self.s = serial.Serial(device, timeout=3)
        self.s.reset_input_buffer()
        for c in ("++mode 1", "++auto 0", "++eoi 1", "++eos 2", "++read_tmo_ms 1000"):
            self.cmd(c)

    def cmd(self, line):
        self.s.write(line.encode() + b"\n")

    def ask(self, line):
        self.s.reset_input_buffer()
        self.cmd(line)
        return self.s.readline().decode(errors="replace").strip()

    def write(self, addr, text):
        self.cmd("++addr %d" % addr)
        esc = "".join("\x1b" + ch if ch in "\r\n\x1b+" else ch for ch in text)
        self.cmd(esc)

    def query(self, addr, text):
        self.write(addr, text)
        self.s.reset_input_buffer()
        self.cmd("++read eoi")
        return self.s.readline().decode(errors="replace").strip()

    def until(self, marker, timeout=30):
        """Everything up to and including the line `marker`."""
        out, t_end = [], time.time() + timeout
        while time.time() < t_end:
            line = self.s.readline().decode(errors="replace")
            out.append(line)
            if line.strip() == marker:
                return "".join(out)
        sys.exit("no %r from the adapter within %d s" % (marker, timeout))


def console(device, command=None, follow=False):
    with serial.Serial(device, timeout=0.5) as s:
        if command:
            s.reset_input_buffer()
            s.write(command.encode() + b"\n")
        t_end = time.time() + 2
        while follow or time.time() < t_end:
            line = s.readline().decode(errors="replace").strip()
            if line:
                print(line)
                if command and not follow:
                    return line


def capture(g, addr, query, name):
    """Record the bus during one query, and save it as NAME.vcd."""
    path = name if name.endswith(".vcd") else name + ".vcd"
    g.ask("++t capture start")
    answer = g.query(addr, query)
    g.cmd("++t capture dump")
    vcd = g.until("$comment end $end")
    with open(path, "w") as f:
        f.write(vcd)
    print("answer: %s\nwrote %s (%d changes)" % (answer, path, vcd.count("\n#")))
    sr = os.environ.get("SIGROK_CLI") or shutil.which("sigrok-cli")
    if sr:
        chans = ":".join("%s=%s" % (c.lower(), c) for c in GPIB_CHANNELS)
        r = subprocess.run([sr, "-I", "vcd", "-i", path, "-P", "ieee488:" + chans, "-A", "ieee488=gpib:texts"],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
    print("open it with: pulseview %s   (decoder: IEEE-488; its channels are named as on the bus)" % path)


def main(argv):
    sn = None
    if "--serial" in argv:
        i = argv.index("--serial")
        sn = argv[i + 1]
        del argv[i:i + 2]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    what = argv[0]
    if what == "list":
        found = ports(sn)
        if not found:
            sys.exit("no GPiBridge found (USB %04x:%04x)" % (VID, PID))
        for k, v in sorted(found.items()):
            print("%s  gpib %s  console %s" % (k, v.get("gpib", "?"), v.get("console", "off")))
        return 0
    serial_number, dev = one(sn)
    if what == "status":
        if "console" in dev:
            console(dev["console"], "status")
        else:
            print(Gpib(dev["gpib"]).ask("++t status"))
    elif what == "console":
        if "console" not in dev:
            sys.exit("the console port is off: `gpibridge.py console-port on` (or read the UART on J4)")
        console(dev["console"], follow=True)
    elif what in ("bootsel", "flash"):
        if "console" in dev:
            console(dev["console"], "bootsel")
        else:
            Gpib(dev["gpib"]).cmd("++t bootsel")
        if what == "flash":
            tool = shutil.which("picotool") or os.path.join(ROOT, "firmware", "build", "_deps", "picotool",
                                                            "picotool")
            time.sleep(2)
            return subprocess.call([tool, "load", "-x", argv[1]])
    elif what == "console-port":
        on = argv[1] in ("on", "1")
        print(Gpib(dev["gpib"]).ask("++t console %d" % on))
        time.sleep(3)                             # it reconnects with the new set of ports
        print(json.dumps(ports(serial_number).get(serial_number, {})))
    elif what in ("idn", "ask", "send", "test", "capture"):
        g = Gpib(dev["gpib"])
        addr = int(argv[1])
        if what == "idn":
            print(g.query(addr, "*IDN?"))
        elif what == "ask":
            print(g.query(addr, argv[2]))
        elif what == "send":
            g.write(addr, argv[2])
        elif what == "capture":
            capture(g, addr, argv[2], argv[3] if len(argv) > 3 else "capture.vcd")
        else:
            ver = g.ask("++ver")
            idn = g.query(addr, "*IDN?")
            t0 = time.time()
            for _ in range(20):
                g.query(addr, "*IDN?")
            rate = 20 / (time.time() - t0)
            spoll = g.ask("++spoll %d" % addr)
            ok = bool(idn) and ver.startswith(("GPiBridge", "Prologix"))
            print(json.dumps(dict(adapter=serial_number, version=ver, idn=idn, spoll=spoll,
                                  queries_per_s=round(rate, 1), ok=ok)))
            return 0 if ok else 1
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
