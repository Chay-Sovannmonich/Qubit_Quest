"""What the player is doing right now: chosen gate, circuit so far, hints, result.

No Pygame here, so the rules can be tested on their own. game/app.py turns mouse clicks
and key presses into calls on GameState, then draws whatever GameState says.
"""
from __future__ import annotations

from game.level import Level, Result
from quantum.simulator import CONTROLLED, bloch_vector, probabilities

WHOLE_REGISTER = {"ORACLE", "DIFFUSION"}   # act on every qubit, placed with one click
DEFAULT_THETA = 1.5707963267948966          # rotations default to a quarter turn (pi/2)


def wires_needed(gate: str) -> int:
    if gate in CONTROLLED:
        return CONTROLLED[gate][1] + 1      # controls + target
    if gate == "SWAP":
        return 2
    if gate in WHOLE_REGISTER:
        return 0
    return 1


class GameState:
    def __init__(self, levels: list[Level], start_index: int = 0):
        self.levels = levels
        self.best: dict[str, int] = {}          # level id -> best stars earned (cleared levels only)
        self.index = start_index
        self.load(start_index)

    # ---- worlds ----
    def worlds(self) -> list[int]:
        return sorted({lv.world for lv in self.levels})

    def world_level_indexes(self, world: int) -> list[int]:
        return [i for i, lv in enumerate(self.levels) if lv.world == world]

    def world_unlocked(self, world: int) -> bool:
        """The first world is always open; any other opens once every level before it is cleared."""
        return all(lv.id in self.best for lv in self.levels if lv.world < world)

    def world_progress(self, world: int) -> tuple[int, int, int, int]:
        """(levels cleared, levels total, stars earned, stars possible)."""
        ids = [self.levels[i].id for i in self.world_level_indexes(world)]
        cleared = [i for i in ids if i in self.best]
        return len(cleared), len(ids), sum(self.best[i] for i in cleared), 3 * len(ids)

    def enter_world(self, world: int) -> bool:
        """Load the first unfinished level of a world (or its first level if all are done)."""
        indexes = self.world_level_indexes(world)
        if not indexes or not self.world_unlocked(world):
            return False
        self.load(next((i for i in indexes if self.levels[i].id not in self.best), indexes[0]))
        return True

    # ---- level control ----
    def load(self, index: int):
        self.index = max(0, min(index, len(self.levels) - 1))
        self.circuit: list[dict] = []
        self.selected: str | None = None
        self.picked_wires: list[int] = []
        self.hints_used = 0
        self.result: Result | None = None
        self.message = self.level.intro

    @property
    def level(self) -> Level:
        return self.levels[self.index]

    def next_level(self) -> bool:
        if self.result and self.result.cleared and self.index + 1 < len(self.levels):
            self.load(self.index + 1)
            return True
        return False

    # ---- building the circuit ----
    def select_gate(self, gate: str):
        gate = gate.upper()
        if not self.level.can_place(gate, self.circuit):
            self.message = f"No {gate} gates left"
            return
        self.result = None
        self.picked_wires = []
        if wires_needed(gate) == 0:
            self._add({"gate": gate})
        elif wires_needed(gate) == 1 and self.level.qubits == 1:
            self._add({"gate": gate, "targets": [0]})
        else:
            self.selected = gate
            self.message = self._prompt()

    def click_wire(self, qubit: int):
        if not self.selected or qubit in self.picked_wires:
            return
        self.picked_wires.append(qubit)
        gate, need = self.selected, wires_needed(self.selected)
        if len(self.picked_wires) < need:
            self.message = self._prompt()
            return
        w = self.picked_wires
        if gate in CONTROLLED:
            step = {"gate": gate, "controls": w[:-1], "targets": [w[-1]]}
        else:
            step = {"gate": gate, "targets": list(w)}
        self._add(step)

    def _add(self, step: dict):
        if step["gate"] in ("RX", "RY", "RZ"):
            step["theta"] = DEFAULT_THETA
        self.circuit.append(step)
        self.selected, self.picked_wires = None, []
        self.message = f"{len(self.circuit)} gate(s) placed. Press Enter to run."

    def _prompt(self) -> str:
        gate, k = self.selected, len(self.picked_wires)
        if gate in CONTROLLED:
            n_ctrl = CONTROLLED[gate][1]
            return f"{gate}: click control qubit {k + 1}" if k < n_ctrl else f"{gate}: click the target qubit"
        if gate == "SWAP":
            return "SWAP: click the first qubit" if k == 0 else "SWAP: click the second qubit"
        return f"{gate}: click a qubit wire"

    def undo(self):
        if self.selected:
            self.selected, self.picked_wires = None, []
        elif self.circuit:
            self.circuit.pop()
        self.result = None
        self.message = "Undone"

    def reset(self):
        hints = self.hints_used
        self.load(self.index)
        self.hints_used = hints                 # resetting does not refund hints

    # ---- results ----
    def run(self) -> Result:
        self.result = self.level.check(self.circuit, self.hints_used)
        self.message = self.result.message
        if self.result.cleared:
            lid = self.level.id
            self.best[lid] = max(self.best.get(lid, 0), self.result.stars)
            self.message +=f"  {'*' * self.result.stars}  {self.level.learned}"
        return self.result

    def hint(self) -> str:
        if self.hints_used < len(self.level.hints):
            self.hints_used += 1
        self.message = "Hint: " + self.level.hints[self.hints_used - 1] if self.level.hints else "No hints here"
        return self.message

    # ---- what to draw ----
    def current_state(self):
        return self.level.state_after(self.circuit)

    def bloch_vectors(self):
        s = self.current_state()
        return [bloch_vector(s, q) for q in range(self.level.qubits)]

    def target_bloch_vectors(self):
        return [bloch_vector(self.level.target, q) for q in range(self.level.qubits)]

    def probabilities(self):
        return probabilities(self.current_state())

    def target_probabilities(self):
        return probabilities(self.level.target)
