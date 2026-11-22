import { useEffect, useState } from "react";
import { api } from "./api";
import { ErrorBox, Loading } from "./components/ui.jsx";
import Home from "./pages/Home.jsx";
import Predict from "./pages/Predict.jsx";
import Compare from "./pages/Compare.jsx";
import Visualize from "./pages/Visualize.jsx";
import WhatIf from "./pages/WhatIf.jsx";
import Explain from "./pages/Explain.jsx";
import Batch from "./pages/Batch.jsx";

const PAGES = [
  ["home", "🏠 Home", Home],
  ["predict", "⚡ Prediction", Predict],
  ["compare", "📊 Model comparison", Compare],
  ["viz", "📈 Data visualization", Visualize],
  ["whatif", "🔀 What-if analysis", WhatIf],
  ["explain", "🧠 Model explanation", Explain],
  ["batch", "📁 Batch prediction", Batch],
];

export default function App() {
  const [page, setPage] = useState("home");
  const [model, setModel] = useState("");
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.get("/features"), api.get("/models"), api.get("/metrics"), api.get("/dataset-info")])
      .then(([features, models, metrics, info]) => {
        setMeta({ features, models: models.models, metrics, info });
        setModel(models.best_model);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error)
    return (
      <div className="center">
        <ErrorBox message={error} />
        <p className="muted">
          Make sure you ran <code>python train_model.py</code> and started the backend on port 8000.
        </p>
      </div>
    );
  if (!meta) return <div className="center"><Loading text="Connecting to the SolarPower AI backend..." /></div>;

  const Page = PAGES.find((p) => p[0] === page)[2];
  const synthetic = meta.info.is_synthetic;
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>☀ SolarPower AI</h1>
        <nav>
          {PAGES.map(([key, label]) => (
            <button key={key} className={page === key ? "active" : ""} onClick={() => setPage(key)}>
              {label}
            </button>
          ))}
        </nav>
        <label className="model-select">
          Active model
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {meta.models.map((m) => (
              <option key={m.key} value={m.key}>
                {m.name}{m.key === meta.metrics.best_model ? " ★ best" : ""}
              </option>
            ))}
          </select>
        </label>
      </aside>
      <main>

        <Page {...meta} model={model} setModel={setModel} />
      </main>
    </div>
  );
}
