#!/usr/bin/env python3
"""The pictures and generated documents the README and HANDBOOK show:

    docs/images/board_top.png, board_bottom.png, board_iso.png   KiCad's 3D renders
    docs/images/housing_*.png                                    enclosure/out's renders
    docs/images/schematic.png, docs/GPiBridge_schematic.pdf      the schematic
    docs/PINOUT.md                                               from gen/pins.py

    python3 tools/make_docs.py      (GPIBRIDGE_VARIANT=lite: the Lite's, as
                                     docs/images/lite_*.png and docs/GPiBridgeLite_schematic.pdf)
"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
import kienv
import pins as PINS
import board_info as BI

DOCS = os.path.join(ROOT, "docs")
IMG = os.path.join(DOCS, "images")
PCB = BI.PCB
PRE = BI.IMAGE_PREFIX


def renders():
    for name, args in (("board_top", ["--side", "top"]), ("board_bottom", ["--side", "bottom"]),
                       ("board_iso", ["--rotate", "-50,0,30", "--zoom", "1.0"])):
        kienv.run_cli(["pcb", "render", "--width", "2000", "--height", "1100", "--quality", "high",
                       "--background", "opaque", "-o", os.path.join(IMG, PRE + name + ".png")] + args + [PCB])
    for name in ("closed", "open", "front", "usb_end"):
        src = os.path.join(ROOT, "enclosure", "out", "render_%s%s.png" % (PRE, name))
        if os.path.exists(src):
            shutil.copy(src, os.path.join(IMG, "%shousing_%s.png" % (PRE, name)))


def schematic():
    import render_sch
    out = os.path.join(BI.SCRATCH, "view")
    render_sch.render(out)
    shutil.copy(os.path.join(out, BI.NAME + "_schematic.pdf"), os.path.join(DOCS, BI.NAME + "_schematic.pdf"))
    shutil.copy(os.path.join(out, PRE + "schematic.png"), os.path.join(IMG, PRE + "schematic.png"))


def pinout():
    L = ["# GPiBridge and GPiBridge Lite rev %s: pinout" % BI.REV, "",
         "Written by `tools/make_docs.py` from `gen/pins.py`, the one source of truth. Both boards",
         "use the same pins; on the Lite the bus lines meet the plug through 100 R each, not through",
         "the transceivers, PE and the TE pins go nowhere, DC carries the board ID (R21: 1 k to",
         "ground there, 10 k to 3.3 V on GPiBridge) and BUS_PWR_EN lights the green BUS LED.", "",
         "## RP2354A GPIO", "", "| GPIO | net | what it is |", "|---|---|---|"]
    for g in sorted(PINS.GPIO):
        net, what = PINS.GPIO[g]
        L.append("| %d | %s | %s |" % (g, net, what or "data, via SN75160B (the Lite: 100 R)"))
    L += ["", "## The IEEE-488 plug (J2), by contact", "",
          "| contact | signal | contact | signal |", "|---|---|---|---|"]
    names = {1: "DIO1", 2: "DIO2", 3: "DIO3", 4: "DIO4", 5: "EOI", 6: "DAV", 7: "NRFD", 8: "NDAC", 9: "IFC",
             10: "SRQ", 11: "ATN", 12: "shield", 13: "DIO5", 14: "DIO6", 15: "DIO7", 16: "DIO8", 17: "REN",
             18: "GND (DAV)", 19: "GND (NRFD)", 20: "GND (NDAC)", 21: "GND (IFC)", 22: "GND (SRQ)",
             23: "GND (ATN)", 24: "logic GND"}
    for c in range(1, 13):
        L.append("| %d | %s | %d | %s |" % (c, names[c], c + 12, names[c + 12]))
    L += ["", "## Debug connectors (JST-SH 3-pin, Raspberry Pi debug pinout, pin 1 nearest the board's top edge)", "",
          "| connector | pin 1 | pin 2 | pin 3 |", "|---|---|---|---|",
          "| J3 SWD | SWCLK | GND | SWDIO |", "| J4 UART (115200 baud) | RX (into the RP2354A) | GND | TX |", ""]
    open(os.path.join(DOCS, "PINOUT.md"), "w").write("\n".join(L))


def main():
    os.makedirs(IMG, exist_ok=True)
    renders()
    schematic()
    if not BI.LITE:
        pinout()                       # one for both boards
    print("docs: images in docs/images (%s*), docs/%s_schematic.pdf%s"
          % (PRE or "", BI.NAME, "" if BI.LITE else ", docs/PINOUT.md"))


if __name__ == "__main__":
    main()
