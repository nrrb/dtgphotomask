#!/usr/bin/env python3
"""
grid_mask.py — Apply a transparent grid mask to an image for DTG shirt printing.

Breaks up solid ink coverage with a regular grid of transparent lines, reducing
stiffness and improving breathability while preserving visual appearance from a
distance. Output is a PNG with an alpha channel ready for print submission.

Requirements:
    pip install Pillow numpy

Usage examples:

    # Default: 0.1" cells, 0.02" lines at 300 DPI (~80% ink coverage per axis)
    python grid_mask.py shirt.jpg output.png

    # Thicker lines for more aggressive ink reduction
    python grid_mask.py shirt.jpg output.png --line-thickness 0.05in

    # Finer grid with pixel measurements
    python grid_mask.py shirt.jpg output.png --cell-size 24 --line-thickness 4

    # Horizontal lines only (removes horizontal bands, preserves vertical)
    python grid_mask.py shirt.jpg output.png --lines horizontal

    # Save a preview composited over gray (simulates white shirt)
    python grid_mask.py shirt.jpg output.png --preview

    # Preview over a dark shirt color
    python grid_mask.py shirt.jpg output.png --preview --preview-bg 40,40,40

    # Invert: grid lines opaque, cells transparent (produces a lattice cutout)
    python grid_mask.py shirt.jpg output.png --invert

    # Explicit grid offset (fine-tune centering by hand)
    python grid_mask.py shirt.jpg output.png --offset-x 0.05in --offset-y 0.05in

    # Override auto-detected DPI (e.g. file lacks metadata or was mis-tagged)
    python grid_mask.py shirt.jpg output.png --dpi 150

    # Equilateral triangle grid (--lines and --offset-* are ignored)
    python grid_mask.py shirt.jpg output.png --pattern triangle
    python grid_mask.py shirt.jpg output.png --pattern triangle --cell-size 0.15in --line-thickness 0.02in
"""

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Dependency check — fail early with a helpful message
# ---------------------------------------------------------------------------

def _check_dependencies():
    missing = []
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append("numpy")
    if missing:
        print(f"Error: missing required package(s): {', '.join(missing)}")
        print(f"Install with:  pip install {' '.join(missing)}")
        sys.exit(1)


_check_dependencies()

from PIL import Image, ImageOps  # noqa: E402
import numpy as np               # noqa: E402


# ---------------------------------------------------------------------------
# DPI detection
# ---------------------------------------------------------------------------

def detect_dpi(img: Image.Image) -> tuple[int, str]:
    """
    Read DPI from image metadata and return (dpi_value, source_description).

    Pillow exposes DPI as img.info['dpi'] = (x, y) for both JPEG (JFIF/EXIF)
    and PNG (pHYs chunk). Returns (None, reason) if no valid DPI is found.
    """
    dpi_info = img.info.get("dpi")
    if dpi_info:
        x_dpi, y_dpi = dpi_info
        # A value of 1 means "unit unknown" in the PNG pHYs chunk — not a real DPI
        if x_dpi > 1:
            dpi = round(x_dpi)
            note = "" if x_dpi == y_dpi else f" (non-square: {x_dpi:.0f}×{y_dpi:.0f}, using width)"
            return dpi, f"detected from image metadata ({dpi} DPI{note})"
    return None, "no DPI metadata found"


# ---------------------------------------------------------------------------
# Measurement parsing
# ---------------------------------------------------------------------------

def parse_measurement(value: str, dpi: int) -> int:
    """
    Convert a measurement string to an integer pixel count.

    Supported formats:
        "0.1in"  → inches × DPI
        "2.54mm" → millimetres × (DPI / 25.4)
        "30px"   → explicit pixels (integer)
        "30"     → plain number treated as pixels
    """
    v = value.strip().lower()
    try:
        if v.endswith("in"):
            return round(float(v[:-2]) * dpi)
        elif v.endswith("mm"):
            return round(float(v[:-2]) / 25.4 * dpi)
        elif v.endswith("px"):
            return int(float(v[:-2]))
        else:
            return int(float(v))
    except ValueError:
        raise ValueError(
            f"Cannot parse '{value}' — expected a number optionally "
            "followed by 'in', 'mm', or 'px' (e.g. 0.1in, 2.5mm, 30)"
        )


# ---------------------------------------------------------------------------
# Grid geometry
# ---------------------------------------------------------------------------

def compute_centered_offset(image_size: int, cell_size: int, line_thickness: int) -> int:
    """
    Return the grid phase offset so the center of the image lands in the
    middle of an opaque cell rather than on a transparent line.

    Result: equal partial margins on both edges, symmetric appearance.
    """
    # Mid-point of the opaque region within one period [line_thickness, cell_size)
    cell_center_in_period = (line_thickness + cell_size) / 2.0
    # Shift the pattern so that (image_size / 2) coincides with a cell center
    return int(image_size / 2.0 - cell_center_in_period) % cell_size


def build_line_mask_1d(size: int, cell_size: int, line_thickness: int, offset: int) -> np.ndarray:
    """
    Return a 1-D boolean array of length `size`.
    True at positions that fall on a transparent grid line.

    The period is `cell_size` pixels; the first `line_thickness` pixels of
    each period (after the phase shift) are marked as lines.
    """
    # Python/NumPy modulo always returns non-negative for a positive divisor
    positions = (np.arange(size, dtype=np.int64) - offset) % cell_size
    return positions < line_thickness


# ---------------------------------------------------------------------------
# Core masking
# ---------------------------------------------------------------------------

def apply_grid_mask(
    img: Image.Image,
    cell_size: int,
    line_thickness: int,
    direction: str = "both",
    offset_x: int = None,
    offset_y: int = None,
    invert: bool = False,
) -> Image.Image:
    """
    Apply a transparent grid mask to an RGBA image and return the result.

    Grid line pixels have their alpha set to 0 (fully transparent).
    All other pixels retain their original RGBA values, including any
    pre-existing transparency in the source image.

    Parameters
    ----------
    img            : RGBA PIL Image
    cell_size      : grid period in pixels
    line_thickness : width of each transparent line in pixels
    direction      : 'both', 'horizontal', or 'vertical'
    offset_x/y     : grid phase offset; None → auto-centred
    invert         : swap mask so cells become transparent and lines stay opaque
    """
    width, height = img.size

    if offset_x is None:
        offset_x = compute_centered_offset(width, cell_size, line_thickness)
    if offset_y is None:
        offset_y = compute_centered_offset(height, cell_size, line_thickness)

    # 1-D masks: True where a line falls along each axis
    x_on_line = build_line_mask_1d(width,  cell_size, line_thickness, offset_x)  # (W,)
    y_on_line = build_line_mask_1d(height, cell_size, line_thickness, offset_y)  # (H,)

    # Expand to 2-D (H, W) by broadcasting
    if direction == "both":
        transparent = x_on_line[np.newaxis, :] | y_on_line[:, np.newaxis]
    elif direction == "vertical":
        transparent = np.broadcast_to(x_on_line[np.newaxis, :], (height, width))
    else:  # horizontal
        transparent = np.broadcast_to(y_on_line[:, np.newaxis], (height, width))

    if invert:
        transparent = ~transparent  # creates a new writeable array

    arr = np.array(img, dtype=np.uint8)
    arr[transparent, 3] = 0  # zero alpha at every masked pixel

    return Image.fromarray(arr, "RGBA")


# ---------------------------------------------------------------------------
# Triangle grid masking
# ---------------------------------------------------------------------------

def apply_triangle_grid_mask(
    img: Image.Image,
    cell_size: int,
    line_thickness: int,
    invert: bool = False,
) -> Image.Image:
    """
    Apply an equilateral triangle grid mask to an RGBA image and return the result.

    Three families of parallel lines (0°, 60°, 120°) subdivide the plane into
    equilateral triangles with side length `cell_size` pixels.  Each line band
    is `line_thickness` pixels wide measured perpendicular to the lines.

    Parameters
    ----------
    img            : RGBA PIL Image
    cell_size      : side length of each equilateral triangle in pixels
    line_thickness : perpendicular width of each transparent line band in pixels
    invert         : swap mask so cells become transparent and lines stay opaque
    """
    width, height = img.size

    # h = perpendicular spacing between parallel lines in each family
    h = cell_size * np.sqrt(3) / 2
    # period of the diagonal coordinate (= 2h = sqrt(3) * cell_size)
    period_d = cell_size * np.sqrt(3)
    # threshold for diagonal families: factor of 2 because perpendicular
    # distance = c / 2 for the (±√3, 1) normal vectors (magnitude = 2)
    thresh_d = 2.0 * line_thickness

    x = np.arange(width,  dtype=np.float64)
    y = np.arange(height, dtype=np.float64)

    c1 = y[:, None] % h                                      # horizontal family  (period = h)
    c2 = (y[:, None] - np.sqrt(3) * x[None, :]) % period_d  # 60° family
    c3 = (y[:, None] + np.sqrt(3) * x[None, :]) % period_d  # 120° family

    transparent = (c1 < line_thickness) | (c2 < thresh_d) | (c3 < thresh_d)

    if invert:
        transparent = ~transparent

    arr = np.array(img, dtype=np.uint8)
    arr[transparent, 3] = 0
    return Image.fromarray(arr, "RGBA")


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def generate_preview(masked: Image.Image, bg_color: tuple) -> Image.Image:
    """
    Composite the masked image over a solid background colour and return
    an RGB image. Useful for checking the effect without a transparency-aware
    viewer (simulates how the print will look over a shirt).
    """
    background = Image.new("RGBA", masked.size, bg_color)
    background.paste(masked, mask=masked.getchannel("A"))
    return background.convert("RGB")


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def coverage_summary(cell_size: int, line_thickness: int, direction: str, pattern: str = "square") -> str:
    """Human-readable ink coverage estimate after masking."""
    if pattern == "triangle":
        h = cell_size * np.sqrt(3) / 2
        keep = max(0.0, 1.0 - line_thickness / h)
        coverage = keep ** 3  # approximate via independence of three families
        return f"~{coverage:.1%} coverage  (~{1 - coverage:.1%} ink removed)"
    ratio = (cell_size - line_thickness) / cell_size
    coverage = ratio ** 2 if direction == "both" else ratio
    return f"{coverage:.1%} coverage  ({1 - coverage:.1%} ink removed)"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grid_mask.py",
        description=(
            "Apply a transparent grid mask to an image for DTG shirt printing.\n"
            "Grid lines become fully transparent in the output PNG."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("input",  help="Input image file (.jpg or .png)")
    parser.add_argument("output", help="Output file — must be .png")

    parser.add_argument(
        "--cell-size", default="0.1in", metavar="SIZE",
        help="Grid cell size: e.g. 0.1in, 2.54mm, 30 (pixels).  Default: 0.1in",
    )
    parser.add_argument(
        "--line-thickness", default="0.02in", metavar="SIZE",
        help="Transparent line thickness (same units as --cell-size).  Default: 0.02in",
    )
    parser.add_argument(
        "--dpi", type=int, default=None,
        help=(
            "Image resolution in DPI — used when measurements are in inches or mm. "
            "Auto-detected from image metadata when available; falls back to 300 if absent."
        ),
    )
    parser.add_argument(
        "--pattern", choices=["square", "triangle"], default="square",
        help="Grid pattern: 'square' for rectangular grid, 'triangle' for equilateral triangles.  Default: square",
    )
    parser.add_argument(
        "--lines", choices=["both", "horizontal", "vertical"], default="both",
        help="Which axis to cut transparent lines on (square pattern only).  Default: both",
    )
    parser.add_argument(
        "--offset-x", default=None, metavar="SIZE",
        help="Override horizontal grid origin (pixels, inches, or mm).  Default: auto-centred",
    )
    parser.add_argument(
        "--offset-y", default=None, metavar="SIZE",
        help="Override vertical grid origin (pixels, inches, or mm).  Default: auto-centred",
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Also save a preview PNG composited over the background colour",
    )
    parser.add_argument(
        "--preview-bg", default="220,220,220", metavar="R,G,B",
        help="Preview background as R,G,B (0–255).  Default: 220,220,220 (light grey)",
    )
    parser.add_argument(
        "--invert", action="store_true",
        help="Invert the mask: cells become transparent, lines stay opaque",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --- Validate paths ---
    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"Input file not found: {args.input}")
    if input_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        parser.error(f"Input must be .jpg or .png, got: {input_path.suffix!r}")

    output_path = Path(args.output)
    if output_path.suffix.lower() != ".png":
        parser.error(f"Output must be .png, got: {output_path.suffix!r}")

    # --- Load image (needed before measurement parsing to detect DPI) ---
    print(f"Input:    {input_path}")
    try:
        img = Image.open(input_path)
    except Exception as e:
        print(f"Error: could not open image — {e}", file=sys.stderr)
        sys.exit(1)

    # Honour EXIF orientation (common in phone photos used as shirt artwork)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass  # Not all images have EXIF; not critical

    # --- Resolve DPI ---
    if args.dpi is not None:
        dpi = args.dpi
        dpi_label = f"specified ({dpi} DPI)"
    else:
        dpi, dpi_label = detect_dpi(img)
        if dpi is None:
            dpi = 300
            dpi_label = "assumed 300 DPI (no metadata — use --dpi to override)"

    img = img.convert("RGBA")
    w, h = img.size

    # --- Parse measurements (now that DPI is known) ---
    try:
        cell_px = parse_measurement(args.cell_size, dpi)
        line_px = parse_measurement(args.line_thickness, dpi)
    except ValueError as e:
        parser.error(str(e))

    if cell_px < 2:
        parser.error(f"--cell-size resolves to {cell_px}px — too small (minimum 2)")
    if line_px < 1:
        parser.error(f"--line-thickness resolves to {line_px}px — too small (minimum 1)")
    if line_px >= cell_px:
        parser.error(
            f"--line-thickness ({line_px}px) must be less than --cell-size ({cell_px}px); "
            "otherwise the whole image would be transparent."
        )

    if args.pattern == "triangle":
        h_px = cell_px * np.sqrt(3) / 2
        if line_px >= h_px:
            parser.error(
                f"--line-thickness ({line_px}px) must be less than the triangle row height "
                f"({h_px:.0f}px = cell-size × √3/2); otherwise the whole image would be transparent."
            )

    offset_x = offset_y = None
    try:
        if args.offset_x is not None:
            offset_x = parse_measurement(args.offset_x, dpi)
        if args.offset_y is not None:
            offset_y = parse_measurement(args.offset_y, dpi)
    except ValueError as e:
        parser.error(str(e))

    # --- Parse preview background colour ---
    try:
        rgb = [int(c.strip()) for c in args.preview_bg.split(",")]
        if len(rgb) != 3 or not all(0 <= v <= 255 for v in rgb):
            raise ValueError
        preview_bg = (rgb[0], rgb[1], rgb[2], 255)
    except ValueError:
        parser.error(
            f"--preview-bg must be three comma-separated integers 0–255, "
            f"e.g. 220,220,220.  Got: {args.preview_bg!r}"
        )

    print(f"Size:     {w} × {h} px")
    print(f"DPI:      {dpi_label}")
    print(f"Cell:     {cell_px}px  ({args.cell_size})")
    print(f"Line:     {line_px}px  ({args.line_thickness})")
    print(f"Pattern:  {args.pattern}" + (f" / {args.lines}" if args.pattern == "square" else ""))
    print(f"Ink:      {coverage_summary(cell_px, line_px, args.lines, args.pattern)}")
    if args.invert:
        print("Mode:     inverted (cells transparent, lines opaque)")

    # --- Apply mask ---
    if args.pattern == "triangle":
        if args.lines != "both":
            print("Note:     --lines is ignored for triangle pattern")
        if offset_x is not None or offset_y is not None:
            print("Note:     --offset-x/--offset-y are ignored for triangle pattern")
        result = apply_triangle_grid_mask(
            img,
            cell_size=cell_px,
            line_thickness=line_px,
            invert=args.invert,
        )
    else:
        result = apply_grid_mask(
            img,
            cell_size=cell_px,
            line_thickness=line_px,
            direction=args.lines,
            offset_x=offset_x,
            offset_y=offset_y,
            invert=args.invert,
        )

    # --- Save outputs ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(output_path), "PNG")
    print(f"Output:   {output_path}")

    if args.preview:
        preview_path = output_path.with_name(output_path.stem + "_preview.png")
        generate_preview(result, preview_bg).save(str(preview_path), "PNG")
        print(f"Preview:  {preview_path}")


if __name__ == "__main__":
    main()
