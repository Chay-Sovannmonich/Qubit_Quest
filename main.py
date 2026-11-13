"""Start Qubit Quest.

    python main.py              # start at the first level
    python main.py --level 3-1  # jump to a level
    python main.py --no-intro   # skip the title screen
"""
import argparse

from game.level import all_levels
from game.state import GameState


def main():
    parser = argparse.ArgumentParser(description="Qubit Quest")
    parser.add_argument("--level", help="level id to start at, e.g. 3-1")
    parser.add_argument("--no-intro", action="store_true", help="skip the title screen")
    args = parser.parse_args()

    levels = all_levels()
    ids = [lv.id for lv in levels]
    start = ids.index(args.level) if args.level in ids else 0

    from game.app import App  # imported here so the tests never need Pygame
    # --level jumps straight into that level; otherwise the world map comes first
    App(GameState(levels, start), intro=not args.no_intro, start_on_map=args.level not in ids).run()


if __name__ == "__main__":
    main()
