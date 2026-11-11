"""Why did own_cnn fail? Val-only diagnostics (post-hoc, not pre-registered).

Reads only files that already exist; it opens NO image and NO test file:
    runs/<run_id>/eval_log.csv              val MAE every 150 steps of a training run
    runs/<run_id>/metrics.json              best val MAE and best step
    results/val_predictions/<run_id>.csv    best checkpoint, one row per val image

Output (results/diagnostics/):
    checkpoint_luck.csv     a) best-checkpoint val MAE vs median val MAE of the last 5 evaluations
    val_offset.csv          b) mean signed val residual, and val MAE after removing it
    own_cnn_val_mae_by_blur.csv   c) own_cnn val MAE per blur level, seeds 42/43/44
    diagnostics.json        all of the above in one file

a) and b) are computed for all 7 final-training runs; the prompt asks for seed 42 of own_cnn and
mobilenet_v3_small, the other rows give the spread over seeds for comparison.
The offset in b) is fitted on val and measured on the same val images, so the corrected MAE is
optimistic. It is a diagnostic only and is never applied to any test prediction.

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\diagnostics.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, RUNS_DIR  # noqa: E402
from src.metrics import mae  # noqa: E402

OUT_DIR = RESULTS_DIR / "diagnostics"
VAL_PREDICTIONS_DIR = RESULTS_DIR / "val_predictions"

# The 7 final-training runs (section 11, 128x96, no AMP), from runs/index.csv.
FINAL_TRAINING_RUNS = {
    ("own_cnn", 42): "20261110-231256_train_own_cnn_73cc",
    ("own_cnn", 43): "20261110-231341_train_own_cnn_be25",
    ("own_cnn", 44): "20261110-231422_train_own_cnn_1c4d",
    ("mobilenet_v3_small", 42): "20261110-231518_train_mobilenet_v3_small_c673",
    ("mobilenet_v3_small", 43): "20261110-231701_train_mobilenet_v3_small_d8bb",
    ("mobilenet_v3_small", 44): "20261110-231834_train_mobilenet_v3_small_88b5",
    ("resnet18", 42): "20261110-232008_train_resnet18_c1c4",
}
LAST_N = 5  # Number of final evaluations used for the "typical" val MAE in a).


def check_run(model, seed, run_id):
    """Stop if the run folder does not hold the run we think it does."""
    args = json.loads((RUNS_DIR / run_id / "config.json").read_text(encoding="utf-8"))["args"]
    expected = {"model": model, "seed": seed, "resolution": "128x96", "amp": False}
    for key, value in expected.items():
        if args[key] != value:
            raise SystemExit(f"{run_id}: {key} = {args[key]}, expected {value}")


def checkpoint_luck(model, seed, run_id):
    """a) Val MAE of the saved checkpoint vs the median of the last 5 evaluations of the run."""
    log = pd.read_csv(RUNS_DIR / run_id / "eval_log.csv")
    metrics = json.loads((RUNS_DIR / run_id / "metrics.json").read_text(encoding="utf-8"))
    last = log["val_mae"].tail(LAST_N)
    best = metrics["best_val_mae"]
    return {
        "model": model,
        "seed": seed,
        "run_id": run_id,
        "best_step": metrics["best_step"],
        "stop_step": metrics["stop_step"],
        "best_val_mae": best,
        "last5_steps": " ".join(str(s) for s in log["step"].tail(LAST_N)),
        "last5_median_val_mae": float(np.median(last)),
        "last5_min_val_mae": float(last.min()),
        "last5_max_val_mae": float(last.max()),
        # > 1 means the saved checkpoint is better than a typical late evaluation.
        "median_over_best": float(np.median(last)) / best,
        # Median over the whole run, every evaluation, as a second reference.
        "all_evals_median_val_mae": float(log["val_mae"].median()),
    }


def val_offset(model, seed, run_id):
    """b) Mean signed residual (prediction - count) on val, and val MAE after removing it."""
    frame = pd.read_csv(VAL_PREDICTIONS_DIR / f"{run_id}.csv")
    residual = frame["prediction"] - frame["count"]
    offset = residual.mean()
    metrics = json.loads((RUNS_DIR / run_id / "metrics.json").read_text(encoding="utf-8"))
    val_mae = mae(frame["count"], frame["prediction"])
    # The CSV must hold the saved checkpoint's predictions (rounding in the CSV only).
    if abs(val_mae - metrics["best_val_mae"]) > 1e-4:
        raise SystemExit(f"{run_id}: CSV MAE {val_mae} != best_val_mae {metrics['best_val_mae']}")
    return {
        "model": model,
        "seed": seed,
        "run_id": run_id,
        "n_images": len(frame),
        "val_mae": val_mae,
        "mean_signed_residual": offset,
        "share_positive_residuals": float((residual > 0).mean()),
        # Counts (of 20) whose mean residual is positive: is the offset the same at every count?
        "counts_with_positive_mean_residual": int((residual.groupby(frame["count"]).mean() > 0).sum()),
        "n_counts": int(frame["count"].nunique()),
        "val_mae_after_removing_offset": mae(frame["count"], frame["prediction"] - offset),
    }


def own_cnn_by_blur():
    """c) own_cnn val MAE per blur level, one row per seed and blur level."""
    rows = []
    for (model, seed), run_id in FINAL_TRAINING_RUNS.items():
        if model != "own_cnn":
            continue
        frame = pd.read_csv(VAL_PREDICTIONS_DIR / f"{run_id}.csv")
        for blur, part in frame.groupby("blur"):
            rows.append({"seed": seed, "blur": blur, "n": len(part), "val_mae": mae(part["count"], part["prediction"]),
                         "mean_signed_residual": (part["prediction"] - part["count"]).mean()})
    return pd.DataFrame(rows)


def main():
    config = {"task": "own_cnn_diagnostics", "sets": "val only", "runs": sorted(FINAL_TRAINING_RUNS.values())}
    with tracked_run("analysis", "own_cnn", config, notes="post-hoc val diagnostics") as run_dir:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for (model, seed), run_id in FINAL_TRAINING_RUNS.items():
            check_run(model, seed, run_id)

        luck = pd.DataFrame([checkpoint_luck(m, s, r) for (m, s), r in FINAL_TRAINING_RUNS.items()])
        offset = pd.DataFrame([val_offset(m, s, r) for (m, s), r in FINAL_TRAINING_RUNS.items()])
        blur = own_cnn_by_blur()

        options = {"index": False, "lineterminator": "\n", "float_format": "%.6g"}
        luck.to_csv(OUT_DIR / "checkpoint_luck.csv", **options)
        offset.to_csv(OUT_DIR / "val_offset.csv", **options)
        blur.to_csv(OUT_DIR / "own_cnn_val_mae_by_blur.csv", **options)

        summary = {
            "note": "post-hoc, val only; the offset correction is never applied to test",
            "checkpoint_luck": luck.to_dict(orient="records"),
            "val_offset": offset.to_dict(orient="records"),
            "own_cnn_val_mae_by_blur": blur.to_dict(orient="records"),
        }
        text = json.dumps(summary, indent=2, default=float)  # default: numpy numbers
        (OUT_DIR / "diagnostics.json").write_text(text + "\n", encoding="utf-8", newline="\n")
        (run_dir / "metrics.json").write_text(text, encoding="utf-8")

        pd.set_option("display.width", 200)
        print(luck.drop(columns=["run_id"]).to_string(index=False))
        print(offset.drop(columns=["run_id"]).to_string(index=False))
        print(blur.pivot(index="seed", columns="blur", values="val_mae").to_string())


if __name__ == "__main__":
    main()
