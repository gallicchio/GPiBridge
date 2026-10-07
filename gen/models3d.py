#!/usr/bin/env python3
"""3D models for the parts whose models KiCad's AppImage does not ship.

Each model is a short list of solids (boxes and extruded polygons) in the
footprint's own frame, in millimetres: X right, Y down (as the footprint is
drawn), Z up out of the board on the part's own side.  From that one list
this writes two files:

  <name>.wrl   coloured, for KiCad's 3D viewer and renders.  KiCad's VRML unit
               is 2.54 mm, so coordinates are divided by 2.54; every face is
               spelled out because KiCad's reader ignores VRML's primitives.
  <name>.step  the same solids as STEP, made by FreeCAD (freecadcmd), for the
               enclosure's interference check.  `kicad-cli pcb export step
               --subst-models` uses the .step in place of the .wrl.

They are honest stand-ins drawn from the datasheets' dimensions, not vendor
CAD.  Run with plain python3; it calls freecadcmd for the STEP files.
"""
import json, math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "hardware", "lib", "GPiBridge.3dshapes")

BLACK = (0.10, 0.10, 0.11)
DARK = (0.22, 0.22, 0.24)
TIN = (0.80, 0.80, 0.78)
STEEL = (0.62, 0.64, 0.67)
NICKEL = (0.72, 0.72, 0.70)
WHITE = (0.92, 0.92, 0.90)
BEIGE = (0.80, 0.74, 0.60)


def box(x0, y0, z0, x1, y1, z1, color):
    return dict(kind="prism", pts=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0=z0, z1=z1, color=color)


def prism(pts, z0, z1, color):
    return dict(kind="prism", pts=list(pts), z0=z0, z1=z1, color=color)


def disc(cx, cy, r, z0, z1, color, n=16):
    return prism([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)],
                 z0, z1, color)


def rounded_rect(cx, cy, w, h, r, n=8):
    """Polygon of a w x h rectangle with corner radius r, centred at (cx, cy)."""
    pts = []
    for (qx, qy, a0) in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                         (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------------------
def qfn60():
    """RP2354A: 7 x 7 x 0.85 mm QFN-60, 0.4 mm pitch (RP2350 datasheet, 14.1)."""
    s = [box(-3.5, -3.5, 0.02, 3.5, 3.5, 0.85, BLACK)]
    for i in range(15):
        o = -2.8 + 0.4 * i
        s.append(box(-3.5, o - 0.1, 0.0, -3.1, o + 0.1, 0.2, TIN))      # pins 1-15, left
        s.append(box(o - 0.1, 3.1, 0.0, o + 0.1, 3.5, 0.2, TIN))        # 16-30, bottom
        s.append(box(3.1, o - 0.1, 0.0, 3.5, o + 0.1, 0.2, TIN))        # 31-45, right
        s.append(box(o - 0.1, -3.5, 0.0, o + 0.1, -3.1, 0.2, TIN))      # 46-60, top
    s.append(disc(-2.6, -2.6, 0.3, 0.85, 0.86, DARK))                   # pin-1 dimple
    return "QFN-60-1EP_7x7mm_P0.4mm", s


def usbc_hro():
    """HRO TYPE-C-31-M-12 (drawing in datasheets/): shell 8.94 x 3.26 mm,
    6.77 mm long, mating face at y = +3.65 in KiCad's footprint frame (0.99 mm
    past the board edge the drawing recommends at y = +2.66)."""
    face, back = 3.65, 3.65 - 6.77
    shell = rounded_rect(0, 0, 8.94, 3.26, 1.55)
    s = []
    # the shell is a stadium in the X-Z plane extruded along Y: build it as
    # slabs along Y by sampling the outline (a prism in our frame is along Z)
    s.append(dict(kind="extrude_y", pts=[(x, z + 1.63) for x, z in shell], y0=back, y1=face, color=STEEL))
    s.append(dict(kind="extrude_y", pts=[(x, z + 1.63) for x, z in rounded_rect(0, 0, 8.34, 2.56, 1.2)],
                  y0=face - 0.01, y1=face + 0.005, color=BLACK))          # the opening
    s.append(box(-3.3, face - 0.02, 1.33, 3.3, face + 0.01, 1.93, WHITE))  # the tongue
    for x in (-4.32, 4.32):
        for y in (-3.13, 1.05):
            s.append(box(x - 0.3, y - 0.5, -1.6, x + 0.3, y + 0.5, 0.0, STEEL))  # shell legs
    for x in (-3.25, -2.45, -1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75, 2.45, 3.25):
        s.append(box(x - 0.1, -4.6, 0.0, x + 0.1, back, 0.12, TIN))       # SMD leads
    return "USB_C_Receptacle_HRO_TYPE-C-31-M-12", s


def aota():
    """Abracon AOTA-B201610S3R3-101-T: 2.0 x 1.6 x 1.0 mm, white polarity dot.
    The dot is where Raspberry Pi's footprint marks it (its F.Fab dot, pad 1)."""
    s = [box(-1.0, -0.8, 0.0, 1.0, 0.8, 1.0, DARK),
         box(-1.0, -0.8, 0.0, -0.4, 0.8, 0.05, TIN), box(0.4, -0.8, 0.0, 1.0, 0.8, 0.05, TIN),
         disc(-0.7, 0.55, 0.15, 1.0, 1.01, WHITE)]
    return "L_Abracon_AOTA-B201610", s


def gpib_plug():
    """The IEEE-488 male plug (NorComp 111-024-113L001), in the footprint's
    frame: this is the mating-face view, the plug standing on the board.
    Measured from NorComp's own 3D model (gen/footprints.py), above the seating
    plane (z = 0): the standoff plate to 0.5, the insulator's rear body to the
    flange, the flange 3.50-4.30, the D shell to the mating face at 12.80; the
    pins reach 5.50 mm through the board, 1.0 mm wide for their first 0.5."""
    sys.path.insert(0, HERE)
    import footprints as F
    fw, fh = F.FLANGE
    rw, rh = F.REAR
    pw, ph = F.PLATE
    ch = F.FLANGE_CH
    flange = [(-fw / 2 + ch, -fh / 2), (fw / 2 - ch, -fh / 2), (fw / 2, -fh / 2 + ch), (fw / 2, fh / 2 - ch),
              (fw / 2 - ch, fh / 2), (-fw / 2 + ch, fh / 2), (-fw / 2, fh / 2 - ch), (-fw / 2, -fh / 2 + ch)]
    iw, ih = F.INSERT
    z_fl = F.FLANGE_Z - F.FLANGE_T
    s = [prism(rounded_rect(0, 0, pw, ph, 2.5), 0.0, 0.5, BEIGE),                    # standoff plate
         prism(rounded_rect(0, 0, rw, rh, 3.0), 0.5, z_fl, BEIGE),                    # rear body
         prism(flange, z_fl, F.FLANGE_Z, NICKEL),
         prism(F.d_outline(), F.FLANGE_Z, F.FACE_Z, NICKEL),                           # the D shell
         box(-iw / 2, -ih / 2, F.FACE_Z, iw / 2, ih / 2, F.FACE_Z + 0.02, BEIGE)]    # the contact insert's face
    for sx in (-1, 1):
        s.append(disc(sx * F.HOLES / 2, 0, F.HOLE_D / 2, F.FLANGE_Z, F.FLANGE_Z + 0.01, BLACK))   # flange holes (drawn)
    (pa, pt), (sa, sl) = F.PIN, F.SHOULDER
    for c in range(1, 25):
        x, y = F.contact_xy(c)
        s.append(box(x - sa / 2, y - pt / 2, -sl, x + sa / 2, y + pt / 2, 0.0, TIN))           # the shoulder
        s.append(box(x - pa / 2, y - pt / 2, -F.PIN_LEN, x + pa / 2, y + pt / 2, -sl, TIN))
    return "IEEE488_Plug_NorComp_111-024-113L001", s


MODELS = [qfn60, usbc_hro, aota, gpib_plug]


# ---------------------------------------------------------------------------
# VRML
def _faces_prism(p):
    pts, z0, z1 = p["pts"], p["z0"], p["z1"]
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [list(reversed(range(n))), [i + n for i in range(n)]]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, j + n, i + n])
    return verts, faces


def _faces_extrude_y(p):
    pts, y0, y1 = p["pts"], p["y0"], p["y1"]
    n = len(pts)
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    faces = [list(range(n)), [i + n for i in reversed(range(n))]]
    for i in range(n):
        j = (i + 1) % n
        faces.append([j, i, i + n, j + n])
    return verts, faces


def wrl(solids):
    out = ["#VRML V2.0 utf8", "# GPiBridge gen/models3d.py: a stand-in drawn from the datasheet's dimensions"]
    for p in solids:
        verts, faces = (_faces_prism if p["kind"] == "prism" else _faces_extrude_y)(p)
        r, g, b = p["color"]
        pts = ", ".join("%.4f %.4f %.4f" % (x / 2.54, -y / 2.54, z / 2.54) for x, y, z in verts)
        idx = " ".join(" ".join(str(i) for i in f) + " -1" for f in faces)
        out.append("Shape { appearance Appearance { material Material { diffuseColor %.3f %.3f %.3f "
                   "specularColor 0.25 0.25 0.25 shininess 0.4 } }\n"
                   "  geometry IndexedFaceSet { solid FALSE creaseAngle 0.5\n"
                   "    coord Coordinate { point [ %s ] }\n    coordIndex [ %s ] } }" % (r, g, b, pts, idx))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# STEP, inside freecadcmd
FREECAD_SCRIPT = r'''
import json, os, Part, FreeCAD
from FreeCAD import Vector
jobs = json.load(open(os.environ["GPIBRIDGE_JOBS"]))
for path, solids in jobs.items():
    shapes = []
    for p in solids:
        if p["kind"] == "prism":
            pts = [Vector(x, -y, p["z0"]) for x, y in p["pts"]]
            d = Vector(0, 0, p["z1"] - p["z0"])
        else:
            pts = [Vector(x, -p["y0"], z) for x, z in p["pts"]]
            d = Vector(0, -(p["y1"] - p["y0"]), 0)
        w = Part.makePolygon(pts + [pts[0]])
        shapes.append(Part.Face(w).extrude(d))
    Part.makeCompound(shapes).exportStep(path)
'''


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = {}
    for fn in MODELS:
        name, solids = fn()
        with open(os.path.join(OUT, name + ".wrl"), "w") as f:
            f.write(wrl(solids))
        jobs[os.path.join(OUT, name + ".step")] = solids
    tmp = os.path.join(ROOT, "build", "models3d_jobs.json")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    json.dump(jobs, open(tmp, "w"))
    script = os.path.join(ROOT, "build", "models3d_freecad.py")
    open(script, "w").write(FREECAD_SCRIPT)
    fc = "freecadcmd"
    try:
        r = subprocess.run([fc, script], capture_output=True, text=True, timeout=600,
                           env=dict(os.environ, GPIBRIDGE_JOBS=tmp))
        ok = all(os.path.exists(p) for p in jobs)
    except FileNotFoundError:
        ok = False
    print("3D models: %d drawn (.wrl)%s" % (len(jobs), ", STEP by FreeCAD" if ok else
                                          "; FreeCAD not found, STEP copies not made"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
