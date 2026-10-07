#!/usr/bin/env python3
"""Make hardware/lib/: every symbol, footprint and 3D model the board uses,
so the project opens and builds on a machine whose KiCad has no libraries.

    hardware/lib/GPiBridge.kicad_sym     KiCad's symbols (flattened) + ours
    hardware/lib/GPiBridge.pretty/       KiCad's footprints, Raspberry Pi's
                                         (gen/rpi_minimal), and the IEEE-488 plug
    hardware/lib/GPiBridge.3dshapes/     KiCad's STEP models + ours (gen/models3d.py)
    hardware/sym-lib-table, fp-lib-table

KiCad's own libraries are read from the KiCad install (tools/kienv.py).  They
are CC-BY-SA 4.0 with an exception for designs that use them (see
hardware/lib/README.md).
"""
import os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
import kienv, kisch
from sexp import parse, head, kids, kid, val, ser
import symbols
from parts import PARTS, LIB

HW = os.path.join(ROOT, "hardware")
LIBDIR = os.path.join(HW, "lib")
PRETTY = os.path.join(LIBDIR, LIB + ".pretty")
SHAPES = os.path.join(LIBDIR, LIB + ".3dshapes")
MODEL_PATH = "${KIPRJMOD}/lib/" + LIB + ".3dshapes/"

# symbol name in our library -> KiCad's stock lib_id
STOCK_SYMBOLS = {
    "R": "Device:R", "C": "Device:C", "L": "Device:L", "LED": "Device:LED",
    "Crystal_GND24": "Device:Crystal_GND24",
    "SW_Push": "Switch:SW_Push", "USB_C_Receptacle_USB2.0_16P": "Connector:USB_C_Receptacle_USB2.0_16P",
    "XC6206P332MR": "Regulator_Linear:XC6206PxxxMR", "AO3401A": "Transistor_FET:AO3401A",
    "2N7002": "Transistor_FET:2N7002", "TestPoint": "Connector:TestPoint",
    "MountingHole": "Mechanical:MountingHole", "PWR_FLAG": "power:PWR_FLAG",
}

# footprint name in our library -> (KiCad library, name), and the 3D model it uses
STOCK_FOOTPRINTS = {
    "R_0402_1005Metric": ("Resistor_SMD", None), "C_0402_1005Metric": ("Capacitor_SMD", None),
    "R_0603_1608Metric": ("Resistor_SMD", None), "C_0603_1608Metric": ("Capacitor_SMD", None),
    "SOT-23": ("Package_TO_SOT_SMD", None), "SOT-23-3": ("Package_TO_SOT_SMD", None),
    "SOIC-20W_7.5x12.8mm_P1.27mm": ("Package_SO", None),
    "Crystal_SMD_3225-4Pin_3.2x2.5mm": ("Crystal", None),
    "LED_0805_2012Metric": ("LED_SMD", None),
    "SW_SPST_TS-1088-xR020": ("Button_Switch_SMD", None),
    "JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical": ("Connector_JST", None),
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": ("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12.wrl"),
    "TestPoint_Pad_D1.0mm": ("TestPoint", ""), "MountingHole_2.2mm_M2": ("MountingHole", ""),
}

# Raspberry Pi's footprints (gen/rpi_minimal/rpi.pretty) -> our name, 3D model
RPI_FOOTPRINTS = {
    "rpi_rp2350a_vias": ("RP2350A_QFN-60_7x7mm_P0.4mm_RPi", "QFN-60-1EP_7x7mm_P0.4mm.wrl", None),
    "abracon_aota-b201610s3r3-101-t": ("L_Abracon_AOTA-B201610_RPi", "L_Abracon_AOTA-B201610.wrl", None),
    "generic_capc1005x50_wide": ("C_0402_RPi_wide", "C_0402_1005Metric.step", "Capacitor_SMD"),
    "generic_capc1005x50": ("C_0402_RPi", "C_0402_1005Metric.step", "Capacitor_SMD"),
    "generic_resc1005x35": ("R_0402_RPi", "R_0402_1005Metric.step", "Resistor_SMD"),
}

# The HRO drawing's recommended layout puts the board edge 5.79 mm in front of
# the upper shell tab (y = -3.13), i.e. at y = +2.66; the mating face overhangs
# it by about 1 mm (learned on the Lorenz board).  JLCPCB pulls silkscreen
# back 0.2 mm from a routed edge, so the outline stops 0.45 mm short of it.
USBC_EDGE_Y = -3.13 + 5.79
USBC_SILK_LIMIT = USBC_EDGE_Y - 0.45


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# symbols
def build_symbols(share):
    entries = []
    for name, stock_id in sorted(STOCK_SYMBOLS.items()):
        node = kisch.SYMS.stock(stock_id, os.path.join(share, "symbols"))
        node = _rename_symbol(node, stock_id.split(":")[1], name)
        if name == "XC6206P332MR":
            _set_prop(node, "Value", "XC6206P332MR")
        entries.append((name, node))
    for name, fn in sorted(symbols.CUSTOM.items()):
        text, _ = fn()
        entries.append((name, parse(text)[0]))
    for net, down in sorted(symbols.RAILS.items()):
        lib_id = kisch.power_lib_id(net)
        kisch.make_power(lib_id, net, down=down)
        node, _ = kisch.SYMS.get(lib_id)
        entries.append((lib_id.split(":", 1)[1], node))
    for name, node in entries:
        _set_prop(node, "Footprint", "")
    write(os.path.join(LIBDIR, LIB + ".kicad_sym"), kisch.library_text(entries))
    return len(entries)


def _rename_symbol(node, old, new):
    node = list(node)
    node[1] = ("str", new)
    out = []
    for c in node:
        if isinstance(c, list) and head(c) == "symbol":
            c = list(c)
            c[1] = ("str", val(c).replace(old, new, 1))
        out.append(c)
    return out


def _set_prop(node, name, value):
    for c in node:
        if isinstance(c, list) and head(c) == "property" and val(c) == name:
            c[2] = ("str", value)


# ---------------------------------------------------------------------------
# footprints
def _fp_name(node, name):
    node[1] = ("str", name)


def _set_model(node, model):
    """Point the footprint's 3D model at our library (or drop it)."""
    rest = [c for c in node if not (isinstance(c, list) and head(c) == "model")]
    node[:] = rest
    if model:
        node.append([("atom", "model"), ("str", MODEL_PATH + model),
                     [("atom", "offset"), [("atom", "xyz"), ("atom", "0"), ("atom", "0"), ("atom", "0")]],
                     [("atom", "scale"), [("atom", "xyz"), ("atom", "1"), ("atom", "1"), ("atom", "1")]],
                     [("atom", "rotate"), [("atom", "xyz"), ("atom", "0"), ("atom", "0"), ("atom", "0")]]])


def _stock_model(node):
    m = kid(node, "model")
    if not m:
        return None
    return os.path.basename(val(m))


def _trim_usbc_silk(node):
    keep = []
    for c in node:
        if isinstance(c, list) and head(c) == "fp_line" and val(kid(c, "layer")) in ("F.SilkS", "F.Silkscreen"):
            s, e = kid(c, "start"), kid(c, "end")
            ys = [float(val(s, 2)), float(val(e, 2))]
            if min(ys) >= USBC_SILK_LIMIT:
                continue
            for p in (s, e):
                if float(val(p, 2)) > USBC_SILK_LIMIT:
                    p[2] = ("atom", "%.2f" % USBC_SILK_LIMIT)
            if abs(float(val(s, 1)) - float(val(e, 1))) + abs(float(val(s, 2)) - float(val(e, 2))) < 0.3:
                continue
        keep.append(c)
    node[:] = keep


RPI_DESCR = "From Raspberry Pi's RP2350A Minimal design (MIT licence), so their regulator layout can be copied exactly"


def _clean_rpi(node):
    """Raspberry Pi's footprints carry their parts database's fields; keep the
    geometry, drop the rest, and say where it came from.  The provenance goes
    in the library description (descr), not the Description field: KiCad
    checks that field against the schematic symbol's."""
    keep = []
    for c in node:
        if isinstance(c, list) and head(c) == "property" and val(c) not in ("Reference", "Value", "Datasheet"):
            continue
        if isinstance(c, list) and head(c) == "property" and val(c) == "Datasheet":
            c[2] = ("str", "")
        if isinstance(c, list) and head(c) in ("embedded_files", "embedded_fonts", "descr"):
            continue
        keep.append(c)
    at = next(i for i, c in enumerate(keep) if isinstance(c, list) and head(c) == "layer") + 1
    keep.insert(at, [("atom", "descr"), ("str", RPI_DESCR)])
    node[:] = keep


def build_footprints(share, models_needed):
    if os.path.isdir(PRETTY):
        shutil.rmtree(PRETTY)
    os.makedirs(PRETTY)
    n = 0
    for name, (lib, model) in sorted(STOCK_FOOTPRINTS.items()):
        src = os.path.join(share, "footprints", lib + ".pretty", name + ".kicad_mod")
        node = parse(open(src, encoding="utf-8").read())[0]
        if model is None:
            model = _stock_model(node)
        if name.startswith("USB_C_Receptacle_HRO"):
            _trim_usbc_silk(node)
        _set_model(node, model)
        if model:
            models_needed[model] = lib
        write(os.path.join(PRETTY, name + ".kicad_mod"), ser(node) + "\n")
        n += 1
    rpi = os.path.join(HERE, "rpi_minimal", "rpi.pretty")
    for src_name, (name, model, mlib) in sorted(RPI_FOOTPRINTS.items()):
        node = parse(open(os.path.join(rpi, src_name + ".kicad_mod"), encoding="utf-8").read())[0]
        _fp_name(node, name)
        _clean_rpi(node)
        _set_model(node, model)
        models_needed[model] = mlib
        write(os.path.join(PRETTY, name + ".kicad_mod"), ser(node) + "\n")
        n += 1
    import footprints
    for name, text in footprints.generated().items():
        write(os.path.join(PRETTY, name + ".kicad_mod"), text)
        n += 1
    models_needed.update({m: None for m in footprints.MODELS})
    return n


def copy_models(share, models_needed):
    os.makedirs(SHAPES, exist_ok=True)
    have, ours = 0, []
    for model, lib in sorted(models_needed.items()):
        dst = os.path.join(SHAPES, model)
        src = os.path.join(share, "3dmodels", (lib or "") + ".3dshapes", model) if lib else None
        if src and os.path.exists(src):
            shutil.copy(src, dst)
            have += 1
        else:
            ours.append(model)            # made by gen/models3d.py
    return have, ours


def lib_tables():
    write(os.path.join(HW, "sym-lib-table"),
          '(sym_lib_table\n\t(version 7)\n\t(lib (name "%s") (type "KiCad") (uri "${KIPRJMOD}/lib/%s.kicad_sym") '
          '(options "") (descr "Every symbol GPiBridge uses"))\n)\n' % (LIB, LIB))
    write(os.path.join(HW, "fp-lib-table"),
          '(fp_lib_table\n\t(version 7)\n\t(lib (name "%s") (type "KiCad") (uri "${KIPRJMOD}/lib/%s.pretty") '
          '(options "") (descr "Every footprint GPiBridge uses"))\n)\n' % (LIB, LIB))
    write(os.path.join(LIBDIR, "README.md"), LIB_README)


LIB_README = """# hardware/lib: everything the board is drawn with

Made by `gen/library.py`; do not edit by hand.

- `GPiBridge.kicad_sym`: KiCad's own symbols (flattened, so nothing points
  at a library you may not have), plus the ones drawn for this board in
  `gen/symbols.py` (RP2354A, SN75160B, SN75161B, the IEEE-488 plug, the debug
  connectors, the power flags).
- `GPiBridge.pretty/`: KiCad's own footprints; Raspberry Pi's QFN-60,
  inductor and 0402 footprints from their RP2350A Minimal design
  (`gen/rpi_minimal/`, MIT licence), used so that their regulator layout can be
  copied exactly; and the IEEE-488 plug (`gen/footprints.py`).
- `GPiBridge.3dshapes/`: KiCad's STEP models, plus the ones drawn in
  `gen/models3d.py` for parts KiCad's AppImage does not ship (the RP2354A's
  QFN-60, the HRO USB-C, the AOTA inductor, the IEEE-488 plug).

Licences: KiCad's symbols, footprints and 3D models are CC-BY-SA 4.0 with the
KiCad libraries' exception (using them in a design does not put the design
under CC-BY-SA).  Raspberry Pi's footprints are MIT licensed
(`gen/rpi_minimal/LICENSE.txt`).  The rest is this project's (see `LICENSE`).
"""


def main():
    share = kienv.share()
    ns = build_symbols(share)
    models = {}
    nf = build_footprints(share, models)
    have, ours = copy_models(share, models)
    lib_tables()
    import models3d
    drawn = {fn()[0] + ".wrl" for fn in models3d.MODELS}
    missing = [m for m in ours if m not in drawn]
    if missing:
        raise SystemExit("no 3D model for: %s" % ", ".join(missing))
    models3d.main()
    keep = {os.path.splitext(m)[0] for m in models} | {os.path.splitext(m)[0] for m in drawn}
    for f in sorted(os.listdir(SHAPES)):
        if os.path.splitext(f)[0] not in keep:
            os.remove(os.path.join(SHAPES, f))         # left by an earlier build: no footprint uses it
    print("library: %d symbols, %d footprints, %d 3D models copied from KiCad, %d drawn"
          % (ns, nf, have, len(drawn)))
    return 0


if __name__ == "__main__":
    main()
