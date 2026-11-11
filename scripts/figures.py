"""Report figures (spec 3.5 and section 11.8), drawn from files that already exist.

Reads only saved results; it opens NO image and NO test file (section 9):
    results/results.csv                     test_seen MAE, CO2 and energy of the 5 final models
    results/test_mae_by_blur.csv            test MAE per model, split and blur level
    results/test_residuals_by_count.csv     test mean residual per model, split and count
    runs/index.csv                          CO2 of every run
    runs/<run_id>/metrics.json, eval_log.csv   val MAE of the training runs

Output (results/figures/, each as PNG at 300 dpi and as PDF):
    mae_vs_co2_training      main figure, x = training CO2 incl. LR search
    mae_vs_co2_project       main figure, x = project CO2 per model
    val_curves               val MAE every 150 steps, 7 final-training runs
    test_mae_by_blur         test_seen MAE per blur level
    residual_by_count        test mean residual per count (seen and unseen counts)
    energy_per_1000          CPU gross energy per 1,000 predictions
    main_points.csv          every point of the main figure with its source

Main figure: final models are test_seen points (filled circles). Val-only variants have NO test
number, so they are drawn with their best val MAE (open triangles, label "val MAE"). The Pareto
front uses the plotted test points only. The mean baseline (MAE 25.85) is not drawn in either
version (the title says so), so the y axis is linear. The project version shows the test points only.

Figure labels: own_cnn is "KirazNet", own_cnn_ds is "KirazNet-Lite" (figures only; code, run
folders and the label column of main_points.csv keep the old names).

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\figures.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Draw to files only, no window.
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import INDEX_CSV, tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, RUNS_DIR  # noqa: E402

FIG_DIR = RESULTS_DIR / "figures"
FINAL_MODELS = ["mean", "brightness", "own_cnn", "mobilenet_v3_small", "resnet18"]
CNNS = ["own_cnn", "mobilenet_v3_small", "resnet18"]

# One fixed colour per model family, used in every figure (colour follows the model).
COLORS = {
    "mean": "#9a9a94",
    "brightness": "#4a4a46",
    "own_cnn": "#2a78d6",
    "mobilenet_v3_small": "#eb6834",
    "resnet18": "#1baf7a",
}
SHORT = {"mean": "mean", "brightness": "brightness", "own_cnn": "KirazNet",
         "mobilenet_v3_small": "mobilenet", "resnet18": "resnet18"}
# Label keys of main_points.csv (unchanged from v1) and the figure text for them.
KEY = {"mean": "mean", "brightness": "brightness", "own_cnn": "own_cnn",
       "mobilenet_v3_small": "mobilenet", "resnet18": "resnet18"}
DISPLAY = {"own_cnn": "KirazNet", "own_cnn s43": "KirazNet s43", "own_cnn s44": "KirazNet s44",
           "own_cnn 256x192": "KirazNet 256x192", "own_cnn depthwise": "KirazNet-Lite"}
MEAN_NOTE = "mean baseline MAE 25.85, not shown"

# The baselines are fitted by scripts/baselines.py; run 20261105-233219 wrote the current
# brightness parameters and val predictions (commit b56eaaf). One run fits both baselines.
BASELINE_FIT_RUN = "20261105-233219_baseline_mean_and_brightness_03b5"

# The 7 final-training runs (128x96, no AMP); seed 42 is the final model of each family.
FINAL_TRAINING_RUNS = [
    ("own_cnn", 42, "20261110-231256_train_own_cnn_73cc"),
    ("own_cnn", 43, "20261110-231341_train_own_cnn_be25"),
    ("own_cnn", 44, "20261110-231422_train_own_cnn_1c4d"),
    ("mobilenet_v3_small", 42, "20261110-231518_train_mobilenet_v3_small_c673"),
    ("mobilenet_v3_small", 43, "20261110-231701_train_mobilenet_v3_small_d8bb"),
    ("mobilenet_v3_small", 44, "20261110-231834_train_mobilenet_v3_small_88b5"),
    ("resnet18", 42, "20261110-232008_train_resnet18_c1c4"),
]

# Val-only variants: (label, family = parent model, run_id, expected config values).
VARIANTS = [
    ("own_cnn s43", "own_cnn", "20261110-231341_train_own_cnn_be25", {"seed": 43}),
    ("own_cnn s44", "own_cnn", "20261110-231422_train_own_cnn_1c4d", {"seed": 44}),
    ("mobilenet s43", "mobilenet_v3_small", "20261110-231701_train_mobilenet_v3_small_d8bb", {"seed": 43}),
    ("mobilenet s44", "mobilenet_v3_small", "20261110-231834_train_mobilenet_v3_small_88b5", {"seed": 44}),
    ("own_cnn 256x192", "own_cnn", "20261110-232222_train_own_cnn_a201", {"resolution": "256x192"}),
    ("own_cnn depthwise", "own_cnn", "20261110-232352_train_own_cnn_ds_13c9", {"model": "own_cnn_ds"}),
    ("resnet18 AMP", "resnet18", "20261110-232429_train_resnet18_0845", {"amp": True, "max_steps": 3000}),
]


# Main-figure label positions (offset in points, alignment) where the default (right) label collides.
# With a linear y axis the points spread out; mobilenet s43 sits next to resnet18 AMP (almost the
# same MAE), so its label goes above the point, and the 256x192 label goes left, away from s43.
LABEL_OFFSETS = {
    "training": {"brightness": (10, 3, "left"), "mobilenet s43": (0, 8, "center"),
                 "own_cnn 256x192": (-7, -3, "right")},
    "project": {"brightness": (10, 3, "left")},
}
X_NOTES = {
    "training": ("x of a val-only variant = its own training run + its parent's LR search (the only runs "
                 "that belong to it).\nx of brightness = the run that fitted it."),
    "project": "x of brightness = that model's project total plus all baseline-fit runs.",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(fig, name):
    """Save one figure as PNG (300 dpi) and PDF, then close it."""
    fig.savefig(FIG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def style(ax):
    """Recessive axes: light grid behind the data, no top/right frame."""
    ax.grid(True, which="major", color="#e1e0d9", linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


# ---------------------------------------------------------------- main figure


def main_points(results, index):
    """One row per point of the main figure: y, both x values, and where they come from."""
    emissions = dict(zip(index["run_id"], index["emissions_kg"]))
    search_kg = index[index["category"] == "search"].groupby("model")["emissions_kg"].sum()
    # All baseline-fitting runs; shared by mean and brightness, so each gets the full sum.
    baseline_runs_kg = index[index["model"] == "mean_and_brightness"]["emissions_kg"].sum()

    rows = []
    for _, r in results.iterrows():
        model = r["model"]
        if model in CNNS:
            x_train, x_project = r["train_incl_search_kg_co2eq"], r["project_kg_co2eq"]
            source = "results/results.csv (train_incl_search_kg_co2eq, project_kg_co2eq)"
        else:  # Baselines: no training run in results.csv, use the fit run(s).
            x_train = emissions[BASELINE_FIT_RUN]
            x_project = r["project_kg_co2eq"] + baseline_runs_kg
            source = f"runs/index.csv ({BASELINE_FIT_RUN}; project = results.csv + all mean_and_brightness runs)"
        rows.append({"label": KEY[model], "family": model, "kind": "test_seen MAE",
                     "mae": r["test_seen_mae"], "x_train_kg": x_train, "x_project_kg": x_project,
                     "mae_source": "results/results.csv (test_seen_mae)", "x_source": source})

    for label, family, run_id, expected in VARIANTS:
        args = read_json(RUNS_DIR / run_id / "config.json")["args"]
        for key, value in expected.items():  # Stop if the run is not the variant we think.
            if args[key] != value:
                raise SystemExit(f"{run_id}: {key} = {args[key]}, expected {value}")
        # A variant reuses its parent's LR (section 11.4), so the parent's LR search is counted.
        # No other run belongs to a variant, so both x values are the same.
        x = emissions[run_id] + search_kg[family]
        rows.append({"label": label, "family": family, "kind": "val MAE",
                     "mae": read_json(RUNS_DIR / run_id / "metrics.json")["best_val_mae"],
                     "x_train_kg": x, "x_project_kg": x,
                     "mae_source": f"runs/{run_id}/metrics.json (best_val_mae)",
                     "x_source": f"runs/index.csv ({run_id} + {family} search runs)"})
    return pd.DataFrame(rows)


def pareto_front(points):
    """Points not beaten on both CO2 and MAE (lower is better for both), sorted by CO2."""
    front, best_mae = [], float("inf")
    for _, p in points.sort_values(["x", "mae"]).iterrows():
        if p["mae"] < best_mae:  # Cheaper points all have a higher MAE: this one is on the front.
            front.append(p)
            best_mae = p["mae"]
    return pd.DataFrame(front)


def plot_main(points, x_column, x_label, name, version, title):
    data = points.assign(x=points[x_column])
    data = data[data["family"] != "mean"]  # Not drawn: MEAN_NOTE in the title.
    if version == "project":
        data = data[data["kind"] == "test_seen MAE"]  # Test points only.
    test = data[data["kind"] == "test_seen MAE"]
    val = data[data["kind"] == "val MAE"]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    front = pareto_front(test)
    ax.step(front["x"], front["mae"], where="post", color="#0b0b0b", linestyle="--",
            linewidth=1, label="Pareto front (test points only)", zorder=1)
    ax.scatter(test["x"], test["mae"], s=70, c=[COLORS[f] for f in test["family"]],
               edgecolors="white", linewidths=1.5, marker="o", zorder=3,
               label="test_seen MAE (final model, seed 42)")
    ax.scatter(val["x"], val["mae"], s=60, facecolors="none", marker="^", linewidths=1.5,
               edgecolors=[COLORS[f] for f in val["family"]], zorder=3,
               label="val MAE (val-only variant, no test run)")

    # Points on the Pareto front get a black ring, so a front of one point is still visible.
    ax.scatter(front["x"], front["mae"], s=180, facecolors="none", edgecolors="#0b0b0b",
               linewidths=1, zorder=2)

    # Direct labels; val points say "val" in the label as well, so they cannot be misread.
    for _, p in data.iterrows():
        text = DISPLAY.get(p["label"], p["label"]) + (" (val)" if p["kind"] == "val MAE" else "")
        dx, dy, ha = LABEL_OFFSETS[version].get(p["label"], (6, 3, "left"))
        leader = {"arrowstyle": "-", "color": "#c3c2b7", "linewidth": 0.6} if dy >= 20 else None
        ax.annotate(text, (p["x"], p["mae"]), xytext=(dx, dy), textcoords="offset points",
                    fontsize=7, color="#3d3d3a", ha=ha, arrowprops=leader)

    ax.set_xscale("log")  # y stays linear: without the mean baseline all MAEs lie within 1-2 cells.
    # Ticks at 1, 2 and 5 times each power of 10 (more if the range is under one decade), as e.g. 2.0e-04.
    ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(2, 5)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.1e}"))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda value, _: f"{value:.1e}"))
    ax.set_xlabel(x_label)
    ax.set_ylabel("MAE (cells)")
    ax.set_title(title, fontsize=10)
    style(ax)
    ax.grid(True, which="minor", color="#f0efea", linewidth=0.4)

    # Legend with neutral (black) proxy markers: the shape says test or val, the colour says model.
    handles = [
        Line2D([], [], color="#0b0b0b", linestyle="--", linewidth=1, label="Pareto front (test points only)"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="none", markeredgecolor="#0b0b0b",
               markersize=11, label="on the Pareto front"),
        Line2D([], [], marker="o", linestyle="none", color="#0b0b0b", markersize=7,
               label="test_seen MAE (final model, seed 42)"),
    ]
    if len(val):
        handles.append(Line2D([], [], marker="^", linestyle="none", markerfacecolor="none",
                              markeredgecolor="#0b0b0b", markersize=7,
                              label="val MAE (val-only variant, no test run)"))
    ax.legend(handles=handles, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2,
              frameon=False)
    fig.text(0.01, -0.06, X_NOTES[version], fontsize=6.5, color="#5f5e5a", va="top")
    save(fig, name)
    return front


# ---------------------------------------------------------------- other figures


def plot_val_curves(baseline_val):
    """Val MAE every 150 steps; a star marks the saved (best) checkpoint."""
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    dashes = {42: "-", 43: "--", 44: ":"}
    for model, seed, run_id in FINAL_TRAINING_RUNS:
        log = pd.read_csv(RUNS_DIR / run_id / "eval_log.csv")
        best = read_json(RUNS_DIR / run_id / "metrics.json")
        ax.plot(log["step"], log["val_mae"], dashes[seed], color=COLORS[model], linewidth=1.5,
                label=f"{SHORT[model]} seed {seed}")
        ax.plot(best["best_step"], best["best_val_mae"], "*", color=COLORS[model], markersize=10,
                markeredgecolor="white", markeredgewidth=0.8)
    ax.axhline(baseline_val, color=COLORS["brightness"], linewidth=1, linestyle="-.",
               label=f"brightness val MAE ({baseline_val:.2f})")
    ax.set_yscale("log")
    ax.set_xlabel("training step")
    ax.set_ylabel("val MAE (cells), log scale")
    ax.set_title("Val MAE during training (star = saved checkpoint)", fontsize=10)
    style(ax)
    ax.legend(fontsize=7, ncol=2, frameon=False)
    save(fig, "val_curves")


def plot_blur(by_blur):
    """test_seen MAE per blur level; the mean baseline is 25.85 at every level and left out."""
    seen = by_blur[by_blur["split"] == "test_seen"]
    levels = sorted(seen["blur"].unique())
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for model in ["brightness"] + CNNS:
        part = seen[seen["model"] == model].sort_values("blur")
        ax.plot(range(len(levels)), part["mae"], "-o", color=COLORS[model], linewidth=2,
                markersize=6, label=SHORT[model])
    ax.set_xticks(range(len(levels)), [f"F{b}" for b in levels])
    ax.set_xlabel("blur level")
    ax.set_ylabel("test_seen MAE (cells)")
    ax.set_title("test_seen MAE per blur level (mean baseline 25.85, not shown)", fontsize=9)
    style(ax)
    ax.legend(fontsize=8, frameon=False)
    save(fig, "test_mae_by_blur")


def plot_residuals(by_count):
    """Mean residual (prediction - count) per count; open squares = held-out (unseen) counts."""
    models = ["brightness"] + CNNS
    fig, axes = plt.subplots(1, len(models), figsize=(11, 3.4), sharey=True)
    for ax, model in zip(axes, models):
        seen = by_count[(by_count["model"] == model) & (by_count["split"] == "test_seen")]
        unseen = by_count[(by_count["model"] == model) & (by_count["split"] == "test_unseen")]
        ax.axhline(0, color="#c3c2b7", linewidth=1)
        ax.plot(seen["count"], seen["mean_residual"], "-o", color=COLORS[model], linewidth=1.2,
                markersize=4, label="seen count (test_seen)")
        ax.plot(unseen["count"], unseen["mean_residual"], "s", markersize=7, markerfacecolor="white",
                markeredgecolor="#0b0b0b", markeredgewidth=1.2, label="unseen count (test_unseen)")
        ax.set_title(SHORT[model], fontsize=9)
        ax.set_xlabel("true count")
        style(ax)
    axes[0].set_ylabel("mean residual (cells)\nprediction - count")
    axes[0].legend(fontsize=7, frameon=False, loc="lower left")
    fig.suptitle("Mean test residual by count (mean baseline = 50.05 - count, not shown)", fontsize=9)
    save(fig, "residual_by_count")


def plot_energy(results):
    """CPU gross energy per 1,000 predictions (the energy ratio of section 11 uses this)."""
    fig, ax = plt.subplots(figsize=(5.5, 4))
    values = results.set_index("model").loc[FINAL_MODELS, "cpu_gross_wh_per_1000"]
    bars = ax.bar([SHORT[m] for m in FINAL_MODELS], values, color=[COLORS[m] for m in FINAL_MODELS],
                  width=0.6)
    for bar, value in zip(bars, values):
        ax.annotate(f"{value:.2g}", (bar.get_x() + bar.get_width() / 2, value), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=8, color="#3d3d3a")
    ax.set_yscale("log")
    ax.set_ylabel("Wh per 1,000 predictions (CPU, gross), log scale")
    ax.set_title("Inference energy, CPU gross, batch 1", fontsize=10)
    style(ax)
    ax.grid(False, axis="x")
    save(fig, "energy_per_1000")


def main():
    config = {"task": "figures", "version": 2, "sets": "saved predictions and run folders only"}
    with tracked_run("analysis", "all_final", config, notes="report figures") as run_dir:
        FIG_DIR.mkdir(parents=True, exist_ok=True)
        results = pd.read_csv(RESULTS_DIR / "results.csv")
        index = pd.read_csv(INDEX_CSV)
        baseline_val = read_json(RESULTS_DIR / "baselines_val.json")["models"]["brightness"]["mae"]["point"]

        points = main_points(results, index)
        points.to_csv(FIG_DIR / "main_points.csv", index=False, lineterminator="\n", float_format="%.6g")
        fronts = {
            "training": plot_main(points, "x_train_kg", "kg CO2eq, training incl. LR search (log scale)",
                                  "mae_vs_co2_training", "training",
                                  f"MAE vs CO2 (training): test_seen for final models, val for variants\n({MEAN_NOTE})"),
            "project": plot_main(points, "x_project_kg", "kg CO2eq, project total per model (log scale)",
                                 "mae_vs_co2_project", "project",
                                 f"MAE vs CO2 (project total): test_seen, final models\n({MEAN_NOTE})"),
        }
        plot_val_curves(baseline_val)
        plot_blur(pd.read_csv(RESULTS_DIR / "test_mae_by_blur.csv"))
        plot_residuals(pd.read_csv(RESULTS_DIR / "test_residuals_by_count.csv"))
        plot_energy(results)

        summary = {name: list(front["label"]) for name, front in fronts.items()}
        (run_dir / "metrics.json").write_text(json.dumps({"pareto_front": summary}, indent=2), encoding="utf-8")
        pd.set_option("display.width", 200)
        print(points.drop(columns=["mae_source", "x_source"]).to_string(index=False))
        print("Pareto front:", summary)


if __name__ == "__main__":
    main()
