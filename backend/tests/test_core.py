"""Run from the backend folder:  python -m pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import FEATURES, TARGET
from app.data import clean_dataset, load_dataset
from app.data_gen import generate_synthetic_data
from app.service import SolarService, validate_inputs, sanity_warnings
from app.training import chronological_split, run_training


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    d = tmp_path_factory.mktemp("work")
    raw = generate_synthetic_data(days=120, seed=1)
    csv = d / "data.csv"
    raw.to_csv(csv, index=False)
    df, _ = clean_dataset(load_dataset(csv))
    run_training(df, d / "models", {"is_synthetic": True, "source": "test"}, quick=True, verbose=False)
    return SolarService(model_dir=d / "models", data_path=csv, info_path=d / "none.json"), df


def test_synthetic_columns_and_labels():
    df = generate_synthetic_data(days=10)
    assert set(FEATURES + [TARGET, "timestamp"]) <= set(df.columns)
    assert df[TARGET].dropna().min() >= 0


def test_cleaning_removes_missing_target_and_sorts():
    df = generate_synthetic_data(days=30)
    clean, report = clean_dataset(df)
    assert clean[TARGET].notna().all()
    assert clean["timestamp"].is_monotonic_increasing
    assert report["rows_final"] == len(clean)


def test_chronological_split_has_no_overlap():
    df, _ = clean_dataset(generate_synthetic_data(days=30))
    train, test = chronological_split(df, 0.2)
    assert train["timestamp"].max() < test["timestamp"].min()


def test_models_saved_and_beat_baseline(trained):
    svc, _ = trained
    m = svc.metrics()
    assert len(m["models"]) == 5
    for r in m["models"]:
        assert r["rmse"] < m["baseline"]["rmse"]


def test_prediction_non_negative_and_night_is_zero(trained):
    svc, _ = trained
    day = dict(irradiance=800, temperature=30, humidity=40, wind_speed=3, cloud_cover=10, hour=12)
    night = dict(day, irradiance=0, hour=2)
    assert svc.predict("random_forest", day)["prediction_kw"] > 1
    assert svc.predict("random_forest", night)["prediction_kw"] < 0.2
    assert svc.predict("linear_regression", night)["prediction_kw"] >= 0


def test_whatif_more_irradiance_means_more_power(trained):
    svc, _ = trained
    base = dict(irradiance=300, temperature=30, humidity=40, wind_speed=3, cloud_cover=10, hour=12)
    r = svc.whatif("extra_trees", base, "irradiance")
    assert r["predictions_kw"][-1] > r["predictions_kw"][5]


def test_input_validation_errors():
    with pytest.raises(ValueError):
        validate_inputs({"irradiance": 5000})
    with pytest.raises(ValueError):
        validate_inputs(dict(irradiance=1, temperature=1, humidity=1, wind_speed=1, cloud_cover=1, hour=99))
    assert sanity_warnings(dict(irradiance=500, temperature=20, humidity=50, wind_speed=1, cloud_cover=10, hour=2))


def test_chart_data_and_batch(trained):
    svc, df = trained
    assert len(svc.hourly()["rows"]) == 24
    assert len(svc.correlation()["labels"]) == 7
    assert svc.scatter("temperature")["points"]
    out = svc.predict_batch("gradient_boosting", df.head(20)[FEATURES])
    assert "predicted_power_kw" in out and len(out) == 20
    with pytest.raises(ValueError):
        svc.predict_batch("gradient_boosting", pd.DataFrame({"a": [1]}))
    imp = svc.importance()["random_forest"]
    assert imp["builtin"] is not None and set(imp["permutation"]) == set(FEATURES)


def test_missing_models_raise_clear_error(tmp_path):
    from app.service import ModelNotReady
    with pytest.raises(ModelNotReady):
        SolarService(model_dir=tmp_path).metrics()
