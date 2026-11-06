from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["n", "s", "e", "w", "ne", "nw", "se", "sw"]
RoomSize = Literal["tiny", "small", "medium", "large", "vast"]
Light = Literal["dark", "dim", "bright"]
DoorType = Literal["wooden", "stone", "iron", "secret", "archway"]
DoorState = Literal["open", "closed", "locked", "barred"]


class _ClosedModel(BaseModel):
    """Rejects keys it doesn't declare, so a misspelled key is a Problem."""

    model_config = ConfigDict(extra="forbid")


class Door(_ClosedModel):
    target: str
    direction: Direction
    type: DoorType = "wooden"
    state: DoorState = "closed"
    dc: int | None = None


class Room(_ClosedModel):
    id: str
    name: str
    description: str = ""
    size: RoomSize = "medium"
    terrain: str = ""
    light: Light = "dark"
    entrance: bool = False
    isolation: bool = False
    exits: list[Door] = Field(default_factory=list)


class Dungeon(_ClosedModel):
    name: str
    level: int | None = None
    theme: str | None = None
    rooms: list[Room]
