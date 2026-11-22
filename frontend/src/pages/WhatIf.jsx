import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import InputControls, { defaultsFrom } from "../components/InputControls.jsx";
import { Card, ErrorBox, fmt } from "../components/ui.jsx";

const PRESETS = [
  ["Your inputs", {}],
  ["Clear sky", { cloud_cover: 0, irradiance: 900 }],
  ["Overcast", { cloud_cover: 90, irradiance: 200 }],
  ["Heat wave (45 °C)", { temperature: 45 }],
  ["Windy (12 m/s)", { wind_speed: 12 }],
];

export default function WhatIf({ features, model }) {
  const [base, setBase] = useState({ ...defaultsFrom(features), irradiance: 700, hour: 12 });
  const [variable, setVariable] = useState("irradiance");
  const [sweep, setSweep] = useState(null);
  const [scen, setScen] = useState([]);
  const [error, setError] = useState(null);

  // Re-run the analysis shortly after the user stops moving a slider.
  useEffect(() => {
    if (Object.values(base).some((v) => v === "")) return;
    const timer = setTimeout(async () => {
      try {
        const [s, sc] = await Promise.all([
          api.post("/whatif", { model, base, variable }),
          api.post("/scenarios", { model, scenarios: PRESETS.map(([name, o]) => ({ name, inputs: { ...base, ...o } })) }),
        ]);
        setSweep(s); setScen(sc); setError(null);
      } catch (e) {
        setError(e.message);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [base, variable, model]);

  const info = features.find((f) => f.key === variable);
  const data = sweep ? sweep.values.map((v, i) => ({ x: v, kw: sweep.predictions_kw[i] })) : [];
  return (
    <div>
      <h2>What-if analysis</h2>
      <div className="two-col">
        <Card title="Current conditions"><InputControls features={features} values={base} onChange={setBase} /></Card>
        <div>
          {error && <ErrorBox message={error} />}
          <Card title="Sweep one variable">
            <label>Vary: <select value={variable} onChange={(e) => setVariable(e.target.value)}>
              {features.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}</select></label>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data} margin={{ top: 10, left: 0, bottom: 15 }}><CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]} label={{ value: `${info.label} (${info.unit})`, position: "insideBottom", offset: -8 }} />
                <YAxis unit=" kW" /><Tooltip formatter={(v) => `${fmt(v, 2)} kW`} />
                <Line dataKey="kw" stroke="#ea580c" strokeWidth={2} dot={false} />
                {sweep && <ReferenceDot x={sweep.current_value} y={sweep.current_prediction_kw} r={6} fill="#2563eb" stroke="white" />}</LineChart>
            </ResponsiveContainer>
            <p className="muted">Blue dot = your current setting ({sweep ? fmt(sweep.current_prediction_kw, 2) : "-"} kW). All other inputs stay fixed.</p>
          </Card>
        </div>
      </div>
      <Card title="Scenario comparison (applied on top of your inputs)">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={scen}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis unit=" kW" /><Tooltip formatter={(v) => `${fmt(v, 2)} kW`} />
            <Bar dataKey="prediction_kw" name="Predicted kW" fill="#f59e0b" /></BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
