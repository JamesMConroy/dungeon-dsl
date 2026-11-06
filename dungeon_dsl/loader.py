"""`load(text) -> Result`: the single entry point from YAML text to a Dungeon.

Three phases, each of which stops the next when it finds an Error: YAML parse,
pydantic structure, then the dungeon-level rules in `check` (ADR 0001).
"""

from __future__ import annotations

import re
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.reader import ReaderError

from dungeon_dsl.models import Dungeon

_LINE_BREAK = re.compile("\r\n|[\r\n\x85  ]")

# These Problems are about the key itself, so its value's position would mislead.
_ANCHORED_ON_KEY = {
    "pydantic.extra_forbidden",
    "pydantic.invalid_key",
    "dungeon.no_entrance",
}


class Position(BaseModel):
    """Line and column, both 1-based. Columns count code points."""

    model_config = ConfigDict(extra="forbid")

    line: int
    col: int


class Span(BaseModel):
    """The end position is exclusive."""

    model_config = ConfigDict(extra="forbid")

    start: Position
    end: Position


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["error", "warning"]
    code: str
    message: str
    loc: list[str | int]
    span: Span | None = None


class Result(BaseModel):
    """`dungeon` is None whenever `problems` holds an Error."""

    model_config = ConfigDict(extra="forbid")

    dungeon: Dungeon | None
    problems: list[Problem]


def load(text: str) -> Result:
    try:
        root, data = _parse(text)
    except yaml.YAMLError as error:
        return Result(dungeon=None, problems=[_syntax_problem(error, text)])
    except RecursionError:
        return Result(dungeon=None, problems=[_too_deep_problem()])

    try:
        dungeon = Dungeon.model_validate(data)
    except ValidationError as error:
        problems = [_structural_problem(details) for details in error.errors()]
        return Result(dungeon=None, problems=_placed(problems, root, text))

    problems = _placed(check(dungeon), root, text)
    has_error = any(problem.severity == "error" for problem in problems)
    return Result(dungeon=None if has_error else dungeon, problems=problems)


def check(dungeon: Dungeon) -> list[Problem]:
    """The dungeon-level rules. Set each Problem's `loc`; `load` finds its span."""
    problems: list[Problem] = []
    entrance = next((room.id for room in dungeon.rooms if room.entrance), None)
    if entrance is None:
        problems.append(
            _error(
                "dungeon.no_entrance",
                "the dungeon needs a room with entrance: true",
                ["rooms"],
            )
        )

    known_ids = {room.id for room in dungeon.rooms}
    # No entrance is already one Problem, so don't also call every Room unreachable.
    reachable = known_ids if entrance is None else _reachable_from(entrance, dungeon)
    # Keyed by id, so Rooms that share an id share their Doors: the duplicate id is
    # already an Error, and a Warning on top of it would be noise.
    links = {(room.id, door.target) for room in dungeon.rooms for door in room.exits}
    seen_ids: set[str] = set()
    for index, room in enumerate(dungeon.rooms):
        if room.id in seen_ids:
            problems.append(
                _error(
                    "room.duplicate_id",
                    f"another room already has the id {room.id!r}",
                    ["rooms", index, "id"],
                )
            )
        seen_ids.add(room.id)
        if room.id not in reachable and not room.isolation:
            problems.append(
                _error(
                    "room.unreachable",
                    f"room {room.id!r} can't be reached from the entrance",
                    ["rooms", index, "id"],
                )
            )
        for door_index, door in enumerate(room.exits):
            if door.target not in known_ids:
                problems.append(
                    _error(
                        "door.unknown_target",
                        f"there is no room {door.target!r}",
                        ["rooms", index, "exits", door_index, "target"],
                    )
                )
            elif (door.target, room.id) not in links:
                problems.append(
                    _warning(
                        "door.one_way",
                        f"room {door.target!r} has no door back to {room.id!r}",
                        ["rooms", index, "exits", door_index, "target"],
                    )
                )
    return problems


def _reachable_from(entrance: str, dungeon: Dungeon) -> set[str]:
    """Room ids connected to the entrance. A Door connects both ways, if it leads anywhere."""
    neighbors: dict[str, set[str]] = {room.id: set() for room in dungeon.rooms}
    for room in dungeon.rooms:
        for door in room.exits:
            if door.target in neighbors:
                neighbors[room.id].add(door.target)
                neighbors[door.target].add(room.id)

    reachable = {entrance}
    stack = [entrance]
    while stack:
        for neighbor in neighbors[stack.pop()] - reachable:
            reachable.add(neighbor)
            stack.append(neighbor)
    return reachable


def _error(code: str, message: str, loc: list[str | int]) -> Problem:
    return Problem(severity="error", code=code, message=message, loc=loc)


def _warning(code: str, message: str, loc: list[str | int]) -> Problem:
    return Problem(severity="warning", code=code, message=message, loc=loc)


def _parse(text: str) -> tuple[Node | None, Any]:
    """One parse, keeping the node graph for positions and the data for pydantic."""
    loader = yaml.SafeLoader(text)
    try:
        root = loader.get_single_node()
        # Also flattens merge keys into the node graph, in place.
        data = None if root is None else loader.construct_document(root)
    finally:
        loader.dispose()
    return root, data


def _syntax_problem(error: yaml.YAMLError, text: str) -> Problem:
    at = None
    message = str(error)
    if isinstance(error, yaml.MarkedYAMLError) and error.problem_mark:
        mark = error.problem_mark
        at = Position(line=mark.line + 1, col=mark.column + 1)
        message = " ".join(filter(None, (error.context, error.problem)))
    elif isinstance(error, ReaderError):
        # The reader rejects bad characters before there are any marks to report.
        before = text[: error.position]
        breaks = list(_LINE_BREAK.finditer(before))
        line_start = breaks[-1].end() if breaks else 0
        at = Position(line=len(breaks) + 1, col=error.position - line_start + 1)
        message = str(error.reason)
    return Problem(
        severity="error",
        code="yaml.syntax",
        message=message,
        loc=[],
        span=Span(start=at, end=at) if at else None,
    )


def _too_deep_problem() -> Problem:
    return Problem(
        severity="error",
        code="yaml.syntax",
        message="the YAML is nested too deeply",
        loc=[],
    )


def _structural_problem(details: Any) -> Problem:
    return Problem(
        severity="error",
        code=f"pydantic.{details['type']}",
        message=details["msg"],
        loc=list(details["loc"]),
    )


def _placed(problems: list[Problem], root: Node | None, text: str) -> list[Problem]:
    return [
        problem.model_copy(update={"span": _span(problem, root, text)})
        for problem in problems
    ]


def _span(problem: Problem, root: Node | None, text: str) -> Span | None:
    if root is None:
        return None
    value, key = _walk(root, problem.loc)
    if key is not None and problem.code in _ANCHORED_ON_KEY:
        return _node_span(key, text)
    return _node_span(value, text)


def _walk(root: Node, loc: list[str | int]) -> tuple[Node, Node | None]:
    """The deepest node `loc` reaches, plus the key node that led to it if any."""
    node, key = root, None
    for part in loc:
        if isinstance(node, MappingNode):
            # Last match wins, as in PyYAML: explicit keys override merged ones.
            matches = [
                (k, v)
                for k, v in node.value
                if isinstance(k, ScalarNode) and k.value == str(part)
            ]
            if not matches:
                break
            key, node = matches[-1]
        elif (
            isinstance(node, SequenceNode)
            and isinstance(part, int)
            and 0 <= part < len(node.value)
        ):
            node, key = node.value[part], None
        else:
            break
    return node, key


def _node_span(node: Node, text: str) -> Span:
    start, end = node.start_mark, node.end_mark
    span_start = Position(line=start.line + 1, col=start.column + 1)
    if isinstance(node, ScalarNode) or end.line == start.line:
        return Span(
            start=span_start, end=Position(line=end.line + 1, col=end.column + 1)
        )
    # A container's end mark overshoots to the next token, so stop at its first line.
    line_break = _LINE_BREAK.search(text, start.index)
    stop = line_break.start() if line_break else len(text)
    return Span(
        start=span_start,
        end=Position(line=span_start.line, col=span_start.col + stop - start.index),
    )
