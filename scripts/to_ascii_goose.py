#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert Canada goose PNG frames into an ASCII flipbook JSON.

Tuned to this specific render's three-tier palette: black head/neck/feet/bill,
dark brown back/wings, light tan chest/belly. The render lacks a true white
cheek patch — the brightest pixels max out around (116,107,95) — so the
`cheek` class captures the lightest sub-band of the chest tier so that the
classifier still distinguishes the side-of-head highlight when it shows.

Alpha-based density (the near-black neck would otherwise vanish under
luminance mapping). Same span-merging strategy as to_ascii_mallard.py.

Usage:
  uv run scripts/to_ascii_goose.py [frames_dir] [out_json]
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

    Empirically this render uses three tight clusters:
      neck:   ~(10,10,10)   — neutral black, sum < 50
      back:   ~(37,25,16)   — warm dark brown, sum ~60-90, R>G>B
      chest:  ~(102,94,82)  — warm light tan, sum ~270-290
      cheek:  ~(110,100,87) — lightest sub-band of chest (sum >= 290)
    """
    s = r + g + b
    # neck: very dark + roughly neutral. The black areas are head/neck/feet/bill
    # all merged; the model has no bill geometry distinct enough to separate.
    if s < 55 and abs(r - g) < 5 and abs(g - b) < 5:
        return "neck"
    # cheek: brightest tier. Real cheek pixels sit in (107-116, 97-107, 85-95).
    # We catch them with a bright-warm rule that excludes mid-range chest.
    if r >= 105 and g >= 95 and b >= 83 and r > b:
        return "cheek"
    # chest: the bulk light-tan body (warm, R>G>B, mid-bright)
    if r >= 80 and r > g >= b and s >= 220:
        return "chest"
    # back: dark brown wings/back. Warm-biased (R>G>B) but darker than chest.
    if r >= 25 and r > g and g >= b and s < 200:
        return "back"
    # Fallback: anything still warm-ish belongs to back; otherwise neck.
    if r > b and s < 150:
        return "back"
    if s < 80:
        return "neck"
    return "chest"


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
            # Bias small/distinctive features so they don't get drowned by
            # mass-color voting.
            if cls_counts["cheek"] / total >= 0.10:
                dominant = "cheek"
            elif cls_counts["neck"] / total >= 0.25:
                dominant = "neck"
            elif cls_counts["back"] / total >= 0.30:
                dominant = "back"
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
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_goose")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/goose.json")
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
