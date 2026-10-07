"""The silkscreen: what the board says about itself.  Called by gen/board.py.

Top side, for a person holding the board with the lid off:
  * what each connector is and which pin is which (SWD, UART, the plug's
    contact numbers), the LEDs' meanings, BOOT, and every test point's rail;
  * the chips by part number and job;
  * the designators of the chips, transistors, crystal and inductor, beside
    their parts; the passives' designators are on the fab layer only, which
    the assembly drawing prints (beside a 0402 a designator is as likely to be
    read as its neighbour's: the Raspberry Pi Pico prints none);
  * the board's name.
Bottom side, in the strip the plug's flange leaves uncovered: the identity
(name, what it is, authors, revision and date, licences).

JLCPCB prints nothing finer than 0.15 mm lines and nothing legible under
0.8 mm text, so every line and stroke here is at least 0.15 mm and every
text at least 0.8 mm high.  KiCad's stock footprints draw their silkscreen at
0.12 mm: it is widened.  The passives' own marks (two dashes beside an 0402)
are dropped: they say nothing and crowd the labels.

Placement is checked in code as it is made: no text over a pad, a via, a
hole, another text or a part's body, and nothing within 0.25 mm of the edge.
A label that cannot be placed is reported, never forced.
"""
import math
import pcbnew
import board_info as BI
import placement as PL

STROKE = 0.15            # JLCPCB's minimum line width
TEXT_H = 0.8             # JLCPCB's minimum legible text height
REF_W = 0.7              # designators a little narrow, to fit beside 0402s
EDGE = 0.2               # silkscreen to board edge
PAD_GAP = 0.15           # silkscreen to exposed copper
GAP = 0.12               # between two silkscreen items

PASSIVE_FOOTPRINTS = ("R_0402", "C_0402", "R_0603", "C_0603")

# The designators printed, and where, in order of preference: U(p), D(own),
# L(eft), R(ight) of the part.  Everything else goes to the fab layer: the
# connectors, LEDs, test points and button carry functional labels instead,
# and U2 and U3 are named with their part numbers above them.
REF_SIDES = {"U1": "RU", "U4": "LRU", "Q1": "RL", "Q2": "UR", "Y1": "RU", "L1": "DU"}


def mm(v):
    return pcbnew.FromMM(float(v))


class Silk:
    def __init__(self, board, P, B):
        self.board, self.P, self.B = board, P, B
        self.W, self.H = PL.BOARD["w"], PL.BOARD["h"]
        self.blocked = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}    # (x0, y0, x1, y1, what)
        self.placed = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
        self.problems = []

    # ---- geometry --------------------------------------------------------------
    def box(self, bb, grow=0.0):
        x0, y0 = self.B(pcbnew.VECTOR2I(bb.GetX(), bb.GetY()))
        x1, y1 = self.B(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
        return (x0 - grow, y0 - grow, x1 + grow, y1 + grow)

    @staticmethod
    def hit(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    def free(self, layer, r):
        """Why the rectangle r cannot take silkscreen on `layer`, or None."""
        if r[0] < EDGE or r[1] < EDGE or r[2] > self.W - EDGE or r[3] > self.H - EDGE:
            return "the board edge"
        for b in self.blocked[layer] + self.placed[layer]:
            if self.hit(r, b):
                return b[4]
        return None

    def obstacles(self, fps):
        """Pads, vias, holes and part bodies, on the side each is seen from."""
        top, bot = pcbnew.F_SilkS, pcbnew.B_SilkS
        for fp in fps.values():
            ref = fp.GetReference()
            back = fp.GetLayer() == pcbnew.B_Cu
            for pad in fp.Pads():
                r = self.box(pad.GetBoundingBox(), PAD_GAP)
                tht = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
                if tht or not back:
                    self.blocked[top].append(r + ("%s pad %s" % (ref, pad.GetNumber()),))
                if tht or back:
                    self.blocked[bot].append(r + ("%s pad %s" % (ref, pad.GetNumber()),))
            # the body: its fab outline (what sits on the board), else the courtyard
            fab = [it for it in fp.GraphicalItems() if it.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab)
                   and it.GetClass() == "PCB_SHAPE"]
            if not fab:                                    # a test point: its pad and ring
                fab = [it for it in fp.GraphicalItems() if it.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
                fab += list(fp.Pads())
            if not fab:
                continue
            bb = fab[0].GetBoundingBox()
            for it in fab[1:]:
                bb.Merge(it.GetBoundingBox())
            body = self.box(bb)
            if ref.startswith("H"):
                continue                                   # its hole is a pad above
            if ref == "J2":
                continue                                   # its flange is 3.5 mm below the board
            self.blocked[bot if back else top].append(body + ("%s body" % ref,))
        for t in self.board.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T:
                r = self.box(t.GetBoundingBox(), 0.05)
                self.blocked[top].append(r + ("via",))
                self.blocked[bot].append(r + ("via",))

    def keep_graphics(self, fps):
        """Footprints' own silkscreen: passives' dashes dropped, the rest
        widened to 0.15 mm and counted as placed."""
        for fp in fps.values():
            name = fp.GetFPIDAsString().split(":")[-1]
            for it in list(fp.GraphicalItems()):
                if it.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                    continue
                if it.GetClass() == "PCB_TEXT":
                    t = it
                    t.SetTextThickness(mm(STROKE))
                    self.placed[it.GetLayer()].append(self.box(t.GetBoundingBox(), GAP) + ("%s text" % fp.GetReference(),))
                    continue
                if name.startswith(PASSIVE_FOOTPRINTS):
                    fp.Remove(it)
                    continue
                if not it.IsSolidFill() and pcbnew.ToMM(it.GetWidth()) < STROKE:
                    it.SetWidth(mm(STROKE))
                self.placed[it.GetLayer()].append(self.box(it.GetBoundingBox(), GAP) + ("%s outline" % fp.GetReference(),))

    # ---- texts -------------------------------------------------------------------
    def _style(self, t, h, w=None, stroke=STROKE, bottom=False, angle=0):
        t.SetBold(False)                 # first: un-bolding resets the stroke to size/8
        t.SetItalic(False)
        t.SetTextSize(pcbnew.VECTOR2I(mm(w or h), mm(h)))
        t.SetTextThickness(mm(stroke))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetMirrored(bottom)
        t.SetTextAngleDegrees(angle)

    def _extent(self, t):
        return self.box(t.GetEffectiveTextShape().BBox())

    def label(self, text, x, y, h=TEXT_H, w=None, stroke=STROKE, bottom=False, angle=0, justify="center",
              what=None):
        """A board text centred (or left/right justified) at (x, y); placed
        only where it is free."""
        layer = pcbnew.B_SilkS if bottom else pcbnew.F_SilkS
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(text)
        t.SetLayer(layer)
        self._style(t, h, w, stroke, bottom, angle)
        if justify != "center":
            t.SetHorizJustify({"left": pcbnew.GR_TEXT_H_ALIGN_LEFT, "right": pcbnew.GR_TEXT_H_ALIGN_RIGHT}[justify])
        t.SetPosition(self.P(x, y))
        r = self._extent(t)
        why = self.free(layer, r)
        if why:
            self.problems.append("label %r at (%.2f, %.2f), extent (%.2f, %.2f)-(%.2f, %.2f): over %s"
                                 % ((text, x, y) + tuple(r) + (why,)))
            return None
        self.board.Add(t)
        self.placed[layer].append((r[0] - GAP, r[1] - GAP, r[2] + GAP, r[3] + GAP, "label %r" % text))
        return r

    def line(self, pts, bottom=False, width=STROKE):
        layer = pcbnew.B_SilkS if bottom else pcbnew.F_SilkS
        for a, b in zip(pts, pts[1:]):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(self.P(*a)); s.SetEnd(self.P(*b))
            s.SetLayer(layer); s.SetWidth(mm(width))
            r = self.box(s.GetBoundingBox())
            why = self.free(layer, r)
            if why:
                self.problems.append("line (%.2f, %.2f)-(%.2f, %.2f): over %s" % (a[0], a[1], b[0], b[1], why))
                continue
            self.board.Add(s)
            self.placed[layer].append((r[0] - GAP, r[1] - GAP, r[2] + GAP, r[3] + GAP, "line"))

    # ---- designators ---------------------------------------------------------------
    def references(self, fps):
        top = pcbnew.F_SilkS
        bodies = {}
        for ref, fp in fps.items():
            if fp.GetLayer() == pcbnew.B_Cu:
                continue
            bb = None
            for pad in fp.Pads():
                pb = pad.GetBoundingBox()
                if bb is None:
                    bb = pb
                else:
                    bb.Merge(pb)
            for it in fp.GraphicalItems():
                if it.GetLayer() == pcbnew.F_Fab and it.GetClass() == "PCB_SHAPE":
                    bb.Merge(it.GetBoundingBox()) if bb is not None else None
            bodies[ref] = self.box(bb) if bb is not None else None
        for ref in sorted(fps, key=_refkey):
            fp = fps[ref]
            t = fp.Reference()
            sides = REF_SIDES.get(ref, "fab")
            if fp.GetLayer() == pcbnew.B_Cu or sides == "fab" or bodies.get(ref) is None:
                self._to_fab(fp)
                continue
            self._style(t, TEXT_H, REF_W)
            x0, y0, x1, y1 = bodies[ref]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            done = False
            for gap in (0.2, 0.45):
                for side in sides:
                    for angle in ((0,) if side in "UD" else (0, 90)):
                        t.SetTextAngleDegrees(angle)
                        t.SetPosition(self.P(cx, cy))
                        ex = self._extent(t)
                        hw, hh = (ex[2] - ex[0]) / 2, (ex[3] - ex[1]) / 2
                        x, y = {"U": (cx, y0 - gap - hh), "D": (cx, y1 + gap + hh),
                                "L": (x0 - gap - hw, cy), "R": (x1 + gap + hw, cy)}[side]
                        t.SetPosition(self.P(x, y))
                        r = self._extent(t)
                        if self.free(top, r) or not self._nearest_is(ref, r, bodies):
                            continue
                        self.placed[top].append((r[0] - GAP, r[1] - GAP, r[2] + GAP, r[3] + GAP, "%s ref" % ref))
                        t.SetLayer(top)
                        t.SetVisible(True)
                        done = True
                        break
                    if done:
                        break
                if done:
                    break
            if not done:
                self._to_fab(fp)

    @staticmethod
    def _nearest_is(ref, r, bodies):
        """The label's nearest part body is its own: never ambiguous."""
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2

        def dist(b):
            dx = max(b[0] - cx, 0, cx - b[2])
            dy = max(b[1] - cy, 0, cy - b[3])
            return math.hypot(dx, dy)
        mine = dist(bodies[ref])
        return all(dist(b) > mine + 0.05 for k, b in bodies.items() if k != ref and b is not None)

    def _to_fab(self, fp):
        """The designator on the fab layer only, for the assembly drawing.  Most
        footprints already draw it there (a ${REFERENCE} text sized to the
        part); then the field itself is hidden, or the drawing shows it twice."""
        t = fp.Reference()
        back = fp.GetLayer() == pcbnew.B_Cu
        t.SetLayer(pcbnew.B_Fab if back else pcbnew.F_Fab)
        own = any(it.GetClass() == "PCB_TEXT" and "${REFERENCE}" in it.GetText()
                  and it.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab) for it in fp.GraphicalItems())
        if own:
            t.SetVisible(False)
            self._fab_text(fp)
            return
        self._style(t, 0.5, 0.5, 0.08, bottom=back)
        t.SetPosition(fp.GetPosition())
        t.SetVisible(True)


    def _fab_text(self, fp):
        """The footprint's own fab designator, legible in the assembly drawing
        and inside the part: Raspberry Pi's are drawn with a 0.01 mm hairline,
        and the test points' and the button's sit outside them, on top of the
        silkscreen labels."""
        body = None
        for it in list(fp.GraphicalItems()) + list(fp.Pads()):
            if it.GetClass() == "PCB_TEXT" or (it.GetClass() == "PCB_SHAPE" and it.GetLayer() not in (pcbnew.F_Fab, pcbnew.B_Fab)):
                continue
            bb = it.GetBoundingBox()
            if body is None:
                body = bb
            else:
                body.Merge(bb)
        x0, y0, x1, y1 = self.box(body)
        side = min(x1 - x0, y1 - y0)
        for it in fp.GraphicalItems():
            if it.GetClass() == "PCB_TEXT" and "${REFERENCE}" in it.GetText() and it.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab):
                h = max(0.25, min(1.0, 0.45 * side))
                it.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
                it.SetTextThickness(mm(max(0.04, 0.15 * h)))
                it.SetPosition(fp.GetPosition())
                if fp.GetReference() in FAB_OFFSET:
                    dx, dy = FAB_OFFSET[fp.GetReference()]
                    it.SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(mm(dx), mm(dy)))
                it.SetKeepUpright(True)          # Raspberry Pi's parts are turned 180 with U1


# Fab designators that cannot sit at their part's centre (board mm from it):
# J2's centre, between the plug's rows, carries "the plug goes on this side"
# on the back, so its designator moves to the D's left end, past contact 12.
FAB_OFFSET = {"J2": (-14.9, 0.0)}


def _refkey(ref):
    """Big parts first (they have the fewest places), then by letter and number."""
    order = {"U": 0, "Q": 1, "Y": 2, "L": 3, "J": 4, "D": 5, "R": 6, "C": 7}
    letters = "".join(c for c in ref if c.isalpha())
    num = int("".join(c for c in ref if c.isdigit()) or 0)
    return (order.get(letters, 9), letters, num)


# ---------------------------------------------------------------------------
def apply(board, fps, P, B):
    S = Silk(board, P, B)
    S.obstacles(fps)
    S.keep_graphics(fps)
    xy = {}
    for ref, fp in fps.items():
        for pad in fp.Pads():
            xy.setdefault((ref, pad.GetNumber()), B(pad.GetPosition()))
    p = lambda ref, num: xy[(ref, num)]
    labels(S, p)
    S.references(fps)
    for msg in S.problems:
        print("   SILK: " + msg)
    n_top = sum(1 for fp in fps.values() if fp.Reference().GetLayer() == pcbnew.F_SilkS)
    print("silk: %d labels, %d of %d designators on the silkscreen (the rest on the fab layer), %d problems"
          % (len(S.placed[pcbnew.F_SilkS]) + len(S.placed[pcbnew.B_SilkS]), n_top, len(fps), len(S.problems)))
    return S


def labels(S, p):
    """The functional labels, laid out by hand from the parts' positions."""
    # the bottom row, read through the lid: each LED's meaning and the test
    # points' rails above them (below is the board edge), BOOT beside its button
    yl = 21.55
    for led, name in (("D1", "USB"), ("D2", "BUS"), ("D3", "ERR")):
        x = (p(led, "1")[0] + p(led, "2")[0]) / 2
        S.label(name, x, yl, h=0.9)
    tps = (("TP5", "GND", -0.15),) if BI.LITE else (("TP4", "5V", 0.0), ("TP5", "GND", -0.15))
    for tp, name, dx in tps:                     # under, apart from the LEDs' names
        S.label(name, p(tp, "1")[0] + dx, 24.62)
    sx, sy = (p("SW1", "1")[0] + p("SW1", "2")[0]) / 2, p("SW1", "1")[1]
    S.label("BOOT", sx + 3.55, sy, h=0.9, angle=90)
    # the other test points
    x, y = p("TP1", "1")
    S.label("VBUS", x + 2.6, y)
    x, y = p("TP2", "1")
    S.label("3V3", x, y + 1.5)
    x, y = p("TP3", "1")
    S.label("1V1", x, y - 1.4)
    # the debug connectors (their pins: 1 at the top, as the Raspberry Pi
    # debug connector standard numbers them; the cables are keyed)
    x = (p("J3", "1")[0] + p("J3", "MP")[0]) / 2
    S.label("SWD", x, p("J3", "1")[1] - 2.85, h=1.0)
    S.label("UART", x, p("J4", "3")[1] + 2.7, h=1.0)
    # the transceivers, by part number and job, in the strip above their pins
    for ref, name in () if BI.LITE else (("U3", "SN75161B CONTROL"), ("U2", "SN75160B DATA")):
        x = (p(ref, "11")[0] + p(ref, "20")[0]) / 2
        S.label(name, x, 0.72, w=0.75)
    # the plug's contact numbers at the ends of its rows
    for c, dx in (("1", 1.32), ("13", 1.62), ("12", -1.62)):         # no room for "24", under "12"
        x, y = p("J2", c)
        S.label(c, x + dx, y)
    # the plug's name, between its rows, and which side it goes on: its pins
    # fit the holes either way up and either way round (the back shows the D)
    x = (p("J2", "12")[0] + p("J2", "10")[0]) / 2
    ymid = (p("J2", "12")[1] + p("J2", "24")[1]) / 2
    S.label("IEEE-488", x + 0.95, ymid)
    S.label("pins stick out on this side", (p("J2", "7")[0] + p("J2", "1")[0]) / 2 + 0.6, ymid)
    # the name, in the free corner by the UART connector
    # three lines between the UART label and the board's edge, 0.15 mm apart
    # ("GPiBridge" has a descender: 0.81 mm above its centre, 1.12 below)
    S.label(BI.FAMILY, 52.7, 21.6, h=1.3, stroke=0.2)
    S.label("USB to GPIB", 52.7, 23.4)
    S.label(("Lite  rev " if BI.LITE else "rev ") + BI.REV, 52.7, 24.5)
    if BI.LITE:
        lite_identity(S, p)
        x1, y1 = p("J2", "1")
        x12, y24 = p("J2", "12")[0], p("J2", "24")[1]
        S.label("the plug goes on this side", (x1 + x12) / 2, (y1 + y24) / 2, bottom=True)
        return
    # the back, in the strip the plug's flange leaves bare: who, what, when
    bottom(S, p)


def lite_identity(S, p):
    """GPiBridge Lite's bus lines run down the back, through the strip where
    GPiBridge prints its identity; the Lite prints it on top, in the band
    between the ribbon and the plug, which its missing transceivers left free."""
    x = 37.5
    S.label("%s  rev %s  %s" % (BI.TITLE, BI.REV, BI.DATE), x, 9.2, h=0.9, w=0.8)
    S.label(BI.URL, x, 10.75)                  # (both lines have descenders)
    S.label(BI.AUTHORS, x, 12.1)
    S.label("CERN-OHL-P-2.0 hardware, MIT firmware", x, 13.2)


def bottom(S, p):
    """Between U3's vias and U2's capacitors' vias, above the flange: the
    identity block, under the repository's URL; right of it, the licences.  Between the plug's rows,
    inside the D drawn by its footprint: which side the plug goes on."""
    x1, y1 = p("J2", "1")
    x12, y24 = p("J2", "12")[0], p("J2", "24")[1]
    S.label("the plug goes on this side", (x1 + x12) / 2, (y1 + y24) / 2, bottom=True)
    x = 29.0                                          # the block between the vias above and the plug below
    S.label(BI.TITLE, x, 4.7, h=1.3, stroke=0.2, bottom=True)
    if BI.URL:
        S.label(BI.URL, x, 6.7, bottom=True)          # where the design lives
    S.label(BI.AUTHORS, x, 8.05, bottom=True)
    S.label("rev %s  %s" % (BI.REV, BI.DATE), x, 9.35, bottom=True)
    x = 46.2
    S.label("CERN-OHL-P-2.0", x, 7.2, bottom=True)
    S.label("MIT firmware", x, 8.75, bottom=True)
