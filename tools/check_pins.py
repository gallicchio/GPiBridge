#!/usr/bin/env python3
"""Check every pin of the symbols drawn for this board against its datasheet.

    python3 tools/check_pins.py          (needs datasheets/txt: tools/fetch_datasheets.py)

  * RP2354A: each pin name and number against the RP2350 datasheet's QFN-60
    tables (14.8.2), and UART0 on its GPIOs against the function table.
    The power table lists IOVDD as "11, 20, 30, 38, 45, 54" and QSPI_IOVDD as
    54; the pinout figure, KiCad's symbol and Raspberry Pi's own board have
    pin 1 = IOVDD and 54 = QSPI_IOVDD.  The figure is taken, and the
    difference is reported, not failed (all of them go to 3.3 V here).
  * SN75160B and SN75161B: against TI's DW package pin figures, transcribed
    below (pdftotext scrambles those figures).
  * The IEEE-488 plug: against the contact assignments of IEEE 488.1.
Exit status 1 on any mismatch.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
sys.path.insert(0, HERE)
TXT = os.path.join(ROOT, "datasheets", "txt")
import symbols as SY

problems, notes = [], []


def symbol_pins(rows):
    return {p[0]: p[1] for p in rows if p}


def rp2354a():
    t = open(os.path.join(TXT, "rp2350-datasheet.txt"), encoding="utf-8").read()
    start = t.index("14.8.2.2. Pin list")
    t = t[start:start + 40000]
    want = {}
    for m in re.finditer(r"^\s*(GPIO\d+)(?:_ADC\d)?\s+(\d+)\s+(?:\d+|-)\s+Digital", t, re.M):
        want.setdefault(m.group(1), m.group(2))
    for name in ("QSPI_SD3", "QSPI_SCLK", "QSPI_SD0", "QSPI_SD2", "QSPI_SD1", "QSPI_SS", "XIN", "XOUT",
                 "RUN", "SWCLK", "SWDIO", "USB_DP", "USB_DM"):
        m = re.search(r"^\s*%s\s+(\d+)\s+\d+" % name, t, re.M)
        want[name] = m.group(1) if m else None
    for name in ("QSPI_IOVDD", "USB_OTP_VDD", "ADC_AVDD", "VREG_AVDD", "VREG_PGND", "VREG_LX", "VREG_VIN",
                 "VREG_FB"):
        m = re.search(r"^\s*%s\s+(\d+)\s+\d+" % name, t, re.M)
        want[name] = m.group(1) if m else None
    m = re.search(r"^\s*DVDD\s+([\d, ]+?)\s{2,}", t, re.M)
    dvdd = set(x.strip() for x in m.group(1).split(","))
    m = re.search(r"^\s*IOVDD\s+([\d, ]+?)\s{2,}", t, re.M)
    iovdd_table = set(x.strip() for x in m.group(1).split(","))
    iovdd_figure = {"1", "11", "20", "30", "38", "45"}
    if iovdd_table != iovdd_figure:
        notes.append("RP2350 datasheet: the power table's IOVDD pins %s differ from the pinout figure's %s; "
                     "the figure (and KiCad, and Raspberry Pi's board) is followed"
                     % (sorted(iovdd_table, key=int), sorted(iovdd_figure, key=int)))
    have = {}
    for p in SY.RP_LEFT + SY.RP_RIGHT + SY.RP_TOP + SY.RP_BOTTOM:
        if p:
            have.setdefault(p[1].replace("~{", "").replace("}", "").split("/")[0], set()).add(p[0])
    n = 0
    for name, num in want.items():
        if num is None:
            problems.append("RP2354A: %s not found in the datasheet text" % name)
            continue
        if num not in have.get(name, set()):
            problems.append("RP2354A: %s is pin %s in the datasheet, %s in the symbol" % (name, num, have.get(name)))
        n += 1
    if have.get("DVDD") != dvdd:
        problems.append("RP2354A: DVDD %s vs datasheet %s" % (have.get("DVDD"), dvdd))
    if have.get("IOVDD") != iovdd_figure:
        problems.append("RP2354A: IOVDD %s vs the pinout figure %s" % (have.get("IOVDD"), iovdd_figure))
    if have.get("GND") != {"61"}:
        problems.append("RP2354A: the exposed pad should be pin 61 (GND)")
    allp = [p[0] for p in SY.RP_LEFT + SY.RP_RIGHT + SY.RP_TOP + SY.RP_BOTTOM if p]
    if sorted(allp, key=int) != [str(i) for i in range(1, 62)]:
        problems.append("RP2354A: the symbol does not have pins 1-61 exactly once each")
    # UART0 on GPIO16 (TX) and GPIO17 (RX): the function table's F2 column
    import pins as PINS
    full = open(os.path.join(TXT, "rp2350-datasheet.txt"), encoding="utf-8").read()
    for net, fn in (("UART_TX", "UART0 TX"), ("UART_RX", "UART0 RX")):
        gp = PINS.GPIO_OF[net]
        if not re.search(r"^\s*%d\s+(?:HSTX\s+)?SPI\d \w+\s+%s" % (gp, fn), full, re.M):
            problems.append("RP2350: GPIO%d is not %s in the function table" % (gp, fn))
    return "RP2354A: %d named pins and 3 supplies checked against the datasheet tables" % n


# TI's DW package pin figures (page 1 of each datasheet), transcribed and
# checked by eye against the rendered figure on 2026-10-06.  pdftotext jumbles
# these figures, so they are not parsed.
SN75160B_FIGURE = {1: "TE", 2: "B1", 3: "B2", 4: "B3", 5: "B4", 6: "B5", 7: "B6", 8: "B7", 9: "B8", 10: "GND",
                   11: "PE", 12: "D8", 13: "D7", 14: "D6", 15: "D5", 16: "D4", 17: "D3", 18: "D2", 19: "D1",
                   20: "VCC"}
SN75161B_FIGURE = {1: "TE", 2: "REN", 3: "IFC", 4: "NDAC", 5: "NRFD", 6: "DAV", 7: "EOI", 8: "ATN", 9: "SRQ",
                   10: "GND", 11: "DC", 12: "SRQ", 13: "ATN", 14: "EOI", 15: "DAV", 16: "NRFD", 17: "NDAC",
                   18: "IFC", 19: "REN", 20: "VCC"}


def ti(name, rows, figure):
    have = {int(p[0]): p[1] for p in rows if p}
    have.setdefault(20, "VCC")
    have.setdefault(10, "GND")
    for num, nm in figure.items():
        if have.get(num) != nm:
            problems.append("%s: pin %d is %r in the symbol, %r in TI's pin figure" % (name, num, have.get(num), nm))
    if set(have) != set(figure):
        problems.append("%s: pins %s in the symbol, %s in the figure" % (name, sorted(have), sorted(figure)))
    return "%s: %d pins checked against TI's pin figure" % (name, len(figure))


def plug():
    # IEEE 488.1 contact assignments
    std = {1: "DIO1", 2: "DIO2", 3: "DIO3", 4: "DIO4", 5: "EOI", 6: "DAV", 7: "NRFD", 8: "NDAC", 9: "IFC",
           10: "SRQ", 11: "ATN", 12: "SHIELD", 13: "DIO5", 14: "DIO6", 15: "DIO7", 16: "DIO8", 17: "REN",
           18: "GND(DAV)", 19: "GND(NRFD)", 20: "GND(NDAC)", 21: "GND(IFC)", 22: "GND(SRQ)", 23: "GND(ATN)",
           24: "LOGIC_GND"}
    have = {int(p[0]): p[1] for p in SY.PLUG_LEFT if p}
    for c, name in std.items():
        if have.get(c) != name:
            problems.append("IEEE-488 plug: contact %d is %r, the standard says %r" % (c, have.get(c), name))
    return "IEEE-488 plug: 24 contacts checked against IEEE 488.1"


def main():
    out = [rp2354a()]
    out.append(ti("SN75160B", SY.SN60_LEFT + SY.SN60_RIGHT, SN75160B_FIGURE))
    out.append(ti("SN75161B", SY.SN61_LEFT + SY.SN61_RIGHT, SN75161B_FIGURE))
    out.append(plug())
    for o in out:
        print(o)
    for n in notes:
        print("NOTE: " + n)
    for p in problems:
        print("MISMATCH: " + p)
    print("pins: %s" % ("all agree with the datasheets" if not problems else "%d mismatches" % len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
