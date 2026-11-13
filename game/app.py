"""Pygame window: draws the Bloch spheres, amplitude bars, circuit and gate palette.

Controls
  click a gate button   choose a gate (1-qubit levels place it straight away)
  click a qubit wire    place the chosen gate; for CNOT click control, then target
  Enter / Space         run the circuit
  Backspace             undo        R  reset        H  hint
  N                     next level (after you clear one)        Esc  back to the world map
"""
from __future__ import annotations

import cmath
import math

import pygame

from game.state import GameState
from quantum.simulator import CONTROLLED, basis_labels

W, H = 1000, 660
BG = (31, 34, 51)
PANEL = (42, 46, 66)
INK = (240, 241, 246)
QUIET = (154, 160, 184)
ACCENT = (228, 87, 46)     # player's arrow
TEAL = (42, 157, 143)      # target
GOLD = (233, 196, 106)

CIRCUIT_X, CIRCUIT_Y, WIRE_GAP, COL_W = 90, 470, 44, 64


# ---------- small drawing helpers ----------
def text(surf, font, s, pos, color=INK, center=False):
    img = font.render(s, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)
    return rect


def wrap(font, s, width):
    words, lines, line = s.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] > width and line:
            lines.append(line)
            line = w
        else:
            line = test
    return lines + ([line] if line else [])


def project(cx, cy, r, x, y, z):
    """Simple oblique view of the sphere: +y to the right, +z up, +x toward the viewer (down-left)."""
    return cx + r * (y - 0.35 * x), cy - r * (z - 0.22 * x)


def draw_bloch(surf, font, cx, cy, r, vec, target, label):
    pygame.draw.circle(surf, QUIET, (cx, cy), r, 1)
    pts = [project(cx, cy, r, math.cos(t), math.sin(t), 0) for t in [i * math.pi / 30 for i in range(61)]]
    for i in range(0, 60, 2):                                    # dashed equator
        pygame.draw.line(surf, QUIET, pts[i], pts[i + 1], 1)
    pygame.draw.line(surf, PANEL, (cx, cy - r), (cx, cy + r), 1)  # z-axis
    text(surf, font, "|0>", (cx, cy - r - 14), QUIET, center=True)
    text(surf, font, "|1>", (cx, cy + r + 14), QUIET, center=True)
    tx, ty = project(cx, cy, r, *target)                          # target ghost
    pygame.draw.circle(surf, TEAL, (int(tx), int(ty)), max(6, r // 12), 2)
    ex, ey = project(cx, cy, r, *vec)                             # state arrow
    pygame.draw.line(surf, ACCENT, (cx, cy), (ex, ey), 4)
    pygame.draw.circle(surf, ACCENT, (int(ex), int(ey)), max(5, r // 16))
    pygame.draw.circle(surf, ACCENT, (cx, cy), 4)
    text(surf, font, label, (cx, cy + r + 36), QUIET, center=True)


def phase_color(amp: complex):
    c = pygame.Color(0)
    c.hsva = ((math.degrees(cmath.phase(amp)) % 360), 65, 95, 100)
    return c


class App:
    def __init__(self, state: GameState, intro: bool = True, start_on_map: bool = True):
        self.intro = intro
        self.mode = "map" if start_on_map else "play"
        self.world_map = None
        pygame.init()
        pygame.display.set_caption("Qubit Quest")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.big = pygame.font.SysFont(None, 40)
        self.font = pygame.font.SysFont(None, 26)
        self.small = pygame.font.SysFont(None, 21)
        self.state = state
        self.buttons: list[tuple[pygame.Rect, str]] = []

    # ---------- input ----------
    def on_click(self, pos):
        for rect, gate in self.buttons:
            if rect.collidepoint(pos):
                self.state.select_gate(gate)
                return
        n = self.state.level.qubits
        for q in range(n):
            wy = CIRCUIT_Y + q * WIRE_GAP
            if abs(pos[1] - wy) <= WIRE_GAP // 2 and CIRCUIT_X - 40 <= pos[0] <= W - 30:
                self.state.click_wire(q)
                return

    def on_key(self, key):
        s = self.state
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            s.run()
        elif key == pygame.K_BACKSPACE:
            s.undo()
        elif key == pygame.K_r:
            s.reset()
        elif key == pygame.K_h:
            s.hint()
        elif key == pygame.K_n and s.result and s.result.cleared:
            nxt = s.index + 1
            if nxt >= len(s.levels) or s.levels[nxt].world != s.level.world:
                self.show_map()                  # world finished: back to the map to see what opened
            else:
                s.next_level()

    def show_map(self):
        self.world_map.show(self.state.level.world)
        self.mode = "map"

    # ---------- drawing ----------
    def draw(self):
        s, lv, scr = self.state, self.state.level, self.screen
        scr.fill(BG)

        # header
        text(scr, self.small, f"WORLD {lv.world}  -  LEVEL {lv.id}  -  {lv.qubits} QUBIT{'S' if lv.qubits > 1 else ''}", (24, 16), QUIET)
        text(scr, self.big, lv.name, (24, 38))
        if s.result and s.result.cleared:
            text(scr, self.big, "*" * s.result.stars, (W - 120, 30), GOLD)

        # Bloch spheres (left)
        n = lv.qubits
        r = {1: 120, 2: 80, 3: 60}[n]
        centers = {1: [250], 2: [140, 360], 3: [95, 250, 405]}[n]
        for q, (cx, vec, tgt) in enumerate(zip(centers, s.bloch_vectors(), s.target_bloch_vectors())):
            draw_bloch(scr, self.small, cx, 245, r, vec, tgt, f"qubit {q}" if n > 1 else "")

        # amplitude bars (right)
        self.draw_bars(560, 110, 400, 250)

        # gate palette
        self.buttons = []
        left = s.level.gates_left(s.circuit)
        x = 24
        for gate, count in lv.gates.items():
            label = f"{gate}  x{left[gate]}"
            w = self.font.size(label)[0] + 24
            rect = pygame.Rect(x, 400, w, 36)
            on = s.selected == gate
            pygame.draw.rect(scr, ACCENT if on else PANEL, rect, border_radius=8)
            text(scr, self.font, label, rect.center, INK if left[gate] > 0 else QUIET, center=True)
            self.buttons.append((rect, gate))
            x += w + 10

        self.draw_circuit()

        # message area
        y = H - 74
        for line in wrap(self.small, s.message, W - 48)[:3]:
            text(scr, self.small, line, (24, y), GOLD if s.result and s.result.cleared else INK)
            y += 20
        text(scr, self.small, "Enter run  |  Backspace undo  |  R reset  |  H hint  |  N next level  |  Esc world map", (24, H - 22), QUIET)
        pygame.display.flip()

    def draw_bars(self, x0, y0, w, h):
        s, scr = self.state, self.screen
        probs, target, amps = s.probabilities(), s.target_probabilities(), s.current_state()
        labels = basis_labels(s.level.qubits)
        n = len(labels)
        gap = 10
        bw = (w - gap * (n - 1)) / n
        text(scr, self.small, "Amplitude bars (height = chance, colour = phase)", (x0, y0 - 28), QUIET)
        pygame.draw.line(scr, QUIET, (x0, y0 + h), (x0 + w, y0 + h), 1)
        for i in range(n):
            bx = x0 + i * (bw + gap)
            ph = probs[i] * h
            if ph > 0.5:
                pygame.draw.rect(scr, phase_color(amps[i]), (bx, y0 + h - ph, bw, ph), border_radius=4)
            th = target[i] * h
            if th > 0.5:
                pygame.draw.rect(scr, TEAL, (bx - 2, y0 + h - th - 2, bw + 4, th + 4), 2, border_radius=5)
            text(scr, self.small, f"|{labels[i]}>", (bx + bw / 2, y0 + h + 14), QUIET, center=True)
            text(scr, self.small, f"{probs[i]:.0%}", (bx + bw / 2, y0 + h - ph - 12), INK, center=True)

    def draw_circuit(self):
        s, scr, n = self.state, self.screen, self.state.level.qubits
        wire_y = [CIRCUIT_Y + q * WIRE_GAP for q in range(n)]
        for q, y in enumerate(wire_y):
            hot = s.selected and q not in s.picked_wires
            pygame.draw.line(scr, TEAL if hot else QUIET, (CIRCUIT_X, y), (W - 30, y), 2 if hot else 1)
            text(scr, self.small, f"q{q}", (CIRCUIT_X - 40, y - 8), QUIET)
            if q in s.picked_wires:
                pygame.draw.circle(scr, ACCENT, (CIRCUIT_X - 10, y), 6)

        for col, step in enumerate(s.circuit):
            cx = CIRCUIT_X + 40 + col * COL_W
            g = step["gate"]
            if g in ("ORACLE", "DIFFUSION"):
                rect = pygame.Rect(cx - 26, wire_y[0] - 18, 52, wire_y[-1] - wire_y[0] + 36)
                pygame.draw.rect(scr, TEAL if g == "ORACLE" else PANEL, rect, border_radius=6)
                text(scr, self.small, "OR" if g == "ORACLE" else "DIF", rect.center, INK, center=True)
            elif g in CONTROLLED:
                ys = [wire_y[c] for c in step["controls"]] + [wire_y[step["targets"][0]]]
                pygame.draw.line(scr, INK, (cx, min(ys)), (cx, max(ys)), 2)
                for c in step["controls"]:
                    pygame.draw.circle(scr, INK, (cx, wire_y[c]), 6)
                ty = wire_y[step["targets"][0]]
                if g == "CZ":
                    pygame.draw.circle(scr, INK, (cx, ty), 6)
                else:                                              # X target: circle with a plus
                    pygame.draw.circle(scr, BG, (cx, ty), 13)
                    pygame.draw.circle(scr, INK, (cx, ty), 13, 2)
                    pygame.draw.line(scr, INK, (cx - 13, ty), (cx + 13, ty), 2)
                    pygame.draw.line(scr, INK, (cx, ty - 13), (cx, ty + 13), 2)
            elif g == "SWAP":
                a, b = (wire_y[t] for t in step["targets"])
                pygame.draw.line(scr, INK, (cx, a), (cx, b), 2)
                for y in (a, b):
                    pygame.draw.line(scr, INK, (cx - 7, y - 7), (cx + 7, y + 7), 2)
                    pygame.draw.line(scr, INK, (cx - 7, y + 7), (cx + 7, y - 7), 2)
            else:
                y = wire_y[step["targets"][0]]
                rect = pygame.Rect(cx - 20, y - 16, 40, 32)
                pygame.draw.rect(scr, PANEL, rect, border_radius=6)
                pygame.draw.rect(scr, QUIET, rect, 1, border_radius=6)
                text(scr, self.small, g, rect.center, INK, center=True)

    # ---------- main loop ----------
    def run(self):
        if self.intro:
            from game.intro import Intro  # imported here: intro.py reuses this module's colours
            if not Intro(self.screen, self.clock).run():
                pygame.quit()
                return
        from game.world_map import WorldMap
        self.world_map = WorldMap(self.screen, self.state)
        if self.mode == "map":
            self.world_map.show()
        while True:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if self.mode == "map":
                    choice = self.world_map.handle_event(event)
                    if choice == "quit":
                        pygame.quit()
                        return
                    if isinstance(choice, int) and self.state.enter_world(choice):
                        self.mode = "play"
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.show_map()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.on_key(event.key)
            if self.mode == "map":
                self.world_map.update(dt)
                self.world_map.draw()
            else:
                self.draw()
