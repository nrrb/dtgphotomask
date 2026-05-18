import { forwardRef } from 'react';

export const MaskPreview = forwardRef(function MaskPreview({ isEmpty }, ref) {
  return (
    <div className="relative rounded-xl overflow-hidden bg-gray-100 border border-gray-200 min-h-[120px]">
      {/* Canvas is always mounted so the ref is always valid and we can draw to it */}
      <canvas ref={ref} className="block w-full h-auto" />
      {isEmpty && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-sm text-gray-400 text-center px-4">
            Adjust parameters to see a live mask preview
          </p>
        </div>
      )}
    </div>
  );
});
