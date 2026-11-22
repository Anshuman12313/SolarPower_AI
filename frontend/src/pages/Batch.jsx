import { useState } from "react";
import { api } from "../api";
import { Card, ErrorBox } from "../components/ui.jsx";

const toCsv = (rows) => {
  const cols = Object.keys(rows[0]);
  return [cols.join(","), ...rows.map((r) => cols.map((c) => r[c] ?? "").join(","))].join("\n");
};
const download = (name, text) => {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
};

export default function Batch({ model, features }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const cols = features.map((f) => f.key);

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true); setError(null); setRows(null);
    const form = new FormData();
    form.append("model", model);
    form.append("file", file);
    try {
      setRows((await api.upload("/predict-batch", form)).rows);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  return (
    <div>
      <h2>Batch prediction</h2>
      <Card title="Upload a CSV">
        <p>Your file needs these columns: <code>{cols.join(", ")}</code>. Up to 5000 rows are processed.</p>
        <button onClick={() => download("template.csv", `${cols.join(",")}\n800,30,40,3,10,12\n0,22,60,1,0,2`)}>Download template</button>{" "}
        <input type="file" accept=".csv" onChange={upload} disabled={busy} />
        {busy && <p className="muted">Predicting...</p>}
      </Card>
      {error && <ErrorBox message={error} />}
      {rows && (
        <Card title={`Results (${rows.length} rows)`}>
          <button className="primary" onClick={() => download("predictions.csv", toCsv(rows))}>Download predictions</button>
          <div className="scroll">
            <table>
              <thead><tr>{Object.keys(rows[0]).map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>{rows.slice(0, 20).map((r, i) => <tr key={i}>{Object.values(r).map((v, j) => <td key={j}>{String(v ?? "")}</td>)}</tr>)}</tbody>
            </table>
          </div>
          {rows.length > 20 && <p className="muted">Showing the first 20 rows. Download the CSV for all of them.</p>}
        </Card>
      )}
    </div>
  );
}
