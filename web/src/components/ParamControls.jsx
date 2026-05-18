const GRIDS = [
  { value: 'square', label: 'Square' },
  { value: 'triangular', label: 'Triangular' },
];

const SHAPES = [
  { value: 'circle', label: 'Circle' },
  { value: 'square', label: 'Square' },
  { value: 'triangle', label: 'Triangle' },
  { value: 'hexagon', label: 'Hexagon' },
  { value: 'star5', label: 'Star 5pt' },
];

const TRI_ORIENTATIONS = [
  { value: 'alternating', label: 'Alternating' },
  { value: 'fixed', label: 'Fixed' },
];

function Field({ label, children }) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-24 text-right text-sm text-gray-500 flex-shrink-0">{label}</label>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function Select({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

function NumberInput({ value, onChange, min, step = 1 }) {
  function clamp(v) {
    return min !== undefined ? Math.max(min, v) : v;
  }
  // Round to avoid floating-point display noise
  function fmt(v) {
    return Number.isInteger(step) ? Math.round(v) : parseFloat(v.toFixed(2));
  }
  return (
    <div className="flex rounded-lg border border-gray-300 bg-white overflow-hidden focus-within:ring-2 focus-within:ring-indigo-400">
      <button
        type="button"
        onClick={() => onChange(fmt(clamp(value - step)))}
        className="px-3 py-2 text-gray-500 hover:bg-gray-100 active:bg-gray-200 text-base leading-none select-none flex-shrink-0 border-r border-gray-200"
        aria-label="Decrease"
      >−</button>
      <input
        type="number"
        value={value}
        min={min}
        step={step}
        onChange={e => {
          const v = parseFloat(e.target.value);
          if (!isNaN(v)) onChange(clamp(v));
        }}
        className="w-full text-center text-sm py-2 bg-transparent focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
      />
      <button
        type="button"
        onClick={() => onChange(fmt(value + step))}
        className="px-3 py-2 text-gray-500 hover:bg-gray-100 active:bg-gray-200 text-base leading-none select-none flex-shrink-0 border-l border-gray-200"
        aria-label="Increase"
      >+</button>
    </div>
  );
}

export function ParamControls({ params, onChange, maskOnly, onMaskOnlyChange }) {
  function set(key, value) {
    onChange({ ...params, [key]: value });
  }

  const isTri = params.shape === 'triangle';

  return (
    <div className="flex flex-col gap-3">
      <Field label="Grid">
        <Select value={params.gridType} onChange={v => set('gridType', v)} options={GRIDS} />
      </Field>

      <Field label="Shape">
        <Select value={params.shape} onChange={v => set('shape', v)} options={SHAPES} />
      </Field>

      <Field label="Size">
        <NumberInput value={params.size} onChange={v => set('size', v)} min={1} step={0.5} />
      </Field>

      <Field label="Spacing">
        <NumberInput value={params.spacing} onChange={v => set('spacing', v)} min={2} step={0.5} />
      </Field>

      <Field label="Offset X">
        <NumberInput value={params.offset[0]} onChange={v => set('offset', [v, params.offset[1]])} min={0} step={1} />
      </Field>

      <Field label="Offset Y">
        <NumberInput value={params.offset[1]} onChange={v => set('offset', [params.offset[0], v])} min={0} step={1} />
      </Field>

      {isTri && (
        <Field label="Tri orient">
          <Select value={params.triOrientation} onChange={v => set('triOrientation', v)} options={TRI_ORIENTATIONS} />
        </Field>
      )}

      {isTri && params.triOrientation === 'fixed' && (
        <Field label="Tri rot°">
          <NumberInput value={params.triRotDeg} onChange={v => set('triRotDeg', v)} min={0} step={1} />
        </Field>
      )}

      <div className="flex items-center gap-3 pt-1">
        <span className="w-24 flex-shrink-0" />
        <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-600">
          <input
            type="checkbox"
            checked={maskOnly}
            onChange={e => onMaskOnlyChange(e.target.checked)}
            className="w-4 h-4 rounded accent-indigo-500"
          />
          Mask Only
          <span className="text-gray-400 text-xs">(no source image needed)</span>
        </label>
      </div>
    </div>
  );
}
