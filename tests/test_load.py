"""The load(text) seam: YAML in, (code, severity, line) out. Never message text."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from dungeon_dsl import load
from dungeon_dsl.svg import render_svg

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.yaml"))

VALID = """\
name: Test
rooms:
  - id: hall
    name: Hall
    entrance: true
    size: large
    exits:
      - target: cell
        direction: n
  - id: cell
    name: Cell
    exits:
      - target: hall
        direction: s
"""


def outcome(text: str) -> list[tuple[str, str, int | None]]:
    return [
        (p.code, p.severity, p.span.start.line if p.span else None)
        for p in load(text).problems
    ]


def span_of(text: str) -> tuple[int, int, int, int]:
    """(start line, start col, end line, end col) of the only Problem."""
    problems = load(text).problems
    assert len(problems) == 1
    span = problems[0].span
    assert span is not None
    return (span.start.line, span.start.col, span.end.line, span.end.col)


def test_a_yaml_syntax_error_is_reported_where_the_parser_gave_up() -> None:
    text = "name: x\nrooms: [\n  a: b: c\n"

    assert load(text).dungeon is None
    assert outcome(text) == [("yaml.syntax", "error", 3)]


def test_a_valid_dungeon_loads_with_no_problems() -> None:
    result = load(VALID)

    assert result.problems == []
    assert result.dungeon is not None
    assert [room.id for room in result.dungeon.rooms] == ["hall", "cell"]


def test_an_unknown_key_is_an_error_on_that_key() -> None:
    # The value starts a line below the key, and it's the key that's wrong.
    text = VALID.replace("    size: large\n", "    sise:\n      large\n")

    assert outcome(text) == [("pydantic.extra_forbidden", "error", 6)]
    assert load(text).dungeon is None
    assert span_of(text) == (6, 5, 6, 9)


@pytest.mark.parametrize(
    ("old", "new", "line"),
    [
        ("size: large", "size: huge", 6),
        ("direction: n", "direction: up", 9),
    ],
)
def test_a_value_outside_its_list_is_an_error_on_that_value(
    old: str, new: str, line: int
) -> None:
    text = VALID.replace(old, new)

    assert outcome(text) == [("pydantic.literal_error", "error", line)]


@pytest.mark.parametrize(
    ("field", "value"),
    [("light", "gloomy"), ("type", "glass"), ("state", "ajar")],
)
def test_the_other_fixed_value_fields_reject_values_outside_their_lists(
    field: str, value: str
) -> None:
    door_or_room = "      " if field != "light" else "  "
    anchor = "        direction: n\n" if field != "light" else "    entrance: true\n"
    text = VALID.replace(anchor, f"{anchor}{door_or_room}  {field}: {value}\n")

    assert [code for code, _, _ in outcome(text)] == ["pydantic.literal_error"]


def test_terrain_stays_free_text() -> None:
    text = VALID.replace("    size: large\n", "    terrain: quicksilver_bog\n")

    assert outcome(text) == []


def test_an_unknown_size_is_an_error_instead_of_a_renderer_crash() -> None:
    text = VALID.replace("size: large", "size: huge")
    span = span_of(text)

    assert span == (6, 11, 6, 15)


def test_a_missing_field_points_at_the_enclosing_mapping() -> None:
    text = VALID.replace("    name: Cell\n", "")

    assert outcome(text) == [("pydantic.missing", "error", 10)]


def test_a_container_span_is_clamped_to_its_first_line() -> None:
    text = VALID.replace("    name: Cell\n", "")

    assert span_of(text) == (10, 5, 10, 13)


def test_a_mapping_on_a_single_line_keeps_its_exact_span() -> None:
    text = "name: x\nrooms:\n  - {id: a}  # comment\n"

    assert span_of(text) == (3, 5, 3, 12)


def test_several_structural_errors_are_reported_together() -> None:
    text = VALID.replace("size: large", "size: huge").replace(
        "direction: s", "direction: up"
    )

    assert sorted(line for _, _, line in outcome(text) if line) == [6, 14]


def test_columns_count_code_points() -> None:
    text = 'name: x\nrooms: [{id: a, name: "🐉🐉", entrance: true, size: huge}]\n'

    # An editor counting UTF-16 units would put this two columns later.
    assert span_of(text) == (2, 51, 2, 55)


def test_an_error_in_merged_data_points_at_the_anchor() -> None:
    text = """\
name: x
rooms:
  - &base
    id: a
    name: A
    entrance: true
    size: huge
  - <<: *base
    id: b
"""
    assert outcome(text) == [
        ("pydantic.literal_error", "error", 7),
        ("pydantic.literal_error", "error", 7),
    ]


def test_an_error_in_aliased_data_points_at_the_anchor() -> None:
    text = """\
name: x
rooms:
  - id: a
    name: A
    entrance: true
    exits:
      - &door
        target: a
        direction: up
      - *door
"""
    assert outcome(text) == [
        ("pydantic.literal_error", "error", 9),
        ("pydantic.literal_error", "error", 9),
    ]


def test_no_entrance_is_one_error_on_the_rooms_key() -> None:
    # Neither Room can be reached from an entrance that isn't there: no pile-on.
    text = VALID.replace("    entrance: true\n", "")

    assert outcome(text) == [("dungeon.no_entrance", "error", 2)]
    assert load(text).dungeon is None
    assert span_of(text) == (2, 1, 2, 6)


def test_no_rooms_at_all_is_no_entrance() -> None:
    assert outcome("name: x\nrooms: []\n") == [("dungeon.no_entrance", "error", 2)]


def test_each_duplicate_room_id_after_the_first_is_an_error_on_that_id() -> None:
    text = VALID + "  - id: cell\n    name: Annex\n  - id: cell\n    name: Attic\n"

    assert outcome(text) == [
        ("room.duplicate_id", "error", 15),
        ("room.duplicate_id", "error", 17),
    ]
    assert load(text).dungeon is None


def test_a_duplicate_id_is_underlined_on_the_id_value() -> None:
    assert span_of(VALID + "  - id: cell\n    name: Annex\n") == (15, 9, 15, 13)


def test_a_merged_id_that_duplicates_points_at_the_anchor() -> None:
    text = """\
name: x
rooms:
  - &base
    id: a
    name: A
    entrance: true
  - <<: *base
    name: B
"""
    assert outcome(text) == [("room.duplicate_id", "error", 4)]


def test_an_id_set_over_a_merge_points_at_the_explicit_key() -> None:
    text = """\
name: x
rooms:
  - id: hall
    name: Hall
    entrance: true
  - &base
    id: a
    name: A
  - <<: *base
    id: b
"""
    assert outcome(text) == [
        ("room.unreachable", "error", 7),
        ("room.unreachable", "error", 10),
    ]


def test_an_unknown_target_in_an_aliased_door_points_at_the_anchor() -> None:
    text = """\
name: x
rooms:
  - id: a
    name: A
    entrance: true
    exits:
      - &door
        target: ghost
        direction: n
      - *door
"""
    assert outcome(text) == [
        ("door.unknown_target", "error", 8),
        ("door.unknown_target", "error", 8),
    ]


def test_several_dungeon_level_errors_are_reported_together() -> None:
    text = (
        VALID.replace("target: cell", "target: cel")
        + "  - id: hall\n    name: Again\n  - id: vault\n    name: Vault\n"
    )

    assert sorted(outcome(text), key=lambda problem: problem[2] or 0) == [
        ("door.unknown_target", "error", 8),
        ("door.one_way", "warning", 13),
        ("room.duplicate_id", "error", 15),
        ("room.unreachable", "error", 17),
    ]
    assert load(text).dungeon is None


def test_a_structural_error_suppresses_the_dungeon_level_rules() -> None:
    text = (
        VALID.replace("size: large", "size: huge")
        .replace("    entrance: true\n", "")
        .replace("target: hall", "target: nowhere")
        + "  - id: cell\n    name: Annex\n"
    )

    assert [code for code, _, _ in outcome(text)] == ["pydantic.literal_error"]


def test_a_door_to_an_unknown_room_is_an_error_on_its_target_only() -> None:
    # No One-way Door Warning either, as the Door leads nowhere.
    text = VALID + "      - target: nowhere\n        direction: e\n"

    assert outcome(text) == [("door.unknown_target", "error", 15)]
    assert load(text).dungeon is None
    assert span_of(text) == (15, 17, 15, 24)


def test_a_room_with_only_a_broken_door_to_it_is_also_unreachable() -> None:
    # Reachability ignores the broken Door, and the cell really is cut off.
    text = VALID.replace("target: cell", "target: cel").replace(
        "    exits:\n      - target: hall\n        direction: s\n", ""
    )

    assert outcome(text) == [
        ("door.unknown_target", "error", 8),
        ("room.unreachable", "error", 10),
    ]


def test_an_unknown_room_does_not_connect_the_doors_that_target_it() -> None:
    text = """\
name: x
rooms:
  - id: hall
    name: Hall
    entrance: true
    exits:
      - target: ghost
        direction: n
  - id: vault
    name: Vault
    exits:
      - target: ghost
        direction: s
"""

    assert sorted(outcome(text), key=lambda problem: problem[2] or 0) == [
        ("door.unknown_target", "error", 7),
        ("room.unreachable", "error", 9),
        ("door.unknown_target", "error", 12),
    ]


def test_without_an_entrance_an_unknown_target_is_still_reported() -> None:
    text = VALID.replace("    entrance: true\n", "").replace(
        "target: hall", "target: nowhere"
    )

    assert sorted(outcome(text), key=lambda problem: problem[2] or 0) == [
        ("dungeon.no_entrance", "error", 2),
        ("door.one_way", "warning", 7),
        ("door.unknown_target", "error", 12),
    ]


def test_a_room_the_entrance_cannot_reach_is_an_error_on_its_id() -> None:
    text = VALID + "  - id: vault\n    name: Vault\n"

    assert outcome(text) == [("room.unreachable", "error", 15)]
    assert load(text).dungeon is None
    assert span_of(text) == (15, 9, 15, 14)


def test_rooms_linked_only_to_each_other_are_each_unreachable() -> None:
    text = (
        VALID
        + """\
  - id: vault
    name: Vault
    exits:
      - target: crypt
        direction: n
  - id: crypt
    name: Crypt
"""
    )

    assert outcome(text) == [
        ("room.unreachable", "error", 15),
        ("door.one_way", "warning", 18),
        ("room.unreachable", "error", 20),
    ]


def test_an_isolated_room_may_be_unreachable() -> None:
    text = VALID + "  - id: vault\n    name: Vault\n    isolation: true\n"

    assert outcome(text) == []


def test_a_door_connects_its_rooms_whichever_side_declares_it() -> None:
    # The hall has no door to the vault; the vault's door to the hall is enough.
    text = (
        VALID
        + """\
  - id: vault
    name: Vault
    exits:
      - target: hall
        direction: e
"""
    )

    assert outcome(text) == [("door.one_way", "warning", 18)]


@pytest.mark.parametrize("text", ["", "# only a comment\n", "just a string\n", "- 1\n"])
def test_a_document_that_is_not_a_mapping_is_a_structural_error(text: str) -> None:
    result = load(text)

    assert result.dungeon is None
    assert [p.code for p in result.problems] == ["pydantic.model_type"]


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ("name: a\x00b\n", 1),  # rejected by the reader, before any parsing
        ("name: x\nrooms: []\n---\nname: y\n", 3),  # two documents
        ("name: *nowhere\n", 1),  # undefined alias
        ("name: !!python/object:os.system x\n", 1),  # unsafe tag
        ("{[a]: b}\n", 1),  # unhashable key, found while constructing
    ],
)
def test_everything_the_yaml_library_rejects_is_a_syntax_error(
    text: str, line: int
) -> None:
    assert outcome(text) == [("yaml.syntax", "error", line)]


def test_absurd_nesting_is_a_problem_not_a_crash() -> None:
    assert [code for code, _, _ in outcome("[" * 20_000)] == ["yaml.syntax"]


def test_a_key_that_is_not_a_string_is_an_error_on_that_key() -> None:
    text = "name: y\nrooms: []\n1:\n  x\n"

    assert outcome(text) == [("pydantic.invalid_key", "error", 3)]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_every_bundled_example_loads_and_renders(example: Path) -> None:
    result = load(example.read_text(encoding="utf-8"))

    assert [p for p in result.problems if p.severity == "error"] == []
    assert result.dungeon is not None
    assert render_svg(result.dungeon)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_no_bundled_example_has_a_warning(example: Path) -> None:
    assert load(example.read_text(encoding="utf-8")).problems == []


ONE_WAY = """\
name: Test
rooms:
  - id: hall
    name: Hall
    entrance: true
    exits:
      - direction: n
        target: pit
  - id: pit
    name: Pit
"""


def test_a_one_way_door_is_a_warning_on_its_target_and_the_dungeon_stays_valid() -> (
    None
):
    result = load(ONE_WAY)

    assert outcome(ONE_WAY) == [("door.one_way", "warning", 8)]
    assert result.problems[0].loc == ["rooms", 0, "exits", 0, "target"]
    assert span_of(ONE_WAY) == (8, 17, 8, 20)
    assert result.dungeon is not None


def test_a_door_to_its_own_room_is_its_own_way_back() -> None:
    text = VALID + "      - target: cell\n        direction: e\n"

    assert outcome(text) == []


def test_a_warning_comes_with_any_errors_and_the_dungeon_is_still_invalid() -> None:
    text = ONE_WAY + "  - id: lost\n    name: Lost\n"

    assert outcome(text) == [
        ("door.one_way", "warning", 8),
        ("room.unreachable", "error", 11),
    ]
    assert load(text).dungeon is None


def test_rooms_sharing_an_id_share_their_ways_back() -> None:
    # Only the first hall has the cell's way back. The duplicate id is the mistake.
    text = (
        VALID
        + "  - id: hall\n    name: Again\n    exits:\n"
        + "      - target: cell\n        direction: w\n"
    )

    assert outcome(text) == [("room.duplicate_id", "error", 15)]


def test_a_broken_door_is_no_way_back_for_the_door_it_was_meant_to_answer() -> None:
    # One typo, two true statements: the target is unknown, and the cell's door is
    # now one-way. Only the Door whose own target is unknown is spared the Warning.
    text = VALID.replace("target: cell", "target: cel")

    assert outcome(text) == [
        ("door.unknown_target", "error", 8),
        ("door.one_way", "warning", 13),
    ]


@pytest.mark.parametrize(
    "value",
    [
        "2000-13-45",
        "!!int foo",
        "!!int ''",
        "!!float foo",
        "!!float ''",
        "!!bool foo",
        "!!timestamp foo",
        "2000-01-01 00:00:00 +99:99",
        "1" * 5000,
        ":".join(["1"] * 400) + ".5",
    ],
)
def test_a_value_yaml_cannot_construct_is_a_problem_on_that_value(value: str) -> None:
    text = VALID.replace("name: Cell", f"name: {value}")

    result = load(text)

    assert outcome(text) == [("yaml.invalid_value", "error", 11)]
    assert result.dungeon is None
    assert span_of(text) == (11, 11, 11, 11 + len(value))


def test_a_key_yaml_cannot_construct_is_a_problem_on_that_key() -> None:
    text = "name: Test\n2000-13-45: oops\n"

    assert span_of(text) == (2, 1, 2, 11)
    assert outcome(text) == [("yaml.invalid_value", "error", 2)]


@pytest.mark.parametrize(
    "text",
    [
        'name: "\\UFFFFFFFF"\n',
        "%YAML " + "9" * 5000 + ".1\n---\nname: x\n",
    ],
)
def test_text_that_breaks_pyyaml_before_any_value_exists_is_a_syntax_problem(
    text: str,
) -> None:
    assert outcome(text) == [("yaml.syntax", "error", 1)]


@pytest.mark.parametrize(
    "text",
    [
        "!!int foo",
        "? !!bool foo\n: x\n",
        "- 2000-13-45\n",
        "&a {<<: *a}\n",
        "&a {*a : x}\n",
        "&a !!set {*a}\n",
        "1.5: x\n",
        "~: x\n",
        "2000-01-01: x\n",
        "? !!binary /w==\n: x\n",
        "name: !!binary /w==\nrooms: []\n",
        'name: "\\uD800"\nrooms: []\n',
        "\x00",
    ],
)
def test_load_never_raises_and_a_broken_dungeon_is_never_returned(text: str) -> None:
    result = load(text)

    assert result.dungeon is None
    assert any(problem.severity == "error" for problem in result.problems)


SECOND_ENTRANCE = """\
  - id: side
    name: Side
    entrance: true
"""


def test_a_disconnected_second_entrance_is_valid() -> None:
    result = load(VALID + SECOND_ENTRANCE)

    assert result.problems == []
    assert result.dungeon is not None


def test_a_room_behind_a_second_entrance_is_reachable() -> None:
    door_to_side = "    exits:\n      - target: side\n        direction: e\n"
    text = (
        VALID
        + "  - id: annex\n    name: Annex\n"
        + door_to_side
        + SECOND_ENTRANCE
        + "    exits:\n      - target: annex\n        direction: w\n"
    )

    assert outcome(text) == []


def test_a_room_neither_entrance_can_reach_is_still_an_error() -> None:
    text = VALID + SECOND_ENTRANCE + "  - id: lost\n    name: Lost\n"

    assert outcome(text) == [("room.unreachable", "error", 18)]


def field_set_to(field: str, value: str) -> str:
    """A one-Room Dungeon, with `field` holding `value`, and that field on line 7."""
    fields = {"id": "a", "name": "A", "description": "", "terrain": ""}
    dungeon_name = value if field == "dungeon name" else "D"
    theme = value if field == "theme" else "t"
    if field in fields:
        fields[field] = value
    return (
        f"name: {dungeon_name}\n"
        f"theme: {theme}\n"
        "rooms:\n"
        f"  - id: {fields['id']}\n"
        f"    name: {fields['name']}\n"
        "    entrance: true\n"
        f"    description: {fields['description'] or 'x'}\n"
        f"    terrain: {fields['terrain'] or 'x'}\n"
    )


FORBIDDEN_IN_XML = ["\\0", "\\x01", "\\x0b", "\\x1f", "\\uFFFE", "\\uFFFF", "\\uD800"]


@pytest.mark.parametrize(
    ("field", "line"),
    [
        ("dungeon name", 1),
        ("theme", 2),
        ("id", 4),
        ("name", 5),
        ("description", 7),
        ("terrain", 8),
    ],
)
@pytest.mark.parametrize("escape", FORBIDDEN_IN_XML)
def test_a_character_svg_cannot_hold_is_an_error_on_that_text(
    escape: str, field: str, line: int
) -> None:
    text = field_set_to(field, f'"x{escape}y"')

    assert outcome(text) == [("text.invalid_character", "error", line)]
    assert load(text).dungeon is None


@pytest.mark.parametrize(
    "escape", ["\\t", "\\n", "\\r", "\\x7f", "\\x85", "\\U0001F409"]
)
@pytest.mark.parametrize("field", ["dungeon name", "id", "name"])
def test_a_character_svg_can_hold_draws_a_well_formed_map(
    escape: str, field: str
) -> None:
    result = load(field_set_to(field, f'"x{escape}y"'))

    assert result.problems == []
    assert result.dungeon is not None
    ET.fromstring(render_svg(result.dungeon))
