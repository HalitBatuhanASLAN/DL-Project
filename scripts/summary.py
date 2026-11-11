"""results/summary.md: one table with every number the report cites, each with its source file.

Reads only files that already exist; it opens NO image and NO test file (section 9):
    results/results.csv, results/results_summary.json   test, energy, CO2, latency, acceptance
    results/baselines_val.json                          val MAE of the baselines
    runs/<run_id>/metrics.json                          val MAE, steps and energy of training runs
    results/diagnostics/*.csv                           post-hoc val diagnostics (scripts/diagnostics.py)
    results/figures/main_points.csv                     points of the main figure (scripts/figures.py)
    results/test_mae_by_blur.csv                        test_seen MAE per blur level
    runs/index.csv                                      project total

Every value is copied by code from its file, so no number is typed by hand.

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\summary.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import INDEX_CSV, tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, RUNS_DIR  # noqa: E402

FINAL_MODELS = ["mean", "brightness", "own_cnn", "mobilenet_v3_small", "resnet18"]
CNNS = ["own_cnn", "mobilenet_v3_small", "resnet18"]

# Training runs cited in the report (same run ids as scripts/figures.py and diagnostics.py).
TRAINING_RUNS = [
    ("own_cnn seed 42 (final)", "20261110-231256_train_own_cnn_73cc"),
    ("own_cnn seed 43", "20261110-231341_train_own_cnn_be25"),
    ("own_cnn seed 44", "20261110-231422_train_own_cnn_1c4d"),
    ("mobilenet_v3_small seed 42 (final)", "20261110-231518_train_mobilenet_v3_small_c673"),
    ("mobilenet_v3_small seed 43", "20261110-231701_train_mobilenet_v3_small_d8bb"),
    ("mobilenet_v3_small seed 44", "20261110-231834_train_mobilenet_v3_small_88b5"),
    ("resnet18 seed 42 (final)", "20261110-232008_train_resnet18_c1c4"),
    ("own_cnn 256x192 (ablation)", "20261110-232222_train_own_cnn_a201"),
    ("own_cnn depthwise-separable (ablation)", "20261110-232352_train_own_cnn_ds_13c9"),
    ("resnet18 AMP (efficiency run)", "20261110-232429_train_resnet18_0845"),
    ("resnet18 FP32 600-step noise reference", "20261110-232634_train_resnet18_8658"),
]
SEED_RUNS = {  # Best val MAE over seeds 42-44, for the seed spread (section 11.8).
    "own_cnn": TRAINING_RUNS[0:3],
    "mobilenet_v3_small": TRAINING_RUNS[3:6],
}

ROWS = []  # (section, quantity, value, source)


def add(section, quantity, value, source):
    ROWS.append((section, quantity, value, source))


def fmt(value, digits=4):
    """Round to `digits` significant digits; keep integers and text as they are."""
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    if float(value).is_integer() and abs(value) >= 1:
        return f"{int(value):,}"
    return f"{float(value):.{digits}g}"


def ci(point, low, high):
    return f"{fmt(point)} [{fmt(low)}, {fmt(high)}]"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_rows(results, summary):
    src = "results/results.csv"
    for _, r in results.iterrows():
        m = r["model"]
        add("test_seen", f"{m}: MAE [95% CI]", ci(r["test_seen_mae"], r["test_seen_mae_low"], r["test_seen_mae_high"]), src)
        add("test_seen", f"{m}: RMSE [95% CI]", ci(r["test_seen_rmse"], r["test_seen_rmse_low"], r["test_seen_rmse_high"]), src)
        add("test_seen", f"{m}: R2 [95% CI]", ci(r["test_seen_r2"], r["test_seen_r2_low"], r["test_seen_r2_high"]), src)
    by_blur = pd.read_csv(RESULTS_DIR / "test_mae_by_blur.csv")
    seen = by_blur[by_blur["split"] == "test_seen"]
    for m in FINAL_MODELS[1:]:  # The mean baseline is 25.85 at every level.
        part = seen[seen["model"] == m].sort_values("blur")
        text = ", ".join(f"F{b} {fmt(v)}" for b, v in zip(part["blur"], part["mae"]))
        add("test_seen", f"{m}: MAE per blur level", text, "results/test_mae_by_blur.csv")
    for m in FINAL_MODELS:
        u = summary["test_unseen"][m]
        add("test_unseen (diagnostic)", f"{m}: MAE [95% CI]",
            ci(u["test_unseen_mae"], u["test_unseen_mae_low"], u["test_unseen_mae_high"]),
            "results/results_summary.json")


def decision_rows(summary):
    src = "results/results_summary.json"
    a = summary["acceptance"]
    add("acceptance (sec. 8)", "MAE_own (own_cnn, test_seen)", fmt(a["mae_own"]), src)
    add("acceptance (sec. 8)", f"MAE_best ({a['best_standard_model']})", fmt(a["mae_best"]), src)
    add("acceptance (sec. 8)", "limit 1.15 x MAE_best", fmt(a["limit_best"]), src)
    add("acceptance (sec. 8)", "pass MAE_own <= 1.15 x MAE_best", fmt(a["pass_best"]), src)
    add("acceptance (sec. 8)", "MAE_mean / limit 0.60 x MAE_mean", f"{fmt(a['mae_mean'])} / {fmt(a['limit_mean'])}", src)
    add("acceptance (sec. 8)", "pass MAE_own <= 0.60 x MAE_mean", fmt(a["pass_mean"]), src)
    r = a["ratio_own_over_best"]
    add("acceptance (sec. 8)", "MAE_own / MAE_best, paired [95% CI]", ci(r["point"], r["low"], r["high"]), src)
    add("acceptance (sec. 8)", "MAE_own / MAE_mean", fmt(a["ratio_own_over_mean"]), src)
    add("acceptance (sec. 8)", "ACCEPTANCE", "PASS" if a["pass"] else "FAIL", src)
    for m in CNNS:
        b = summary["beats_brightness"][m]
        r, u = b["ratio_mae_over_brightness"], b["test_unseen_ratio_diagnostic"]
        add("beats brightness (sec. 11)", f"{m}: MAE / MAE_brightness, test_seen [95% CI]", ci(r["point"], r["low"], r["high"]), src)
        add("beats brightness (sec. 11)", f"{m}: beats brightness", fmt(b["beats_brightness"]), src)
        add("beats brightness (sec. 11)", f"{m}: energy ratio (CPU gross)", fmt(b["energy_ratio_cpu_gross"]), src)
        add("beats brightness (sec. 11)", f"{m}: test_unseen ratio (diagnostic) [95% CI]", ci(u["point"], u["low"], u["high"]), src)


def val_rows():
    base = read_json(RESULTS_DIR / "baselines_val.json")["models"]
    for m in ["mean", "brightness"]:
        v = base[m]["mae"]
        add("val", f"{m}: val MAE [95% CI]", ci(v["point"], v["low"], v["high"]), "results/baselines_val.json")
    for label, run_id in TRAINING_RUNS:
        m = read_json(RUNS_DIR / run_id / "metrics.json")
        add("val", f"{label}: best val MAE (best step / stop step)",
            f"{fmt(m['best_val_mae'])} ({m['best_step']} / {m['stop_step']})", f"runs/{run_id}/metrics.json")
    for model, runs in SEED_RUNS.items():
        values = [read_json(RUNS_DIR / r / "metrics.json")["best_val_mae"] for _, r in runs]
        add("val", f"{model}: best val MAE over seeds 42-44, mean +- SD (ddof 1), min-max",
            f"{fmt(np.mean(values))} +- {fmt(np.std(values, ddof=1))}, {fmt(min(values))}-{fmt(max(values))}",
            "runs/<3 seed runs>/metrics.json")


def cost_rows(results, index):
    src = "results/results.csv"
    for _, r in results.iterrows():
        m = r["model"]
        add("size", f"{m}: params / MFLOPs per image / file MB",
            f"{fmt(r['params'])} / {fmt(r['mflops_per_img'])} / {fmt(r['model_size_mb'])}", src)
    for _, r in results.iterrows():
        m = r["model"]
        add("latency (batch 1)", f"{m}: CPU ms median / p95", f"{fmt(r['cpu_ms_median'])} / {fmt(r['cpu_ms_p95'])}", src)
        if m in CNNS:
            add("latency (batch 1)", f"{m}: GPU ms median / p95", f"{fmt(r['gpu_ms_median'])} / {fmt(r['gpu_ms_p95'])}", src)
    for _, r in results.iterrows():
        m = r["model"]
        add("energy per 1,000 predictions", f"{m}: CPU Wh gross / net",
            f"{fmt(r['cpu_gross_wh_per_1000'])} / {fmt(r['cpu_net_wh_per_1000'])}", src)
        if m in CNNS:
            add("energy per 1,000 predictions", f"{m}: GPU Wh gross / net",
                f"{fmt(r['gpu_gross_wh_per_1000'])} / {fmt(r['gpu_net_wh_per_1000'])}", src)
    for _, r in results[results["model"].isin(CNNS)].iterrows():
        m = r["model"]
        add("training footprint", f"{m}: final run (seed 42) Wh / g CO2eq",
            f"{fmt(r['train_kwh'] * 1000)} / {fmt(r['train_kg_co2eq'] * 1000)}", src)
        add("training footprint", f"{m}: training incl. LR search g CO2eq", fmt(r["train_incl_search_kg_co2eq"] * 1000), src)
    for _, r in results.iterrows():
        add("training footprint", f"{r['model']}: project g CO2eq (runs named after the model)",
            fmt(r["project_kg_co2eq"] * 1000), src)
    # Mixed precision (section 11.5): energy per step, AMP vs FP32.
    for label, run_id in [TRAINING_RUNS[6], TRAINING_RUNS[9], TRAINING_RUNS[10]]:
        m = read_json(RUNS_DIR / run_id / "metrics.json")
        add("mixed precision (sec. 11.5)", f"{label}: mWh per step ({m['steps_run']} steps)",
            fmt(m["energy_kwh"] * 1e6 / m["steps_run"]), f"runs/{run_id}/metrics.json")
    add("project total", "runs in runs/index.csv (before this summary run) / failed",
        f"{len(index)} / {(index['status'] == 'failed').sum()}", "runs/index.csv")
    add("project total", "energy Wh / g CO2eq / duration s",
        f"{fmt(index['energy_kwh'].sum() * 1000)} / {fmt(index['emissions_kg'].sum() * 1000)} / {fmt(index['duration_s'].sum())}",
        "runs/index.csv")


def figure_rows():
    points = pd.read_csv(RESULTS_DIR / "figures" / "main_points.csv")
    for _, p in points[points["kind"] == "val MAE"].iterrows():
        add("main figure (val-only points)", f"{p['label']}: val MAE / x g CO2eq",
            f"{fmt(p['mae'])} / {fmt(p['x_train_kg'] * 1000)}", "results/figures/main_points.csv")
    for _, p in points[points["family"].isin(["mean", "brightness"])].iterrows():
        add("main figure (baselines)", f"{p['label']}: x training / x project g CO2eq",
            f"{fmt(p['x_train_kg'] * 1000)} / {fmt(p['x_project_kg'] * 1000)}", "results/figures/main_points.csv")
    # The latest run of scripts/figures.py (its config says task "figures") holds the Pareto front.
    figures_runs = [d for d in sorted(RUNS_DIR.glob("*_analysis_all_final_*"))
                    if read_json(d / "config.json")["args"].get("task") == "figures"]
    figures_run = figures_runs[-1]
    front = read_json(figures_run / "metrics.json")["pareto_front"]
    for version, labels in front.items():
        add("main figure", f"Pareto front, x = {version}", ", ".join(labels), f"runs/{figures_run.name}/metrics.json")


def diagnostic_rows():
    folder = "results/diagnostics/"
    luck = pd.read_csv(RESULTS_DIR / "diagnostics" / "checkpoint_luck.csv")
    for _, r in luck.iterrows():
        add("diagnostics a) checkpoint luck", f"{r['model']} seed {r['seed']}: best val MAE / median of last 5 evals (ratio)",
            f"{fmt(r['best_val_mae'])} / {fmt(r['last5_median_val_mae'])} ({fmt(r['median_over_best'], 3)})",
            folder + "checkpoint_luck.csv")
    offset = pd.read_csv(RESULTS_DIR / "diagnostics" / "val_offset.csv")
    for _, r in offset.iterrows():
        add("diagnostics b) val offset", f"{r['model']} seed {r['seed']}: mean signed residual / val MAE -> after removing it",
            f"{fmt(r['mean_signed_residual'])} / {fmt(r['val_mae'])} -> {fmt(r['val_mae_after_removing_offset'])}",
            folder + "val_offset.csv")
        add("diagnostics b) val offset", f"{r['model']} seed {r['seed']}: counts with positive mean residual",
            f"{r['counts_with_positive_mean_residual']} of {r['n_counts']}", folder + "val_offset.csv")
    blur = pd.read_csv(RESULTS_DIR / "diagnostics" / "own_cnn_val_mae_by_blur.csv")
    for seed, part in blur.groupby("seed"):
        add("diagnostics c) own_cnn val MAE per blur", f"seed {seed}",
            ", ".join(f"F{b} {fmt(v)}" for b, v in zip(part["blur"], part["val_mae"])),
            folder + "own_cnn_val_mae_by_blur.csv")


def main():
    config = {"task": "summary_table", "sets": "saved results only"}
    with tracked_run("analysis", "all_final", config, notes="results/summary.md") as run_dir:
        results = pd.read_csv(RESULTS_DIR / "results.csv")
        summary = read_json(RESULTS_DIR / "results_summary.json")
        index = pd.read_csv(INDEX_CSV)  # This run is added only after it ends.

        test_rows(results, summary)
        decision_rows(summary)
        val_rows()
        cost_rows(results, index)
        figure_rows()
        diagnostic_rows()

        lines = [
            "# Numbers cited in the report",
            "",
            f"Generated by `scripts/summary.py` ({summary['rules_version']}, resolution {summary['resolution']}).",
            "Every value is read by code from the file in the last column. CIs: 95 % scene bootstrap,",
            "B = 10,000, seed 42 (section 8). test_unseen and the diagnostics never decide anything.",
            "The diagnostics are post-hoc and val only; the offset correction is never applied to test.",
            "",
            "| # | Section | Quantity | Value | Source |",
            "| --- | --- | --- | --- | --- |",
        ]
        for number, (section, quantity, value, source) in enumerate(ROWS, start=1):
            lines.append(f"| {number} | {section} | {quantity} | {value} | `{source}` |")
        text = "\n".join(lines) + "\n"
        (RESULTS_DIR / "summary.md").write_text(text, encoding="utf-8", newline="\n")
        (run_dir / "metrics.json").write_text(json.dumps({"rows": len(ROWS)}), encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
