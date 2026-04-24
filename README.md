# dtgphotomask

**Print your photos on t-shirts. Without turning the shirt into cardboard.**

Direct-to-garment (DTG) printing dumps a lot of ink onto fabric. Great for solid designs — not so great when your photo covers the whole shirt and it comes out stiff, cracked, and uncomfortable to wear. This toolkit fixes that by punching geometric holes into your image's transparency layer before it goes to the printer.

Less ink. Same image. Shirt you can actually move in.

---

## What it does

Takes an image and applies a repeating transparency mask — circles, hexagons, stars, squares, triangles, or grid lines — reducing ink coverage while keeping the design visually intact at normal viewing distance. The transparent gaps let the fabric breathe and the ink flex, so the print lasts longer and feels better.

Three tools:

| Tool | What it's for |
|------|--------------|
| `mask_tui.py` | **Interactive TUI** — live preview, file browser, all the options |
| `mask.py` | **Geometric masks** — circles, hexagons, stars, squares, triangles |
| `grid_mask.py` | **Grid masks** — horizontal/vertical lines, DPI-aware inch measurements |

---

## The TUI

<img width="1440" height="852" alt="Screenshot 2026-04-24 at 12 23 47 AM" src="https://github.com/user-attachments/assets/59b95d35-451f-4cfd-8aef-3d197f8b619c" />
<img width="1440" height="852" alt="Screenshot 2026-04-24 at 12 23 57 AM" src="https://github.com/user-attachments/assets/fdc87f92-cf05-4479-8924-01fc4149dd56" />


Run it with:

```bash
python mask_tui.py
```

Change a parameter, the preview updates live. Click the `…` buttons to browse for files. Hit **Run** when you like what you see.

---

## Quick start

### Install dependencies

```bash
pip install Pillow numpy textual rich
```

### Grid mask (simplest path to a DTG-ready file)

```bash
python grid_mask.py my_photo.jpg output.png
```

Default settings: 0.1" cells, 0.02" transparent lines at 300 DPI. Removes ~36% of ink, keeps the design looking solid.

```
Input:    my_photo.jpg
Size:     4000 × 5000 px
DPI:      300 (detected from image metadata)
Cell:     30px  (0.10in)
Line:     6px   (0.02in)
Pattern:  square / both
Ink:      64.0% coverage  (36.0% ink removed)
Output:   output.png
```

Add `--preview` to composite the masked image over a shirt-colored background and see exactly how it'll look:

```bash
python grid_mask.py my_photo.jpg output.png --preview --preview-bg 30,30,30
```

### Geometric mask (circles, hexagons, stars...)

```bash
# Circles on a triangular grid
python mask.py --input my_photo.jpg --output output.png \
  --grid triangular --shape circle --size 40 --spacing 90

# Stars on a square grid
python mask.py --input my_photo.jpg --output output.png \
  --grid square --shape star5 --size 35 --spacing 80

# Hexagons, because hexagons are great
python mask.py --input my_photo.jpg --output output.png \
  --shape hexagon --size 40 --spacing 90
```

---

## Shapes

`mask.py` supports five shapes tiled across two grid types:

| Shape | `--shape` value | Grid options |
|-------|----------------|-------------|
| Circle | `circle` | square, triangular |
| Square | `square` | square, triangular |
| Triangle | `triangle` | triangular (always) |
| Hexagon | `hexagon` | square, triangular |
| 5-pointed star | `star5` | square, triangular |

Triangular grid staggers every other row for the densest possible coverage. Square grid aligns everything on a rectangular lattice.

---

## Grid mask options

```bash
# Thicker lines = more ink removed
python grid_mask.py photo.jpg out.png --line-thickness 0.05in

# Use millimeters
python grid_mask.py photo.jpg out.png --cell-size 3mm --line-thickness 0.5mm

# Horizontal lines only
python grid_mask.py photo.jpg out.png --lines horizontal

# Triangle grid (three families of lines at 60°)
python grid_mask.py photo.jpg out.png --pattern triangle --cell-size 0.15in

# Invert: make the lines opaque and punch holes in everything else
python grid_mask.py photo.jpg out.png --invert
```

---

## Generate a mask without a source image

Useful for testing patterns or bringing masks into other software:

```bash
python mask.py --output mask.png \
  --grid triangular --shape circle \
  --size 35 --spacing 80 \
  --width 1200 --height 800 --mask-only
```

---

## Why this exists

DTG printers lay down white ink as an underbase before printing the image. On a full-photo print, that's a *lot* of ink stacked up — the shirt gets stiff, the design cracks as it stretches, and the printing shop charges more for coverage. The standard fix is to manually mask images in Photoshop, which is tedious.

This toolkit automates the pattern geometry so you can dial in coverage percentage, preview the result, and generate print-ready PNGs without touching a GUI image editor.

---

## Files

```
mask.py          Geometric aperture mask generator (CLI)
mask_tui.py      Interactive TUI frontend
grid_mask.py     Grid-line mask generator (CLI, DPI-aware)
```

---

## License

MIT
