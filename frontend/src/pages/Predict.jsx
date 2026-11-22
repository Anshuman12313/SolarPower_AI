import { useState } from "react";
import { api } from "../api";
import InputControls, { defaultsFrom } from "../components/InputControls.jsx";
import { Card, ErrorBox, fmt } from "../components/ui.jsx";

export default function Predict({ features, model, info }) {
  const [inputs, setInputs] = useState(defaultsFrom(features));
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true); setError(null);
    try {
      setResult(await api.post("/predict", { model, inputs }));
    } catch (e) {
      setError(e.message); setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const capacity = info.panel_capacity_kw;
  return (
    <div>
      <h2>Power output prediction</h2>
      <div className="two-col">
        <Card title="Weather conditions">
          <InputControls features={features} values={inputs} onChange={setInputs} />
          <button className="primary" onClick={submit} disabled={busy}>{busy ? "Predicting..." : "Predict solar output"}</button>
        </Card>
        <div>
          {error && <ErrorBox message={error} />}
          {result && (
            <Card title={`Prediction (${result.model_name})`}>
              <p className="huge">{fmt(result.prediction_kw, 2)} <span>kW</span></p>
              {capacity && (
                <>
                  <div className="bar"><div style={{ width: `${Math.min(100, (result.prediction_kw / capacity) * 100)}%` }} /></div>
                  <p className="muted">{fmt((result.prediction_kw / capacity) * 100, 0)}% of the {capacity} kW system capacity</p>
                </>
              )}
              {result.warnings.map((w) => <div className="warnbox" key={w}>⚠ {w}</div>)}
            </Card>
          )}
          {!result && !error && <Card><p className="muted">Set the conditions and press <b>Predict</b>. Change the active model in the sidebar.</p></Card>}
        </div>
      </div>
    </div>
  );
}
