#!/usr/bin/env python3
"""Make hardware/GPiBridge.kicad_pcb (or, with GPIBRIDGE_VARIANT=lite,
hardware/GPiBridgeLite.kicad_pcb) from the netlist, the placement table
(gen/placement.py), the routes (gen/routes.py) and the silkscreen
(gen/silk.py).

    python3 gen/board.py              place, route, pour, silk, save
    python3 gen/board.py --place      placement only (no tracks): for floorplanning
    python3 gen/board.py --dump F     also write a JSON of pads, courtyards and nets
                                      for tools/plot_board.py

Runs inside KiCad's own Python (it relaunches itself there through
tools/kienv.py), so pcbnew does every rotation, flip and pad transform: no
coordinate convention of ours can disagree with KiCad's.

Board coordinates in the placement table are millimetres from the board's
top-left corner, x right, y down; ORIGIN puts that corner on KiCad's page.
"""
import json, math, os, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)

if "--inside" not in sys.argv:
    import subprocess, kienv
    # a fixed hash seed: any set of strings iterates in the same order every run,
    # so items are made in the same order and get the same UUIDs (main())
    r = subprocess.run(kienv.python() + [os.path.abspath(__file__), "--inside"] + sys.argv[1:],
                       cwd=ROOT, text=True, capture_output=True, env=dict(os.environ, PYTHONHASHSEED="0"))
    sys.stdout.write("\n".join(l for l in r.stdout.splitlines() if "Font '" not in l) + ("\n" if r.stdout else ""))
    sys.stderr.write("\n".join(l for l in r.stderr.splitlines() if "Font '" not in l))
    sys.exit(r.returncode)

import pcbnew
from sexp import parse, kids, kid, val
import board_info as BI
import placement as PL

HW = BI.HW
PCB = BI.PCB
NETLIST = BI.NETLIST
LIBDIR = os.path.join(HW, "lib", "GPiBridge.pretty")
ORIGIN = (100.0, 100.0)


def mm(v):
    return pcbnew.FromMM(float(v))


def P(x, y):
    """Board coordinates (mm from the top-left corner) to KiCad's."""
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))


def B(v):
    """KiCad's coordinates back to board millimetres."""
    return (pcbnew.ToMM(v.x) - ORIGIN[0], pcbnew.ToMM(v.y) - ORIGIN[1])


# ---------------------------------------------------------------------------
def read_netlist(path):
    doc = parse(open(path, encoding="utf-8").read())[0]
    comps = {}
    for c in kids(kid(doc, "components"), "comp"):
        ref = val(kid(c, "ref"))
        fields = {}
        fl = kid(c, "fields")
        for f in kids(fl, "field") if fl else []:
            if len(f) > 2:
                fields[val(kid(f, "name"))] = val(f, 2)
        comps[ref] = dict(value=val(kid(c, "value")), footprint=val(kid(c, "footprint")), fields=fields)
    nets = {}
    for n in kids(kid(doc, "nets"), "net"):
        nets[val(kid(n, "name"))] = [(val(kid(x, "ref")), val(kid(x, "pin"))) for x in kids(n, "node")]
    return comps, nets


# ---------------------------------------------------------------------------
# The stackup: JLCPCB JLC04161H-7628, 1.6 mm.  F.Cu signals, In1 a solid
# ground, In2 signals and the 3.3 V pour, B.Cu signals under a ground fill.
STACKUP = [("F.Cu", "copper", 0.035), ("dielectric 1", "prepreg", 0.2104),
           ("In1.Cu", "copper", 0.0152), ("dielectric 2", "core", 1.065),
           ("In2.Cu", "copper", 0.0152), ("dielectric 3", "prepreg", 0.2104),
           ("B.Cu", "copper", 0.035)]


def setup(board):
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))
    # the zone filler reads the board's own settings, not the project file:
    # set the ones that decide how far a pour backs off
    ds.m_MinClearance = mm(0.15)
    ds.m_HoleClearance = mm(0.2)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_TrackMinWidth = mm(0.127)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.25)
    for name in ("In1.Cu", "In2.Cu"):
        board.SetLayerType(board.GetLayerID(name), pcbnew.LT_SIGNAL)
    # the drill/place origin at the board's bottom-left corner: Gerbers, drill
    # and placement files all measure from it, x right and y up
    ds.SetAuxOrigin(P(0, PL.BOARD["h"]))
    ds.SetGridOrigin(P(0, PL.BOARD["h"]))
    board.SetLayerName(board.GetLayerID("In1.Cu"), "In1.Cu")


def outline(board):
    w, h, r = PL.BOARD["w"], PL.BOARD["h"], PL.BOARD["r"]
    segs = [((r, 0), (w - r, 0)), ((w, r), (w, h - r)), ((w - r, h), (r, h)), ((0, h - r), (0, r))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    for cx, cy, a0 in ((r, r, 180), (w - r, r, 270), (w - r, h - r, 0), (r, h - r, 90)):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(P(cx, cy))
        s.SetStart(P(cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(LIBDIR, name)
    if fp is None:
        raise SystemExit("footprint %s not found in %s" % (fpid, LIBDIR))
    return fp


SEEDS = set()


def seed(what):
    """Restart KiCad's UUID generator from a seed named for what comes next
    (a footprint's reference, a stage of the build), so each part's UUIDs
    depend on that part alone: changing one footprint leaves every other
    one's lines in the file as they were."""
    n = zlib.crc32(("gpibridge:" + what).encode()) or 1
    assert n not in SEEDS, "two seeds collide: %s" % what
    SEEDS.add(n)
    pcbnew.KIID.SeedGenerator(n)


def place_parts(board, comps, nets):
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pin_net[(ref, pin)] = name
    fps = {}
    missing = []
    for ref, c in sorted(comps.items()):
        if not c["footprint"] or c["footprint"].endswith(":"):
            continue                         # PWR_FLAGs
        seed(ref)
        fp = load_fp(c["footprint"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for k, v in c["fields"].items():
            if k in ("LCSC", "MPN"):
                fp.SetField(k, v)
                # a new field lands visible on the silkscreen: the BOM reads it, nobody needs to see it
                f = fp.GetField(k) if hasattr(fp, "GetField") else fp.GetFieldByName(k)
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        board.Add(fp)
        if ref not in PL.PLACE:
            missing.append(ref)
            x, y, rot, side = 80.0 + 5 * (len(missing) % 6), 5.0 * (len(missing) // 6), 0, "F"
        else:
            x, y, rot, side = PL.PLACE[ref]
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))
        for pad in fp.Pads():
            n = pin_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fps[ref] = fp
    return fps, netinfo, missing


def dump(board, fps, nets, path):
    """Pads, courtyards and nets in board millimetres, for tools/plot_board.py."""
    out = {"board": PL.BOARD, "parts": {}, "nets": {}, "flange": PL.FLANGE}
    for ref, fp in fps.items():
        cy = fp.GetCourtyard(fp.GetLayer() == pcbnew.B_Cu and pcbnew.B_CrtYd or pcbnew.F_CrtYd)
        if cy.OutlineCount():
            bb = cy.BBox()
            box = [B(pcbnew.VECTOR2I(bb.GetX(), bb.GetY())), B(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))]
        else:
            bb = fp.GetBoundingBox(False)
            box = [B(pcbnew.VECTOR2I(bb.GetX(), bb.GetY())), B(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))]
        pads = []
        for p in fp.Pads():
            c = B(p.GetPosition())
            s = p.GetBoundingBox()
            pads.append(dict(num=p.GetNumber(), net=p.GetNetname(), x=c[0], y=c[1],
                             w=pcbnew.ToMM(s.GetWidth()), h=pcbnew.ToMM(s.GetHeight()),
                             th=p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH))
        out["parts"][ref] = dict(box=box, pads=pads, side="B" if fp.GetLayer() == pcbnew.B_Cu else "F",
                                 value=fp.GetValue(), pos=B(fp.GetPosition()), rot=fp.GetOrientationDegrees())
    json.dump(out, open(path, "w"), indent=0)


def copper(board, args):
    """Planned copper, ground fan-out, then the router; returns the Router."""
    import routing as RT
    import routes as RS
    R = RT.Router(board, P, B, PL.BOARD["w"], PL.BOARD["h"])
    R.load_pads()
    pads = RS.Pads(board, B)
    RS.rpi_core(R, pads)
    RS.ribbon(R, pads)
    (RS.bus_side_lite if BI.LITE else RS.bus_side)(R, pads)
    RS.lanes(R, pads)
    RS.local(R, pads)
    RS.supply_planes(R)
    n = R.fanout("GND")
    print("copper: planned and fan-out: %d tracks, %d vias (%d ground fan-outs)" % (R.n_tracks, R.n_vias, n))
    if "--planned" not in args:
        RS.autoroute(R, pads)
    return R


def pours(board, R):
    """Ground everywhere the routing left room: In1 solid, and fills on F.Cu
    and In2 (the bottom layer is the two supply pours, made with the
    routing).  Then fill every zone, so the saved board carries its copper."""
    W, H = PL.BOARD["w"], PL.BOARD["h"]
    whole = [(0, 0), (W, 0), (W, H), (0, H)]
    R.zone("GND", pcbnew.In1_Cu, whole, priority=0, clearance=0.2, min_width=0.2, item=False, name="GND plane")
    R.zone("GND", pcbnew.In2_Cu, whole, priority=0, clearance=0.2, min_width=0.25, item=False, name="GND In2")
    R.zone("GND", pcbnew.F_Cu, whole, priority=0, clearance=0.2, min_width=0.25, item=False, name="GND top")
    # the filler drops islands it finds unconnected, and it judges that from the
    # board's connectivity, which a board built in memory has not computed yet:
    # without this it removed the ground pour under the USB-C
    board.BuildConnectivity()
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    n = sum(1 for z in board.Zones() if z.HasFilledPolysForLayer(z.GetFirstLayer()) and
            z.GetFilledPolysList(z.GetFirstLayer()).OutlineCount())
    print("pours: %d zones, %d filled" % (len(list(board.Zones())), n))


def main():
    args = [a for a in sys.argv[1:] if a != "--inside"]
    # every item's UUID from a seeded generator, so a rebuild of an unchanged
    # design writes the same file and git shows only what changed
    pcbnew.KIID.SeedGenerator(488)
    comps, nets = read_netlist(NETLIST)
    board = pcbnew.CreateEmptyBoard()
    setup(board)
    outline(board)
    fps, netinfo, missing = place_parts(board, comps, nets)
    if "--dump" in args:
        dump(board, fps, nets, args[args.index("--dump") + 1])
    if "--place" not in args:
        seed("copper")
        R = copper(board, args)
        for net, why in R.failed:
            print("   UNROUTED %s: %s" % (net, why))
        left = {n: R.unrouted(n) for n in R.by_net if not n.startswith("<") and R.unrouted(n)}
        for n in sorted(left):
            for g in R.groups(n):
                pos = R.g.pos(next(iter(next(iter(R.items[g[0]].cells.values())))))
                whats = sorted(set(R.items[i].what for i in g))
                print("      %s piece at (%.1f, %.1f): %s" % (n, pos[0], pos[1], ", ".join(whats)[:100]))
        seed("pours")
        pours(board, R)
        import silk
        seed("silk")
        silk.apply(board, fps, P, B)
        print("copper: %d tracks, %d vias; %d nets with unjoined pieces%s"
              % (R.n_tracks, R.n_vias, len(left), (": " + ", ".join("%s(%d)" % kv for kv in sorted(left.items())))
                 if left else ""))
    if "--stamp" in args and "--place" not in args:
        import routing as RT
        i = args.index("--stamp")
        net, x, y, r = args[i + 1], float(args[i + 2]), float(args[i + 3]), float(args[i + 4])
        st = RT.stamp(R, net, 0.15, x - r, y - r, x + r, y + r)
        json.dump(st, open(os.path.join(ROOT, "build", "stamp.json"), "w"))
        print("stamp: %s around (%.1f, %.1f) -> build/stamp.json" % (net, x, y))
    board.Save(PCB)
    # pcbnew's Save also writes the .kicad_pro, with its default net classes
    # and rules: put the project's own back
    import project
    project.write(HW)
    print("board: %d footprints placed%s -> %s" % (len(fps), ("; NOT IN THE PLACEMENT TABLE: " + " ".join(missing)) if missing else "",
                                                     os.path.relpath(PCB, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
