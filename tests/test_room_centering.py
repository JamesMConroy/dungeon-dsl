import re
import xml.etree.ElementTree as ET

import pytest

from dungeon_dsl.models import Dungeon, Room
from dungeon_dsl.svg import CELL_SIZE, ROOM_X, ROOM_Y, SIZE_DIMS, render_svg

SVG_NS = "http://www.w3.org/2000/svg"


def _minimal_dungeon(size: str) -> Dungeon:
    return Dungeon(
        name="Test",
        rooms=[
            Room.model_validate(
                {"id": "r1", "name": "Room 1", "size": size, "entrance": True}
            )
        ],
    )


def _parse_translate(transform: str) -> tuple[float, float]:
    m = re.match(r"translate\(([^,]+),\s*([^)]+)\)", transform)
    assert m, f"unexpected transform: {transform!r}"
    return float(m.group(1)), float(m.group(2))


@pytest.mark.parametrize("size,dims", SIZE_DIMS.items())
def test_room_centered_in_cell(size: str, dims: tuple[int, int]) -> None:
    rw, rh = dims
    root = ET.fromstring(render_svg(_minimal_dungeon(size)))

    # floor_layer is the second <g> child; it holds one <g transform="translate(...)"> per room
    floor_layer = root.findall(f"{{{SVG_NS}}}g")[1]
    room_g = floor_layer.find(f"{{{SVG_NS}}}g")
    assert room_g is not None

    tx, ty = _parse_translate(room_g.get("transform", ""))

    # Room at grid (0, 0) → cell center is (CELL_SIZE/2, CELL_SIZE/2).
    # Rect is drawn at (ROOM_X, ROOM_Y) in local space, so its world center is
    # (tx + ROOM_X + rw/2, ty + ROOM_Y + rh/2) and must equal the cell center.
    assert tx + ROOM_X + rw / 2 == pytest.approx(CELL_SIZE / 2), (
        f"size={size!r}: room not horizontally centered (tx={tx})"
    )
    assert ty + ROOM_Y + rh / 2 == pytest.approx(CELL_SIZE / 2), (
        f"size={size!r}: room not vertically centered (ty={ty})"
    )
