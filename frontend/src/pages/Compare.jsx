import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Async, Card, fmt, useApi } from "../components/ui.jsx";

export default function Compare({ metrics, model, models }) {
  const rows = metrics.models;
  const label = models.find((m) => m.key === model)?.name;
  const avp = useApi(`/actual-vs-predicted?model=${model}`);
  return (
    <div>
      <h2>Model comparison</h2>
      <Card title="Test-set metrics">
        <p className="muted">
          Test data = the newest {metrics.split.test_rows} hours (from {metrics.split.test_start}). Lower is better for
          MAE, MSE and RMSE; higher is better for R². The baseline always predicts the training average.
        </p>
        <table>
          <thead><tr><th>Model</th><th>MAE</th><th>MSE</th><th>RMSE</th><th>R²</th><th>CV RMSE</th><th>Train time (s)</th></tr></thead>
          <tbody>
            <tr className="muted"><td>Baseline (mean)</td><td>{fmt(metrics.baseline.mae)}</td><td>{fmt(metrics.baseline.mse)}</td><td>{fmt(metrics.baseline.rmse)}</td><td>{fmt(metrics.baseline.r2)}</td><td>-</td><td>-</td></tr>
            {rows.map((r) => (
              <tr key={r.key} className={r.key === metrics.best_model ? "best" : ""}>
                <td>{r.name}{r.key === metrics.best_model && " ★"}</td>
                <td>{fmt(r.mae)}</td><td>{fmt(r.mse)}</td><td>{fmt(r.rmse)}</td><td>{fmt(r.r2, 4)}</td>
                <td>{fmt(r.cv_rmse)}</td><td>{r.train_seconds}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">CV RMSE = average error across 3 time-ordered validation folds inside the training data (used to pick hyper-parameters).</p>
      </Card>

      <div className="two-col">
        <Card title="Error comparison (lower is better)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rows}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip /><Legend />
              <Bar dataKey="mae" name="MAE" fill="#f59e0b" /><Bar dataKey="rmse" name="RMSE" fill="#ef4444" /></BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="R² score (higher is better)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rows}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis domain={[0.9, 1]} /><Tooltip /><Bar dataKey="r2" name="R²" fill="#10b981" /></BarChart>
          </ResponsiveContainer>
          <p className="muted">Axis starts at 0.9 so small differences are visible.</p>
        </Card>
      </div>

      <Card title={`Actual vs predicted: ${label} (test set sample)`}>
        <Async state={avp}>
          {(d) => {
            const data = d.actual.map((a, i) => ({ i, actual: a, predicted: d.predicted[i], time: d.timestamps[i] }));
            return (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="i" hide /><YAxis unit=" kW" /><Tooltip labelFormatter={(i) => data[i]?.time} /><Legend />
                  <Line dataKey="actual" stroke="#2563eb" dot={false} name="Actual" /><Line dataKey="predicted" stroke="#f97316" dot={false} name="Predicted" /></LineChart>
              </ResponsiveContainer>
            );
          }}
        </Async>
      </Card>
    </div>
  );
}
