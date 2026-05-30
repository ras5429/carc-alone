# carc-alone

A solo Carcassonne implementation built with Python and Pygame-ce.
Playable in the browser via WebAssembly — no installation needed.

> **Personal project.** This repo is public so it can be hosted on GitHub Pages.
> Issues and pull requests will not be reviewed or accepted.

## Play

[ras5429.github.io/carc-alone](https://ras5429.github.io/carc-alone/)

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```powershell
uv run main.py
```

## Build for web

```powershell
uv run python -m pygbag --build main.py
```

Output lands in `build/web/`. The GitHub Actions workflow deploys this automatically on push to `main`.

## Stack

- **Engine** — Pygame-ce
- **Web runtime** — Pygbag (WASM via Emscripten)
- **Tooling** — uv
