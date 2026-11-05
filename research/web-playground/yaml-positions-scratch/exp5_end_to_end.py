"""End-to-end sketch: YAML text -> list of diagnostics {line, col, end_line, end_col, msg} (1-based).

Uses a scratch subclass of the real Dungeon model whose semantic validator raises a located
ValidationError, to show the pattern without touching package code.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from pydantic import ValidationError, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

sys.path.insert(0, "/Users/james.conroy/Projects/personal/dungeon-dsl")
from dungeon_dsl import models  # noqa: E402

MERGE_TAG = "tag:yaml.org,2002:merge"


@dataclass
class Diagnostic:
    line: int
    col: int
    end_line: int
    end_col: int
    msg: str


def _mapping_lookup(node: MappingNode, key: str) -> tuple[Node, Node] | None:
    # Explicit keys win over merged ones; last duplicate wins (matches PyYAML construction).
    hit = None
    for k, v in node.value:
        if isinstance(k, ScalarNode) and k.tag != MERGE_TAG and k.value == key:
            hit = (k, v)
    if hit:
        return hit
    for k, v in node.value:
        if k.tag == MERGE_TAG:
            for src in (v.value if isinstance(v, SequenceNode) else [v]):
                if isinstance(src, MappingNode) and (hit := _mapping_lookup(src, key)):
                    return hit
    return None


def locate(root: Node, loc: tuple[int | str, ...]) -> tuple[Node, bool]:
    """Walk loc; return (best node, exact?). For a mapping hit, return the *value* node,
    except when the walk stops early: then return the deepest key node reached (nicer squiggle)."""
    node, anchor = root, root
    for part in loc:
        if isinstance(node, MappingNode) and (hit := _mapping_lookup(node, str(part))):
            anchor, node = hit[0], hit[1]
        elif isinstance(node, SequenceNode) and isinstance(part, int) and 0 <= part < len(node.value):
            node = anchor = node.value[part]
        else:
            # missing field / union-tag segment / past a scalar
            return anchor, False
    return node, True


def _span(node: Node) -> tuple[int, int, int, int]:
    s, e = node.start_mark, node.end_mark
    if isinstance(node, ScalarNode):
        return s.line + 1, s.column + 1, e.line + 1, e.column + 1
    # Containers' end_mark points at the *next* token (often next line); clamp to first line.
    return s.line + 1, s.column + 1, s.line + 1, s.column + 2


def diagnose(src: str, model=models.Dungeon) -> tuple[object | None, list[Diagnostic]]:
    loader = yaml.SafeLoader(src)
    try:
        root = loader.get_single_node()
        data = loader.construct_document(root) if root is not None else None
    except yaml.MarkedYAMLError as e:
        m = e.problem_mark or e.context_mark
        line, col = (m.line + 1, m.column + 1) if m else (1, 1)
        return None, [Diagnostic(line, col, line, col + 1, f"{e.context or ''} {e.problem or ''}".strip())]
    finally:
        loader.dispose()
    try:
        return model.model_validate(data), []
    except ValidationError as ve:
        out = []
        for err in ve.errors(include_url=False):
            node, exact = locate(root, err["loc"]) if root is not None else (None, False)
            span = _span(node) if node is not None else (1, 1, 1, 2)
            out.append(Diagnostic(*span, err["msg"]))
        return None, out


class LocatedDungeon(models.Dungeon):
    """Pattern: semantic checks collect *all* problems and raise one ValidationError with precise locs."""

    @model_validator(mode="after")
    def check_door_targets(self):  # overrides the parent's same-named validator
        ids = {r.id for r in self.rooms}
        errs = [
            InitErrorDetails(
                type=PydanticCustomError("unknown_room", "unknown room '{target}'", {"target": d.target}),
                loc=("rooms", ri, "exits", di, "target"),
                input=d.target,
            )
            for ri, r in enumerate(self.rooms)
            for di, d in enumerate(r.exits)
            if d.target not in ids
        ]
        if errs:
            raise ValidationError.from_exception_data(type(self).__name__, errs)
        return self


SRC = """\
name: Demo
rooms:
  - id: a
    name: A
    entrance: true
    exits:
      - {target: b, direction: n}
      - {target: ghost, direction: s}
  - id: b
    name: B
    exits:
      - target: phantom
        direction: s
"""

if __name__ == "__main__":
    for label, src, model in [
        ("stock model, semantic err", SRC, models.Dungeon),
        ("located model, semantic err", SRC, LocatedDungeon),
        ("type error + missing field", SRC.replace("    name: B\n", "").replace("direction: n", "direction: 7"), LocatedDungeon),
        ("syntax error", SRC.replace("  - id: b", " - id: b"), LocatedDungeon),
    ]:
        print("==", label)
        _, diags = diagnose(src, model)
        for d in diags:
            print("  ", d)
