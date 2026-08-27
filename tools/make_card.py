"""Render the social preview card, using only the standard library.

Twitter, Slack, Discord and GitHub's own preview want a raster image at roughly
1200x630 and none of them render SVG, so the wordmark has to be drawn.

The S reuses the exact curves from the logo (tools/make_icon.py) so the mark and
the wordmark cannot drift apart. H and E are straight strokes. The words
themselves live in the og:description rather than being faked here as bars.

    python tools/make_card.py [output.png]
"""

import struct
import sys
import zlib

from make_icon import CURVES, cubic  # the same S the logo draws

W, H = 1200, 630
BG = (11, 11, 20)
VIOLET, INDIGO, CYAN = (124, 58, 237), (79, 70, 229), (6, 182, 212)
WHITE = (255, 255, 255)

# The logo's S lives in this box on its 128-unit grid.
S_BOX = (42.0, 29.0, 84.0, 84.0)


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def blend(base, colour, alpha):
    return tuple(round(b + (c - b) * alpha) for b, c in zip(base, colour))


def gradient_at(t):
    t = clamp01(t)
    if t < 0.5:
        a, b, u = VIOLET, INDIGO, t * 2
    else:
        a, b, u = INDIGO, CYAN, (t - 0.5) * 2
    return tuple(round(p + (q - p) * u) for p, q in zip(a, b))


def distance_to_segment(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5


def unit_s(steps=90):
    """The logo's S, sampled onto a 0..1 by 0..1 grid."""
    x0, y0, x1, y1 = S_BOX
    points = []
    for curve in CURVES:
        for i in range(steps):
            x, y = cubic(*curve, i / (steps - 1))
            points.append(((x - x0) / (x1 - x0), (y - y0) / (y1 - y0)))
    return list(zip(points, points[1:]))


S_UNIT = unit_s()

# H and E as strokes on the same unit grid.
LETTERS = {
    "H": [[(0.04, 0.0), (0.04, 1.0)], [(0.96, 0.0), (0.96, 1.0)], [(0.04, 0.5), (0.96, 0.5)]],
    "E": [[(0.98, 0.0), (0.06, 0.0), (0.06, 1.0), (0.98, 1.0)], [(0.06, 0.5), (0.76, 0.5)]],
}


def place(letter, x, y, width, height):
    """Segments for one letter, positioned in pixels."""
    if letter == "S":
        strokes = [[a, b] for a, b in S_UNIT]
    else:
        strokes = LETTERS[letter]
    out = []
    for stroke in strokes:
        points = [(x + px * width, y + py * height) for px, py in stroke]
        out.extend(zip(points, points[1:]))
    return out


def render():
    cap = 168
    width = cap * 0.74
    gap = 44
    left = 104
    top = 214
    word = []
    for index, letter in enumerate("SHE"):
        word.extend(place(letter, left + index * (width + gap), top, width, cap))
    word_right = left + 3 * width + 2 * gap

    stroke = 9.0
    badge = (W - 268, 104, W - 104, 268)
    badge_r = 40

    # The rule under the wordmark, and the S inside the badge.
    rule_y = top + cap + 74
    rule_x1 = left + 430

    rows = []
    for y in range(H):
        row = bytearray([0])
        for x in range(W):
            px, py = x + 0.5, y + 0.5
            colour = BG

            for cx, cy, radius, tint, strength in (
                (-80, -60, 660, VIOLET, 0.34),
                (W + 60, H + 100, 760, CYAN, 0.24),
                (W * 0.58, -160, 500, INDIGO, 0.20),
            ):
                d = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
                if d < radius:
                    colour = blend(colour, tint, strength * (1 - d / radius) ** 2)

            if x % 64 == 0 or y % 64 == 0:
                colour = blend(colour, WHITE, 0.03 * max(0.0, 1 - y / (H * 0.95)))

            bx0, by0, bx1, by1 = badge
            if bx0 - 6 <= px <= bx1 + 6 and by0 - 6 <= py <= by1 + 6:
                cx = min(max(px, bx0 + badge_r), bx1 - badge_r)
                cy = min(max(py, by0 + badge_r), by1 - badge_r)
                edge = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 - badge_r
                cover = clamp01(0.5 - edge)
                if cover > 0:
                    t = ((px - bx0) / (bx1 - bx0) + (py - by0) / (by1 - by0)) / 2
                    colour = blend(colour, gradient_at(t), cover)
                    inner = 30.0
                    ux = (px - (bx0 + inner)) / ((bx1 - bx0) - 2 * inner)
                    uy = (py - (by0 + inner)) / ((by1 - by0) - 2 * inner)
                    if -0.4 <= ux <= 1.4 and -0.4 <= uy <= 1.4:
                        near = min(distance_to_segment(ux, uy, a, b) for a, b in S_UNIT)
                        scale = (bx1 - bx0) - 2 * inner
                        colour = blend(colour, WHITE,
                                       cover * clamp01(0.5 - (near * scale - 7.0)))

            if left - 24 <= px <= word_right + 24 and top - 24 <= py <= top + cap + 24:
                near = min(distance_to_segment(px, py, a, b) for a, b in word)
                cover = clamp01(0.5 - (near - stroke))
                if cover > 0:
                    colour = blend(colour, gradient_at((px - left) / (word_right - left)),
                                   cover)

            if rule_y <= py <= rule_y + 6 and left <= px <= rule_x1:
                colour = blend(colour, gradient_at((px - left) / (rule_x1 - left)), 0.9)

            row += bytes(colour) + b"\xff"
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path, raw, width, height):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)
    return len(png)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "site/assets/social-card.png"
    written = write_png(out, render(), W, H)
    print(f"wrote {out} ({W}x{H}, {written // 1024} KB)")


if __name__ == "__main__":
    main()
