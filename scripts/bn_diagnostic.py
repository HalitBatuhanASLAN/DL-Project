"""Post-hoc BatchNorm diagnostic. NOT pre-registered and NOT used for any choice.

Question: is part of a model's val error caused by BatchNorm running statistics that lag behind
the weights (they are an exponential average collected while the weights were still changing)?

For one saved checkpoint:
  1. val MAE with the checkpoint as saved ("before"; must equal best_val_mae of the run).
  2. Reset every BatchNorm running mean/variance and recompute them with ONE pass over the
     train cache: train mode, no gradient, no optimiser, no flips, batches of 32 in cache order.
     momentum=None makes BatchNorm keep a plain average over the batches instead of an
     exponential one, so every train batch counts the same.
  3. Check that no weight changed, then val MAE again ("after").

The recalibrated weights are NOT saved; the checkpoint stays the final model (section 11.3).
Train and val only; test files are refused (section 9).

Output: results/bn_diagnostic/<run_id of the checkpoint>.json

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\bn_diagnostic.py --checkpoint checkpoints\\<run_id>.pt
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from torch import nn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, RUNS_DIR  # noqa: E402
from src.data import load_train_or_val, to_model_input  # noqa: E402
from src.metrics import mae, r2, rmse  # noqa: E402
from src.models import build_model, predict  # noqa: E402

BATCH_SIZE = 32
OUT_DIR = RESULTS_DIR / "bn_diagnostic"


def val_metrics(model, val_x, val_counts):
    """MAE, RMSE and R2 on val in cells, eval mode (predict() switches to eval mode)."""
    pred = predict(model, val_x, BATCH_SIZE).numpy()
    return {"mae": mae(val_counts, pred), "rmse": rmse(val_counts, pred), "r2": r2(val_counts, pred)}


@torch.no_grad()
def recompute_bn_statistics(model, train_x):
    """Replace the BN running statistics by their plain average over one pass of train_x."""
    bn_layers = [m for m in model.modules() if isinstance(m, nn.modules.batchnorm._BatchNorm)]
    for bn in bn_layers:
        bn.reset_running_stats()  # mean 0, var 1, num_batches_tracked 0
        bn.momentum = None  # None = cumulative average instead of exponential average.
    model.train()  # Train mode: BN normalises with batch statistics and updates its running ones.
    for start in range(0, len(train_x), BATCH_SIZE):  # All images, the last batch may be smaller.
        model(train_x[start : start + BATCH_SIZE])
    model.eval()
    return len(bn_layers)


def main():
    parser = argparse.ArgumentParser(description="Post-hoc BN diagnostic for one checkpoint.")
    parser.add_argument("--checkpoint", required=True, help="checkpoints/<run_id>.pt")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("No GPU found.")
    device = torch.device("cuda")
    checkpoint_path = Path(args.checkpoint)
    source_run = checkpoint_path.stem  # The checkpoint is named after its training run.
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model_name, resolution = checkpoint["model"], checkpoint["resolution"]
    config = {"checkpoint": str(checkpoint_path), "source_run": source_run, "model": model_name,
              "resolution": resolution, "seed": checkpoint["seed"], "batch_size": BATCH_SIZE}

    with tracked_run("analysis", model_name, config, notes="post-hoc BN diagnostic") as run_dir:
        train_u8, _, _, _ = load_train_or_val("train", resolution)
        val_u8, val_counts, _, _ = load_train_or_val("val", resolution)
        train_x = to_model_input(train_u8, resolution, device)
        val_x = to_model_input(val_u8, resolution, device)
        val_counts = val_counts.astype(float)

        # pretrained=False: every weight comes from the checkpoint anyway.
        model = build_model(model_name, pretrained=False).to(device)
        model.load_state_dict(checkpoint["state_dict"])
        before = val_metrics(model, val_x, val_counts)

        # Copy of every trainable weight, to prove afterwards that none of them changed.
        weights_before = {name: p.detach().clone() for name, p in model.named_parameters()}
        n_bn = recompute_bn_statistics(model, train_x)
        unchanged = all(torch.equal(p, weights_before[name]) for name, p in model.named_parameters())
        if not unchanged:
            raise SystemExit("A weight changed: the diagnostic is invalid.")
        after = val_metrics(model, val_x, val_counts)

        # The training run's own value, to confirm "before" reproduces it.
        run_metrics = json.loads((RUNS_DIR / source_run / "metrics.json").read_text(encoding="utf-8"))
        result = {
            **config,
            "pre_registered": False,
            "used_for_choices": False,
            "n_batchnorm_layers": n_bn,
            "n_train_images": len(train_x),
            "weights_unchanged": unchanged,
            "best_val_mae_of_run": run_metrics["best_val_mae"],
            "val_before": before,
            "val_after": after,
            "mae_change": after["mae"] - before["mae"],
            "recalibrated_weights_saved": False,
        }
        (run_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        text = json.dumps(result, indent=2) + "\n"
        (OUT_DIR / f"{source_run}.json").write_text(text, encoding="utf-8", newline="\n")
        print(text)


if __name__ == "__main__":
    main()
