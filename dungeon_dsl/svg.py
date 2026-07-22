from .layout import Placement, compute_layout
from .models import Door, Dungeon
import xml.etree.ElementTree as ET
import math
import random

CELL_SIZE = (
    140  # px per grid cell — bigger than the 100x80 room so there's room for corridors
)

ROOM_X, ROOM_Y = 10, 10
ROOM_W, ROOM_H = 100, 80

PAD = 24  # breathing room so hatching isn't clipped at the map edges
LEGEND_WIDTH = 220
LEGEND_LINE_HEIGHT = 22
FONT = "Georgia, 'Times New Roman', serif"


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

    for placement in lay_out.placements.values():
        svg.append(render_room(placement, numbers[placement.room.id]))

    svg.append(
        render_legend(dungeon, numbers, x=min_x * CELL_SIZE + map_w + PAD, y=min_y * CELL_SIZE)
    )

    ET.indent(svg)
    return ET.tostring(svg, encoding="unicode")


def render_legend(dungeon: Dungeon, numbers: dict[str, int], x: float, y: float) -> ET.Element:
    g = ET.Element("g", {"font-family": FONT})
    title = ET.SubElement(g, "text", {"x": str(x), "y": str(y + 16), "font-size": "16", "font-weight": "bold"})
    title.text = dungeon.name
    for i, room in enumerate(dungeon.rooms):
        entry = ET.SubElement(g, "text", {
            "x": str(x), "y": str(y + 44 + i * LEGEND_LINE_HEIGHT), "font-size": "14",
        })
        entry.text = f"{numbers[room.id]}. {room.name}"
    return g


def render_room(placement: Placement, number: int) -> ET.Element:
    g = ET.Element(
        "g",
        {
            "transform": f"translate({placement.x * CELL_SIZE}, {placement.y * CELL_SIZE})"
        },
    )

    rng = random.Random(placement.room.name)
    x0, y0 = ROOM_X, ROOM_Y
    x1, y1 = ROOM_X + ROOM_W, ROOM_Y + ROOM_H

    hatch = ET.SubElement(g, "g", {"stroke": "black", "stroke-linecap": "round"})
    hatch_edge(hatch, x0, y0, x1, y0, 0, -1, rng)
    hatch_edge(hatch, x1, y0, x1, y1, 1, 0, rng)
    hatch_edge(hatch, x0, y1, x1, y1, 0, 1, rng)
    hatch_edge(hatch, x0, y0, x0, y1, -1, 0, rng)

    ET.SubElement(g, "rect", {"x": str(x0), "y": str(y0), "width": str(ROOM_W), "height": str(ROOM_H),
                              "fill": "white", "stroke": "black", "stroke-width": "2"})

    text = ET.SubElement(g, "text", {
        "x": str(ROOM_X + ROOM_W / 2), "y": str(ROOM_Y + ROOM_H / 2 + 7),
        "text-anchor": "middle", "font-family": FONT,
        "font-style": "italic", "font-size": "20",
    })
    text.text = str(number)
    return g


def render_door(source: Placement, target: Placement, door: Door) -> str:
    return ""

def hatch_edge(
    parent: ET.Element,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    nx: float,
    ny: float,
    rng: random.Random,
) -> None:
    """Scatter short 'hand-drawn' ticks along the outside of an edge
    (nx, ny) -> outward normal
    """

    edge_len = math.hypot(x2 - x1, y2 - y1)
    dx, dy = (x2 - x1) /edge_len, (y2- y1) / edge_len

    spacing, base_len  = 3.2, 15.0
    clump_t = rng.uniform(-4.0, 0.0)
    direction = rng.choice((-1, 1))
    prev_spine = None  # last stroke of the previous clump: (bx, by, ux, uy, length)

    while clump_t < edge_len + 4.0:
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

            if is_spine:
                tick = base_len * rng.uniform(1.5, 1.9)
            else:
                tick = base_len + rng.uniform(-3.0, 3.0)
            if prev_spine is not None:
                tick = clip_to_spine(bx, by, ux, uy, tick, prev_spine)

            if tick > 1.5:  # skip nubs clipped down to nothing
                ET.SubElement(parent, "line", {
                    "x1": f"{bx:.2f}",
                    "y1": f"{by:.2f}",
                    "x2": f"{bx + ux * tick:.2f}",
                    "y2": f"{by + uy * tick:.2f}",
                    "stroke-width": f"{rng.uniform(0.8, 1.3):.2f}"
                })
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

