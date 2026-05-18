import { useState, useRef, useCallback } from 'react';
import { ImageDropzone } from './components/ImageDropzone';
import { ParamControls } from './components/ParamControls';
import { MaskPreview } from './components/MaskPreview';
import { ResultPreview } from './components/ResultPreview';
import { DownloadButton } from './components/DownloadButton';
import { useMaskProcessor } from './lib/useMaskProcessor';
import { buildFilename } from './lib/maskEngine';

const DEFAULT_PARAMS = {
  gridType: 'square',
  shape: 'square',
  size: 12,
  spacing: 28,
  offset: [0, 0],
  triOrientation: 'alternating',
  triRotDeg: 0,
};

export default function App() {
  const [params, setParams] = useState(DEFAULT_PARAMS);
  const [sourceImg, setSourceImg] = useState(null);
  const [sourceName, setSourceName] = useState('');
  const [maskOnly, setMaskOnly] = useState(false);
  const [canvases, setCanvases] = useState({ maskCanvas: null, resultCanvas: null });

  const maskCanvasRef = useRef(null);
  const resultCanvasRef = useRef(null);

  const onDone = useCallback((c) => setCanvases(c), []);

  useMaskProcessor(params, sourceImg, maskOnly, maskCanvasRef, resultCanvasRef, onDone);

  function handleImage(img, name) {
    setSourceImg(img);
    setSourceName(name);
  }

  // Mask preview always renders (uses 800×600 default when no image loaded)
  const hasMask = !!canvases.maskCanvas;
  const hasResult = !maskOnly && !!canvases.resultCanvas;
  const downloadCanvas = maskOnly ? canvases.maskCanvas : canvases.resultCanvas;
  const filename = buildFilename(sourceName, params, maskOnly);

  function getDownloadCanvas() { return downloadCanvas; }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="3" strokeWidth={2} />
              <circle cx="6" cy="6" r="2" strokeWidth={2} />
              <circle cx="18" cy="6" r="2" strokeWidth={2} />
              <circle cx="6" cy="18" r="2" strokeWidth={2} />
              <circle cx="18" cy="18" r="2" strokeWidth={2} />
            </svg>
          </div>
          <h1 className="text-lg font-bold tracking-tight">dtg photomask</h1>
          <span className="text-xs text-gray-400 ml-auto">client-side · no upload</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex flex-col lg:flex-row gap-6">

          {/* LEFT: controls */}
          <div className="flex flex-col gap-5 lg:w-80 flex-shrink-0">
            <section className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Source Image
              </h2>
              {maskOnly ? (
                <div className="text-sm text-gray-400 text-center py-4 border-2 border-dashed border-gray-200 rounded-xl">
                  Not needed in Mask Only mode
                </div>
              ) : (
                <ImageDropzone onImage={handleImage} />
              )}
            </section>

            <section className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Mask Parameters
              </h2>
              <ParamControls
                params={params}
                onChange={setParams}
                maskOnly={maskOnly}
                onMaskOnlyChange={setMaskOnly}
              />
            </section>
          </div>

          {/* RIGHT: previews */}
          <div className="flex flex-col gap-5 flex-1 min-w-0">
            <section className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Mask Preview
              </h2>
              <MaskPreview ref={maskCanvasRef} isEmpty={!hasMask} />
              {hasMask && maskOnly && (
                <div className="mt-4 flex flex-col gap-2">
                  <DownloadButton
                    getCanvas={getDownloadCanvas}
                    filename={filename}
                    disabled={!downloadCanvas}
                  />
                  <p className="text-xs text-gray-400 text-center">
                    You can also right-click the preview above and save
                  </p>
                </div>
              )}
            </section>

            {!maskOnly && (
              <section className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  Result
                  {hasResult && (
                    <span className="text-gray-400 font-normal normal-case">
                      · right-click to save
                    </span>
                  )}
                </h2>
                <ResultPreview ref={resultCanvasRef} isEmpty={!hasResult} maskOnly={maskOnly} />
                {hasResult && (
                  <div className="mt-4">
                    <DownloadButton
                      getCanvas={getDownloadCanvas}
                      filename={filename}
                      disabled={!downloadCanvas}
                    />
                  </div>
                )}
              </section>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
