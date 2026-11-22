"""Central configuration: paths, feature definitions and valid ranges."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
DATA_PATH = DATA_DIR / "solar_data.csv"
DATA_INFO_PATH = DATA_DIR / "dataset_info.json"

TIME_COL = "timestamp"
TARGET = "power_kw"
FEATURES = ["irradiance", "temperature", "humidity", "wind_speed", "cloud_cover", "hour"]
# Features after engineering (hour -> hour_sin, hour_cos)
MODEL_FEATURES = ["irradiance", "temperature", "humidity", "wind_speed",
                  "cloud_cover", "hour_sin", "hour_cos"]

FEATURE_INFO = [
    dict(key="irradiance", label="Solar irradiance", unit="W/m²", min=0, max=1200, default=600, step=10,
         description="Solar power reaching one square metre of the panel. The strongest driver of output."),
    dict(key="temperature", label="Ambient temperature", unit="°C", min=-10, max=60, default=30, step=1,
         description="Air temperature. Hot panels are less efficient, so very high temperature slightly lowers output."),
    dict(key="humidity", label="Relative humidity", unit="%", min=0, max=100, default=50, step=1,
         description="Moisture in the air. High humidity scatters sunlight and has a small negative effect."),
    dict(key="wind_speed", label="Wind speed", unit="m/s", min=0, max=25, default=3, step=0.5,
         description="Wind cools the panel, which improves its efficiency."),
    dict(key="cloud_cover", label="Cloud cover", unit="%", min=0, max=100, default=20, step=1,
         description="Fraction of the sky covered by clouds. Clouds reduce irradiance."),
    dict(key="hour", label="Hour of the day", unit="h", min=0, max=23, default=12, step=1,
         description="0-23. Captures the daily sun cycle (encoded as sine/cosine inside the model)."),
]
FEATURE_RANGES = {f["key"]: (f["min"], f["max"]) for f in FEATURE_INFO}

MODEL_LABELS = {
    "linear_regression": "Linear Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "extra_trees": "Extra Trees",
    "gradient_boosting": "Gradient Boosting",
}
