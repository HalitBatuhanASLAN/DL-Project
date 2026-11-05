"""The test run of one final model, section 9 of the rules.

This is the only script that opens test_seen and test_unseen. One run gives both sets.

One test run per final model: mean, brightness, own_cnn, resnet18, mobilenet_v3_small, at the main
resolution, seed 42. Anything else needs --force --reason "...": a second run of a model, and any
ablation variant (section 9 counts that as an extra logged test use).
Every run, forced or not, is added to results/test_log.csv BEFORE a test file is opened, so a run
that crashes half way is still a test use.

Output: results/test_log.csv                                      one row per run
        results/test_predictions/<label>_<split>_run<k>.csv       one row per test image
        runs/<run_id>/metrics.json                                metrics with scene bootstrap CIs
<label> is <model>_<resolution>, and <k> is 1 for the first run of that label.

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\evaluate_test.py --model mean
    .venv\\Scripts\\python.exe scripts\\evaluate_test.py --model own_cnn --checkpoint checkpoints\\<run_id>.pt
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from src.data import read_cache, save_predictions, to_model_input  # noqa: E402
from src.metrics import bootstrap_ci, mae, r2, rmse  # noqa: E402
from src.models import ALL_MODELS, build_model, predict  # noqa: E402

TEST_LOG = RESULTS_DIR / "test_log.csv"
PREDICTIONS_DIR = RESULTS_DIR / "test_predictions"
BASELINES_JSON = RESULTS_DIR / "baselines_val.json"
BRIGHTNESS_JSON = RESULTS_DIR / "baselines" / "brightness_params.json"
SPLITS = ["test_seen", "test_unseen"]
BASELINES = ["mean", "brightness"]
FINAL_MODELS = BASELINES + ["own_cnn", "resnet18", "mobilenet_v3_small"]
LOG_COLUMNS = ["time", "label", "attempt", "forced", "reason", "run_id", "checkpoint"]
METRICS = {"mae": mae, "rmse": rmse, "r2": r2}


def past_runs(label):
    """Return how many runs of this label are already in the log."""
    if not TEST_LOG.exists():
        return 0
    with open(TEST_LOG, newline="", encoding="utf-8") as file:
        return sum(row["label"] == label for row in csv.DictReader(file))


def append_log(row):
    """Add one row to results/test_log.csv, with the header if the file is new."""
    write_header = not TEST_LOG.exists()
    with open(TEST_LOG, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_COLUMNS, lineterminator="\n")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def load_cnn(args, device, final_seed):
    """Load a checkpoint and check that it is the model the arguments say it is."""
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    if checkpoint["model"] != args.model or checkpoint["resolution"] != args.resolution:
        raise SystemExit("The checkpoint is a different model or resolution than the arguments.")
    if checkpoint["seed"] != final_seed and not args.force:
        raise SystemExit("Seed 42 is the final model (section 11): this needs --force --reason.")
    model = build_model(args.model, pretrained=False).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    return model


def baseline_predictions(name, images):
    """Predictions of the mean or brightness baseline, with the parameters fitted on train."""
    if name == "mean":
        train_mean = json.loads(BASELINES_JSON.read_text(encoding="utf-8"))["train_mean"]
        return np.full(len(images), train_mean)
    params = json.loads(BRIGHTNESS_JSON.read_text(encoding="utf-8"))
    return params["a"] + params["b"] * images.mean(axis=(1, 2))  # Raw: no clipping (section 6).


def main():
    main_resolution = load_decision("resolution.json")["main_resolution"]
    parser = argparse.ArgumentParser(description="Test run of one model (section 9).")
    parser.add_argument("--model", required=True, choices=BASELINES + ALL_MODELS)
    parser.add_argument("--checkpoint", help="required for a CNN")
    parser.add_argument("--resolution", default=main_resolution)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    # These checks open nothing, so a refused run is not a test use.
    is_cnn = args.model not in BASELINES
    if is_cnn and not args.checkpoint:
        raise SystemExit("A CNN needs --checkpoint.")
    if args.force and not args.reason:
        raise SystemExit("--force needs --reason.")

    label = f"{args.model}_{args.resolution}"
    attempt = past_runs(label) + 1
    is_final = args.model in FINAL_MODELS and args.resolution == main_resolution
    if (attempt > 1 or not is_final) and not args.force:
        raise SystemExit(
            f"{label}: run {attempt}, final model: {is_final}. Section 9: this needs --force --reason."
        )

    rules = load_rules()
    config = {"rules_version": rules["version"], "label": label, "attempt": attempt}
    with tracked_run(category="eval", model=args.model, config=config, notes=args.reason) as run_dir:
        device = torch.device("cuda")
        model = load_cnn(args, device, rules["models"]["final_seed"]) if is_cnn else None

        # The log row comes first: from here on, this run counts as a test use.
        append_log(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "label": label,
                "attempt": attempt,
                "forced": args.force,
                "reason": args.reason,
                "run_id": run_dir.name,
                "checkpoint": args.checkpoint or "",
            }
        )

        results = {"label": label, "attempt": attempt}
        for split in SPLITS:  # test_seen is primary, test_unseen is a diagnostic (section 8).
            images, counts, blurs, scene_ids = read_cache(split, args.resolution)
            if is_cnn:
                inputs = to_model_input(images, args.resolution, device)
                predictions = predict(model, inputs).numpy()
            else:
                predictions = baseline_predictions(args.model, images)

            save_predictions(
                PREDICTIONS_DIR / f"{label}_{split}_run{attempt}.csv",
                args.model,
                scene_ids,
                counts,
                blurs,
                predictions,
            )
            results[split] = {
                name: bootstrap_ci(counts.astype(float), predictions, scene_ids, metric)
                for name, metric in METRICS.items()
            }

        (run_dir / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
