import { forwardRef } from 'react';

export const ResultPreview = forwardRef(function ResultPreview({ isEmpty, maskOnly }, ref) {
  const emptyMsg = maskOnly
    ? 'Mask preview will appear above'
    : 'Upload an image to see the result';

  return (
    <div className="relative rounded-xl overflow-hidden border border-gray-200 checkerboard min-h-[120px]">
      {/* Canvas is always mounted so the ref is always valid */}
      <canvas ref={ref} className="block w-full h-auto" />
      {isEmpty && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-sm text-gray-400 bg-white/80 px-3 py-2 rounded-lg text-center">
            {emptyMsg}
          </p>
        </div>
      )}
    </div>
  );
});
