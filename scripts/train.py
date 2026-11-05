"""One training run, sections 11.2, 11.3 and 11.6 of the rules.

Data comes from the cache, train and val only; test files are refused (section 9).
Every model gets the same loss, optimiser, schedule, batch size and early stopping.

Output: checkpoints/<run_id>.pt                    best checkpoint (git-ignored)
        runs/<run_id>/eval_log.csv                 step, train_loss, val_mae, lr, elapsed_s
        runs/<run_id>/metrics.json                 best val MAE/RMSE/R2, stop step, steps run, ...
        results/val_predictions/<run_id>.csv       best checkpoint, one row per val image

Examples, after committing this script:
    .venv\\Scripts\\python.exe scripts\\train.py --model own_cnn --seed 42 --lr 1e-3
    .venv\\Scripts\\python.exe scripts\\train.py --model resnet18 --lr 1e-3 --amp
    .venv\\Scripts\\python.exe scripts\\train.py --model own_cnn --lr 1e-3 --max-steps 20 ^
        --eval-every 10 --category env --notes "smoke test"
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from src.data import load_train_or_val, save_predictions, to_model_input  # noqa: E402
from src.metrics import mae, r2, rmse  # noqa: E402
from src.models import ALL_MODELS, build_model, predict  # noqa: E402

RULES = load_rules()
TRAINING = RULES["training"]
STOPPING = TRAINING["early_stopping"]
FLIPS = RULES["preprocess"]["augmentation"]
TARGET_SCALE = RULES["preprocess"]["target_scale"]  # Target = count / 100.
BATCH_SIZE = TRAINING["batch_size"]
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
VAL_PREDICTIONS_DIR = RESULTS_DIR / "val_predictions"


def set_seeds(seed):
    """Fix every random source (section 11.2)."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def batch_indices(n_images, generator):
    """Yield index tensors forever: a new shuffle each pass, incomplete last batch dropped."""
    while True:
        order = torch.randperm(n_images, generator=generator, device=generator.device)
        for start in range(0, n_images - BATCH_SIZE + 1, BATCH_SIZE):
            yield order[start : start + BATCH_SIZE]


def random_flips(images, generator):
    """Flip each image of the batch on its own (section 6). images is N x 1 x H x W."""
    size = (len(images), 1, 1, 1)  # One decision per image, broadcast over C, H and W.
    flip_h = torch.rand(size, generator=generator, device=images.device) < FLIPS["hflip_p"]
    flip_v = torch.rand(size, generator=generator, device=images.device) < FLIPS["vflip_p"]
    images = torch.where(flip_h, images.flip(-1), images)  # Last axis: left <-> right.
    return torch.where(flip_v, images.flip(-2), images)  # Second-last axis: up <-> down.


def run_training(
    model_name, seed, lr, resolution, max_steps, amp=False, category="train", eval_every=None, notes=""
):
    """Do one tracked run and return its metrics.json as a dict. Also used by lr_search.py."""
    if not torch.cuda.is_available():
        raise SystemExit("No GPU found: section 11.2 keeps the data on the GPU.")
    device = torch.device("cuda")
    eval_every = eval_every or STOPPING["eval_every_steps"]
    config = {
        "rules_version": RULES["version"],
        "model": model_name,
        "seed": seed,
        "lr": lr,
        "resolution": resolution,
        "max_steps": max_steps,
        "amp": amp,
        "eval_every": eval_every,
    }

    with tracked_run(category=category, model=model_name, config=config, notes=notes) as run_dir:
        run_id = run_dir.name
        set_seeds(seed)
        torch.cuda.reset_peak_memory_stats()  # So the peak below belongs to this run only.

        # All images stay on the GPU as tensors; no workers (section 11.2).
        train_u8, train_counts, _, _ = load_train_or_val("train", resolution)
        val_u8, val_counts, val_blurs, val_scenes = load_train_or_val("val", resolution)
        train_x = to_model_input(train_u8, resolution, device)
        val_x = to_model_input(val_u8, resolution, device)
        train_y = torch.from_numpy(train_counts).to(device).float() / TARGET_SCALE
        val_counts = val_counts.astype(float)  # Metrics are in cells.

        model = build_model(model_name).to(device)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=lr, weight_decay=TRAINING["weight_decay"]
        )
        # Cosine from lr to 0 over the whole budget; early stopping does not shorten it.
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_steps, eta_min=0)
        scaler = torch.amp.GradScaler("cuda", enabled=amp)  # enabled=False: does nothing.

        # A separate generator: the batches and flips of a seed are the same for every model.
        generator = torch.Generator(device=device).manual_seed(seed)
        batches = batch_indices(len(train_x), generator)

        checkpoint_path = CHECKPOINT_DIR / f"{run_id}.pt"
        CHECKPOINT_DIR.mkdir(exist_ok=True)
        log_path = run_dir / "eval_log.csv"
        log_rows = []
        best_mae = float("inf")
        best_step = None
        counter = 0  # Evaluations since the last improvement (section 11.3).
        stopped_early = False
        losses_since_eval = []
        step_seconds = []
        eval_seconds = 0.0
        run_start = time.perf_counter()

        model.train()
        for step in range(1, max_steps + 1):
            step_start = time.perf_counter()
            current_lr = optimizer.param_groups[0]["lr"]  # The LR this step really uses.

            index = next(batches)
            images = random_flips(train_x[index], generator)
            with torch.autocast("cuda", enabled=amp):
                # squeeze(1): (N, 1) -> (N). Without it, l1_loss would broadcast to N x N.
                loss = F.l1_loss(model(images).squeeze(1), train_y[index])

            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            # .item() waits for the GPU, so the time below is the real time of this step.
            losses_since_eval.append(loss.item())
            step_seconds.append(time.perf_counter() - step_start)

            if step % eval_every == 0 or step == max_steps:
                eval_start = time.perf_counter()
                with torch.autocast("cuda", enabled=amp):
                    val_pred = predict(model, val_x, BATCH_SIZE).numpy()
                val_mae = mae(val_counts, val_pred)

                # Early stopping, section 11.3. best_mae is the value of the saved checkpoint.
                if val_mae <= best_mae - STOPPING["min_delta_cells"]:
                    best_mae, best_step, counter = val_mae, step, 0
                    torch.save(
                        {"state_dict": model.state_dict(), "step": step, "val_mae": val_mae, **config},
                        checkpoint_path,
                    )
                else:
                    counter += 1
                eval_seconds += time.perf_counter() - eval_start

                log_rows.append(
                    {
                        "step": step,
                        "train_loss": float(np.mean(losses_since_eval)),  # On count / 100.
                        "val_mae": val_mae,
                        "lr": current_lr,
                        "elapsed_s": time.perf_counter() - run_start,
                    }
                )
                losses_since_eval = []
                # Rewritten each time, so a crash keeps the log up to this evaluation.
                pd.DataFrame(log_rows).to_csv(log_path, index=False, lineterminator="\n")
                print(f"step {step:5d}  {log_rows[-1]}")

                can_stop = step >= STOPPING["no_stop_before_step"]
                if can_stop and counter >= STOPPING["patience_evals"]:
                    stopped_early = True
                    break

        # The saved checkpoint is the model (section 11.3): reload it and predict once more.
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
        model.load_state_dict(checkpoint["state_dict"])
        with torch.autocast("cuda", enabled=amp):
            best_pred = predict(model, val_x, BATCH_SIZE).numpy()

        save_predictions(
            VAL_PREDICTIONS_DIR / f"{run_id}.csv",
            model_name,
            val_scenes,
            val_counts.astype(int),
            val_blurs,
            best_pred,
        )

        metrics = {
            **config,
            "best_val_mae": mae(val_counts, best_pred),
            "best_val_rmse": rmse(val_counts, best_pred),
            "best_val_r2": r2(val_counts, best_pred),
            "best_val_mae_when_saved": best_mae,  # Must equal best_val_mae: reload check.
            "best_step": best_step,
            "stop_step": step,
            "steps_run": step,
            "stopped_early": stopped_early,
            "last_val_mae": val_mae,  # At the last step; this one decides the LR search.
            "train_seconds": float(np.sum(step_seconds)),
            "eval_seconds": eval_seconds,
            "median_step_seconds": float(np.median(step_seconds)),
            "gpu_peak_allocated_mib": torch.cuda.max_memory_allocated() / 1024**2,
            "gpu_peak_reserved_mib": torch.cuda.max_memory_reserved() / 1024**2,
            "checkpoint": str(checkpoint_path.relative_to(PROJECT_ROOT)),
        }
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    torch.cuda.empty_cache()  # Frees the GPU memory for the next trial of lr_search.py.
    # Read back, because tracked_run has now added duration and energy to this file.
    return json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="One training run (section 11.2-11.3).")
    parser.add_argument("--model", required=True, choices=ALL_MODELS)
    parser.add_argument("--seed", type=int, default=RULES["models"]["final_seed"])
    parser.add_argument("--lr", type=float, required=True)
    parser.add_argument("--resolution", default=load_decision("resolution.json")["main_resolution"])
    parser.add_argument("--max-steps", type=int, default=TRAINING["max_steps"])
    parser.add_argument("--amp", action="store_true", help="mixed precision (section 11.5 only)")
    parser.add_argument("--category", default="train", choices=["train", "search", "env"])
    parser.add_argument("--eval-every", type=int, default=STOPPING["eval_every_steps"])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    metrics = run_training(
        args.model,
        args.seed,
        args.lr,
        args.resolution,
        args.max_steps,
        args.amp,
        args.category,
        args.eval_every,
        args.notes,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
