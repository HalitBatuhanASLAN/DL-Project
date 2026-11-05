"""Check 1 (size), check 2 (separation) and the resolution sheet, section 4 of the rules.

Training scenes only, nuclei channel from results/decisions/stain.json, F1.

Output: results/decisions/resolution.json        main and ablation resolution, all numbers
        results/visual_check/resolution_pairs.csv one row per peak pair
        results/visual_check/sheet_c_resolution.png
        results/visual_check/peaks_c100.png

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\check_resolution.py
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Writes files only, opens no window.
import matplotlib.pyplot as plt  # noqa: E402 (backend must be set first)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import ndimage  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import (  # noqa: E402
    VISUAL_DIR,
    first_training_samples,
    largest_component,
    load_decision,
    load_rules,
    load_split_table,
    otsu,
    read_training_image,
    resize_box,
    save_decision,
)

PAIRS_CSV = VISUAL_DIR / "resolution_pairs.csv"
SHEET_PNG = VISUAL_DIR / "sheet_c_resolution.png"
PEAKS_PNG = VISUAL_DIR / "peaks_c100.png"
NATIVE_HW = (520, 696)  # Checked for all files by check F.
CROP_NATIVE = (100, 100, 200, 267)  # top, left, height, width of the zoomed crop (same aspect).


def name_of(size_wh):
    """Return the name of a resolution, e.g. "128x96"."""
    return f"{size_wh[0]}x{size_wh[1]}"


def equivalent_diameter(image):
    """Return the diameter of a circle with the area of the largest Otsu component."""
    area = int(largest_component(image > otsu(image)).sum())
    return math.sqrt(4 * area / math.pi), area


def odd_window(d_native):
    """Return the odd integer nearest to d_native / 2, at least 3."""
    return max(3, 2 * round((d_native / 2 - 1) / 2) + 1)


def find_peaks(image, window, sigma):
    """Return peaks as (row, col): local maxima of the smoothed image above its Otsu value."""
    smoothed = ndimage.gaussian_filter(image.astype(float), sigma=sigma)
    is_local_max = smoothed == ndimage.maximum_filter(smoothed, size=window)
    return np.argwhere(is_local_max & (smoothed > otsu(smoothed)))


def nearest_neighbour_pairs(peaks):
    """Join each peak to its nearest neighbour. Unordered, duplicates removed."""
    differences = peaks[:, None, :] - peaks[None, :, :]
    distances = np.sqrt((differences**2).sum(axis=2))
    np.fill_diagonal(distances, np.inf)  # A peak is not its own neighbour.
    nearest = distances.argmin(axis=1)
    return sorted({(min(i, int(j)), max(i, int(j))) for i, j in enumerate(nearest)})


def dip_ratio(image, peak_a, peak_b, f_y, f_x, n_points):
    """Return min(inner points) / min(end points) on the segment between two native peaks.

    The two peaks are resolved at this image's resolution if the ratio is <= the limit.
    """
    # Native centres mapped to this image's pixel grid (rule in section 4).
    r_a, c_a = (peak_a[0] + 0.5) / f_y - 0.5, (peak_a[1] + 0.5) / f_x - 0.5
    r_b, c_b = (peak_b[0] + 0.5) / f_y - 0.5, (peak_b[1] + 0.5) / f_x - 0.5
    rows = np.linspace(r_a, r_b, n_points)
    cols = np.linspace(c_a, c_b, n_points)
    # order=1 is bilinear. "nearest" only matters for a peak in the outermost half pixel.
    line = ndimage.map_coordinates(image.astype(float), [rows, cols], order=1, mode="nearest")
    return float(line[1:-1].min() / min(line[0], line[-1]))


def run_size_check(table, stain, size_rules, candidates):
    """Check 1: return d_native and the numbers for each candidate."""
    samples = first_training_samples(table, size_rules["n_samples"])
    diameters = []
    areas = []
    for sample in samples:
        image = read_training_image(table, size_rules["count"], size_rules["blur"], sample, stain)
        diameter, area = equivalent_diameter(image)
        diameters.append(diameter)
        areas.append(area)
    d_native = float(np.median(diameters))

    limit = size_rules["min_median_diameter_px"]
    results = {}
    for size_wh in candidates:
        factor = NATIVE_HW[1] / size_wh[0]
        d_candidate = d_native / factor
        results[name_of(size_wh)] = {
            "factor": factor,
            "d_at_candidate_px": d_candidate,
            "passes": d_candidate >= limit,
        }
    numbers = {
        "samples": samples,
        "areas_px": areas,
        "diameters_px": diameters,
        "d_native_median_px": d_native,
        "limit_px": limit,
        "candidates": results,
    }
    return d_native, numbers


def run_pair_check(table, stain, pair_rules, candidates, d_native):
    """Check 2: return one row per peak pair and the numbers for each candidate."""
    samples = first_training_samples(table, pair_rules["n_samples"])
    window = odd_window(d_native)
    limit = pair_rules["max_saddle_to_peak"]
    n_points = pair_rules["line_points"]
    sigma = pair_rules["peak_smoothing_sigma_px"]
    rows = []
    peaks_per_image = {}
    figure_data = None

    for sample in samples:
        native = read_training_image(table, pair_rules["count"], pair_rules["blur"], sample, stain)
        resized = {name_of(size_wh): (resize_box(native, size_wh), size_wh) for size_wh in candidates}
        peaks = find_peaks(native, window, sigma)
        pairs = nearest_neighbour_pairs(peaks)
        peaks_per_image[str(sample)] = len(peaks)

        pair_rows = []
        for i, j in pairs:
            row = {
                "sample": sample,
                "r1": int(peaks[i][0]),
                "c1": int(peaks[i][1]),
                "r2": int(peaks[j][0]),
                "c2": int(peaks[j][1]),
                "distance_px": float(np.hypot(*(peaks[i] - peaks[j]))),
                "ratio_native": dip_ratio(native, peaks[i], peaks[j], 1.0, 1.0, n_points),
            }
            for name, (image, size_wh) in resized.items():
                f_y, f_x = NATIVE_HW[0] / size_wh[1], NATIVE_HW[1] / size_wh[0]
                row[f"ratio_{name}"] = dip_ratio(image, peaks[i], peaks[j], f_y, f_x, n_points)
            pair_rows.append(row)
        rows.extend(pair_rows)
        if figure_data is None:  # The first training sample is the one drawn.
            figure_data = (sample, native, peaks, pair_rows)

    df = pd.DataFrame(rows)
    df["resolved_native"] = df["ratio_native"] <= limit
    native_resolved = df[df["resolved_native"]]

    results = {}
    for size_wh in candidates:
        name = name_of(size_wh)
        df[f"resolved_{name}"] = df[f"ratio_{name}"] <= limit
        kept = int((native_resolved[f"ratio_{name}"] <= limit).sum())
        retention = kept / len(native_resolved)
        results[name] = {
            "kept": kept,
            "retention": retention,
            "passes": retention >= pair_rules["min_resolved_retention"],
        }

    numbers = {
        "samples": samples,
        "maximum_filter_window_px": window,
        "peaks_per_image": peaks_per_image,
        "pairs": len(df),
        "resolved_at_native": len(native_resolved),
        "pair_distance_px_min_median_max": [
            float(df["distance_px"].min()),
            float(df["distance_px"].median()),
            float(df["distance_px"].max()),
        ],
        "max_saddle_to_peak": limit,
        "min_resolved_retention": pair_rules["min_resolved_retention"],
        "candidates": results,
    }
    return df, numbers, figure_data


def draw_sheet(table, stain, sample, candidates):
    """Resolution sheet: one training scene at native and at every candidate."""
    native_c100 = read_training_image(table, 100, 1, sample, stain)
    native_c1 = read_training_image(table, 1, 1, sample, stain)
    # Largest resolution first; every image keeps its own pixels (no interpolation).
    sizes = [None] + sorted(candidates, reverse=True)
    top, left, height, width = CROP_NATIVE

    # Crop around the single nucleus of the C1 scene, clipped to stay inside the image.
    rows, cols = np.nonzero(largest_component(native_c1 > otsu(native_c1)))
    c1_half = 45
    c1_top = int(np.clip(rows.mean() - c1_half, 0, NATIVE_HW[0] - 2 * c1_half))
    c1_left = int(np.clip(cols.mean() - c1_half, 0, NATIVE_HW[1] - 2 * c1_half))

    fig, axes = plt.subplots(3, len(sizes), figsize=(3.1 * len(sizes), 7.6))
    for column, size_wh in enumerate(sizes):
        name = "native 696x520" if size_wh is None else name_of(size_wh)
        small_c100 = native_c100 if size_wh is None else resize_box(native_c100, size_wh)
        small_c1 = native_c1 if size_wh is None else resize_box(native_c1, size_wh)
        f_y, f_x = (1.0, 1.0) if size_wh is None else (NATIVE_HW[0] / size_wh[1], NATIVE_HW[1] / size_wh[0])

        axes[0, column].imshow(small_c100, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        axes[0, column].set_title(name, fontsize=10)

        r0, r1 = int(top / f_y), int((top + height) / f_y)
        c0, c1 = int(left / f_x), int((left + width) / f_x)
        axes[1, column].imshow(
            small_c100[r0:r1, c0:c1], cmap="gray", vmin=0, vmax=255, interpolation="nearest"
        )

        r0, r1 = int(c1_top / f_y), int((c1_top + 2 * c1_half) / f_y)
        c0, c1 = int(c1_left / f_x), int((c1_left + 2 * c1_half) / f_x)
        axes[2, column].imshow(
            small_c1[r0:r1, c0:c1], cmap="gray", vmin=0, vmax=255, interpolation="nearest"
        )

    labels = [f"C100 s{sample:02d}", "C100 crop", "C1 crop"]
    for row, label in zip(axes, labels):
        row[0].set_ylabel(label, fontsize=10)
        for axis in row:
            axis.set_xticks([])
            axis.set_yticks([])
    fig.tight_layout()
    fig.savefig(SHEET_PNG, dpi=130)
    plt.close(fig)


def draw_peaks(figure_data, main_name, limit):
    """Show the detected peaks and pairs of one C100 scene, to check the detector by eye."""
    sample, native, peaks, pair_rows = figure_data
    fig, axis = plt.subplots(figsize=(9, 6.9))
    axis.imshow(native, cmap="gray")
    for row in pair_rows:
        kept = row[f"ratio_{main_name}"] <= limit
        resolved_native = row["ratio_native"] <= limit
        if not resolved_native:
            color = "#9b9b96"  # Unresolved already at native: not part of the check.
        else:
            color = "#2a78d6" if kept else "#e8a33d"
        axis.plot([row["c1"], row["c2"]], [row["r1"], row["r2"]], color=color, linewidth=1.5)
    axis.scatter(peaks[:, 1], peaks[:, 0], s=10, color="#ffffff", linewidths=0)
    axis.set_title(
        f"C100 F1 s{sample:02d}, {len(peaks)} peaks. Blue: resolved at native and {main_name}. "
        "Orange: lost. Grey: unresolved at native.",
        fontsize=9,
    )
    axis.set_xticks([])
    axis.set_yticks([])
    fig.tight_layout()
    fig.savefig(PEAKS_PNG, dpi=130)
    plt.close(fig)


def choose(res_rules, passes_128, passes_256):
    """Decision rule of section 4. Returns the main resolution name."""
    if passes_128:
        return "128x96"
    if passes_256:
        return "256x192"
    return "348x260"


def main():
    # Refuses to run without a finished stain check.
    stain_decision = load_decision("stain.json")
    stain = stain_decision["nuclei_stain"]
    if stain is None:
        raise SystemExit("stain.json says stop: resolve the stain check first.")
    print(f"Nuclei stain: w{stain} ({stain_decision['decision']})")

    rules = load_rules()
    res_rules = rules["resolution"]
    candidates = [tuple(size) for size in res_rules["candidates_wh"]]
    table = load_split_table()
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)

    d_native, size_numbers = run_size_check(table, stain, res_rules["size_check"], candidates)
    print(f"Check 1: {size_numbers}")

    pairs, pair_numbers, figure_data = run_pair_check(
        table, stain, res_rules["pair_check"], candidates, d_native
    )
    pairs.to_csv(PAIRS_CSV, index=False, lineterminator="\n")
    print(f"Check 2: {pair_numbers}")

    passes = {
        name: size_numbers["candidates"][name]["passes"] and pair_numbers["candidates"][name]["passes"]
        for name in size_numbers["candidates"]
    }
    main_name = choose(res_rules, passes["128x96"], passes["256x192"])
    ablation_name = res_rules["ablation_for"][main_name]
    main_wh = [int(value) for value in main_name.split("x")]

    draw_sheet(table, stain, pair_numbers["samples"][0], candidates)
    draw_peaks(figure_data, main_name, res_rules["pair_check"]["max_saddle_to_peak"])

    save_decision(
        "resolution.json",
        {
            "rules_version": rules["version"],
            "nuclei_stain": stain,
            "d_native_px": d_native,
            "check_1_size": size_numbers,
            "check_2_separation": pair_numbers,
            "candidate_passes_both": passes,
            "main_resolution": main_name,
            "main_resolution_wh": main_wh,
            "main_factor": NATIVE_HW[1] / main_wh[0],
            "ablation_resolution": ablation_name,
        },
    )
    print(f"Passes both: {passes}")
    print(f"Decision: main {main_name}, ablation {ablation_name}")


if __name__ == "__main__":
    config = {"script": "scripts/check_resolution.py"}
    with tracked_run(category="analysis", model="none", config=config):
        main()
