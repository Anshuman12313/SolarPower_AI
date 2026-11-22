import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Async, Card, useApi } from "../components/ui.jsx";

const toRows = (obj) => Object.entries(obj).map(([name, value]) => ({ name, value: Number(value.toFixed(4)) })).sort((a, b) => b.value - a.value);

function Chart({ rows, color }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows} layout="vertical" margin={{ left: 30 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="name" width={90} /><Tooltip /><Bar dataKey="value" fill={color} /></BarChart>
    </ResponsiveContainer>
  );
}

export default function Explain({ model, models, features }) {
  const state = useApi("/importance");
  const label = models.find((m) => m.key === model)?.name;
  return (
    <div>
      <h2>Model explanation: {label}</h2>
      <Async state={state}>
        {(all) => {
          const imp = all[model];
          return (
            <>
              <div className="two-col">
                <Card title="Built-in feature importance (tree models)">
                  {imp.builtin ? <Chart rows={toRows(imp.builtin)} color="#ea580c" /> : <p className="muted">Linear Regression has no tree importance. Choose a tree-based model in the sidebar.</p>}
                  <p className="muted">How much each feature reduced prediction error inside the trees. Values add up to 1.</p>
                </Card>
                <Card title="Permutation importance (all models)">
                  <Chart rows={toRows(imp.permutation)} color="#2563eb" />
                  <p className="muted">Drop in R² on the test set when one feature is shuffled. Bigger drop = the model relies on it more.</p>
                </Card>
              </div>
              <Card title="How to read this">
                <ul>
                  <li><b>Irradiance</b> dominates: output is basically sunlight times panel efficiency.</li>
                  <li><b>Hour</b> also matters because it tells the model whether the sun is up.</li>
                  <li><b>Cloud cover</b> looks small because its effect already flows through irradiance (the two are correlated). Importance scores of correlated features can hide each other.</li>
                  <li><b>Temperature, humidity and wind</b> have small effects, because they only adjust efficiency by a few percent. A small score does not mean they are physically irrelevant.</li>
                </ul>
                <p className="muted">These results describe what the model learned from this dataset. On synthetic data they reflect the formulas used to generate it.</p>
              </Card>
              <Card title="Feature glossary">
                <ul>{features.map((f) => <li key={f.key}><b>{f.label}</b> ({f.unit}): {f.description}</li>)}</ul>
              </Card>
            </>
          );
        }}
      </Async>
    </div>
  );
}
