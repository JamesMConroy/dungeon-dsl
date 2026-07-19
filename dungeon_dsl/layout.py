from dataclasses import dataclass
from collections import deque

from .models import Room, Dungeon


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

    queue: deque[str] = deque([entrance.id])
    while queue:
        current_id = queue.popleft()
        current = placements[current_id]

        for door in by_id[current_id].exits:
            if door.target in placements:
                continue
            dx, dy = DIRECTION_OFFSET[door.direction]
            ideal_cell = (current.x + dx, current.y + dy)
            t = by_id[door.target]
            placements[t.id] = Placement(room=t, x=ideal_cell[0], y=ideal_cell[1])
            queue.append(door.target)

    return Layout(placements)
