"""Cross-check every level's solution against Qiskit. Skipped if Qiskit is not installed."""
import numpy as np
import pytest

qiskit = pytest.importorskip("qiskit")
from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Statevector  # noqa: E402

from game.level import all_levels  # noqa: E402
from quantum.simulator import fidelity  # noqa: E402


def _mcz(qc: QuantumCircuit, qubits: list[int]):
    """Multi-controlled Z on all listed qubits."""
    *ctrl, tgt = qubits
    qc.h(tgt)
    if len(ctrl) == 1:
        qc.cx(ctrl[0], tgt)
    else:
        qc.mcx(ctrl, tgt)
    qc.h(tgt)


def to_qiskit(n: int, start_bits: str, circuit: list[dict], marked: str | None) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for q, b in enumerate(start_bits):
        if b == "1":
            qc.x(q)
    for step in circuit:
        g, t, c = step["gate"].upper(), step.get("targets", []), step.get("controls", [])
        if g in ("X", "Y", "Z", "H", "S", "T"):
            getattr(qc, g.lower())(t[0])
        elif g in ("RX", "RY", "RZ"):
            getattr(qc, g.lower())(step["theta"], t[0])
        elif g == "CNOT":
            qc.cx(c[0], t[0])
        elif g == "CZ":
            qc.cz(c[0], t[0])
        elif g == "TOFFOLI":
            qc.ccx(c[0], c[1], t[0])
        elif g == "SWAP":
            qc.swap(t[0], t[1])
        elif g == "ORACLE":
            zeros = [q for q, b in enumerate(marked) if b == "0"]
            for q in zeros:
                qc.x(q)
            _mcz(qc, list(range(n)))
            for q in zeros:
                qc.x(q)
        elif g == "DIFFUSION":
            for q in range(n):
                qc.h(q); qc.x(q)
            _mcz(qc, list(range(n)))
            for q in range(n):
                qc.x(q); qc.h(q)
        else:
            raise ValueError(g)
    return qc


LEVELS = [lv for lv in all_levels() if np.count_nonzero(lv.start) == 1]  # basis-state starts


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv.id)
def test_level_solution_matches_qiskit(level):
    start_bits = format(int(np.flatnonzero(level.start)[0]), f"0{level.qubits}b")
    qc = to_qiskit(level.qubits, start_bits, level.solution, level.oracle)
    # Qiskit puts qubit 0 on the right; reverse so qubit 0 is the leftmost bit, like ours.
    theirs = Statevector.from_instruction(qc).reverse_qargs().data
    ours = level.state_after(level.solution)
    assert fidelity(ours, theirs) == pytest.approx(1, abs=1e-9)
