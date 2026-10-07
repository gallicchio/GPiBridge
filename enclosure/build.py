#!/usr/bin/env python3
"""Build the housing: two parts for JLC3DP (MJF PA12), drawn in FreeCAD's
Python from the board's own placement, and checked against the board's 3D
model for collisions.

    python3 enclosure/build.py

Writes enclosure/out/:
    gpibridge_base.step / .stl     the part on the instrument's side: the plug's
                                   flange bears on its face, the board lies in it
    gpibridge_lid.step / .stl      the cover: openings for the USB-C, the two
                                   debug connectors, the three LEDs and BOOT
    gpibridge_lite_lid.step / .stl the same cover, engraved for GPiBridge Lite (one
                                   base fits both boards: their parts that reach the
                                   housing sit in the same places)
    gpibridge_board.step,          each board with every part, from KiCad
    gpibridgelite_board.step
    CHECK.txt                      what the parts collide with (must be nothing),
                                   and NorComp's own plug model in its place, when
                                   reference/ has it
and renders in enclosure/out/ (see enclosure/README.md).

How it goes together (the plug is soldered last, in the base, as on UsbGpib):
  1. JLCPCB fits every part but the plug.
  2. Push the plug's rear body through the base's opening from the front: its
     flange lies against the base's front face.
  3. Lay the board into the base, the plug's 24 pins up through it, and press it
     down onto the plug's standoff plate (the pins' shoulders grip the holes);
     solder them.
  4. Put the lid on: two M2 x 10 screws through the lid and the board's corner
     holes into the base.

The base's front plate is what pushes on the flange when the adapter is
plugged in, so insertion force does not go through the solder joints.  (The
flange's own holes cannot take screws: they fall on the board, over the USB
and UART circuits.)
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import placement as PL
import footprints as F
import kienv

OUT = os.path.join(HERE, "out")
BOARDS = [  # name, title, tagline, lid
    ("GPiBridge", "GPiBridge", "USB to GPIB", "gpibridge_lid"),
    ("GPiBridgeLite", "GPiBridge Lite", "USB to GPIB", "gpibridge_lite_lid"),
]
NORCOMP = os.path.join(ROOT, "reference", "111-024-113L001.STEP")       # not committed: NorComp's


def params():
    """Every dimension the housing takes from the board, in board millimetres
    (x right, y down from the board's top-left corner; z up from the board's
    bottom face)."""
    P = PL.PLACE
    return dict(
        board=dict(w=PL.BOARD["w"], h=PL.BOARD["h"], r=PL.BOARD["r"], t=1.6),
        # the plug (gen/footprints.py, from NorComp's 3D model and drawing)
        plug=dict(x=PL.XC, y=PL.YC, rear=list(F.REAR), flange=list(F.FLANGE), flange_z=-F.FLANGE_Z + F.FLANGE_T,
                  flange_t=F.FLANGE_T, face_z=-F.FACE_Z),
        usbc=dict(y=P["J1"][1], face_x=-1.2, w=8.94, h=3.26),
        holes=[list(P["H1"][:2]), list(P["H2"][:2])],
        leds=[list(P[r][:2]) for r in ("D1", "D2", "D3")],
        boot=list(P["SW1"][:2]),
        debug=[list(P["J3"][:2]), list(P["J4"][:2])],
        # the USB-C's four shell legs come through the board: pockets below them
        legs=[[1.4, 15.68], [1.4, 24.32], [5.58, 15.68], [5.58, 24.32]],
        boards=[dict(title=t, tagline=g, lid=l, step=os.path.join(OUT, n.lower() + "_board.step"))
                for n, t, g, l in BOARDS],
        norcomp_step=NORCOMP,
    )


def main():
    os.makedirs(OUT, exist_ok=True)
    json.dump(params(), open(os.path.join(OUT, "params.json"), "w"), indent=1)
    for name, title, tagline, lid in BOARDS:
        pcb = os.path.join(ROOT, "hardware", name + ".kicad_pcb")
        if os.path.exists(pcb):
            kienv.run_cli(["pcb", "export", "step", "--subst-models", "--no-dnp", "--drill-origin", "--force",
                           "-o", os.path.join(OUT, name.lower() + "_board.step"), pcb])
    r = subprocess.run(["freecadcmd", os.path.join(HERE, "housing.py")], capture_output=True, text=True,
                       env=dict(os.environ, GPIBRIDGE_OUT=OUT), timeout=1800)
    log = r.stdout + r.stderr
    for line in log.splitlines():
        if line.startswith(("HOUSING", "CHECK", "ERROR", "Traceback")) or "Error" in line:
            print(line)
    if r.returncode or "ERROR" in log:
        sys.stderr.write(log[-3000:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
