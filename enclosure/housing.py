"""The housing, in FreeCAD (run by enclosure/build.py through freecadcmd).

Frame: KiCad's STEP frame with the drill origin at the board's bottom-left
corner: X right, Y up, Z up from the board's bottom face.  The plug is below
the board (Z < 0), its mating face toward the instrument.

    base   Z from the front face (where the plug's flange bears) to the board's
           top face: a front plate the board lies on, with an opening for the
           plug's rear body, and walls around the board's edge
    lid    Z from the board's top face to the cover: walls, openings, and two
           screw bosses that clamp the board onto the base

JLC3DP's MJF PA12: walls 1.2 mm (their minimum is 0.8 mm), clearances 0.15 mm
on fits that must slide, 0.3 mm where nothing must touch.
"""
import json, os
import FreeCAD as App
import Part
from FreeCAD import Vector as V

OUT = os.environ["GPIBRIDGE_OUT"]
P = json.load(open(os.path.join(OUT, "params.json")))
W, H, T = P["board"]["w"], P["board"]["h"], P["board"]["t"]

WALL = 1.2            # side walls and the lid's top
FIT = 0.15            # board to wall, all round
LIFT = 4.7            # room above the board's top face (tallest: the JST-SH, 4.32 mm; 0.38 to spare)
PLATE = 3.5           # base front plate: board bottom to the flange's back face, 3.50 in
                      # NorComp's model.  The board lies on the plate, the plug's standoff on
                      # the board and its flange on the plate's face, all at once, so the lid's
                      # screws bend nothing and pushing the plug in loads the base, not the
                      # solder joints.  (3.3 would hold the board 0.2 mm up on the plug until
                      # the screws pressed it down.)
R_OUT = P["board"]["r"] + FIT + WALL
SCREW = 8             # M2 x 8 thread-forming screws, under the head to the tip (screw_check)
PILOT = 3.0           # their pilot holes' depth in the plate, leaving 0.5 mm at the front face
CBORE = 4.3           # the lid's counterbores: an M2 pan head is up to 4.0 mm across, a cheese
                      # head 3.8; the boss under it is 4.4

# the outline, in Y-up board coordinates: the USB-C's face is flush with the
# end wall's outer face, so the left wall is exactly as thick as the overhang
X0 = P["usbc"]["face_x"]           # -1.2: outer face of the USB end wall
X1 = W + FIT + WALL
Y0 = -(FIT + WALL)
Y1 = H + FIT + WALL
Z_FRONT = -PLATE
Z_SPLIT = T                        # base and lid meet at the board's top face
Z_TOP = T + LIFT + WALL


def Y(y):
    """Board y (down from the top edge) to the STEP frame's Y (up)."""
    return H - y


def rrect(x0, y0, x1, y1, r, z0, z1):
    """A box with rounded vertical edges."""
    b = Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    if r > 0:
        edges = [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
        b = b.makeFillet(min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01), edges)
    return b


def cyl(x, y, d, z0, z1):
    return Part.makeCylinder(d / 2, z1 - z0, V(x, y, z0))


def slot(cx, cy, length, width, z0, z1, along_x=True):
    """A stadium-shaped hole (for the USB-C's shell legs)."""
    if along_x:
        return rrect(cx - length / 2, cy - width / 2, cx + length / 2, cy + width / 2, width / 2 - 0.01, z0, z1)
    return rrect(cx - width / 2, cy - length / 2, cx + width / 2, cy + length / 2, width / 2 - 0.01, z0, z1)


# ---------------------------------------------------------------------------
def base():
    outer = rrect(X0, Y0, X1, Y1, R_OUT, Z_FRONT, Z_SPLIT)
    pocket = rrect(-0.05, -FIT, W + FIT, H + FIT, P["board"]["r"] + FIT, 0.0, Z_SPLIT + 1)
    b = outer.cut(pocket)
    # the plug's rear body passes through the front plate, 0.3 mm clear all
    # round; and at the front face a 0.4 mm step, for the fillet where NorComp's
    # insulator meets the flange (in their model it flares out over the last
    # 0.1 mm, to within 0.13 mm of a plain 0.2 mm opening)
    rw, rh = P["plug"]["rear"]
    px, py = P["plug"]["x"], Y(P["plug"]["y"])
    c = 0.3
    b = b.cut(rrect(px - rw / 2 - c, py - rh / 2 - c, px + rw / 2 + c, py + rh / 2 + c, 1.0, Z_FRONT - 1, 1))
    c += 0.4
    b = b.cut(rrect(px - rw / 2 - c, py - rh / 2 - c, px + rw / 2 + c, py + rh / 2 + c, 1.0, Z_FRONT - 1, Z_FRONT + 0.4))
    # pockets under the USB-C's shell legs, which come through the board
    for x, y in P["legs"]:
        b = b.cut(slot(x, Y(y), 2.6, 1.6, -1.6, 1))
    # the USB-C overhangs the board's end by 1.2 mm, over this wall: 0.2 mm under it
    w = P["usbc"]["w"]
    yc = Y(P["usbc"]["y"])
    b = b.cut(Part.makeBox(1.4, w + 0.6, 0.5, V(X0 - 0.1, yc - w / 2 - 0.3, Z_SPLIT - 0.2)))
    # pilot holes for the M2 thread-forming screws (3 mm deep in the plate)
    for x, y in P["holes"]:
        b = b.cut(cyl(x, Y(y), 1.7, -PILOT, 1))
    return b


def lid():
    outer = rrect(X0, Y0, X1, Y1, R_OUT, Z_SPLIT, Z_TOP)
    cavity = rrect(-0.05, -FIT, W + FIT, H + FIT, P["board"]["r"] + FIT, Z_SPLIT - 1, Z_TOP - WALL)
    l = outer.cut(cavity)
    # screw bosses down to the board's top face, with clearance holes and
    # counterbores for the M2 heads
    for x, y in P["holes"]:
        l = l.fuse(cyl(x, Y(y), 4.4, Z_SPLIT, Z_TOP - 0.01))
        l = l.cut(cyl(x, Y(y), 2.4, Z_SPLIT - 1, Z_TOP + 1))
        l = l.cut(cyl(x, Y(y), CBORE, Z_TOP - WALL, Z_TOP + 1))
    # the USB-C, through the end wall: its shell plus 0.3 mm, open to the split
    w, h = P["usbc"]["w"], P["usbc"]["h"]
    yc = Y(P["usbc"]["y"])
    l = l.cut(rrect(X0 - 1, yc - w / 2 - 0.3, 0.5, yc + w / 2 + 0.3, 0.3, Z_SPLIT - 1, Z_SPLIT + h + 0.3))
    # the LEDs and BOOT
    for x, y in P["leds"]:
        l = l.cut(cyl(x, Y(y), 1.6, Z_TOP - WALL - 1, Z_TOP + 1))
    x, y = P["boot"]
    l = l.cut(cyl(x, Y(y), 1.8, Z_TOP - WALL - 1, Z_TOP + 1))
    # the debug connectors: the cable's plug goes in from the top
    for x, y in P["debug"]:
        l = l.cut(rrect(x - 2.4, Y(y) - 2.9, x + 2.6, Y(y) + 2.9, 0.5, Z_TOP - WALL - 1, Z_TOP + 1))
    return l


FONT = os.path.join(os.path.dirname(OUT), "fonts", "DejaVuSans-Bold.ttf")     # enclosure/fonts/
DEPTH = 0.5           # JLC3DP's MJF: engraved details at least 0.5 mm wide and deep


def text_faces(text, size):
    """The glyphs of `text` as faces (holes cut), and their bounding box."""
    faces = []
    for char in Part.makeWireString(text, FONT, size, 0):
        if char:                         # a glyph's outline and its holes, as one face
            faces.append(Part.makeFace(char, "Part::FaceMakerBullseye"))
    comp = Part.makeCompound(faces)
    return comp, comp.BoundBox


ENGRAVED = []                            # (x0, y0, x1, y1, text): for the overlap check


def engrave(shape, text, x, y, size, align="center", max_w=None):
    """Cut `text` 0.5 mm into the lid's top, centred (or right-aligned) on
    board point (x, y).  `size` is the font size; shrunk to fit max_w."""
    comp, bb = text_faces(text, size)
    if max_w and bb.XLength > max_w:
        comp, bb = text_faces(text, size * max_w / bb.XLength)
    dx = {"center": x - (bb.XMin + bb.XMax) / 2, "right": x - bb.XMax, "left": x - bb.XMin}[align]
    dy = Y(y) - (bb.YMin + bb.YMax) / 2
    comp.translate(V(dx, dy, Z_TOP - DEPTH))
    b = comp.BoundBox
    ENGRAVED.append((b.XMin, b.YMin, b.XMax, b.YMax, text))
    print("HOUSING engraved %-12s %.1f x %.1f mm at (%.1f, %.1f)" % (text, b.XLength, b.YLength, x, y))
    return shape.cut(comp.extrude(V(0, 0, DEPTH + 1)))


def labels(l, title, tagline):
    """The lid says what is under each opening, and which board it holds."""
    del ENGRAVED[:]
    pitch = P["leds"][1][0] - P["leds"][0][0]
    for (x, y), name in zip(P["leds"], ("USB", "BUS", "ERR")):
        l = engrave(l, name, x, y - 2.8, 2.6, max_w=pitch - 1.4)
    x, y = P["boot"]
    l = engrave(l, "BOOT", x, y - 2.8, 2.6)
    for (x, y), name in zip(P["debug"], ("SWD", "UART")):
        l = engrave(l, name, x - 2.9, y, 2.6, align="right")
    l = engrave(l, title, 25.0, 8.3, 5.0, max_w=36.0)
    l = engrave(l, tagline, 25.0, 13.3, 2.6)
    # no two labels touch, and none runs into an opening
    for i, a in enumerate(ENGRAVED):
        for b in ENGRAVED[i + 1:]:
            if a[0] < b[2] + 0.8 and b[0] < a[2] + 0.8 and a[1] < b[3] + 0.5 and b[1] < a[3] + 0.5:
                print("ERROR: engraved %r and %r touch" % (a[4], b[4]))
    return l


def front_mark(b):
    """On the base's front face, in the strip the flange leaves bare: which way
    the plug goes in.  Its rear body is symmetric, so nothing else stops it
    going in turned round, with every signal on the wrong contact.  Read from
    the front (the instrument's side), so the text is mirrored here."""
    fy = P["plug"]["y"] - P["plug"]["flange"][1] / 2         # the flange's edge nearer the board's top
    comp, bb = text_faces("D wide side this way", 2.2)
    if bb.XLength > 40:
        comp, bb = text_faces("D wide side this way", 2.2 * 40 / bb.XLength)
    comp = comp.mirror(V(0, 0, 0), V(1, 0, 0))               # read from -Z
    bb = comp.BoundBox
    yc = Y(fy - 2.6)
    comp.translate(V(P["plug"]["x"] - (bb.XMin + bb.XMax) / 2, yc - (bb.YMin + bb.YMax) / 2, Z_FRONT - 1))
    b = b.cut(comp.extrude(V(0, 0, 1 + DEPTH)))
    # and an arrow at each end, pointing at the flange
    for x in (P["plug"]["x"] - 23.0, P["plug"]["x"] + 23.0):
        y0, y1 = Y(fy - 3.6), Y(fy - 1.2)
        tri = Part.makePolygon([V(x - 1.2, y0, Z_FRONT - 1), V(x + 1.2, y0, Z_FRONT - 1), V(x, y1, Z_FRONT - 1),
                                V(x - 1.2, y0, Z_FRONT - 1)])
        b = b.cut(Part.Face(tri).extrude(V(0, 0, 1 + DEPTH)))
    return b


def check(parts, board):
    """Volumes where a housing part and the board's 3D model overlap."""
    out = []
    for name, part in parts:
        for i, solid in enumerate(board.Solids):
            if not part.BoundBox.intersect(solid.BoundBox):
                continue
            try:
                common = part.common(solid)
            except Exception as e:
                out.append("%s vs solid %d: %s" % (name, i, e))
                continue
            if common.Volume > 0.01:
                bb = common.BoundBox
                out.append("%s overlaps a board solid by %.3f mm3 at x %.1f..%.1f y %.1f..%.1f z %.2f..%.2f"
                           % (name, common.Volume, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    return out


def norcomp_check(parts):
    """The real plug, NorComp's own 3D model, where the assembly puts it: its
    flange on the base's front face, its standoff plate on the board.  The
    model is not in the repository (reference/ is not committed); without it
    this check says so and passes."""
    path = P.get("norcomp_step")
    if not path or not os.path.exists(path):
        return ["NorComp's model (reference/111-024-113L001.STEP) not found: not checked"], None
    plug = Part.Shape()
    plug.read(path)
    # their frame: Y along the plug (pins at -9.25, seating plane -3.75, flange's
    # back face -0.25, mating face 9.05), the D's wide side toward -Z.  Ours: the
    # mating face toward -Z, the wide side toward the board's top edge (+Y)
    m = App.Matrix(-1, 0, 0, P["plug"]["x"], 0, 0, -1, Y(P["plug"]["y"]), 0, -1, 0, -3.75, 0, 0, 0, 1)
    plug = plug.transformGeometry(m)
    out = []
    for name, part in parts:
        common = part.common(plug)
        if common.Volume > 0.01:
            bb = common.BoundBox
            out.append("%s overlaps NorComp's plug by %.3f mm3 at x %.1f..%.1f y %.1f..%.1f z %.2f..%.2f"
                       % (name, common.Volume, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    # how close the plug's body comes to the base's opening, below the flange
    base = dict(parts)["base"]
    body = plug.common(Part.makeBox(80, 40, 3.4, V(-10, -10, -3.45)))       # 0.05 clear of the flange
    gap = base.distToShape(body)[0] if body.Volume > 0 else -1
    return out, gap


def screw_check():
    """Where the screws end.  The head sits on the counterbore's floor and the
    thread forms only in the base's plate (the lid and board holes are clear),
    so the tip must stop inside the pilot hole, with thread enough to hold."""
    tip = (Z_TOP - WALL) - SCREW
    grip = -tip                                  # the plate's top face is z = 0
    spare = tip + PILOT
    line = ("M2 x %d screws: %.2f mm of thread in the base's plate, the tip %.2f mm above the "
            "pilot hole's bottom" % (SCREW, grip, spare))
    if spare < 0.3 or grip < 1.5:
        print("ERROR: %s" % line)
    return line


def write(name, shape):
    shape.exportStep(os.path.join(OUT, "%s.step" % name))
    mesh = shape.tessellate(0.05)
    import Mesh
    Mesh.Mesh([[mesh[0][i] for i in tri] for tri in mesh[1]]).write(os.path.join(OUT, "%s.stl" % name))
    bb = shape.BoundBox
    print("HOUSING %s: %.1f x %.1f x %.1f mm, %.2f cm3" % (name, bb.XLength, bb.YLength, bb.ZLength, shape.Volume / 1000))


b = front_mark(base())
write("gpibridge_base", b)
report = ["Housing against each board's 3D model (every part, KiCad's STEP export)", ""]
total = 0
for bd in P["boards"]:
    l = labels(lid(), bd["title"], bd["tagline"])
    write(bd["lid"], l)
    if not os.path.exists(bd["step"]):
        report.append("%s: no 3D model (%s), not checked" % (bd["title"], os.path.basename(bd["step"])))
        continue
    board = Part.Shape()
    board.read(bd["step"])
    bb = board.BoundBox
    print("HOUSING %s model: x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f"
          % (bd["title"], bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    problems = check((("base", b), (bd["lid"], l)), board)
    total += len(problems)
    report.append("%s, in gpibridge_base and %s:" % (bd["title"], bd["lid"]))
    report += ["  " + p for p in problems] or ["  no overlap: nothing on the board touches either part"]
    for p in problems:
        print("CHECK %s: %s" % (bd["title"], p))
problems, gap = norcomp_check((("base", b), ("lid", l)))
total += sum(1 for p in problems if "overlaps" in p)
report += ["", "NorComp's own model of the plug (reference/111-024-113L001.STEP), flange on the base's face:"]
report += ["  " + p for p in problems] or ["  no overlap"]
if gap is not None:
    report.append("  its body to the base's opening: %.2f mm at the closest" % gap)
    print("CHECK NorComp's plug: %s; body to opening %.2f mm" % ("; ".join(problems) or "no overlap", gap))
report += ["", screw_check()]
print("CHECK " + report[-1])
open(os.path.join(OUT, "CHECK.txt"), "w").write("\n".join(report) + "\n")
print("CHECK %d overlap(s)" % total)
