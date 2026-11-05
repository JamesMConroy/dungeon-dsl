"""Experiment: what ruamel.yaml round-trip `.lc` gives. Run with: uv run --with ruamel.yaml python exp4_ruamel_lc.py"""
from ruamel.yaml import YAML
import ruamel.yaml

SRC = """\
defaults: &door
  type: wooden
rooms:
  - id: a
    exits:
      - <<: *door
        target: b
      - {target: c, direction: up}
"""
y = YAML()  # typ='rt'
d = y.load(SRC)
print("ruamel", ruamel.yaml.__version__)
rooms = d["rooms"]
print("rooms seq item 0 (line,col):", rooms.lc.item(0))
ex = rooms[0]["exits"]
print("exit 0 key 'target':", ex[0].lc.key("target"), "value:", ex[0].lc.value("target"))
try:
    print("exit 0 merged key 'type':", ex[0].lc.key("type"))
except Exception as e:
    print("exit 0 merged key 'type' ->", type(e).__name__, e)
print("flow exit 1 'direction' value:", ex[1].lc.value("direction"))
print("scalar has position attr?", hasattr(ex[1]["direction"], "lc"), type(ex[1]["direction"]))
print("isinstance dict:", isinstance(d, dict), type(d).__mro__[:3])
