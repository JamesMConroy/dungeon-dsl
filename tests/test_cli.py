import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GOBLIN_WARREN = REPO_ROOT / "examples" / "goblin_warren.yaml"
GOBLIN_WARREN_ROOMS = [
    "Grand Hall",
    "North Passage",
    "Goblin Throne",
    "Storage Chamber",
    "Hidden Escape Route",
]
SVG = "{http://www.w3.org/2000/svg}svg"


def dungeon_dsl(*args: str) -> subprocess.CompletedProcess[str]:
    command = Path(sys.executable).parent / "dungeon-dsl"
    return subprocess.run(
        [str(command), *args], capture_output=True, text=True, check=False
    )


def test_console_script_renders_a_dungeon_map() -> None:
    result = dungeon_dsl(str(GOBLIN_WARREN), "-f", "svg")

    assert result.returncode == 0, result.stderr
    root = ET.fromstring(result.stdout)
    assert root.tag == SVG
    assert all(room in result.stdout for room in GOBLIN_WARREN_ROOMS)


def test_problems_are_printed_for_editors_and_dumped_as_json(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        GOBLIN_WARREN.read_text(encoding="utf-8").replace(
            "size: large", "size: huge", 1
        ),
        encoding="utf-8",
    )
    line = broken.read_text(encoding="utf-8").splitlines().index("    size: huge") + 1

    printed = dungeon_dsl(str(broken), "-f", "svg")
    dumped = dungeon_dsl(str(broken), "--json")
    valid = dungeon_dsl(str(GOBLIN_WARREN), "--json")

    assert printed.returncode != 0
    assert printed.stdout == ""
    assert re.fullmatch(
        rf"{re.escape(str(broken))}:{line}:11: error: .+ \[pydantic\.literal_error\]\n",
        printed.stderr,
    )

    assert dumped.returncode != 0
    result = json.loads(dumped.stdout)
    assert result["dungeon"] is None
    assert result["problems"][0]["code"] == "pydantic.literal_error"
    assert result["problems"][0]["severity"] == "error"
    assert result["problems"][0]["loc"] == ["rooms", 0, "size"]
    assert result["problems"][0]["span"] == {
        "start": {"line": line, "col": 11},
        "end": {"line": line, "col": 15},
    }

    assert valid.returncode == 0
    assert json.loads(valid.stdout)["dungeon"]["name"] == "Goblin Warren"


def test_warnings_fail_only_under_strict(tmp_path: Path) -> None:
    one_way = tmp_path / "one_way.yaml"
    one_way.write_text(
        "name: x\n"
        "rooms:\n"
        "  - {id: hall, name: Hall, entrance: true, exits: "
        "[{target: pit, direction: n}]}\n"
        "  - {id: pit, name: Pit}\n",
        encoding="utf-8",
    )

    default = dungeon_dsl(str(one_way), "-f", "svg")
    strict = dungeon_dsl(str(one_way), "-f", "svg", "--strict")
    strict_json = dungeon_dsl(str(one_way), "--strict", "--json")

    assert default.returncode == 0, default.stderr
    assert re.fullmatch(
        rf"{re.escape(str(one_way))}:3:\d+: warning: .+ \[door\.one_way\]\n",
        default.stderr,
    )
    assert ET.fromstring(default.stdout).tag == SVG

    assert strict.returncode != 0
    assert strict.stderr == default.stderr
    assert ET.fromstring(strict.stdout).tag == SVG

    assert strict_json.returncode != 0
    assert json.loads(strict_json.stdout)["problems"][0]["code"] == "door.one_way"


def test_strict_passes_a_dungeon_with_no_problems() -> None:
    assert dungeon_dsl(str(GOBLIN_WARREN), "--strict").returncode == 0


def test_only_the_cli_module_needs_typer() -> None:
    # The wheel runs in Pyodide without the cli extra, so typer is absent there.
    probe = """
import importlib, pkgutil, sys
import dungeon_dsl
sys.modules["typer"] = None  # any later `import typer` raises ImportError
for module in pkgutil.iter_modules(dungeon_dsl.__path__, "dungeon_dsl."):
    if module.name != "dungeon_dsl.cli":
        importlib.import_module(module.name)
        print(module.name)
"""
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    assert "dungeon_dsl.svg" in result.stdout.split()
