import { useEffect, useState } from "react";
import { api } from "../api";

// Fetch data from the API when the page opens (or when `path` changes).
export function useApi(path) {
  const [state, setState] = useState({ data: null, error: null, loading: !!path });
  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    setState({ data: null, error: null, loading: true });
    api
      .get(path)
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((e) => !cancelled && setState({ data: null, error: e.message, loading: false }));
    return () => {
      cancelled = true;
    };
  }, [path]);
  return state;
}

export const Card = ({ title, children, className = "" }) => (
  <section className={`card ${className}`}>
    {title && <h3>{title}</h3>}
    {children}
  </section>
);
export const ErrorBox = ({ message }) => <div className="error">⚠ {message}</div>;
export const Loading = ({ text = "Loading..." }) => <p className="muted">{text}</p>;

// Shows a loading / error message, otherwise renders children(data).
export function Async({ state, children }) {
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorBox message={state.error} />;
  return children(state.data);
}

export const fmt = (n, d = 3) => (typeof n === "number" ? n.toFixed(d) : "-");
