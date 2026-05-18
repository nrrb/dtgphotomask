export function DownloadButton({ getCanvas, filename, disabled }) {
  function handleDownload() {
    const canvas = getCanvas();
    if (!canvas) return;
    canvas.toBlob(blob => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    }, 'image/png');
  }

  return (
    <button
      onClick={handleDownload}
      disabled={disabled}
      className={`
        flex items-center justify-center gap-2 w-full rounded-xl py-3 px-4
        text-sm font-semibold transition-colors
        ${disabled
          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
          : 'bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white cursor-pointer'
        }
      `}
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      {disabled ? 'Processing…' : `Download ${filename}`}
    </button>
  );
}
