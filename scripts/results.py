"""Results table, acceptance and "beats brightness", sections 8, 11 and 11.8 of the rules.

Reads only files that already exist; it opens NO image (section 9):
    results/test_predictions/<model>_<res>_<split>_run1.csv   one row per test image
    results/test_log.csv                                     which checkpoint each test run used
    results/measure/<model>.json                             latency and energy per 1,000 predictions
    results/model_tables/totals.csv                          params and MACs
    runs/index.csv                                           energy and CO2 of every run

Output: results/results.csv                  one row per final model (the spec table)
        results/results_summary.json         acceptance, beats-brightness, test_unseen, totals
        results/test_mae_by_blur.csv         MAE per model, split and blur level
        results/test_residuals_by_count.csv  residuals per model, split and count

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\results.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import INDEX_CSV, tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from src.metrics import bootstrap_ci, bootstrap_ratio_ci, mae, r2, rmse  # noqa: E402

RULES = load_rules()
RESOLUTION = load_decision("resolution.json")["main_resolution"]
PREDICTIONS_DIR = RESULTS_DIR / "test_predictions"
MEASURE_DIR = RESULTS_DIR / "measure"
FINAL_MODELS = ["mean", "brightness", "own_cnn", "mobilenet_v3_small", "resnet18"]
CNNS = ["own_cnn", "mobilenet_v3_small", "resnet18"]
STANDARD = ["mobilenet_v3_small", "resnet18"]
METRICS = {"mae": mae, "rmse": rmse, "r2": r2}
SPLITS = ["test_seen", "test_unseen"]
KEYS = ["scene_id", "count", "blur"]  # Identify one test image.

# Baselines are not in the model table; their numbers are counted by hand.
# mean: 1 parameter (the train mean), no arithmetic per image.
# brightness: 2 parameters (a, b); 128 x 96 = 12,288 pixels -> 12,288 additions and 1 division
# for the mean pixel, then 1 multiplication and 1 addition: 12,291 FLOPs.
BASELINE_PARAMS = {"mean": 1, "brightness": 2}
BASELINE_FLOPS = {"mean": 0, "brightness": 128 * 96 + 3}
BASELINE_FILES = {"brightness": RESULTS_DIR / "baselines" / "brightness_params.json"}


def load_predictions(model, split):
    """Return the test predictions of one model, sorted so all models line up row by row."""
    path = PREDICTIONS_DIR / f"{model}_{RESOLUTION}_{split}_run1.csv"
    return pd.read_csv(path).sort_values(KEYS).reset_index(drop=True)


def checkpoint_of(model):
    """Return the checkpoint path used by the (single) test run of a CNN, from the test log."""
    log = pd.read_csv(RESULTS_DIR / "test_log.csv")
    rows = log[log["label"] == f"{model}_{RESOLUTION}"]
    if len(rows) != 1:
        raise SystemExit(f"{model}: {len(rows)} test runs in the log, expected exactly 1.")
    return PROJECT_ROOT / rows["checkpoint"].iloc[0]


def footprint(model, index):
    """Energy and CO2 in three ways (section 11.8). Baselines have no training run."""
    project = index[index["model"] == model]  # Every run named after this model, any category.
    result = {"project_kg_co2eq": project["emissions_kg"].sum()}
    if model not in CNNS:
        return {"train_kwh": np.nan, "train_kg_co2eq": np.nan, "train_incl_search_kg_co2eq": np.nan, **result}

    run_id = checkpoint_of(model).stem  # The checkpoint is named after its training run.
    final = index[index["run_id"] == run_id].iloc[0]
    search = index[(index["category"] == "search") & (index["model"] == model)]
    return {
        "train_kwh": final["energy_kwh"],
        "train_kg_co2eq": final["emissions_kg"],
        "train_incl_search_kg_co2eq": final["emissions_kg"] + search["emissions_kg"].sum(),
        **result,
    }


def size_and_cost(model, totals):
    """Parameters, MFLOPs per image and file size in MB (10^6 bytes)."""
    if model in CNNS:
        row = totals[(totals["model"] == model) & (totals["resolution"] == RESOLUTION)].iloc[0]
        return {
            "params": int(row["params"]),
            "mflops_per_img": 2 * row["macs"] / 1e6,  # 2 FLOPs = 1 MAC (section 11.7).
            "model_size_mb": checkpoint_of(model).stat().st_size / 1e6,
        }
    path = BASELINE_FILES.get(model)
    return {
        "params": BASELINE_PARAMS[model],
        "mflops_per_img": BASELINE_FLOPS[model] / 1e6,
        "model_size_mb": path.stat().st_size / 1e6 if path else np.nan,
    }


def speed_and_energy(model):
    """Latency in ms and energy per 1,000 predictions in Wh, from results/measure/<model>.json."""
    measured = json.loads((MEASURE_DIR / f"{model}.json").read_text(encoding="utf-8"))
    result = {}
    # measure.py names the GPU by torch's device type, "cuda".
    for device, key in [("gpu", "cuda"), ("cpu", "cpu")]:
        latency = measured["latency"].get(key)  # Baselines have no GPU entry.
        energy = measured["energy"].get(key)
        result[f"{device}_ms_median"] = latency["median_ms"] if latency else np.nan
        result[f"{device}_ms_p95"] = latency["p95_ms"] if latency else np.nan
        result[f"{device}_gross_wh_per_1000"] = energy["median_gross_kwh_per_1000"] * 1000 if energy else np.nan
        result[f"{device}_net_wh_per_1000"] = energy["median_net_kwh_per_1000"] * 1000 if energy else np.nan
    return result


def metrics_with_ci(table, prefix):
    """MAE, RMSE and R2 with scene-bootstrap 95 % CIs as flat columns (section 8)."""
    columns = {}
    for name, metric in METRICS.items():
        ci = bootstrap_ci(table["count"], table["prediction"], table["scene_id"], metric)
        columns[f"{prefix}_{name}"] = ci["point"]
        columns[f"{prefix}_{name}_low"] = ci["low"]
        columns[f"{prefix}_{name}_high"] = ci["high"]
    return columns


def main():
    with tracked_run("analysis", "all_final", {"task": "results", "resolution": RESOLUTION}) as run_dir:
        predictions = {(m, s): load_predictions(m, s) for m in FINAL_MODELS for s in SPLITS}
        # Paired statistics need the same images in the same order for every model.
        for split in SPLITS:
            reference = predictions[("mean", split)][KEYS]
            for model in FINAL_MODELS:
                if not predictions[(model, split)][KEYS].equals(reference):
                    raise SystemExit(f"{model} {split}: images differ from the mean baseline.")

        index = pd.read_csv(INDEX_CSV)
        totals = pd.read_csv(RESULTS_DIR / "model_tables" / "totals.csv")

        # 1. The spec table, one row per final model.
        rows = []
        for model in FINAL_MODELS:
            rows.append(
                {
                    "model": model,
                    **size_and_cost(model, totals),
                    **metrics_with_ci(predictions[(model, "test_seen")], "test_seen"),
                    **footprint(model, index),
                    **speed_and_energy(model),
                    "test_unseen_mae": mae(
                        predictions[(model, "test_unseen")]["count"],
                        predictions[(model, "test_unseen")]["prediction"],
                    ),
                }
            )
        table = pd.DataFrame(rows)
        table.to_csv(RESULTS_DIR / "results.csv", index=False, lineterminator="\n", float_format="%.6g")

        def paired_ratio(model_a, model_b, split="test_seen"):
            """MAE_a / MAE_b with the paired scene bootstrap (same resampled scenes)."""
            a, b = predictions[(model_a, split)], predictions[(model_b, split)]
            return bootstrap_ratio_ci(a["count"], a["prediction"], b["prediction"], a["scene_id"])

        # 2. Acceptance, section 8: decided on point estimates; the CI is only reported.
        seen_mae = dict(zip(table["model"], table["test_seen_mae"]))
        best = min(STANDARD, key=lambda m: seen_mae[m])
        rules = RULES["evaluation"]["acceptance"]
        acceptance = {
            "mae_own": seen_mae["own_cnn"],
            "mae_best": seen_mae[best],
            "best_standard_model": best,
            "mae_mean": seen_mae["mean"],
            "limit_best": rules["ratio_best"] * seen_mae[best],
            "limit_mean": rules["ratio_mean"] * seen_mae["mean"],
            "ratio_own_over_best": paired_ratio("own_cnn", best),
            "ratio_own_over_mean": seen_mae["own_cnn"] / seen_mae["mean"],
        }
        acceptance["pass_best"] = bool(acceptance["mae_own"] <= acceptance["limit_best"])
        acceptance["pass_mean"] = bool(acceptance["mae_own"] <= acceptance["limit_mean"])
        acceptance["pass"] = acceptance["pass_best"] and acceptance["pass_mean"]

        # 3. Beats brightness, section 11: the whole paired CI must lie below 1.
        cpu_gross = dict(zip(table["model"], table["cpu_gross_wh_per_1000"]))
        beats = {}
        for model in CNNS:
            ratio = paired_ratio(model, "brightness")
            beats[model] = {
                "ratio_mae_over_brightness": ratio,
                "beats_brightness": bool(ratio["high"] < RULES["test_protocol"]["beats_brightness"]["wins_if_ci_high_below"]),
                "energy_ratio_cpu_gross": cpu_gross[model] / cpu_gross["brightness"],
                "test_unseen_ratio_diagnostic": paired_ratio(model, "brightness", "test_unseen"),
            }

        # 4. test_unseen, diagnostic only (section 8).
        unseen = {m: metrics_with_ci(predictions[(m, "test_unseen")], "test_unseen") for m in FINAL_MODELS}

        # 5. MAE per blur level, and residuals (prediction - count) per count.
        by_blur, by_count = [], []
        for (model, split), frame in predictions.items():
            frame = frame.assign(residual=frame["prediction"] - frame["count"])
            for blur, part in frame.groupby("blur"):
                by_blur.append({"model": model, "split": split, "blur": blur, "n": len(part),
                                "mae": mae(part["count"], part["prediction"])})
            for count, part in frame.groupby("count"):
                by_count.append({"model": model, "split": split, "count": count, "n": len(part),
                                 "mean_residual": part["residual"].mean(),
                                 "mae": part["residual"].abs().mean()})
        pd.DataFrame(by_blur).to_csv(RESULTS_DIR / "test_mae_by_blur.csv", index=False,
                                     lineterminator="\n", float_format="%.6g")
        pd.DataFrame(by_count).to_csv(RESULTS_DIR / "test_residuals_by_count.csv", index=False,
                                      lineterminator="\n", float_format="%.6g")

        # Project total = every row of runs/index.csv so far (this run is added after it ends).
        summary = {
            "rules_version": RULES["version"],
            "resolution": RESOLUTION,
            "acceptance": acceptance,
            "beats_brightness": beats,
            "test_unseen": unseen,
            "project_total": {
                "runs": len(index),
                "energy_kwh": index["energy_kwh"].sum(),
                "emissions_kg": index["emissions_kg"].sum(),
                "note": "runs/index.csv before this analysis run",
            },
        }
        text = json.dumps(summary, indent=2, default=float)  # default: numpy numbers + "\n"
        (RESULTS_DIR / "results_summary.json").write_text(text, encoding="utf-8", newline="\n")
        (run_dir / "metrics.json").write_text(text, encoding="utf-8")
        print(table.T.to_string())
        print(text)


if __name__ == "__main__":
    main()
