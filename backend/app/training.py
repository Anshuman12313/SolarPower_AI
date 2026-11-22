"""Model training, tuning, evaluation and artifact saving."""
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (ExtraTreesRegressor, GradientBoostingRegressor,
                              RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from .config import FEATURES, MODEL_FEATURES, MODEL_LABELS, TARGET, TIME_COL
from .features import prepare_features


def build_pipeline(estimator, scale: bool = False) -> Pipeline:
    """features -> impute missing values -> (scale) -> model. Saved as ONE object."""
    steps = [("features", FunctionTransformer(prepare_features)),
             ("imputer", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scaler", StandardScaler()))
    steps.append(("model", estimator))
    return Pipeline(steps)


def get_model_specs(quick: bool = False):
    """(key, estimator, needs_scaling, hyper-parameter grid)."""
    if quick:  # tiny grids: used by unit tests
        return [
            ("linear_regression", LinearRegression(), True, {}),
            ("decision_tree", DecisionTreeRegressor(random_state=42), False, {"model__max_depth": [8]}),
            ("random_forest", RandomForestRegressor(n_estimators=30, random_state=42, n_jobs=-1), False,
             {"model__max_depth": [10]}),
            ("extra_trees", ExtraTreesRegressor(n_estimators=30, random_state=42, n_jobs=-1), False,
             {"model__max_depth": [10]}),
            ("gradient_boosting", GradientBoostingRegressor(n_estimators=50, random_state=42), False,
             {"model__max_depth": [3]}),
        ]
    return [
        ("linear_regression", LinearRegression(), True, {}),
        ("decision_tree", DecisionTreeRegressor(random_state=42), False,
         {"model__max_depth": [6, 10, 14], "model__min_samples_leaf": [1, 5, 20]}),
        ("random_forest", RandomForestRegressor(random_state=42, n_jobs=-1), False,
         {"model__n_estimators": [100, 150], "model__max_depth": [10, 14],
          "model__min_samples_leaf": [3, 8]}),
        ("extra_trees", ExtraTreesRegressor(random_state=42, n_jobs=-1), False,
         {"model__n_estimators": [100, 150], "model__max_depth": [10, 14],
          "model__min_samples_leaf": [3, 8]}),
        ("gradient_boosting", GradientBoostingRegressor(random_state=42), False,
         {"model__n_estimators": [100, 200], "model__learning_rate": [0.05, 0.1],
          "model__max_depth": [3, 4]}),
    ]


def chronological_split(df: pd.DataFrame, test_size: float = 0.2):
    """Oldest rows -> training, newest rows -> testing (no shuffling = no leakage)."""
    n_test = max(1, int(len(df) * test_size))
    return df.iloc[:-n_test].copy(), df.iloc[-n_test:].copy()


def evaluate(y_true, y_pred) -> dict:
    y_pred = np.clip(y_pred, 0, None)           # power can never be negative
    mse = mean_squared_error(y_true, y_pred)
    return {"mae": float(mean_absolute_error(y_true, y_pred)), "mse": float(mse),
            "rmse": float(np.sqrt(mse)), "r2": float(r2_score(y_true, y_pred))}


def _builtin_importance(pipe: Pipeline):
    model = pipe.named_steps["model"]
    if not hasattr(model, "feature_importances_"):
        return None
    imp = dict(zip(MODEL_FEATURES, model.feature_importances_.astype(float)))
    imp["hour"] = imp.pop("hour_sin") + imp.pop("hour_cos")   # merge the two hour columns
    return imp


def run_training(df: pd.DataFrame, model_dir, source_info: dict, test_size: float = 0.2,
                 quick: bool = False, verbose: bool = True) -> dict:
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    log = print if verbose else (lambda *a, **k: None)

    train_df, test_df = chronological_split(df, test_size)
    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_test, y_test = test_df[FEATURES], test_df[TARGET]
    log(f"Train rows: {len(train_df)} | Test rows: {len(test_df)} (chronological split)")

    # Baseline: always predicts the training mean. Every real model must beat it.
    baseline = build_pipeline(DummyRegressor(strategy="mean")).fit(X_train, y_train)
    baseline_metrics = evaluate(y_test, baseline.predict(X_test))

    results, importance, predictions = [], {}, {}
    sample_idx = np.linspace(0, len(test_df) - 1, num=min(600, len(test_df))).astype(int)
    cv = TimeSeriesSplit(n_splits=3)
    perm_rows = min(3000, len(X_test))

    for key, estimator, scale, grid in get_model_specs(quick):
        log(f"Training {MODEL_LABELS[key]} ...")
        search = GridSearchCV(build_pipeline(estimator, scale), grid, cv=cv,
                              scoring="neg_root_mean_squared_error", n_jobs=-1)
        start = time.perf_counter()
        search.fit(X_train, y_train)
        seconds = time.perf_counter() - start
        best = search.best_estimator_

        scores = evaluate(y_test, best.predict(X_test))
        results.append({
            "key": key, "name": MODEL_LABELS[key], **scores,
            "cv_rmse": float(-search.best_score_),
            "train_seconds": round(seconds, 2),
            "best_params": {k.replace("model__", ""): v for k, v in search.best_params_.items()},
        })
        joblib.dump(best, model_dir / f"{key}.joblib", compress=3)

        perm = permutation_importance(best, X_test.iloc[:perm_rows], y_test.iloc[:perm_rows],
                                      n_repeats=5, random_state=42, scoring="r2")
        importance[key] = {"builtin": _builtin_importance(best),
                           "permutation": dict(zip(FEATURES, perm.importances_mean.astype(float)))}
        pred = np.clip(best.predict(X_test), 0, None)
        predictions[key] = {"actual": y_test.to_numpy()[sample_idx].round(3).tolist(),
                            "predicted": pred[sample_idx].round(3).tolist()}

    best_key = min(results, key=lambda r: r["rmse"])["key"]
    ts = (test_df[TIME_COL].astype(str).to_numpy()[sample_idx].tolist()
          if TIME_COL in test_df.columns else list(range(len(sample_idx))))
    metrics = {
        "source": source_info, "best_model": best_key, "baseline": baseline_metrics, "models": results,
        "split": {"strategy": "chronological", "test_size": test_size,
                  "train_rows": int(len(train_df)), "test_rows": int(len(test_df)),
                  "train_end": str(train_df[TIME_COL].max()) if TIME_COL in df else None,
                  "test_start": str(test_df[TIME_COL].min()) if TIME_COL in df else None},
    }
    (model_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (model_dir / "importance.json").write_text(json.dumps(importance, indent=2), encoding="utf-8")
    (model_dir / "predictions.json").write_text(
        json.dumps({"timestamps": ts, "models": predictions}), encoding="utf-8")
    log(f"Best model by RMSE: {MODEL_LABELS[best_key]}")
    return metrics
