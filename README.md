# rotating-animations

Rotating ASCII flipbooks rendered from low-poly 3D models. A render pipeline (Blender + Python) plus a thin TanStack Start web shell that flipbooks the result in the browser.

Live: <https://rotating-animations.localhost> (via `just dev`).

## How it works

1. **Source model** — a `.glb` file in `models/`.
2. **Render frames** — Blender spins the model 360° and renders 60 PNGs into `frames_<name>/` (Cycles, GPU).
3. **PNG → ASCII JSON** — a Python script walks each PNG in a grid; per cell it picks a character from a density ramp and a CSS class from the dominant color. All 60 frames go into `web/src/<name>.json`.
4. **Flipbook in the browser** — the TanStack Start route imports the JSON and a `requestAnimationFrame` loop swaps frames ~30×/s. CSS in `web/src/styles.css` colors each class.

The "3D-ness" only exists at render time; the browser just flips through pre-computed text frames.

## Quick start

```sh
just install   # bun install in web/
just dev       # https dev server via portless
just build     # vite build + nitro prerender
just test      # vitest
```

Adding a new animation: see [`CLAUDE.md`](./CLAUDE.md) for the full pipeline (render command, converter choice, route wiring).

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
