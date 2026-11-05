"""Experiment: YAML syntax-error marks; compose+construct in one parse; mapping end marks."""
import yaml

BAD = [
    "name: x\nrooms:\n  - id: a\n   name: b\n",       # bad indent
    "name: [unclosed\n",                              # flow unclosed
    "a: b: c\n",                                      # mapping values not allowed
    "a: *nope\n",                                     # undefined alias (composer)
    "a: 1\n\tb: 2\n",                                 # tab
    "a: 'x\n",                                        # unterminated quote
    "--- a\n--- b\n",                                 # multiple docs w/ single loader
]
for src in BAD:
    try:
        L = yaml.SafeLoader(src)
        try:
            L.get_single_node()
        finally:
            L.dispose()
    except yaml.MarkedYAMLError as e:
        pm, cm = e.problem_mark, e.context_mark
        print(repr(src[:20]), type(e).__name__, "|", e.problem, "| problem@",
              (pm.line + 1, pm.column + 1, pm.index) if pm else None,
              "| context:", e.context, (cm.line + 1, cm.column + 1) if cm else None)
    except yaml.YAMLError as e:
        print(repr(src[:20]), "unmarked", type(e).__name__, e)

print("--- single parse: compose then construct from the same loader")
SRC = "name: X\nrooms:\n  - id: a\n    name: A\n  - id: b\n    name: B\n\nfoo: 1\n"
L = yaml.SafeLoader(SRC)
try:
    node = L.get_single_node()
    data = L.construct_document(node)
finally:
    L.dispose()
print(data)
rooms = node.value[1][1]
for item in rooms.value:
    print("room mapping", (item.start_mark.line + 1, item.start_mark.column + 1), "->",
          (item.end_mark.line + 1, item.end_mark.column + 1))
print("key node for 'rooms'", node.value[1][0].start_mark.line + 1, node.value[1][0].start_mark.column + 1)

print("--- duplicate keys: PyYAML last-wins silently?")
print(yaml.safe_load("a: 1\na: 2\n"))

print("--- non-ASCII: column/index are in code points")
n = yaml.compose("é🐉: x\nk: bad\n")
k, v = n.value[0]
print("value col", v.start_mark.column, "index", v.start_mark.index)
print("cext available:", yaml.__with_libyaml__)
