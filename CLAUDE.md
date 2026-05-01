# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo shape

```
.
├── Justfile             # all dev/build commands (run from repo root)
├── models/              # source .glb files (one per animation)
├── scripts/             # Blender + Python pipeline (render → ASCII)
├── frames_<name>/       # PNG sequences (gitignored, regenerable)
└── web/                 # TanStack Start app (Bun + Vite + Tailwind v4)
    └── src/
        ├── routes/      # file-based routing; one route per animation
        ├── <name>.json  # generated ASCII flipbook (committed)
        └── styles.css   # per-animation classes scoped under .<name>
```

## Commands

Run from the repo root:

| | |
|---|---|
| `just dev` | Dev server behind `bunx portless` → `https://rotating-animations.localhost` (HTTPS, sudo on first run for the local CA) |
| `just dev-bare` | Plain `vite dev` if portless gets in the way |
| `just build` | Vite build + Nitro prerender of every route |
| `just preview` | Serve the built app |
| `just test` | `vitest run` |
| `just install` | `bun install` inside `web/` |

`web/package.json` always invokes Vite as `bun --bun vite ...` — the `--bun` flag is load-bearing (without it Bun delegates to Node).

## Adding a new animation: the four-stage pipeline

This repo is fundamentally a **render pipeline + a thin web shell**, not a typical web app. Each animation goes through:

1. **Source model** → drop a `.glb` into `models/<name>.glb`.
2. **Render frames** (Blender, Cycles GPU):
   ```
   blender -b -P scripts/render_spin.py -- models/<name>.glb frames_<name> 60 <orient>
   ```
   `<orient>` is `lay_flat` (default — rotates the longest axis to +X, suits horizontally-elongated objects like a hotdog) or `upright` (preserves Z-up, suits cups/animals/anything you don't want laid on its side).
3. **PNG → ASCII JSON** with a converter under `scripts/to_ascii*.py` (run via `uv run`):
   - **Per-model classifier** (`to_ascii.py` for hotdog, `to_ascii_mallard.py` for mallard) — hand-tuned RGB/HSV thresholds emit `<span class="...">` per region (bun/dog/mustard, body/head/bill/feet/collar). Use when the model has a distinctive palette and you want richly-colored output.
   - **Generic** (`to_ascii_generic.py`) — saturation splits cells into `solid` vs `tea`; suits mostly-white or low-contrast subjects.
   - Output goes to `web/src/<name>.json`.
4. **Wire the route** — three places, every time:
   - `web/src/routes/<name>.tsx` — imports `#/<name>.json`, runs the rAF flipbook (see existing routes; they're identical except for class names and frame-rate constant).
   - `web/src/routes/__root.tsx` — append to the `TABS` array.
   - `web/src/routes/index.tsx` — append to the `ANIMATIONS` array.
   - Add a `.<name>` block + per-class colors to `web/src/styles.css`.

`routeTree.gen.ts` regenerates from the file system on dev/build — don't edit by hand.

## Converter design notes (subtle and easy to break)

- **Char density mapping is not universal.** The hotdog converter maps brightness → ramp index, which works because the hotdog is bright on a transparent background. The mallard's dark brown body **washes out** under that scheme, so its converter switches to **alpha-based density** (opaque = densest char) while still using RGB thresholds for class. When adding a dark-bodied subject, copy the mallard, not the hotdog.
- **Class biasing matters.** Small features (mustard on the hotdog, bill on the duck) get drowned by mass-color voting unless they win at low presence thresholds (`>= 0.12-0.20` of the cell). Tune the thresholds, not the classifier order.
- **Pure white rarely renders as pure white.** The mallard's collar threshold of `(200,200,200)` finds nothing in head-on frames because lighting drops the values. Lower the threshold or accept that the collar only appears at certain angles.

## Stack conventions (TanStack Start + Bun + Tailwind v4)

- Bun is the runtime; never strip `--bun` from the npm scripts.
- Tailwind v4 is **CSS-first** — no `tailwind.config.*`, no `@tailwind base/components/utilities`. The single `@import 'tailwindcss'` in `web/src/styles.css` is wired into the document via `?url` import in `__root.tsx`.
- All pages prerender at build time (`/`, `/glizzy`, `/teacup`, `/mallard`); SSR is enabled, so route components must guard `window`/`requestAnimationFrame` behind `typeof window !== 'undefined'`.
- Subpath imports use `#/*` → `./src/*` (declared in `web/package.json`); use `import frames from '#/<name>.json'` rather than relative paths.
- Per-animation styles are namespaced under `.<name>` (e.g. `.hotdog .mustard`, `.mallard .head`) — keep new animations in the same shape so classes never collide.
- `effect-ts` is the documented default for server-side logic in this stack, but every route here is static client-side animation; existing routes carry an `// effect-ts skipped` comment explaining why. Match that pattern.

## What lives where (gitignored vs committed)

- **Committed**: source models (`models/*.glb`), rendered ASCII (`web/src/*.json`), all scripts, route code.
- **Gitignored** (root `.gitignore`): `frames/`, intermediate render PNGs, `web/node_modules`, `web/dist`, `web/.tanstack`, `web/.nitro`, `web/.output`. Note: when you render a new animation, the new `frames_<name>/` directory **isn't** matched by the existing `frames/` ignore — add it before committing or extend the ignore to `frames*/`.
