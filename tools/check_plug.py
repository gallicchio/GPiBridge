#!/usr/bin/env python3
"""Is the GPIB plug's footprint the right way round?

    python3 tools/check_plug.py

A 24-pin IEEE-488 plug has two rows of twelve pins at 2.16 mm: its pattern is
symmetric under a half turn and under a mirror, so a footprint that is drawn
mirrored, or a plug soldered turned round, puts every signal on the wrong
contact and nothing on the board looks wrong.  The only proof is a board that
works.  xyphro's UsbGpib V2 is one, built in quantity
(github.com/xyphro/UsbGpib, HW/REV2, "Upcoming_Rev2" and "ManyRev2" photos), and
mounts the same plug the same way: under the board, pins up through it.

From its KiCad file (HW/REV2/KicadV2/xyp-gpib.kicad_pcb, footprint GPIB1 on
B.Cu at 180 degrees), seen from the top of the board, the pins of these
signals sit at (mm, x right, y down):

    DIO1 (contact 1)   (218.194, 80.405)
    ATN  (contact 11)  (196.594, 80.405)
    DIO5 (contact 13)  (218.194, 84.695)
    REN  (contact 17)  (209.554, 84.695)

This check finds the same four on GPiBridge's board and asks that they lie in
the same pattern: the same offsets from DIO1, not mirrored, not turned.  (Read
2026-10-06: they match to 0.001 mm.)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
import board_info as BI

USBGPIB_V2 = {"DIO1": (218.194, 80.405), "ATN": (196.594, 80.405), "DIO5": (218.194, 84.695),
              "REN": (209.554, 84.695)}

if "--inside" not in sys.argv:
    import subprocess, kienv
    r = subprocess.run(kienv.python() + [os.path.abspath(__file__), "--inside"], capture_output=True, text=True,
                       env=dict(os.environ))
    sys.stdout.write(r.stdout)
    sys.stderr.write("\n".join(l for l in r.stderr.splitlines() if "Font '" not in l and "Debug" not in l))
    sys.exit(r.returncode)

import pcbnew


def main():
    b = pcbnew.LoadBoard(BI.PCB)
    fp = b.FindFootprintByReference("J2")
    ours = {}
    for p in fp.Pads():
        name = p.GetNetname().replace("Net-(J2-", "").rstrip(")")
        ours[name] = (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
    bad = 0
    o0, t0 = ours["DIO1"], USBGPIB_V2["DIO1"]
    for sig in ("ATN", "DIO5", "REN"):
        d_ours = (ours[sig][0] - o0[0], ours[sig][1] - o0[1])
        d_theirs = (USBGPIB_V2[sig][0] - t0[0], USBGPIB_V2[sig][1] - t0[1])
        ok = abs(d_ours[0] - d_theirs[0]) < 0.01 and abs(d_ours[1] - d_theirs[1]) < 0.01
        bad += not ok
        print("  %-5s from DIO1: ours (%+.3f, %+.3f), UsbGpib V2 (%+.3f, %+.3f)  %s"
              % (sig, d_ours[0], d_ours[1], d_theirs[0], d_theirs[1], "ok" if ok else "DIFFERENT"))
    print("plug: %s" % ("the same pattern as UsbGpib V2's working board" if not bad else
                        "NOT the pattern of UsbGpib V2's board: check the footprint's mirroring"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
