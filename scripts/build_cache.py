"""Build the image cache, section 6 of the rules. One run makes both resolutions.

Why one run: the ablation needs the same images, and one read of the TIFs is cheaper than two.
Both resolutions are resized directly from the native image.

Input:  splits/splits.csv, results/decisions/{stain,resolution,blur_levels}.json
Output: data/cache/{split}_{WxH}.npz     images (uint8, N x H x W), count, blur, scene_id
        results/norm_stats.json          mean and std per resolution, TRAIN pixels only
        results/cache_manifest.json      file names, shapes, SHA-256, image counts, checks

Test images are read here only to resize and store them. Nothing about their pixels is printed
or used for any choice.

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\build_cache.py
"""

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import (  # noqa: E402
    RESULTS_DIR,
    load_decision,
    load_rules,
    load_split_table,
    read_tif,
    resize_box,
    sha256,
)

CACHE_DIR = PROJECT_ROOT / "data" / "cache"
NORM_STATS_JSON = RESULTS_DIR / "norm_stats.json"
MANIFEST_JSON = RESULTS_DIR / "cache_manifest.json"
SPLITS = ["train", "val", "test_seen", "test_unseen"]
EXPECTED_IMAGES = {"train": 1200, "val": 400, "test_seen": 400, "test_unseen": 400}


def parse_size(name):
    """Turn "128x96" into the tuple (128, 96), which is (width, height)."""
    width, height = name.split("x")
    return int(width), int(height)


def cache_path(split, resolution):
    """Return the path of one cache file, e.g. data/cache/train_128x96.npz."""
    return CACHE_DIR / f"{split}_{resolution}.npz"


def build_split(rows, sizes, expected_hw):
    """Read the images of one split once; return {resolution: uint8 array N x H x W}."""
    stacks = {name: np.zeros((len(rows), h, w), dtype=np.uint8) for name, (w, h) in sizes.items()}
    for i, relative_path in enumerate(rows["relative_path"]):
        native = read_tif(PROJECT_ROOT / relative_path)
        # Section 1: any file that differs means stop.
        if native.shape != expected_hw or native.dtype != np.uint8:
            raise SystemExit(f"Unexpected image {relative_path}: {native.shape}, {native.dtype}")
        for name, size_wh in sizes.items():
            stacks[name][i] = resize_box(native, size_wh)
    return stacks


def report(checks, name, passed):
    """Print one check as PASS or FAIL and remember it."""
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    checks[name] = bool(passed)


def check_scenes(scene_ids, blurs, levels):
    """Return True if every scene has exactly one image per chosen blur level."""
    for scene in np.unique(scene_ids):
        if sorted(blurs[scene_ids == scene].tolist()) != sorted(levels):
            return False
    return True


def check_file(checks, split, resolution, levels, expected_shape):
    """Run the checks on one file as it was written to disk. Returns its manifest entry."""
    path = cache_path(split, resolution)
    with np.load(path) as cache:  # No pickle: scene_id is a plain string array.
        images, counts, blurs, scene_ids = (
            cache["images"],
            cache["count"],
            cache["blur"],
            cache["scene_id"],
        )

    label = f"{split}_{resolution}"
    report(checks, f"{label}: {EXPECTED_IMAGES[split]} images", len(images) == EXPECTED_IMAGES[split])
    report(checks, f"{label}: shape N x H x W", images.shape[1:] == expected_shape)
    report(checks, f"{label}: dtype uint8", images.dtype == np.uint8)
    report(checks, f"{label}: 4 images per scene, one per level", check_scenes(scene_ids, blurs, levels))
    # uint8 pixels cannot be NaN, so the labels are the part that could really fail here.
    no_nan = not (np.isnan(images.astype(float)).any() or np.isnan(counts.astype(float)).any())
    report(checks, f"{label}: no NaN", no_nan)

    return {
        "file": path.name,
        "split": split,
        "resolution": resolution,
        "images_shape": list(images.shape),
        "n_images": len(images),
        "n_scenes": int(len(np.unique(scene_ids))),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def train_pixel_stats(resolution):
    """Return mean and std of x = u8 / 255 over all train pixels (section 6)."""
    with np.load(cache_path("train", resolution)) as cache:
        pixels = cache["images"] / 255.0
    return {"mean": float(pixels.mean()), "std": float(pixels.std()), "n_pixels": int(pixels.size)}


def write_json(path, data):
    """Write a JSON file with stable formatting."""
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    rules = load_rules()
    table = load_split_table()
    stain = load_decision("stain.json")["nuclei_stain"]
    resolution = load_decision("resolution.json")
    levels = load_decision("blur_levels.json")["chosen_levels"]
    main_name, ablation_name = resolution["main_resolution"], resolution["ablation_resolution"]
    sizes = {name: parse_size(name) for name in (main_name, ablation_name)}
    expected_hw = tuple(rules["data"]["expected_shape_hw"])
    print(f"Stain w{stain}, blur levels {levels}, resolutions {list(sizes)}")

    config = {
        "rules_version": rules["version"],
        "stain": stain,
        "blur_levels": levels,
        "resolutions": list(sizes),
    }
    with tracked_run(category="preprocess", model="none", config=config):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        chosen = table[(table["stain"] == stain) & table["blur"].isin(levels)]

        for split in SPLITS:
            rows = chosen[chosen["split"] == split].sort_values(["count", "sample", "blur"])
            print(f"Reading {split}: {len(rows)} images")
            stacks = build_split(rows, sizes, expected_hw)
            for name, images in stacks.items():
                np.savez(
                    cache_path(split, name),
                    images=images,
                    count=rows["count"].to_numpy(dtype=np.int64),
                    blur=rows["blur"].to_numpy(dtype=np.int64),
                    # dtype=str gives a plain string array that loads without pickle.
                    scene_id=np.array(rows["scene_id"].tolist(), dtype=str),
                )

        # All checks read the files back, so they test what is on disk.
        checks = {}
        files = []
        for name, (width, height) in sizes.items():
            for split in SPLITS:
                files.append(check_file(checks, split, name, levels, (height, width)))

        expected_mean = rules["baselines"]["mean"]["expected_train_mean"]
        with np.load(cache_path("train", main_name)) as cache:
            train_mean = float(cache["count"].mean())
        report(checks, f"train mean target = {expected_mean}", round(train_mean, 2) == expected_mean)

        norm_stats = {name: train_pixel_stats(name) for name in sizes}
        write_json(
            NORM_STATS_JSON,
            {
                "rules_version": rules["version"],
                "definition": "x = (u8/255 - mean) / std, over all train pixels",
                "resolutions": norm_stats,
            },
        )
        write_json(
            MANIFEST_JSON,
            {
                "rules_version": rules["version"],
                "nuclei_stain": stain,
                "blur_levels": levels,
                "main_resolution": main_name,
                "ablation_resolution": ablation_name,
                "resize": rules["resolution"]["resize"],
                "cache_dir": "data/cache",
                "files": files,
                "all_checks_passed": all(checks.values()),
                "checks": checks,
            },
        )

        print(f"\n{sum(checks.values())} of {len(checks)} checks passed")
        for name, stats in norm_stats.items():
            print(f"Norm stats {name}: mean {stats['mean']:.6f}, std {stats['std']:.6f}")
        total_mb = sum(entry["size_bytes"] for entry in files) / 1024**2
        print(f"Cache on disk: {total_mb:.1f} MiB")

        # Inside the tracked block, so that a failed check gives a run with status "failed".
        if not all(checks.values()):
            raise SystemExit("At least one cache check failed.")


if __name__ == "__main__":
    main()
