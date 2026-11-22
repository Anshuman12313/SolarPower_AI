"""Loading, validating and cleaning the dataset."""
import numpy as np
import pandas as pd
from .config import FEATURES, TARGET, TIME_COL, FEATURE_RANGES


def load_dataset(path, rename: dict | None = None) -> pd.DataFrame:
    """Read a CSV. `rename` maps your column names to the project's names."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Dataset not found: {path}. Run `python train_model.py` first.")
    if rename:
        df = df.rename(columns=rename)
    if TIME_COL in df.columns:
        df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
        if "hour" not in df.columns:
            df["hour"] = df[TIME_COL].dt.hour
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}. "
                         f"Required: {FEATURES + [TARGET]}")
    return df


def clean_dataset(df: pd.DataFrame):
    """Return (clean_df, report). Missing FEATURE values are kept as NaN and imputed
    inside the model pipeline (so no information from the test set leaks into training)."""
    report = {"rows_before": int(len(df))}
    df = df.copy()
    if TIME_COL in df.columns:
        df = df.dropna(subset=[TIME_COL]).drop_duplicates(subset=[TIME_COL]).sort_values(TIME_COL)
    else:
        df = df.drop_duplicates()
    report["rows_after_duplicates"] = int(len(df))

    for col in FEATURES + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Physically impossible values become missing
    invalid = {}
    for col, (lo, hi) in FEATURE_RANGES.items():
        bad = (df[col] < lo) | (df[col] > hi)
        invalid[col] = int(bad.sum())
        df.loc[bad, col] = np.nan
    report["invalid_set_to_missing"] = invalid

    report["missing_features_before_imputation"] = {c: int(df[c].isna().sum()) for c in FEATURES}
    report["rows_missing_target_dropped"] = int(df[TARGET].isna().sum())
    df = df.dropna(subset=[TARGET])
    df[TARGET] = df[TARGET].clip(lower=0)
    report["rows_final"] = int(len(df))
    return df.reset_index(drop=True), report
