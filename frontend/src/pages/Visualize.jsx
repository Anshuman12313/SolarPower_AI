import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { Async, Card, useApi } from "../components/ui.jsx";

const TABS = [["irradiance", "Irradiance vs power"], ["temperature", "Temperature vs power"], ["hourly", "Hourly pattern"], ["corr", "Correlation heatmap"]];

function ScatterView({ x, unit }) {
  const state = useApi(`/viz/scatter?x=${x}`);
  return (
    <Async state={state}>
      {(d) => (
        <>
          <ResponsiveContainer width="100%" height={380}>
            <ScatterChart margin={{ left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="x" name={x} unit={unit} label={{ value: `${x} (${unit})`, position: "insideBottom", offset: -10 }} domain={["auto", "auto"]} />
              <YAxis type="number" dataKey="y" name="power" unit=" kW" />
              <ZAxis range={[18, 18]} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Scatter data={d.points} fill="#f59e0b" fillOpacity={0.45} />
            </ScatterChart>
          </ResponsiveContainer>
          <p className="muted">
            {x === "irradiance"
              ? "Output rises almost linearly with irradiance. The spread comes from temperature, wind and noise."
              : "Only daytime hours (irradiance above 50 W/m²) are shown. Temperature mostly follows the sun, so the relationship is indirect: hot panels lose about 0.4% per °C."}
          </p>
        </>
      )}
    </Async>
  );
}

function Hourly() {
  const state = useApi("/viz/hourly");
  return (
    <Async state={state}>
      {(d) => (
        <>
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={d.rows}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hour" /><YAxis unit=" kW" /><Tooltip /><Legend />
              <Line dataKey="p90" name="90th percentile" stroke="#fdba74" dot={false} />
              <Line dataKey="mean" name="Average" stroke="#ea580c" strokeWidth={3} dot={false} />
              <Line dataKey="p10" name="10th percentile" stroke="#fdba74" dot={false} /></LineChart>
          </ResponsiveContainer>
          <p className="muted">Generation is zero at night and peaks around midday. The band shows how much clouds change output.</p>
        </>
      )}
    </Async>
  );
}

function Heatmap() {
  const state = useApi("/viz/correlation");
  const color = (v) => (v >= 0 ? `rgba(234,88,12,${Math.abs(v)})` : `rgba(37,99,235,${Math.abs(v)})`);
  return (
    <Async state={state}>
      {(d) => (
        <>
          <div className="scroll">
            <table className="heat">
              <thead><tr><th />{d.labels.map((l) => <th key={l}>{l}</th>)}</tr></thead>
              <tbody>
                {d.labels.map((row, i) => (
                  <tr key={row}><th>{row}</th>
                    {d.matrix[i].map((v, j) => <td key={j} style={{ background: color(v), color: Math.abs(v) > 0.5 ? "#fff" : "#111" }}>{v.toFixed(2)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">Orange = positive correlation, blue = negative. Correlation measures linear relationships only; irradiance and cloud cover are strongly linked to each other.</p>
        </>
      )}
    </Async>
  );
}

export default function Visualize() {
  const [tab, setTab] = useState("irradiance");
  return (
    <div>
      <h2>Data visualization</h2>
      <div className="tabs">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      <Card>
        {tab === "irradiance" && <ScatterView x="irradiance" unit="W/m²" />}
        {tab === "temperature" && <ScatterView x="temperature" unit="°C" />}
        {tab === "hourly" && <Hourly />}
        {tab === "corr" && <Heatmap />}
      </Card>
    </div>
  );
}
