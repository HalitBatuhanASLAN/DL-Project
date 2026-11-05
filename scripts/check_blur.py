"""Check B1 (blur levels), section 5 of the rules.

Scenes: first training sample x the 20 seen counts, nuclei channel, chosen resolution.
hp(img) = img - gaussian_filter(img, sigma), with sigma = nucleus radius at that resolution.
D(F) = 1 - mean over scenes of Pearson r(hp(F1), hp(F)).

Output: results/decisions/blur_levels.json        D(F) for all 16 levels, K, chosen levels
        results/visual_check/blur_similarity.csv  one row per blur level
        results/visual_check/blur_curve.png
        results/visual_check/blur_strip.png

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\check_blur.py
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
    load_decision,
    load_rules,
    load_split_table,
    read_training_image,
    resize_box,
    save_decision,
    seen_counts,
)

SIMILARITY_CSV = VISUAL_DIR / "blur_similarity.csv"
CURVE_PNG = VISUAL_DIR / "blur_curve.png"
STRIP_PNG = VISUAL_DIR / "blur_strip.png"
STRIP_COUNT = 53  # A seen count near the middle of the range, drawn in the strip figure.
LINE_COLOR = "#2a78d6"
INK = "#52514e"
GRID = "#e4e3df"


def high_pass(image, sigma):
    """Remove everything coarser than the nucleus radius."""
    image = image.astype(float)
    return image - ndimage.gaussian_filter(image, sigma=sigma)


def measure_levels(table, stain, sample, counts, levels, size_wh, sigma):
    """Return an array of Pearson r, one row per scene (count), one column per blur level."""
    correlations = np.zeros((len(counts), len(levels)))
    for row, count in enumerate(counts):
        reference = None
        for column, blur in enumerate(levels):
            image = read_training_image(table, count, blur, sample, stain)
            filtered = high_pass(resize_box(image, size_wh), sigma).ravel()
            if reference is None:
                reference = filtered  # levels[0] is F1.
            correlations[row, column] = np.corrcoef(reference, filtered)[0, 1]
    return correlations


def choose_levels(levels, d_values, k, always_include):
    """Return (targets, chosen levels). F1 and F48 are reserved, the rest picked greedily."""
    d_of = dict(zip(levels, d_values))
    d_last = d_of[levels[-1]]
    targets = [i / (k - 1) * d_last for i in range(k)]
    chosen = list(always_include)  # t_0 = 0 is F1, t_(K-1) = D(F48) is F48.
    for target in targets[1:-1]:
        unused = [blur for blur in levels if blur not in chosen]
        chosen.append(min(unused, key=lambda blur: abs(d_of[blur] - target)))
    return targets, sorted(chosen)


def draw_curve(levels, d_values, targets, chosen, name):
    """D(F) against F, with the chosen levels marked and the targets as thin lines."""
    fig, axis = plt.subplots(figsize=(7.5, 4.2))
    for target in targets:
        axis.axhline(target, color=GRID, linewidth=1, zorder=1)
    axis.plot(levels, d_values, color=LINE_COLOR, linewidth=2, marker="o", markersize=3, zorder=2)
    d_of = dict(zip(levels, d_values))
    chosen_d = [d_of[blur] for blur in chosen]
    axis.scatter(chosen, chosen_d, s=64, color=LINE_COLOR, edgecolor="white", linewidth=2, zorder=3)
    for blur, value in zip(chosen, chosen_d):
        axis.annotate(f"F{blur}", (blur, value), xytext=(-4, 8), textcoords="offset points",
                      fontsize=9, color=INK, ha="right")
    axis.set_xlabel("Blur level F", color=INK)
    axis.set_ylabel("D(F) = 1 - mean r(hp(F1), hp(F))", color=INK)
    axis.set_title(f"Blur distance at {name}; large dots = chosen, grey lines = targets t_k",
                   fontsize=10, color=INK, loc="left")
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(colors=INK)
    fig.tight_layout()
    fig.savefig(CURVE_PNG, dpi=130)
    plt.close(fig)


def draw_strip(table, stain, sample, chosen, size_wh):
    """The same training scene at each chosen blur level, at the chosen resolution."""
    fig, axes = plt.subplots(1, len(chosen), figsize=(2.6 * len(chosen), 2.4), squeeze=False)
    for axis, blur in zip(axes[0], chosen):
        image = resize_box(read_training_image(table, STRIP_COUNT, blur, sample, stain), size_wh)
        axis.imshow(image, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        axis.set_title(f"F{blur}", fontsize=10)
        axis.set_xticks([])
        axis.set_yticks([])
    fig.tight_layout()
    fig.savefig(STRIP_PNG, dpi=130)
    plt.close(fig)


def main():
    # Refuses to run without a finished resolution check.
    resolution = load_decision("resolution.json")
    stain = resolution["nuclei_stain"]
    name = resolution["main_resolution"]
    size_wh = tuple(resolution["main_resolution_wh"])
    sigma = resolution["d_native_px"] / 2 / resolution["main_factor"]
    print(f"Stain w{stain}, resolution {name}, high-pass sigma {sigma:.3f} px")

    rules = load_rules()
    blur_rules = rules["blur"]
    table = load_split_table()
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)

    sample = first_training_samples(table, 1)[0]
    counts = seen_counts(table)
    levels = sorted(table["blur"].unique().tolist())
    if levels[0] != 1 or levels[-1] != 48 or len(levels) != 16 or len(counts) != 20:
        raise SystemExit(f"Unexpected levels or counts: {levels}, {counts}")

    correlations = measure_levels(table, stain, sample, counts, levels, size_wh, sigma)
    d_values = (1 - correlations.mean(axis=0)).tolist()
    d_last = d_values[-1]

    k_raw = math.ceil(d_last / blur_rules["d_step"]) + 1
    k = min(max(k_raw, blur_rules["k_min"]), blur_rules["k_max"])
    targets, chosen = choose_levels(levels, d_values, k, blur_rules["always_include"])

    similarity = pd.DataFrame(
        {
            "blur": levels,
            "d": d_values,
            "scene_r_min": correlations.min(axis=0),
            "scene_r_max": correlations.max(axis=0),
            "chosen": [blur in chosen for blur in levels],
        }
    )
    similarity.to_csv(SIMILARITY_CSV, index=False, lineterminator="\n")
    print(similarity.to_string(index=False))

    draw_curve(levels, d_values, targets, chosen, name)
    draw_strip(table, stain, sample, chosen, size_wh)

    save_decision(
        "blur_levels.json",
        {
            "rules_version": rules["version"],
            "nuclei_stain": stain,
            "resolution": name,
            "highpass_sigma_px": sigma,
            "sample": sample,
            "counts": counts,
            "d_by_level": {str(blur): value for blur, value in zip(levels, d_values)},
            "d_step": blur_rules["d_step"],
            "d_f48": d_last,
            "k_before_clipping": k_raw,
            "k": k,
            "targets": targets,
            "chosen_levels": chosen,
            "d_is_monotonic": bool(np.all(np.diff(d_values) >= 0)),
        },
    )
    print(f"D(F48) = {d_last:.4f}, K = {k} (before clipping {k_raw})")
    print(f"Targets: {[round(value, 4) for value in targets]}")
    print(f"Decision: blur levels {chosen}")


if __name__ == "__main__":
    config = {"script": "scripts/check_blur.py"}
    with tracked_run(category="analysis", model="none", config=config):
        main()
