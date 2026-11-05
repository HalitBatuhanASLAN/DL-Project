"""Access to the image cache, shared by the scripts, section 6 and section 9 of the rules.

Training, search and measurement scripts use load_train_or_val(), which refuses test files.
Only scripts/evaluate_test.py may call read_cache() for a test split (section 9).
"""

import json

import numpy as np
import pandas as pd

from src.common import PROJECT_ROOT, RESULTS_DIR, sha256

CACHE_DIR = PROJECT_ROOT / "data" / "cache"
MANIFEST_JSON = RESULTS_DIR / "cache_manifest.json"
NORM_STATS_JSON = RESULTS_DIR / "norm_stats.json"


def read_cache(split, resolution):
    """Read one cache file after checking its SHA-256. Has no guard: see load_train_or_val."""
    path = CACHE_DIR / f"{split}_{resolution}.npz"
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    expected = {entry["file"]: entry["sha256"] for entry in manifest["files"]}[path.name]
    if sha256(path) != expected:
        raise SystemExit(f"{path.name} does not match results/cache_manifest.json")
    with np.load(path) as cache:  # No pickle: scene_id is a plain string array.
        return cache["images"], cache["count"], cache["blur"], cache["scene_id"]


def load_train_or_val(split, resolution):
    """Same as read_cache, but refuses every split except train and val (section 9)."""
    if split not in ("train", "val"):
        raise SystemExit(f"Refused: {split} may only be opened by scripts/evaluate_test.py")
    return read_cache(split, resolution)


def load_norm_stats(resolution):
    """Return (mean, std) of the train pixels at this resolution (section 6)."""
    stats = json.loads(NORM_STATS_JSON.read_text(encoding="utf-8"))["resolutions"][resolution]
    return stats["mean"], stats["std"]


def save_predictions(path, model, scene_ids, counts, blurs, predictions):
    """Write one row per image: model, scene_id, count, blur, prediction (in cells)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(
        {
            "model": model,  # One name, repeated on every row.
            "scene_id": scene_ids,
            "count": counts,
            "blur": blurs,
            "prediction": predictions,
        }
    )
    table.to_csv(path, index=False, lineterminator="\n")
