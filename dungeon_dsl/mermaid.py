from __future__ import annotations

from .models import Dungeon, Room

LIGHT_LABEL = {
    "dark": "🌑",
    "dim": "🌘",
    "bright": "☀️",
}


def _node_label(room: Room) -> str:
    light = LIGHT_LABEL.get(room.light, "")
    prefix = "▶ " if room.entrance else ""
    return f"{room.id}[\"{prefix}{light} {room.name}\"]"


def _edge_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def render_mermaid(dungeon: Dungeon) -> str:
    # mermaid-ascii (our fast local preview tool) only understands plain
    # node declarations and solid `-->` edges: no style/classDef/:::class
    # and no dashed `-.->`. Keep the output to that subset and fold any
    # extra info (secret doors, entrance, light) into labels instead.
    lines = ["flowchart TD"]

    for room in dungeon.rooms:
        lines.append(f"    {_node_label(room)}")

    seen_edges: set[tuple[str, str]] = set()
    for room in dungeon.rooms:
        for door in room.exits:
            key = _edge_key(room.id, door.target)
            if key in seen_edges:
                continue
            seen_edges.add(key)

            label = f"{door.direction}/{door.type}/{door.state}"
            if door.type == "secret":
                label += " 🔒"
            lines.append(f"    {room.id} -->|{label}| {door.target}")

    return "\n".join(lines)
