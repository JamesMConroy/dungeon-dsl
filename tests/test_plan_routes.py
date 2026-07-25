from dungeon_dsl.layout import Placement
from dungeon_dsl.models import Door, Room
from dungeon_dsl.svg import plan_routes


def place(room_id: str, x: int, y: int) -> Placement:
    return Placement(room=Room(id=room_id, name=room_id.title()), x=x, y=y)


def edge(source: Placement, target: Placement) -> tuple[Placement, Placement, Door]:
    # plan_routes never reads the Door; direction here is a placeholder
    return (source, target, Door(target=target.room.id, direction="n"))


def cells(*placements: Placement) -> set[tuple[int, int]]:
    return {(p.x, p.y) for p in placements}


def test_adjacent_rooms_route_straight() -> None:
    a, b, c = place("a", 0, 0), place("b", 1, 0), place("c", 0, 1)
    routes = plan_routes([edge(a, b), edge(a, c)], cells(a, b, c))
    assert routes[("a", "b")] == "straight"
    assert routes[("a", "c")] == "straight"


def test_overlapping_rooms_skip() -> None:
    a, b = place("a", 0, 0), place("b", 0, 0)
    routes = plan_routes([edge(a, b)], cells(a, b))
    assert routes[("a", "b")] == "skip"


def test_straight_path_blocked_by_room_skips() -> None:
    a, b, blocker = place("a", 0, 0), place("b", 2, 0), place("x", 1, 0)
    routes = plan_routes([edge(a, b)], cells(a, b, blocker))
    assert routes[("a", "b")] == "skip"


def test_straight_path_over_empty_gap_cell_allowed() -> None:
    a, b = place("a", 0, 0), place("b", 2, 0)
    routes = plan_routes([edge(a, b)], cells(a, b))
    assert routes[("a", "b")] == "straight"


def test_knight_move_skips() -> None:
    a, b = place("a", 0, 0), place("b", 1, 2)
    routes = plan_routes([edge(a, b)], cells(a, b))
    assert routes[("a", "b")] == "skip"


def test_diagonal_with_free_corners_prefers_v_first() -> None:
    a, b = place("a", 0, 0), place("b", 1, -1)
    routes = plan_routes([edge(a, b)], cells(a, b))
    assert routes[("a", "b")] == "v-first"


def test_diagonal_forced_h_first_when_v_corner_blocked() -> None:
    a, b = place("a", 0, 0), place("b", 1, -1)
    blocker = place("x", 0, -1)  # occupies the vertical-first transit cell
    routes = plan_routes([edge(a, b)], cells(a, b, blocker))
    assert routes[("a", "b")] == "h-first"


def test_diagonal_with_both_corners_blocked_skips() -> None:
    a, b = place("a", 0, 0), place("b", 1, -1)
    v_block, h_block = place("x", 0, -1), place("y", 1, 0)
    routes = plan_routes([edge(a, b)], cells(a, b, v_block, h_block))
    assert routes[("a", "b")] == "skip"


def test_claims_steer_second_diagonal_off_shared_wall() -> None:
    # size_test scenario: hall->vestry is corner-forced h-first (claims
    # hall's east wall); hall->oubliette has both corners free and must
    # pick v-first because h-first would reuse the claimed east wall
    hall, chapel = place("hall", 0, 0), place("chapel", 0, -1)
    vestry, oubliette = place("vestry", 1, -1), place("oubliette", 1, 1)
    routes = plan_routes(
        [edge(hall, vestry), edge(hall, oubliette)],
        cells(hall, chapel, vestry, oubliette),
    )
    assert routes[("hall", "vestry")] == "h-first"
    assert routes[("hall", "oubliette")] == "v-first"


def test_straight_door_claims_correct_walls() -> None:
    # regression: a vertical straight door once claimed e/w walls due to a
    # cell_dx/cell_dy typo, creating a phantom north-wall claim that pushed
    # an unrelated diagonal onto a crowded wall
    hall, south = place("hall", 0, 0), place("south", 0, 1)
    airshaft = place("airshaft", 1, -1)  # ne of hall, both corners free
    routes = plan_routes(
        [edge(hall, south), edge(hall, airshaft)],
        cells(hall, south, airshaft),
    )
    # with correct claims (hall "s", south "n") the diagonal's v-first
    # route through hall's north wall is unclaimed and wins the tie
    assert routes[("hall", "airshaft")] == "v-first"


def test_every_edge_gets_a_verdict() -> None:
    a, b = place("a", 0, 0), place("b", 1, 0)
    c, d = place("c", 1, -1), place("d", 3, 2)
    e = place("e", 0, 0)  # overlaps a
    edges = [edge(a, b), edge(a, c), edge(a, d), edge(a, e)]
    routes = plan_routes(edges, cells(a, b, c, d))
    assert len(routes) == len(edges)
    for source, target, _ in edges:
        assert (source.room.id, target.room.id) in routes
