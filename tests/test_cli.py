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
