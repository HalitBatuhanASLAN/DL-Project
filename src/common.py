"""Small helpers shared by all scripts: paths, rules, image I/O, Otsu, hashing."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

# Paths are built from this file's location, so the working directory does not matter.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = PROJECT_ROOT / "configs" / "rules.json"
RUNS_DIR = PROJECT_ROOT / "runs"
RESULTS_DIR = PROJECT_ROOT / "results"
SPLITS_DIR = PROJECT_ROOT / "splits"


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


def sha256(path):
    """Return the SHA-256 hex digest of a file, read in 1 MB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
