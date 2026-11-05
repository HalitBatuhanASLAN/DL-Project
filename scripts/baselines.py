"""Mean and brightness baselines on val, section 7 of the rules. Fixed in advance, no variants.

Reads only the TRAIN and VAL caches at the main resolution. It opens no test file: test_seen is
touched only through the labels in splits/splits.csv, for the analytic check at the end.

Output: results/baselines/brightness_params.json  a and b, fitted on train
        results/baselines_val.json                val MAE, RMSE, R2 with scene bootstrap CIs
        results/baselines_val_per_blur.csv        val metrics per blur level
        results/baselines/val_predictions.csv     one row per val image (section 11.8)
        results/val_predictions/baselines.csv     same rows, next to the CNN predictions
        results/val_predictions/baselines.csv     same rows, next to the CNN predictions

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\baselines.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules, load_split_table  # noqa: E402
from src.data import load_train_or_val  # noqa: E402
from src.metrics import CI, N_BOOT, SEED, bootstrap_ci, mae, r2, rmse  # noqa: E402

PARAMS_JSON = RESULTS_DIR / "baselines" / "brightness_params.json"
VAL_JSON = RESULTS_DIR / "baselines_val.json"
PER_BLUR_CSV = RESULTS_DIR / "baselines_val_per_blur.csv"
# The first path is the one in the rules, the second is the folder for all val predictions.
PREDICTION_CSVS = [
    RESULTS_DIR / "baselines" / "val_predictions.csv",
    RESULTS_DIR / "val_predictions" / "baselines.csv",
]
METRICS = {"mae": mae, "rmse": rmse, "r2": r2}


def brightness_feature(images):
    """Mean uint8 pixel value of each cached image, before normalisation."""
    return images.mean(axis=(1, 2))


def fit_brightness(feature, counts):
    """Ordinary least squares for count = a + b * feature. Returns (a, b)."""
    design = np.column_stack([np.ones(len(feature)), feature])
    (a, b), *_ = np.linalg.lstsq(design, counts.astype(float), rcond=None)
    return float(a), float(b)


def score(y_true, y_pred, scene_ids):
    """Return every metric with its scene bootstrap CI. Same resamples for every model."""
    return {
        name: bootstrap_ci(y_true, y_pred, scene_ids, metric) for name, metric in METRICS.items()
    }


def analytic_test_seen_mae(table, stain, levels, train_mean):
    """MAE of the mean baseline on test_seen, from the labels in splits.csv only."""
    rows = table[
        (table["split"] == "test_seen") & (table["stain"] == stain) & table["blur"].isin(levels)
    ]
    return mae(rows["count"].to_numpy(dtype=float), np.full(len(rows), train_mean))


def main():
    rules = load_rules()
    table = load_split_table()  # Labels only.
    stain = load_decision("stain.json")["nuclei_stain"]
    levels = load_decision("blur_levels.json")["chosen_levels"]
    resolution = load_decision("resolution.json")["main_resolution"]

    config = {"rules_version": rules["version"], "resolution": resolution, "seed": SEED}
    with tracked_run(category="baseline", model="mean_and_brightness", config=config):
        train_images, train_counts, _, _ = load_train_or_val("train", resolution)
        val_images, val_counts, val_blurs, val_scenes = load_train_or_val("val", resolution)
        val_counts = val_counts.astype(float)

        # Both baselines are fitted on train only.
        train_mean = float(train_counts.mean())
        a, b = fit_brightness(brightness_feature(train_images), train_counts)
        train_fit = a + b * brightness_feature(train_images)

        predictions = {
            "mean": np.full(len(val_counts), train_mean),
            "brightness": a + b * brightness_feature(val_images),  # Raw: no clipping (section 6).
        }

        results = {name: score(val_counts, pred, val_scenes) for name, pred in predictions.items()}

        per_blur_rows = []
        for name, pred in predictions.items():
            for blur in levels:
                keep = val_blurs == blur
                row = {"model": name, "blur": blur, "n_images": int(keep.sum())}
                for metric, values in score(val_counts[keep], pred[keep], val_scenes[keep]).items():
                    row[metric] = values["point"]
                    row[f"{metric}_low"] = values["low"]
                    row[f"{metric}_high"] = values["high"]
                per_blur_rows.append(row)
        per_blur = pd.DataFrame(per_blur_rows)

        # Analytic check, labels only.
        expected_mae = rules["baselines"]["mean"]["expected_test_seen_mae"]
        test_seen_mae = analytic_test_seen_mae(table, stain, levels, train_mean)
        analytic_passed = round(test_seen_mae, 2) == expected_mae

        # Save.
        PARAMS_JSON.parent.mkdir(parents=True, exist_ok=True)
        params = {
            "rules_version": rules["version"],
            "model": "count = a + b * feature",
            "feature": "mean uint8 pixel value of the cached image",
            "resolution": resolution,
            "a": a,
            "b": b,
            "fit_on": "train",
            "n_train_images": len(train_counts),
            "train_r2": r2(train_counts, train_fit),
        }
        PARAMS_JSON.write_text(json.dumps(params, indent=2) + "\n", encoding="utf-8", newline="\n")

        val_results = {
            "rules_version": rules["version"],
            "resolution": resolution,
            "train_mean": train_mean,
            "n_val_images": len(val_counts),
            "n_val_scenes": int(len(np.unique(val_scenes))),
            "bootstrap": {"unit": "scene", "n": N_BOOT, "seed": SEED, "ci": CI},
            "models": results,
            "analytic_test_seen_mae_of_mean": test_seen_mae,
            "analytic_check_passed": analytic_passed,
        }
        VAL_JSON.write_text(json.dumps(val_results, indent=2) + "\n", encoding="utf-8", newline="\n")
        per_blur.to_csv(PER_BLUR_CSV, index=False, lineterminator="\n")

        # One row per val image, mean rows first, then brightness rows (section 11.8).
        tables = [
            pd.DataFrame(
                {
                    "model": name,
                    "scene_id": val_scenes,
                    "count": val_counts.astype(int),
                    "blur": val_blurs,
                    "prediction": pred,
                }
            )
            for name, pred in predictions.items()
        ]
        for path in PREDICTION_CSVS:
            path.parent.mkdir(parents=True, exist_ok=True)
            pd.concat(tables).to_csv(path, index=False, lineterminator="\n")

        # Print.
        print(f"Train mean {train_mean:.4f}. Brightness fit: a = {a:.6f}, b = {b:.6f}")
        for name, model in results.items():
            for metric, values in model.items():
                print(
                    f"{name:<11}{metric:<5} {values['point']:9.4f}  "
                    f"[{values['low']:.4f}, {values['high']:.4f}]"
                )
        print(per_blur[["model", "blur", "mae", "mae_low", "mae_high"]].to_string(index=False))
        print(
            f"{'PASS' if analytic_passed else 'FAIL'}  analytic test_seen MAE of the mean baseline: "
            f"{test_seen_mae:.4f}, expected {expected_mae}"
        )
        if not analytic_passed:
            raise SystemExit("The analytic check failed.")


if __name__ == "__main__":
    main()
