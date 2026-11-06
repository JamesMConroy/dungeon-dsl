"""The load(text) seam: YAML in, (code, severity, line) out. Never message text."""

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


def test_existing_dungeon_level_rules_still_report_at_line_one() -> None:
    # Until they move into check(), these are pydantic errors on the whole Dungeon.
    text = VALID.replace("    entrance: true\n", "")

    assert outcome(text) == [("pydantic.value_error", "error", 1)]


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
