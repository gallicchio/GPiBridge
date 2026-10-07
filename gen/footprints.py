"""Footprints drawn for GPiBridge.

IEEE488_Plug_24P_P2.16mm_DIP_Solder
    The 24-contact IEEE-488 male plug, DIP-solder type (NorComp
    111-024-113L001; its drawing and 3D model, from Digi-Key, are in the
    untracked reference/): two rows of twelve pins, 2.16 mm pitch, rows 4.29 mm
    apart, 1.00 mm holes.  Pads are 1.5 x 2.0 mm ovals, as on UsbGpib V2, which
    many people have built.

    Pads are numbered by IEEE-488 CONTACT number, not by solder-cup order.

    The plug sits under the board, so the footprint goes on the back (B.Cu)
    and this library drawing is the view of the plug's mating face.  Seen
    that way, contact 1 is at the upper left, contacts 1-12 run along the wide
    side of the D, and 13-24 along the narrow side (the receptacle in IEEE 488.1
    is the mirror image: contact 1 at the upper right).  Placed on the back,
    KiCad mirrors it, so seen from the top of the board contact 1 is at the
    right end of the row nearer the D's wide side, which is how UsbGpib V2's
    proven board has it (tools/check_plug.py compares the two).

    The pins form a symmetric grid, so the plug can be soldered in turned
    round by 180 degrees, with every signal on the wrong contact.  The D is
    drawn on the back silkscreen and the fab layer, and the top silkscreen
    marks contacts 1, 12 and 13 (24 is under 12; there is no room for its
    label).  Nothing stops it mechanically: HANDBOOK.md step 5 is the check, a
    meter on contact 24 after two pins are tacked.

    Dimensions: the pin pattern from NorComp's drawing (rev 15, 2025: the
    recommended layout, 2.16 mm pitch, rows 4.29 mm apart, 1.00 mm holes); the
    body from NorComp's 3D model of the part (111-024-113L001.STEP, 2020,
    sliced in FreeCAD on 2026-10-06; it is not redistributed here).  Above the
    seating plane, where the standoff plate (30.40 x 11.00 mm, 0.5 mm thick)
    touches the board: the insulator's rear body (32.70 x 14.30 mm) to 3.50 mm,
    the steel flange 3.50-4.30 mm, the D shell to the mating face at 12.80 mm.
    The courtyard is the standoff plate; the rear body and the flange are on
    the fab layer.  Flush, tented vias may lie under the rear body; no
    through-hole lead may.

    The pins are flat, 0.6 x 0.3 mm, but 1.0 mm wide for the first 0.5 mm
    below the seating plane: that shoulder grips the 1.00 mm hole, so the plug
    is pressed in until its standoff plate touches the board (HANDBOOK.md).
    They reach 5.00 +/- 0.38 mm below the seating plane by the rev 15 drawing,
    5.50 in the 3D model; the model's 5.50 is drawn, the longer.
"""
import uuid

PITCH = 2.16          # contact pitch
ROW = 4.29            # row spacing (+/- 0.25)
DRILL = 1.00          # NorComp's recommended layout, and UsbGpib V2's
PAD = (1.5, 2.0)      # UsbGpib V2's pads
FLANGE = (54.70, 15.30)   # A (+/- 0.38) and the flange's height (+/- 0.38)
FLANGE_CH = 5.94          # its ends: 45 degree chamfers, flat only 3.4 mm across the middle (STEP)
HOLES, HOLE_D = 46.70, 3.20   # B (+/- 0.25): the flange's holes, unused (drawing rev 15)
# the D shell's outer surface (STEP, sliced 5 mm above the flange): half its
# width at heights y across it, from the wide side (contacts 1-12, y < 0) to
# the narrow side.  37.10 x 13.00 mm over all; the drawing's C, 36.20, is its
# inside.  The flanks run straight from y = -1 to y = 4, at about 15 degrees.
D_HALF = [(-6.5, 15.33), (-6.25, 16.32), (-6.0, 16.81), (-5.5, 17.46), (-5.0, 17.89), (-4.5, 18.18),
          (-4.0, 18.38), (-3.5, 18.50), (-3.0, 18.55), (-2.5, 18.53), (-2.0, 18.44), (-1.0, 18.17),
          (4.0, 16.83), (4.5, 16.63), (5.0, 16.33), (5.5, 15.91), (6.0, 15.26), (6.25, 14.76), (6.5, 13.77)]
INSERT = (28.0, 4.0)      # the contact insert inside the D
# below the flange (STEP):
REAR = (32.70, 14.30)     # the insulator's rear body, 0.5-3.5 mm above the seating plane; corners r 3
PLATE = (30.40, 11.00)    # the standoff plate on the seating plane, 0.5 mm thick; corners r 2.5
FACE_Z, FLANGE_Z = 12.80, 4.30    # mating face and flange (its face side) above the seating plane
FLANGE_T = 0.80           # flange thickness: its back face is 3.50 mm above the seating plane
PIN = (0.6, 0.3)          # the pins' section (along the row, across it)
SHOULDER = (1.0, 0.5)     # the pins' width and length just below the seating plane
PIN_LEN = 5.50            # pin tips below the seating plane (STEP; drawing rev 15: 5.00 +/- 0.38)


def d_outline():
    """The D shell's outline (footprint frame), clockwise from the wide side."""
    right = [(hw, y) for y, hw in D_HALF]
    return right + [(-x, y) for x, y in reversed(right)]


MODELS = ["IEEE488_Plug_NorComp_111-024-113L001.wrl"]


def contact_xy(c):
    """Pad centre of IEEE-488 contact c (1-24) in the footprint's own frame."""
    k = c if c <= 12 else c - 12
    x = (k - 6.5) * PITCH
    y = -ROW / 2 if c <= 12 else ROW / 2
    return round(x, 4), round(y, 4)


def _u(*a):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "gpibridge-fp:" + ":".join(map(str, a))))


def _line(x0, y0, x1, y1, layer, w):
    return ('\t(fp_line (start %.4f %.4f) (end %.4f %.4f) (stroke (width %.3f) (type solid)) (layer "%s") (uuid "%s"))'
            % (x0, y0, x1, y1, w, layer, _u("l", x0, y0, x1, y1, layer)))


def _poly(pts, layer, w):
    out = []
    for (a, b) in zip(pts, pts[1:] + pts[:1]):
        out.append(_line(a[0], a[1], b[0], b[1], layer, w))
    return out


def _circle(x, y, r, layer, w):
    return ('\t(fp_circle (center %.4f %.4f) (end %.4f %.4f) (stroke (width %.3f) (type solid)) (fill no) (layer "%s") (uuid "%s"))'
            % (x, y, x + r, y, w, layer, _u("c", x, y, r, layer)))


def _text(kind, s, x, y, layer, size=1.0, hide=False, w=0.15, justify=None):
    j = " (justify %s)" % justify if justify else ""
    h = " (hide yes)" if hide else ""
    if kind in ("Reference", "Value"):
        return ('\t(property "%s" "%s" (at %.3f %.3f 0) (layer "%s")%s (uuid "%s") (effects (font (size %.2f %.2f) (thickness %.2f))%s))'
                % (kind, s, x, y, layer, h, _u("p", kind), size, size, w, j))
    return ('\t(fp_text user "%s" (at %.3f %.3f 0) (layer "%s") (uuid "%s") (effects (font (size %.2f %.2f) (thickness %.2f))%s))'
            % (s, x, y, layer, _u("t", s, x, y), size, size, w, j))


def gpib_plug():
    name = "IEEE488_Plug_24P_P2.16mm_DIP_Solder"
    fw, fh = FLANGE
    sh = D_HALF[-1][0] - D_HALF[0][0]
    out = ['(footprint "%s"' % name,
           '\t(version 20241229)', '\t(generator "gpibridge_gen")', '\t(generator_version "10.0")',
           '\t(layer "F.Cu")',
           '\t(descr "IEEE-488 (GPIB) 24-contact male plug, DIP solder, 2.16 mm pitch, rows 4.29 mm apart '
           '(NorComp 111-024-113L001). Pads numbered by IEEE-488 contact number. Mount on the back: this is '
           'the view of the mating face.")',
           '\t(tags "IEEE-488 GPIB micro ribbon plug")',
           _text("Reference", "REF**", 0, -fh / 2 - 1.2, "F.SilkS"),
           _text("Value", name, 0, fh / 2 + 1.2, "F.Fab"),
           '\t(attr through_hole)']
    # flange outline (fab): ends chamfered at 45 degrees, as NorComp's model has them
    ch = FLANGE_CH
    flange = [(-fw / 2 + ch, -fh / 2), (fw / 2 - ch, -fh / 2), (fw / 2, -fh / 2 + ch), (fw / 2, fh / 2 - ch),
              (fw / 2 - ch, fh / 2), (-fw / 2 + ch, fh / 2), (-fw / 2, fh / 2 - ch), (-fw / 2, -fh / 2 + ch)]
    out += _poly(flange, "F.Fab", 0.10)
    for sx in (-1, 1):
        out.append(_circle(sx * HOLES / 2, 0, HOLE_D / 2, "F.Fab", 0.10))
    # the D: wide side toward contacts 1-12 (y < 0 here)
    d = d_outline()
    out += _poly(d, "F.Fab", 0.10)
    out += _poly(d, "F.SilkS", 0.15)
    rw, rh = REAR
    out += _poly([(-rw / 2, -rh / 2), (rw / 2, -rh / 2), (rw / 2, rh / 2), (-rw / 2, rh / 2)], "F.Fab", 0.10)
    out.append(_text("user", "1", contact_xy(1)[0], -sh / 2 + 1.25, "F.SilkS", 0.8, w=0.15))
    out.append(_text("user", "12", contact_xy(12)[0], -sh / 2 + 1.25, "F.SilkS", 0.8, w=0.15))
    out.append(_text("user", "13", contact_xy(13)[0], sh / 2 - 1.25, "F.SilkS", 0.8, w=0.15))
    out.append(_text("user", "24", contact_xy(24)[0], sh / 2 - 1.25, "F.SilkS", 0.8, w=0.15))
    out.append(_text("user", "${REFERENCE}", 0, 0, "F.Fab", 1.0))
    c = 0.25
    pw, ph = PLATE
    out += _poly([(-pw / 2 - c, -ph / 2 - c), (pw / 2 + c, -ph / 2 - c), (pw / 2 + c, ph / 2 + c), (-pw / 2 - c, ph / 2 + c)],
                 "F.CrtYd", 0.05)
    for cn in range(1, 25):
        x, y = contact_xy(cn)
        shape = "roundrect" if cn == 1 else "oval"
        rr = " (roundrect_rratio 0.15)" if cn == 1 else ""
        out.append('\t(pad "%d" thru_hole %s (at %.4f %.4f) (size %.2f %.2f) (drill %.2f) (layers "*.Cu" "*.Mask")%s'
                   ' (remove_unused_layers no) (uuid "%s"))' % (cn, shape, x, y, PAD[0], PAD[1], DRILL, rr, _u("pad", cn)))
    out.append('\t(model "${KIPRJMOD}/lib/GPiBridge.3dshapes/%s" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'
               % MODELS[0])
    out.append(')')
    return name, "\n".join(out) + "\n"


def generated():
    out = {}
    for fn in (gpib_plug,):
        name, text = fn()
        out[name] = text
    return out
