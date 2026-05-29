# carc-alone
A Carcassonne-style board game implementation built with Python and Pygame-ce.

## Features
- **Tile Placement**: Rotate and place tiles according to valid edge constraints.
- **Meeple Management**: Place meeples on features (Cities, Roads, Abbeys) to claim points.
- **Dynamic Scoring**: Automatic scoring for completed roads, cities, and cloisters.
- **Web Compatibility**: Built to run in the browser via WebAssembly (Pygbag).

## How to Run
### Locally
Using `uv`:
```powershell
uv run carcassonne.py
```

## Technical Stack
- **Engine**: Pygame-ce
- **Environment**: uv (Python 3.12+)
- **Deployment**: GitHub Pages via Pygbag (WASM)
