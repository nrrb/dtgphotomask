import { useRef, useState } from 'react';

export function ImageDropzone({ onImage }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [info, setInfo] = useState(null);

  function loadFile(file) {
    if (!file || !file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setInfo({ name: file.name, w: img.naturalWidth, h: img.naturalHeight });
      onImage(img, file.name);
    };
    img.src = url;
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    loadFile(e.dataTransfer.files[0]);
  }

  function onDragOver(e) { e.preventDefault(); setDragging(true); }
  function onDragLeave() { setDragging(false); }
  function onFileChange(e) { loadFile(e.target.files[0]); }

  return (
    <div
      onClick={() => inputRef.current.click()}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      className={`
        relative flex flex-col items-center justify-center gap-2
        min-h-[120px] rounded-xl border-2 border-dashed cursor-pointer
        transition-colors select-none
        ${dragging
          ? 'border-indigo-500 bg-indigo-50'
          : 'border-gray-300 bg-gray-50 hover:border-indigo-400 hover:bg-indigo-50'
        }
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={onFileChange}
      />
      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M3 16.5V19a2 2 0 002 2h14a2 2 0 002-2v-2.5M16 10l-4-4m0 0L8 10m4-4v12" />
      </svg>
      {info ? (
        <div className="text-center">
          <p className="text-sm font-medium text-gray-700 truncate max-w-[260px]">{info.name}</p>
          <p className="text-xs text-gray-400">{info.w} × {info.h}px</p>
          <p className="text-xs text-indigo-500 mt-1">tap to change</p>
        </div>
      ) : (
        <div className="text-center px-4">
          <p className="text-sm font-medium text-gray-600">Drop image here or tap to upload</p>
          <p className="text-xs text-gray-400 mt-0.5">Any size — PNG, JPG, WEBP…</p>
        </div>
      )}
    </div>
  );
}
