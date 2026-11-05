"""Check F (file sanity) and check A (stain identity), sections 1, 3 and 9 of the rules.

Check F reads all 19,200 files, test files included, for aggregate statistics only.
No test image is displayed or used for any choice (documented exception, section 9).
Check A reads C1 F1 of the first 2 training samples, both stains.

Output: results/decisions/stain.json         nuclei stain and all measured numbers
        results/visual_check/file_sanity.csv one row per stain x split
        results/visual_check/stain_overlay.png

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\check_stain.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Writes files only, opens no window.
import matplotlib.pyplot as plt  # noqa: E402 (backend must be set first)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import (  # noqa: E402
    VISUAL_DIR,
    first_training_samples,
    largest_component,
    load_rules,
    load_split_table,
    otsu,
    read_tif,
    read_training_image,
    save_decision,
)

SANITY_CSV = VISUAL_DIR / "file_sanity.csv"
OVERLAY_PNG = VISUAL_DIR / "stain_overlay.png"
SPLIT_NAMES = ["train", "val", "test_seen", "test_unseen"]
ZOOM_HALF_SIZE = 80  # Half width of the zoomed overlay, in native pixels.


def check_files(table, data_rules):
    """Check F: return (bad files, one statistics row per stain x split)."""
    expected_shape = tuple(data_rules["expected_shape_hw"])
    expected_dtype = data_rules["expected_dtype"]
    bad_files = []
    rows = []

    for stain in sorted(table["stain"].unique()):
        for split in SPLIT_NAMES:
            part = table[(table["stain"] == stain) & (table["split"] == split)]
            hist = np.zeros(256, dtype=np.int64)  # Pixel count per grey value.
            medians = []
            for relative_path in part["relative_path"]:
                image = read_tif(PROJECT_ROOT / relative_path)
                if image.shape != expected_shape or image.dtype != expected_dtype:
                    bad_files.append(f"{relative_path}: {image.shape} {image.dtype}")
                    continue
                hist += np.bincount(image.ravel(), minlength=256)
                medians.append(float(np.median(image)))

            n_pixels = hist.sum()
            used_values = np.flatnonzero(hist)
            rows.append(
                {
                    "stain": int(stain),
                    "split": split,
                    "files": len(part),
                    "min": int(used_values[0]),
                    "max": int(used_values[-1]),
                    "mean": float((hist * np.arange(256)).sum() / n_pixels),
                    "mean_of_medians": float(np.mean(medians)),
                    "pct_pixels_at_0": float(100 * hist[0] / n_pixels),
                    "pct_pixels_at_255": float(100 * hist[255] / n_pixels),
                }
            )
            print(f"Check F: w{stain} {split} done ({len(part)} files)")
    return bad_files, rows


def largest_object(image):
    """Otsu threshold (foreground = pixel > t), then the largest connected component."""
    threshold = otsu(image)
    return threshold, largest_component(image > threshold)


def measure_sample(table, sample, stain_rules):
    """Check A for one sample: return the numbers, the images and the masks."""
    count, blur = stain_rules["count"], stain_rules["blur"]
    image_1 = read_training_image(table, count, blur, sample, 1)
    image_2 = read_training_image(table, count, blur, sample, 2)
    threshold_1, mask_1 = largest_object(image_1)
    threshold_2, mask_2 = largest_object(image_2)

    area_1 = int(mask_1.sum())
    area_2 = int(mask_2.sum())
    overlap = int((mask_1 & mask_2).sum())
    numbers = {
        "sample": sample,
        "otsu_w1": threshold_1,
        "otsu_w2": threshold_2,
        "area_w1": area_1,
        "area_w2": area_2,
        "overlap": overlap,
        "containment_w1_in_w2": overlap / area_1,
        "containment_w2_in_w1": overlap / area_2,
        "area_ratio_w1_over_w2": area_1 / area_2,
        "area_ratio_w2_over_w1": area_2 / area_1,
    }
    return numbers, (image_1, image_2), (mask_1, mask_2)


def channel_passes(measurements, x, y, stain_rules):
    """True if channel x is the nuclei channel in every sample: inside y and smaller."""
    return all(
        m[f"containment_w{x}_in_w{y}"] >= stain_rules["min_containment"]
        and m[f"area_ratio_w{x}_over_w{y}"] <= stain_rules["max_area_ratio"]
        for m in measurements
    )


def draw_overlay(panels):
    """Save one row per sample: w1, w2, and a zoom with both object outlines."""
    fig, axes = plt.subplots(len(panels), 3, figsize=(11, 3.1 * len(panels)), squeeze=False)
    for row, (sample, (image_1, image_2), (mask_1, mask_2)) in zip(axes, panels):
        row[0].imshow(image_1, cmap="gray")
        row[0].set_title(f"s{sample:02d} w1", fontsize=10)
        row[1].imshow(image_2, cmap="gray")
        row[1].set_title(f"s{sample:02d} w2", fontsize=10)

        # Zoom on the object: w1 as the background, outlines of both objects on top.
        rows, cols = np.nonzero(mask_1 | mask_2)
        centre_r, centre_c = int(rows.mean()), int(cols.mean())
        row[2].imshow(image_1, cmap="gray")
        row[2].contour(mask_1, levels=[0.5], colors="#2a78d6", linewidths=1.5)
        row[2].contour(mask_2, levels=[0.5], colors="#e8a33d", linewidths=1.5)
        row[2].set_xlim(centre_c - ZOOM_HALF_SIZE, centre_c + ZOOM_HALF_SIZE)
        row[2].set_ylim(centre_r + ZOOM_HALF_SIZE, centre_r - ZOOM_HALF_SIZE)
        row[2].set_title("zoom: blue = w1 object, orange = w2 object", fontsize=10)
        for axis in row:
            axis.set_xticks([])
            axis.set_yticks([])
    fig.tight_layout()
    fig.savefig(OVERLAY_PNG, dpi=130)
    plt.close(fig)


def main():
    rules = load_rules()
    stain_rules = rules["stain"]
    table = load_split_table()
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)

    # Check F.
    if len(table) != rules["data"]["expected_files"]:
        raise SystemExit(f"Expected {rules['data']['expected_files']} rows, found {len(table)}")
    bad_files, sanity_rows = check_files(table, rules["data"])
    pd.DataFrame(sanity_rows).to_csv(SANITY_CSV, index=False, lineterminator="\n")
    print(pd.DataFrame(sanity_rows).to_string(index=False))
    print(f"Check F: {len(bad_files)} of {len(table)} files differ from the expected format")

    # Check A.
    samples = first_training_samples(table, stain_rules["n_samples"])
    measurements = []
    panels = []
    for sample in samples:
        numbers, images, masks = measure_sample(table, sample, stain_rules)
        measurements.append(numbers)
        panels.append((sample, images, masks))
        print(numbers)
    draw_overlay(panels)

    w1_passes = channel_passes(measurements, 1, 2, stain_rules)
    w2_passes = channel_passes(measurements, 2, 1, stain_rules)
    documented = stain_rules["documented_nuclei_stain"]

    # Decision rule, sections 1 and 3 of docs/decision_rules.md.
    if bad_files:
        nuclei_stain, decision = None, "stop: file format differs (section 1)"
    elif w2_passes:
        nuclei_stain, decision = 2, "nuclei = w2, as documented"
    elif w1_passes:
        nuclei_stain, decision = 1, "nuclei = w1, conflict with the documentation"
    else:
        nuclei_stain, decision = None, "stop: repeat on 5 samples, no cache until resolved"

    save_decision(
        "stain.json",
        {
            "rules_version": rules["version"],
            "check_f": {
                "files_checked": len(table),
                "bad_files": bad_files,
                "by_stain_and_split": sanity_rows,
            },
            "check_a": {
                "count": stain_rules["count"],
                "blur": stain_rules["blur"],
                "samples": samples,
                "connectivity": "4-connected (scipy.ndimage.label default)",
                "min_containment": stain_rules["min_containment"],
                "max_area_ratio": stain_rules["max_area_ratio"],
                "measurements": measurements,
                "w1_passes": w1_passes,
                "w2_passes": w2_passes,
            },
            "documented_nuclei_stain": documented,
            "nuclei_stain": nuclei_stain,
            "conflict_with_documentation": nuclei_stain not in (None, documented),
            "decision": decision,
        },
    )
    print(f"w1 passes: {w1_passes}, w2 passes: {w2_passes}")
    print(f"Decision: {decision}")
    return nuclei_stain


if __name__ == "__main__":
    config = {"script": "scripts/check_stain.py"}
    with tracked_run(category="analysis", model="none", config=config):
        result = main()
    # A "stop" is a valid outcome of a completed run, so it does not mark the run as failed;
    # the exit code tells the caller not to go on.
    if result is None:
        sys.exit("Rule says stop. See results/decisions/stain.json.")
