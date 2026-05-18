import { useEffect, useRef, useCallback } from 'react';
import { generateTilingMask, applyMaskToImage } from './maskEngine';

/**
 * Debounced hook that renders mask + result canvases whenever params or source change.
 * Mask preview always renders (falls back to 800×600 if no source image).
 */
export function useMaskProcessor(params, sourceImg, maskOnly, maskCanvasRef, resultCanvasRef, onDone) {
  const timerRef = useRef(null);
  const offscreenMask = useRef(document.createElement('canvas'));
  const offscreenSource = useRef(document.createElement('canvas'));

  const process = useCallback(() => {
    const { size, spacing } = params;
    if (size <= 0 || spacing <= 1) return;

    // Canvas dimensions: use source image if available, else default
    const w = sourceImg ? (sourceImg.naturalWidth || sourceImg.width) : 800;
    const h = sourceImg ? (sourceImg.naturalHeight || sourceImg.height) : 600;

    // Generate full-res mask
    generateTilingMask(offscreenMask.current, { ...params, width: w, height: h });

    // Render mask preview (scaled to fit preview column)
    if (maskCanvasRef.current) {
      const el = maskCanvasRef.current;
      const maxW = el.parentElement?.clientWidth || 600; // 600 fallback when canvas is hidden
      const scale = Math.min(1, maxW / w);
      const pw = Math.max(1, Math.round(w * scale));
      const ph = Math.max(1, Math.round(h * scale));
      el.width = pw;
      el.height = ph;
      el.getContext('2d').drawImage(offscreenMask.current, 0, 0, pw, ph);
    }

    if (maskOnly || !sourceImg) {
      onDone?.({ maskCanvas: offscreenMask.current, resultCanvas: null });
      return;
    }

    // Draw source to offscreen canvas
    offscreenSource.current.width = w;
    offscreenSource.current.height = h;
    offscreenSource.current.getContext('2d').drawImage(sourceImg, 0, 0);

    // Apply mask → result
    const resultCanvas = applyMaskToImage(offscreenSource.current, offscreenMask.current);

    // Render result preview
    if (resultCanvasRef.current) {
      const el = resultCanvasRef.current;
      const maxW = el.parentElement?.clientWidth || 600; // 600 fallback when canvas is hidden
      const scale = Math.min(1, maxW / w);
      const pw = Math.max(1, Math.round(w * scale));
      const ph = Math.max(1, Math.round(h * scale));
      el.width = pw;
      el.height = ph;
      el.getContext('2d').drawImage(resultCanvas, 0, 0, pw, ph);
    }

    onDone?.({ maskCanvas: offscreenMask.current, resultCanvas });
  }, [params, sourceImg, maskOnly, maskCanvasRef, resultCanvasRef, onDone]);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(process, 200);
    return () => clearTimeout(timerRef.current);
  }, [process]);
}
