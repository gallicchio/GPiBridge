#!/usr/bin/env python3
"""Pictures of the board in its housing, by KiCad's own renderer: a copy of
the board carries the housing's STEP files as the 3D models of one extra
footprint, and kicad-cli renders it from a few sides.

    python3 enclosure/render.py          (after enclosure/build.py)

Writes enclosure/out/render_*.png; with GPIBRIDGE_VARIANT=lite, the Lite in its
lid, enclosure/out/render_lite_*.png.
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import board_info as BI
LID = "lite_lid" if BI.LITE else "lid"

if "--inside" not in sys.argv:
    import kienv
    OUT = os.path.join(HERE, "out")
    views = [  # name, models, kicad-cli render arguments
        ("closed", "base," + LID, ["--rotate", "-55,0,35", "--zoom", "0.9"]),
        ("open", "base", ["--rotate", "-55,0,35", "--zoom", "0.9"]),
        ("top", "base," + LID, ["--side", "top"]),
        ("front", "base," + LID, ["--side", "bottom"]),
        ("usb_end", "base," + LID, ["--rotate", "-75,0,-80", "--zoom", "1.1"]),
    ]
    if BI.LITE:
        views = views[:2]
    for name, models, args in views:
        # beside the real board, so ${KIPRJMOD} finds hardware/lib's models; removed after
        pcb = os.path.join(ROOT, "hardware", ".render_%s.kicad_pcb" % name)
        r = subprocess.run(kienv.python() + [os.path.abspath(__file__), "--inside", pcb, models],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
        png = os.path.join(OUT, "render_%s%s.png" % (BI.IMAGE_PREFIX, name))
        try:
            kienv.run_cli(["pcb", "render", "--width", "2000", "--height", "1300", "--quality", "high",
                           "--background", "opaque", "-o", png] + args + [pcb])
        finally:
            for ext in ("", ".bak"):
                if os.path.exists(pcb + ext):
                    os.remove(pcb + ext)
            pro = pcb.replace(".kicad_pcb", ".kicad_pro")
            if os.path.exists(pro):
                os.remove(pro)
        print(png)
    sys.exit(0)

import pcbnew
pcb, models = sys.argv[sys.argv.index("--inside") + 1], sys.argv[sys.argv.index("--inside") + 2].split(",")
board = pcbnew.LoadBoard(BI.PCB)
fp = pcbnew.FOOTPRINT(board)
fp.SetReference("HOUSING")
fp.Reference().SetVisible(False)
fp.Value().SetVisible(False)
fp.SetPosition(board.GetDesignSettings().GetAuxOrigin())     # the board's bottom-left corner
for m in models:
    mod = pcbnew.FP_3DMODEL()
    mod.m_Filename = os.path.join(HERE, "out", "gpibridge_%s.step" % m)
    mod.m_Offset = pcbnew.VECTOR3D(0, 0, -1.6)      # a top-side model's z = 0 is the board's top face
    mod.m_Opacity = 1.0
    fp.Models().push_back(mod)
board.Add(fp)
board.Save(pcb)
