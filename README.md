# Qubit Quest

A puzzle game that teaches quantum computing. Each level gives you a start state and a target;
place gates to get there and watch the qubit move on a Bloch sphere.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py                 # play from level 1-1
python main.py --level 5-1     # jump to a level
python -m pytest               # run the tests
```

## Controls

| Action | How |
|---|---|
| Choose a gate | Click a gate button (1-qubit levels place it straight away) |
| Place it | Click a qubit wire. For CNOT: click the control, then the target |
| Run | Enter or Space |
| Undo / reset / hint | Backspace / R / H |
| Next level (after clearing) | N |

## Project layout

```
quantum/simulator.py   statevector simulator: gates, Grover oracle/diffusion, fidelity, Bloch vectors
game/level.py          loads level files, checks answers, gives stars
game/state.py          what the player is doing (chosen gate, circuit, hints) - no Pygame, so it's testable
game/app.py            Pygame window: spheres, amplitude bars, palette, circuit
levels/*.json          one file per level
tests/                 pytest tests; test_against_qiskit.py runs only if Qiskit is installed
main.py                starts the game
```

## Conventions

* **Qubit 0 is the leftmost bit.** For 2 qubits the order is |00>, |01>, |10>, |11>. Qiskit uses
  the opposite order; `tests/test_against_qiskit.py` converts between them.
* A level is cleared when fidelity |<target|state>|^2 is at least 0.999.
* Stars: 1 = cleared, 2 = within par, 3 = within par with no hints.

## Adding a level

Copy a file in `levels/`, give it a new `id` like `2-5`, and fill in:

```json
{
  "id": "2-5", "name": "Only H and T", "world": 2, "qubits": 1,
  "start": "0",
  "target": {"amplitudes": [0.7071, [0.5, 0.5]]},
  "gates": {"H": 2, "T": 2}, "par": 2,
  "intro": "One sentence telling the player the goal.",
  "hints": ["gentle", "clearer", "the answer"],
  "learned": "What this level taught.",
  "solution": [{"gate": "H", "targets": [0]}, {"gate": "T", "targets": [0]}]
}
```

* `start` / `target`: a bit string like `"01"`, or `{"amplitudes": [...]}` where each amplitude is
  a number or `[real, imag]`. Amplitudes are normalised for you.
* Grover levels also need `"oracle": "10"` (the marked item).
* Then run `python -m pytest`: the tests check that your `solution` clears the level within par.

## What's here and what's next

Done: simulator with tests, 6 sample levels (one per idea: 1-1, 2-3, 2-4, 3-1, 4-2, 5-1),
win check and stars, a playable Pygame screen.

Suggested next steps for the team:

* **Developer 1 (core):** write the rest of the 15-20 levels; add a level-select / save file for stars.
* **Developer 2 (visuals):** smooth arrow animation between gates; let the player drag to rotate
  the sphere; nicer amplitude bars.
* **Developer 3 (UI):** drag-and-drop instead of click-to-place; menus; the "show the math" panel;
  package with `pyinstaller --onefile main.py`.
