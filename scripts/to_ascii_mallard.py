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


def synthesize_eyes(
    cells: list[list[tuple[str, str] | None]],
) -> list[tuple[int, int]]:
    """Pick (cy, cx) positions where fake eye dots should be drawn.

    The model only has eye geometry on the sides of the head, so head-on /
    back-on rotation frames render no black eye pixels at all. This synthesizes
    two black dots in the upper head region of every frame so the duck always
    has visible eyes. Anchored to the bill when visible (bill direction tells
    us which side the head is facing); falls back to head centroid otherwise.
    """
    head_cells = [(cy, cx) for cy, row in enumerate(cells)
                  for cx, c in enumerate(row) if c and c[0] == "head"]
    bill_cells = [(cy, cx) for cy, row in enumerate(cells)
                  for cx, c in enumerate(row) if c and c[0] == "bill"]
    if not head_cells:
        return []

    h_cy = sum(cy for cy, _ in head_cells) / len(head_cells)
    h_cx = sum(cx for _, cx in head_cells) / len(head_cells)

    if bill_cells:
        b_cy = sum(cy for cy, _ in bill_cells) / len(bill_cells)
        b_cx = sum(cx for _, cx in bill_cells) / len(bill_cells)
        # Vector from bill back into the head. Eyes sit ~40% of that vector
        # behind the bill, raised one cell above the bill line.
        dx = h_cx - b_cx
        dy = h_cy - b_cy
        anchor_cx = b_cx + dx * 0.4
        anchor_cy = b_cy + dy * 0.4 - 1
        # If the bill is roughly head-on (vector tiny), place two symmetric
        # eyes on either side; otherwise the head is in profile, single eye.
        if abs(dx) < 1.5:
            return [
                (round(anchor_cy), round(anchor_cx - 3)),
                (round(anchor_cy), round(anchor_cx + 3)),
            ]
        return [(round(anchor_cy), round(anchor_cx))]

    # No bill visible: head facing away. Plant eye(s) symmetrically near the
    # top of the head silhouette so the back of the head still reads as a duck.
    top_cy = min(cy for cy, _ in head_cells)
    return [
        (top_cy + 2, round(h_cx) - 2),
        (top_cy + 2, round(h_cx) + 2),
    ]


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
                    if cls == "eye" and cy > EYE_MAX_ROW:
                        cls = "chest"
                    cls_counts[cls] += 1
                    n += 1
            if n == 0:
                continue
            total = sum(cls_counts.values())
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
            avg_a = a_sum / cell_pixels
            density = min(1.0, max(0.0, (avg_a / 255 - 0.2) / 0.8))
            idx = int(density * (len(RAMP) - 1))
            cells[cy][cx] = (dominant, RAMP[idx])

    # Synthesize eye dots — one per frame minimum, two for head-on / back-on.
    for ey, ex in synthesize_eyes(cells):
        if 0 <= ey < ROWS and 0 <= ex < COLS and cells[ey][ex] is not None:
            cells[ey][ex] = ("eye", "@")
            counts["eye"] += 1

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
