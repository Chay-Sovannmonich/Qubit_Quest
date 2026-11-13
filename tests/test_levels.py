"""Every level must be solvable within its par, using only its allowed gates."""
import pytest

from game.level import Level, all_levels

LEVELS = all_levels()


def test_levels_found():
    assert len(LEVELS) >= 1


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv.id)
def test_solution_clears_level_with_three_stars(level: Level):
    result = level.check(level.solution)
    assert result.cleared, f"{level.id}: {result.message}"
    assert result.stars == 3


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv.id)
def test_solution_only_uses_allowed_gates(level: Level):
    assert all(n >= 0 for n in level.gates_left(level.solution).values())


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv.id)
def test_level_is_not_already_solved(level: Level):
    assert not level.check([]).cleared


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv.id)
def test_level_has_three_hints(level: Level):
    assert len(level.hints) == 3


def test_stars():
    lv = next(l for l in LEVELS if l.id == "2-4")
    long_way = [{"gate": "H", "targets": [0]}, {"gate": "Z", "targets": [0]}, {"gate": "H", "targets": [0]}]
    # H Z H acts like X, which leaves |+> unchanged, so it must fail
    assert not lv.check(long_way).cleared
    assert lv.check(lv.solution, hints_used=1).stars == 2


def test_too_many_gates_is_rejected():
    lv = next(l for l in LEVELS if l.id == "1-1")
    result = lv.check([{"gate": "X", "targets": [0]}] * 3)
    assert not result.cleared and "Too many" in result.message
