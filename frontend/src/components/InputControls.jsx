// One slider + number box per feature. `values` is an object keyed by feature name.
export default function InputControls({ features, values, onChange }) {
  const set = (key, raw) => onChange({ ...values, [key]: raw === "" ? "" : Number(raw) });
  return (
    <div className="controls">
      {features.map((f) => (
        <div className="control" key={f.key}>
          <label htmlFor={f.key}>
            {f.label} <span className="muted">({f.unit})</span>
          </label>
          <div className="control-row">
            <input
              type="range" min={f.min} max={f.max} step={f.step}
              value={values[f.key] === "" ? f.min : values[f.key]}
              onChange={(e) => set(f.key, e.target.value)}
            />
            <input
              id={f.key} type="number" min={f.min} max={f.max} step={f.step}
              value={values[f.key]} onChange={(e) => set(f.key, e.target.value)}
            />
          </div>
          <small className="muted">{f.description}</small>
        </div>
      ))}
    </div>
  );
}

export const defaultsFrom = (features) => Object.fromEntries(features.map((f) => [f.key, f.default]));
