# PLAN: dtgphotomask Web UI

Client-side Vite + React + Tailwind CSS app that replicates `mask_tui.py` entirely in the browser.  
No server. All image processing runs on the client via Canvas API.

---

## Goals

- Upload an image → live preview of the generated tiling mask + masked image
- All parameters from Mode A of `mask.py` exposed as controls
- "Mask Only" toggle: download just the grayscale mask (no source image required)
- Download button + right-click-to-save on result image
- Filename derived from original image name + key mask parameters
- Checkerboard background behind transparent areas
- Mobile-first layout, also good on desktop
- 100% client-side, no backend

---

## Technology

| Layer | Choice | Reason |
|-------|--------|--------|
| Bundler | Vite | Fast HMR, zero-config |
| UI | React 18 | Component state fits live-preview pattern |
| Styling | Tailwind CSS v3 | Mobile-first utilities, no custom CSS files needed |
| Canvas | Native browser Canvas 2D API | Port of `mask.py` geometry logic |
| Image output | `canvas.toBlob("image/png")` → object URL | Pure client-side download |

---

## Project Structure

```
dtgphotomask/
├── mask.py                   # existing Python (unchanged)
├── mask_tui.py               # existing TUI (unchanged)
├── web/                      # NEW — Vite/React app
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       │   ├── ImageDropzone.jsx    # drag-and-drop + file picker
│       │   ├── ParamControls.jsx    # all mask parameter controls
│       │   ├── MaskPreview.jsx      # live B&W mask canvas
│       │   ├── ResultPreview.jsx    # masked image on checkerboard
│       │   └── DownloadButton.jsx   # named download + instructions
│       └── lib/
│           ├── maskEngine.js        # port of mask.py geometry to Canvas 2D
│           └── useMaskProcessor.js  # React hook: params → canvases (debounced)
```

---

## Porting `mask.py` to `maskEngine.js`

All math is a direct JavaScript translation of the Python. No external libraries needed.

### Functions to port

| Python | JavaScript | Notes |
|--------|-----------|-------|
| `star5_vertices` | `star5Vertices(cx, cy, outerR, innerR)` | Direct port |
| `regular_polygon_vertices` | `regularPolygonVertices(cx, cy, r, n, rotDeg)` | Direct port |
| `triangle_vertices` | `triangleVertices(cx, cy, r, pointUp)` | Wraps above |
| `square_vertices` | `squareVertices(cx, cy, halfW, rotDeg)` | Direct port |
| `hexagon_vertices` | `hexagonVertices(cx, cy, r, rotDeg)` | Direct port |
| `square_grid_centers` | `squareGridCenters(w, h, spacing, offset)` | Generator → array |
| `triangular_grid_centers` | `triangularGridCenters(w, h, spacing, offset)` | Generator → array |
| `draw_aperture` | `drawAperture(ctx, shape, col, row, cx, cy, size, triOri, triRotDeg)` | Canvas 2D |
| `generate_tiling_mask` | `generateTilingMask(canvas, params)` | Draws to offscreen canvas |
| `apply_mask_to_image` | `applyMaskToImage(sourceCanvas, maskCanvas)` | Returns new canvas |

### Canvas rendering approach

- Use `OffscreenCanvas` (or a hidden `<canvas>`) for mask generation
- `generateTilingMask`: fill black, draw white apertures with `ctx.fill()`
- `applyMaskToImage`: draw source image, then use mask as alpha channel via `ImageData` pixel loop (set each pixel's alpha to the mask's red channel value)
- Final result canvas has checkerboard as CSS `background` (no extra pixels needed)

---

## UI Layout

### Mobile (single column)

```
┌─────────────────────────────┐
│  dtg photomask              │  ← header
├─────────────────────────────┤
│  [  Drop image here / tap ] │  ← ImageDropzone (tap to open picker)
├─────────────────────────────┤
│  Grid      [ Square ▾ ]     │
│  Shape     [ Circle ▾ ]     │
│  Size      [  40  ]         │
│  Spacing   [  90  ]         │
│  Offset X  [   0  ]         │
│  Offset Y  [   0  ]         │
│  (triangle fields hidden    │
│   unless shape=triangle)    │
│  ☐ Mask Only                │
├─────────────────────────────┤
│  MASK PREVIEW               │
│  ┌─────────────────────┐    │
│  │  live canvas        │    │
│  └─────────────────────┘    │
├─────────────────────────────┤
│  RESULT (checkerboard bg)   │
│  ┌─────────────────────┐    │
│  │  masked image       │    │
│  │  (right-click save) │    │
│  └─────────────────────┘    │
│  [ ⬇ Download result.png ]  │
└─────────────────────────────┘
```

### Desktop (two-column)

```
┌─────────────────────────────────────────────────────┐
│  dtg photomask                                      │
├──────────────────────┬──────────────────────────────┤
│  ImageDropzone       │   MASK PREVIEW               │
│                      │   ┌──────────────────────┐   │
│  Grid    [ Sq ▾ ]    │   │  live canvas         │   │
│  Shape   [ Ci ▾ ]    │   └──────────────────────┘   │
│  Size    [ 40 ]      │                              │
│  Spacing [ 90 ]      │   RESULT                     │
│  Offset  [ 0 ][ 0 ] │   ┌──────────────────────┐   │
│  ...                 │   │  masked image        │   │
│  ☐ Mask Only         │   └──────────────────────┘   │
│                      │   [ ⬇ Download ]             │
└──────────────────────┴──────────────────────────────┘
```

---

## Parameters (Mode A only)

| Control | Type | Default | Notes |
|---------|------|---------|-------|
| Grid | Select | square | square / triangular |
| Shape | Select | circle | circle / square / triangle / hexagon / star5 |
| Size | Number input | 40 | aperture radius / half-width in px |
| Spacing | Number input | 90 | center-to-center spacing in px |
| Offset X | Number input | 0 | grid offset px |
| Offset Y | Number input | 0 | grid offset px |
| Tri orientation | Select | alternating | shown only when shape=triangle |
| Tri rotation° | Number input | 0 | shown only when shape=triangle & orientation=fixed |
| Mask Only | Checkbox | false | hides source image dropzone requirement |

---

## Live Preview Behavior

1. Params change → debounce 200ms → `useMaskProcessor` hook fires
2. Hook renders mask to an offscreen canvas scaled to preview size (max 600px wide)
3. If source image loaded: apply mask → render to result canvas at full resolution
4. Both canvases update via React refs (no re-render, direct canvas writes)
5. Result canvas is inside a div with CSS checkerboard background

---

## Download Filename Convention

Format: `{originalName}_{shape}_{grid}_s{size}_sp{spacing}.png`

Examples:
- `shirt_circle_square_s40_sp90.png`
- `photo_triangle_triangular_s35_sp80.png`  
- `shirt_mask_only_hexagon_square_s40_sp90.png` (when Mask Only is checked)

---

## Performance Considerations

- Large images (e.g. 4000×5000px): mask generation is O(width × height / spacing²) which is fast
- `applyMaskToImage` pixel loop is O(width × height) — for very large images this runs on the main thread; acceptable for this tool but noted
- Preview is always rendered at ≤600px wide for speed; download uses full resolution
- Debounce on param changes prevents thrashing

---

## Implementation Steps

1. **Scaffold** — `npm create vite@latest web -- --template react`, install Tailwind, configure
2. **`maskEngine.js`** — port all geometry functions from `mask.py`, unit-testable pure functions
3. **`useMaskProcessor.js`** — hook that takes params + source image → mask canvas + result canvas
4. **`ImageDropzone.jsx`** — drag-and-drop zone + click-to-upload, shows filename + dimensions
5. **`ParamControls.jsx`** — all controls, emits param object on any change
6. **`MaskPreview.jsx`** — `<canvas>` that receives mask canvas data
7. **`ResultPreview.jsx`** — `<canvas>` on checkerboard background, context menu works natively
8. **`DownloadButton.jsx`** — `canvas.toBlob` → anchor click with computed filename
9. **`App.jsx`** — wires everything together, Tailwind mobile-first layout
10. **Polish** — loading state, empty states, error messages, responsive tweaks

---

## Out of Scope

- Mode B (external mask upload) — excluded per user preference
- Server-side processing
- Authentication / persistence
- Undo/redo history
