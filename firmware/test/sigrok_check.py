#!/usr/bin/env python3
"""Read the simulated bus with sigrok's own IEEE-488 decoder: an independent
reading of what the firmware put on the wires.

    python3 sigrok_check.py          (make runs it after test_wire)

test_wire writes out/<name>_bus.vcd (the bus, as a logic analyser on the plug
sees it) and out/<name>_pins.vcd (the RP2354A's pins, as the board's own
capture sees them, ++t capture); `test_wire lite` the same for GPiBridge Lite,
out/lite_<name>_*.vcd.  sigrok-cli decodes each with its "ieee488"
decoder; the talker bytes it finds must be exactly the bytes test_wire sent
and received.  Needs sigrok-cli (on the PATH, or $SIGROK_CLI); without it the
check says so and passes.
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS = ":".join("%s=%s" % (c.lower(), c) for c in
                    ["DIO%d" % i for i in range(1, 9)] + ["EOI", "DAV", "NRFD", "NDAC", "IFC", "SRQ", "ATN", "REN"])

# what test_wire.c sends and receives in each recorded phase
IDN = b"HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n"
LOW = bytes(b for b in range(0x01, 0x80) if b not in (0x0A, 0x0D)) + b"\n"
HIGH = bytes(range(0x80, 0x100)) + b"\n"
EXPECT = {
    "idn": b"*IDN?\n" + IDN,
    "bytes_low": LOW + b"ECHO?\n" + LOW,
    "bytes_high": HIGH + b"ECHO?\n" + HIGH,
}


def main():
    sr = os.environ.get("SIGROK_CLI") or shutil.which("sigrok-cli")
    if not sr:
        print("sigrok check: skipped (no sigrok-cli; apt install sigrok-cli, or set SIGROK_CLI)")
        return 0
    bad = total = 0
    for board, (name, want) in [(b, e) for b in ("", "lite_") for e in EXPECT.items()]:
        for view in ("bus", "pins"):
            vcd = os.path.join(HERE, "out", "%s%s_%s.vcd" % (board, name, view))
            total += 1
            r = subprocess.run([sr, "-I", "vcd", "-i", vcd, "-P", "ieee488:" + CHANNELS, "-B", "ieee488=data"],
                               capture_output=True)
            ok = r.returncode == 0 and r.stdout == want
            bad += not ok
            if not ok:
                print("sigrok check: %s%s_%s: decoded %d bytes, expected %d%s" % (
                    board, name, view, len(r.stdout), len(want),
                    "; first difference at byte %d" % next((i for i, (a, b) in enumerate(zip(r.stdout, want))
                                                           if a != b), min(len(r.stdout), len(want)))
                    if r.returncode == 0 else ": " + r.stderr.decode(errors="replace")[-200:]))
    print("sigrok check: %d of %d recordings decode to exactly the bytes sent (sigrok's ieee488 decoder)"
          % (total - bad, total))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
