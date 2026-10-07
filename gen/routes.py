"""The copper laid by plan, before the router: Raspberry Pi's regulator, the
power rings under the RP2354A, the ribbon of lines from the RP2354A to the
transceivers' terminal pins, and the transceivers' bus pins to the plug.
Everything is computed from the pads' positions on the board, so it follows
the placement.

The ribbon (see gen/placement.py's floorplan): the lines leave the RP2354A's
right side 0.4 mm apart, step up together at 45 degrees, and run east under
the transceivers' bodies 0.3 mm apart, each turning up into its pin.  They
are 0.127 mm wide: at 0.4 mm pitch a 45 degree step leaves 0.157 mm between
them (JLCPCB's 4-layer minimum is 0.09 mm).  The bus side runs 0.2 mm: U3's
lines straight down to contacts 5-9 and REN between contacts 9 and 10 into the
gap between the plug's rows; ATN and SRQ cross under on the bottom layer;
U2's B1-B4 down to contacts 4-1, B5-B8 past contact 1 into the gap and on to
contacts 16-13.
"""
import json, math, os
import pcbnew
import board_info as BI
import placement as PL
import routing as RT

HERE = os.path.dirname(os.path.abspath(__file__))
FINE, BUS = 0.127, 0.2

# the ribbon, top to bottom: net (as the RP2354A pin's label) and its height under the transceivers
RIBBON = [("REN", 4.0), ("IFC", 4.3), ("NDAC", 4.6), ("NRFD", 4.9), ("DAV", 5.2), ("EOI", 5.5),
          ("DIO4", 6.4), ("DIO3", 6.7), ("DIO2", 7.0), ("DIO1", 7.3),
          ("DIO8", 7.6), ("DIO7", 7.9), ("DIO6", 8.2), ("DIO5", 8.5)]
# the two lines that leave the RP2354A's top side: the height they turn east
# at, and how far past XJ they start their step.  They run 0.3 apart, so
# IFC steps 0.1 later than REN to keep its slant 0.4/sqrt(2) from REN's.
RIBBON_TURN = {"REN": (5.6, 0.0), "IFC": (5.9, 0.1)}
XJ = 19.1                                     # where the ribbon starts its 45 degree step
CH = 0.3                                      # chamfer at each corner


class Pads:
    """(ref, pad number) -> (x, y, net), and net -> [(ref, num)], from the board."""

    def __init__(self, board, B):
        self.xy, self.net, self.of = {}, {}, {}
        for fp in board.GetFootprints():
            for p in fp.Pads():
                key = (fp.GetReference(), p.GetNumber())
                if key in self.xy:
                    continue
                self.xy[key] = B(p.GetPosition())
                self.net[key] = p.GetNetname()
                self.of.setdefault(p.GetNetname(), []).append(key)

    def find(self, ref, net_suffix, where=None):
        """The pad of `ref` whose net ends with `net_suffix` (a label name)."""
        hits = [k for k, n in self.net.items() if k[0] == ref and (n == net_suffix or n.endswith("/" + net_suffix))]
        if where:
            hits = [k for k in hits if where(self.xy[k])]
        if len(hits) != 1:
            raise SystemExit("routes: %s %s: %d pads" % (ref, net_suffix, len(hits)))
        return hits[0]


def chamfer(pts, c=CH):
    """Cut every right-angle corner of a polyline at 45 degrees."""
    out = [pts[0]]
    for a, b, d in zip(pts, pts[1:], pts[2:]):
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = d[0] - b[0], d[1] - b[1]
        la, lb = math.hypot(ux, uy), math.hypot(vx, vy)
        if la < 1e-9 or lb < 1e-9:
            continue
        cos = (ux * vx + uy * vy) / (la * lb)
        if abs(cos) < 1e-6 and min(la, lb) > 2 * c:
            out.append((b[0] - ux / la * c, b[1] - uy / la * c))
            out.append((b[0] + vx / lb * c, b[1] + vy / lb * c))
        else:
            out.append(b)
    out.append(pts[-1])
    return out


# ---------------------------------------------------------------------------
def rpi_core(R, pads):
    """Raspberry Pi's regulator copper (gen/rpi_minimal/regulator.json) turned
    with U1, the 1.1 V and 3.3 V rings under the chip, their vias, and the
    stubs from the supply pins to the rings."""
    d = json.load(open(os.path.join(HERE, "rpi_minimal", "regulator.json")))
    # their net names to ours, through U1's pin numbers (both are the RP2350A's QFN-60)
    names = {}
    for f in d["footprints"]:
        if f["ref"] == "U1":
            for num, theirs in f["pads"].items():
                ours = pads.net.get(("U1", num))
                if ours:
                    names[theirs] = ours

    def T(p):                                   # their frame -> our board (U1 turned 180 degrees)
        return (round(PL.U1_X - p[0], 4), round(PL.U1_Y - p[1], 4))

    # their zones join pads solidly; so does our ground pour, at the regulator's
    # parts (a thermal relief there finds room for one spoke only)
    for fp in R.board.GetFootprints():
        if fp.GetReference() in ("C6", "C7", "C9", "L1", "R3"):
            for pad in fp.Pads():
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    for z in d["zones"]:
        for lname in z["layers"]:
            R.zone(names[z["net"]], pcbnew.F_Cu if lname == "F.Cu" else pcbnew.B_Cu, [T(p) for p in z["outline"]],
                   priority=z["priority"], clearance=z["clearance"], min_width=z["min_width"],
                   connect="solid" if z["pad_connection"] == 2 else "thermal")
    for t in d["tracks"]:
        L = 0 if t["layer"] == "F.Cu" else 2
        R.track(names[t["net"]], L, T(t["start"]), T(t["end"]), t["width"])
    vias = [(names[v["net"]], T(v["at"]), (v["diameter"], v["drill"])) for v in d["vias"]]
    for net, at, size in vias:
        R.via(net, *at, size=size)
    # their two ground vias 0.6 mm apart touch on the bottom layer, which is our
    # 3.3 V pour there: one pad, not two that meet at a point
    for i, (n1, a1, s1) in enumerate(vias):
        for n2, a2, s2 in vias[i + 1:]:
            if n1 == n2 and math.hypot(a1[0] - a2[0], a1[1] - a2[1]) <= (s1[0] + s2[0]) / 2 + 1e-6:
                R.track(n1, 2, a1, a2, min(s1[0], s2[0]))
    # their USB lines from pins 51 and 52 to the 27 R, past the 1.1 V vias (from RP-010328-CA)
    for pin, pts in (("52", [(0.4, -3.438), (0.4, -4.0), (-1.1, -5.5), (-1.1, -6.92)]),
                     ("51", [(0.8, -3.438), (0.775, -3.463), (0.775, -4.101), (-0.1, -4.976), (-0.1, -6.92)])):
        R.polyline(pads.net[("U1", pin)], 0, [T(p) for p in pts], 0.15)
    # the rings: 1.1 V inside (to 2.2 mm from the centre, around the ground pad), 3.3 V
    # outside it (to 2.8).  The stubs from DVDD pins 6, 23 and 39 cross the 3.3 V ring
    # and cut it into three arcs, each joined to its own IOVDD pins; the arc between
    # pins 20 and 11 has no pin that can reach outward, so it gets a via.
    cx, cy = PL.U1_X, PL.U1_Y

    def sq(r):
        return [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    R.zone("+1V1", pcbnew.F_Cu, sq(2.2), priority=3, clearance=0.15, min_width=0.2, connect="solid", item=False)
    R.zone("+3V3", pcbnew.F_Cu, sq(2.8), priority=1, clearance=0.15, min_width=0.15, connect="solid", item=False)

    def rect(net, x0, y0, x1, y1):
        R._poly_item(net, 0, [(cx + x0, cy + y0), (cx + x1, cy + y0), (cx + x1, cy + y1), (cx + x0, cy + y1)])
    a, b = 1.85, 2.2                             # (the side bars run the full height, so the
    for x0, y0, x1, y1 in ((-b, -b, b, -a), (-b, a, b, b), (-b, -b, -a, b), (a, -b, b, b)):   # router's grid joins them)
        rect("+1V1", x0, y0, x1, y1)
    a, b, h = 2.35, 2.8, 0.25                   # h: half the cut a 0.2 mm stub makes, with clearance
    u1 = {num: (x, y) for (ref, num), (x, y) in pads.xy.items() if ref == "U1"}
    c6 = u1["6"][1] - cy                         # where the stubs cross: pin 6 on the right side,
    c23 = u1["23"][0] - cx                       # pin 23 along the top, pin 39 on the left
    c39 = u1["39"][1] - cy
    # arc A: top from pin 23 to the corner, right side down to pin 6
    rect("+3V3", c23 + h, -b, b, -a); rect("+3V3", a, -b, b, c6 - h)
    # arc B: right side below pin 6, the bottom, left side below pin 39
    rect("+3V3", a, c6 + h, b, b); rect("+3V3", -b, a, b, b); rect("+3V3", -b, c39 + h, -a, b)
    # arc C: left side above pin 39, top to pin 23
    rect("+3V3", -b, -b, -a, c39 - h); rect("+3V3", -b, -b, c23 - h, -a)
    R.via("+3V3", cx + 2.5, cy - 2.5)            # arc A's way out
    # Raspberry Pi's vias from the 1.1 V ring to the bottom layer: towards the
    # regulator (their bottom-layer track from the inductor ends there), and
    # towards DVDD pin 6, where pin 6's capacitor joins.  Their two others,
    # towards pins 23 and 39, would join nothing here: the bottom layer under
    # the chip is the 3.3 V pour.
    for p in ((0.488, -2.15), (-2.15, -0.8)):
        R.via("+1V1", *T(p), size=(0.6, 0.25))
    # stubs: every supply pin straight inward, along its pad, to its ring (3.3 V
    # at 2.575 mm from the centre, the middle of its band; 1.1 V at 2.025)
    for num in ("1", "11", "20", "30", "38", "44", "45"):
        x, y = u1[num]
        R.track("+3V3", 0, (x, y), _toward(x, y, cx, cy, 2.575), 0.2)
    for num in ("6", "23", "39"):
        x, y = u1[num]
        R.track("+1V1", 0, (x, y), _toward(x, y, cx, cy, 2.025), 0.2)


def _toward(x, y, cx, cy, r):
    """The point r from the centre (square measure) straight in from a pad at
    (x, y) on one side of the square chip, along the pad.  A corner pin's stub
    stays on its pad's line too: a slanted one passes its neighbour 0.09 mm
    away."""
    dx, dy = x - cx, y - cy
    if abs(dx) > abs(dy):                       # left or right side
        return (cx + math.copysign(r, dx), y)
    return (x, cy + math.copysign(r, dy))


# ---------------------------------------------------------------------------
def ribbon(R, pads):
    above = lambda p: p[1] < PL.U_Y
    for name, yu in RIBBON:
        u1 = pads.find("U1", name)
        if BI.LITE:                             # the Lite: up into its resistor's pad 1
            dst = pads.find(lite_res(name), name)
        else:
            dest_ref = "U3" if name in ("REN", "IFC", "NDAC", "NRFD", "DAV", "EOI") else "U2"
            dst = pads.find(dest_ref, name, where=above)
        net = pads.net[u1]
        x1, y1 = pads.xy[u1]
        xd, yd = pads.xy[dst]
        if name in RIBBON_TURN:                 # from the top side: up, then east
            yt, dx = RIBBON_TURN[name]
            pts = [(x1, y1), (x1, yt), (XJ + dx, yt), (XJ + dx + (yt - yu), yu), (xd, yu), (xd, yd)]
        else:
            pts = [(x1, y1), (XJ, y1), (XJ + (y1 - yu), yu), (xd, yu), (xd, yd)]
        R.polyline(net, 0, chamfer(pts), FINE)


def bus_side(R, pads):
    """The transceivers' bus pins to the plug's contacts."""
    xy = pads.xy
    below = lambda p: p[1] > PL.U_Y

    def bus(ref, num):
        return xy[(ref, num)]

    def contact(c):
        return xy[("J2", str(c))]
    up, lo = PL.ROW_UP, PL.ROW_LO
    # U3 (SN75161B): REN 2, IFC 3, NDAC 4, NRFD 5, DAV 6, EOI 7, ATN 8, SRQ 9
    for pin, c in (("3", 9), ("4", 8), ("5", 7), ("6", 6), ("7", 5)):
        (x, y), (xc, yc) = bus("U3", pin), contact(c)
        y0 = y + 0.95 if abs(xc - x) > 1.0 else y + 1.65
        pts = [(x, y), (x, y0), (xc, y0 + abs(xc - x)), (xc, yc)] if abs(xc - x) > 0.01 else [(x, y), (xc, yc)]
        R.polyline(pads.net[("U3", pin)], 0, pts, BUS)
    # REN: between contacts 9 and 10, along the gap between the rows, into contact 17
    (x, y), (xc, yc) = bus("U3", "2"), contact(17)
    xg = (contact(9)[0] + contact(10)[0]) / 2
    yg = (up + lo) / 2 - 0.1
    pts = [(x, y), (x, y + 0.95), (xg, y + 0.95 + (x - xg)), (xg, yg - CH), (xg + CH, yg), (xc - 0.7, yg),
           (xc, yg + 0.7), (xc, yc)]
    R.polyline(pads.net[("U3", "2")], 0, pts, BUS)
    # ATN and SRQ: a via under each pin, then west on the bottom layer to contacts 11 and 10
    for pin, c, yb in (("8", 11, 13.15), ("9", 10, 13.75)):
        (x, y), (xc, yc) = bus("U3", pin), contact(c)
        net = pads.net[("U3", pin)]
        R.track(net, 0, (x, y), (x, 13.15), BUS)
        R.via(net, x, 13.15)
        pts = [(x, 13.15)] + ([(x - (yb - 13.15), yb)] if yb > 13.15 else []) + [(xc + 0.7, yb), (xc, yb + 0.7), (xc, yc)]
        R.polyline(net, 2, pts, BUS)
    # U2 (SN75160B): B1-B4 (pins 2-5) to contacts 4-1, B5-B8 (pins 6-9) to contacts 16-13
    for k, (pin, c) in enumerate((("2", 4), ("3", 3), ("4", 2), ("5", 1))):
        (x, y), (xc, yc) = bus("U2", pin), contact(c)
        yr = 12.95 + 0.35 * k
        pts = chamfer([(x, y), (x, yr), (xc, yr), (xc, yc)])
        R.polyline(pads.net[("U2", pin)], 0, pts, BUS)
    for k, (pin, c) in enumerate((("6", 16), ("7", 15), ("8", 14), ("9", 13))):
        (x, y), (xc, yc) = bus("U2", pin), contact(c)
        yr = (up + 1.0) + 0.4 + 0.35 * k
        pts = chamfer([(x, y), (x, yr), (xc, yr), (xc, yc)])
        R.polyline(pads.net[("U2", pin)], 0, pts, BUS)


def lite_res(name):
    """The Lite's 100 R in bus line `name`: R30 + its GPIO."""
    import pins as PINS
    return "R%d" % (30 + PINS.GPIO_OF[name])


# the Lite's gap between the plug's rows: REN's lane and DIO8-5's, top to bottom
LITE_GAP_REN = 17.5
LITE_GAP = {"DIO8": 16.85, "DIO7": 17.25, "DIO6": 17.65, "DIO5": 18.05}


def bus_side_lite(R, pads):
    """GPiBridge Lite: from each 100 R's outer pad, a via, and the bottom layer
    straight down to its contact.  REN crosses between contacts 9 and 10 and
    runs along the gap between the rows to contact 17; DIO5-8 pass the end of
    the upper row and come back along the gap to contacts 13-16, the lowest
    lane turning down first."""
    xy = pads.xy

    def contact(c):
        return xy[("J2", str(c))]
    contacts = {"ATN": 11, "SRQ": 10, "IFC": 9, "NDAC": 8, "NRFD": 7, "DAV": 6, "EOI": 5,
                "DIO4": 4, "DIO3": 3, "DIO2": 2, "DIO1": 1, "REN": 17, "DIO8": 16, "DIO7": 15, "DIO6": 14, "DIO5": 13}
    for name, c in contacts.items():
        ref = lite_res(name)
        x, yp = xy[(ref, "2")]
        net = pads.net[(ref, "2")]
        vy = PL.LITE_VIA_Y
        R.track(net, 0, (x, yp), (x, vy), BUS)
        R.via(net, x, vy)
        xc, yc = contact(c)
        if c <= 12:                              # straight down to its contact
            pts = [(x, vy), (xc, yc)]
        elif name == "REN":                      # through the upper row, along the gap
            yg = LITE_GAP_REN
            pts = [(x, vy), (x, yg - CH), (x + CH, yg), (xc - CH, yg), (xc, yg + CH), (xc, yc)]
        else:                                    # round the end of the upper row
            yg = LITE_GAP[name]
            pts = [(x, vy), (x, yg - CH), (x - CH, yg), (xc + CH, yg), (xc, yg + CH), (xc, yc)]
        R.polyline(net, 2, pts, BUS)


# ---------------------------------------------------------------------------
# The long lines, by plan.  The RP2354A's left side escapes through two
# staircases of vias: DC and PE rise to a band along the top edge on In2 and
# drop to vias under the transceivers' top rows; LED_USB, LED_ERR, TE_DATA
# and TE_CTRL fall to a band along the bottom edge on In2 and rise between the
# plug's pins to the transceivers' TE pins, or end at the LEDs.  SWCLK, SWDIO
# and the UART leave the top side through vias and run on In2 under the
# ribbon to the debug connectors at the right end, with ATN and SRQ above
# them.  The 5 V for the transceivers runs from the switch at the left end
# along the top edge, 0.5 mm wide, into the bottom-layer 5 V pour.  The
# router then joins each pad to its lane.
IN2 = 1
LANE = 0.15
C10_VIA = (21.45, 10.8)        # beside TP3, clear of the ribbon's lowest line (x + y >= 32.12)
VBUS_X = 7.6                   # VBUS's riser in front of the USB-C's pads
VBUS_JUMP = (10.1, 22.75)      # the bottom-layer VBUS jumper's lower via: below the In2 bottom band
V5_VIA_Y = 10.6                # the 5 V via above Q1's drain, between R17 and the escape vias
DEBUG_TURN = 51.95             # x where the first debug lane (RX) turns down: clear of U2's bus line at x 51
ESC = {          # escape vias at the RP2354A: label -> (x, y)
    "DC": (8.2, 6.8), "PE": (7.55, 7.2),
    "LED_USB": (6.9, 8.9), "LED_ERR": (7.4, 9.4), "TE_DATA": (7.9, 9.9), "TE_CTRL": (8.4, 10.4),
    "UART_RX": (12.7, 4.85), "UART_TX": (13.55, 5.55), "SWDIO": (14.1, 4.85), "SWCLK": (14.8, 5.55),
    "SRQ": (16.45, 5.35), "ATN": (17.15, 4.75),
}


def _lane_fns(R, pads):
    def net(label):
        return pads.net[pads.find("U1", label)]

    def lane(label, pts, end_via=True, width=LANE, layer=IN2):
        n = net(label)
        R.via(n, *pts[0])
        R.polyline(n, layer, chamfer(pts), width)
        if end_via:
            R.via(n, *pts[-1])
    return net, lane


def _escapes(R, pads, esc):
    """From the RP2354A's pins to their vias, on the top layer: from the left
    side west, then 45 degrees to the via; from the top side up."""
    net, _ = _lane_fns(R, pads)
    xy = pads.xy
    for label, (vx, vy) in esc.items():
        px, py = xy[pads.find("U1", label)]
        if abs(px - (PL.U1_X - 3.45)) < 0.01:       # left side
            d = vy - py
            pts = [(px, py), (vx + abs(d), py), (vx, vy)]
        else:                                     # top side
            d = vx - px
            pts = [(px, py), (px, vy + abs(d)), (vx, vy)]
        R.polyline(net(label), 0, pts, LANE)


def _xout_boot(R, pads):
    net, _ = _lane_fns(R, pads)
    xy = pads.xy
    # XOUT: up from pin 22, through the gap between the crystal's lower pads,
    # under its body and out between its left pads to the 1 k (R6); the 0.5 mm
    # gap is too tight for the router's grid
    px, py = xy[pads.find("U1", "XOUT")]
    gx = (xy[("Y1", "1")][0] + xy[("Y1", "4")][0]) / 2          # the gap's middle
    gy = (xy[("Y1", "4")][1] + xy[("Y1", "3")][1]) / 2          # between the left pads
    rx, ry = xy[("R6", "2")]
    R.polyline(net("XOUT"), 0, [(px, py), (px, 5.0), (gx, 5.0 - (px - gx)), (gx, gy), (rx + 0.6, gy),
                                (rx, gy + 0.6), (rx, ry)], LANE)
    # QSPI_SS (BOOT): from pin 60 down the corridor between the USB-side
    # capacitors and the plug's contacts 12 and 24 to the 1 k, then the button
    px, py = xy[pads.find("U1", "QSPI_SS")]
    tx, ty = xy[("R10", "2")]
    xc = (xy[("C20", "1")][0] + 0.28 + xy[("J2", "12")][0] - 0.75) / 2      # the corridor's middle
    R.polyline(net("QSPI_SS"), 0, [(px, py), (px, py + 0.9), (xc, py + 0.9 + (xc - px)), (xc, ty - 0.35 - abs(xc - tx)),
                                   (tx, ty - 0.35), (tx, ty)], LANE)
    bx, by = xy[("R10", "1")]
    sx, sy = xy[("SW1", "2")]
    R.polyline(pads.net[("R10", "1")], 0, [(bx, by), (bx, sy - 0.6), (sx, sy)], LANE)


def _debug_lanes(R, pads, esc):
    """SWCLK, SWDIO and the UART on In2 under the ribbon to the right end.  At
    the right end they turn down in turn, the lowest lane first (RX, TX, SWDIO
    0.5 mm apart; SWCLK, the top lane, runs on to its resistor), each to a via
    at its 100 R, and step up into it; nothing crosses.  Between U2 and J3 the
    SWD resistors stand upright, their connector pad on the pin's line; below
    U2 the UART ones lie in line with J4's pins."""
    net, lane = _lane_fns(R, pads)
    xy = pads.xy
    for k, (label, yl, ref, pin) in enumerate((("UART_RX", 6.8, "R11", ("J4", "1")), ("UART_TX", 6.5, "R12", ("J4", "3")),
                                               ("SWDIO", 6.2, "R8", ("J3", "3")), ("SWCLK", 5.9, "R7", ("J3", "1")))):
        x, y = esc[label]
        rx, ry = xy[(ref, "2")]
        if label == "SWCLK":                      # straight on, then down into R7 from above
            lane(label, [(x, y), (x, yl), (rx, yl)])
            R.track(net(label), 0, (rx, yl), (rx, ry), LANE)
        else:
            xv = DEBUG_TURN + 0.5 * k
            lane(label, [(x, y), (x, yl), (xv, yl), (xv, ry)])
            R.track(net(label), 0, (xv, ry), (rx, ry), LANE)
        R.track(pads.net[(ref, "1")], 0, xy[(ref, "1")], xy[pin], LANE)


def _led_anodes(R, pads):
    xy = pads.xy
    for led, res in (("D1", "R13"), ("D2", "R18"), ("D3", "R14")):
        a = next(k for k in pads.of[pads.net[(led, "2")]] if k[0] == res)
        R.track(pads.net[(led, "2")], 0, xy[(led, "2")], xy[a], LANE)


def _debug_grounds(R, pads):
    """The debug connectors' ground pins: a via toward their mounting pads,
    clear of the signal pins, and the two mounting pads on to it (under the body)."""
    xy = pads.xy
    for ref in ("J3", "J4"):
        x, y = xy[(ref, "2")]
        R.track("GND", 0, (x, y), (x + 1.45, y), 0.3)
        R.via("GND", x + 1.45, y)
        fp = R.board.FindFootprintByReference(ref)
        for mp in [pd for pd in fp.Pads() if pd.GetNumber() == "MP"]:      # two pads share the number
            mx, my = R.B(mp.GetPosition())
            d = mx - (x + 1.45)
            R.polyline("GND", 0, [(x + 1.45, y), (mx, y + math.copysign(d, my - y)), (mx, my)], 0.3)


def lanes(R, pads):
    if BI.LITE:
        return lanes_lite(R, pads)
    net, lane = _lane_fns(R, pads)
    xy = pads.xy
    u3 = lambda num: xy[("U3", num)]
    u2 = lambda num: xy[("U2", num)]
    under = 3.9                                   # vias under the transceivers' top rows
    _escapes(R, pads, ESC)
    _xout_boot(R, pads)
    # BUS_PWR_EN: west under the escapes' vias to the switch's gate
    px, py = xy[pads.find("U1", "BUS_PWR_EN")]
    gx, gy = xy[("Q2", "1")]
    R.polyline(net("BUS_PWR_EN"), 0, [(px, py), (gx, py), (gx, gy)], LANE)
    # the top band: PE above DC
    x, y = ESC["PE"]
    lane("PE", [(x, y), (x, 1.5), (u2("11")[0], 1.5), (u2("11")[0], under)])
    x, y = ESC["DC"]
    lane("DC", [(x, y), (x, 1.8), (u3("11")[0], 1.8), (u3("11")[0], under)])
    # the vias under the transceivers' top rows, up into their pins
    for ref, num in (("U3", "11"), ("U3", "12"), ("U3", "13"), ("U2", "11")):
        px, py = xy[(ref, num)]
        R.track(pads.net[(ref, num)], 0, (px, under), (px, py), LANE)
    # under the ribbon: ATN, SRQ to U3; SWCLK, SWDIO, TX, RX on to the right end
    x, y = ESC["ATN"]
    lane("ATN", [(x, y), (u3("13")[0] - (y - under), y), (u3("13")[0], under)])
    x, y = ESC["SRQ"]
    lane("SRQ", [(x, y), (u3("12")[0] - (y - under), y), (u3("12")[0], under)])
    _debug_lanes(R, pads, ESC)
    # the bottom band: TE_CTRL on top, then TE_DATA, LED_ERR, LED_USB
    gap_ctrl = (xy[("J2", "9")][0] + xy[("J2", "10")][0]) / 2      # between contacts 9 and 10 (and 21, 22)
    gap_data = (xy[("J2", "2")][0] + xy[("J2", "3")][0]) / 2       # between contacts 2 and 3 (and 14, 15)
    x, y = ESC["TE_CTRL"]
    lane("TE_CTRL", [(x, y), (x, 21.2), (gap_ctrl, 21.2), (gap_ctrl, 14.0), (24.75, 13.25), (24.75, 12.4)])
    R.track(net("TE_CTRL"), 0, (24.75, 12.4), (u3("1")[0], 12.4), LANE)
    rx, ry = xy[("R20", "1")]                    # its 10 k pull-down, at 45 degrees into the via
    R.track(net("TE_CTRL"), 0, (rx, ry), (rx + (ry - 12.4), 12.4), LANE)
    x, y = ESC["TE_DATA"]
    lane("TE_DATA", [(x, y), (x, 21.5), (gap_data, 21.5), (gap_data, 12.94), (40.0, 12.3)])
    R.track(net("TE_DATA"), 0, (40.0, 12.3), (u2("1")[0], 12.3), LANE)
    rx, ry = xy[("R19", "1")]
    R.track(net("TE_DATA"), 0, (rx, ry), (rx + (12.3 - ry), 12.3), LANE)
    # the two firmware LEDs: along the bottom band to a via over each LED's
    # resistor, and down into it; each resistor runs on into its LED's anode
    # (LED_USB, the band's lowest lane, steps down 0.5 mm first: a via on its
    # own line would touch LED_ERR's, 0.3 mm above)
    for label, yl, ref, drop in (("LED_ERR", 21.8, "R14", 0.0), ("LED_USB", 22.1, "R13", 0.5)):
        x, y = ESC[label]
        rx, ry = xy[(ref, "2")]
        pts = [(x, y), (x, yl), (rx - drop, yl)] + ([(rx, yl + drop)] if drop else [])
        lane(label, pts)
        R.track(net(label), 0, (rx, yl + drop), (rx, ry), LANE)
    _led_anodes(R, pads)
    _debug_grounds(R, pads)
    # 5 V from the switch at the left end to the bottom-layer pour on the right:
    # up from Q1's drain to a via, along the top edge on In2, down into U3's
    # 1 uF and the pour
    qx, qy = xy[("Q1", "3")]
    R.track("+5V_GPIB", 0, (qx, qy), (qx, V5_VIA_Y), 0.5)
    R.via("+5V_GPIB", qx, V5_VIA_Y)
    R.polyline("+5V_GPIB", IN2, chamfer([(qx, V5_VIA_Y), (qx, 0.9), (22.75, 0.9)], 0.5), 0.5)
    R.via("+5V_GPIB", 22.75, 0.9)
    cx, cy = xy[("C25", "1")]
    R.track("+5V_GPIB", 0, (cx, cy), (22.75, 0.9), 0.4)


# GPiBridge Lite: the escapes it keeps (DC goes to its board-ID resistor, no
# via; PE and the TE pins go nowhere).  BUS_PWR_EN, to the green LED, takes
# the staircase's first step and the two firmware LEDs the next two, so the
# three lanes run down In2 where GPiBridge's run, clear of the USB-C's shell.
ESC_LITE = {k: v for k, v in ESC.items() if k not in ("DC", "PE", "TE_DATA", "TE_CTRL")}
ESC_LITE.update({"BUS_PWR_EN": ESC["LED_USB"], "LED_USB": ESC["LED_ERR"], "LED_ERR": ESC["TE_DATA"]})
LITE_FEED_Y = 3.2                  # the vias under ATN's and SRQ's resistors
LITE_FEED_DX = -0.6                # beside the resistor: its own line runs down the bottom layer below it
# the bottom band, 0.5 mm apart so a lane passing another's via clears it
LITE_LED_BAND = (("LED_ERR", 21.2, "R14"), ("LED_USB", 21.7, "R13"), ("BUS_PWR_EN", 22.2, "R18"))


def lanes_lite(R, pads):
    net, lane = _lane_fns(R, pads)
    xy = pads.xy
    _escapes(R, pads, ESC_LITE)
    # DC: west, then 45 degrees, up into R21 (1 k to ground: the board ID)
    px, py = xy[pads.find("U1", "DC")]
    x, y = ESC["DC"]
    R.polyline(net("DC"), 0, [(px, py), (x + abs(y - py), py), (x, y), xy[("R21", "1")]], LANE)
    _xout_boot(R, pads)
    # ATN and SRQ: under the ribbon on In2 to a via under each one's resistor
    for label in ("ATN", "SRQ"):
        x, y = ESC_LITE[label]
        rx, ry = xy[(lite_res(label), "1")]
        fx = rx + LITE_FEED_DX
        lane(label, [(x, y), (fx - (y - LITE_FEED_Y), y), (fx, LITE_FEED_Y)])
        R.polyline(net(label), 0, [(fx, LITE_FEED_Y), (rx, LITE_FEED_Y + LITE_FEED_DX), (rx, ry)], LANE)
    _debug_lanes(R, pads, ESC_LITE)
    # the bottom band: LED_ERR on top, LED_USB, BUS_PWR_EN; each to a via over
    # its resistor's pad, and down into it
    for label, yl, ref in LITE_LED_BAND:
        x, y = ESC_LITE[label]
        rx, ry = xy[next(k for k in pads.of[net(label)] if k[0] == ref)]
        lane(label, [(x, y), (x, yl), (rx, yl)])
        R.track(net(label), 0, (rx, yl), (rx, ry), LANE)
    _led_anodes(R, pads)
    _debug_grounds(R, pads)


def local(R, pads):
    """The short connections, by plan: each decoupling capacitor to its pin,
    the USB-C's pads to their parts, VBUS, the 3.3 V regulator, and the
    transceivers' 5 V switch.  The router is left only the ground fan-out."""
    xy = pads.xy

    def N(ref, num):
        return pads.net[(ref, num)]

    def line(ref, num, pts, width=0.2, layer=0):
        R.polyline(N(ref, num), layer, pts, width)

    u1 = lambda num: xy[("U1", num)]
    p = lambda ref, num: xy[(ref, num)]

    # ---- the RP2354A's capacitors --------------------------------------------
    # left side: pin 38 to C17 and pin 39 to C12, over the unused pins 40-43;
    # pin 44 straight to C21; pin 45 down to C18
    (x, y), (cx, cy) = u1("38"), p("C17", "1")
    line("C17", "1", [(x, y), (cx + (cy - y), y), (cx, cy)])
    (x, y), (cx, cy) = u1("39"), p("C12", "1")
    xm = cx + 0.57                                 # 0.175 mm clear of pins 40 and 41
    line("C12", "1", [(x, y), (xm, y), (xm, cy - (xm - cx - 0.27)), (cx + 0.27, cy), (cx, cy)], 0.15)
    line("C21", "1", [p("C21", "1"), u1("44")])
    (x, y), (cx, cy) = u1("45"), p("C18", "1")
    line("C18", "1", [(x, y), (cx + (cy - y), y), (cx, cy)])
    # top side: pin 30 up to C16
    (x, y), (cx, cy) = u1("30"), p("C16", "1")
    line("C16", "1", [(x, y), (x, cy + (x - cx)), (cx, cy)])
    # below the ribbon: pin 1 along a 3.3 V line through C13, C14 and C15 (the
    # last two serve pins 11 and 20 through the ring), with vias to the bottom
    # pour between them; their ground pads on a line below, with vias too
    (x, y) = u1("1")
    xe = p("C15", "1")[0]
    line("C13", "1", [(x, y), (xe, y)], 0.25)
    yg = p("C13", "2")[1]
    line("C13", "2", [(p("C13", "2")[0], yg), (p("C10", "2")[0], yg)], 0.25)
    for a, b in (("C13", "C14"), ("C14", "C15")):
        xv = (p(a, "1")[0] + p(b, "1")[0]) / 2
        R.via("+3V3", xv, y)
        R.via("GND", xv, yg)
    # DVDD pin 6's capacitor: from Raspberry Pi's via inside the ring, east on
    # In2 under the ribbon to a via beside the +1V1 test point, then down to C10
    vx, vy = PL.U1_X + 2.15, PL.U1_Y + 0.8          # their (-2.15, -0.8), turned with U1
    tx, ty = p("TP3", "1")
    R.polyline("+1V1", IN2, [(vx, vy), (C10_VIA[0], vy)], 0.3)
    R.via("+1V1", *C10_VIA)
    R.track("+1V1", 0, C10_VIA, (tx, ty), 0.25)
    cx, cy = p("C10", "1")
    R.polyline("+1V1", 0, [C10_VIA, (cx, C10_VIA[1] + (cx - C10_VIA[0])), (cx, cy)], 0.25)
    # DVDD pin 23's capacitor (C11, above the crystal's corner): the ring's
    # top corner, by the bottom layer (as Raspberry Pi do), around arc A's via
    cx, cy = p("C11", "1")
    R.via("+1V1", 17.0, 8.0)
    R.polyline("+1V1", 2, [(17.0, 8.0), (17.0, 7.2), (cx, 7.2 - (cx - 17.0)), (cx, cy + 0.77)], 0.25)
    R.via("+1V1", cx, cy + 0.77)
    R.track("+1V1", 0, (cx, cy + 0.77), (cx, cy), 0.25)
    # USB_OTP_VDD's own capacitor beside Raspberry Pi's C12 (our C19)
    line("C20", "1", [p("C19", "1"), p("C20", "1")])
    line("C20", "2", [p("C19", "2"), p("C20", "2")])

    # ---- USB-C -------------------------------------------------------------------
    # the two D- pads join behind the row (west), the two D+ pads in front;
    # the pair then runs east 0.5 mm apart and turns up into the 27 R
    jx = p("J1", "A6")[0]                          # the pad row's centre line
    behind, front = jx - 1.045, jx + 1.005         # 0.25 mm and 0.2 mm clear of the pads' ends
    dm1, dm2 = p("J1", "B7")[1], p("J1", "A7")[1]
    dp1, dp2 = p("J1", "A6")[1], p("J1", "B6")[1]
    R.polyline(N("J1", "B7"), 0, [(jx, dm1), (behind, dm1), (behind, dm2), (jx, dm2)], 0.15)
    R.polyline(N("J1", "A6"), 0, [(jx, dp2), (front, dp2), (front, dp1)], 0.15)
    rx, ry = p("R1", "1")
    R.polyline(N("J1", "B7"), 0, chamfer([(jx, dm1), (rx, dm1), (rx, ry)]), 0.2)
    rx, ry = p("R2", "1")
    R.polyline(N("J1", "A6"), 0, chamfer([(jx, dp1), (rx, dp1), (rx, ry)]), 0.2)
    # CC1 and CC2 to their 5.1 k
    for pad, res in (("A5", "R4"), ("B5", "R5")):
        (x, y), (rx, ry) = p("J1", pad), p(res, "1")
        d = abs(y - ry)
        R.polyline(N("J1", pad), 0, [(x, y), (rx - d, y), (rx, ry)], 0.15)
    # VBUS, upper pad: out in front of the row, up to a line under Q1 (its
    # source, R16, C8), and across to C1, then on the bottom layer down to
    # the lower group (a fat line behind the row would run under the shell)
    vt, vb = p("J1", "A4"), p("J1", "A9")
    c1 = p("C1", "1")
    if BI.LITE:                                  # no 5 V switch: up to C1's line only
        R.polyline("VBUS", 0, chamfer([vt, (xv := VBUS_X, vt[1]), (xv, c1[1])]), 0.4)
    else:
        xv, yq = VBUS_X, p("Q1", "2")[1]
        R.polyline("VBUS", 0, chamfer([vt, (xv, vt[1]), (xv, yq), (p("R16", "1")[0], yq)]), 0.4)
        for ref in ("R16", "C8"):
            R.track("VBUS", 0, (p(ref, "1")[0], yq), p(ref, "1"), 0.4)
    R.track("VBUS", 0, (xv, c1[1]), (VBUS_JUMP[0], c1[1]), 0.4)
    R.via("VBUS", VBUS_JUMP[0], c1[1])
    R.track("VBUS", 2, (VBUS_JUMP[0], c1[1]), VBUS_JUMP, 0.4)
    R.via("VBUS", *VBUS_JUMP)
    # VBUS, lower pad: a line east past C2 to the regulator's input, and up to TP1
    u4 = p("U4", "3")
    R.polyline("VBUS", 0, [vb, (u4[0], vb[1]), u4], 0.4)
    R.track("VBUS", 0, (p("C2", "1")[0], vb[1]), p("C2", "1"), 0.4)
    tx, ty = p("TP1", "1")
    R.polyline("VBUS", 0, [(u4[0], vb[1]), (u4[0] + (vb[1] - ty), ty), (tx, ty)], 0.3)
    # 3.3 V out: a line from the regulator through C3 to TP2, a via to the pour
    u2 = p("U4", "2")
    tx, ty = p("TP2", "1")
    R.track("+3V3", 0, u2, (tx, u2[1]), 0.4)
    R.track("+3V3", 0, (p("C3", "1")[0], u2[1]), p("C3", "1"), 0.4)
    R.via("+3V3", (p("C3", "1")[0] + tx) / 2, u2[1] + 0.35)
    # ground: the regulator's pin and C3 on a short line
    g = p("U4", "1")
    R.polyline("GND", 0, [g, (p("C3", "2")[0] - 0.47, g[1]), p("C3", "2")], 0.4)

    if BI.LITE:
        _local_lite(R, pads)
        return
    # ---- the transceivers' 5 V switch -------------------------------------------
    # gate line: Q1's gate west to R16 and C8, R17 down onto it from Q2's drain
    g = p("Q1", "1")
    R.polyline(N("Q1", "1"), 0, [g, (p("R16", "2")[0], g[1]), p("R16", "2")], 0.2)
    R.track(N("Q1", "1"), 0, (p("C8", "2")[0], g[1]), p("C8", "2"), 0.2)
    R.track(N("Q1", "1"), 0, p("R17", "1"), g, 0.2)
    R.track(N("Q2", "3"), 0, p("Q2", "3"), p("R17", "2"), 0.2)
    # DC's 10 k pull-up sits over DC's via; its 3.3 V end takes a via
    x, y = ESC["DC"]
    line("R21", "2", [(x, y), p("R21", "2")], LANE)
    x, y = p("R21", "1")                           # west: east of it, PE climbs on In2
    R.via("+3V3", x - 0.75, y)
    R.track("+3V3", 0, (x, y), (x - 0.75, y), 0.25)
    # J1's ground pads join the top pour solidly (a relief finds room for one spoke)
    for fp in R.board.GetFootprints():
        if fp.GetReference() == "J1":
            for pad in fp.Pads():
                if pad.GetNumber() in ("A1", "A12", "B1", "B12"):
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    # the +5V test point in the bottom row, a via into the 5 V pour beside it
    x, y = p("TP4", "1")
    R.via("+5V_GPIB", x - 0.95, y)
    R.track("+5V_GPIB", 0, (x - 0.95, y), (x, y), 0.3)


def _local_lite(R, pads):
    """The Lite's own short connections: R21, the board ID, from DC down to
    ground through a via beside it (GPiBridge has it up to 3.3 V there)."""
    x, y = pads.xy[("R21", "2")]
    R.via("GND", x - 0.75, y)
    R.track("GND", 0, (x, y), (x - 0.75, y), 0.25)
    # J1's ground pads join the top pour solidly (a relief finds room for one spoke)
    for fp in R.board.GetFootprints():
        if fp.GetReference() == "J1":
            for pad in fp.Pads():
                if pad.GetNumber() in ("A1", "A12", "B1", "B12"):
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)


def supply_planes(R):
    """The bottom layer's two pours, and the router's knowledge of them: 3.3 V
    under the RP2354A, and right of it the transceivers' 5 V (on the Lite,
    ground, between the bus lines that run down it)."""
    W, H, xs = PL.BOARD["w"], PL.BOARD["h"], PL.SUPPLY_SPLIT
    left = [(0, 0), (xs - 0.2, 0), (xs - 0.2, H), (0, H)]
    right = [(xs + 0.2, 0), (W, 0), (W, H), (xs + 0.2, H)]
    m = 0.6                                      # vias this far inside a pour count as on it
    RT.PLANES["+3V3"] = [(m, m), (xs - m, m), (xs - m, H - m), (m, H - m)]
    if BI.LITE:
        # the ground pour starts past the plug's contacts 11 and 23, which the
        # split would otherwise cut through (a pad at a pour's edge gets one spoke)
        xg = PL.contact_x(11) + 1.0
        R.zone("+3V3", pcbnew.B_Cu, left, priority=0, clearance=0.2, min_width=0.2, item=False)
        R.zone("GND", pcbnew.B_Cu, [(xg, 0), (W, 0), (W, H), (xg, H)], priority=0, clearance=0.2, min_width=0.25,
               item=False)
        return
    RT.PLANES["+5V_GPIB"] = [(xs + m, m), (W - m, m), (W - m, H - m), (xs + m, H - m)]
    R.zone("+3V3", pcbnew.B_Cu, left, priority=0, clearance=0.2, min_width=0.2, item=False)
    R.zone("+5V_GPIB", pcbnew.B_Cu, right, priority=0, clearance=0.2, min_width=0.2, item=False)


# layer costs for the router: grid layer 0 = F.Cu, 1 = In2.Cu, 2 = B.Cu
TOP = {0: 1.0, 1: 3.0, 2: 6.0}             # local wiring on the top layer; the bottom is the supply pours
INNER = {0: 2.0, 1: 1.0, 2: 6.0}


def autoroute(R, pads):
    """Everything not laid by plan.  The supplies fan out to their planes
    first; then the most constrained nets (crystal, USB, the RP2354A's
    escapes to the planned vias), then the rest, short ones first."""
    def n(label):
        for name in R.nets:
            if name == label or name.endswith("/" + label):
                return name
        if BI.LITE:
            return None                           # GPiBridge's transceiver nets: not on the Lite
        raise SystemExit("autoroute: no net %s" % label)
    import time
    for net in ("+3V3",) if BI.LITE else ("+3V3", "+5V_GPIB"):
        R.fanout(net, reach=1.0, skip=("TP",))
    order = [
        # the debug connectors and their 100 R, before the long lines reach them
        ("Net-(J3-SWCLK)", 0.15, dict(layers=(0,))), ("Net-(J3-SWDIO)", 0.15, dict(layers=(0,))),
        ("Net-(J4-RX)", 0.15, dict(layers=(0,))), ("Net-(J4-TX)", 0.15, dict(layers=(0,))),
        # crystal and USB: top layer only
        (n("XIN"), 0.15, dict(layers=(0,))), (n("XOUT"), 0.15, dict(layers=(0,))),
        ("Net-(C5-Pad2)", 0.15, dict(layers=(0,))),
        (n("USB_DM"), 0.2, dict(layers=(0,))), (n("USB_DP"), 0.2, dict(layers=(0,))),
        (n("USB_D+"), 0.2, dict(layer_cost=TOP)), (n("USB_D-"), 0.2, dict(layer_cost=TOP)),
        ("Net-(J1-CC1)", 0.15, dict(layers=(0,))), ("Net-(J1-CC2)", 0.15, dict(layers=(0,))),
        # the RP2354A's escapes to the planned vias, and the lanes' far ends
        (n("DC"), 0.15, dict(layers=(0,))), (n("PE"), 0.15, dict(layers=(0,))),
        (n("BUS_PWR_EN"), 0.15, dict(layers=(0,))),
        (n("LED_USB"), 0.15, dict(layer_cost=TOP)), (n("LED_ERR"), 0.15, dict(layer_cost=TOP)),
        (n("TE_DATA"), 0.15, dict(layer_cost=TOP)), (n("TE_CTRL"), 0.15, dict(layer_cost=TOP)),
        (n("UART_RX"), 0.15, dict(layer_cost=TOP)), (n("UART_TX"), 0.15, dict(layer_cost=TOP)),
        (n("SWDIO"), 0.15, dict(layer_cost=TOP)), (n("SWCLK"), 0.15, dict(layer_cost=TOP)),
        (n("SRQ"), 0.15, dict(layers=(0,))), (n("ATN"), 0.15, dict(layers=(0,))),
        (n("QSPI_SS"), 0.15, dict(layers=(0,))), ("Net-(R10-Pad1)", 0.15, dict(layers=(0,))),
        # supplies that are routed, not poured
        ("+1V1", 0.25, dict(layer_cost={0: 1.0, 1: 3.0, 2: 1.5})), ("VBUS", 0.4, dict(layer_cost=TOP)),
        ("+5V_GPIB", 0.4, dict(layer_cost=TOP)), ("+3V3", 0.25, dict(layer_cost=TOP)),
        ("Net-(Q1-G)", 0.15, dict(layer_cost=TOP)), ("Net-(Q2-D)", 0.15, dict(layer_cost=TOP)),
        ("Net-(D1-A)", 0.15, dict(layers=(0,))), ("Net-(D2-A)", 0.15, dict(layers=(0,))),
        ("Net-(D3-A)", 0.15, dict(layers=(0,))),
    ]
    if BI.LITE:
        order = [o for o in order if o[0] and o[0] in R.nets]
    for net, w, kw in order:
        t = time.time()
        ok = R.route_net(net, w, **kw)
        dt = time.time() - t
        if not ok or dt > 5:
            print("   %-22s %s  %.1f s" % (net, "ok" if ok else "FAILED", dt))
    # anything the table forgot
    for net in sorted(R.by_net):
        if not net.startswith("<") and R.unrouted(net):
            R.route_net(net, 0.15, layer_cost=TOP)
