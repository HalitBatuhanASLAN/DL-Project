"""Energy saved by early stopping and by the image cache (section 11.5: "reported without extra
training").

(a) Early stopping. Every training run (category train, status ok) with max_steps = 3,000 that
    stopped before step 3,000. Saved = (3,000 - steps_run) x that run's energy per step, where
    energy per step = the run's whole measured energy / steps_run (so it includes start-up and the
    val evaluations, spread over the steps). g CO2eq uses the same run's emissions / energy.
    Read from runs/<run_id>/metrics.json and config.json; nothing is re-trained.

(b) Caching. Two measured runs, one after the other:
      1. tif_decode: read the 1,200 TRAIN TIFs listed in splits/splits.csv (nuclei stain, chosen
         blur levels) from data/raw and resize them with build_cache.build_split, the code that
         built the cache. Only the main resolution (128x96) is made, because a training run at
         128x96 needs only that one (build_cache made both resolutions in one pass).
      2. cache_load: load data/cache/train_128x96.npz with load_train_or_val, exactly as
         scripts/train.py does (including its SHA-256 check).
    Saving per training run, if TIFs were decoded at the start of every epoch instead of loading
    the cache once: passes x E(tif_decode) - E(cache_load), passes = ceil(steps_run / batches per
    epoch) of the seed-42 own_cnn run (batch 32, drop_last: 1,200 // 32 = 37 batches per epoch).
    The one-time cost of building the cache is listed next to it (run of build_cache.py).

    Both runs are short (a few seconds). A run shorter than 3 x measure_power_secs is flagged
    short_run (section 10): its energy is below the measurement resolution and is an estimate.
    The OS file cache may hold some TIFs already, which makes tif_decode faster than a cold read.

Only train files are opened. No test file, no val file, no image is displayed.

Output: results/savings.json. Three tracked runs, all category analysis.

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\savings.py
"""

import json
import math
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))  # Lets Python import build_cache.

from build_cache import build_split, parse_size  # noqa: E402 (the code that built the cache)
from src.carbon import INDEX_CSV, tracked_run  # noqa: E402
from src.common import RESULTS_DIR, RUNS_DIR, load_decision, load_rules, load_split_table  # noqa: E402
from src.data import load_train_or_val  # noqa: E402

SAVINGS_JSON = RESULTS_DIR / "savings.json"
BUDGET_STEPS = 3000
EPOCH_RUN = "20261110-231256_train_own_cnn_73cc"  # own_cnn (KirazNet) seed 42, the final model.
BUILD_CACHE_RUN = "20261105-225640_preprocess_none_851d"  # The build_cache.py run that wrote the cache.


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_numbers(run_dir):
    """Time and energy of a finished tracked run, from its metrics.json."""
    m = read_json(run_dir / "metrics.json")
    return {"run_id": run_dir.name, "duration_s": m["duration_s"], "energy_wh": m["energy_kwh"] * 1000,
            "g_co2eq": m["emissions_kg"] * 1000, "short_run": m["short_run"]}


def tif_decode(resolution, expected_hw):
    """Read and resize the train TIFs; returns the seconds spent and the number of images."""
    table = load_split_table()
    stain = load_decision("stain.json")["nuclei_stain"]
    levels = load_decision("blur_levels.json")["chosen_levels"]
    rows = table[(table["stain"] == stain) & table["blur"].isin(levels) & (table["split"] == "train")]
    rows = rows.sort_values(["count", "sample", "blur"])  # Same order as build_cache.py.
    if len(rows) != 1200 or set(rows["split"]) != {"train"}:
        raise SystemExit(f"Expected 1,200 train TIFs, found {len(rows)}")
    start = time.perf_counter()
    stacks = build_split(rows, {resolution: parse_size(resolution)}, expected_hw)
    seconds = time.perf_counter() - start
    return seconds, len(stacks[resolution])


def cache_load(resolution):
    """Load the train cache as scripts/train.py does; returns the seconds spent and the image count."""
    start = time.perf_counter()
    images, _, _, _ = load_train_or_val("train", resolution)
    seconds = time.perf_counter() - start
    return seconds, len(images)


def early_stopping_rows(index):
    """One row per training run that stopped before the 3,000-step budget."""
    rows = []
    for run_id in index[(index["category"] == "train") & (index["status"] == "ok")]["run_id"]:
        m = read_json(RUNS_DIR / run_id / "metrics.json")
        args = read_json(RUNS_DIR / run_id / "config.json")["args"]
        if args["max_steps"] != BUDGET_STEPS or m["steps_run"] >= BUDGET_STEPS:
            continue  # Ran the full budget, or had a different budget (the 600-step noise reference).
        wh_per_step = m["energy_kwh"] * 1000 / m["steps_run"]
        g_per_wh = m["emissions_kg"] / m["energy_kwh"]  # Carbon intensity used by that run.
        steps_saved = BUDGET_STEPS - m["steps_run"]
        rows.append({
            "run_id": run_id, "model": args["model"], "seed": args["seed"],
            "resolution": args["resolution"], "amp": args["amp"],
            "steps_run": m["steps_run"], "steps_not_run": steps_saved,
            "run_wh": m["energy_kwh"] * 1000, "mwh_per_step": wh_per_step * 1000,
            "wh_saved": steps_saved * wh_per_step, "g_co2eq_saved": steps_saved * wh_per_step * g_per_wh,
        })
    return rows


def main():
    rules = load_rules()
    resolution = load_decision("resolution.json")["main_resolution"]
    expected_hw = tuple(rules["data"]["expected_shape_hw"])
    batch_size = rules["training"]["batch_size"]

    # Run 1: decode the TIFs. Run 2: load the cache. Each is its own measured run.
    with tracked_run("analysis", "none", {"task": "savings_tif_decode", "resolution": resolution},
                     notes="savings: decode + resize 1,200 train TIFs") as decode_dir:
        seconds, n = tif_decode(resolution, expected_hw)
        (decode_dir / "metrics.json").write_text(json.dumps({"timed_s": seconds, "images": n}), encoding="utf-8")
    with tracked_run("analysis", "none", {"task": "savings_cache_load", "resolution": resolution},
                     notes="savings: load train cache") as load_dir:
        seconds, n = cache_load(resolution)
        (load_dir / "metrics.json").write_text(json.dumps({"timed_s": seconds, "images": n}), encoding="utf-8")

    # Run 3: the arithmetic, from files only.
    with tracked_run("analysis", "all_final", {"task": "savings_report"}, notes="results/savings.json"):
        index = pd.read_csv(INDEX_CSV)
        early = early_stopping_rows(index)

        decode, load = run_numbers(decode_dir), run_numbers(load_dir)
        decode["timed_s"] = read_json(decode_dir / "metrics.json")["timed_s"]
        load["timed_s"] = read_json(load_dir / "metrics.json")["timed_s"]
        epoch_run = read_json(RUNS_DIR / EPOCH_RUN / "metrics.json")
        batches_per_epoch = 1200 // batch_size  # drop_last (section 11.2).
        epochs = epoch_run["steps_run"] / batches_per_epoch
        passes = math.ceil(epochs)  # A started pass would need its images decoded.
        build = read_json(RUNS_DIR / BUILD_CACHE_RUN / "metrics.json")

        caching = {
            "resolution": resolution,
            "tif_decode": decode,
            "cache_load": load,
            "epoch_source_run": EPOCH_RUN,
            "steps_run": epoch_run["steps_run"],
            "batches_per_epoch": batches_per_epoch,
            "epochs": epochs,
            "passes_decoded": passes,
            "decode_every_epoch_wh": passes * decode["energy_wh"],
            "decode_every_epoch_s": passes * decode["duration_s"],
            "saving_per_training_run_wh": passes * decode["energy_wh"] - load["energy_wh"],
            "saving_per_training_run_g_co2eq": passes * decode["g_co2eq"] - load["g_co2eq"],
            "saving_per_training_run_s": passes * decode["duration_s"] - load["duration_s"],
            "build_cache_once": {"run_id": BUILD_CACHE_RUN, "wh": build["energy_kwh"] * 1000,
                                 "g_co2eq": build["emissions_kg"] * 1000, "duration_s": build["duration_s"],
                                 "note": "all 4 splits, both resolutions, one time"},
            "note": "short_run = energy below measurement resolution (section 10); an estimate",
        }
        savings = {
            "early_stopping": {
                "budget_steps": BUDGET_STEPS,
                "energy_per_step": "run energy / steps_run (includes start-up and val evaluations)",
                "runs": early,
                "total_steps_not_run": sum(r["steps_not_run"] for r in early),
                "total_wh_saved": sum(r["wh_saved"] for r in early),
                "total_g_co2eq_saved": sum(r["g_co2eq_saved"] for r in early),
            },
            "caching": caching,
        }
        SAVINGS_JSON.write_text(json.dumps(savings, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(savings, indent=2))


if __name__ == "__main__":
    main()
