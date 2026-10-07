#!/usr/bin/env python3
"""The manufacturing release, for JLCPCB: everything to upload, in one folder.

    python3 mfg/make_release.py [--boards N] [--assembled N] [--refresh]

--boards is the number of bare boards ordered (JLCPCB's minimum, 5), and
--assembled how many of them JLCPCB fits parts to (their minimum, 2).
GPIBRIDGE_VARIANT=lite makes the Lite's release, in mfg/release-lite/ with
GPiBridgeLite_ names.

Writes mfg/release/:
    GPiBridge_gerbers.zip          Gerbers and Excellon drill, measured from the
                                   board's bottom-left corner
    GPiBridge_bom.csv              one line per LCSC code (JLCPCB's columns)
    GPiBridge_cpl.csv              placements for JLCPCB: rotations corrected
                                   (mfg/jlc_rotation.py), and each part moved to
                                   where JLCPCB's library puts its origin
                                   (mfg/footprint_check.py's datum: the USB-C)
    GPiBridge_cpl_native.csv       the same with KiCad's own rotations
    PLACEMENT_CHECKS.txt           the parts nobody has yet seen right in
                                   JLCPCB's placement preview, with their
                                   predicted corrections: look at these
    hand_solder.csv                what JLCPCB does not fit (the GPIB plug)
    GPiBridge_assembly_top.pdf,    every designator, from the fab layers
    GPiBridge_assembly_bottom.pdf
    cost_estimate.csv              stock and price per code, with the time asked
    FABRICATION_NOTES.txt          what to tick on the order form, and the total

Gates (the release stops rather than lie):
  * every SMD part has an LCSC code;
  * every code's JLCPCB description carries the schematic's value and package
    (a typing slip once ordered a 180 k resistor as a 2.2 pF capacitor);
  * the board file carries filled zones (one shipped once with none);
  * DRC is clean (tools/pcb_check.py).
It runs mfg/footprint_check.py too (FOOTPRINT_CHECK.txt): does each ordered
part fit its copper?

Reads hardware/GPiBridge.kicad_pcb, hardware/checks/netlist.net (LCSC codes
from the schematic) and gen/parts.py, or the Lite's.
"""
import collections, csv, datetime, json, math, os, re, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import kienv, jlc_api, jlc_rotation
import board_info as BI
import placement as PL
from sexp import parse, kids, kid, val

NAME = BI.NAME
PCB = BI.PCB
NETLIST = BI.NETLIST
OUT = BI.RELEASE
GERBER_LAYERS = ("F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts")
NOT_PARTS = ("TP", "H")                        # bare pads and holes: nothing to place
# JLCPCB's own price for the order, read off Jason's cart: (date, PCBs, assembly), to
# keep the estimate below honest.  Both 5 boards with 2 assembled, 4 layers, ENIG.
JLC_QUOTE = {"GPiBridge": ("2026-10-06", 24.80, 60.56), "GPiBridgeLite": ("2026-10-06", 25.85, 40.18)}
HAND = {"J2": "the IEEE-488 plug: JLCPCB holds none (NorComp's is C5470282, pre-order only), and it goes "
              "through the housing's base before it is soldered"}


def run(args):
    return kienv.run_cli(args)


# ---------------------------------------------------------------------------
def components():
    """Every part, from the board (where and which way) and the netlist (its
    LCSC code), classed smt / hand / none."""
    doc = parse(open(NETLIST, encoding="utf-8").read())[0]
    code, value = {}, {}
    for c in kids(kid(doc, "components"), "comp"):
        ref = val(kid(c, "ref"))
        value[ref] = val(kid(c, "value"))
        fl = kid(c, "fields")
        for f in kids(fl, "field") if fl else []:
            if val(kid(f, "name")) == "LCSC" and len(f) > 2:
                code[ref] = val(f, 2)
    os.makedirs(BI.SCRATCH, exist_ok=True)
    pos = os.path.join(BI.SCRATCH, "pos.csv")
    run(["pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "--use-drill-file-origin", "-o", pos, PCB])
    rows = []
    for r in csv.DictReader(open(pos, encoding="utf-8")):
        ref = r["Ref"]
        if ref.startswith(NOT_PARTS) and re.match(r"^(TP|H)\d+$", ref):
            cls = "none"
        elif ref in HAND:
            cls = "hand"
        elif not code.get(ref):
            cls = "nocode"
        else:
            cls = "smt"
        rows.append(dict(ref=ref, value=value.get(ref, r["Val"]), fp=r["Package"], lcsc=code.get(ref, ""),
                         x=float(r["PosX"]), y=float(r["PosY"]), rot=float(r["Rot"]) % 360.0,
                         side=r["Side"], cls=cls))
    rows.sort(key=lambda r: (re.sub(r"\d+", "", r["ref"]), int(re.sub(r"\D", "", r["ref"]) or 0)))
    return rows


def write_bom(rows):
    smt = [r for r in rows if r["cls"] == "smt"]
    by = collections.defaultdict(list)
    for r in smt:
        by[r["lcsc"]].append(r)
    with open(os.path.join(OUT, NAME + "_bom.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for c, group in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            values = list(dict.fromkeys(g["value"] for g in group))      # J3 "SWD" and J4 "UART": one part
            w.writerow(["/".join(values), ",".join(g["ref"] for g in group), group[0]["fp"], c])
    with open(os.path.join(OUT, "hand_solder.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Value", "Footprint", "Why"])
        for r in rows:
            if r["cls"] == "hand":
                w.writerow([r["ref"], r["value"], r["fp"], HAND[r["ref"]]])
    return smt, by


def datum_shift(r, fits):
    """How far to move one placement in the JLCPCB CPL (x right, y up, mm).

    JLCPCB puts THEIR library part's origin at the CPL's position.  Where that
    is not KiCad's origin, the part lands off its pads by the difference:
    every USB-C so far, 1.3-1.6 mm towards its pad row, hanging off the board
    in the preview until moved by hand.  mfg/footprint_check.py fits their
    land pattern onto ours and finds where their origin sits in our footprint
    (dx, dy); here that point is carried onto the board.  Only past
    DATUM_OK, and only when the fit is good, so fitting noise moves nothing."""
    import footprint_check as FC
    fit = fits.get((r["lcsc"], r["side"] == "bottom"))
    if not fit or math.hypot(fit["dx"], fit["dy"]) <= FC.DATUM_OK or fit["worst"] > FC.LAND_OK:
        return 0.0, 0.0
    if r["side"] != "top":
        raise SystemExit("FAILED: %s has a datum offset on the bottom side, which this does not handle" % r["ref"])
    a = math.radians(r["rot"])                   # KiCad: counter-clockwise, in a y-down world
    sx = fit["dx"] * math.cos(a) + fit["dy"] * math.sin(a)
    sy = -fit["dx"] * math.sin(a) + fit["dy"] * math.cos(a)
    return round(sx, 3), round(-sy, 3)           # the CPL's y points up


def write_cpl(smt, fits):
    unchecked = collections.OrderedDict()           # LCSC code -> its placements, never seen in a preview
    moved = []                                      # (row, dx, dy): placements moved to JLCPCB's origin
    for name, corrected in ((NAME + "_cpl.csv", True), (NAME + "_cpl_native.csv", False)):
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for r in smt:
                rot = jlc_rotation.cpl_rotation(r["rot"], r["side"], r["fp"], r["lcsc"]) if corrected else r["rot"]
                x, y = r["x"], r["y"]
                if corrected:
                    if not jlc_rotation.checked(r["fp"], r["lcsc"]):
                        unchecked.setdefault(r["lcsc"], []).append(r)
                    dx, dy = datum_shift(r, fits)
                    if dx or dy:
                        moved.append((r, dx, dy))
                        x, y = x + dx, y + dy
                w.writerow([r["ref"], "%.3fmm" % x, "%.3fmm" % y, r["side"].capitalize(), "%g" % rot])
    return unchecked, moved


def placement_checks(rows, unchecked, fits, moved):
    """What to look at in JLCPCB's 'Confirm parts placement' preview, part by part.
    `fits` is mfg/footprint_check.py's FITS: the turn that laid JLCPCB's drawing
    of each part on our footprint, by pin number, printed as a cross-check."""
    L = ["%s rev %s: PLACEMENT CHECKS for JLCPCB's preview" % (NAME, BI.REV), ""]
    if moved:
        L += ["MOVED in %s_cpl.csv to where JLCPCB's library puts the part's origin (their" % NAME,
              "drawing's zero is not KiCad's; FOOTPRINT_CHECK.txt's 'datum').  In the preview each",
              "should sit squarely on its pads.  If one sits off them by about the same distance",
              "the other way, their library has changed: say so, and it goes into the code.", ""]
        for r, dx, dy in moved:
            L.append("  %-6s %-10s %-44s moved (%+.3f, %+.3f) mm (x right, y up)"
                     % (r["ref"], r["lcsc"], r["fp"][:44], dx, dy))
        L.append("")
    L += [
         "The CPL's rotations are KiCad's plus mfg/jlc_rotation.py's corrections.  Any part",
         "listed below has not yet been seen right in a preview: its correction is PREDICTED",
         "from JLCPCB's own drawing of the part, by pin number or by polarity mark",
         "(jlc_rotation.py says how; the method has been right on every top-side part read",
         "so far, GPiBridge's eleven included).  In the preview, check each one's pin 1 or",
         "polarity mark (JLCPCB's dot) against the board, write down any part that is wrong",
         "and by how much, and put what you saw into jlc_rotation.py.", "",
         "Not yet seen right in a preview:"]
    look = {
        "RP2350A_QFN-60_7x7mm_P0.4mm_RPi": "pin 1 at the bottom-right corner (the chip is turned 180), by the silk dot",
        "SOIC-20W_7.5x12.8mm_P1.27mm": "pin 1 bottom left, by the silk triangle; U2 and U3 face the same way",
        "SOT-23": "pin 1 by the silk triangle",
        "SOT-23-3": "pin 1 by the silk triangle",
        "LED_0805_2012Metric": "cathode (pad 1) to the LEFT, inside the silk bracket",
        "L_Abracon_AOTA-B201610_RPi": "the white dot on the RIGHT pad (pad 1, +1V1), by the silk dot, as on "
                                      "Raspberry Pi's own boards",
        "JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical": "the opening faces up; pin 1 at the top, by the silk step",
    }
    for code, group in unchecked.items():
        fp = group[0]["fp"]
        corr, conf, why = jlc_rotation.correction(fp, code)
        L.append("  %-8s %-12s %-10s %s" % (", ".join(g["ref"] for g in group),
                                          "/".join(dict.fromkeys(g["value"] for g in group)), code, fp))
        L.append("      correction %d (%s)%s" % (corr, conf, ": " + why if why else ""))
        fit = fits.get((code, False))
        if fit:
            turn = "as drawn" if fit["deg"] == 0 else ("turned 180" if fit["deg"] == 180 else
                                                       "turned %d clockwise" % fit["deg"])
            by_pins = (360 - fit["deg"]) % 360
            L.append("      JLCPCB's drawing lies on ours %s (by pin number, %d pads, worst %.2f mm): %s"
                     % (turn, fit["n"], fit["worst"],
                        "agrees" if by_pins == corr else "would say %d, see above" % by_pins))
        if fp in look:
            L.append("      look for: %s" % look[fp])
    if not unchecked:
        L.append("  (none: every polarized part's rotation has been read in a preview)")
    read = [r["ref"] for r in rows if r["cls"] == "smt" and r["fp"] not in jlc_rotation.ROTATION_NA
            and jlc_rotation.checked(r["fp"], r["lcsc"])]
    L += ["", "Read right in a preview already: " + " ".join(sorted(read, key=lambda x: (re.sub(r"\d+", "", x),
                                                                                       int(re.sub(r"\D", "", x) or 0)))),
          "No orientation to get wrong (two pads, or symmetric): " + ", ".join(
              sorted({r["fp"] for r in rows if r["cls"] == "smt" and r["fp"] in jlc_rotation.ROTATION_NA}))]
    open(os.path.join(OUT, "PLACEMENT_CHECKS.txt"), "w").write("\n".join(L) + "\n")
    return L


def export_gerbers():
    gerb = os.path.join(OUT, "gerbers")
    if os.path.isdir(gerb):
        shutil.rmtree(gerb)
    os.makedirs(gerb)
    run(["pcb", "export", "gerbers", "-o", gerb, "--layers", GERBER_LAYERS, "--no-protel-ext",
         "--subtract-soldermask", "--use-drill-file-origin", PCB])
    run(["pcb", "export", "drill", "-o", gerb + os.sep, "--format", "excellon", "--drill-origin", "plot",
         "--excellon-units", "mm", "--excellon-zeros-format", "decimal", "--excellon-separate-th",
         "--generate-map", "--map-format", "gerberx2", PCB])
    zpath = os.path.join(OUT, NAME + "_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(gerb)):
            z.write(os.path.join(gerb, fn), fn)
    for side, layers, mirror in (("top", "F.Fab,F.Silkscreen,Edge.Cuts", False),
                                 ("bottom", "B.Fab,B.Silkscreen,Edge.Cuts", True)):
        p = os.path.join(OUT, "%s_assembly_%s.pdf" % (NAME, side))
        run(["pcb", "export", "pdf", "-o", p, "--layers", layers, "--mode-single", "--exclude-value"]
            + (["--mirror"] if mirror else []) + [PCB])
    return zpath, sorted(os.listdir(gerb))


# ---------------------------------------------------------------------------
PKG = {"R_0402_1005Metric": "0402", "C_0402_1005Metric": "0402", "C_0603_1608Metric": "0603",
       "R_0402_RPi": "0402", "C_0402_RPi": "0402", "C_0402_RPi_wide": "0402", "LED_0805_2012Metric": "0805"}
UNIT = {"p": ["pF"], "n": ["nF"], "u": ["uF", "µF"], "r": ["Ω"], "k": ["kΩ"], "m": ["MΩ"],
        "uh": ["uH", "µH"]}


def code_value_check(smt, refresh):
    """Every code's JLCPCB description must carry the schematic's value and
    package.  Returns the offenders, and the parts that could not be asked."""
    seen, bad, unasked = set(), [], []
    for r in smt:
        key = (r["lcsc"], r["value"], r["fp"])
        if key in seen:
            continue
        seen.add(key)
        try:
            p, ts = jlc_api.by_code(r["lcsc"], refresh=refresh)
        except Exception as e:
            unasked.append("%s (%s): %s" % (r["lcsc"], r["value"], e))
            continue
        if not p:
            bad.append("%s (%s): JLCPCB does not know it" % (r["lcsc"], r["value"]))
            continue
        desc = " ".join(str(p.get(k) or "") for k in ("describe", "componentModelEn", "componentSpecificationEn",
                                                     "componentTypeEn", "erpComponentName")).lower()
        want = PKG.get(r["fp"])
        if want and want not in desc:
            bad.append("%s (%s %s): JLCPCB says %s" % (r["lcsc"], r["value"], want, desc[:80]))
            continue
        v = r["value"].lower().replace("µ", "u")
        m = re.match(r"^([\d.]+)\s*(p|n|u|k|m|uh)?(\b|$)", v)
        if r["fp"].startswith(("R_", "C_")) and m:
            num, u = m.group(1), (m.group(2) or "r")
            units = UNIT["uh" if u == "uh" else u] if not r["fp"].startswith("C_") or u != "r" else ["F"]
            if r["fp"].startswith("C_"):
                units = {"p": ["pF"], "n": ["nF"], "u": ["uF", "µF"]}.get(u, ["F"])
            if not any((num + sep + un).lower() in desc for un in units for sep in ("", " ")):
                bad.append("%s (%s): JLCPCB says %s" % (r["lcsc"], r["value"], desc[:80]))
    return bad, unasked


def cost(smt, boards, refresh):
    """Parts for `boards` assembled boards, at JLCPCB's live prices."""
    cnt = collections.Counter(r["lcsc"] for r in smt)
    lines, parts, ext, thin = [], 0.0, [], []
    for c, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        try:
            p, ts = jlc_api.by_code(c, refresh=refresh)
        except Exception as e:
            lines.append([c, n, "?", "", "", "", "query failed: %s" % e])
            continue
        if not p:
            lines.append([c, n, "?", "", "", "", "not found"])
            continue
        need = n * boards
        lt = jlc_api.library_type(p)
        stock = int(p.get("stockCount") or 0)
        price = jlc_api.unit_price(p, max(need, 1))
        if lt not in ("Basic", "Preferred"):
            ext.append(c)
        parts += price * need
        if stock < max(need * 10, 100):
            thin.append((c, p.get("componentModelEn", ""), stock, need))
        lines.append([c, n, lt, stock, "%.4f" % price, ts, p.get("componentModelEn", "")])
    return lines, parts, ext, thin


def pad_counts():
    """Solder joints per part, (SMD pads, through-hole pads): JLCPCB charges assembly
    by the joint, and through-hole joints as hand work, with a fee of their own."""
    doc = parse(open(PCB, encoding="utf-8").read())[0]
    out = {}
    for fp in kids(doc, "footprint"):
        ref = next((val(p, 2) for p in kids(fp, "property") if val(p) == "Reference"), None)
        pads = kids(fp, "pad")
        smd = {val(p, 1) for p in pads if val(p, 2) == "smd"}
        # a plated hole numbered like an SMD pad is a via in that pad (the
        # RP2354A's exposed pad has nine), not a lead to solder
        out[ref] = (sum(1 for p in pads if val(p, 2) == "smd"),
                    sum(1 for p in pads if val(p, 2) == "thru_hole" and val(p, 1) not in smd))
    return out


def footprint_check(refresh):
    """Does each ordered part fit its copper?  JLCPCB's own land patterns
    (from EasyEDA) against the board; a part wanting a hole the board lacks
    stops the release."""
    import footprint_check as FC
    try:
        nbad, text = FC.report(os.path.join(OUT, NAME + "_bom.csv"), refresh, False)
    except Exception as e:
        return "not run: %s" % e, {}
    open(os.path.join(OUT, "FOOTPRINT_CHECK.txt"), "w").write("\n".join(text) + "\n")
    hard = [l.strip() for l in text if l.startswith("       HOLE")]       # a problem line, not the legend
    if hard:
        raise SystemExit("FAILED: a part wants a hole the board does not have:\n  " + "\n  ".join(hard))
    return ("no part wants a hole; %d note(s) to read"
            % sum(1 for l in text if l.startswith(("       land", "       datum", "       PADS"))), FC.FITS)


def drc_clean():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pcb_check.py")], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout.strip().splitlines() or ["?"])[-1]


def filled_zones():
    return open(PCB, encoding="utf-8").read().count("(filled_polygon")


def main(argv):
    boards = int(argv[argv.index("--boards") + 1]) if "--boards" in argv else 5           # bare boards
    assembled = int(argv[argv.index("--assembled") + 1]) if "--assembled" in argv else 2   # of them, fitted
    refresh = "--refresh" in argv
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    nf = filled_zones()
    if not nf:
        raise SystemExit("FAILED: the board file has no filled zones (run gen/board.py)")
    ok, drc = drc_clean()
    if not ok:
        raise SystemExit("FAILED: DRC is not clean: %s (tools/pcb_check.py)" % drc)
    rows = components()
    nocode = [r["ref"] for r in rows if r["cls"] == "nocode"]
    if nocode:
        raise SystemExit("FAILED: SMD parts without an LCSC code: %s" % ", ".join(nocode))
    smt, by = write_bom(rows)
    bad, unasked = code_value_check(smt, refresh)
    if bad:
        raise SystemExit("FAILED: LCSC codes whose JLCPCB description does not match the schematic:\n  "
                         + "\n  ".join(bad))
    fp_verdict, fits = footprint_check(refresh)          # before the CPL: it says where JLCPCB's origins are
    unchecked, moved = write_cpl(smt, fits)
    zpath, gfiles = export_gerbers()
    checks = placement_checks(rows, unchecked, fits, moved)
    lines, parts, ext, thin = cost(smt, assembled, refresh)
    with open(os.path.join(OUT, "cost_estimate.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["LCSC", "per board", "library", "stock", "unit USD @ %d boards" % assembled, "asked", "part"])
        w.writerows(lines)
    # JLCPCB's 2026 list prices for a small 4-layer board with economic PCBA (estimates,
    # labelled as such): 5 boards of 4 layers about $8, $8 assembly setup, $1.5 stencil,
    # $3 per Extended part, about 0.17 cents a joint.  Parts and joints are paid for
    # the assembled boards only; JLCPCB rounds some parts up to their reel minimums.
    pcb_cost = (8.0 if boards <= 5 else 8.0 + 1.2 * (boards - 5)) + 15.0     # + ENIG
    pads = pad_counts()
    n_joints = sum(pads.get(r["ref"], (2, 0))[0] for r in smt)
    n_tht = sum(pads.get(r["ref"], (2, 0))[1] for r in smt)       # the USB-C's soldered shell legs
    # through-hole joints are hand work: about $3.58 an order and 1.7 cents a joint (Icepi's order)
    setup = 8.0 + 1.5 + 3.0 * len(ext) + (3.58 if n_tht else 0.0)
    per_board = 0.0017 * n_joints + 0.017 * n_tht
    total = pcb_cost + setup + per_board * assembled + parts
    N = []
    N.append("%s rev %s: FABRICATION NOTES (written %s; design date %s)" % (NAME, BI.REV, datetime.date.today().isoformat(), BI.DATE))
    N.append("")
    N.append("BOARD (upload %s_gerbers.zip)" % NAME)
    N.append("  %.1f x %.1f mm, 4 layers, 1.6 mm, stackup JLC04161H-7628 (impedance control not needed)." % (PL.BOARD["w"], PL.BOARD["h"]))
    N.append("  Surface finish: ENIG (the RP2354A is a 0.4 mm pitch QFN-60).  Mask green, silkscreen white, both sides.")
    N.append("  Smallest track and gap 0.127 mm (the ribbon from the RP2354A); vias 0.45/0.25 mm, and Raspberry Pi's 0.6/0.25.")
    N.append("  'Remove order number': yes (there is no room for it).  Via covering: tented.")
    N.append("  Files: %s" % ", ".join(gfiles))
    N.append("")
    N.append("ORDER: %d boards, %d of them assembled (JLCPCB's minimums: 5 boards, 2 assembled)." % (boards, assembled))
    N.append("")
    N.append("ASSEMBLY (JLCPCB economic PCBA, top side only)")
    N.append("  Upload %s_bom.csv and %s_cpl.csv: %d placements, %d BOM lines, %d Extended (%s)."
             % (NAME, NAME, len(smt), len(by), len(ext), ", ".join(ext) or "none"))
    N.append("  %s_cpl_native.csv has KiCad's own rotations and positions, for comparison." % NAME)
    if moved:
        N.append("  Moved in the CPL to JLCPCB's own origin for the part, so it lands on its pads: %s."
                 % ", ".join("%s by (%+.3f, %+.3f) mm" % (r["ref"], dx, dy) for r, dx, dy in moved))
    if unchecked:
        N.append("  In the placement preview, check the parts in PLACEMENT_CHECKS.txt: %d placements of %d part numbers"
                 % (sum(len(g) for g in unchecked.values()), len(unchecked)))
        N.append("  whose rotation is predicted, not yet seen right.")
    else:
        N.append("  Every polarized part's rotation has been read right in a preview (PLACEMENT_CHECKS.txt).")
    N.append("  Not fitted by JLCPCB (hand_solder.csv): J2, the IEEE-488 plug (NorComp 111-024-113L001 or any 24-pin male,")
    N.append("  DIP solder, 2.16 mm pitch).  Solder it last, from the top, with the board in the housing's lower half.")
    tps = sorted((k for k in pads if k and re.match(r"^TP\d+$", k)), key=lambda k: int(k[2:]))
    N.append("  Test points %s are bare pads; H1, H2 are M2 holes (no hardware)." % ", ".join(tps))
    N.append("")
    N.append("COST ESTIMATE for %d boards, %d assembled (JLCPCB list prices as of 2026; parts from their live API):"
             % (boards, assembled))
    N.append("  PCBs, 4-layer ENIG, %d               ~$%.0f  (about $15 less with lead-free HASL)" % (boards, pcb_cost))
    N.append("  assembly setup, stencil, Extended%s ~$%.0f" % (", THT" if n_tht else "    ", setup))
    N.append("  assembly, %d joints a board%s x %d   ~$%.0f" % (n_joints, " (+%d THT)" % n_tht if n_tht else "",
                                                             assembled, per_board * assembled))
    N.append("  parts for %d boards                   $%.2f" % (assembled, parts))
    N.append("  TOTAL before shipping and duty       ~$%.0f  (~$%.0f an assembled board; the other %d bare boards"
             % (total, total / assembled, boards - assembled))
    N.append("  are spares, for parts by hand)")
    if NAME in JLC_QUOTE and boards == 5 and assembled == 2:
        d, q_pcb, q_asm = JLC_QUOTE[NAME]
        N.append("  JLCPCB's own quote (the cart, %s): $%.2f PCBs + $%.2f assembly = $%.2f; this model is"
                 % (d, q_pcb, q_asm, q_pcb + q_asm))
        N.append("  $%.1f off on the PCBs and $%.1f on assembly." % (q_pcb - pcb_cost, q_asm - (setup + per_board * assembled + parts)))
    N.append("  (US import: JLCPCB collects duty under DDP; budget 35-90% of the goods' value, plus shipping.)")
    # what the adapter needs beyond JLCPCB's order (prices looked up 2026-10-06)
    N.append("  Not in that order, per adapter: the IEEE-488 plug (NorComp 111-024-113L001, Digi-Key $4.22 each),")
    N.append("  the two housing parts (JLC3DP MJF PA12, about 7.5 g at $0.275/g: about $3 with their minimums),")
    N.append("  two M2 x 10 thread-forming screws.  A finished adapter, of these first %d: about $%.0f; in a run of"
             % (assembled, total / assembled + 4.22 + 3 + 0.2))
    N.append("  5 assembled, about $%.0f." % ((total - parts - per_board * assembled) / 5 + parts / assembled
                                            + per_board + 4.22 + 3 + 0.2))
    if thin:
        N.append("")
        N.append("THIN STOCK (under 10x what %d boards need, or under 100): %s" % (assembled, "; ".join("%s %s stock %d need %d" % t for t in thin)))
    if unasked:
        N.append("")
        N.append("NOT CHECKED (no answer from JLCPCB): " + "; ".join(unasked))
    N.append("")
    N.append("Checks passed: DRC clean (%s); %d filled zone polygons in the file; every SMD part coded;" % (drc, nf))
    N.append("every code's JLCPCB description matches its value and package.")
    N.append("Land patterns: FOOTPRINT_CHECK.txt (mfg/footprint_check.py: %s)." % fp_verdict)
    open(os.path.join(OUT, "FABRICATION_NOTES.txt"), "w").write("\n".join(N) + "\n")
    print("\n".join(N))
    print("\n".join(checks[checks.index("", 2) + 1:]))
    print("release in", os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
