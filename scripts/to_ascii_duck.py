#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert low-poly mallard-style duck PNG frames into an ASCII flipbook JSON.

Tuned to this specific render (much dimmer than to_ascii_mallard.py's source —
the lit "white" collar shows as ~(140,140,140) and the body is a desaturated
blue-gray rather than brown). Eye is rendered with a black decal on this
model's head and is naturally visible at every rotation, so no synthesis pass.

Usage:
  uv run scripts/to_ascii_duck.py [frames_dir] [out_json]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

RAMP = " ·~o+=*x%$@"
COLS, ROWS = 100, 41


def classify(r: int, g: int, b: int) -> str | None:
    """Pixel → CSS class. Order = most-specific first."""
    s = r + g + b
    # eye: very dark + neutral (~(10,14,10))
    if s < 55 and abs(r - g) < 8 and abs(g - b) < 8:
        return "eye"
    # collar: light gray band, rendered ~(140,140,140), not pure white
    if r >= 125 and g >= 125 and b >= 125 and abs(r - g) < 18 and abs(g - b) < 18:
        return "collar"
    # bill/feet: golden yellow ~(135,121,21). Keep them in one class — both
    # render as the same hue and the visual effect is fine.
    if r >= 100 and g >= 80 and b < 60 and r - b > 60 and abs(r - g) < 50:
        return "bill"
    # head: green dominant ~(39,90,37). Strict G-dominance to not catch the
    # mid-saturation chest browns.
    if g > r + 20 and g > b + 20 and g >= 50:
        return "head"
    # chest: warm brown ~(56,40,32) — R>G>B, low blue
    if r > g and g >= b and r - b > 12 and r < 130:
        return "chest"
    # body: cool blue-gray ~(60,74,81) — B >= G >= R, low saturation
    return "body"


def convert(png_path: Path) -> tuple[list[str], Counter]:
    img = Image.open(png_path).convert("RGBA")
    W, H = img.size
    cell_w = W / COLS
    cell_h = H / ROWS
    px = img.load()
    counts: Counter = Counter()
    lines: list[str] = []
    for cy in range(ROWS):
        parts: list[str] = []
        buf = ""
        cur: str | None = None

        def flush():
            nonlocal buf, cur
            if buf:
                parts.append(f'<span class="{cur}">{buf}</span>')
                buf = ""
                cur = None

        for cx in range(COLS):
            x0, x1 = int(cx * cell_w), int((cx + 1) * cell_w)
            y0, y1 = int(cy * cell_h), int((cy + 1) * cell_h)
            cls_counts: Counter = Counter()
            a_sum = 0
            cell_pixels = 0
            n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    cell_pixels += 1
                    r, g, b, a = px[x, y]
                    a_sum += a
                    if a < 60:
                        continue
                    cls = classify(r, g, b)
                    if cls is None:
                        continue
                    cls_counts[cls] += 1
                    n += 1
            if n == 0:
                flush()
                parts.append(" ")
                continue
            total = sum(cls_counts.values())
            # Small features win at low presence — same scheme as mallard.
            if cls_counts["eye"] / total >= 0.10:
                dominant = "eye"
            elif cls_counts["bill"] / total >= 0.15:
                dominant = "bill"
            elif cls_counts["collar"] / total >= 0.15:
                dominant = "collar"
            elif cls_counts["head"] / total >= 0.30:
                dominant = "head"
            elif cls_counts["chest"] / total >= 0.30:
                dominant = "chest"
            else:
                dominant = cls_counts.most_common(1)[0][0]
            counts[dominant] += 1
            avg_a = a_sum / cell_pixels
            density = min(1.0, max(0.0, (avg_a / 255 - 0.2) / 0.8))
            idx = int(density * (len(RAMP) - 1))
            ch = RAMP[idx]
            if dominant != cur:
                flush()
                cur = dominant
            buf += ch
        flush()
        lines.append("".join(parts))
    return lines, counts


def main() -> int:
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_duck")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/duck.json")
    pngs = sorted(frames_dir.glob("*.png"))
    if not pngs:
        print(f"no PNGs in {frames_dir}", file=sys.stderr)
        return 1
    frames: dict[str, list[str]] = {}
    totals: Counter = Counter()
    for i, p in enumerate(pngs):
        lines, counts = convert(p)
        frames[f"frame_{i:03d}"] = lines
        totals.update(counts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(frames))
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {len(frames)} frames → {out_path} ({size_kb:.1f} KB)")
    print(f"class distribution: {dict(totals)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
