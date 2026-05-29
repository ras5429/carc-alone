# carc-alone
A Carcassonne-style board game implementation built with Python and Pygame-ce.

## Features
- **Tile Placement**: Rotate and place tiles according to valid edge constraints.
- **Meeple Management**: Place meeples on features (Cities, Roads, Cloisters) to claim points.
- **Dynamic Scoring**: Automatic scoring for completed roads, cities, and Cloisters.
- **Web Compatibility**: Built to run in the browser via WebAssembly (Pygbag).

## How to Run
### Locally
Using `uv`:
```powershell
uv run main.py
```

### Web Preview
To simulate the GitHub Pages environment locally:
```powershell
uv run python -m pygbag --disable-sound-format-error .
```

## Technical Stack
- **Engine**: Pygame-ce
- **Environment**: uv (Python 3.12+)
- **Deployment**: GitHub Pages via Pygbag (WASM)
