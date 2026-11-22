"""Business logic used by the API: loading models, predicting, what-if, chart data.
Pure Python (no web framework) so it can be unit-tested on its own."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import (DATA_INFO_PATH, DATA_PATH, FEATURE_INFO, FEATURE_RANGES, FEATURES,
                     MODEL_DIR, MODEL_LABELS, TARGET)
from .data import clean_dataset, load_dataset


class ModelNotReady(Exception):
    """Raised when trained models are missing."""


def validate_inputs(inputs: dict) -> dict:
    """Check that all six features are present, numeric and inside the valid range."""
    clean = {}
    for name in FEATURES:
        if name not in inputs or inputs[name] is None:
            raise ValueError(f"Missing input: {name}")
        try:
            value = float(inputs[name])
        except (TypeError, ValueError):
            raise ValueError(f"Input '{name}' must be a number")
        lo, hi = FEATURE_RANGES[name]
        if not lo <= value <= hi:
            raise ValueError(f"Input '{name}' must be between {lo} and {hi} (got {value})")
        clean[name] = value
    return clean


def sanity_warnings(x: dict) -> list:
    """Friendly warnings when the inputs are physically unlikely."""
    w = []
    night = x["hour"] < 5 or x["hour"] > 19
    if night and x["irradiance"] > 50:
        w.append("Irradiance is above 0 at night. Real sunlight is almost zero before 5 AM or after 7 PM.")
    if not night and 9 <= x["hour"] <= 15 and x["irradiance"] < 20:
        w.append("Irradiance is near zero during midday. This only happens in very heavy storms.")
    if x["cloud_cover"] > 90 and x["irradiance"] > 700:
        w.append("Irradiance is very high for an almost fully cloudy sky.")
    return w


class SolarService:
    def __init__(self, model_dir=MODEL_DIR, data_path=DATA_PATH, info_path=DATA_INFO_PATH):
        self.model_dir = Path(model_dir)
        self.data_path = Path(data_path)
        self.info_path = Path(info_path)
        self._models = {}
        self._df = None

    # ---------- artifacts ----------
    def _read_json(self, name):
        path = self.model_dir / name
        if not path.exists():
            raise ModelNotReady("Trained models not found. Run `python train_model.py` in the backend folder.")
        return json.loads(path.read_text(encoding="utf-8"))

    def metrics(self):
        return self._read_json("metrics.json")

    def importance(self):
        return self._read_json("importance.json")

    def model_list(self):
        m = self.metrics()
        return {"best_model": m["best_model"],
                "models": [{"key": r["key"], "name": r["name"]} for r in m["models"]]}

    def dataset_info(self):
        if not self.info_path.exists():
            raise ModelNotReady("Dataset info not found. Run `python train_model.py`.")
        return json.loads(self.info_path.read_text(encoding="utf-8"))

    def _model(self, key):
        if key not in MODEL_LABELS:
            raise ValueError(f"Unknown model '{key}'. Choose one of {list(MODEL_LABELS)}")
        if key not in self._models:
            path = self.model_dir / f"{key}.joblib"
            if not path.exists():
                raise ModelNotReady("Trained models not found. Run `python train_model.py` in the backend folder.")
            self._models[key] = joblib.load(path)
        return self._models[key]

    def _data(self):
        if self._df is None:
            try:
                raw = load_dataset(self.data_path)
            except FileNotFoundError:
                raise ModelNotReady("Dataset not found. Run `python train_model.py`.")
            self._df, _ = clean_dataset(raw)
        return self._df

    # ---------- prediction ----------
    def predict_frame(self, key, frame: pd.DataFrame) -> np.ndarray:
        pred = self._model(key).predict(frame[FEATURES])
        return np.clip(pred, 0, None)                 # power cannot be negative

    def predict(self, key, inputs: dict) -> dict:
        x = validate_inputs(inputs)
        value = float(self.predict_frame(key, pd.DataFrame([x]))[0])
        return {"model": key, "model_name": MODEL_LABELS[key], "prediction_kw": round(value, 3),
                "warnings": sanity_warnings(x)}

    def predict_batch(self, key, df: pd.DataFrame, limit=5000) -> pd.DataFrame:
        missing = [c for c in FEATURES if c not in df.columns]
        if missing:
            raise ValueError(f"CSV is missing columns: {missing}. Required: {FEATURES}")
        if len(df) == 0:
            raise ValueError("The CSV has no rows.")
        out = df.head(limit).copy()
        for col in FEATURES:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        out["predicted_power_kw"] = self.predict_frame(key, out).round(3)
        return out

    def whatif(self, key, base: dict, variable: str, points: int = 40) -> dict:
        x = validate_inputs(base)
        if variable not in FEATURE_RANGES:
            raise ValueError(f"Unknown variable '{variable}'")
        lo, hi = FEATURE_RANGES[variable]
        values = np.arange(lo, hi + 1) if variable == "hour" else np.linspace(lo, hi, points)
        frame = pd.DataFrame([{**x, variable: float(v)} for v in values])
        preds = self.predict_frame(key, frame)
        return {"variable": variable, "current_value": x[variable],
                "current_prediction_kw": round(float(self.predict_frame(key, pd.DataFrame([x]))[0]), 3),
                "values": [round(float(v), 2) for v in values],
                "predictions_kw": [round(float(p), 3) for p in preds]}

    def scenarios(self, key, scenarios: list) -> list:
        out = []
        for s in scenarios:
            x = validate_inputs(s["inputs"])
            out.append({"name": s.get("name", "Scenario"), "inputs": x,
                        "prediction_kw": round(float(self.predict_frame(key, pd.DataFrame([x]))[0]), 3)})
        return out

    # ---------- chart data ----------
    def scatter(self, x: str, max_points=1500) -> dict:
        if x not in FEATURES:
            raise ValueError(f"Unknown feature '{x}'")
        df = self._data()
        if x != "irradiance":                          # night rows would hide the pattern
            df = df[df["irradiance"] > 50]
        df = df[[x, TARGET, "cloud_cover"]].dropna()
        if len(df) > max_points:
            df = df.sample(max_points, random_state=1)
        return {"x": x, "points": [{"x": float(a), "y": float(b), "cloud": float(c)}
                                   for a, b, c in df.itertuples(index=False)]}

    def hourly(self) -> dict:
        g = self._data().groupby("hour")[TARGET]
        stats = pd.DataFrame({"mean": g.mean(), "p10": g.quantile(0.1), "p90": g.quantile(0.9)}).round(3)
        return {"rows": [{"hour": int(h), **r} for h, r in stats.to_dict("index").items()]}

    def correlation(self) -> dict:
        cols = FEATURES + [TARGET]
        corr = self._data()[cols].corr().round(3).fillna(0)
        return {"labels": cols, "matrix": corr.values.tolist()}

    def actual_vs_predicted(self, key) -> dict:
        data = self._read_json("predictions.json")
        if key not in data["models"]:
            raise ValueError(f"No predictions stored for '{key}'")
        m = data["models"][key]
        return {"timestamps": data["timestamps"], "actual": m["actual"], "predicted": m["predicted"],
                "residuals": [round(a - p, 3) for a, p in zip(m["actual"], m["predicted"])]}

    @staticmethod
    def feature_info():
        return FEATURE_INFO
