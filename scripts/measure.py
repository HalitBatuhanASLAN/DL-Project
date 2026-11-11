"""Latency and energy per 1,000 predictions of one model, section 11.7 of the rules.

All on val images, category measure. Every prediction starts from the cached uint8 image, so the
normalisation of the CNNs and the mean pixel of the brightness baseline are both counted.
The mean baseline "predicts" by returning the train mean, so it measures the loop and the machine.

Latency (CPU for every model, GPU for the CNNs): eval mode, no_grad, batch size 1, 200 warm-up
passes, then 5 repeats of 1,000 timed passes. Reported: median and p95.

Energy per 1,000 predictions (CPU for every model, GPU for the CNNs): a 60 s idle measurement, then
3 repeats of a loop of at least 60 s, each repeat its own tracked run.
    gross = energy of the repeat / predictions * 1000
    net   = (energy of the repeat - idle power * duration of the repeat) / predictions * 1000
The energy ratio in the report uses CPU gross.

One model per call takes about 8 minutes for a CNN and 4 minutes for a baseline.

Output: results/measure/<model>.json

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\measure.py --model brightness
    .venv\\Scripts\\python.exe scripts\\measure.py --model own_cnn --checkpoint checkpoints\\<run_id>.pt
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_decision, load_rules  # noqa: E402
from src.data import load_norm_stats, load_train_or_val  # noqa: E402
from src.models import ALL_MODELS, build_model  # noqa: E402

RULES = load_rules()
LATENCY = RULES["measurement"]["latency"]
ENERGY = RULES["measurement"]["energy_per_1000"]
OUT_DIR = RESULTS_DIR / "measure"
BRIGHTNESS_JSON = RESULTS_DIR / "baselines" / "brightness_params.json"
BASELINES_JSON = RESULTS_DIR / "baselines_val.json"  # Holds the train mean (50.05).
BASELINES = ["mean", "brightness"]
CPU_THREADS = 4  # Fixed for every model (section 11.7).
KWH_PER_KW_SECOND = 1 / 3600


def sync(device):
    """Wait until the GPU has finished, so a timer read is honest (section 11.7)."""
    if device.type == "cuda":
        torch.cuda.synchronize()


def load_val_images(resolution, device):
    """Return the val images as uint8 tensors N x H x W on the device."""
    images, _, _, _ = load_train_or_val("val", resolution)
    return torch.from_numpy(images).to(device)


def make_predictor(name, checkpoint_path, resolution, device):
    """Return a function that turns one uint8 image into one prediction."""
    if name == "mean":
        train_mean = json.loads(BASELINES_JSON.read_text(encoding="utf-8"))["train_mean"]
        return lambda image: train_mean  # Same answer for every image (section 7).
    if name == "brightness":
        params = json.loads(BRIGHTNESS_JSON.read_text(encoding="utf-8"))
        return lambda image: params["a"] + params["b"] * image.float().mean()

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint["model"] != name or checkpoint["resolution"] != resolution:
        raise SystemExit("The checkpoint is a different model or resolution than the arguments.")
    model = build_model(name, pretrained=False).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    mean, std = load_norm_stats(resolution)
    # image[None, None] adds the batch and channel axes: H x W -> 1 x 1 x H x W.
    return lambda image: model((image[None, None].float() / 255 - mean) / std)


def timed_passes(predict_one, images, n_passes, device):
    """Return the time of each pass in milliseconds."""
    times = []
    for i in range(n_passes):
        image = images[i % len(images)]  # Cycles through the val images.
        sync(device)
        start = time.perf_counter()
        predict_one(image)
        sync(device)
        times.append((time.perf_counter() - start) * 1000)
    return np.array(times)


def measure_latency(name, checkpoint, resolution, device):
    """Return median and p95 latency in ms: one value per repeat, and their median."""
    config = {"task": "latency", "device": device.type, "threads": CPU_THREADS, "resolution": resolution}
    with tracked_run("measure", name, config, notes=f"latency {device.type}") as run_dir:
        with torch.no_grad():
            images = load_val_images(resolution, device)
            predict_one = make_predictor(name, checkpoint, resolution, device)
            timed_passes(predict_one, images, LATENCY["warmup_passes"], device)
            repeats = [
                timed_passes(predict_one, images, LATENCY["timed_passes"], device)
                for _ in range(LATENCY["repeats"])
            ]
        result = {
            "median_ms_per_repeat": [float(np.median(times)) for times in repeats],
            "p95_ms_per_repeat": [float(np.percentile(times, 95)) for times in repeats],
        }
        result["median_ms"] = float(np.median(result["median_ms_per_repeat"]))
        result["p95_ms"] = float(np.median(result["p95_ms_per_repeat"]))
        (run_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def measure_idle(name):
    """Return the idle power in kW over 60 s, with the same tracker as the loops."""
    config = {"task": "idle", "seconds": ENERGY["idle_s"]}
    with tracked_run("measure", name, config, notes="idle before energy loops") as run_dir:
        time.sleep(ENERGY["idle_s"])
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    return metrics["energy_kwh"] / (metrics["duration_s"] * KWH_PER_KW_SECOND)


def energy_repeat(name, checkpoint, resolution, device, repeat, idle_kw):
    """Run one loop of at least 60 s and return gross and net kWh per 1,000 predictions."""
    config = {
        "task": "energy",
        "device": device.type,
        "threads": CPU_THREADS,
        "resolution": resolution,
        "repeat": repeat,
    }
    notes = f"energy {device.type}, repeat {repeat}"
    with tracked_run("measure", name, config, notes=notes) as run_dir:
        with torch.no_grad():
            images = load_val_images(resolution, device)
            predict_one = make_predictor(name, checkpoint, resolution, device)
            n_predictions = 0
            start = time.perf_counter()
            while time.perf_counter() - start < ENERGY["min_loop_s"]:
                predict_one(images[n_predictions % len(images)])
                n_predictions += 1
            sync(device)
        (run_dir / "metrics.json").write_text(
            json.dumps({"n_predictions": n_predictions}), encoding="utf-8"
        )

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    idle_kwh = idle_kw * metrics["duration_s"] * KWH_PER_KW_SECOND
    return {
        "run_id": run_dir.name,
        "n_predictions": n_predictions,
        "duration_s": metrics["duration_s"],
        "energy_kwh": metrics["energy_kwh"],
        "gross_kwh_per_1000": metrics["energy_kwh"] / n_predictions * 1000,
        "net_kwh_per_1000": (metrics["energy_kwh"] - idle_kwh) / n_predictions * 1000,
    }


def main():
    parser = argparse.ArgumentParser(description="Latency and energy of one model (section 11.7).")
    parser.add_argument("--model", required=True, choices=ALL_MODELS + BASELINES)
    parser.add_argument("--checkpoint", help="required for a CNN")
    parser.add_argument("--resolution", default=load_decision("resolution.json")["main_resolution"])
    args = parser.parse_args()
    if args.model not in BASELINES and not args.checkpoint:
        raise SystemExit("A CNN needs --checkpoint.")

    torch.set_num_threads(CPU_THREADS)
    devices = [torch.device("cpu")]
    if args.model not in BASELINES:  # GPU only for the CNNs (section 11.7).
        devices.append(torch.device("cuda"))

    result = {
        "rules_version": RULES["version"],
        "model": args.model,
        "resolution": args.resolution,
        "checkpoint": args.checkpoint,
        "cpu_threads": CPU_THREADS,
        "idle_kw": measure_idle(args.model),
        "latency": {},
        "energy": {},
    }
    for device in devices:
        result["latency"][device.type] = measure_latency(
            args.model, args.checkpoint, args.resolution, device
        )
        repeats = [
            energy_repeat(args.model, args.checkpoint, args.resolution, device, r, result["idle_kw"])
            for r in range(1, ENERGY["repeats"] + 1)
        ]
        result["energy"][device.type] = {
            "repeats": repeats,
            "median_gross_kwh_per_1000": float(np.median([r["gross_kwh_per_1000"] for r in repeats])),
            "median_net_kwh_per_1000": float(np.median([r["net_kwh_per_1000"] for r in repeats])),
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2) + "\n"
    (OUT_DIR / f"{args.model}.json").write_text(text, encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    main()
