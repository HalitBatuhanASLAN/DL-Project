"""Build the frozen train/val/test split, section 2 of docs/decision_rules.md.

Only file names are used; no image is opened.

Output: splits/splits.csv        one row per image, the source of truth
        splits/splits.sha256     hash of splits.csv
        results/split_summary.csv   one row per split

Run from anywhere with the project virtual environment:
    .venv\\Scripts\\python.exe scripts\\make_split.py
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, SPLITS_DIR, load_rules, sha256  # noqa: E402

SPLITS_CSV = SPLITS_DIR / "splits.csv"
SPLITS_HASH = SPLITS_DIR / "splits.sha256"
SUMMARY_CSV = RESULTS_DIR / "split_summary.csv"

SPLIT_NAMES = ["train", "val", "test_seen", "test_unseen"]
EXPECTED_SCENES = {"train": 300, "val": 100, "test_seen": 100, "test_unseen": 100}

# Same pattern as scripts/data_inventory.py, e.g. SIMCEPImages_B13_C53_F4_s11_w1.TIF
NAME_PATTERN = re.compile(r"^SIMCEPImages_[A-Z]\d{2}_C(\d+)_F(\d+)_s(\d+)_w(\d+)\.TIF$")


def list_images(raw_dir, expected_files):
    """Return a table with one row per image, built from the file names only."""
    rows = []
    for path in raw_dir.glob("*.TIF"):
        match = NAME_PATTERN.match(path.name)
        if match is None:
            raise SystemExit(f"Unexpected file name: {path.name}")
        count, blur, sample, stain = (int(value) for value in match.groups())
        rows.append(
            {
                "relative_path": path.relative_to(PROJECT_ROOT).as_posix(),
                "count": count,
                "blur": blur,
                "sample": sample,
                "stain": stain,
                "scene_id": f"C{count}_s{sample:02d}",  # A scene is (count, sample).
            }
        )
    if len(rows) != expected_files:
        raise SystemExit(f"Expected {expected_files} images, found {len(rows)}")
    # A fixed row order makes the file, and so its hash, reproducible.
    return pd.DataFrame(rows).sort_values(["count", "sample", "blur", "stain"], ignore_index=True)


def assign_splits(df, split_rules):
    """Add the split column. Returns the table and the samples of each split."""
    first_sample, last_sample = split_rules["samples"]
    rng = np.random.default_rng(split_rules["seed"])
    perm = rng.permutation(np.arange(first_sample, last_sample + 1))

    # One permutation shared by all counts.
    n_train = split_rules["n_train_samples"]
    n_val = split_rules["n_val_samples"]
    n_test = split_rules["n_test_samples"]
    train_samples = perm[:n_train].tolist()
    val_samples = perm[n_train : n_train + n_val].tolist()
    test_samples = perm[n_train + n_val : n_train + n_val + n_test].tolist()

    split_of_sample = {}
    for name, samples in [("train", train_samples), ("val", val_samples), ("test_seen", test_samples)]:
        for sample in samples:
            split_of_sample[sample] = name

    df = df.copy()
    df["split"] = df["sample"].map(split_of_sample)
    # Held-out counts override the sample rule: all their samples go to test_unseen.
    df.loc[df["count"].isin(split_rules["held_out_counts"]), "split"] = "test_unseen"
    return df, perm.tolist(), train_samples, val_samples, test_samples


def run_checks(df, held_out_counts):
    """Run the built-in checks. Returns a list of (description, passed)."""
    checks = []

    # a) No scene appears in two splits.
    splits_per_scene = df.groupby("scene_id")["split"].nunique()
    checks.append(("a) no scene appears in two splits", bool(splits_per_scene.max() == 1)))

    # b) Number of scenes in each split.
    scene_counts = df.groupby("split")["scene_id"].nunique().to_dict()
    checks.append((f"b) scene counts {scene_counts}", scene_counts == EXPECTED_SCENES))

    # c) Held-out counts appear only in test_unseen, and nothing else appears there.
    is_held_out = df["count"].isin(held_out_counts)
    is_unseen = df["split"] == "test_unseen"
    checks.append(("c) held-out counts only in test_unseen", bool((is_held_out == is_unseen).all())))

    # d) Within a split, every count x blur x stain cell holds the same number of images.
    cells = df.groupby(["split", "count", "blur", "stain"]).size()
    sizes_per_split = cells.groupby("split").nunique()
    checks.append(("d) cells balanced within each split", bool(sizes_per_split.max() == 1)))
    return checks


def summarise(df):
    """Return one row per split: scenes, images, and which counts and samples it has."""
    rows = []
    for name in SPLIT_NAMES:
        part = df[df["split"] == name]
        rows.append(
            {
                "split": name,
                "scenes": part["scene_id"].nunique(),
                "images": len(part),
                "n_counts": part["count"].nunique(),
                "n_samples": part["sample"].nunique(),
                "images_per_cell": part.groupby(["count", "blur", "stain"]).size().iloc[0],
                "counts": " ".join(str(value) for value in sorted(part["count"].unique())),
                "samples": " ".join(str(value) for value in sorted(part["sample"].unique())),
            }
        )
    return pd.DataFrame(rows)


def main():
    rules = load_rules()
    split_rules = rules["split"]
    raw_dir = PROJECT_ROOT / rules["data"]["raw_dir"]

    df = list_images(raw_dir, rules["data"]["expected_files"])
    df, perm, train_samples, val_samples, test_samples = assign_splits(df, split_rules)

    print(f"Sample permutation (seed {split_rules['seed']}): {perm}")
    print(f"Train samples    : {train_samples}")
    print(f"Val samples      : {val_samples}")
    print(f"Test samples     : {test_samples}")
    print(f"Held-out counts  : {split_rules['held_out_counts']}")
    print()

    checks = run_checks(df, split_rules["held_out_counts"])
    for description, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {description}")

    # Nothing is written unless every check passed. SystemExit marks the run as failed.
    if not all(passed for _, passed in checks):
        raise SystemExit("A split check failed; nothing was written.")

    SPLITS_DIR.mkdir(exist_ok=True)
    columns = ["relative_path", "count", "blur", "sample", "stain", "scene_id", "split"]
    # "\n" line endings on every system, so the hash does not depend on Windows.
    df[columns].to_csv(SPLITS_CSV, index=False, lineterminator="\n")
    SPLITS_HASH.write_text(f"{sha256(SPLITS_CSV)}  splits.csv\n", encoding="utf-8", newline="\n")

    summary = summarise(df)
    summary.to_csv(SUMMARY_CSV, index=False, lineterminator="\n")

    print()
    print(summary[["split", "scenes", "images", "images_per_cell"]].to_string(index=False))
    print()
    print(f"Saved {SPLITS_CSV.relative_to(PROJECT_ROOT).as_posix()} ({len(df)} rows)")
    print(f"SHA-256 {sha256(SPLITS_CSV)}")


if __name__ == "__main__":
    config = {"script": "scripts/make_split.py", "seed": load_rules()["split"]["seed"]}
    with tracked_run(category="preprocess", model="none", config=config):
        main()
