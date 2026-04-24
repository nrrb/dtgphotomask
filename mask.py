#!/usr/bin/env python3
"""
mask.py — Regular grid aperture mask generator and image processor.

Generates geometric tiling masks (circle, square, triangle, hexagon, star5)
on square or triangular grids, and applies them to images as transparency masks.
Also supports loading external black-and-white PNG masks directly.

Usage:
  Mode A (generated tiling mask):
    python mask.py --input photo.jpg --output result.png \
      --grid square --shape circle --size 40 --spacing 90 \
      --width 1200 --height 800

  Mode A with triangles (always uses triangular grid):
    python mask.py --input photo.jpg --output result.png \
      --shape triangle --size 40 --spacing 90 \
      --width 1200 --height 800 \
      --triangle-orientation fixed --triangle-rotation 30

  Mode A mask only (no source image):
    python mask.py --output mask.png \
      --grid triangular --shape hexagon --size 35 --spacing 80 \
      --width 1200 --height 800 --mask-only

  Mode B (external B&W mask):
    python mask.py --input photo.jpg --output result.png \
      --mask-file my_mask.png
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Vertex generators
# ---------------------------------------------------------------------------

def star5_vertices(cx, cy, outer_r, inner_r):
    """Return 10 (x, y) vertices for a 5-pointed star, tip pointing up."""
    pts = []
    for i in range(10):
        angle = math.radians(-90 + i * 36)  # start at top
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def regular_polygon_vertices(cx, cy, r, n, rotation_deg=0.0):
    """Return n (x, y) vertices for a regular polygon centred at (cx, cy)."""
    pts = []
    for i in range(n):
        angle = math.radians(rotation_deg + i * 360 / n)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def triangle_vertices(cx, cy, r, point_up=True):
    """
    Equilateral triangle with circumradius r.
    point_up=True  → vertex at top  (rotation -90°)
    point_up=False → vertex at bottom (rotation 90°)
    """
    rot = -90.0 if point_up else 90.0
    return regular_polygon_vertices(cx, cy, r, 3, rotation_deg=rot)


def square_vertices(cx, cy, half_w, rotation_deg=0.0):
    """Square with half-width half_w."""
    return regular_polygon_vertices(cx, cy, half_w * math.sqrt(2), 4,
                                    rotation_deg=rotation_deg + 45)


def hexagon_vertices(cx, cy, r, rotation_deg=0.0):
    return regular_polygon_vertices(cx, cy, r, 6, rotation_deg=rotation_deg)


# ---------------------------------------------------------------------------
# Grid centre generators
# ---------------------------------------------------------------------------

def square_grid_centers(width, height, spacing, offset=(0, 0)):
    """Yield (col, row, cx, cy) for a square grid covering the canvas."""
    ox, oy = offset
    cols = math.ceil(width / spacing) + 2
    rows = math.ceil(height / spacing) + 2
    start_x = ox % spacing - spacing
    start_y = oy % spacing - spacing
    for row in range(rows):
        for col in range(cols):
            cx = start_x + col * spacing
            cy = start_y + row * spacing
            yield col, row, cx, cy


def triangular_grid_centers(width, height, spacing, offset=(0, 0)):
    """
    Yield (col, row, cx, cy) for a triangular (hex close-packed) lattice.
    Row spacing = spacing * sqrt(3)/2, alternating rows offset by spacing/2.
    """
    ox, oy = offset
    row_h = spacing * math.sqrt(3) / 2
    cols = math.ceil(width / spacing) + 3
    rows = math.ceil(height / row_h) + 3
    start_x = ox % spacing - spacing
    start_y = oy % row_h - row_h
    for row in range(rows):
        for col in range(cols):
            cx = start_x + col * spacing + (spacing / 2 if row % 2 == 1 else 0)
            cy = start_y + row * row_h
            yield col, row, cx, cy


# ---------------------------------------------------------------------------
# Mask drawing
# ---------------------------------------------------------------------------

def draw_aperture(draw, shape, col, row, cx, cy, size,
                  tri_orientation, tri_rotation_deg):
    """Stamp one aperture onto the ImageDraw canvas (white on black)."""
    if shape == "circle":
        draw.ellipse(
            [cx - size, cy - size, cx + size, cy + size],
            fill=255
        )

    elif shape == "square":
        pts = square_vertices(cx, cy, size)
        draw.polygon(pts, fill=255)

    elif shape == "hexagon":
        pts = hexagon_vertices(cx, cy, size, rotation_deg=0)
        draw.polygon(pts, fill=255)

    elif shape == "star5":
        inner_r = size * 0.382
        pts = star5_vertices(cx, cy, size, inner_r)
        draw.polygon(pts, fill=255)

    elif shape == "triangle":
        if tri_orientation == "alternating":
            # parity by column index within triangular lattice
            point_up = (col % 2 == 0)
        else:
            # fixed — use tri_rotation_deg; point_up ignored, use polygon directly
            pts = regular_polygon_vertices(cx, cy, size, 3,
                                           rotation_deg=tri_rotation_deg - 90)
            draw.polygon(pts, fill=255)
            return
        pts = triangle_vertices(cx, cy, size, point_up=point_up)
        draw.polygon(pts, fill=255)


def generate_tiling_mask(width, height, grid_type, shape, size, spacing,
                         offset, tri_orientation, tri_rotation_deg):
    """
    Return a grayscale PIL Image (mode 'L') of the tiling mask.
    White = keep, Black = transparent.
    """
    mask_img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask_img)

    # Triangle always uses triangular grid regardless of grid_type arg
    effective_grid = "triangular" if shape == "triangle" else grid_type

    if effective_grid == "square":
        centers = square_grid_centers(width, height, spacing, offset)
    else:
        centers = triangular_grid_centers(width, height, spacing, offset)

    for col, row, cx, cy in centers:
        draw_aperture(draw, shape, col, row, cx, cy, size,
                      tri_orientation, tri_rotation_deg)

    return mask_img


# ---------------------------------------------------------------------------
# Image application
# ---------------------------------------------------------------------------

def apply_mask_to_image(source_img, mask_img):
    """
    Apply a grayscale mask to a source image.
    White mask pixels → fully opaque, black → fully transparent.
    Returns RGBA image.
    """
    src = source_img.convert("RGBA")
    alpha = mask_img.convert("L")
    # Resize mask to match source if needed (Mode B safety net)
    if alpha.size != src.size:
        alpha = alpha.resize(src.size, Image.LANCZOS)
    r, g, b, _ = src.split()
    return Image.merge("RGBA", (r, g, b, alpha))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate geometric tiling masks and apply to images."
    )

    # Source image
    p.add_argument("--input", "-i", metavar="PATH",
                   help="Source image path (required unless --mask-only)")

    # Output
    p.add_argument("--output", "-o", metavar="PATH", required=True,
                   help="Output PNG path")

    # Mode B
    p.add_argument("--mask-file", metavar="PATH",
                   help="External B&W mask PNG (Mode B). Black=keep, white=transparent.")

    # Mode A — grid & aperture
    p.add_argument("--grid", choices=["square", "triangular"], default="square",
                   help="Grid lattice type (ignored when --shape triangle)")
    p.add_argument("--shape",
                   choices=["circle", "square", "triangle", "hexagon", "star5"],
                   default="circle",
                   help="Aperture shape")
    p.add_argument("--size", type=float, default=40,
                   help="Aperture radius / half-width in pixels")
    p.add_argument("--spacing", type=float, default=90,
                   help="Center-to-center spacing in pixels")
    p.add_argument("--width", type=int, default=None,
                   help="Canvas width in pixels (defaults to source image width)")
    p.add_argument("--height", type=int, default=None,
                   help="Canvas height in pixels (defaults to source image height)")
    p.add_argument("--offset", type=float, nargs=2, default=[0, 0],
                   metavar=("DX", "DY"),
                   help="Grid offset in pixels (default: 0 0)")

    # Triangle-specific
    p.add_argument("--triangle-orientation",
                   choices=["alternating", "fixed"], default="alternating",
                   help="Triangle aperture orientation (default: alternating)")
    p.add_argument("--triangle-rotation", type=float, default=0.0,
                   metavar="DEG",
                   help="Rotation in degrees for fixed triangle orientation "
                        "(0 = pointing up, default: 0)")

    # Mask only
    p.add_argument("--mask-only", action="store_true",
                   help="Output generated mask as grayscale PNG only (Mode A)")

    return p.parse_args()


def main():
    args = parse_args()

    mode_b = args.mask_file is not None

    # ---- Mode B: external mask ----
    if mode_b:
        if args.input is None:
            print("Error: --input is required in Mode B (--mask-file).",
                  file=sys.stderr)
            sys.exit(1)

        source_img = Image.open(args.input)
        mask_img = Image.open(args.mask_file).convert("L")

        # Invert: black(0) → keep(255), white(255) → transparent(0)
        mask_arr = np.array(mask_img)
        mask_arr = 255 - mask_arr
        mask_img = Image.fromarray(mask_arr, mode="L")

        result = apply_mask_to_image(source_img, mask_img)
        result.save(args.output, format="PNG")
        print(f"Saved masked image → {args.output}")
        return

    # ---- Mode A: generated tiling mask ----

    # Resolve canvas size
    if args.width is None or args.height is None:
        if args.input is None and not args.mask_only:
            print("Error: Provide --width and --height, or --input to infer size.",
                  file=sys.stderr)
            sys.exit(1)
        if args.input is not None:
            with Image.open(args.input) as probe:
                iw, ih = probe.size
            width = args.width if args.width is not None else iw
            height = args.height if args.height is not None else ih
        else:
            print("Error: --width and --height are required with --mask-only "
                  "when no --input is given.", file=sys.stderr)
            sys.exit(1)
    else:
        width, height = args.width, args.height

    mask_img = generate_tiling_mask(
        width=width,
        height=height,
        grid_type=args.grid,
        shape=args.shape,
        size=args.size,
        spacing=args.spacing,
        offset=tuple(args.offset),
        tri_orientation=args.triangle_orientation,
        tri_rotation_deg=args.triangle_rotation,
    )

    if args.mask_only:
        mask_img.save(args.output, format="PNG")
        print(f"Saved mask → {args.output}")
        return

    if args.input is None:
        print("Error: --input is required unless --mask-only is set.",
              file=sys.stderr)
        sys.exit(1)

    source_img = Image.open(args.input)
    result = apply_mask_to_image(source_img, mask_img)
    result.save(args.output, format="PNG")
    print(f"Saved masked image → {args.output}")


if __name__ == "__main__":
    main()
