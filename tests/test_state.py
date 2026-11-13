from game.level import all_levels
from game.state import GameState


def state_at(level_id):
    levels = all_levels()
    return GameState(levels, [l.id for l in levels].index(level_id))


def test_one_qubit_gate_places_immediately():
    gs = state_at("1-1")
    gs.select_gate("X")
    assert gs.circuit == [{"gate": "X", "targets": [0]}]
    assert gs.run().cleared


def test_cnot_needs_control_then_target():
    gs = state_at("3-1")
    gs.select_gate("H"); gs.click_wire(0)
    gs.select_gate("CNOT")
    assert "control" in gs.message
    gs.click_wire(0)
    assert "target" in gs.message
    gs.click_wire(1)
    assert gs.circuit[-1] == {"gate": "CNOT", "controls": [0], "targets": [1]}
    result = gs.run()
    assert result.cleared and result.stars == 3


def test_same_wire_twice_is_ignored():
    gs = state_at("3-1")
    gs.select_gate("CNOT"); gs.click_wire(0); gs.click_wire(0)
    assert gs.circuit == [] and gs.picked_wires == [0]


def test_gate_budget_blocks_extra_gates():
    gs = state_at("1-1")
    gs.select_gate("X"); gs.select_gate("X")
    assert len(gs.circuit) == 1 and "No X" in gs.message


def test_grover_whole_register_gates_and_bars():
    gs = state_at("5-1")
    gs.select_gate("H"); gs.click_wire(0)
    gs.select_gate("H"); gs.click_wire(1)
    assert abs(gs.probabilities()[2] - 0.25) < 1e-9      # all four cards equal
    gs.select_gate("ORACLE"); gs.select_gate("DIFFUSION")
    assert abs(gs.probabilities()[2] - 1) < 1e-9         # marked card "10" at 100%
    assert gs.run().cleared


def test_hint_costs_a_star_and_reset_keeps_it():
    gs = state_at("1-1")
    gs.hint(); gs.reset()
    gs.select_gate("X")
    assert gs.run().stars == 2


def test_undo_and_next_level():
    gs = state_at("1-1")
    gs.select_gate("X"); gs.undo()
    assert gs.circuit == [] and not gs.next_level()
    gs.select_gate("X"); gs.run()
    assert gs.next_level() and gs.level.id != "1-1"


def test_entangled_arrows_shrink():
    gs = state_at("3-1")
    gs.select_gate("H"); gs.click_wire(0)
    gs.select_gate("CNOT"); gs.click_wire(0); gs.click_wire(1)
    assert all(abs(v) < 1e-9 for vec in gs.bloch_vectors() for v in vec)


def test_only_world_one_is_unlocked_at_start():
    gs = state_at("1-1")
    assert gs.worlds() == [1, 2, 3, 4, 5]
    assert [gs.world_unlocked(w) for w in gs.worlds()] == [True, False, False, False, False]
    assert not gs.enter_world(2) and gs.level.id == "1-1"


def test_clearing_a_world_unlocks_the_next():
    gs = state_at("1-1")
    gs.select_gate("X")
    assert gs.run().cleared
    assert gs.world_progress(1) == (1, 1, 3, 3)
    assert gs.world_unlocked(2) and not gs.world_unlocked(3)
    assert gs.enter_world(2) and gs.level.id == "2-3"
