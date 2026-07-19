from .layout import Placement, compute_layout
from .models import Door, Dungeon
import xml.etree.ElementTree as ET
import random

CELL_SIZE = (
    140  # px per grid cell — bigger than the 100x80 room so there's room for corridors
)


def render_svg(dungeon: Dungeon) -> str:
    lay_out = compute_layout(dungeon)

    xs = [p.x for p in lay_out.placements.values()]
    ys = [p.y for p in lay_out.placements.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"{min_x * CELL_SIZE} {min_y * CELL_SIZE} {(max_x - min_x + 1) * CELL_SIZE} {(max_y - min_y + 1) * CELL_SIZE}",
        },
    )

    defs = ET.SubElement(svg, "defs")

    for placement in lay_out.placements.values():
        svg.append(render_room(placement))

    render_hatch_pattern(defs)

    ET.indent(svg)
    return ET.tostring(svg, encoding="unicode")


def render_room(placement: Placement) -> ET.Element:
    g = ET.Element(
        "g",
        {
            "transform": f"translate({placement.x * CELL_SIZE}, {placement.y * CELL_SIZE})"
        },
    )
    ET.SubElement(g, "path", {
        "d": "M 10,10 L 110,10 L 110,90 L 10,90 Z M 18,18 L 102,18 L 102,82 L 18,82 Z",
        "fill": "url(#hatch)",
        "fill-rule": "evenodd",
    })
    text = ET.SubElement(g, "text", {"x": "60", "y": "50", "text-anchor": "middle"})
    text.text = placement.room.name
    return g


def render_door(source: Placement, target: Placement, door: Door) -> str:
    return ""

def render_hatch_pattern(defs: ET.Element) -> None:
    pattern = ET.SubElement(defs, "pattern", {
        "id": "hatch", "width": "16", "height": "16",
        "patternUnits": "userSpaceOnUse", "patternTransform": "rotate(45)",
    })

    def draw_lines(parent: ET.Element) -> None:
        for x in range(0, 16, 2):
            for y in range(0, 16, 2):
                length = random.uniform(2, 4)
                jx = x + random.uniform(-0.5, 0.5)
                jy = y + random.uniform(-0.5, 0.5)
                ET.SubElement(parent, "line", {
                    "x1": str(jx), "y1": str(jy), "x2": str(jx), "y2": str(jy + length),
                    "stroke": "black", "stroke-width": "1",
                })

    draw_lines(pattern)
    perpendicular = ET.SubElement(pattern, "g", {"transform": "rotate(90, 8, 8)"})
    draw_lines(perpendicular)
