#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert scarlet macaw PNG frames into an ASCII flipbook JSON.

Tuned to this render's palette (red head/body, yellow shoulder band, dark blue
wings/tail tip, light-grey beak, dark eye/feet). Same span-merging strategy
and alpha-based density as to_ascii_mallard.py.

Usage:
  uv run scripts/to_ascii_parrot.py [frames_dir] [out_json]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

RAMP = " ·~o+=*x%$@"
COLS, ROWS = 100, 41


def classify(r: int, g: int, b: int) -> str | None:
    """Pixel → CSS class. Order matters: most-specific bands first."""
    s = r + g + b

    # dark: eye, feet, claws — very dark and roughly neutral.
    # Sampled feet/eye ~(13,16,16), claws similar. Stay tight so dark-red
    # shadows (e.g. r=94,g=1,b=0) don't leak in (those are warm-biased).
    if s < 80 and abs(r - g) < 12 and abs(r - b) < 12 and abs(g - b) < 12:
        return "dark"

    # blue wings / tail tip: B is the dominant channel, all values low-ish.
    # Sampled (8,29,54), (22,38,61), (20,34,54). B noticeably > R, B >= G.
    if b > r + 10 and b >= g and b >= 30 and r < 80:
        return "blue"

    # yellow shoulder band: high R, mid G, very low B. Sampled (131,96,8),
    # (130,81,10), (137,99,3). Distinguishing from red: G is substantially
    # higher (red has G < 50, yellow has G > 60). Bias low so the small band
    # doesn't get drowned by the surrounding red vote.
    if r >= 100 and g >= 55 and b < 40 and r - b > 60 and r - g > 15:
        return "yellow"

    # light-grey beak: r ≈ g ≈ b, all mid-bright. Sampled (104,101,101),
    # (128,126,126). Tight neutrality bound so warm flesh tones stay out.
    if r >= 90 and g >= 90 and b >= 90 and abs(r - g) < 15 and abs(r - b) < 15 and abs(g - b) < 15:
        return "beak"

    # red — dominant body color. Sampled across a wide range
    # ~(94,1,0) shadow → (133,37,40) lit. R clearly dominates G and B.
    if r >= 70 and r > g + 30 and r > b + 30:
        return "red"

    return None


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
            # Bias small features so they survive against the red majority.
            if cls_counts["dark"] / total >= 0.20:
                dominant = "dark"
            elif cls_counts["beak"] / total >= 0.15:
                dominant = "beak"
            elif cls_counts["yellow"] / total >= 0.15:
                dominant = "yellow"
            elif cls_counts["blue"] / total >= 0.15:
                dominant = "blue"
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
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_parrot")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/parrot.json")
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
