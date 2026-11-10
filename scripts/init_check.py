"""Init check for rules-v2.1 (section 11.1): every model must start at the mean baseline.

For each of the 4 models, in its own tracked run (category env), with no training:
  1. Build the model (seed 42) and compute the val MAE in eval mode at step 0.
     Expected: 25.85 cells, the val MAE of the mean baseline (results/baselines_val.json),
     because the head weights are 0 and every image gets 0.5005 -> 50.05 cells.
  2. One forward + backward pass on the first 32 train images, train mode, L1 loss, no
     optimiser step. The gradient of the head weights must be non-zero, or the model could
     never leave the mean prediction.
PASS if |val MAE - 25.85| <= 0.01 cells (float32 rounding only), and all head weights are 0
and the head weight gradient norm is > 0.

Output: results/init_check.json

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\init_check.py
"""

import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from src.data import load_train_or_val, to_model_input  # noqa: E402
from src.metrics import mae  # noqa: E402
from src.models import ALL_MODELS, build_model, output_layer, predict  # noqa: E402

RULES = load_rules()
SEED = RULES["models"]["final_seed"]  # 42
BATCH_SIZE = RULES["training"]["batch_size"]  # 32
TARGET_SCALE = RULES["preprocess"]["target_scale"]  # 100
TOLERANCE = 0.01  # Cells. Float32 rounding of 0.5005 is far below this.


def check_model(name, resolution, device):
    """Build one model, check its step-0 val MAE and its head gradient. Returns a dict."""
    torch.manual_seed(SEED)
    model = build_model(name).to(device)
    head = output_layer(model)

    # 1. Val MAE at step 0, eval mode (predict() switches to eval mode itself).
    val_u8, val_counts, _, _ = load_train_or_val("val", resolution)
    val_pred = predict(model, to_model_input(val_u8, resolution, device), BATCH_SIZE).numpy()
    val_mae = mae(val_counts.astype(float), val_pred)

    # 2. One forward + backward pass in train mode; no optimiser, so nothing is updated.
    train_u8, train_counts, _, _ = load_train_or_val("train", resolution)
    images = to_model_input(train_u8[:BATCH_SIZE], resolution, device)
    targets = torch.from_numpy(train_counts[:BATCH_SIZE]).to(device).float() / TARGET_SCALE
    model.train()
    loss = F.l1_loss(model(images).squeeze(1), targets)
    loss.backward()
    grad_norm = head.weight.grad.norm().item()

    expected = json.loads((RESULTS_DIR / "baselines_val.json").read_text(encoding="utf-8"))
    expected_mae = expected["models"]["mean"]["mae"]["point"]  # 25.85
    passed = (
        abs(val_mae - expected_mae) <= TOLERANCE
        and head.weight.abs().max().item() == 0.0
        and grad_norm > 0
    )
    return {
        "model": name,
        "val_mae_step0": val_mae,
        "expected_val_mae": expected_mae,
        "prediction_min_cells": float(val_pred.min()),
        "prediction_max_cells": float(val_pred.max()),
        "head_weight_max_abs": head.weight.abs().max().item(),
        "head_bias": head.bias.item(),
        "train_loss_cells": loss.item() * TARGET_SCALE,
        "head_weight_grad_norm": grad_norm,
        "result": "PASS" if passed else "FAIL",
    }


def main():
    if not torch.cuda.is_available():
        raise SystemExit("No GPU found.")
    device = torch.device("cuda")
    resolution = load_decision("resolution.json")["main_resolution"]

    results = []
    for name in ALL_MODELS:
        config = {"rules_version": RULES["version"], "model": name, "seed": SEED,
                  "resolution": resolution, "check": "init"}
        with tracked_run("env", name, config, notes="init check, no training") as run_dir:
            result = {"run_id": run_dir.name, **check_model(name, resolution, device)}
            (run_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        results.append(result)
        print(json.dumps(result, indent=2))

    summary = {
        "rules_version": RULES["version"],
        "tolerance_cells": TOLERANCE,
        "all_pass": all(r["result"] == "PASS" for r in results),
        "models": results,
    }
    text = json.dumps(summary, indent=2) + "\n"
    (RESULTS_DIR / "init_check.json").write_text(text, encoding="utf-8", newline="\n")
    print("ALL PASS" if summary["all_pass"] else "SOME FAIL")


if __name__ == "__main__":
    main()
