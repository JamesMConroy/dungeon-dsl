"""Experiment: walk a pydantic loc tuple through a PyYAML composed node graph."""
import yaml
from yaml.nodes import MappingNode, SequenceNode, ScalarNode
from pydantic import BaseModel, ValidationError, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError
import sys
sys.path.insert(0, "/Users/james.conroy/Projects/personal/dungeon-dsl")
from dungeon_dsl.models import Dungeon

SRC = """\
name: Test
defaults: &door
  type: wooden
  state: closed
rooms:
  - id: a
    name: A
    entrance: true
    exits:
      - target: b
        direction: n
      - {target: b, direction: up}
  - id: b
    name: B
    exits:
      - <<: *door
        target: a
        direction: s
        dc: notanint
  - id: c
    name: C
    exits: [{target: nowhere, direction: s}]
"""


def walk(node, loc):
    """Return (node, consumed_prefix_len). Stops at deepest resolvable node."""
    for i, part in enumerate(loc):
        if isinstance(node, MappingNode):
            # merge keys: also look inside '<<' values (PyYAML keeps raw '<<' in composed graph)
            found = None
            for k, v in node.value:
                if isinstance(k, ScalarNode) and k.value == str(part):
                    found = (k, v)
            if found is None:
                for k, v in node.value:
                    if k.tag == "tag:yaml.org,2002:merge":
                        srcs = v.value if isinstance(v, SequenceNode) else [v]
                        for s in srcs:
                            for kk, vv in s.value:
                                if kk.value == str(part):
                                    found = (kk, vv)
            if found is None:
                return node, i
            node = found[1]
        elif isinstance(node, SequenceNode) and isinstance(part, int):
            if not 0 <= part < len(node.value):
                return node, i
            node = node.value[part]
        else:
            return node, i
    return node, len(loc)


root = yaml.compose(SRC)
data = yaml.safe_load(SRC)
for item in [("rooms", 1, "exits", 0, "dc"), ("rooms", 1, "exits", 0, "type"), ("rooms", 0, "exits", 1, "direction"), ("rooms", 2, "exits", 0, "target")]:
    n, used = walk(root, item)
    print(item, "->", type(n).__name__, f"L{n.start_mark.line+1}:C{n.start_mark.column+1}", "-", f"L{n.end_mark.line+1}:C{n.end_mark.column+1}", "used", used, repr(getattr(n, 'value', None) if isinstance(n, ScalarNode) else '...'))

print("--- pydantic errors on this doc")
try:
    Dungeon.model_validate(data)
except ValidationError as e:
    for err in e.errors():
        n, used = walk(root, err["loc"])
        print(err["loc"], err["type"], err["msg"][:60], "->", f"L{n.start_mark.line+1}:C{n.start_mark.column+1}")

print("--- alias identity: same node object reused?")
src2 = "a: &x {k: 1}\nb: *x\n"
r2 = yaml.compose(src2)
print(r2.value[0][1] is r2.value[1][1], r2.value[1][1].start_mark.line)

print("--- int-like keys / key 'on' types")
r3 = yaml.compose("1: a\non: b\n")
print([(k.tag, k.value) for k, _ in r3.value], yaml.safe_load("1: a\non: b\n"))
