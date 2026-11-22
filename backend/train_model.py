"""Train all models.  Usage:

    python train_model.py                       # generate synthetic data + train
    python train_model.py --data my.csv --source "NASA POWER + plant X" --rename "GHI:irradiance,T2M:temperature"
"""
import argparse
import json

from app.config import DATA_PATH, DATA_INFO_PATH, MODEL_DIR
from app.data import clean_dataset, load_dataset
from app.data_gen import save_synthetic_dataset
from app.training import run_training


def parse_rename(text):
    if not text:
        return None
    try:
        return dict(pair.split(":") for pair in text.split(","))
    except ValueError:
        raise SystemExit('--rename must look like "oldName:newName,oldName2:newName2"')


def main():
    p = argparse.ArgumentParser(description="Train SolarPower AI models")
    p.add_argument("--data", help="Path to your own CSV (default: generate synthetic data)")
    p.add_argument("--source", default="User supplied dataset", help="Describe where your data came from")
    p.add_argument("--rename", help='Map your column names, e.g. "GHI:irradiance,T2M:temperature"')
    p.add_argument("--regenerate", action="store_true", help="Regenerate the synthetic dataset")
    p.add_argument("--quick", action="store_true", help="Small hyper-parameter grids (faster)")
    args = p.parse_args()

    try:
        if args.data:
            df = load_dataset(args.data, parse_rename(args.rename))
            info = {"name": args.data, "is_synthetic": False, "source": args.source,
                    "rows": int(len(df)), "note": "User-supplied data. Source is as stated by the user."}
            DATA_INFO_PATH.write_text(json.dumps(info, indent=2), encoding="utf-8")
            df.to_csv(DATA_PATH, index=False)          # the dashboard reads this copy
        else:
            if args.regenerate or not DATA_PATH.exists():
                print("Generating SYNTHETIC dataset ...")
                save_synthetic_dataset()
            df = load_dataset(DATA_PATH)
            info = json.loads(DATA_INFO_PATH.read_text(encoding="utf-8"))

        df, report = clean_dataset(df)
        print("Cleaning report:", json.dumps(report, indent=2))
        info["cleaning_report"] = report
        DATA_INFO_PATH.write_text(json.dumps(info, indent=2), encoding="utf-8")

        metrics = run_training(df, MODEL_DIR, info, quick=args.quick)
    except (FileNotFoundError, ValueError) as err:
        raise SystemExit(f"ERROR: {err}")

    print(f"\n{'Model':<20}{'MAE':>8}{'MSE':>8}{'RMSE':>8}{'R2':>8}")
    print(f"{'Baseline (mean)':<20}{metrics['baseline']['mae']:8.3f}{metrics['baseline']['mse']:8.3f}"
          f"{metrics['baseline']['rmse']:8.3f}{metrics['baseline']['r2']:8.3f}")
    for m in metrics["models"]:
        print(f"{m['name']:<20}{m['mae']:8.3f}{m['mse']:8.3f}{m['rmse']:8.3f}{m['r2']:8.3f}")
    print("\nModels saved in:", MODEL_DIR)


if __name__ == "__main__":
    main()
