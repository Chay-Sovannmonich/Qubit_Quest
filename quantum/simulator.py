"""Statevector simulator for Qubit Quest (1 to 3 qubits).

Conventions
-----------
* Qubit 0 is the LEFTMOST bit: for 2 qubits the basis order is |00>, |01>, |10>, |11>,
  where the first digit is qubit 0. (Qiskit uses the opposite order; the tests handle that.)
* A state is a 1-D numpy array of complex numbers with length 2**n.
* A circuit is a list of steps. Each step is a dict, for example:
      {"gate": "H", "targets": [0]}
      {"gate": "CNOT", "controls": [0], "targets": [1]}
      {"gate": "RY", "targets": [0], "theta": 1.5708}
      {"gate": "ORACLE", "marked": "10"}      # Grover: flips the sign of |10>
      {"gate": "DIFFUSION"}                    # Grover: reflection about the average
"""
from __future__ import annotations

import numpy as np

SQ2 = 1 / np.sqrt(2)

# ---------- single-qubit gate matrices ----------
GATES_1Q = {
    "I": np.eye(2, dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
    "H": SQ2 * np.array([[1, 1], [1, -1]], dtype=complex),
    "S": np.array([[1, 0], [0, 1j]], dtype=complex),
    "T": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
}


def rotation(axis: str, theta: float) -> np.ndarray:
    """Rotation gate RX, RY or RZ by angle theta (radians)."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    if axis == "RX":
        return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)
    if axis == "RY":
        return np.array([[c, -s], [s, c]], dtype=complex)
    if axis == "RZ":
        return np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=complex)
    raise ValueError(f"unknown rotation {axis}")


# Gates that act on two or three qubits, with how many controls they take.
CONTROLLED = {"CNOT": ("X", 1), "CZ": ("Z", 1), "TOFFOLI": ("X", 2)}
ALL_GATES = set(GATES_1Q) | {"RX", "RY", "RZ"} | set(CONTROLLED) | {"SWAP", "ORACLE", "DIFFUSION"}


# ---------- states ----------
def initial_state(n_qubits: int, bits: str | None = None) -> np.ndarray:
    """Basis state |bits>, e.g. initial_state(2, "01"). Defaults to all zeros."""
    bits = bits or "0" * n_qubits
    if len(bits) != n_qubits or set(bits) - {"0", "1"}:
        raise ValueError(f"bits {bits!r} do not match {n_qubits} qubits")
    state = np.zeros(2**n_qubits, dtype=complex)
    state[int(bits, 2)] = 1
    return state


def n_qubits_of(state: np.ndarray) -> int:
    n = int(round(np.log2(len(state))))
    if 2**n != len(state):
        raise ValueError("state length must be a power of 2")
    return n


# ---------- applying gates ----------
def apply_1q(state: np.ndarray, U: np.ndarray, target: int) -> np.ndarray:
    """Apply a 2x2 matrix U to one qubit."""
    n = n_qubits_of(state)
    psi = state.reshape([2] * n)
    psi = np.tensordot(U, psi, axes=([1], [target]))  # new axis 0 = target
    psi = np.moveaxis(psi, 0, target)
    return psi.reshape(-1)


def apply_controlled(state: np.ndarray, U: np.ndarray, controls: list[int], target: int) -> np.ndarray:
    """Apply U to `target` only where every control qubit is 1."""
    n = n_qubits_of(state)
    if target in controls or len(set(controls)) != len(controls):
        raise ValueError("control and target qubits must all be different")
    psi = state.reshape([2] * n).copy()
    idx = [slice(None)] * n
    for c in controls:
        idx[c] = 1
    sub = psi[tuple(idx)]                       # axes left: the non-control qubits, in order
    remaining = [q for q in range(n) if q not in controls]
    t_axis = remaining.index(target)
    sub = np.moveaxis(np.tensordot(U, sub, axes=([1], [t_axis])), 0, t_axis)
    psi[tuple(idx)] = sub
    return psi.reshape(-1)


def apply_swap(state: np.ndarray, a: int, b: int) -> np.ndarray:
    n = n_qubits_of(state)
    return np.swapaxes(state.reshape([2] * n), a, b).reshape(-1)


def apply_oracle(state: np.ndarray, marked: str) -> np.ndarray:
    """Grover oracle: flip the sign of the marked basis state, e.g. marked='10'."""
    out = state.copy()
    out[int(marked, 2)] *= -1
    return out


def apply_diffusion(state: np.ndarray) -> np.ndarray:
    """Grover diffusion: reflect every amplitude about the average (2|s><s| - I)."""
    return 2 * state.mean() - state


def apply_step(state: np.ndarray, step: dict) -> np.ndarray:
    """Apply one circuit step (see the module docstring for the format)."""
    gate = step["gate"].upper()
    targets = step.get("targets", [])
    controls = step.get("controls", [])
    if gate in GATES_1Q:
        return apply_1q(state, GATES_1Q[gate], targets[0])
    if gate in ("RX", "RY", "RZ"):
        return apply_1q(state, rotation(gate, float(step["theta"])), targets[0])
    if gate in CONTROLLED:
        base, n_ctrl = CONTROLLED[gate]
        if len(controls) != n_ctrl:
            raise ValueError(f"{gate} needs {n_ctrl} control qubit(s)")
        return apply_controlled(state, GATES_1Q[base], controls, targets[0])
    if gate == "SWAP":
        return apply_swap(state, targets[0], targets[1])
    if gate == "ORACLE":
        return apply_oracle(state, step["marked"])
    if gate == "DIFFUSION":
        return apply_diffusion(state)
    raise ValueError(f"unknown gate {gate}")


def run_circuit(start: np.ndarray, circuit: list[dict]) -> np.ndarray:
    """Run every step in order and return the final state."""
    state = np.asarray(start, dtype=complex)
    for step in circuit:
        state = apply_step(state, step)
    return state


# ---------- reading results ----------
def fidelity(state: np.ndarray, target: np.ndarray) -> float:
    """|<target|state>|^2 for normalised states. Ignores global phase. 1 = perfect match."""
    a = state / np.linalg.norm(state)
    b = target / np.linalg.norm(target)
    return float(abs(np.vdot(b, a)) ** 2)


def probabilities(state: np.ndarray) -> np.ndarray:
    return np.abs(state) ** 2


def reduced_density_matrix(state: np.ndarray, qubit: int) -> np.ndarray:
    """2x2 density matrix of one qubit, with the other qubits traced out."""
    n = n_qubits_of(state)
    psi = np.moveaxis(state.reshape([2] * n), qubit, 0).reshape(2, -1)
    return psi @ psi.conj().T


def bloch_vector(state: np.ndarray, qubit: int = 0) -> tuple[float, float, float]:
    """(x, y, z) of one qubit. Length 1 = pure; shorter = entangled with other qubits."""
    rho = reduced_density_matrix(state, qubit)
    x = 2 * rho[0, 1].real
    y = 2 * rho[1, 0].imag
    z = (rho[0, 0] - rho[1, 1]).real
    return float(x), float(y), float(z)


def basis_labels(n_qubits: int) -> list[str]:
    return [format(i, f"0{n_qubits}b") for i in range(2**n_qubits)]
