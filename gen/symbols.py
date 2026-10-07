"""The symbols drawn for GPiBridge (the rest are KiCad's, vendored by
gen/library.py).  Each is drawn the way the schematic flows: inputs and the
USB on the left, signals leaving to the right, supplies on top, grounds below.

Pin numbers come from the datasheets' pin figures, cited per symbol, and
tools/check_pins.py compares them with the datasheet tables again.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
sys.path.insert(0, HERE)
import kisch
from kisch import _hdr, _pin, _rect, _poly

G = 2.54


def _close(out):
    out += ['(embedded_fonts no)', ')']
    return "\n".join(out)


def box_symbol(name, ref, left, right, top, bottom, w, keywords="", value=None,
               top_pitch=G, top_x=None, extra=(), bottom_x=None):
    """A rectangle `w` wide.  left/right: lists of (number, name, type) or
    None for a gap, top to bottom.  top/bottom: (number, name, type) left to
    right, at `top_pitch` (or at explicit x positions `top_x`)."""
    rows = max(len(left), len(right))
    hh = rows * G / 2.0 + G / 2.0
    hw = w / 2.0
    out = _hdr(name, ref, value or name, hh + 3.81, keywords=keywords)
    out.append('(symbol "%s_0_1"' % name)
    out.append(_rect(-hw, hh, hw, -hh))
    out.extend(extra)
    out.append(')')
    out.append('(symbol "%s_1_1"' % name)
    y0 = hh - G
    for i, p in enumerate(left):
        if p:
            out.append(_pin(p[0], p[1], -hw - 5.08, y0 - i * G, 0, 5.08, p[2]))
    for i, p in enumerate(right):
        if p:
            out.append(_pin(p[0], p[1], hw + 5.08, y0 - i * G, 180, 5.08, p[2]))
    xs = top_x or [-(len(top) - 1) * top_pitch / 2.0 + i * top_pitch for i in range(len(top))]
    for x, p in zip(xs, top):
        out.append(_pin(p[0], p[1], x, hh + 5.08, 270, 5.08, p[2]))
    bx = bottom_x or [-(len(bottom) - 1) * G + i * 2 * G for i in range(len(bottom))]
    for x, p in zip(bx, bottom):
        out.append(_pin(p[0], p[1], x, -hh - 5.08, 90, 5.08, p[2]))
    out.append(')')
    return _close(out), dict(hw=hw, hh=hh, top_x=xs)


B, I, O, PI, PO, PA, NC = "bidirectional", "input", "output", "power_in", "power_out", "passive", "no_connect"

# ---------------------------------------------------------------------------
# RP2354A: RP2350 datasheet, Table 1674 (QFN-60 numbers) and Figure "RP2350A
# pinout"; the same numbers as KiCad's MCU_RaspberryPi:RP2350A.  The four
# QSPI data pins and SCLK reach the flash inside the package; only QSPI_SS is
# used outside (BOOTSEL).
import pins as PINS

_gp = {0: 2, 1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9, 7: 10, 8: 12, 9: 13, 10: 14, 11: 15, 12: 16, 13: 17,
       14: 18, 15: 19, 16: 27, 17: 28, 18: 29, 19: 31, 20: 32, 21: 33, 22: 34, 23: 35, 24: 36,
       25: 37, 26: 40, 27: 41, 28: 42, 29: 43}
GPIO_PIN = dict(_gp)        # GPIO number -> QFN-60 pin number


def _g(n):
    nm = "GPIO%d" % n + ("/ADC%d" % (n - 26) if n >= 26 else "")
    return (str(_gp[n]), nm, B)


def _rows(nets):
    return [(_g(PINS.GPIO_OF[n]) if n else None) for n in nets]


# Left side: the USB pair, the crystal, the debug port, reset and BOOTSEL, the
# unused QSPI pins, then the GPIOs that are not bus lines.  Empty rows leave
# room for each pin's parts (crystal caps, pull-ups) to hang free.
_LEFT_FIXED = {"USB_DM": ("51", "USB_DM", B), "USB_DP": ("52", "USB_DP", B), "XIN": ("21", "XIN", I),
               "XOUT": ("22", "XOUT", O), "SWCLK": ("24", "SWCLK", I), "SWDIO": ("25", "SWDIO", B),
               "RUN": ("26", "RUN", I), "QSPI_SS": ("60", "~{QSPI_SS}", B), "QSPI_SCLK": ("56", "QSPI_SCLK", B),
               "QSPI_SD0": ("57", "QSPI_SD0", B), "QSPI_SD1": ("59", "QSPI_SD1", B),
               "QSPI_SD2": ("58", "QSPI_SD2", B), "QSPI_SD3": ("55", "QSPI_SD3", B)}


def _left(n):
    if n is None:
        return None
    if n in _LEFT_FIXED:
        return _LEFT_FIXED[n]
    return _g(PINS.GPIO_OF[n])


RP_LEFT = [_left(n) for n in PINS.LEFT_ROWS]
RP_RIGHT = _rows(PINS.RIGHT_ROWS)
# supplies, left to right: the core regulator, the 1.1 V core, the 3.3 V I/O
RP_TOP = [("46", "VREG_AVDD", PI), ("49", "VREG_VIN", PI), ("48", "VREG_LX", PO), ("50", "VREG_FB", PI),
          ("6", "DVDD", PI), ("23", "DVDD", PI), ("39", "DVDD", PI),
          ("1", "IOVDD", PI), ("11", "IOVDD", PI), ("20", "IOVDD", PI), ("30", "IOVDD", PI),
          ("38", "IOVDD", PI), ("45", "IOVDD", PI),
          ("54", "QSPI_IOVDD", PI), ("53", "USB_OTP_VDD", PI), ("44", "ADC_AVDD", PI)]
RP_BOTTOM = [("47", "VREG_PGND", PI), ("61", "GND", PI)]
RP_TOP_PITCH = 7.62


def rp2354a():
    w = (len(RP_TOP) + 1) * RP_TOP_PITCH
    return box_symbol("RP2354A", "U", RP_LEFT, RP_RIGHT, RP_TOP, RP_BOTTOM, w,
                      keywords="Raspberry Pi RP2354A: RP2350 with 2 MB flash in the package, QFN-60",
                      top_pitch=RP_TOP_PITCH)


# ---------------------------------------------------------------------------
# SN75160B (TI SLLS004B, DW package pin figure): 1 TE, 2-9 B1-B8, 10 GND,
# 11 PE, 12-19 D8-D1, 20 VCC.  PE is active HIGH (3-state outputs); KiCad's
# own symbol draws it as ~{PE}, which is wrong.  Terminal side left, bus right.
_T60 = {"DIO%d" % i: (str(20 - PINS.U2_CHANNEL["DIO%d" % i]), "D%d" % PINS.U2_CHANNEL["DIO%d" % i]) for i in range(1, 9)}
_T60.update({"PE": ("11", "PE"), "TE_DATA": ("1", "TE")})
U2_ROWS = PINS.RIGHT_ROWS[PINS.RIGHT_ROWS.index("DIO1"):PINS.RIGHT_ROWS.index("TE_DATA") + 1]
SN60_LEFT = [((_T60[n][0], _T60[n][1], I if n in ("PE", "TE_DATA") else B) if n else None) for n in U2_ROWS]
SN60_RIGHT = [((str(PINS.U2_CHANNEL[n] + 1), "B%d" % PINS.U2_CHANNEL[n], B) if n and n.startswith("DIO") else None)
              for n in U2_ROWS]


def sn75160b():
    return box_symbol("SN75160B", "U", SN60_LEFT, SN60_RIGHT, [("20", "VCC", PI)], [("10", "GND", PI)], 15.24,
                      keywords="TI SN75160B octal IEEE-488 bus transceiver, data lines",
                      top_x=[0.0], bottom_x=[2 * G])


# SN75161B (TI SLLS005B, DW package pin figure): 1 TE, 2 REN, 3 IFC, 4 NDAC,
# 5 NRFD, 6 DAV, 7 EOI, 8 ATN, 9 SRQ (bus side), 10 GND, 11 DC, 12 SRQ,
# 13 ATN, 14 EOI, 15 DAV, 16 NRFD, 17 NDAC, 18 IFC, 19 REN (terminal side),
# 20 VCC.  Rows in the order of the MCU's GPIO8-15, each straight across.
_T61 = {"EOI": "14", "DAV": "15", "NRFD": "16", "NDAC": "17", "ATN": "13", "SRQ": "12", "IFC": "18",
        "REN": "19", "TE_CTRL": "1", "DC": "11"}
_B61 = {"EOI": "7", "DAV": "6", "NRFD": "5", "NDAC": "4", "ATN": "8", "SRQ": "9", "IFC": "3", "REN": "2"}
U3_ROWS = PINS.RIGHT_ROWS[PINS.RIGHT_ROWS.index("DC"):]
SN61_LEFT = [((_T61[n], n.replace("TE_CTRL", "TE"), I if n in ("TE_CTRL", "DC") else B) if n else None) for n in U3_ROWS]
SN61_RIGHT = [((_B61[n], n, B) if n in _B61 else None) for n in U3_ROWS]


def sn75161b():
    return box_symbol("SN75161B", "U", SN61_LEFT, SN61_RIGHT, [("20", "VCC", PI)], [("10", "GND", PI)], 15.24,
                      keywords="TI SN75161B octal IEEE-488 bus transceiver, control lines, single controller",
                      top_x=[0.0], bottom_x=[2 * G])


# ---------------------------------------------------------------------------
# The IEEE-488 plug, pins numbered by IEEE-488 contact number (IEEE 488.1,
# the receptacle figure: contacts 1-12 along the wide side of the D).  Rows in
# the order the transceivers deliver them.
GPIB_SIGNALS = {1: "DIO1", 2: "DIO2", 3: "DIO3", 4: "DIO4", 13: "DIO5", 14: "DIO6", 15: "DIO7", 16: "DIO8",
                5: "EOI", 6: "DAV", 7: "NRFD", 8: "NDAC", 11: "ATN", 10: "SRQ", 9: "IFC", 17: "REN"}
GPIB_GROUNDS = {12: "SHIELD", 18: "GND(DAV)", 19: "GND(NRFD)", 20: "GND(NDAC)", 21: "GND(IFC)",
                22: "GND(SRQ)", 23: "GND(ATN)", 24: "LOGIC_GND"}
_CONTACT = {v: k for k, v in GPIB_SIGNALS.items()}
# the plug's rows line up with the transceivers' bus rows, so every bus line
# runs straight across; the eight grounds follow
# runs straight across; the eight ground contacts sit in the gap between the
# two transceivers, where no bus line runs
_span = PINS.RIGHT_ROWS[PINS.RIGHT_ROWS.index("DIO1"):PINS.RIGHT_ROWS.index("REN") + 1]
_gap0 = _span.index("TE_DATA") + 4
PLUG_LEFT = [((str(_CONTACT[n]), n, B) if n in _CONTACT else None) for n in _span]
for _k, _c in enumerate((12, 18, 19, 20, 21, 22, 23, 24)):
    assert PLUG_LEFT[_gap0 + _k] is None and _span[_gap0 + _k] is None
    PLUG_LEFT[_gap0 + _k] = (str(_c), GPIB_GROUNDS[_c], PA)


def gpib_plug():
    name = "IEEE488_Plug"
    left = PLUG_LEFT
    rows = len(left)
    hh = rows * G / 2.0 + G / 2.0
    w = 17.78
    hw = w / 2.0
    out = _hdr(name, "J", "IEEE-488", hh + 3.81,
               keywords="IEEE-488 (GPIB) 24-contact male plug; pins are IEEE contact numbers")
    out.append('(symbol "%s_0_1"' % name)
    out.append(_rect(-hw, hh, hw, -hh))
    # the plug's face, small, on the right of the box: a D-shaped outline
    d = [(hw - 4.6, hh - 2.0), (hw - 1.4, hh - 2.0), (hw - 1.9, hh - 15.0), (hw - 4.1, hh - 15.0), (hw - 4.6, hh - 2.0)]
    out.append(_poly(d, fill="none", width=0.2))
    for i in range(6):
        y = hh - 3.6 - 2.0 * i
        out.append(_poly([(hw - 3.7, y), (hw - 3.3, y)], width=0.3))
        out.append(_poly([(hw - 2.7, y), (hw - 2.3, y)], width=0.3))
    out.append(')')
    out.append('(symbol "%s_1_1"' % name)
    y0 = hh - G
    for i, p in enumerate(left):
        if p:
            out.append(_pin(p[0], p[1], -hw - 5.08, y0 - i * G, 0, 5.08, p[2]))
    out.append(')')
    return _close(out), dict(hw=hw, hh=hh)


def debug_conn(name, pins, keywords):
    """A 3-pin JST-SH (Raspberry Pi debug connector) with its two mounting
    pads; pins on the right, pointing at the chip it serves."""
    hh = 5.08
    hw = 3.81
    out = _hdr(name, "J", name.replace("Conn_", ""), hh + 1.27, keywords=keywords)
    out.append('(symbol "%s_0_1"' % name)
    out.append(_rect(-hw, hh, hw, -hh))
    out.append(')')
    out.append('(symbol "%s_1_1"' % name)
    for i, (num, nm, t) in enumerate(pins):
        out.append(_pin(num, nm, hw + 5.08, hh - G * (i + 1), 180, 5.08, t))
    out.append(_pin("MP", "", 0, -hh - 5.08, 90, 5.08, PA))     # the mounting pads, to ground
    out.append(')')
    return _close(out), {}


def conn_swd():
    # Raspberry Pi 3-pin debug connector specification: 1 SC, 2 GND, 3 SD
    return debug_conn("Conn_SWD", [("1", "SWCLK", PA), ("3", "SWDIO", PA), ("2", "GND", PA)],
                      "Raspberry Pi 3-pin debug connector, serial wire debug: 1 SC, 2 GND, 3 SD")


def conn_uart():
    # the same specification, UART: 1 RX (into the target), 2 GND, 3 TX
    return debug_conn("Conn_UART", [("1", "RX", PA), ("3", "TX", PA), ("2", "GND", PA)],
                      "Raspberry Pi 3-pin debug connector, UART: 1 RX (into this board), 2 GND, 3 TX")


CUSTOM = {"RP2354A": rp2354a, "SN75160B": sn75160b, "SN75161B": sn75161b, "IEEE488_Plug": gpib_plug,
          "Conn_SWD": conn_swd, "Conn_UART": conn_uart}

RAILS = {"VBUS": False, "+3V3": False, "+1V1": False, "+5V_GPIB": False, "GND": True}
