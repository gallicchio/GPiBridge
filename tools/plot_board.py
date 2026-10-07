#!/usr/bin/env python3
"""Draw the floorplan: board outline, the plug's flange, courtyards, pads and
the ratsnest (a minimum spanning tree per net), to judge a placement at a
glance.  Reads the JSON that `gen/board.py --dump` writes.

    python3 tools/plot_board.py build/board.json build/view/floorplan.png [--no-gnd]
        [--zoom x0 y0 x1 y1] [--labels]

--zoom draws only that window (board millimetres); --labels prints each pad's
net on it, small, for checking a crowded corner.
"""
import json, math, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon


def mst(points):
    if len(points) < 2:
        return []
    inside, edges = {0}, []
    best = {i: (math.dist(points[0], points[i]), 0) for i in range(1, len(points))}
    while best:
        i = min(best, key=lambda k: best[k][0])
        d, j = best.pop(i)
        edges.append((points[j], points[i]))
        inside.add(i)
        for k in best:
            dk = math.dist(points[i], points[k])
            if dk < best[k][0]:
                best[k] = (dk, i)
    return edges


def main():
    src, out = sys.argv[1], sys.argv[2]
    no_gnd = "--no-gnd" in sys.argv
    d = json.load(open(src))
    W, H = d["board"]["w"], d["board"]["h"]
    labels = "--labels" in sys.argv
    zoom = None
    if "--zoom" in sys.argv:
        i = sys.argv.index("--zoom")
        zoom = [float(v) for v in sys.argv[i + 1:i + 5]]
    zw, zh = (zoom[2] - zoom[0], zoom[3] - zoom[1]) if zoom else (W + 6, H + 6)
    scale = 14.0 / max(zw, zh * 1.6)
    fig, ax = plt.subplots(figsize=(max(6, zw * scale * 1.6), max(4, zh * scale * 1.6)), dpi=130)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    if d.get("flange"):
        f = d["flange"]
        ax.add_patch(Rectangle((f["x0"], f["y0"]), f["x1"] - f["x0"], f["y1"] - f["y0"], fill=False, lw=1, ls="--", ec="gray"))
    nets = {}
    parked = []
    for ref, p in d["parts"].items():
        (x0, y0), (x1, y1) = p["box"]
        if p["pos"][0] > W + 8 or p["pos"][1] > H + 8:
            parked.append(ref)
            continue
        col = "#3060c0" if p["side"] == "F" else "#c06030"
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.6, ec=col))
        for pd in p["pads"]:
            pc = "#d4a020" if pd["th"] else "#c03030" if p["side"] == "F" else "#3090c0"
            ax.add_patch(Rectangle((pd["x"] - pd["w"] / 2, pd["y"] - pd["h"] / 2), pd["w"], pd["h"], fc=pc, ec="none", alpha=0.8))
            if labels and pd["net"]:
                nm = pd["net"].replace("Net-(", "").replace(")", "").lstrip("/")
                ax.text(pd["x"], pd["y"], nm, ha="center", va="center", fontsize=2.6, color="k",
                        rotation=90 if pd["h"] > pd["w"] * 1.3 else 0, clip_on=True)
            if pd["net"]:
                nets.setdefault(pd["net"], []).append((pd["x"], pd["y"]))
        ax.text((x0 + x1) / 2, y0 + 0.25 if labels else (y0 + y1) / 2, ref, ha="center", va="center",
                fontsize=5 if (x1 - x0) > 3 else 3.5, color=col, weight="bold", clip_on=True)
    total = 0.0
    for net, pts in nets.items():
        if no_gnd and net == "GND":
            continue
        for a, b in mst(pts):
            total += math.dist(a, b)
            ax.plot([a[0], b[0]], [a[1], b[1]], lw=0.35, color="#20a040" if net != "GND" else "#bbbbbb")
    if zoom:
        ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[3], zoom[1])
    else:
        ax.set_xlim(-3, W + 3); ax.set_ylim(H + 3, -3)
    ax.set_aspect("equal")
    ax.set_title("ratsnest %.0f mm%s" % (total, ("   not placed: " + " ".join(sorted(parked))) if parked else ""), fontsize=6)
    ax.tick_params(labelsize=5)
    ax.grid(True, lw=0.2, alpha=0.4)
    plt.tight_layout()
    plt.savefig(out)
    print("%s: ratsnest %.0f mm" % (out, total))


if __name__ == "__main__":
    main()
