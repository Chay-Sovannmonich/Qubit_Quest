import numpy as np
import pytest

from quantum.simulator import (
    SQ2, apply_step, bloch_vector, fidelity, initial_state, probabilities, run_circuit,
)

ZERO, ONE = initial_state(1, "0"), initial_state(1, "1")
PLUS = np.array([SQ2, SQ2], dtype=complex)
MINUS = np.array([SQ2, -SQ2], dtype=complex)


def g(name, *targets, **kw):
    return {"gate": name, "targets": list(targets), **kw}


# ---------- single-qubit gates ----------
def test_x_flips_zero_to_one():
    assert fidelity(run_circuit(ZERO, [g("X", 0)]), ONE) == pytest.approx(1)


def test_h_makes_plus():
    assert np.allclose(run_circuit(ZERO, [g("H", 0)]), PLUS)


def test_hzh_equals_x():
    assert np.allclose(run_circuit(ZERO, [g("H", 0), g("Z", 0), g("H", 0)]), ONE)


def test_z_turns_plus_into_minus():
    assert fidelity(run_circuit(PLUS, [g("Z", 0)]), MINUS) == pytest.approx(1)


def test_y_on_zero_is_one_up_to_global_phase():
    out = run_circuit(ZERO, [g("Y", 0)])
    assert np.allclose(out, [0, 1j])               # i|1>
    assert fidelity(out, ONE) == pytest.approx(1)  # global phase ignored


def test_t_twice_is_s():
    assert np.allclose(run_circuit(PLUS, [g("T", 0), g("T", 0)]), run_circuit(PLUS, [g("S", 0)]))


def test_ry_half_pi_makes_plus():
    assert np.allclose(run_circuit(ZERO, [g("RY", 0, theta=np.pi / 2)]), PLUS)


# ---------- multi-qubit gates and qubit order ----------
def test_qubit_zero_is_leftmost_bit():
    assert np.allclose(run_circuit(initial_state(2), [g("X", 0)]), initial_state(2, "10"))


def test_bell_state():
    out = run_circuit(initial_state(2), [g("H", 0), {"gate": "CNOT", "controls": [0], "targets": [1]}])
    assert np.allclose(out, [SQ2, 0, 0, SQ2])


def test_cnot_reverse_direction():
    out = run_circuit(initial_state(2, "01"), [{"gate": "CNOT", "controls": [1], "targets": [0]}])
    assert np.allclose(out, initial_state(2, "11"))


def test_cz_only_flips_11():
    plus2 = run_circuit(initial_state(2), [g("H", 0), g("H", 1)])
    out = apply_step(plus2, {"gate": "CZ", "controls": [0], "targets": [1]})
    assert np.allclose(out, [0.5, 0.5, 0.5, -0.5])


def test_swap():
    assert np.allclose(run_circuit(initial_state(2, "10"), [g("SWAP", 0, 1)]), initial_state(2, "01"))


def test_ghz_state():
    out = run_circuit(initial_state(3), [
        g("H", 0),
        {"gate": "CNOT", "controls": [0], "targets": [1]},
        {"gate": "CNOT", "controls": [1], "targets": [2]},
    ])
    expected = np.zeros(8, dtype=complex)
    expected[0] = expected[7] = SQ2
    assert np.allclose(out, expected)


@pytest.mark.parametrize("bits, flips", [("110", True), ("100", False), ("010", False), ("111", True)])
def test_toffoli(bits, flips):
    out = run_circuit(initial_state(3, bits), [{"gate": "TOFFOLI", "controls": [0, 1], "targets": [2]}])
    new = bits[:2] + (str(1 - int(bits[2])) if flips else bits[2])
    assert np.allclose(out, initial_state(3, new))


def test_controlled_gate_needs_right_number_of_controls():
    with pytest.raises(ValueError):
        apply_step(initial_state(3), {"gate": "TOFFOLI", "controls": [0], "targets": [2]})


# ---------- Grover ----------
@pytest.mark.parametrize("marked", ["00", "01", "10", "11"])
def test_grover_two_qubits_one_round_finds_answer(marked):
    out = run_circuit(initial_state(2), [g("H", 0), g("H", 1), {"gate": "ORACLE", "marked": marked}, {"gate": "DIFFUSION"}])
    assert probabilities(out)[int(marked, 2)] == pytest.approx(1)


def test_grover_three_qubits_two_rounds_about_95_percent():
    rnd = [{"gate": "ORACLE", "marked": "101"}, {"gate": "DIFFUSION"}]
    out = run_circuit(initial_state(3), [g("H", 0), g("H", 1), g("H", 2)] + rnd * 2)
    assert probabilities(out)[5] == pytest.approx(0.9453, abs=1e-3)


def test_grover_third_round_overshoots():
    rnd = [{"gate": "ORACLE", "marked": "101"}, {"gate": "DIFFUSION"}]
    two = run_circuit(initial_state(3), [g("H", 0), g("H", 1), g("H", 2)] + rnd * 2)
    three = run_circuit(initial_state(3), [g("H", 0), g("H", 1), g("H", 2)] + rnd * 3)
    assert probabilities(three)[5] < probabilities(two)[5]


# ---------- Bloch vectors and fidelity ----------
@pytest.mark.parametrize("circuit, vec", [
    ([], (0, 0, 1)),
    ([g("X", 0)], (0, 0, -1)),
    ([g("H", 0)], (1, 0, 0)),
    ([g("H", 0), g("S", 0)], (0, 1, 0)),
])
def test_bloch_vectors(circuit, vec):
    assert np.allclose(bloch_vector(run_circuit(ZERO, circuit)), vec)


def test_entangled_qubit_has_short_bloch_vector():
    bell = run_circuit(initial_state(2), [g("H", 0), {"gate": "CNOT", "controls": [0], "targets": [1]}])
    assert np.allclose(bloch_vector(bell, 0), (0, 0, 0))


def test_fidelity_ignores_global_phase_and_scores_half_way():
    assert fidelity(-1j * ONE, ONE) == pytest.approx(1)
    assert fidelity(PLUS, ONE) == pytest.approx(0.5)
    assert fidelity(ZERO, ONE) == pytest.approx(0)
