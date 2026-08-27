"""Render the SHE logo to a PNG, using nothing but the standard library.

The VS Code marketplace and social-preview cards want a raster icon. Rather
than add Pillow or a headless browser as a build dependency, this walks the
same curves the SVG describes and stamps them onto a pixel buffer.

    python tools/make_icon.py [size] [output.png]
"""

import struct
import sys
import zlib

VIOLET, INDIGO, CYAN = (124, 58, 237), (79, 70, 229), (6, 182, 212)
WHITE = (255, 255, 255)
CORNER = 30 / 128          # corner radius, as a fraction of the side
STROKE = 5.5 / 128         # half the S stroke width

# The S from site/assets/logo.svg, as cubic segments on a 128x128 grid.
CURVES = [
    ((84, 44), (84, 35), (76, 29), (64, 29)),
    ((64, 29), (52, 29), (44, 35), (44, 43)),
    ((44, 43), (44, 61), (84, 51), (84, 69)),
    ((84, 69), (84, 78), (75, 84), (63, 84)),
    ((63, 84), (51, 84), (42, 78), (42, 69)),
]
CURSOR = (86, 79, 95, 88)                  # the little block after the S
TICKS = [((64, 16), (64, 23)), ((112, 64), (105, 64)),
         ((64, 112), (64, 105)), ((16, 64), (23, 64))]


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def sample_path(steps=260):
    points = []
    for curve in CURVES:
        for i in range(steps):
            points.append(cubic(*curve, i / (steps - 1)))
    return points


def blend(base, colour, alpha):
    return tuple(round(b + (c - b) * alpha) for b, c in zip(base, colour))


def gradient(x, y, size):
    t = (x / size + y / size) / 2
    if t < 0.5:
        a, b, u = VIOLET, INDIGO, t * 2
    else:
        a, b, u = INDIGO, CYAN, (t - 0.5) * 2
    return tuple(round(p + (q - p) * u) for p, q in zip(a, b))


def render(size=128):
    scale = size / 128
    radius = CORNER * size
    stroke = STROKE * size
    points = [(x * scale, y * scale) for x, y in sample_path()]
    ticks = [((a[0] * scale, a[1] * scale), (b[0] * scale, b[1] * scale)) for a, b in TICKS]
    cursor = tuple(v * scale for v in CURSOR)

    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            px, py = x + 0.5, y + 0.5

            # rounded-square mask, softened at the edge
            cx = min(max(px, radius), size - radius)
            cy = min(max(py, radius), size - radius)
            edge = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 - radius
            alpha = clamp01(0.5 - edge)
            if alpha <= 0:
                row += bytes((0, 0, 0, 0))
                continue

            colour = gradient(x, y, size)

            # hour ticks, faint
            for a, b in ticks:
                d = distance_to_segment(px, py, a, b)
                coverage = clamp01(1.5 * scale - d + 0.5)
                if coverage > 0:
                    colour = blend(colour, WHITE, coverage * 0.38)

            # the S
            near = min(((px - qx) ** 2 + (py - qy) ** 2 for qx, qy in points))
            d = near ** 0.5 - stroke
            coverage = clamp01(0.5 - d)
            if coverage > 0:
                colour = blend(colour, WHITE, coverage)

            # the cursor block
            if cursor[0] <= px <= cursor[2] and cursor[1] <= py <= cursor[3]:
                colour = WHITE

            row += bytes(colour) + bytes([round(alpha * 255)])
        rows.append(bytes(row))
    return b"".join(rows)


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def distance_to_segment(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def write_png(path, raw, size):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)
    return len(png)


def main():
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 128
    out = sys.argv[2] if len(sys.argv) > 2 else "icon.png"
    written = write_png(out, render(size), size)
    print(f"wrote {out} ({size}x{size}, {written} bytes)")


if __name__ == "__main__":
    main()
