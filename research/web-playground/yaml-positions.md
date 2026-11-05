# Position-preserving YAML: pydantic `loc` → YAML line/col in Pyodide

Researched 2026-11-05 for [issue 03](https://github.com/JamesMConroy/dungeon-dsl/issues/4).
Experiments live in [`yaml-positions-scratch/`](yaml-positions-scratch/) and run against the repo venv
(PyYAML 6.0.3, pydantic 2.13.4). `exp5_end_to_end.py` is the working prototype.

## TL;DR / recommendation

**Stay on PyYAML. Parse once with `yaml.SafeLoader`: `get_single_node()` → `construct_document(node)`.
Validate the constructed data with pydantic, then walk each error's `loc` through the node graph to get
a `start_mark`/`end_mark` span.** For whole-model checks, have the `model_validator` collect every
problem and **raise one `pydantic_core.ValidationError.from_exception_data(...)` with precise `loc`s**.
pydantic-core unwraps these into ordinary line errors, so they go through the same walk. Syntax
errors arrive as `yaml.MarkedYAMLError` with `problem_mark`/`context_mark`.

ruamel.yaml adds nothing we need. It gives only start positions (no end), it raises `KeyError` on merged
keys, and it pulls in another package. Skip it.

## Findings

### 1. Pyodide availability (primary source: Pyodide lock files on jsDelivr)

| Pyodide | Python | pyyaml | ruamel-yaml | pydantic / pydantic-core |
|---|---|---|---|---|
| `314.0.7` (npm `latest`) | 3.14.2 | 6.0.3 (wasm wheel) | 0.19.1 (pure) | **2.12.5 / 2.41.5** |
| `0.29.5` (npm `stable-0.29`) | 3.13.2 | 6.0.2 (wasm wheel) | 0.18.10 (pure) | 2.12.5 / 2.41.5 |

Sources: `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide-lock.json`,
`https://cdn.jsdelivr.net/pyodide/v0.29.5/full/pyodide-lock.json`, `https://registry.npmjs.org/pyodide` (dist-tags).

- Both YAML libraries ship in the Pyodide distribution, so either loads with `loadPackage`/micropip and
  needs no PyPI fetch. ruamel's PyPI metadata (0.19.1) makes the C ext (`clib`/`clibz`) opt-in extras only,
  so micropip of the pure wheel would also work (https://pypi.org/pypi/ruamel.yaml/json).
- **Surprise / risk outside this ticket:** the repo pins `pydantic>=2.13.4`, but Pyodide ships
  **2.12.5**. pydantic-core is a compiled wheel, so we can't micropip a newer one. The pin needs relaxing
  (or a split pin for the browser build), otherwise micropip dependency resolution fails. Pyodide also
  moved to CPython-based versioning (`314.x`).

### 2. PyYAML `compose` / node marks

- `yaml.compose()` "returns the root of the representation graph for the first document". `Mark.line` and
  `Mark.column` start "from 0" (https://pyyaml.org/wiki/PyYAMLDocumentation, sections *yaml package*
  and *Mark*). The docs give nodes the signature `ScalarNode(tag, value, style, start_mark, end_mark)` but
  don't describe node marks in prose. Behaviour below was verified by experiment (`exp1`, `exp3`).
- Scalar nodes have tight `start_mark`..`end_mark` spans, including in flow style:
  `{target: b, direction: up}` gives `up` at exactly L12:C32–34.
- **Container end marks are sloppy.** A block mapping's `end_mark` is the start of the *next* token,
  often the next item's `-` or a line after trailing blank lines (`exp3`: the room mapping spans
  (3,5)→(5,3)). For containers, clamp the squiggle to the first line, or put it on the key node.
- **Single parse:** `L = yaml.SafeLoader(src); root = L.get_single_node(); data = L.construct_document(root); L.dispose()`.
  This is what `safe_load` does internally, and it gives us the node graph without a second parse.
- **Aliases:** an alias resolves to the *same node object* as its anchor (`exp1`: `r.value[0][1] is r.value[1][1]`).
  An error inside aliased data therefore points at the **anchor definition**, not the `*alias` use site.
  That's semantically defensible ("the bad value lives here"), but it can surprise users. The alias use
  site isn't recoverable from the node graph, because the composer discards alias events.
- **Merge keys (`<<`):** `SafeConstructor.flatten_mapping` **mutates the node graph in place** during
  `construct_document`. It deletes the `<<` entry and prepends the merged `(key, value)` pairs, giving
  `node.value = merge + node.value`. See `yaml/constructor.py` `flatten_mapping` and `exp` inline check:
  `['<<','t']` → `[('type',0),('t',3)]`. If you walk the graph *after* construction, a "last match wins"
  key lookup reproduces PyYAML semantics exactly: explicit keys override merged ones, and duplicate keys
  are last-wins (`{'a': 2}` for `a: 1\na: 2`). Merged-key errors point at the anchor's key/value.
- **Key matching:** compare `key_node.value == str(loc_part)`. `loc` parts for model fields are field names
  (or aliases if we ever add `by_alias`). YAML 1.1 bool/int-looking keys (`on:`, `1:`) are a non-issue for
  our schema. They do collide in `safe_load` (`{1:'a', True:'b'}` → `{1: 'b'}`), which is a separate footgun.
- **Columns are code points.** `Mark.index`/`column` count Python str code points (`exp3`: `é🐉: x` puts the value at
  column 4). JS editors (CodeMirror/Monaco) index UTF-16 units, so astral characters (emoji) shift columns by 1
  each. Convert on the JS side, or send `Mark.index` and map it with `[...text]`. Confidence: medium. I didn't
  test this inside an editor.

### 3. pydantic `loc` shapes we'll see

- Field/type errors carry a full path: `('rooms', 1, 'exits', 0, 'dc')` → walked to `dc: notanint` (`exp1`).
- **Missing field:** the loc ends at a key that doesn't exist (`('rooms', 1, 'name')`). The walk stops early,
  so anchor on the deepest node reached, which is the room mapping (`exp5`: "Field required" at L9:C5).
- **Union members** add tag segments (e.g. `'int'`, `'function-after[...]'`) after the real path. The walk
  can't resolve them and stops at the scalar, which is the right result. `int | None` doesn't add one
  (verified: `dc` errors end at `'dc'`).
- **`model_validator`s report at the model's own loc, not a field.** `Door.check_direction` → `('rooms', 0, 'exits', 1)`
  (the whole door mapping). All four `Dungeon` validators → `()`, i.e. line 1 (`exp1`, `exp5` "stock model").
- after-validators only run if field validation passed. When several fail, only the **first** one's error
  surfaces (`exp2` "chained": only `one` appears). Users fix errors one at a time unless we collect them.

### 4. Raising located errors from validators

- Pydantic docs list `ValueError`, `AssertionError` and `PydanticCustomError` as the exceptions to raise
  (https://pydantic.dev/docs/validation/latest/concepts/validators/#raising-validation-errors). The docs don't
  mention raising `ValidationError` directly, though the wrap-validator example re-raises one from the handler.
- **pydantic-core explicitly supports it.** `convert_err` in `src/validators/function.rs` says
  "Only `ValueError` (including `PydanticCustomError` and `ValidationError`) and `AssertionError` are considered
  as validation errors". The `ValidationError` branch calls `validation_error.into_val_error()`, which re-emits
  its line errors with their own locs. The same branch exists in v2.27.2 and v2.41.5 (Pyodide's version)
  and on main
  (https://github.com/pydantic/pydantic-core/blob/v2.41.5/src/validators/function.rs,
  https://github.com/pydantic/pydantic-core/blob/main/src/errors/validation_exception.rs).
- Verified (`exp2`): raising `ValidationError.from_exception_data("Dungeon", [InitErrorDetails(type=PydanticCustomError(...), loc=("rooms", ri, "exits", di, "target"), input=...)])`
  from an after-`model_validator` yields errors at exactly those locs. Multiple errors per raise work, and when the
  model is nested under another field the parent's loc is **prefixed** (`('dungeon','rooms',0,...)`).
  The locs are therefore relative to the model, which is what we want.
- Gotcha: `PydanticCustomError` templates use plain `{name}` replacement. Format specs like `{target!r}` are
  **not** interpreted and come out literally (`exp2`). Use `'{target}'`.
- Confidence that this keeps working: medium-high. It's deliberate code with a doc comment, not an accident,
  but it isn't in the user docs. If it ever breaks, the fallback is to run semantic checks outside pydantic as
  `semantic_errors(dungeon) -> list[(loc, msg)]` after `model_validate`, and merge the results.
- Cheaper wins in `models.py`: `Door.check_direction` should be a `field_validator("direction")`, or `direction`
  should be a `Literal[...]`/`Enum`, which gives loc `(…, 'direction')` with no plumbing. Fold the four `Dungeon`
  checks into one validator that *collects* errors (duplicate ids → each `('rooms', i, 'id')`, bad targets →
  `(…, 'exits', j, 'target')`, unreachable → `('rooms', i, 'id')`, no entrance → `('rooms',)`) so the editor
  shows them all at once.

### 5. YAML syntax errors

`yaml.MarkedYAMLError` subclasses (`ScannerError`, `ParserError`, `ComposerError`, `ConstructorError`) carry
`problem_mark` and, often, `context_mark`, plus `problem`/`context` strings. Both marks are 0-based. Verified
across bad indent, unclosed flow, `a: b: c`, undefined alias, tab indent, unterminated quote, and multi-doc
(`exp3`). Every case had a `problem_mark`. Use `problem_mark` for the squiggle and optionally add `context_mark`
as related info ("while parsing a flow sequence" at L1:C7). These errors are fatal. PyYAML doesn't recover, so you
get at most one syntax diagnostic per parse.

### 6. ruamel.yaml (`exp4`, ruamel 0.19.1 round-trip)

- `CommentedMap.lc.key(k)` / `.lc.value(k)` / `CommentedSeq.lc.item(i)` return 0-based `(line, col)`
  (https://yaml.dev/doc/ruamel.yaml/detail/). They return **start only, with no end**, so there's no range for squiggles.
- Scalars are plain `str` with no position. You always go through the parent's `lc`.
- Merged keys (`<<: *door`) → `lc.key('type')` raises **`KeyError`**, which is worse than PyYAML.
- Benefit vs. PyYAML: none for this use case. Its real advantages (comment/format-preserving round-trip) would
  only matter if the playground *rewrites* YAML, e.g. quick-fixes. Revisit then.

## Sketch: loc → node walk

Full runnable version: [`yaml-positions-scratch/exp5_end_to_end.py`](yaml-positions-scratch/exp5_end_to_end.py).

```python
from yaml.nodes import MappingNode, SequenceNode, ScalarNode

def locate(root, loc):
    """Return (node, exact). Run AFTER construct_document (merges already flattened in-place)."""
    node = anchor = root
    for part in loc:
        if isinstance(node, MappingNode):
            hit = None
            for k, v in node.value:            # last match wins == PyYAML semantics
                if isinstance(k, ScalarNode) and k.value == str(part):
                    hit = (k, v)
            if hit is None:
                return anchor, False           # missing field: point at enclosing mapping/key
            anchor, node = hit                 # remember key node for nicer fallback
        elif isinstance(node, SequenceNode) and isinstance(part, int) and 0 <= part < len(node.value):
            node = anchor = node.value[part]
        else:
            return anchor, False               # union tag segment / walked past a scalar
    return node, True

def span(node):                                 # 1-based for the editor
    s, e = node.start_mark, node.end_mark
    if isinstance(node, ScalarNode):
        return s.line + 1, s.column + 1, e.line + 1, e.column + 1
    return s.line + 1, s.column + 1, s.line + 1, s.column + 2   # containers: end_mark unreliable
```

Pipeline:

```python
loader = yaml.SafeLoader(src)
try:
    root = loader.get_single_node()                   # MarkedYAMLError -> problem_mark
    data = loader.construct_document(root)            # mutates root: merges flattened
finally:
    loader.dispose()
try:
    Dungeon.model_validate(data)
except ValidationError as ve:
    diags = [(span(locate(root, e["loc"])[0]), e["msg"]) for e in ve.errors(include_url=False)]
```

Located semantic error from a validator:

```python
raise ValidationError.from_exception_data(type(self).__name__, [
    InitErrorDetails(type=PydanticCustomError("unknown_room", "unknown room '{target}'", {"target": d.target}),
                     loc=("rooms", ri, "exits", di, "target"), input=d.target)
    for ri, r in enumerate(self.rooms) for di, d in enumerate(r.exits) if d.target not in ids])
```

Prototype output (`exp5`): the stock model reports `unknown room 'ghost'` at L1:C1. The located model reports
L8:C18–23 (`ghost`) and L12:C17–24 (`phantom`).

## Confidence notes

- **High:** PyYAML mark semantics, the walk, merge flattening, syntax-error marks, and the located-ValidationError
  pattern. All were verified by running code on PyYAML 6.0.3 / pydantic 2.13.4, and the pydantic-core branch was
  confirmed in source for the version Pyodide ships (2.41.5).
- **Not run inside Pyodide.** The browser build uses pydantic 2.12.5 and PyYAML 6.0.2/6.0.3. The code paths used
  are unchanged across those versions in the source I checked, but nothing was executed in wasm.
- **Medium:** UTF-16 column conversion details, which depend on the editor chosen. Whether the "anchor, not alias
  site" behaviour is acceptable UX is a product call.
- PyYAML's own docs are thin on node marks. The node-level claims rest on experiment and source, not prose docs.
