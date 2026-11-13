"""Animated title screen shown before the first level.

Each letter of the title starts as two "superposed" ghosts (teal |0> above, orange |1> below)
that wobble and collapse into a single solid letter, while a Bloch-sphere arrow precesses
underneath.  Any key or click skips the animation; a second press starts the game.  Esc quits.
"""
from __future__ import annotations

import math
import random

import pygame

from game.app import ACCENT, BG, GOLD, H, INK, PANEL, QUIET, TEAL, W, project, text

TITLE = "Qubit Quest"
TAGLINE = "Steer a qubit with quantum gates. Solve the puzzle."
PROMPT = "Press any key or click to begin"

LETTER_START, LETTER_STAGGER, LETTER_DUR = 0.4, 0.07, 0.9
TITLE_DONE = LETTER_START + LETTER_STAGGER * (len(TITLE) - 1) + LETTER_DUR
READY = TITLE_DONE + 0.6          # everything on screen, prompt showing
FADE_OUT = 0.35

TITLE_Y, TAG_Y = 165, 245
SPHERE_C, SPHERE_R = (W // 2, 430), 95


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class Intro:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen, self.clock = screen, clock
        self.title_font = pygame.font.SysFont(None, 128)
        self.tag_font = pygame.font.SysFont(None, 32)
        self.small = pygame.font.SysFont(None, 22)
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)

        rng = random.Random(7)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.2), rng.uniform(0, math.tau))
                      for _ in range(140)]

        # pre-render every letter in its three colours and work out where it sits
        total = self.title_font.size(TITLE)[0]
        x0 = (W - total) / 2
        self.letters = []
        for i, ch in enumerate(TITLE):
            if ch == " ":
                continue
            x = x0 + self.title_font.size(TITLE[:i])[0]
            imgs = {"solid": self.title_font.render(ch, True, INK),
                    "zero": self.title_font.render(ch, True, TEAL),
                    "one": self.title_font.render(ch, True, ACCENT)}
            self.letters.append((i, x, imgs))
        self.title_rect = pygame.Rect(x0, TITLE_Y - 50, total, 100)

    # ---------- drawing ----------
    def draw(self, t: float):
        scr = self.screen
        scr.fill(BG)
        self.draw_stars(t)
        self.draw_sphere(t)
        self.draw_title(t)

        if t > TITLE_DONE:                                    # gold underline grows out from the centre
            p = _ease((t - TITLE_DONE) / 0.5)
            half = self.title_rect.width / 2 * p
            cx, y = W / 2, TITLE_Y + 50
            pygame.draw.line(scr, GOLD, (cx - half, y), (cx + half, y), 3)

        tag_a = _ease((t - TITLE_DONE - 0.1) / 0.6)
        if tag_a > 0:
            img = self.tag_font.render(TAGLINE, True, QUIET)
            img.set_alpha(int(255 * tag_a))
            scr.blit(img, img.get_rect(center=(W // 2, TAG_Y + 12 * (1 - tag_a))))

        if t > READY:
            pulse = 0.55 + 0.45 * math.sin((t - READY) * 3.2)
            img = self.tag_font.render(PROMPT, True, INK)
            img.set_alpha(int(255 * pulse))
            scr.blit(img, img.get_rect(center=(W // 2, H - 70)))
            text(scr, self.small, "Esc to quit", (W // 2, H - 36), QUIET, center=True)

    def draw_stars(self, t: float):
        fade = _ease(t / 1.0)
        for x, y, speed, phase in self.stars:
            b = fade * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * speed + phase)))
            c = tuple(int(BG[k] + (QUIET[k] - BG[k]) * b) for k in range(3))
            yy = (y - t * speed * 4) % H                     # slow upward drift
            pygame.draw.circle(self.screen, c, (int(x), int(yy)), 1 if speed < 1.6 else 2)

    def draw_title(self, t: float):
        for i, x, imgs in self.letters:
            start = LETTER_START + LETTER_STAGGER * i
            if t < start:
                continue
            p = _ease((t - start) / LETTER_DUR)
            y = TITLE_Y - imgs["solid"].get_height() / 2
            if p < 1:
                amp = 38 * (1 - p)
                wob = math.sin(t * 11 + i * 1.7)
                appear = min(1.0, (t - start) / 0.25)
                for key, sign in (("zero", -1), ("one", 1)):
                    img = imgs[key]
                    img.set_alpha(int(150 * appear * (1 - p * 0.6)))
                    self.screen.blit(img, (x + 3 * wob * sign, y + sign * amp * (0.8 + 0.2 * wob)))
            solid = imgs["solid"]
            solid.set_alpha(int(255 * p ** 2))
            self.screen.blit(solid, (x, y))

    def draw_sphere(self, t: float):
        a = _ease((t - 0.8) / 1.0)
        if a <= 0:
            return
        lay = self.layer
        lay.fill((0, 0, 0, 0))
        cx, cy = SPHERE_C
        r = SPHERE_R

        pygame.draw.circle(lay, PANEL, (cx, cy), r)
        pygame.draw.circle(lay, QUIET, (cx, cy), r, 1)
        eq = [project(cx, cy, r, math.cos(s), math.sin(s), 0) for s in (k * math.pi / 30 for k in range(61))]
        for k in range(0, 60, 2):
            pygame.draw.line(lay, QUIET, eq[k], eq[k + 1], 1)
        pygame.draw.line(lay, QUIET, (cx, cy - r), (cx, cy + r), 1)
        text(lay, self.small, "|0>", (cx, cy - r - 14), QUIET, center=True)
        text(lay, self.small, "|1>", (cx, cy + r + 14), QUIET, center=True)

        def vec(s):
            theta = 1.05 + 0.45 * math.sin(s * 0.8)
            phi = s * 1.7
            return math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)

        trail = [project(cx, cy, r, *vec(t - k * 0.03)) for k in range(40)]
        for k in range(len(trail) - 1):
            fade = 1 - k / len(trail)
            pygame.draw.line(lay, (*GOLD, int(200 * fade)), trail[k], trail[k + 1], 2)

        ex, ey = trail[0]
        pygame.draw.line(lay, ACCENT, (cx, cy), (ex, ey), 4)
        pygame.draw.circle(lay, (*ACCENT, 70), (int(ex), int(ey)), 13)
        pygame.draw.circle(lay, ACCENT, (int(ex), int(ey)), 7)
        pygame.draw.circle(lay, ACCENT, (cx, cy), 4)

        lay.set_alpha(int(255 * a))
        self.screen.blit(lay, (0, 0))

    # ---------- loop ----------
    def run(self) -> bool:
        """Play the intro. Returns True to start the game, False if the player quit."""
        t, leaving = 0.0, None
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return False
                pressed = event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
                if pressed and leaving is None:
                    if t < READY:
                        t = READY                              # first press skips the animation
                    else:
                        leaving = t

            self.draw(t)
            if leaving is not None:
                k = (t - leaving) / FADE_OUT
                veil = pygame.Surface((W, H))
                veil.fill(BG)
                veil.set_alpha(int(255 * min(1.0, k)))
                self.screen.blit(veil, (0, 0))
                if k >= 1:
                    pygame.display.flip()
                    return True
            pygame.display.flip()
            t += self.clock.tick(60) / 1000
