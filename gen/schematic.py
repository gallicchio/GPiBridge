#!/usr/bin/env python3
"""Draw GPiBridge's schematic: one A3 sheet, in the Art of Electronics style.

Signals run left to right: USB-C, the RP2354A, the two IEEE-488
transceivers, the plug.  Power comes from the top.  Every supply pin
has its own capacitor, drawn at that pin.  Notes sit at the nodes they
describe.

    python3 gen/schematic.py        writes hardware/GPiBridge.kicad_sch

Everything is placed relative to the RP2354A's pins, whose order comes from
gen/pins.py, so moving a signal to another GPIO moves its whole line.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
import kisch
from parts import PARTS, LIB
import pins as PINS
import symbols as SYMB
import board_info as BI

HW = os.path.join(ROOT, "hardware")
G = 2.54
S = None
REFS = {}
NOTE = (255, 255, 194)


# ---------------------------------------------------------------------------
def part(key, ref, x, y, rot=0, unit=1, value=None, mirror=None, text="auto", fsize=1.27, sym=None, **kw):
    """Place PARTS[key] as `ref`.  text: "auto" (reference above, value
    below), "right" (both to the right of a vertical part), "hide"."""
    p = dict(PARTS[key])
    if sym:
        p["sym"] = LIB + ":" + sym
    fields = {"MPN": p["mpn"]} if p["mpn"] else {}
    value = p["value"] if value is None else value
    if text == "right":
        dx = 2.8 if p["sym"].endswith(":C") else 1.9          # clear of a capacitor's wide plates
        kw.setdefault("ref_at", (x + dx, y - 0.3))
        kw.setdefault("val_at", (x + dx, y + 0.3))
    if text == "hide":
        kw["hide_ref"] = kw["hide_value"] = True
    pl = S.sym(p["sym"], x, y, rot=rot, ref=ref, value=value, footprint=p["fp"], unit=unit, mirror=mirror,
               lcsc=p["lcsc"], fields=fields, fsize=fsize, **kw)
    REFS.setdefault(ref, key)
    return pl


def _pins(pl):
    _, pins = kisch.SYMS.get(pl.lib_id)
    return [pl.pin(p["num"]) for p in pins if p["unit"] in (0, pl.unit)]


def hpart(key, ref, xc, y, unit=1, **kw):
    """A two-pin part lying on a horizontal line; returns (left, right)."""
    pl = part(key, ref, xc, y, rot=90, unit=unit, **kw)
    a, b = sorted(_pins(pl), key=lambda q: q[0])
    return a, b


def vpart(key, ref, x, yc, unit=1, **kw):
    """A two-pin part standing on a vertical line; returns (top, bottom)."""
    kw.setdefault("text", "right")
    pl = part(key, ref, x, yc, unit=unit, **kw)
    a, b = sorted(_pins(pl), key=lambda q: q[1])
    return a, b


def gnd(x, y):
    return S.power("GND", x, y)


def flag(net, x, y):
    return S.power(net, x, y)


def W(*pts):
    S.wires(*pts)


def J(x, y):
    S.junction(x, y)


_flags = iter("#FLG%02d" % i for i in range(1, 50))


def pwr_flag(x, y, rot=0):
    """KiCad's PWR_FLAG, at the point where a rail is driven from outside the
    sheet's own parts (a connector, a switch, an inductor)."""
    return S.sym(PARTS["PWR_FLAG"]["sym"], x, y, rot=rot, ref=next(_flags), value="PWR_FLAG", footprint="",
                 in_bom=False, on_board=False, hide_ref=True, hide_value=True)


def label(x, y, name, size=1.0):
    """A net name on a wire (the wire carries on: nothing disappears)."""
    S.label(x, y, name, size=size)


def note(x, y, text, cols=44, size=1.0):
    return S.note(x, y, text, size=size, cols=cols, color=NOTE)


def gpin(net):
    """QFN pin number of the GPIO carrying `net`."""
    return str(SYMB.GPIO_PIN[PINS.GPIO_OF[net]])


# ---------------------------------------------------------------------------
LITE_NOTE = ("An RP2354A runs the IEEE-488 handshake and talks to the host over USB as a Prologix-compatible "
             "serial controller. GPiBridge Lite has no bus transceivers: each of the sixteen bus lines meets an "
             "RP2354A pin through 100 R. The firmware drives them open-drain (low to assert, let go to release), "
             "and the pads' output is forced low in hardware, so no pin can drive a line high. That carries one "
             "instrument, or a few on a short cable: 12 mA sinks against the standard's 48 mA, and no "
             "terminations of its own. For a full bus, GPiBridge. The plug hangs under the board; everything "
             "else is on top.")


def lite_bus_side(pin, ry, xR, YV):
    """GPiBridge Lite: every bus line from its RP2354A pin through 100 R
    straight across to the plug, whose rows are in the order of the pins
    (gen/symbols.py); the green BUS LED on BUS_PWR_EN."""
    xRs = xR + 20.32                        # the series resistors' column
    hhJ = len(SYMB.PLUG_LEFT) * G / 2 + G / 2
    J2x = xR + 48.26
    J2y = ry(gpin("DIO1")) + hhJ - G
    J2 = part("GPIB", "J2", J2x, J2y, ref_at=(J2x - 8.89, J2y - hhJ - 1.0), val_at=(J2x - 8.89, J2y + hhJ + 1.2))
    for p in SYMB.PLUG_LEFT:
        if not p or p[2] == "passive":
            continue
        num, name = p[0], p[1]
        gp = PINS.GPIO_OF[name]
        y = ry(gpin(name))
        dst = J2.pin(num)
        assert abs(dst[1] - y) < 0.01, (name, dst, y)
        # neighbouring rows alternate between two columns, so each resistor has
        # room above it for its name; their value is in the note below
        x = xRs + (7.62 if PINS.RIGHT_ROWS.index(name) % 2 else 0.0)
        l, r = hpart("R100", "R%d" % (30 + gp), x, y, ref_at=(x, y - 1.3), justify="center", hide_value=True,
                     fsize=1.0)
        W(pin(gpin(name)), l)
        W(r, dst)
        label(xR + 0.8, y, name)
    _plug_grounds(J2)
    for net in PINS.LITE_UNUSED:                            # GPiBridge's transceiver controls
        S.nc(*pin(gpin(net)))
    # DC: the board ID, 1 k to ground where GPiBridge has 10 k to 3.3 V
    y = ry(gpin("DC"))
    xp = xR + 8.89
    W(pin(gpin("DC")), (xp, y))
    label(xR + 0.8, y, "DC")
    t, b = vpart("R1K", PINS.LITE_PULL_DOWN["DC"], xp, y + 3.81, fsize=1.0)
    gnd(*b)
    note(J2x + 10.5, y - 14.0, "DC: the board ID. R21 is 1 k down here, 10 k up on GPiBridge. The firmware "
         "reads DC at start-up, before it drives anything: low runs the Lite's pin layer.", cols=22)
    # the green BUS LED, on the signal that powers GPiBridge's transceivers
    y = ry(gpin("BUS_PWR_EN"))
    l, r = hpart("R100", "R18", xR + 15.24, y)
    W(pin(gpin("BUS_PWR_EN")), l)
    label(xR + 0.8, y, "BUS_PWR_EN")
    xd = xR + 27.94
    d2 = part("LED_G", "D2", xd, y, rot=180, value="BUS green", ref_at=(xd - 5.6, y - 4.8), val_at=(xd - 2.2, y - 4.8))
    W(r, d2.pin("2"))
    gnd(*d2.pin("1"))
    note(xR + 6.0, y - 24.0, "BUS (green): lit while the firmware is on the bus. BUS_PWR_EN is the signal that "
         "switches GPiBridge's transceivers on, which lights the same LED there.", cols=40)
    xt5 = xR + 30.48
    part("TP", "TP5", xt5, YV + 7.62, value="GND", ref_at=(xt5 + 1.5, YV + 4.0), val_at=(xt5 + 1.5, YV + 5.7),
         fsize=1.0)
    gnd(xt5, YV + 7.62)
    note(xR + 3.0, ry(gpin("TE_DATA")) + 3.0,
         "R30-R45: 100 R in every line (R30 + the GPIO number). They hold the current to about 35 mA if an "
         "instrument drives a line high while the RP2354A holds it low, and static on a contact reaches the "
         "pin through them. A line held low sits at about 0.25 V with one instrument's terminations on it "
         "(3 k to 5 V, 6.2 k to ground), about 0.6 V with three (TTL low: under 0.8 V).", cols=26)
    note(J2x + 10.5, J2y - hhJ, "IEEE-488 plug, hand-soldered. Contacts 1-12 run along the wide side of the D. "
         "TTL levels, low = true. The RP2354A's bus pins are 5 V tolerant while it is powered (5.5 V max) and "
         "take up to 3.63 V while it is not: a standard bus idles at about 3.4 V.", cols=22)
    note(J2x + 10.5, ry(gpin("NRFD")) - 4.0, "Open-drain: a line is asserted by driving its pin low and "
         "released by letting go. NRFD, NDAC and SRQ are wired-OR on every bus, and the Lite treats the other "
         "lines the same way, so it never needs to know who else is driving.", cols=22)


def _plug_grounds(J2):
    """The plug's shield and seven ground returns, joined down to one ground."""
    gp_ = [J2.pin(p[0]) for p in SYMB.PLUG_LEFT if p and p[2] == "passive"]
    xg2 = gp_[0][0] - 2.54
    for q in gp_:
        W(q, (xg2, q[1]))
    W((xg2, gp_[0][1]), (xg2, gp_[-1][1]))
    for q in gp_[1:-1]:
        J(xg2, q[1])
    W((xg2, gp_[-1][1]), (xg2, gp_[-1][1] + 2.54))
    J(xg2, gp_[-1][1])
    gnd(xg2, gp_[-1][1] + 5.08)
    W((xg2, gp_[-1][1] + 2.54), (xg2, gp_[-1][1] + 5.08))


# ---------------------------------------------------------------------------
def draw():
    global S
    S = kisch.Sch(BI.NAME, BI.NAME + ".kicad_sch", paper="A3",
                  title="%s: %s adapter" % (BI.TITLE, BI.TAGLINE), rev=BI.REV, date=BI.DATE,
                  company=BI.AUTHORS + ("  --  https://" + BI.URL if BI.URL else ""),
                  comments=["Made by gen/schematic.py from gen/pins.py and gen/parts.py: edit those, not this file",
                            BI.LICENCE,
                            ("RP2354A on the bus through 100 R" if BI.LITE else "RP2354A + SN75160B/SN75161B")
                            + ": a Prologix-compatible '++' controller over USB"])
    kisch.SYMS.load_library(os.path.join(HW, "lib", LIB + ".kicad_sym"), LIB)

    S.text(17.78, 21.59, "%s: %s" % (BI.TITLE, BI.TAGLINE), size=3.0, bold=True)
    note(17.78, 238.76, LITE_NOTE if BI.LITE else
         "An RP2354A runs the IEEE-488 handshake and talks to the host over USB as a Prologix-compatible "
         "serial controller (and, in a later firmware, a USBTMC/USB488 instrument). Two TI transceivers (SN75160B "
         "data, SN75161B control) drive the bus as IEEE 488.1 asks: 48 mA sinks, terminations, hysteresis, and no "
         "load on the bus when unpowered. Their 5 V is switched on by the firmware once the host has configured "
         "the USB port, so the board is off the bus until the firmware is ready. The plug hangs under the board; "
         "everything else is on top.",
         cols=64, size=1.27)

    # ---- the RP2354A --------------------------------------------------------
    UX, UY = 215.9, 157.48
    hw = (len(SYMB.RP_TOP) + 1) * SYMB.RP_TOP_PITCH / 2
    hh = max(len(SYMB.RP_LEFT), len(SYMB.RP_RIGHT)) * G / 2 + G / 2
    U1 = part("RP2354A", "U1", UX, UY, ref_at=(UX - hw, UY - hh - 1.2), val_at=(UX - hw, UY + hh + 1.2))
    pin = U1.pin

    def ry(num):
        return pin(num)[1]

    xL, xR = pin("51")[0], pin(gpin("DIO1"))[0]

    # ---- supplies along the top: each pin's wire rises to its rail; its
    # capacitor hangs from that wire, ground just below
    xs = {p[0]: pin(p[0])[0] for p in SYMB.RP_TOP}
    ytop = pin("46")[1]
    Y33, Y11, Yj = ytop - 27.94, ytop - 20.32, ytop - 15.24
    YV = Y33 - 15.24                                  # the VBUS rail
    caps = iter("C%d" % i for i in range(10, 22))

    def decap(num, key="C100N", ref=None):
        """The capacitor hangs beside its pin's wire; its name and value sit
        centred under its ground, between the wires."""
        x = xs[num]
        W((x, Yj), (x + G, Yj))
        t, b = vpart(key, ref or next(caps), x + G, Yj + 3.81, fsize=1.0, justify="center",
                     ref_at=(x + G, ytop - 2.0), val_at=(x + G, ytop - 2.0))
        gnd(*b)
        J(x, Yj)

    x = xs["46"]                                   # VREG_AVDD: 33 R and 4.7 uF (Raspberry Pi's R3, C9)
    t, b = vpart("R33_RPI", "R3", x, Y33 + 3.81, fsize=1.0)
    W(b, (x, ytop))
    W((x, b[1] + G), (x - G, b[1] + G))
    J(x, b[1] + G)
    pwr_flag(x - G, b[1] + G)
    decap("46", "C4U7_RPI", "C9")
    W((xs["49"], Y33), (xs["49"], ytop))            # VREG_VIN: 4.7 uF (C6)
    decap("49", "C4U7_RPI_WIDE", "C6")
    yL = ytop - 5.08                               # VREG_LX through L1 to the 1.1 V node
    W((xs["48"], ytop), (xs["48"], yL))
    xm = (xs["48"] + xs["50"]) / 2
    part("L3U3", "L1", xm, yL, rot=270, ref_at=(xm - 3.0, yL - 1.7), val_at=(xm - 3.0, yL + 1.5), fsize=1.0)
    W((xs["50"], ytop), (xs["50"], Y11))            # VREG_FB senses it; 4.7 uF (C7)
    J(xs["50"], yL)
    decap("50", "C4U7_RPI_WIDE", "C7")
    dv = [p[0] for p in SYMB.RP_TOP if p[1] == "DVDD"]
    W((xs["50"], Y11), (xs[dv[-1]], Y11))
    for n in dv:
        W((xs[n], Y11), (xs[n], ytop))
        if n != dv[-1]:
            J(xs[n], Y11)
        decap(n)
    flag("+1V1", xs["50"], Y11)
    J(xs[dv[0]] + 3.81, Y11)
    pwr_flag(xs[dv[0]] + 3.81, Y11)
    io = [p[0] for p in SYMB.RP_TOP if p[1] in ("IOVDD", "QSPI_IOVDD", "USB_OTP_VDD", "ADC_AVDD")]
    for n in io:
        W((xs[n], Y33), (xs[n], ytop))
        decap(n)
        if n != io[-1]:
            J(xs[n], Y33)
    W((xs["46"], Y33), (xs[io[-1]], Y33))
    J(xs["49"], Y33)
    for n in ("47", "61"):
        gnd(*pin(n))
    note(xs["46"] - 3.0, YV + 2.0,
         "Core regulator (1.1 V): Raspberry Pi's parts and layout, copied exactly (gen/rpi_minimal). L1 is "
         "polarity-marked: its dot must sit as their footprint shows.", cols=44)
    note(xs["1"] - 3.0, YV + 2.0,
         "3.3 V and 1.1 V: one 100 nF for every supply pin. On the board each sits at its pin, except where "
         "the pin is walled in by signal lines (pins 6, 11, 20, 23): those join it through the supply rings "
         "under the chip.", cols=44)

    # ---- USB-C ----------------------------------------------------------------
    J1x = 35.56
    J1 = part("USBC", "J1", J1x, ry("51"), ref_at=(J1x - 10.16, ry("51") - 19.1), val_at=(J1x - 10.16, ry("51") + 26.4))
    xst = J1.pin("A7")[0] + G
    for a, b in (("A7", "B7"), ("A6", "B6")):
        W(J1.pin(a), (xst, J1.pin(a)[1]), (xst, J1.pin(b)[1]), J1.pin(b))
    ydm, ydp = J1.pin("B7")[1], J1.pin("A6")[1]
    J(xst, ydm); J(xst, ydp)
    l, r = hpart("R27", "R1", xL - 17.78, ydm)
    W((xst, ydm), l); W(r, pin("51"))
    label(xst + 3.0, ydm, "USB_D-"); label(r[0] + 1.0, ydm, "USB_DM")
    l, r = hpart("R27", "R2", xL - 30.48, ydp, ref_at=(xL - 34.29, ydp + 3.0), val_at=(xL - 30.48, ydp + 1.6))
    W((xst, ydp), l); W(r, pin("52"))
    label(xst + 3.0, ydp, "USB_D+"); label(r[0] + 1.0, ydp, "USB_DP")
    note(xL - 52.0, ydp + 4.6, "USB 2.0 full speed, 12 Mbit/s. 27 R at the chip (RP2350 datasheet).", cols=40)
    cc1, cc2 = J1.pin("A5"), J1.pin("B5")
    l, r = hpart("R5K1", "R5", cc2[0] + 7.62, cc2[1], ref_at=(cc2[0] + 3.2, cc2[1] + 3.0),
                 val_at=(cc2[0] + 3.2, cc2[1] + 3.0))
    W(cc2, l); gnd(*r)
    l, r = hpart("R5K1", "R4", cc1[0] + 20.32, cc1[1], ref_at=(cc1[0] + 16.51, cc1[1] - 1.6),
                 val_at=(cc1[0] + 20.6, cc1[1] - 2.9))
    W(cc1, l); gnd(*r)
    note(cc1[0] + 27.0, cc1[1] + 1.4, "CC1, CC2: 5.1 k to ground say 'device'; the host then gives 5 V.", cols=32)
    for n in ("A8", "B8"):
        S.nc(*J1.pin(n))
    W(J1.pin("SH"), J1.pin("A1"))
    gnd(*J1.pin("A1"))
    xf = (J1.pin("SH")[0] + J1.pin("A1")[0]) / 2
    J(xf, J1.pin("SH")[1])
    pwr_flag(xf, J1.pin("SH")[1], rot=180)
    note(J1x - 20.0, ry("51") + 31.0, "USB-C. Takes 5 V, about 40 mA: the RP2354A and its LEDs." if BI.LITE else
         "USB-C. Takes 5 V, up to 270 mA (each transceiver 110 mA max); "
         "the transceivers wait for the host's 300 mA.", cols=30)

    # ---- VBUS rail and the 3.3 V LDO -------------------------------------------
    vb = J1.pin("A4")
    xvb = vb[0] + 5.08
    W(vb, (xvb, vb[1]), (xvb, YV))
    flag("VBUS", xvb, YV)
    J(vb[0] + G, vb[1])
    pwr_flag(vb[0] + G, vb[1])
    t, b = vpart("C10U", "C1", xvb + 7.62, YV + 6.35)
    W((xvb, YV), (xvb + 7.62, YV), t); gnd(*b)
    J(xvb + 7.62, YV)
    U4x = xs["46"] - 38.1
    U4 = part("XC6206", "U4", U4x, Y33, ref_at=(U4x - 6.0, Y33 - 4.0), val_at=(U4x - 16.0, Y33 + 9.5))
    vi, vo = U4.pin("3"), U4.pin("2")
    gnd(*U4.pin("1"))
    xin = vi[0] - 5.08
    W((xvb + 7.62, YV), (xin, YV), (xin, Y33), vi)
    J(xin, YV)
    t, b = vpart("C1U", "C2", xin - 5.08, Y33 + 6.35)
    W((xin, Y33), (xin - 5.08, Y33), t); gnd(*b)
    J(xin, Y33)
    xo = vo[0] + 5.08
    t, b = vpart("C1U", "C3", xo, Y33 + 6.35)
    W(vo, (xo, Y33), t); gnd(*b)
    W((xo, Y33), (xs["46"], Y33))
    J(xo, Y33)
    flag("+3V3", vo[0], Y33)
    note(xvb + 14.0, YV + 2.0, "XC6206: 3.3 V, 200 mA, for the RP2354A only (about 50 mA). Dropout 0.25 V at "
         "100 mA: a USB port sagging to 4.4 V still gives 3.3 V.", cols=34)
    xv = xs["46"] + 25.0
    tp = part("TP", "TP1", xv, YV, value="VBUS", ref_at=(xv + 1.5, YV - 3.6), val_at=(xv + 1.5, YV - 1.9), fsize=1.0)
    tp = part("TP", "TP2", xo + 10.16, Y33, value="+3V3", ref_at=(xo + 11.7, Y33 - 3.6), val_at=(xo + 11.7, Y33 - 1.9), fsize=1.0)
    J(xo + 10.16, Y33)
    if BI.LITE:
        W((xin, YV), (xv, YV))                     # the rail ends at its test point (no 5 V switch beyond)
    else:
        J(xv, YV)
    x11 = xs[dv[-1]] - 3.81
    part("TP", "TP3", x11, Y11, value="+1V1", ref_at=(x11 + 1.5, Y11 - 3.6), val_at=(x11 + 1.5, Y11 - 1.9), fsize=1.0)
    J(x11, Y11)

    # ---- crystal --------------------------------------------------------------
    yi, yo = ry("21"), ry("22")
    Xc = xL - 33.02
    yc = (yi + yo) / 2
    Y1 = part("Y12M", "Y1", Xc, yc, rot=270, ref_at=(Xc + 4.4, yc - 0.3), val_at=(Xc + 4.4, yc + 0.3))
    W(pin("21"), (Xc, yi), Y1.pin("1"))
    l, r = hpart("R1K", "R6", xL - 15.24, yo)
    W(pin("22"), r); W(l, (Xc, yo), Y1.pin("3"))
    for (yy, ref) in ((yi, "C4"), (yo, "C5")):
        l, r = hpart("C15P", ref, Xc - 7.62, yy, ref_at=(Xc - 9.0, yy - 2.6), val_at=(Xc - 5.6, yy - 2.6))
        W(r, (Xc, yy)); gnd(*l)
        J(Xc, yy)
    gnd(*Y1.pin("2"))
    note(Xc - 24.0, yo + 6.4, "ABM8-272-T3, 12 MHz, 10 pF load: the crystal Raspberry Pi specifies, with "
         "their 15 pF loads and the 1 k that limits its drive.", cols=40)

    # ---- SWD --------------------------------------------------------------------
    ysc, ysd = ry("24"), ry("25")
    J3x = 35.56
    J3 = part("JSTSH3", "J3", J3x, ysd, value="SWD", sym="Conn_SWD", ref_at=(J3x - 3.81, ysd - 6.4),
              val_at=(J3x + 4.6, ysd - 6.4))
    l, r = hpart("R100", "R7", xL - 15.24, ysc)
    W(J3.pin("1"), l); W(r, pin("24"))
    l, r = hpart("R100", "R8", xL - 27.94, ysd, ref_at=(xL - 32.2, ysd + 3.0), val_at=(xL - 26.4, ysd + 1.6))
    W(J3.pin("3"), l); W(r, pin("25"))
    gnd(*J3.pin("2")); gnd(*J3.pin("MP"))
    note(J3x - 18.0, ysd + 14.5, "Raspberry Pi debug connector (JST-SH 3-pin): the Debug Probe's 'D' "
         "cable. 100 R on the target side, at the connector (the spec: at the chip). 3.3 V logic.", cols=34)

    # ---- RUN and BOOT ------------------------------------------------------------
    yr, yb = ry("26"), ry("60")
    xtp = xL - 17.78
    S.nc(*pin("26"))
    l, r = hpart("R1K", "R10", xL - 15.24, yb)
    W(pin("60"), r)
    sw = part("BUTTON", "SW1", xL - 33.02, yb, ref_at=(xL - 38.1, yb - 3.3), val_at=(xL - 30.48, yb - 3.3))
    W(l, sw.pin("2"))
    gnd(*sw.pin("1"))
    note(xL - 98.0, yb + 4.0, "BOOT: hold it while plugging in to start the RP2354A's USB bootloader. Rarely "
         "needed: 'picotool reboot -f -u' gets there from software. RUN stays open: it has its own "
         "pull-up inside the RP2354A (datasheet table 1677), and the Debug Probe resets the chip "
         "over SWD.", cols=40)
    for n in ("56", "57", "59", "58", "55"):
        S.nc(*pin(n))
    note(xL - 52.0, ry("57") - 1.0, "The 2 MB flash is inside the RP2354A; these stay open.", cols=24)

    # ---- UART --------------------------------------------------------------------
    yrx, ytx = ry(gpin("UART_RX")), ry(gpin("UART_TX"))
    J4 = part("JSTSH3", "J4", J3x, ytx, value="UART", sym="Conn_UART", ref_at=(J3x - 3.81, ytx - 6.4),
              val_at=(J3x + 4.6, ytx - 6.4))
    l, r = hpart("R100", "R11", xL - 15.24, yrx)
    W(J4.pin("1"), l); W(r, pin(gpin("UART_RX")))
    l, r = hpart("R100", "R12", xL - 27.94, ytx, ref_at=(xL - 32.2, ytx + 3.0), val_at=(xL - 26.4, ytx + 1.6))
    W(J4.pin("3"), l); W(r, pin(gpin("UART_TX")))
    gnd(*J4.pin("2")); gnd(*J4.pin("MP"))
    note(J3x - 18.0, ytx + 14.5, "UART0 console, 115200 baud: the Debug Probe's 'U' cable. Works when USB "
         "does not.", cols=34)

    # ---- LEDs ----------------------------------------------------------------------
    for net, rref, dref, key, lab in (("LED_USB", "R13", "D1", "LED_Y", "USB yellow"),
                                        ("LED_ERR", "R14", "D3", "LED_R", "ERR red")):
        y = ry(gpin(net))
        l, r = hpart("R330", rref, xL - 15.24, y)
        W(r, pin(gpin(net)))
        d = part(key, dref, xL - 33.02, y, value=lab, ref_at=(xL - 38.1, y - 3.2), val_at=(xL - 34.3, y - 3.2))
        W(d.pin("2"), l)
        gnd(*d.pin("1"))
    note(xL - 98.0, ry(gpin("LED_USB")) + 3.0, "USB (yellow) and ERR (red) are the firmware's. Both are "
         "low-voltage colours, so a 3.3 V pin lights them through 330 R (3 mA).", cols=40)

    for name, num in (("XIN", "21"), ("SWCLK", "24"), ("SWDIO", "25"), ("QSPI_SS", "60"),
                      ("UART_RX", gpin("UART_RX")), ("UART_TX", gpin("UART_TX")),
                      ("LED_USB", gpin("LED_USB")), ("LED_ERR", gpin("LED_ERR"))):
        x, y = pin(num)
        label(x - 11.5, y, name)
    label(pin("22")[0] - 7.5, ry("22"), "XOUT")

    # ---- spare GPIOs ---------------------------------------------------------------
    for net in ("GP18", "GP26", "GP27", "GP28", "GP29"):
        S.nc(*pin(gpin(net)))

    if not BI.LITE:
        # ---- the bus side ------------------------------------------------------------------
        U2x = xR + 48.26
        xp = xR + 8.89                          # the pull resistors' column, on the MCU side
        xRs = xR + 17.78                        # the series resistors' column
        hh2 = len(SYMB.SN60_LEFT) * G / 2 + G / 2
        U2y = ry(gpin("DIO1")) + hh2 - G
        U2 = part("SN75160B", "U2", U2x, U2y, ref_at=(U2x + 1.0, U2y - hh2 - 1.0), val_at=(U2x - 7.62, U2y + hh2 + 1.2))
        hh3 = len(SYMB.SN61_LEFT) * G / 2 + G / 2
        U3y = ry(gpin("DC")) + hh3 - G
        U3 = part("SN75161B", "U3", U2x, U3y, ref_at=(U2x + 1.0, U3y - hh3 - 1.0), val_at=(U2x - 7.62, U3y + hh3 + 1.2))
        u2pin = {p[1]: p[0] for p in SYMB.SN60_LEFT if p}
        u3pin = {p[1]: p[0] for p in SYMB.SN61_LEFT if p}
        for net in PINS.RIGHT_ROWS:
            if not net or net == "BUS_PWR_EN":
                continue
            gp = gpin(net)
            y = ry(gp)
            if net.startswith("DIO"):
                dst = U2.pin(u2pin["D%d" % PINS.U2_CHANNEL[net]])
            elif net in ("PE", "TE_DATA"):
                dst = U2.pin(u2pin["PE" if net == "PE" else "TE"])
            elif net in ("DC", "TE_CTRL"):
                dst = U3.pin(u3pin["DC" if net == "DC" else "TE"])
            else:
                dst = U3.pin(u3pin[net])
            assert abs(dst[1] - y) < 0.01, (net, dst, y)
            label(xR + 0.8, y, net)
            W(pin(gp), dst)
        for k, net in enumerate(PINS.PULL_UP):
            y = ry(gpin(net))
            t, b = vpart("R10K", PINS.PULL_R[net], xp, y - 3.81, fsize=1.0)
            flag("+3V3", *t)
            J(xp, y)
        for net, ref in (("TE_DATA", "R19"), ("TE_CTRL", "R20")):
            y = ry(gpin(net))
            t, b = vpart("R10K", ref, xp + 3.81, y + 3.81, fsize=1.0)
            gnd(*b)
            J(xp + 3.81, y)
        note(xRs + 2.0, ry(gpin("TE_CTRL")) + 4.0,
             "Direction: the firmware sets TE high before it drives a line, and stops driving before it "
             "sets TE low, in one place. The transceivers' terminal outputs are short-circuit limited "
             "(15-75 mA).", cols=17)
        note(xRs + 2.0, ry(gpin("TE_DATA")) + 4.0,
             "10 k defaults. With the RP2354A in reset or blank, DC high (device) and TE low (listen): "
             "the transceivers cannot drive ATN, REN, IFC or DIO while the 5 V switch opens.", cols=17)

        # transceiver supplies: 100 n and 1 u at each VCC pin, hanging to the
        # right of the supply wire, above the chip; the rail's flag on a stub
        vcc = {}
        for U, c100, c1u in ((U2, "C22", "C23"), (U3, "C24", "C25")):
            vx, vy = U.pin("20")
            yj = vy - 7.62
            W((vx, vy), (vx, yj))
            W((vx - 2 * G, yj), (vx + 2 * G, yj))
            J(vx, yj)
            t, b = vpart("C100N", c100, vx + 2 * G, yj + 3.81, fsize=1.0)
            gnd(*b)
            t, b = vpart("C1U", c1u, vx - 2 * G, yj + 3.81, fsize=1.0, ref_at=(vx - 2 * G - 2.8, yj + 3.5),
                         val_at=(vx - 2 * G - 2.8, yj + 4.1), justify="right")
            gnd(*b)
            gnd(*U.pin("10"))
            vcc[U.ref] = (vx, yj)
        vx3, yj3 = vcc["U3"]
        yf3 = yj3 - 7.62
        W((vx3, yj3), (vx3, yf3), (vx3 + 2 * G, yf3))
        J(vx3, yf3) if False else None
        flag("+5V_GPIB", vx3 + 2 * G, yf3)

        # ---- the transceivers' 5 V switch -----------------------------------------------
        vx2, yj2 = vcc["U2"]
        Q1x, Q1y = vx2 - G, YV + 12.7
        Q1 = part("AO3401A", "Q1", Q1x, Q1y, mirror="x", ref_at=(Q1x + 5.2, Q1y - 0.4), val_at=(Q1x + 5.2, Q1y + 0.4))
        qs, qd, qg = Q1.pin("2"), Q1.pin("3"), Q1.pin("1")
        W(qs, (qs[0], YV))
        W(qd, (vx2, yj2))
        yf2 = qd[1] + 5.08
        W((vx2, yf2), (vx2 + 2 * G, yf2))
        J(vx2, yf2)
        flag("+5V_GPIB", vx2 + 2 * G, yf2)
        W((vx2, yf2 + G), (vx2 - 2 * G, yf2 + G))
        J(vx2, yf2 + G)
        pwr_flag(vx2 - 2 * G, yf2 + G)
        xg = qg[0] - 5.08
        t16, b16 = vpart("R100K", "R16", xg, YV + 3.81, fsize=1.0)
        t8, b8 = vpart("C10N", "C8", xg - 7.62, YV + 3.81, fsize=1.0, ref_at=(xg - 10.4, YV + 3.5),
                       val_at=(xg - 10.4, YV + 4.1), justify="right")
        W(b16, (xg, qg[1]), qg)
        W(b8, b16)
        J(*b16)
        J(xg, YV); J(xg - 7.62, YV)
        t17, b17 = vpart("R4K7", "R17", xg, qg[1] + 3.81, fsize=1.0)
        J(xg, qg[1])
        Q2 = part("2N7002", "Q2", xg - G, b17[1] + 7.62, ref_at=(xg + 2.8, b17[1] + 6.9), val_at=(xg + 2.8, b17[1] + 7.5))
        W(b17, Q2.pin("3"))
        gnd(*Q2.pin("2"))
        g2 = Q2.pin("1")
        xb = xR + 7.62
        W(pin(gpin("BUS_PWR_EN")), (xb, ry(gpin("BUS_PWR_EN"))), (xb, g2[1]), g2)
        label(xR + 0.8, ry(gpin("BUS_PWR_EN")), "BUS_PWR_EN")
        xpd = (xb + g2[0]) / 2
        t, b = vpart("R10K", "R15", xpd, g2[1] + 3.81, fsize=1.0)
        gnd(*b)
        J(xpd, g2[1])
        W((xin, YV), (qs[0], YV))
        # level with the supply-pin note to its left, and clear of the 3.3 V rail below
        note(xg - 69.4, YV + 2.0,
             "The transceivers get 5 V only when the firmware sets BUS_PWR_EN, after it has released every line. "
             "In reset, crashed or blank, they are off, and TI's parts do not load an unpowered bus. It also keeps "
             "5 V off the RP2354A's pins while it is unpowered: they tolerate 5 V only when powered.", cols=60)
        # the green BUS LED, lit whenever the transceivers have power, and TP4
        xl = vx2 + 30.48
        flag("+5V_GPIB", xl, YV + 2.54)
        t, b = vpart("R1K5", "R18", xl, YV + 6.35, fsize=1.0)
        W((xl, YV + 2.54), t)
        d2 = part("LED_G", "D2", xl, b[1] + 6.35, rot=90, value="BUS green", ref_at=(xl + 2.8, b[1] + 6.0),
                  val_at=(xl + 2.8, b[1] + 6.6), fsize=1.0)
        W(b, d2.pin("2"))
        gnd(*d2.pin("1"))
        xt4 = xl + 15.24
        flag("+5V_GPIB", xt4 - 5.08, YV + 7.62)
        W((xt4 - 5.08, YV + 7.62), (xt4, YV + 7.62))
        part("TP", "TP4", xt4, YV + 7.62, value="+5V_GPIB", ref_at=(xt4 + 1.5, YV + 4.0), val_at=(xt4 + 1.5, YV + 5.7),
             fsize=1.0)
        note(xl - 3.0, d2.pin("1")[1] + 5.0, "BUS (green): lit whenever the transceivers have power.", cols=26)
        xt5 = xt4 + 12.7
        part("TP", "TP5", xt5, YV + 7.62, value="GND", ref_at=(xt5 + 1.5, YV + 4.0), val_at=(xt5 + 1.5, YV + 5.7),
             fsize=1.0)
        gnd(xt5, YV + 7.62)

        # ---- the plug ------------------------------------------------------------------
        hhJ = len(SYMB.PLUG_LEFT) * G / 2 + G / 2
        J2x = U2x + 38.1
        J2y = ry(gpin("DIO1")) + hhJ - G
        J2 = part("GPIB", "J2", J2x, J2y, ref_at=(J2x - 8.89, J2y - hhJ - 1.0), val_at=(J2x - 8.89, J2y + hhJ + 1.2))
        u2b = {p[1]: p[0] for p in SYMB.SN60_RIGHT if p}
        u3b = {p[1]: p[0] for p in SYMB.SN61_RIGHT if p}
        for p in SYMB.PLUG_LEFT:
            if not p:
                continue
            num, name = p[0], p[1]
            if name.startswith("DIO"):
                src = U2.pin(u2b["B%d" % PINS.U2_CHANNEL[name]])
            elif name in u3b:
                src = U3.pin(u3b[name])
            else:
                continue
            dst = J2.pin(num)
            assert abs(src[1] - dst[1]) < 0.01, (name, src, dst)
            W(src, dst)
        _plug_grounds(J2)
        note(J2x + 10.5, J2y - hhJ, "IEEE-488 plug, hand-soldered. Contacts 1-12 run along the wide side of the D. "
             "TTL levels, low = true, 0 to 5.5 V; the drivers sink 48 mA and the terminations are inside U2 and "
             "U3. Connect only to an IEEE-488 bus.", cols=22)
        note(J2x + 10.5, ry(gpin("DIO8")) + 10.0, "U2, SN75160B, carries DIO1-8. TE high drives them onto "
             "the bus; PE high makes its drivers totem-pole, low open-collector (needed for parallel poll).", cols=22)
        note(J2x + 10.5, ry(gpin("NRFD")) - 4.0, "U3, SN75161B, carries the control lines. DC low = system "
             "controller (drives ATN, REN, IFC; listens to SRQ). TE high = talker (drives DAV, EOI); low = "
             "listener (drives NRFD, NDAC).", cols=22)
    else:
        lite_bus_side(pin, ry, xR, YV)
    # mounting holes
    for k, ref in enumerate(("H1", "H2")):
        part("HOLE", ref, 106.68 + 10.16 * k, 243.84, value="M2", ref_at=(104.6 + 10.16 * k, 240.2),
             val_at=(104.6 + 10.16 * k, 247.6), fsize=1.0)
    note(101.6, 251.46, "H1, H2: M2 holes; the two screws that close the housing pass through them.", cols=30)
    return S


def main():
    s = draw()
    touches = s.touches()
    nets = s.nets()
    over = s.overlaps()                  # before save(), which rewrites the wire list
    out = s.save(HW)
    print("schematic: %d accidental touches, %d net problems, %d overlaps -> %s"
          % (len(touches), len(nets), len(over), os.path.relpath(out, ROOT)))
    for m in (touches + nets + over)[:60]:
        print("   ", m)
    return 1 if touches or nets or over else 0


if __name__ == "__main__":
    sys.exit(main())
