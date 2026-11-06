from collections import deque
from dataclasses import dataclass

from .models import Dungeon, Room


@dataclass
class Placement:
    room: Room
    x: int
    y: int


@dataclass
class Layout:
    placements: dict[str, Placement]  # keyed by room id


DIRECTION_OFFSET = {
    "n": (0, -1),
    "s": (0, 1),
    "e": (1, 0),
    "w": (-1, 0),
    "ne": (1, -1),
    "nw": (-1, -1),
    "se": (1, 1),
    "sw": (-1, 1),
}


def compute_layout(dungeon: Dungeon) -> Layout:
    placements: dict[str, Placement] = {}
    by_id: dict[str, Room] = {}

    entrance: Room | None = None

    for r in dungeon.rooms:
        by_id[r.id] = r
        if r.entrance and entrance is None:
            placements[r.id] = Placement(room=r, x=0, y=0)
            entrance = r

    assert entrance is not None

    # edges between placed rooms; their straight corridor paths count as
    # blocked cells so later rooms can't be dropped on top of a corridor
    edges: list[tuple[str, str]] = []

    _place_through_doors(entrance, dungeon, by_id, placements, edges)

    # Rooms no Door leads to from the entrance: isolated ones, and ones joined only
    # by their own one-way Door. Each starts its own group on a fresh row below.
    for room in dungeon.rooms:
        if room.id not in placements:
            x = min(p.x for p in placements.values())
            y = max(p.y for p in placements.values()) + 2
            placements[room.id] = Placement(room=room, x=x, y=y)
            _place_through_doors(room, dungeon, by_id, placements, edges)

    return Layout(placements)


def _place_through_doors(
    start: Room,
    dungeon: Dungeon,
    by_id: dict[str, Room],
    placements: dict[str, Placement],
    edges: list[tuple[str, str]],
) -> None:
    """Breadth-first from the already placed `start`, along each Door's direction."""
    queue: deque[str] = deque([start.id])
    while queue:
        current_id = queue.popleft()

        for door in by_id[current_id].exits:
            if door.target in placements:
                edges.append((current_id, door.target))
                continue
            dx, dy = DIRECTION_OFFSET[door.direction]

            # if the ideal cell is taken, insert an empty row/column along
            # the door's axis to open space: rooms past the contested line
            # shift by one, previously-adjacent pairs become collinear with
            # an empty cell between (rendered as a longer corridor)
            tx, ty = 0, 0
            for _ in range(len(dungeon.rooms)):
                current = placements[current_id]
                tx, ty = current.x + dx, current.y + dy
                if (tx, ty) not in _blocked_cells(placements, edges):
                    break
                if dx:
                    _insert_gap(placements, "x", tx, dx)
                else:
                    _insert_gap(placements, "y", ty, dy)

            t = by_id[door.target]
            placements[t.id] = Placement(room=t, x=tx, y=ty)
            edges.append((current_id, t.id))
            queue.append(t.id)


def _insert_gap(
    placements: dict[str, Placement], axis: str, coord: int, sign: int
) -> None:
    """Shift every room at or past `coord` (in `sign` direction) by one cell."""
    for p in placements.values():
        v = getattr(p, axis)
        if (v - coord) * sign >= 0:
            setattr(p, axis, v + sign)


def _blocked_cells(
    placements: dict[str, Placement], edges: list[tuple[str, str]]
) -> set[tuple[int, int]]:
    cells = {(p.x, p.y) for p in placements.values()}
    for a, b in edges:
        pa, pb = placements[a], placements[b]
        if pa.x == pb.x:
            for y in range(min(pa.y, pb.y) + 1, max(pa.y, pb.y)):
                cells.add((pa.x, y))
        elif pa.y == pb.y:
            for x in range(min(pa.x, pb.x) + 1, max(pa.x, pb.x)):
                cells.add((x, pa.y))
        elif abs(pa.x - pb.x) == 1 and abs(pa.y - pb.y) == 1:
            # a diagonal edge renders as an L through one of the two corner
            # cells; reserve both since the renderer picks at draw time
            cells.add((pa.x, pb.y))
            cells.add((pb.x, pa.y))
    return cells
