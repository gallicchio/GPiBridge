#!/usr/bin/env python3
"""Copy the RP2350 regulator layout out of Raspberry Pi's own design.

"Hardware design with RP2350" says to copy the Pico 2 / Minimal design's
regulator layout exactly, or deviate at your own risk.  This script takes it
from Raspberry Pi's "RP2350A Minimal KiCAD design" (RP-010328-CA, MIT licence):

  gen/rpi_minimal/rpi.pretty/       the QFN-60 footprint (with its exposed-pad
                                    vias), the AOTA inductor, the 0402 parts
  gen/rpi_minimal/regulator.json    the zones, tracks and vias around pins 46-54
                                    (the regulator, and the capacitor that pins 53
                                    and 54 share), in millimetres from U1's centre
  gen/rpi_minimal/LICENSE.txt       their licence

    python3 tools/extract_rpi_minimal.py [path/to/RP2350A Minimal KiCAD.zip]

Without an argument it downloads the ZIP into reference/ (ignored by git).  The
output is committed, so the build never needs the ZIP.
"""
import json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "gen", "rpi_minimal")
URL = "https://pip.raspberrypi.com/documents/RP-010328-CA"
sys.path.insert(0, HERE)

INSIDE = r'''
import pcbnew, sys, json, os
b = pcbnew.LoadBoard(sys.argv[1]); out = sys.argv[2]
u1 = [fp for fp in b.GetFootprints() if fp.GetReference() == "U1"][0]
ux, uy = pcbnew.ToMM(u1.GetPosition().x), pcbnew.ToMM(u1.GetPosition().y)
def rel(p): return [round(pcbnew.ToMM(p.x) - ux, 4), round(pcbnew.ToMM(p.y) - uy, 4)]
data = {"source": "Raspberry Pi RP2350A Minimal Design Example R4 (RP-010328-CA), MIT licence, (c) 2026 Raspberry Pi Ltd",
        "frame": "millimetres from U1's centre, U1 at rotation 0 (pin 1 at top left), y down",
        "zones": [], "tracks": [], "vias": [], "footprints": []}
for z in b.Zones():
    if 4 <= z.GetAssignedPriority() <= 7:          # the regulator's own copper islands
        ol = z.Outline().COutline(0)
        data["zones"].append(dict(net=z.GetNetname(), layers=[b.GetLayerName(l) for l in z.GetLayerSet().Seq()],
            priority=z.GetAssignedPriority(), clearance=pcbnew.ToMM(z.GetLocalClearance() or 0),
            min_width=pcbnew.ToMM(z.GetMinThickness()), pad_connection=int(z.GetPadConnection()),
            outline=[rel(ol.CPoint(i)) for i in range(ol.PointCount())]))
X0, X1, Y0, Y1 = -2.2, 5.0, -8.6, -3.2               # the regulator corner above pins 46-54
def inside(p): x, y = rel(p); return X0 <= x <= X1 and Y0 <= y <= Y1
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        if inside(t.GetPosition()):
            data["vias"].append(dict(at=rel(t.GetPosition()), diameter=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)),
                                     drill=pcbnew.ToMM(t.GetDrillValue()), net=t.GetNetname()))
    elif t.GetNetname() in ("+1V1", "/VREG_AVDD", "/VREG_LX", "GND", "+3V3") and (inside(t.GetStart()) or inside(t.GetEnd())):
        data["tracks"].append(dict(layer=t.GetLayerName(), start=rel(t.GetStart()), end=rel(t.GetEnd()),
                                   width=pcbnew.ToMM(t.GetWidth()), net=t.GetNetname()))
io = pcbnew.PCB_IO_KICAD_SEXPR()
lib = os.path.join(out, "rpi.pretty")
os.path.isdir(lib) or io.CreateLibrary(lib)
for fp in b.GetFootprints():
    if fp.GetReference() in ("U1", "L1", "C6", "C7", "C9", "R3", "R7", "R8"):
        data["footprints"].append(dict(ref=fp.GetReference(), fpid=fp.GetFPIDAsString(), at=rel(fp.GetPosition()),
                                       rot=fp.GetOrientationDegrees(), value=fp.GetValue(),
                                       pads={p.GetNumber(): p.GetNetname() for p in fp.Pads()}))
        f2 = pcbnew.FOOTPRINT(fp); f2.SetPosition(pcbnew.VECTOR2I(0, 0)); f2.SetOrientationDegrees(0)
        io.FootprintSave(lib, f2)
json.dump(data, open(os.path.join(out, "regulator.json"), "w"), indent=1)
print(len(data["zones"]), "zones,", len(data["tracks"]), "tracks,", len(data["vias"]), "vias")
'''


def main():
    import kienv
    zpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reference", "RP2350A_Minimal_KiCAD.zip")
    if not os.path.exists(zpath):
        os.makedirs(os.path.dirname(zpath), exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        open(zpath, "wb").write(urllib.request.urlopen(req, timeout=120).read())
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zpath) as z:
        z.extractall(tmp)
    pcb = [os.path.join(d, f) for d, _, fs in os.walk(tmp) for f in fs if f.endswith(".kicad_pcb")][0]
    lic = [os.path.join(d, f) for d, _, fs in os.walk(tmp) for f in fs if f == "LICENSE.txt"][0]
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copy(lic, os.path.join(OUT, "LICENSE.txt"))
    script = os.path.join(tmp, "inside.py")
    open(script, "w").write(INSIDE)
    r = subprocess.run(kienv.python() + [script, pcb, OUT], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr[-2000:])
    shutil.rmtree(tmp)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
