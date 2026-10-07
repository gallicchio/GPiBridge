#!/usr/bin/env python3
"""Check a placement before routing it: courtyards that overlap, pads of
different nets too close, parts off the board, copper too near the edge.
Reads the JSON that `gen/board.py --dump` writes.

    python3 tools/check_place.py build/board.json

Courtyards are compared as their bounding boxes, which is exact for the
rectangles every footprint here has.  A part on the back is checked only
against the back, except for its through-hole pads, which are on both.
"""
import json, sys

PAD_GAP = 0.2        # mm between pads of different nets (JLCPCB's SMT minimum is ~0.15)
EDGE = 0.3           # mm from copper to the board edge


def overlap(a, b, gap=0.0):
    (ax0, ay0), (ax1, ay1) = a
    (bx0, by0), (bx1, by1) = b
    return ax0 < bx1 + gap and bx0 < ax1 + gap and ay0 < by1 + gap and by0 < ay1 + gap


def pad_box(p):
    return [(p["x"] - p["w"] / 2, p["y"] - p["h"] / 2), (p["x"] + p["w"] / 2, p["y"] + p["h"] / 2)]


def gap(a, b):
    (ax0, ay0), (ax1, ay1) = a
    (bx0, by0), (bx1, by1) = b
    dx = max(0.0, max(ax0, bx0) - min(ax1, bx1))
    dy = max(0.0, max(ay0, by0) - min(ay1, by1))
    return (dx * dx + dy * dy) ** 0.5


def main():
    d = json.load(open(sys.argv[1]))
    W, H = d["board"]["w"], d["board"]["h"]
    parts = d["parts"]
    out = []
    refs = sorted(parts)
    for i, a in enumerate(refs):
        pa = parts[a]
        (x0, y0), (x1, y1) = pa["box"]
        if pa["side"] == "F" and (x0 < -0.01 or y0 < -0.01 or x1 > W + 0.01 or y1 > H + 0.01) and not a.startswith("J1"):
            out.append("%s: courtyard leaves the board (%.2f,%.2f)-(%.2f,%.2f)" % (a, x0, y0, x1, y1))
        for p in pa["pads"]:
            (px0, py0), (px1, py1) = pad_box(p)
            if min(px0, py0, W - px1, H - py1) < EDGE - 1e-6 and not a.startswith("J1"):
                out.append("%s pad %s: %.2f mm from the board edge" % (a, p["num"], min(px0, py0, W - px1, H - py1)))
        for b in refs[i + 1:]:
            pb = parts[b]
            if pa["side"] == pb["side"] and overlap(pa["box"], pb["box"]):
                out.append("courtyards overlap: %s and %s" % (a, b))
            for p in pa["pads"]:
                for q in pb["pads"]:
                    both = (p["th"] or pa["side"] == pb["side"]) and (q["th"] or pa["side"] == pb["side"])
                    if not both or (p["net"] and p["net"] == q["net"]):
                        continue
                    g = gap(pad_box(p), pad_box(q))
                    if g < PAD_GAP:
                        out.append("pads %.2f mm apart: %s.%s (%s) and %s.%s (%s)"
                                   % (g, a, p["num"], p["net"], b, q["num"], q["net"]))
    for o in out:
        print("  " + o)
    print("placement: %d problems" % len(out))
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
