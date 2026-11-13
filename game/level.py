"""Loading levels and checking the player's answer. No Pygame here, so it is easy to test."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from quantum.simulator import initial_state, fidelity, run_circuit

LEVEL_DIR = Path(__file__).resolve().parent.parent / "levels"
PASS_FIDELITY = 0.999


def parse_state(spec, n_qubits: int) -> np.ndarray:
    """A state in a level file is either a bit string like "01",
    or {"amplitudes": [...]} where each amplitude is a number or [real, imag]."""
    if isinstance(spec, str):
        return initial_state(n_qubits, spec)
    amps = [complex(a[0], a[1]) if isinstance(a, list) else complex(a) for a in spec["amplitudes"]]
    if len(amps) != 2**n_qubits:
        raise ValueError(f"need {2**n_qubits} amplitudes, got {len(amps)}")
    state = np.array(amps, dtype=complex)
    return state / np.linalg.norm(state)


@dataclass
class Result:
    fidelity: float
    cleared: bool
    stars: int
    message: str


@dataclass
class Level:
    id: str
    name: str
    world: int
    qubits: int
    start: np.ndarray
    target: np.ndarray
    gates: dict[str, int]          # gate name -> how many the player may use
    par: int
    hints: list[str] = field(default_factory=list)
    intro: str = ""
    learned: str = ""
    oracle: str | None = None      # marked item for Grover levels
    solution: list[dict] = field(default_factory=list)  # hidden; used by tests

    @classmethod
    def from_file(cls, path: str | Path) -> "Level":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n = data["qubits"]
        return cls(
            id=data["id"], name=data["name"], world=data["world"], qubits=n,
            start=parse_state(data["start"], n), target=parse_state(data["target"], n),
            gates=data["gates"], par=data["par"], hints=data.get("hints", []),
            intro=data.get("intro", ""), learned=data.get("learned", ""),
            oracle=data.get("oracle"), solution=data.get("solution", []),
        )

    # ---- rules ----
    def gates_left(self, circuit: list[dict]) -> dict[str, int]:
        used = Counter(step["gate"].upper() for step in circuit)
        return {g: n - used.get(g, 0) for g, n in self.gates.items()}

    def can_place(self, gate: str, circuit: list[dict]) -> bool:
        return self.gates_left(circuit).get(gate.upper(), 0) > 0

    def prepare(self, step: dict) -> dict:
        """Fill in level-specific details, e.g. which item the Grover oracle marks."""
        if step["gate"].upper() == "ORACLE":
            return {**step, "marked": self.oracle}
        return step

    def state_after(self, circuit: list[dict]) -> np.ndarray:
        return run_circuit(self.start, [self.prepare(s) for s in circuit])

    def check(self, circuit: list[dict], hints_used: int = 0) -> Result:
        for gate, left in self.gates_left(circuit).items():
            if left < 0:
                return Result(0.0, False, 0, f"Too many {gate} gates")
        if any(s["gate"].upper() not in self.gates for s in circuit):
            return Result(0.0, False, 0, "That gate is not allowed in this level")
        f = fidelity(self.state_after(circuit), self.target)
        if f < PASS_FIDELITY:
            return Result(f, False, 0, f"Not yet: {f:.0%} match")
        stars = 1 + (len(circuit) <= self.par) + (len(circuit) <= self.par and hints_used == 0)
        return Result(f, True, stars, "Level clear!")


def all_levels() -> list[Level]:
    """Every level, in play order (sorted by world, then level number)."""
    levels = [Level.from_file(p) for p in LEVEL_DIR.glob("*.json")]
    return sorted(levels, key=lambda lv: tuple(int(x) for x in lv.id.split("-")))
