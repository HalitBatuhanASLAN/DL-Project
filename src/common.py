"""Small helpers shared by all scripts: paths, rules, image I/O, Otsu, hashing."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage

# Paths are built from this file's location, so the working directory does not matter.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = PROJECT_ROOT / "configs" / "rules.json"
RUNS_DIR = PROJECT_ROOT / "runs"
RESULTS_DIR = PROJECT_ROOT / "results"
SPLITS_DIR = PROJECT_ROOT / "splits"
DECISIONS_DIR = RESULTS_DIR / "decisions"
VISUAL_DIR = RESULTS_DIR / "visual_check"


def load_rules():
    """Return the frozen design rules from configs/rules.json as a dict."""
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def read_tif(path):
    """Read one TIF file and return its pixels as a numpy array."""
    with Image.open(path) as image:
        return np.asarray(image)


def resize_box(image, size_wh):
    """Resize a uint8 array with BOX (area averaging). size_wh is (width, height)."""
    resized = Image.fromarray(image).resize(size_wh, Image.Resampling.BOX)
    return np.asarray(resized)


def otsu(image):
    """Return the Otsu threshold of an image; foreground is pixel > threshold.

    Otsu tries every split of a 256-bin histogram and keeps the split with the
    largest between-class variance. A constant image has no valid split and raises
    ValueError.
    """
    image = np.asarray(image)
    # For uint8 each bin holds exactly one grey value; otherwise bins span min..max.
    if image.dtype == np.uint8:
        value_range = (0, 256)
    else:
        value_range = (float(image.min()), float(image.max()))
    hist, edges = np.histogram(image, bins=256, range=value_range)
    centers = (edges[:-1] + edges[1:]) / 2

    # For a split after bin i: background = bins 0..i, foreground = bins i+1..255.
    weight_bg = np.cumsum(hist)  # Number of background pixels.
    weight_fg = weight_bg[-1] - weight_bg  # Number of foreground pixels.
    sum_bg = np.cumsum(hist * centers)  # Sum of background values.
    sum_fg = sum_bg[-1] - sum_bg  # Sum of foreground values.

    # A split with an empty class divides by zero; that gives NaN, skipped by nanargmax.
    with np.errstate(divide="ignore", invalid="ignore"):
        between_variance = weight_bg * weight_fg * (sum_bg / weight_bg - sum_fg / weight_fg) ** 2
    return float(centers[np.nanargmax(between_variance)])


def largest_component(mask):
    """Return the largest connected component of a boolean mask.

    scipy's default structure is 4-connectivity (diagonal pixels are not neighbours).
    """
    labels, n_components = ndimage.label(mask)
    if n_components == 0:
        raise ValueError("The mask is empty.")
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0  # Label 0 is the background.
    return labels == sizes.argmax()


def load_split_table():
    """Return splits/splits.csv after checking it against splits/splits.sha256."""
    splits_csv = SPLITS_DIR / "splits.csv"
    expected = (SPLITS_DIR / "splits.sha256").read_text(encoding="utf-8").split()[0]
    if sha256(splits_csv) != expected:
        raise SystemExit("splits/splits.csv does not match splits/splits.sha256")
    return pd.read_csv(splits_csv)


def first_training_samples(table, k):
    """Return the k smallest train sample indices (section 2 of the rules)."""
    return sorted(table.loc[table["split"] == "train", "sample"].unique().tolist())[:k]


def seen_counts(table):
    """Return the 20 seen counts: the counts that appear in train."""
    return sorted(table.loc[table["split"] == "train", "count"].unique().tolist())


def read_training_image(table, count, blur, sample, stain):
    """Read one image. Refuses anything outside train, so no check can peek at test."""
    row = table[
        (table["count"] == count)
        & (table["blur"] == blur)
        & (table["sample"] == sample)
        & (table["stain"] == stain)
    ]
    if len(row) != 1 or row["split"].iloc[0] != "train":
        raise SystemExit(f"Not a training image: C{count} F{blur} s{sample} w{stain}")
    return read_tif(PROJECT_ROOT / row["relative_path"].iloc[0])


def load_decision(name):
    """Return results/decisions/<name>; stops if the previous check has not run."""
    path = DECISIONS_DIR / name
    if not path.exists():
        raise SystemExit(f"Missing {path.name}: run the previous check first.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_decision(name, decision):
    """Write results/decisions/<name> with stable formatting."""
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(decision, indent=2) + "\n"
    (DECISIONS_DIR / name).write_text(text, encoding="utf-8", newline="\n")


def sha256(path):
    """Return the SHA-256 hex digest of a file, read in 1 MB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
