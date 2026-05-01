#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert a directory of RGBA PNG frames into an ASCII flipbook JSON.

Generic version (vs. to_ascii.py which is hotdog-tuned). Each cell's character
is picked from a ramp based on a "darkness from white" score that combines
alpha (silhouette) with inverse luminance (interior shadow). Suitable for
mostly-light objects (teacup, vase, ceramic) where the hotdog's hue-class
classifier would degenerate.

Cells are classified into two CSS classes by saturation:
  - "solid" — neutral / white (the porcelain shell)
  - "tea"   — saturated color (the tea liquid inside)

Usage:
  uv run scripts/to_ascii_generic.py [frames_dir] [out_json] [cols] [rows]
"""

import json
import sys
from pathlib import Path

from PIL import Image

RAMP = " .,:;-+=ox*X#%@"
DEFAULT_COLS, DEFAULT_ROWS = 100, 41


def saturation(r: int, g: int, b: int) -> float:
    """HSV-style saturation in [0, 1]. Pure white/black/grey → 0."""
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx == 0:
        return 0.0
    return (mx - mn) / mx


def convert(png_path: Path, cols: int, rows: int) -> list[str]:
    img = Image.open(png_path).convert("RGBA")
    W, H = img.size
    cell_w = W / cols
    cell_h = H / rows
    px = img.load()
    lines: list[str] = []
    for cy in range(rows):
        parts: list[str] = []
        buf = ""
        cur: str | None = None

        def flush():
            nonlocal buf, cur
            if buf:
                parts.append(f'<span class="{cur}">{buf}</span>')
                buf = ""
                cur = None

        for cx in range(cols):
            x0, x1 = int(cx * cell_w), int((cx + 1) * cell_w)
            y0, y1 = int(cy * cell_h), int((cy + 1) * cell_h)
            a_sum = 0
            lum_sum = 0
            sat_sum = 0.0
            n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    r, g, b, a = px[x, y]
                    a_sum += a
                    lum_sum += (r + g + b) // 3
                    sat_sum += saturation(r, g, b)
                    n += 1
            if n == 0:
                flush()
                parts.append(" ")
                continue
            avg_a = a_sum / n
            avg_lum = lum_sum / n
            avg_sat = sat_sum / n
            if avg_a < 50:
                flush()
                parts.append(" ")
                continue
            # tea: opaque cells with noticeable hue (ceramic is ~0 sat)
            cls = "tea" if avg_sat > 0.04 else "solid"
            shaded = (avg_a / 255) * (1.0 - avg_lum / 255)
            silhouette = (avg_a / 255) * 0.3
            density = max(shaded, silhouette)
            # Boost density for tea so it reads as a richer area than the cup
            if cls == "tea":
                density = max(density, 0.55)
            idx = min(len(RAMP) - 1, int(density * (len(RAMP) - 1) * 1.6))
            ch = RAMP[idx]
            if cls != cur:
                flush()
                cur = cls
            buf += ch
        flush()
        line = "".join(parts)
        lines.append(line if line.strip() else "")
    return lines


def main() -> int:
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/frames.json")
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_COLS
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_ROWS
    pngs = sorted(frames_dir.glob("*.png"))
    if not pngs:
        print(f"no PNGs in {frames_dir}", file=sys.stderr)
        return 1
    frames: dict[str, list[str]] = {}
    for i, p in enumerate(pngs):
        frames[f"frame_{i:03d}"] = convert(p, cols, rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(frames))
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {len(frames)} frames → {out_path} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
