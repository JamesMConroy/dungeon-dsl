"""Experiment: can a model_validator raise an error with a precise loc?"""
from __future__ import annotations
from pydantic import BaseModel, ValidationError, model_validator, ValidationInfo
from pydantic_core import InitErrorDetails, PydanticCustomError


class Door(BaseModel):
    target: str


class Room(BaseModel):
    id: str
    exits: list[Door] = []


# A: raise ValidationError.from_exception_data from inside the validator
class DungeonA(BaseModel):
    rooms: list[Room]

    @model_validator(mode="after")
    def check(self) -> DungeonA:
        ids = {r.id for r in self.rooms}
        errs: list[InitErrorDetails] = []
        for ri, r in enumerate(self.rooms):
            for di, d in enumerate(r.exits):
                if d.target not in ids:
                    errs.append(InitErrorDetails(
                        type=PydanticCustomError("unknown_room", "unknown room {target!r}", {"target": d.target}),
                        loc=("rooms", ri, "exits", di, "target"),
                        input=d.target,
                    ))
        if errs:
            raise ValidationError.from_exception_data("Dungeon", errs)
        return self


# B: PydanticCustomError (loc stays at root)
class DungeonB(BaseModel):
    rooms: list[Room]

    @model_validator(mode="after")
    def check(self) -> DungeonB:
        raise PydanticCustomError("unknown_room", "unknown room")


data = {"rooms": [{"id": "a", "exits": [{"target": "x"}, {"target": "a"}, {"target": "y"}]}]}

for cls in (DungeonA, DungeonB):
    print("==", cls.__name__)
    try:
        cls.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            print("  ", err["loc"], err["type"], err["msg"])

# Nested: DungeonA used as a field of a wrapper -> is loc prefixed?
class Wrapper(BaseModel):
    dungeon: DungeonA

print("== nested")
try:
    Wrapper.model_validate({"dungeon": data})
except ValidationError as e:
    for err in e.errors():
        print("  ", err["loc"], err["type"], err["msg"])

# C: multiple model_validators -- does the 2nd run when the 1st fails?
class DungeonC(BaseModel):
    rooms: list[Room]

    @model_validator(mode="after")
    def one(self):
        raise ValueError("one")

    @model_validator(mode="after")
    def two(self):
        raise ValueError("two")

print("== chained after-validators")
try:
    DungeonC.model_validate(data)
except ValidationError as e:
    print("  ", [(x["loc"], x["msg"]) for x in e.errors()])

# D: field error + model validator: does model validator run if a field fails?
print("== field fails -> after validator?")
try:
    DungeonA.model_validate({"rooms": [{"id": 1, "exits": [{"target": "zz"}]}]})
except ValidationError as e:
    print("  ", [(x["loc"], x["msg"]) for x in e.errors()])
