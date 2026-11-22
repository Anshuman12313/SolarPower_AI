"""Feature engineering shared by training and prediction."""
import numpy as np
import pandas as pd


def prepare_features(X) -> pd.DataFrame:
    """Replace `hour` by sin/cos so that hour 23 and hour 0 are neighbours."""
    X = pd.DataFrame(X)
    out = X[["irradiance", "temperature", "humidity", "wind_speed", "cloud_cover"]].astype(float).copy()
    hour = X["hour"].astype(float)
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return out
