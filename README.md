# rotating-animations

Rotating ASCII flipbooks rendered from low-poly 3D models. A render pipeline (Blender + Python) plus a thin TanStack Start web shell that flipbooks the result in the browser.

Live: <https://rotating-animations.localhost> (via `just dev`).

## How it works

1. **Source model** — a `.glb` file in `models/`.
2. **Render frames** — Blender spins the model 360° and renders 60 PNGs into `frames_<name>/` (Cycles, GPU).
3. **PNG → ASCII JSON** — a Python script walks each PNG in a grid; per cell it picks a character from a density ramp and a CSS class from the dominant color. All 60 frames go into `web/src/<name>.json`.
4. **Flipbook in the browser** — the TanStack Start route imports the JSON and a `requestAnimationFrame` loop swaps frames ~30×/s. CSS in `web/src/styles.css` colors each class.

The "3D-ness" only exists at render time; the browser just flips through pre-computed text frames.

## Prerequisites

| Tool | Used for | Install |
|---|---|---|
| [Bun](https://bun.sh) ≥ 1.3 | runtime + package manager for `web/` | `curl -fsSL https://bun.sh/install \| bash` |
| [just](https://github.com/casey/just) | task runner (`just <recipe>`) | `brew install just` |
| [uv](https://docs.astral.sh/uv/) | runs Python converters with PEP-723 inline deps | `brew install uv` |
| [Blender](https://www.blender.org/) ≥ 4.2 | renders the 3D models to PNG sequences | `brew install --cask blender` |

The site itself (no re-render) only needs Bun + just. Re-rendering or adding a new animation also needs uv + Blender.

## Quick start

Just view the site (uses the ASCII JSONs already committed under `web/src/`):

```sh
just install   # bun install in web/
just dev-bare  # plain Vite dev server (random http port)
```

Or `just dev` to run behind [portless](https://github.com/lukeed/portless) at `https://rotating-animations.localhost` — this prompts for sudo on first run to install a local CA, so prefer `dev-bare` for a quick look.

```sh
just build     # vite build + nitro prerender of every route
just preview   # serve the built app
just test      # vitest (currently no test files)
```

## Reproducing an animation from scratch

Re-render and re-convert the penguin end-to-end:

```sh
# 1. render 60 frames (Blender, Cycles GPU; takes ~1–2 min on Apple Silicon)
blender -b -P scripts/render_spin.py -- models/penguin.glb frames_penguin 60 upright

# 2. convert PNGs → ASCII JSON (overwrites web/src/penguin.json)
uv run scripts/to_ascii_generic.py frames_penguin web/src/penguin.json

# 3. view it
just dev-bare   # then open the printed URL and click "penguin"
```

Orient modes for `render_spin.py`:
- `lay_flat` (default) — rotates the longest axis to +X, suits horizontally-elongated objects (hotdog).
- `upright` — preserves Z-up, suits cups, animals, anything you don't want laid on its side.

Converter choice (`scripts/to_ascii_*.py`):
- **Per-model** (`to_ascii.py`, `to_ascii_mallard.py`, `to_ascii_penguin.py`, …) — hand-tuned RGB/HSV thresholds emit richer per-region classes (body / head / bill / …). Use when the model has a distinctive palette.
- **Generic** (`to_ascii_generic.py`) — saturation splits cells into `solid` vs `tea`; suits mostly-white or low-contrast subjects.

Adding a new animation (model → route): see [`CLAUDE.md`](./CLAUDE.md) for the full four-step wiring (route file, `__root.tsx` tabs array, `index.tsx` listing, `styles.css` block).

## Repo shape

```
models/              # source .glb files
scripts/             # Blender render + PNG→ASCII converters (uv run)
frames_<name>/       # rendered PNG sequences (gitignored, regenerable)
web/                 # TanStack Start app
  src/routes/        # one route per animation
  src/<name>.json    # generated ASCII flipbook (committed)
  src/styles.css     # per-animation classes scoped under .<name>
```

## Credits

All 3D models are sourced from [Poly Pizza](https://poly.pizza/) under their respective licenses.

- Hot dog by jeremy [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/eiPR4iwcYpa)
- Penguin by Poly by Google [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/fBXvsC6pe_V)
- Toco Toucan by Anonymous [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/fFVqukPnc62)
- Parrot by Poly by Google [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/35EeLqGHH1y)
- Cup Tea by Kenney via [Poly Pizza](https://poly.pizza/m/M2sVC8jbmi)
- Duck by jeremy [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/2KHEgw1ztVI)
- Mallard duck by Poly by Google [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/frSLi6b6Vid)
- Goose by Poly by Google [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/9wn3If7Qgb4)
- Hummingbird by Poly by Google [[CC-BY](https://creativecommons.org/licenses/by/3.0/)] via [Poly Pizza](https://poly.pizza/m/70NyKFt-vLF)
