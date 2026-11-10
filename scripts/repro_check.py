"""Reproducibility check: the same training run twice must give the same model.

Runs scripts/train.py's run_training twice with the same settings (own_cnn, seed 42, lr 1e-3,
150 steps, category env). With 150 steps and evaluation every 150 steps, the only evaluation is at
step 150, so the saved checkpoint holds the final weights. Then compares, in a third tracked run:
  - val MAE at step 150 of both runs,
  - every tensor of both checkpoints (weights and BatchNorm buffers): bit-identical or not, and
    the largest absolute difference.

Output: results/repro_check.json

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\repro_check.py
"""

import json
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from train import run_training  # noqa: E402 (train.py is next to this file)

RULES = load_rules()
SETTINGS = {"model_name": "own_cnn", "seed": 42, "lr": 1e-3, "max_steps": 150}
NOTES = "reproducibility check"


def compare_checkpoints(path_a, path_b):
    """Return (bit_identical, largest absolute difference, name of that tensor)."""
    a = torch.load(path_a, map_location="cpu", weights_only=True)["state_dict"]
    b = torch.load(path_b, map_location="cpu", weights_only=True)["state_dict"]
    assert a.keys() == b.keys()
    identical = all(torch.equal(a[key], b[key]) for key in a)
    largest, where = 0.0, None
    for key in a:
        # .double() so integer buffers (num_batches_tracked) can be subtracted too.
        difference = (a[key].double() - b[key].double()).abs().max().item()
        if difference > largest:
            largest, where = difference, key
    return identical, largest, where


def main():
    resolution = load_decision("resolution.json")["main_resolution"]
    runs = [
        run_training(**SETTINGS, resolution=resolution, category="env", notes=NOTES)
        for _ in range(2)
    ]

    config = {"rules_version": RULES["version"], "compare": [r["checkpoint"] for r in runs]}
    with tracked_run("env", "own_cnn", config, notes=NOTES + ", compare") as run_dir:
        identical, largest, where = compare_checkpoints(
            PROJECT_ROOT / runs[0]["checkpoint"], PROJECT_ROOT / runs[1]["checkpoint"]
        )
        result = {
            "rules_version": RULES["version"],
            "settings": {**SETTINGS, "resolution": resolution},
            "run_ids": [Path(r["checkpoint"]).stem for r in runs],
            "val_mae": [r["last_val_mae"] for r in runs],
            "val_mae_identical": runs[0]["last_val_mae"] == runs[1]["last_val_mae"],
            "weights_bit_identical": identical,
            "largest_abs_difference": largest,
            "largest_difference_tensor": where,
        }
        (run_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    text = json.dumps(result, indent=2) + "\n"
    (RESULTS_DIR / "repro_check.json").write_text(text, encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    main()
