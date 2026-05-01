#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=10"]
# ///
"""Convert mallard duck PNG frames into an ASCII flipbook JSON.

Tuned to this specific render's palette (green head, yellow bill, orange feet,
brown body, white collar). Same span-merging strategy as to_ascii.py.

Usage:
  uv run scripts/to_ascii_mallard.py [frames_dir] [out_json]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

RAMP = " ·~o+=*x%$@"
COLS, ROWS = 100, 41
# The eye only ever appears on the head (upper portion of frame). Below this
# row, "eye-like" pixels are deep crevice shadows on the brown body and should
# render as chest, not as black dots.
EYE_MAX_ROW = 17


def classify(r: int, g: int, b: int) -> str | None:
    """Pixel → CSS class. Order matters: most-specific bands first."""
    s = r + g + b
    # eye: very dark + strictly neutral (~(20,20,20) in this render). Tight
    # bounds so the deep-shadow brown at the jaw line (~(30,28,27)) doesn't
    # leak in — that's still warm-biased (R > G > B) and slightly brighter.
    if s < 70 and abs(r - g) < 4 and abs(g - b) < 4:
        return "eye"
    # white collar: rendered ~(170,170,170), not pure white. r≈g≈b, all bright-ish.
    if r >= 145 and g >= 145 and b >= 140 and abs(r - g) < 25 and abs(g - b) < 25:
        return "collar"
    # yellow bill: warm, high R+G, lower B, R close to G
    if r >= 150 and g >= 120 and b < 140 and r - b > 40 and abs(r - g) < 70 and g >= b:
        return "bill"
    # orange feet: high R, mid-low G, low B
    if r >= 130 and r - g > 40 and b < 90:
        return "feet"
    # green head: G dominates, dark-ish (the head is a desaturated teal-green)
    if g > r and g > b and g >= 50:
        return "head"
    # body: uniform brown in this model. Split by luminance so the lit upper
    # back reads as a lighter "back" tone vs the shaded "chest" underside,
    # giving the silhouette some shape even though the GLB has one material.
    if s >= 200:
        return "back"
    return "chest"


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
                    # Spatially gate the eye class — see EYE_MAX_ROW.
                    if cls == "eye" and cy > EYE_MAX_ROW:
                        cls = "chest"
                    cls_counts[cls] += 1
                    n += 1
            if n == 0:
                flush()
                parts.append(" ")
                continue
            total = sum(cls_counts.values())
            # Bias: small but distinctive features win at low presence.
            # Order = visual priority. Eye is tiny (~3px wide) so threshold low.
            if cls_counts["eye"] / total >= 0.08:
                dominant = "eye"
            elif cls_counts["bill"] / total >= 0.12:
                dominant = "bill"
            elif cls_counts["collar"] / total >= 0.10:
                dominant = "collar"
            elif cls_counts["feet"] / total >= 0.20:
                dominant = "feet"
            elif cls_counts["head"] / total >= 0.30:
                dominant = "head"
            else:
                dominant = cls_counts.most_common(1)[0][0]
            counts[dominant] += 1
            # Alpha-based density: opaque cells get the densest chars, edges
            # taper. This keeps a dark-bodied duck from looking ghostly.
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
    frames_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "frames_mallard")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "web/src/mallard.json")
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
