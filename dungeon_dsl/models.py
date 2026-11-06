from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
