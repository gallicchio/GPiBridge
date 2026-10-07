"""A grid router with A* per connection, for a four-layer board whose In1 is
an unbroken ground plane: tracks go on F.Cu, In2.Cu and B.Cu.

Adapted from the ECP5-2ADC-2DAC project's pcb/router.py.  Obstacles live in
reference-counted cell grids, one per (layer, width class): an obstacle of
radius R blocks every cell closer than R + clearance + half the track width,
so a track of that class is legal wherever its cells are free.  A net's own
pads and tracks are lifted out of the grids while it is routed, which lets a
track start inside its pad and join its own net anywhere.  Vias are through
vias and need a free cell on every routing layer in the via's class.

Grid pitch 0.1 mm, so the RP2354A's 0.4 mm pins sit on it.
"""
import heapq, math
from array import array

PITCH = 0.1
LAYERS = ["F.Cu", "In2.Cu", "B.Cu"]          # In1.Cu is the ground plane
NL = len(LAYERS)
CLEAR = 0.16                                   # rules ask 0.15; the grid rounds
# half widths: fine 0.127 mm, thin 0.15, mid 0.2, wide 0.4, via 0.45 mm pad
CLASSES = {"fine": 0.0635, "thin": 0.075, "mid": 0.1, "wide": 0.2, "via": 0.225}
CLS = ["fine", "thin", "mid", "wide", "via"]
VIA_COST = 40.0                                # about 4 mm of track
TURN_COST = 2.0
# per layer, the cost multiplier of (horizontal, vertical) steps: F.Cu free,
# In2 and B.Cu nudged toward one direction each so they cross cleanly
DIR_PENALTY = {0: (1.0, 1.0), 1: (1.0, 1.3), 2: (1.3, 1.0)}


def width_class(w):
    hw = w / 2.0
    for c in ("fine", "thin", "mid", "wide"):
        if hw <= CLASSES[c] + 1e-6:
            return c
    return "wide"


class Grid:
    def __init__(self, w, h, edge_clear=0.3):
        self.w, self.h = w, h
        self.nx, self.ny = int(round(w / PITCH)) + 1, int(round(h / PITCH)) + 1
        self.n = self.nx * self.ny
        self.g = {(L, c): array("H", bytes(2 * self.n)) for L in range(NL) for c in CLS}
        self.keep = {L: bytearray(self.n) for L in range(NL)}    # 1 = no track of any net
        self.novia = bytearray(self.n)
        # the board edge: copper keeps edge_clear from it
        for c in CLS:
            m = int(math.ceil((edge_clear + CLASSES[c]) / PITCH))
            for L in range(NL):
                a = self.g[(L, c)]
                for j in range(self.ny):
                    for i in range(self.nx):
                        if i < m or j < m or i >= self.nx - m or j >= self.ny - m:
                            a[j * self.nx + i] += 1

    def cell(self, x, y):
        return (int(round(x / PITCH)), int(round(y / PITCH)))

    def k(self, x, y):
        i, j = self.cell(x, y)
        return j * self.nx + i

    def pos(self, k):
        return ((k % self.nx) * PITCH, (k // self.nx) * PITCH)

    # ---- obstacles --------------------------------------------------------
    def shape_cells(self, shape, r):
        """Cells within r of a shape: ("disc", x, y, rad) | ("rect", x, y, hw,
        hh, ang) | ("seg", x0, y0, x1, y1, hw)."""
        kind = shape[0]
        if kind == "disc":
            _, x, y, rad = shape
            return self._disc(x, y, rad + r)
        if kind == "seg":
            _, x0, y0, x1, y1, hw = shape
            L = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(L / (PITCH * 0.5)))
            out = set()
            for s in range(n + 1):
                t = s / float(n)
                out.update(self._disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, hw + r))
            return out
        _, x, y, hw, hh, ang = shape
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        rr = math.hypot(hw, hh) + r
        ci, cj = self.cell(x, y)
        n = int(math.ceil(rr / PITCH)) + 1
        out = []
        for di in range(-n, n + 1):
            i = ci + di
            if not (0 <= i < self.nx):
                continue
            for dj in range(-n, n + 1):
                j = cj + dj
                if not (0 <= j < self.ny):
                    continue
                dx, dy = i * PITCH - x, j * PITCH - y
                ux, uy = dx * ca + dy * sa, -dx * sa + dy * ca
                gx, gy = max(0.0, abs(ux) - hw), max(0.0, abs(uy) - hh)
                if gx * gx + gy * gy <= r * r + 1e-9:
                    out.append(j * self.nx + i)
        return out

    def _disc(self, x, y, r):
        ci, cj = self.cell(x, y)
        n = int(math.ceil(r / PITCH)) + 1
        out = []
        r2 = r * r + 1e-9
        for di in range(-n, n + 1):
            i = ci + di
            if not (0 <= i < self.nx):
                continue
            dx2 = (i * PITCH - x) ** 2
            for dj in range(-n, n + 1):
                j = cj + dj
                if 0 <= j < self.ny and dx2 + (j * PITCH - y) ** 2 <= r2:
                    out.append(j * self.nx + i)
        return out

    def obstacle(self, shape, layers, clear=CLEAR):
        """{(L, cls): cells} that `shape` on `layers` blocks for each class."""
        out = {}
        for c in CLS:
            cells = self.shape_cells(shape, clear + CLASSES[c])
            for L in layers:
                out[(L, c)] = cells
        return out

    def add(self, cells):
        for key, ks in cells.items():
            a = self.g[key]
            for k in ks:
                a[k] += 1

    def sub(self, cells):
        for key, ks in cells.items():
            a = self.g[key]
            for k in ks:
                if a[k] > 0:
                    a[k] -= 1

    def keepout(self, x0, y0, x1, y1, layers, via=True):
        i0, j0 = self.cell(min(x0, x1), min(y0, y1))
        i1, j1 = self.cell(max(x0, x1), max(y0, y1))
        for j in range(max(0, j0), min(self.ny - 1, j1) + 1):
            for i in range(max(0, i0), min(self.nx - 1, i1) + 1):
                k = j * self.nx + i
                for L in layers:
                    self.keep[L][k] = 1
                if via:
                    self.novia[k] = 1

    # ---- the search -------------------------------------------------------
    def route(self, starts, goals, cls, layers=None, allow_via=True, max_pop=600000, bbox=None,
              via_cost=VIA_COST, layer_cost=None):
        """starts, goals: sets of (L, k).  Returns [(L, k), ...] or None.
        layer_cost: {L: multiplier} on a layer's step costs (default 1)."""
        nx = self.nx
        if bbox is None:
            i0, j0, i1, j1 = 0, 0, nx - 1, self.ny - 1
        else:
            i0, j0, i1, j1 = bbox
        grid = [self.g[(L, cls)] for L in range(NL)]
        vg = [self.g[(L, "via")] for L in range(NL)]
        keep = self.keep
        use = list(layers) if layers is not None else list(range(NL))
        goal = set(goals)
        gpts = list({(k % nx, k // nx) for (_, k) in goal})
        if len(gpts) > 60:
            gpts = gpts[::max(1, len(gpts) // 60)]

        def h(i, j):
            return min(max(abs(gi - i), abs(gj - j)) + 0.414 * min(abs(gi - i), abs(gj - j)) for gi, gj in gpts) * 0.98

        pq, best, par = [], {}, {}
        for s in starts:
            if s in goal:
                return [s]
            if s[0] not in use:
                continue
            best[s] = 0.0
            heapq.heappush(pq, (h(s[1] % nx, s[1] // nx), 0.0, s[0], s[1], -1))
        NB = [(1, 0, 1.0, 0), (-1, 0, 1.0, 0), (0, 1, 1.0, 1), (0, -1, 1.0, 1),
              (1, 1, 1.414, 2), (1, -1, 1.414, 3), (-1, 1, 1.414, 3), (-1, -1, 1.414, 2)]
        pops, found = 0, None
        while pq:
            f, gc, L, k, d = heapq.heappop(pq)
            if best.get((L, k), 1e18) < gc - 1e-9:
                continue
            pops += 1
            if pops > max_pop:
                break
            if (L, k) in goal:
                found = (L, k)
                break
            i, j = k % nx, k // nx
            ph, pv = DIR_PENALTY[L]
            if layer_cost:
                lc = layer_cost.get(L, 1.0)
                ph, pv = ph * lc, pv * lc
            gl, kl = grid[L], keep[L]
            for di, dj, c, nd in NB:
                ii, jj = i + di, j + dj
                if ii < i0 or jj < j0 or ii > i1 or jj > j1:
                    continue
                kk = jj * nx + ii
                if (gl[kk] or kl[kk]) and (L, kk) not in goal:
                    continue
                if di and dj:
                    if gl[j * nx + ii] or gl[jj * nx + i]:
                        continue
                    cc = c * (ph + pv) / 2.0
                else:
                    cc = c * (ph if di else pv)
                if d >= 0 and d != nd:
                    cc += TURN_COST
                ng = gc + cc
                if ng < best.get((L, kk), 1e18):
                    best[(L, kk)] = ng
                    par[(L, kk)] = (L, k)
                    heapq.heappush(pq, (ng + h(ii, jj), ng, L, kk, nd))
            if allow_via and not self.novia[k] and all(not vg[LL][k] for LL in range(NL)):
                for LL in use:
                    if LL == L:
                        continue
                    ng = gc + via_cost
                    if ng < best.get((LL, k), 1e18):
                        best[(LL, k)] = ng
                        par[(LL, k)] = (L, k)
                        heapq.heappush(pq, (ng + h(i, j), ng, LL, k, -1))
        if found is None:
            return None
        path, cur = [], found
        while cur is not None:
            path.append(cur)
            cur = par.get(cur)
        path.reverse()
        return path


def simplify(path, nx):
    """Runs of one direction on one layer become segments; a change of layer
    is a via.  Returns (segments [(L, x0, y0, x1, y1)], vias [(x, y)])."""
    segs, vias = [], []
    if not path:
        return segs, vias
    pts = [(L, (k % nx) * PITCH, (k // nx) * PITCH) for L, k in path]
    i = 0
    while i < len(pts) - 1:
        L, x, y = pts[i]
        if pts[i + 1][0] != L:
            vias.append((x, y))
            i += 1
            continue
        dx, dy = round((pts[i + 1][1] - x) / PITCH), round((pts[i + 1][2] - y) / PITCH)
        j = i + 1
        while j + 1 < len(pts) and pts[j + 1][0] == L and \
                (round((pts[j + 1][1] - pts[j][1]) / PITCH), round((pts[j + 1][2] - pts[j][2]) / PITCH)) == (dx, dy):
            j += 1
        segs.append((L, x, y, pts[j][1], pts[j][2]))
        i = j
    return segs, vias
