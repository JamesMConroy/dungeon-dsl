import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from dungeon_dsl import load
from dungeon_dsl.models import Door, Dungeon, Room
from dungeon_dsl.svg import render_svg

SVG = "{http://www.w3.org/2000/svg}"
GOBLIN_WARREN = Path(__file__).parent.parent / "examples" / "goblin_warren.yaml"
GOBLIN_WARREN_IDS = {
    "entrance",
    "corridor_north",
    "throne_room",
    "treasure_room",
    "escape_tunnel",
}


def _dungeon(name_of_second_room: str = "Second") -> Dungeon:
    return Dungeon(
        name="Test",
        rooms=[
            Room(
                id="first",
                name="First",
                entrance=True,
                exits=[Door(target="second", direction="e")],
            ),
            Room(
                id="second",
                name=name_of_second_room,
                exits=[Door(target="first", direction="w")],
            ),
        ],
    )


def _loaded(text: str) -> Dungeon:
    result = load(text)
    assert result.dungeon is not None, result.problems
    return result.dungeon


def _goblin_warren() -> Dungeon:
    return _loaded(GOBLIN_WARREN.read_text())


def _room_groups(root: ET.Element) -> list[ET.Element]:
    return [g for g in root.iter(f"{SVG}g") if g.get("class") == "room"]


def _legend_lines(root: ET.Element) -> list[ET.Element]:
    return [t for t in root.iter(f"{SVG}text") if t.get("data-room-id") is not None]


def test_every_room_has_exactly_one_room_group_with_its_id() -> None:
    root = ET.fromstring(render_svg(_goblin_warren()))

    ids = [g.get("data-room-id") for g in _room_groups(root)]

    assert sorted(ids, key=str) == sorted(GOBLIN_WARREN_IDS)


def test_room_group_holds_the_rooms_floor_and_a_label_that_ignores_the_pointer() -> (
    None
):
    root = ET.fromstring(render_svg(_goblin_warren()))

    groups = _room_groups(root)
    assert groups
    for group in groups:
        assert group.find(f"{SVG}rect") is not None
        label = group.find(f"{SVG}text")
        assert label is not None
        assert label.get("pointer-events") == "none"


def test_every_legend_line_carries_its_rooms_id_in_room_order() -> None:
    dungeon = _goblin_warren()
    root = ET.fromstring(render_svg(dungeon))

    lines = {t.get("data-room-id"): t.text for t in _legend_lines(root)}

    assert list(lines) == [room.id for room in dungeon.rooms]
    assert lines["throne_room"] == "3. Goblin Throne"


def test_renaming_a_room_leaves_the_drawing_unchanged() -> None:
    before = ET.fromstring(render_svg(_dungeon("Second")))
    after = ET.fromstring(render_svg(_dungeon("A Quite Different Name")))

    # The legend is the svg's last child, and the one place a name belongs.
    def drawing(root: ET.Element) -> list[bytes]:
        return [ET.tostring(child) for child in list(root)[:-1]]

    assert drawing(before) == drawing(after)
    assert before.get("viewBox") == after.get("viewBox")


def test_room_ids_with_markup_characters_stay_inert() -> None:
    hostile = '"><script>x</script>'
    dungeon = Dungeon(name="Test", rooms=[Room(id=hostile, name="R", entrance=True)])

    root = ET.fromstring(render_svg(dungeon))

    assert [g.get("data-room-id") for g in _room_groups(root)] == [hostile]
    assert root.find(f".//{SVG}script") is None


HALL = """\
name: Test
rooms:
  - id: hall
    name: Hall
    entrance: true
"""
VAULT = """\
  - id: vault
    name: Vault
    isolation: true
"""
CRYPT_JOINED_TO_VAULT = """\
    exits:
      - target: crypt
        direction: e
  - id: crypt
    name: Crypt
    isolation: true
    exits:
      - target: vault
        direction: w
"""


@pytest.mark.parametrize(
    ("text", "ids"),
    [
        (HALL + VAULT, ["hall", "vault"]),
        (HALL + VAULT + CRYPT_JOINED_TO_VAULT, ["hall", "vault", "crypt"]),
        # Connected to the hall only by its own one-way Door, which is valid.
        (
            HALL
            + "  - id: cell\n    name: Cell\n    exits:\n"
            + "      - target: hall\n        direction: n\n",
            ["hall", "cell"],
        ),
        # A second entrance, joined to nothing.
        (
            HALL + "  - id: side\n    name: Side\n    entrance: true\n",
            ["hall", "side"],
        ),
        # Isolated, with a one-way Door into the rest of the Dungeon.
        (
            HALL + VAULT + "    exits:\n      - target: hall\n        direction: n\n",
            ["hall", "vault"],
        ),
    ],
    ids=[
        "lone isolated",
        "joined isolated",
        "door out only",
        "second entrance",
        "isolated door out",
    ],
)
def test_rooms_the_entrance_has_no_door_to_still_get_their_room_group(
    text: str, ids: list[str]
) -> None:
    root = ET.fromstring(render_svg(_loaded(text)))

    assert [g.get("data-room-id") for g in _room_groups(root)] == ids


def _room_positions(text: str) -> dict[str | None, str | None]:
    root = ET.fromstring(render_svg(_loaded(text)))
    return {g.get("data-room-id"): g.get("transform") for g in _room_groups(root)}


def test_isolated_rooms_are_drawn_apart_without_overlapping() -> None:
    text = HALL + VAULT + CRYPT_JOINED_TO_VAULT

    positions = _room_positions(text)

    assert len(set(positions.values())) == len(positions)
    assert positions["hall"] == _room_positions(HALL)["hall"]


def test_doors_between_isolated_rooms_are_drawn() -> None:
    joined = ET.fromstring(render_svg(_loaded(HALL + VAULT + CRYPT_JOINED_TO_VAULT)))

    corridors = [g for g in joined.iter(f"{SVG}polygon")]

    assert len(corridors) == 1


RENDER_GOBLIN_WARREN = """
import sys
from dungeon_dsl import load
from dungeon_dsl.svg import render_svg
sys.stdout.write(render_svg(load(open(sys.argv[1]).read()).dungeon))
"""


@pytest.mark.parametrize("hash_seed", ["1", "2"])
def test_identical_input_gives_identical_output_in_any_process(hash_seed: str) -> None:
    output = subprocess.run(
        [sys.executable, "-c", RENDER_GOBLIN_WARREN, str(GOBLIN_WARREN)],
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert output == render_svg(_goblin_warren())
