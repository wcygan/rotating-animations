#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert toco toucan PNG frames into an ASCII flipbook JSON.

Tuned to this specific render's palette (dark grey body/wings/head, peach-cream
giant beak, dark tip + eye, white chest patch, pale-blue feet). Same span-merging
strategy as to_ascii_mallard.py; alpha-based density so the dark grey body
doesn't drop out under brightness-based ramps.

Usage:
  uv run scripts/to_ascii_toucan.py [frames_dir] [out_json]
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
    # tip / eye: very dark, near-neutral. Covers (0,0,0)-(64,64,64) range.
    if s < 200 and abs(r - g) < 20 and abs(g - b) < 20:
        return "tip"
    # beak: warm peach/cream. R clearly > B, fairly bright. Excludes neutrals.
    # The render gives (240,208,176)-(240,240,208) on lit faces and
    # (208,144,96) on shaded undersides. Require r > b + 12 to keep it off
    # the (224,224,224) chest and the cool feet.
    if r >= 180 and r > b + 12 and r >= g and g >= b - 10:
        return "beak"
    # feet: pale blue/lavender. B clearly > R, fairly bright.
    # (176,208,240), (192,224,240), (160,192,224).
    if b >= 180 and b > r + 12 and b >= g:
        return "feet"
    # chest: truly neutral white-ish. r≈g≈b, all bright. Must come AFTER beak
    # and feet so warm/cool tints don't slip in.
    if r >= 180 and abs(r - g) < 12 and abs(g - b) < 12 and abs(r - b) < 12:
        return "chest"
    # body: everything else opaque. Grey body/wings/head dominates.
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
            # Bias: small bright features should win over body votes when
            # they have meaningful presence. Beak is large; doesn't need much.
            if cls_counts["tip"] / total >= 0.18:
                dominant = "tip"
            elif cls_counts["feet"] / total >= 0.18:
                dominant = "feet"
            elif cls_counts["chest"] / total >= 0.20:
                dominant = "chest"
            elif cls_counts["beak"] / total >= 0.25:
                dominant = "beak"
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
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_toucan")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/toucan.json")
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
