"""World select screen: the five worlds sit on a path.  World 1 is open; every other world is
wrapped in a chain with a padlock until all levels of the worlds before it are cleared.
When a world opens, the chain bursts outward and the padlock floats away.

  Left / Right    choose a world        Enter / click    play it        Esc    quit
"""
from __future__ import annotations

import math
import random

import pygame

from game.app import ACCENT, BG, GOLD, H, INK, PANEL, QUIET, TEAL, W, text

WORLD_NAMES = {1: "Flip Fields", 2: "Superposition Sea", 3: "Entangled Woods",
               4: "Triple Tangle Peaks", 5: "Oracle Vault"}
WORLD_COLORS = {1: TEAL, 2: (74, 140, 222), 3: (150, 104, 214), 4: ACCENT, 5: GOLD}
STEEL = (176, 182, 200)
CHAIN = (118, 124, 148)
R = 56                     # planet radius
UNLOCK_ANIM = 1.1          # seconds for the chain-bursting animation
FADE_IN = 0.3


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class WorldMap:
    def __init__(self, screen: pygame.Surface, state):
        self.screen, self.state = screen, state
        self.big = pygame.font.SysFont(None, 60)
        self.font = pygame.font.SysFont(None, 28)
        self.small = pygame.font.SysFont(None, 21)
        self.num = pygame.font.SysFont(None, 64)
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        rng = random.Random(11)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.2), rng.uniform(0, math.tau))
                      for _ in range(110)]
        self.t = 0.0
        self.shown_at = 0.0
        self.selected = state.level.world
        self.hover: int | None = None
        self.shake: dict[int, float] = {}        # world -> time the player poked its lock
        self.unlocking: dict[int, float] = {}    # world -> time its unlock animation started
        self.seen_open = {w for w in state.worlds() if state.world_unlocked(w)}
        self.message = ""

    # ---------- state ----------
    def show(self, world: int | None = None):
        """Called whenever the map comes on screen; starts unlock animations for newly opened worlds."""
        self.shown_at = self.t
        self.message = ""
        if world is not None:
            self.selected = world
        for w in self.state.worlds():
            if self.state.world_unlocked(w) and w not in self.seen_open:
                self.seen_open.add(w)
                self.unlocking[w] = self.t + 0.35       # small pause so the player sees it happen
                self.selected = w
                self.message = f"World {w}: {WORLD_NAMES.get(w, '')} is now open!"

    def update(self, dt: float):
        self.t += dt

    def positions(self) -> dict[int, tuple[float, float]]:
        ws = self.state.worlds()
        span = W - 260
        return {w: (130 + span * i / max(1, len(ws) - 1), 300 if i % 2 else 380) for i, w in enumerate(ws)}

    def hit(self, pos) -> int | None:
        for w, (x, y) in self.positions().items():
            if math.hypot(pos[0] - x, pos[1] - y) <= R + 14:
                return w
        return None

    def try_enter(self, w: int):
        if self.state.world_unlocked(w):
            return w
        self.shake[w] = self.t
        ws = self.state.worlds()
        prev = ws[ws.index(w) - 1]
        self.message = f"World {w} is locked. Clear every level in World {prev} to open it."
        return None

    def handle_event(self, event):
        """Returns a world number to play, "quit", or None."""
        ws = self.state.worlds()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected = ws[max(0, ws.index(self.selected) - 1)]
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected = ws[min(len(ws) - 1, ws.index(self.selected) + 1)]
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return self.try_enter(self.selected)
        elif event.type == pygame.MOUSEMOTION:
            self.hover = self.hit(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            w = self.hit(event.pos)
            if w is not None:
                self.selected = w
                return self.try_enter(w)
        return None

    # ---------- drawing ----------
    def draw(self):
        scr, t = self.screen, self.t
        scr.fill(BG)
        for x, y, speed, phase in self.stars:
            b = 0.3 + 0.5 * (0.5 + 0.5 * math.sin(t * speed + phase))
            pygame.draw.circle(scr, _mix(BG, QUIET, b), (int(x), int((y - t * speed * 3) % H)), 1 if speed < 1.6 else 2)

        text(scr, self.big, "Choose Your World", (W // 2, 70), INK, center=True)
        text(scr, self.small, "Clear every level in a world to unlock the next one", (W // 2, 112), QUIET, center=True)

        pos = self.positions()
        ws = self.state.worlds()
        for a, b in zip(ws, ws[1:]):                       # dotted path between worlds
            (x1, y1), (x2, y2) = pos[a], pos[b]
            open_ = self.state.world_unlocked(b) and b not in self._still_locked_visually()
            d = math.hypot(x2 - x1, y2 - y1)
            for k in range(int((d - 2 * R - 20) / 14) + 1):
                s = (R + 10 + k * 14) / d
                pygame.draw.circle(scr, GOLD if open_ else PANEL, (int(x1 + (x2 - x1) * s), int(y1 + (y2 - y1) * s)), 3)

        for w in ws:
            self.draw_world(w, *pos[w])

        if self.message:
            text(scr, self.font, self.message, (W // 2, H - 72), GOLD, center=True)
        text(scr, self.small, "Left / Right choose  |  Enter or click to play  |  Esc quit", (W // 2, H - 30), QUIET, center=True)

        fade = 1 - (self.t - self.shown_at) / FADE_IN
        if fade > 0:
            veil = pygame.Surface((W, H))
            veil.fill(BG)
            veil.set_alpha(int(255 * fade))
            scr.blit(veil, (0, 0))
        pygame.display.flip()

    def _still_locked_visually(self) -> set[int]:
        return {w for w, start in self.unlocking.items() if self.t < start}

    def draw_world(self, w: int, x: float, y: float):
        scr, t = self.screen, self.t
        unlocked = self.state.world_unlocked(w)
        start = self.unlocking.get(w)
        p = None if start is None else (t - start) / UNLOCK_ANIM   # unlock animation progress
        looks_locked = not unlocked or (p is not None and p < 0)

        if w in self.shake:                                       # poke a locked world -> it rattles
            k = t - self.shake[w]
            x += 7 * math.sin(k * 45) * max(0.0, 1 - k / 0.4)
        cx, cy = int(x), int(y)
        sel, hov = w == self.selected, w == self.hover

        if sel or hov:                                            # selection orbit
            rr = R + 20 + 2 * math.sin(t * 3)
            pygame.draw.circle(scr, GOLD if sel else QUIET, (cx, cy), int(rr), 2)

        if looks_locked:
            pygame.draw.circle(scr, PANEL, (cx, cy), R)
            pygame.draw.circle(scr, _mix(PANEL, QUIET, 0.4), (cx, cy), R, 2)
            self.draw_chain(scr, cx, cy, R + 12, t * 0.25, CHAIN)
            self.draw_padlock(scr, cx, cy, STEEL)
        else:
            col = WORLD_COLORS.get(w, TEAL)
            glow = 0.5 + 0.5 * math.sin(t * 2 + w)
            pygame.draw.circle(scr, _mix(BG, col, 0.25 + 0.1 * glow), (cx, cy), R + 8)
            pygame.draw.circle(scr, col, (cx, cy), R)
            pygame.draw.circle(scr, _mix(col, (255, 255, 255), 0.35), (cx - R // 2, cy - R // 2), R // 5)
            pygame.draw.circle(scr, _mix(col, BG, 0.3), (cx, cy), R, 3)
            text(scr, self.num, str(w), (cx, cy + 3), BG, center=True)

            if p is not None and p < 1:                          # chain bursts, padlock floats away
                lay = self.layer
                lay.fill((0, 0, 0, 0))
                e = 1 - (1 - p) ** 2
                self.draw_chain(lay, cx, cy, R + 12 + 45 * e, t * 0.25 + e, CHAIN)
                self.draw_padlock(lay, cx, cy - int(60 * e), STEEL, open_shackle=True)
                lay.set_alpha(int(255 * (1 - p)))
                scr.blit(lay, (0, 0))
                if p < 0.35:                                     # quick flash ring
                    pygame.draw.circle(scr, GOLD, (cx, cy), int(R + 30 * p / 0.35), 3)

        # labels
        ly = cy + R + 36
        text(scr, self.small, f"WORLD {w}", (cx, ly), QUIET, center=True)
        text(scr, self.font, WORLD_NAMES.get(w, f"World {w}"), (cx, ly + 22), QUIET if looks_locked else INK, center=True)
        if looks_locked:
            text(scr, self.small, "Locked", (cx, ly + 46), _mix(QUIET, BG, 0.3), center=True)
        else:
            done, total, stars, most = self.state.world_progress(w)
            text(scr, self.small, f"{done}/{total} levels   {stars}/{most} stars", (cx, ly + 46), GOLD if done == total else QUIET, center=True)

    @staticmethod
    def draw_chain(surf, cx, cy, radius, spin, color):
        """A ring of chain links around the planet: flat links alternate with side-on rings."""
        n = 22
        for k in range(n):
            a0 = spin + k * math.tau / n
            a1 = a0 + math.tau / n * 0.75
            p0 = (cx + radius * math.cos(a0), cy + radius * math.sin(a0))
            p1 = (cx + radius * math.cos(a1), cy + radius * math.sin(a1))
            if k % 2 == 0:
                pygame.draw.line(surf, color, p0, p1, 6)
                pygame.draw.line(surf, _mix(color, BG, 0.5), p0, p1, 2)
            else:
                mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
                pygame.draw.circle(surf, color, (int(mid[0]), int(mid[1])), 6, 2)

    @staticmethod
    def draw_padlock(surf, cx, cy, color, open_shackle=False):
        body = pygame.Rect(cx - 20, cy - 6, 40, 30)
        lift = 9 if open_shackle else 0
        pygame.draw.arc(surf, color, pygame.Rect(cx - 13, cy - 30 - lift, 26, 34), 0, math.pi, 5)
        pygame.draw.line(surf, color, (cx - 11, cy - 14 - lift), (cx - 11, cy - 4 - (lift if open_shackle else 0)), 5)
        if not open_shackle:
            pygame.draw.line(surf, color, (cx + 11, cy - 14), (cx + 11, cy - 4), 5)
        pygame.draw.rect(surf, color, body, border_radius=6)
        pygame.draw.rect(surf, _mix(color, BG, 0.4), body, 2, border_radius=6)
        pygame.draw.circle(surf, BG, (cx, cy + 5), 5)
        pygame.draw.rect(surf, BG, (cx - 2, cy + 6, 4, 10))
