#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert hummingbird PNG frames into an ASCII flipbook JSON.

Tuned to this specific render's palette: royal-blue head, mint-green body,
dusty-purple wings, rust-orange tail underside, near-black eye. Alpha-based
density (the bird is dark overall, so brightness-as-density washes it out).
Same span-merging strategy as to_ascii_mallard.py.

Usage:
  uv run scripts/to_ascii_hummingbird.py [frames_dir] [out_json]
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

    Channel signatures observed on f_015:
      head  ~(36, 56,125) — saturated royal blue, B >> R, B >> G
      body  ~(102,143,112) — mint green, G dominant
      wing  ~(84, 71,103) — dusty purple, B > G, R close to B (low sat)
      tail  ~(159,113, 75) — warm rust, R > G > B
      eye   ~(20, 20, 20) — near-black neutral
    """
    s = r + g + b
    # near-black eye / beak shadow: very dark, neutral.
    if s < 90 and abs(r - g) < 15 and abs(g - b) < 15:
        return "dark"
    # rust tail: warm cast (R > G >= B) with appreciable warmth. Loose floor
    # so shaded tail edges (R~90) don't get swept into wing.
    if r > g and g >= b and r - b >= 30 and r >= 90:
        return "tail"
    # mint green body: G the dominant channel.
    if g > r + 5 and g >= b - 5 and g >= 90:
        return "body"
    # royal blue head: B clearly dominant over both R and G. Discriminator
    # against purple wings is B-R: head ≥ 30, wing ~ 0.
    if b >= 95 and b - r >= 30 and b - g >= 30:
        return "head"
    # dusty purple wing: B > G, R within 35 of B (purple has near-equal R/B).
    # Bottom bound r >= 55 keeps deep crevice shadows from leaking in.
    if b > g and abs(r - b) < 35 and b >= 75 and r >= 55:
        return "wing"
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
            # Bias toward small features so they aren't absorbed by mass-color
            # voting. Eye is rarest → lowest threshold; head/tail next; body and
            # wing dominate by area so they only win on plurality.
            if cls_counts["dark"] / total >= 0.08:
                dominant = "dark"
            elif cls_counts["tail"] / total >= 0.20:
                dominant = "tail"
            elif cls_counts["head"] / total >= 0.25:
                dominant = "head"
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
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_hummingbird")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/hummingbird.json")
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
