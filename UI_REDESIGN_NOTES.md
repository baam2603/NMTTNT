# Battle City Tanks — Modern Gaming UI

## What changed

The redesign uses a military-green / near-black / orange palette while keeping the original 480 × 416 game canvas and the original gameplay engine.

- `tanks.py`: modern menu, tactical HUD/sidebar, after-action report, and Game Over screen.
- `images/`, `sounds/`, `levels/`, `fonts/`, and `.hiscore`: kept from the original project.

## What was intentionally preserved

- Tank movement and firing controls.
- Enemy AI and spawn logic.
- Collision, bullets, bonuses, level maps, and castle behavior.
- Player count selection with Up/Down and Enter to start.
- Existing sound toggle (`M`) and quit (`Q`) controls during gameplay.
- Score persistence in `.hiscore` and level progression.

## Run on macOS

1. Extract this ZIP to a normal folder, for example `~/Documents/battle-city-tanks-modern-ui`.
2. Open that folder in VS Code.
3. In the VS Code terminal, create/activate a virtual environment if desired, then install Pygame:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install pygame
   ```

4. Run from the project root (important because assets use relative paths):

   ```bash
   python tanks.py
   ```

If the game does not start, check that the terminal's current directory is the folder containing `tanks.py`, `images/`, `sounds/`, `levels/`, and `fonts/`.

## Revert

Keep a copy of your original `tanks.py` before replacing it. To revert, restore that original file. The redesign has been syntax-checked with Python, but a live Pygame window was not launched in this build environment.
