from .layout import Placement, compute_layout
from .models import Door, Dungeon
import xml.etree.ElementTree as ET
import math
import random

from typing import Literal
from collections import Counter

CELL_SIZE = (
    140  # px per grid cell — bigger than the 100x80 room so there's room for corridors
)

ROOM_X, ROOM_Y = 10, 10

SIZE_DIMS = {
    "tiny": (60, 50),
    "small": (80, 64),
    "medium": (100, 80),
    "large": (100, 80),
    "vast": (100, 80),
}

CORRIDOR_WIDTHS = {
    "tiny": 12,
    "small": 14,
    "medium": 18,
    "large": 18,
    "vast": 18,
}

PAD = 24  # breathing room so hatching isn't clipped at the map edges
LEGEND_WIDTH = 220
LEGEND_LINE_HEIGHT = 22
FONT = "Georgia, 'Times New Roman', serif"

Route = Literal["straight", "v-first", "h-first", "skip"]


def plan_routes(
    edges: list[tuple[Placement, Placement, Door]], room_cells: set[tuple[int, int]]
) -> dict[tuple[str, str], Route]:

    out: dict[tuple[str, str], Route] = {}
    claims: Counter[tuple[str, str]] = Counter()
    # Pass 1, for corridors don't have options
    for source, target, _ in edges:
        key = (source.room.id, target.room.id)
        cell_dx, cell_dy = target.x - source.x, target.y - source.y

        if cell_dx == 0 and cell_dy == 0:
            out[key] = "skip"
            continue
        if cell_dx and cell_dy:
            continue

        step_x = (cell_dx > 0) - (cell_dx < 0)
        step_y = (cell_dy > 0) - (cell_dy < 0)
        distance = abs(cell_dx) + abs(cell_dy)

        for i in range(1, distance):
            if (source.x + step_x * i, source.y + step_y * i) in room_cells:
                out[key] = "skip"
                break
        else:
            out[key] = "straight"
            if cell_dx:
                claims[(source.room.id, "e" if cell_dx > 0 else "w")] += 1
                claims[(target.room.id, "w" if cell_dx > 0 else "e")] += 1
            else:
                claims[(source.room.id, "s" if cell_dy > 0 else "n")] += 1
                claims[(target.room.id, "n" if cell_dy > 0 else "s")] += 1

    for source, target, _ in edges:
        key = (source.room.id, target.room.id)
        if key in out:
            continue  # already added in pass 1
        cell_dx, cell_dy = target.x - source.x, target.y - source.y

        if abs(cell_dx) != 1 or abs(cell_dy) != 1:
            out[key] = "skip"  # knight move displacement 'unroutable'
            continue

        v_ok = (source.x, target.y) not in room_cells
        h_ok = (target.x, source.y) not in room_cells
        v_walls = (
            (source.room.id, "s" if cell_dy > 0 else "n"),
            (target.room.id, "w" if cell_dx > 0 else "e"),
        )
        h_walls = (
            (source.room.id, "e" if cell_dx > 0 else "w"),
            (target.room.id, "n" if cell_dy > 0 else "s"),
        )

        if not v_ok and not h_ok:
            out[key] = "skip"
            continue
        v_cost = claims[v_walls[0]] + claims[v_walls[1]]
        h_cost = claims[h_walls[0]] + claims[h_walls[1]]
        if v_ok and (not h_ok or v_cost <= h_cost):
            out[key] = "v-first"
            walls = v_walls
        else:
            out[key] = "h-first"
            walls = h_walls
        claims[walls[0]] += 1
        claims[walls[1]] += 1

    return out


def render_svg(dungeon: Dungeon) -> str:
    lay_out = compute_layout(dungeon)
    numbers = {room.id: i + 1 for i, room in enumerate(dungeon.rooms)}

    xs = [p.x for p in lay_out.placements.values()]
    ys = [p.y for p in lay_out.placements.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    map_w = (max_x - min_x + 1) * CELL_SIZE
    map_h = (max_y - min_y + 1) * CELL_SIZE
    legend_h = 40 + LEGEND_LINE_HEIGHT * len(dungeon.rooms)

    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": (
                f"{min_x * CELL_SIZE - PAD} {min_y * CELL_SIZE - PAD} "
                f"{map_w + 2 * PAD + LEGEND_WIDTH} {max(map_h, legend_h) + 2 * PAD}"
            ),
        },
    )

    # two paint layers: all rock hatching first, then every white floor
    # rect on top — so stray tick ends can never show inside a room or
    # corridor, no matter which feature drew them
    hatch_layer = ET.SubElement(
        svg, "g", {"stroke": "black", "stroke-linecap": "round"}
    )
    floor_layer = ET.SubElement(svg, "g")

    for placement in lay_out.placements.values():
        render_room(hatch_layer, floor_layer, placement, numbers[placement.room.id])

    room_cells = {(p.x, p.y) for p in lay_out.placements.values()}
    edges: list[tuple[Placement, Placement, Door]] = []
    seen: set[frozenset[str]] = set()

    for room in dungeon.rooms:
        for door in room.exits:
            key = frozenset((room.id, door.target))
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                (lay_out.placements[room.id], lay_out.placements[door.target], door)
            )

    routes = plan_routes(edges, room_cells)

    for source, target, door in edges:
        render_door(
            hatch_layer,
            floor_layer,
            source,
            target,
            door,
            routes[(source.room.id, target.room.id)],
        )

    svg.append(
        render_legend(
            dungeon, numbers, x=min_x * CELL_SIZE + map_w + PAD, y=min_y * CELL_SIZE
        )
    )

    ET.indent(svg)
    return ET.tostring(svg, encoding="unicode")


def render_legend(
    dungeon: Dungeon, numbers: dict[str, int], x: float, y: float
) -> ET.Element:
    g = ET.Element("g", {"font-family": FONT})
    title = ET.SubElement(
        g,
        "text",
        {"x": str(x), "y": str(y + 16), "font-size": "16", "font-weight": "bold"},
    )
    title.text = dungeon.name
    for i, room in enumerate(dungeon.rooms):
        entry = ET.SubElement(
            g,
            "text",
            {
                "x": str(x),
                "y": str(y + 44 + i * LEGEND_LINE_HEIGHT),
                "font-size": "14",
            },
        )
        entry.text = f"{numbers[room.id]}. {room.name}"
    return g


def _room_rect(p: Placement) -> tuple[float, float, float, float]:
    """Returns (left, top, right, bottom) in world coordinates."""
    rw, rh = SIZE_DIMS[p.room.size]
    left = p.x * CELL_SIZE + (CELL_SIZE - rw) / 2
    top = p.y * CELL_SIZE + (CELL_SIZE - rh) / 2
    return left, top, left + rw, top + rh


def render_room(
    hatch_layer: ET.Element, floor_layer: ET.Element, placement: Placement, number: int
) -> None:

    rng = random.Random(placement.room.name)
    x0, y0 = ROOM_X, ROOM_Y
    rw, rh = SIZE_DIMS[placement.room.size]
    x1 = ROOM_X + rw
    y1 = ROOM_Y + rh

    left, top, _, _ = _room_rect(placement)
    tf = f"translate({left - ROOM_X}, {top - ROOM_Y})"

    hatch = ET.SubElement(hatch_layer, "g", {"transform": tf})
    hatch_edge(hatch, x0, y0, x1, y0, 0, -1, rng)
    hatch_edge(hatch, x1, y0, x1, y1, 1, 0, rng)
    hatch_edge(hatch, x0, y1, x1, y1, 0, 1, rng)
    hatch_edge(hatch, x0, y0, x0, y1, -1, 0, rng)

    floor = ET.SubElement(floor_layer, "g", {"transform": tf})
    ET.SubElement(
        floor,
        "rect",
        {
            "x": str(x0),
            "y": str(y0),
            "width": str(rw),
            "height": str(rh),
            "fill": "white",
            "stroke": "black",
            "stroke-width": "2",
        },
    )

    text = ET.SubElement(
        floor,
        "text",
        {
            "x": str(ROOM_X + rw / 2),
            "y": str(ROOM_Y + rh / 2 + 7),
            "text-anchor": "middle",
            "font-family": FONT,
            "font-style": "italic",
            "font-size": "20",
        },
    )
    text.text = str(number)


def render_door(
    hatch_layer: ET.Element,
    floor_layer: ET.Element,
    source: Placement,
    target: Placement,
    door: Door,
    route: Route,
) -> None:

    if route == "skip":
        return

    cell_dx, cell_dy = target.x - source.x, target.y - source.y

    rng = random.Random("-".join(sorted((source.room.id, target.room.id))))

    # get the left/top/right/bottom of both rooms
    sl, st, sr, sb = _room_rect(source)
    tl, tt, tr, tb = _room_rect(target)
    width = min(CORRIDOR_WIDTHS[source.room.size], CORRIDOR_WIDTHS[target.room.size])

    # diagonal: L-shaped corridor through a corner cell
    if route == "v-first" or route == "h-first":
        sw, sh = SIZE_DIMS[source.room.size]
        tw, th = SIZE_DIMS[target.room.size]
        margin = 24
        if route == "v-first":
            p0 = (
                sr - min(margin, sw / 3) if cell_dx > 0 else sl + min(margin, sw / 3),
                sb if cell_dy > 0 else st,
            )
            p2 = (
                tl if cell_dx > 0 else tr,
                tt + min(margin, th / 3) if cell_dy > 0 else tb - min(margin, th / 3),
            )
            p1 = (p0[0], p2[1])

        elif route == "h-first":
            # horizontal-first: leave source's e/w wall, bend, enter target's n/s wall
            p0 = (
                sr if cell_dx > 0 else sl,
                sb - min(margin, sh / 3) if cell_dy > 0 else st + min(margin, sh / 3),
            )
            p2 = (
                tl + min(margin, tw / 3) if cell_dx > 0 else tr - min(margin, tw / 3),
                tt if cell_dy > 0 else tb,
            )
            p1 = (p2[0], p0[1])

        render_corridor(hatch_layer, floor_layer, door, rng, [p0, p1, p2], width)
        return

    # straight: wall-to-wall, may span inserted-gap cells but never a room
    if cell_dx:
        west, east = (source, target) if source.x < target.x else (target, source)
        _, _, wr, _ = _room_rect(west)
        el, _, _, _ = _room_rect(east)
        a = (wr, (st + sb) / 2)
        b = (el, a[1])
    else:
        north, south = (source, target) if source.y < target.y else (target, source)
        _, _, _, nb = _room_rect(north)
        _, sot, _, _ = _room_rect(south)
        a = ((sl + sr) / 2, nb)
        b = (a[0], sot)

    render_corridor(hatch_layer, floor_layer, door, rng, [a, b], width)


def render_corridor(
    hatch_layer: ET.Element,
    floor_layer: ET.Element,
    door: Door,
    rng: random.Random,
    pts: list[tuple[float, float]],
    width: int,
) -> None:
    """Draw a corridor along an axis-aligned polyline (2 points = straight,
    3 = one bend): white floor strip of width, walls and hatching
    down both sides, door glyph on the longest segment.
    """
    half = width / 2
    units = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        units.append(((x2 - x1) / length, (y2 - y1) / length))

    hatch = ET.SubElement(hatch_layer, "g")
    floor = ET.SubElement(floor_layer, "g")

    # offset the centerline by +/-half; at a 90-degree bend the mitered
    # corner is the point offset by both segments' normals at once
    sides = {}
    for s in (-1, 1):
        path = []
        for i, (x, y) in enumerate(pts):
            nx = ny = 0.0
            if i > 0:
                nx += -units[i - 1][1] * s
                ny += units[i - 1][0] * s
            if i < len(units):
                nx += -units[i][1] * s
                ny += units[i][0] * s
            path.append((x + nx * half, y + ny * half))
        sides[s] = path
        for i, u in enumerate(units):
            hatch_edge(
                hatch,
                path[i][0],
                path[i][1],
                path[i + 1][0],
                path[i + 1][1],
                -u[1] * s,
                u[0] * s,
                rng,
            )

    # floor polygon: one offset path out, the other back, with the ends
    # pushed 2px into the rooms so the wall openings are cut cleanly
    def extended(path: list[tuple[float, float]]) -> list[tuple[float, float]]:
        p = list(path)
        p[0] = (p[0][0] - units[0][0] * 2, p[0][1] - units[0][1] * 2)
        p[-1] = (p[-1][0] + units[-1][0] * 2, p[-1][1] + units[-1][1] * 2)
        return p

    ring = extended(sides[1]) + extended(sides[-1])[::-1]
    ET.SubElement(
        floor,
        "polygon",
        {
            "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in ring),
            "fill": "white",
        },
    )
    for s in (-1, 1):
        ET.SubElement(
            floor,
            "polyline",
            {
                "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in sides[s]),
                "fill": "none",
                "stroke": "black",
                "stroke-width": "2",
            },
        )

    longest = max(range(len(units)), key=lambda i: math.dist(pts[i], pts[i + 1]))
    mx = (pts[longest][0] + pts[longest + 1][0]) / 2
    my = (pts[longest][1] + pts[longest + 1][1]) / 2
    angle = math.degrees(math.atan2(units[longest][1], units[longest][0]))
    add_door_glyph(floor, door, mx, my, angle, width)


def add_door_glyph(
    g: ET.Element, door: Door, cx: float, cy: float, angle: float, width: int
) -> None:
    """Door marker at (cx, cy); angle is the corridor's direction in degrees."""
    if door.type == "archway":
        return  # open passage, no glyph

    if door.type == "secret":
        s = ET.SubElement(
            g,
            "text",
            {
                "x": f"{cx}",
                "y": f"{cy + 4}",
                "text-anchor": "middle",
                "font-family": FONT,
                "font-style": "italic",
                "font-size": "13",
            },
        )
        s.text = "S"
        return

    # physical door: a rectangle straddling the corridor, wider than it,
    # drawn axis-aligned then rotated to match the corridor's direction
    grp = ET.SubElement(
        g, "g", {"transform": f"rotate({angle:.1f}, {cx:.2f}, {cy:.2f})"}
    )
    along, across = 8, width + 8
    ET.SubElement(
        grp,
        "rect",
        {
            "x": f"{cx - along / 2:.2f}",
            "y": f"{cy - across / 2:.2f}",
            "width": f"{along}",
            "height": f"{across}",
            "fill": "white",
            "stroke": "black",
            "stroke-width": "1.5",
        },
    )
    if door.state == "locked":
        ET.SubElement(
            grp,
            "circle",
            {"cx": f"{cx:.2f}", "cy": f"{cy:.2f}", "r": "2", "fill": "black"},
        )


def hatch_edge(
    parent: ET.Element,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    nx: float,
    ny: float,
    rng: random.Random,
    overshoot: float = 4.0,
) -> None:
    """Scatter short 'hand-drawn' ticks along the outside of an edge
    (nx, ny) -> outward normal
    """

    edge_len = math.hypot(x2 - x1, y2 - y1)
    dx, dy = (x2 - x1) / edge_len, (y2 - y1) / edge_len

    spacing, base_len = 3.2, 15.0
    clump_t = rng.uniform(-overshoot, 0.0)
    direction = rng.choice((-1, 1))
    prev_spine = None  # last stroke of the previous clump: (bx, by, ux, uy, length)

    while clump_t < edge_len + overshoot:
        clump_slant = direction * rng.uniform(0.68, 0.88)
        t = clump_t
        n_ticks = rng.randint(4, 6)
        for i in range(n_ticks):
            is_spine = i == n_ticks - 1
            slant = clump_slant + rng.uniform(-0.04, 0.04)
            ux = nx * math.cos(slant) - ny * math.sin(slant)
            uy = nx * math.sin(slant) + ny * math.cos(slant)

            bx = x1 + dx * t + nx * rng.uniform(-1.5, 0.5)
            by = y1 + dy * t + ny * rng.uniform(-1.5, 0.5)

            if t > edge_len + overshoot:
                break

            if is_spine:
                tick = base_len * rng.uniform(1.5, 1.9)
            else:
                tick = base_len + rng.uniform(-3.0, 3.0)
            if prev_spine is not None:
                tick = clip_to_spine(bx, by, ux, uy, tick, prev_spine)

            if tick > 1.5:  # skip nubs clipped down to nothing
                ET.SubElement(
                    parent,
                    "line",
                    {
                        "x1": f"{bx:.2f}",
                        "y1": f"{by:.2f}",
                        "x2": f"{bx + ux * tick:.2f}",
                        "y2": f"{by + uy * tick:.2f}",
                        "stroke-width": f"{rng.uniform(0.8, 1.3):.2f}",
                    },
                )
            if is_spine:
                prev_spine = (bx, by, ux, uy, tick)
            t += rng.uniform(spacing * 0.7, spacing * 1.3)

        # overlap the next clump into this one's tail, but never let it
        # start behind this one's start — guarantees forward progress
        clump_t = max(t - rng.uniform(1.0, 3.0), clump_t + spacing)
        direction = -direction


def clip_to_spine(
    bx: float,
    by: float,
    ux: float,
    uy: float,
    tick: float,
    spine: tuple[float, float, float, float, float],
) -> float:
    """Shorten a tick so it ends where it first crosses the spine segment.

    Tick is the ray B + s*u, spine the segment P + r*v. Solving
    B + s*u = P + r*v by Cramer's rule gives s and r as ratios of 2D
    cross products. Clip only if the hit is inside both: 0 < s < tick
    along the ray, and r within the spine (with a little slack so ticks
    can land right at its ends).
    """
    px, py, vx, vy, vlen = spine
    denom = ux * vy - uy * vx
    if abs(denom) < 1e-9:  # parallel — same-lean clumps in a row never clip
        return tick
    wx, wy = px - bx, py - by
    s = (wx * vy - wy * vx) / denom
    r = (wx * uy - wy * ux) / denom
    if 0.5 < s < tick and -1.0 < r < vlen + 1.5:
        return s
    return tick
