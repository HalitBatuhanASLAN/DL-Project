"""LR search for one model, section 11.4 of the rules.

Each LR is a normal training run of 300 steps, on the full train set, seed 42, cosine over those
300 steps, and is its own tracked run (category search). The choice is the lowest val MAE at
step 300, which is the last evaluation of the trial, not the best one. A tie goes to the lower LR.
If the winner is on the edge of the grid, one more value beyond it is tried, once.

Output: results/lr_search/<model>.json

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\lr_search.py --model own_cnn
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from src.models import ALL_MODELS  # noqa: E402
from train import run_training  # noqa: E402 (train.py is next to this file)

RULES = load_rules()
SEARCH = RULES["lr_search"]
OUT_DIR = RESULTS_DIR / "lr_search"


def run_trial(model_name, lr, resolution):
    """Run one trial and return the numbers the choice and the report need."""
    metrics = run_training(
        model_name,
        seed=SEARCH["seed"],
        lr=lr,
        resolution=resolution,
        max_steps=SEARCH["steps"],
        category="search",
        notes=f"lr search, lr {lr}",
    )
    return {
        "lr": lr,
        "val_mae_at_last_step": metrics["last_val_mae"],
        "steps_run": metrics["steps_run"],
        "run_id": Path(metrics["checkpoint"]).stem,  # The checkpoint is named after the run.
        "duration_s": metrics["duration_s"],
        "energy_kwh": metrics["energy_kwh"],
    }


def choose(trials):
    """Return the trial with the lowest val MAE. On a tie, tuples compare the LR next."""
    return min(trials, key=lambda trial: (trial["val_mae_at_last_step"], trial["lr"]))


def main():
    parser = argparse.ArgumentParser(description="LR search for one model (section 11.4).")
    parser.add_argument("--model", required=True, choices=ALL_MODELS)
    args = parser.parse_args()

    resolution = load_decision("resolution.json")["main_resolution"]
    grid = SEARCH["grid"]
    trials = [run_trial(args.model, lr, resolution) for lr in grid]

    # Edge rule: one more value beyond the edge, for any model. Not repeated after that.
    best = choose(trials)
    extra_lr = None
    if best["lr"] == grid[0]:
        extra_lr = SEARCH["edge_values"]["below"]
    elif best["lr"] == grid[-1]:
        extra_lr = SEARCH["edge_values"]["above"]
    if extra_lr is not None:
        trials.append(run_trial(args.model, extra_lr, resolution))
        best = choose(trials)  # Same choice rule, over all trials.

    result = {
        "rules_version": RULES["version"],
        "model": args.model,
        "resolution": resolution,
        "seed": SEARCH["seed"],
        "steps": SEARCH["steps"],
        "grid": grid,
        "edge_rule_lr": extra_lr,
        "chosen_lr": best["lr"],
        "trials": trials,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2) + "\n"
    (OUT_DIR / f"{args.model}.json").write_text(text, encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    main()
