#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert a directory of RGBA PNG frames into a single hotdog.json.

Each pixel is classified by HSV hue into bun / dog / mustard, and emitted as
an ASCII character whose density tracks the pixel's luminance. Consecutive
characters in the same class are merged into one <span>.

Usage:
  uv run scripts/to_ascii.py [frames_dir] [out_json]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

RAMP = " ·~o+=*x%$@"
COLS, ROWS = 100, 41


def classify(r: int, g: int, b: int) -> str | None:
    """Tuned to this specific render's color values.

    Why these thresholds: the rendered mustard maxes out near (133, 78, 3) — not
    a bright yellow, but distinguishable from the bun (~(115, 75, 21)) by its
    near-zero blue channel. The sausage is the only thing with very low G.
    """
    if r + g + b < 60:
        return None
    if g >= 65 and b < 12 and r >= 125:
        return "mustard"
    if g < 45 and (r - g) > 60 and b < 35:
        return "dog"
    return "bun"


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
            lum_sum = 0
            n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    r, g, b, a = px[x, y]
                    if a < 60:
                        continue
                    cls = classify(r, g, b)
                    if cls is None:
                        continue
                    cls_counts[cls] += 1
                    lum_sum += (r + g + b) // 3
                    n += 1
            if n == 0:
                flush()
                parts.append(" ")
                continue
            total = sum(cls_counts.values())
            # Bias: mustard wins if it's at least 18% of the cell
            if cls_counts["mustard"] / total >= 0.18:
                dominant = "mustard"
            else:
                dominant = cls_counts.most_common(1)[0][0]
            counts[dominant] += 1
            avg_lum = lum_sum // n
            ch = RAMP[avg_lum * (len(RAMP) - 1) // 255]
            if dominant != cur:
                flush()
                cur = dominant
            buf += ch
        flush()
        lines.append("".join(parts))
    return lines, counts


def main() -> int:
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/hotdog.json")
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
