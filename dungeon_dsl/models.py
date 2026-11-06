from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Direction = Literal["n", "s", "e", "w", "ne", "nw", "se", "sw"]
RoomSize = Literal["tiny", "small", "medium", "large", "vast"]
Light = Literal["dark", "dim", "bright"]
DoorType = Literal["wooden", "stone", "iron", "secret", "archway"]
DoorState = Literal["open", "closed", "locked", "barred"]


class Door(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    direction: Direction
    type: DoorType = "wooden"
    state: DoorState = "closed"
    dc: int | None = None


class Room(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    size: RoomSize = "medium"
    terrain: str = ""
    light: Light = "dark"
    entrance: bool = False
    isolation: bool = False
    exits: list[Door] = Field(default_factory=list)


class Dungeon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    level: int | None = None
    theme: str | None = None
    rooms: list[Room]

    @model_validator(mode="after")
    def check_unique_ids(self) -> Dungeon:
        ids = [r.id for r in self.rooms]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate room ids: {sorted(dupes)}")
        return self

    @model_validator(mode="after")
    def check_door_targets(self) -> Dungeon:
        ids = {r.id for r in self.rooms}
        for room in self.rooms:
            for door in room.exits:
                if door.target not in ids:
                    raise ValueError(
                        f"room {room.id!r} has a door targeting unknown room {door.target!r}"
                    )
        return self

    @model_validator(mode="after")
    def check_entrance(self) -> Dungeon:
        if not any(r.entrance for r in self.rooms):
            raise ValueError("dungeon must have at least one room with entrance: true")
        return self

    @model_validator(mode="after")
    def check_connectivity(self) -> Dungeon:
        by_id = {r.id: r for r in self.rooms}
        adjacency: dict[str, set[str]] = {r.id: set() for r in self.rooms}
        for room in self.rooms:
            for door in room.exits:
                adjacency[room.id].add(door.target)
                adjacency[door.target].add(room.id)

        entrance = next(r.id for r in self.rooms if r.entrance)
        seen = {entrance}
        stack = [entrance]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        unreachable = [
            r.id for r in self.rooms if r.id not in seen and not by_id[r.id].isolation
        ]
        if unreachable:
            raise ValueError(f"rooms unreachable from entrance: {sorted(unreachable)}")
        return self
