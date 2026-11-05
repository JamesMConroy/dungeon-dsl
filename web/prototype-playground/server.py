"""PROTOTYPE — throwaway. Playground UX prototype (wayfinder ticket 06).

Stands in for Pyodide: a stdlib HTTP server that runs the real dungeon_dsl
pipeline on POST /render. Pyodide renders in ~9ms, so latency here is faithful.
Adds the §4 hooks (class="room", data-room-id) by post-processing the SVG, so
package code stays untouched.

Run: just prototype   (then open http://localhost:8770)
"""

import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dungeon_dsl.models import Dungeon  # noqa: E402
from dungeon_dsl.svg import render_svg  # noqa: E402

HERE = Path(__file__).parent
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def loc_to_mark(root: yaml.Node | None, loc: tuple) -> tuple[int, int]:
    """Walk a pydantic loc through the composed YAML node graph. 1-based line/col."""
    node = root
    for part in loc:
        if isinstance(node, yaml.MappingNode) and isinstance(part, str):
            nxt = None
            for k, v in node.value:
                if k.value == part:
                    nxt = v
            if nxt is None:
                break
            node = nxt
        elif isinstance(node, yaml.SequenceNode) and isinstance(part, int):
            if part >= len(node.value):
                break
            node = node.value[part]
        else:
            break
    if node is None:
        return 1, 1
    return node.start_mark.line + 1, node.start_mark.column + 1


def tag_svg(svg_text: str, dungeon: Dungeon) -> str:
    """Stamp class="room" + data-room-id on room floor groups and legend lines."""
    tree = ET.fromstring(svg_text)
    num_by_name = {}
    ids_by_num = {}
    q = lambda t: f"{{{SVG_NS}}}{t}"  # noqa: E731

    legend_g = tree[-1]
    for text in legend_g.findall(q("text"))[1:]:
        m = re.match(r"(\d+)\. (.*)", text.text or "")
        if m:
            num_by_name[m.group(2)] = int(m.group(1))
    for room in dungeon.rooms:
        ids_by_num[num_by_name.get(room.name)] = room.id
    for text in legend_g.findall(q("text"))[1:]:
        m = re.match(r"(\d+)\.", text.text or "")
        if m and int(m.group(1)) in ids_by_num:
            text.set("class", "legend-entry")
            text.set("data-room-id", ids_by_num[int(m.group(1))])

    floor_layer = tree[1]
    for g in floor_layer.findall(q("g")):
        rect = g.find(q("rect"))
        label = g.find(q("text"))
        if rect is None or label is None or not (label.text or "").isdigit():
            continue
        rid = ids_by_num.get(int(label.text))
        if rid:
            g.set("class", "room")
            g.set("data-room-id", rid)
            label.set("pointer-events", "none")
    return ET.tostring(tree, encoding="unicode")


def render(text: str) -> dict:
    t0 = time.perf_counter()
    try:
        root = yaml.compose(text)
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line, col = (mark.line + 1, mark.column + 1) if mark else (1, 1)
        msg = getattr(e, "problem", None) or str(e)
        return {"ok": False, "errors": [
            {"line": line, "col": col, "path": "", "msg": f"YAML syntax: {msg}"}
        ], "ms": _ms(t0)}
    try:
        dungeon = Dungeon.model_validate(data)
    except ValidationError as e:
        errs = []
        for err in e.errors():
            line, col = loc_to_mark(root, err["loc"])
            path = ".".join(str(p) for p in err["loc"]) or "(dungeon)"
            msg = err["msg"].removeprefix("Value error, ")
            errs.append({"line": line, "col": col, "path": path, "msg": msg})
        return {"ok": False, "errors": errs, "ms": _ms(t0)}
    except Exception as e:  # noqa: BLE001  — validators crash on some bad input
        return {"ok": False, "errors": [
            {"line": 1, "col": 1, "path": "", "msg": f"{type(e).__name__}: {e}"}
        ], "ms": _ms(t0)}

    try:
        svg = tag_svg(render_svg(dungeon), dungeon)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "errors": [
            {"line": 1, "col": 1, "path": "", "msg": f"render crashed: {type(e).__name__}: {e}"}
        ], "ms": _ms(t0)}

    numbers = {}
    for m in re.finditer(r'data-room-id="([^"]+)"[^>]*>\s*<rect[^>]*/>\s*<text[^>]*>(\d+)<', svg):
        numbers[m.group(1)] = int(m.group(2))
    return {
        "ok": True,
        "svg": svg,
        "dungeon": dungeon.model_dump(),
        "numbers": numbers,
        "ms": _ms(t0),
    }


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?")[0].split("#")[0]
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/examples":
            ex = {p.stem: p.read_text() for p in sorted((ROOT / "examples").glob("*.yaml"))}
            self._send(200, json.dumps(ex).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/render":
            self._send(404, b"not found", "text/plain")
            return
        n = int(self.headers.get("Content-Length", 0))
        text = self.rfile.read(n).decode()
        self._send(200, json.dumps(render(text)).encode(), "application/json")

    def log_message(self, *args) -> None:  # quiet
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    print(f"PROTOTYPE playground: http://localhost:{port}/?variant=A")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
