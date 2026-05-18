// Port of mask.py geometry to Canvas 2D API.

const DEG = Math.PI / 180;

function regularPolygonVertices(cx, cy, r, n, rotDeg = 0) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const angle = (rotDeg + (i * 360) / n) * DEG;
    pts.push([cx + r * Math.cos(angle), cy + r * Math.sin(angle)]);
  }
  return pts;
}

function star5Vertices(cx, cy, outerR, innerR) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const angle = (-90 + i * 36) * DEG;
    const r = i % 2 === 0 ? outerR : innerR;
    pts.push([cx + r * Math.cos(angle), cy + r * Math.sin(angle)]);
  }
  return pts;
}

function triangleVertices(cx, cy, r, pointUp = true) {
  return regularPolygonVertices(cx, cy, r, 3, pointUp ? -90 : 90);
}

function squareVertices(cx, cy, halfW, rotDeg = 0) {
  return regularPolygonVertices(cx, cy, halfW * Math.SQRT2, 4, rotDeg + 45);
}

function hexagonVertices(cx, cy, r, rotDeg = 0) {
  return regularPolygonVertices(cx, cy, r, 6, rotDeg);
}

function* squareGridCenters(width, height, spacing, offset = [0, 0]) {
  const [ox, oy] = offset;
  const cols = Math.ceil(width / spacing) + 2;
  const rows = Math.ceil(height / spacing) + 2;
  const startX = (ox % spacing) - spacing;
  const startY = (oy % spacing) - spacing;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      yield [col, row, startX + col * spacing, startY + row * spacing];
    }
  }
}

function* triangularGridCenters(width, height, spacing, offset = [0, 0]) {
  const [ox, oy] = offset;
  const rowH = spacing * Math.sqrt(3) / 2;
  const cols = Math.ceil(width / spacing) + 3;
  const rows = Math.ceil(height / rowH) + 3;
  const startX = (ox % spacing) - spacing;
  const startY = (oy % rowH) - rowH;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const cx = startX + col * spacing + (row % 2 === 1 ? spacing / 2 : 0);
      const cy = startY + row * rowH;
      yield [col, row, cx, cy];
    }
  }
}

function drawPolygon(ctx, pts) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.fill();
}

function drawAperture(ctx, shape, col, _row, cx, cy, size, triOrientation, triRotDeg) {
  switch (shape) {
    case 'circle':
      ctx.beginPath();
      ctx.arc(cx, cy, size, 0, Math.PI * 2);
      ctx.fill();
      break;
    case 'square':
      drawPolygon(ctx, squareVertices(cx, cy, size));
      break;
    case 'hexagon':
      drawPolygon(ctx, hexagonVertices(cx, cy, size));
      break;
    case 'star5':
      drawPolygon(ctx, star5Vertices(cx, cy, size, size * 0.382));
      break;
    case 'triangle':
      if (triOrientation === 'fixed') {
        drawPolygon(ctx, regularPolygonVertices(cx, cy, size, 3, triRotDeg - 90));
      } else {
        drawPolygon(ctx, triangleVertices(cx, cy, size, col % 2 === 0));
      }
      break;
  }
}

/**
 * Renders a tiling mask to the given canvas.
 * White = keep, Black = transparent (same convention as mask.py).
 */
export function generateTilingMask(canvas, { width, height, gridType, shape, size, spacing, offset, triOrientation, triRotDeg }) {
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = '#fff';

  const effectiveGrid = shape === 'triangle' ? 'triangular' : gridType;
  const centers = effectiveGrid === 'square'
    ? squareGridCenters(width, height, spacing, offset)
    : triangularGridCenters(width, height, spacing, offset);

  for (const [col, row, cx, cy] of centers) {
    drawAperture(ctx, shape, col, row, cx, cy, size, triOrientation, triRotDeg);
  }
}

/**
 * Applies a mask canvas (white=keep) to a source ImageBitmap/HTMLImageElement.
 * Returns a new canvas with RGBA output (transparent where mask is black).
 */
export function applyMaskToImage(sourceCanvas, maskCanvas) {
  const w = sourceCanvas.width;
  const h = sourceCanvas.height;

  const out = document.createElement('canvas');
  out.width = w;
  out.height = h;
  const ctx = out.getContext('2d');

  // Draw source
  ctx.drawImage(sourceCanvas, 0, 0);
  const imgData = ctx.getImageData(0, 0, w, h);

  // Sample mask (resize if needed)
  const mw = maskCanvas.width;
  const mh = maskCanvas.height;
  let maskData;
  if (mw === w && mh === h) {
    maskData = maskCanvas.getContext('2d').getImageData(0, 0, w, h);
  } else {
    const tmp = document.createElement('canvas');
    tmp.width = w;
    tmp.height = h;
    const tctx = tmp.getContext('2d');
    tctx.drawImage(maskCanvas, 0, 0, w, h);
    maskData = tctx.getImageData(0, 0, w, h);
  }

  // Set alpha from mask red channel
  const d = imgData.data;
  const m = maskData.data;
  for (let i = 0; i < d.length; i += 4) {
    d[i + 3] = m[i]; // mask R channel → alpha
  }

  ctx.putImageData(imgData, 0, 0);
  return out;
}

/**
 * Builds the output filename from original name + params.
 */
export function buildFilename(originalName, params, maskOnly) {
  const base = originalName ? originalName.replace(/\.[^.]+$/, '') : 'image';
  const prefix = maskOnly ? `${base}_mask_only` : base;
  return `${prefix}_${params.shape}_${params.gridType}_s${params.size}_sp${params.spacing}.png`;
}
