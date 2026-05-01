#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert emperor penguin PNG frames into an ASCII flipbook JSON.

Tuned to this specific render's palette (black body/head/flippers, white-ish
grey belly, mustard-yellow collar patch, orange/coral beak). Uses alpha-based
density (the black body would vanish under luminance mapping — same problem
the mallard converter solves).

Usage:
  uv run scripts/to_ascii_penguin.py [frames_dir] [out_json]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

RAMP = " ·~o+=*x%$@"
COLS, ROWS = 100, 41


def classify(r: int, g: int, b: int) -> str | None:
    """Pixel → CSS class. Order matters: most-specific bands first.

    Sampled values (this render):
      body  ~(16,16,16)              — very dark neutral
      belly ~(120-135, 118-130, 110-125) — bright neutral, faintly warm
      collar ~(120-130, 100-107, 5-25)  — yellow/mustard: R≈G, B≪
      beak  ~(120-135, 65-75, 50-60)    — orange/coral: R>G>B, R-G≈55
    """
    s = r + g + b
    # beak: orange/coral. R clearly dominates, G mid, B low. Tight on the
    # R-G gap so the warm-tinted belly highlights don't leak in.
    if r >= 100 and r - g >= 35 and r - b >= 50 and g - b < 35:
        return "beak"
    # collar: mustard yellow. R and G both mid, B near zero.
    if r >= 90 and g >= 75 and b < 50 and abs(r - g) < 40 and r - b > 60:
        return "collar"
    # belly: bright-ish neutral grey/white. r ≈ g ≈ b, all reasonably bright.
    if r >= 90 and g >= 85 and b >= 80 and abs(r - g) < 20 and abs(g - b) < 25:
        return "belly"
    # body: everything else that's opaque is the black plumage (incl. dim
    # shadow pixels around the silhouette edge).
    return "body"


def convert(png_path: Path) -> tuple[list[str], Counter]:
    img = Image.open(png_path).convert("RGBA")
    W, H = img.size
    cell_w = W / COLS
    cell_h = H / ROWS
    px = img.load()
    counts: Counter = Counter()
    cells: list[list[tuple[str, str] | None]] = [
        [None] * COLS for _ in range(ROWS)
    ]

    for cy in range(ROWS):
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
                continue
            total = sum(cls_counts.values())
            # Bias small features so they survive the dominant black body in
            # mixed cells along the beak/collar boundaries.
            if cls_counts["beak"] / total >= 0.15:
                dominant = "beak"
            elif cls_counts["collar"] / total >= 0.18:
                dominant = "collar"
            elif cls_counts["belly"] / total >= 0.30:
                dominant = "belly"
            else:
                dominant = cls_counts.most_common(1)[0][0]
            counts[dominant] += 1
            avg_a = a_sum / cell_pixels
            density = min(1.0, max(0.0, (avg_a / 255 - 0.2) / 0.8))
            idx = int(density * (len(RAMP) - 1))
            cells[cy][cx] = (dominant, RAMP[idx])

    # Stringify with span-merging.
    lines: list[str] = []
    for cy in range(ROWS):
        parts: list[str] = []
        buf = ""
        cur: str | None = None
        for cx in range(COLS):
            cell = cells[cy][cx]
            if cell is None:
                if buf:
                    parts.append(f'<span class="{cur}">{buf}</span>')
                    buf = ""
                    cur = None
                parts.append(" ")
                continue
            cls, ch = cell
            if cls != cur:
                if buf:
                    parts.append(f'<span class="{cur}">{buf}</span>')
                    buf = ""
                cur = cls
            buf += ch
        if buf:
            parts.append(f'<span class="{cur}">{buf}</span>')
        lines.append("".join(parts))
    return lines, counts


def main() -> int:
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_penguin")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/penguin.json")
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
    total_cells = sum(totals.values()) or 1
    pct = {k: f"{v} ({100*v/total_cells:.1f}%)" for k, v in totals.items()}
    print(f"class distribution: {pct}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
