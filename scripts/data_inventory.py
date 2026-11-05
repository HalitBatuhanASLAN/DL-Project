"""Data inventory for BBBC005 v1 (synthetic fluorescent cell images).

This script only DESCRIBES the dataset. It makes no design decisions: there is
no subset selection, no train/val/test split, no resizing and no model.

Input : data/raw/ (the extracted BBBC005_v1_images.zip)
Output: data/bbbc005_index.csv   one row per image (not committed, data/ is ignored)
        results/data_inventory.txt   the full printed summary

Run from anywhere with the project virtual environment:
    .venv\\Scripts\\python.exe scripts\\data_inventory.py
"""

import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

# Paths are built from this file's location, so the working directory does not matter.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INDEX_CSV = PROJECT_ROOT / "data" / "bbbc005_index.csv"
SUMMARY_TXT = PROJECT_ROOT / "results" / "data_inventory.txt"

SEED = 42  # Fixed seed so the random images and scenes are the same on every run.
NUM_RANDOM_IMAGES = 5  # Task 2f: how many images to open.
NUM_PIXEL_SCENES = 20  # How many scenes the pixel check in section 5 looks at.

# File name pattern, inferred from the real names printed in section 2. Example:
#   SIMCEPImages_B13_C53_F4_s11_w1.TIF
# Well column and sample are zero-padded to 2 digits; C and F are not padded.
NAME_PATTERN = re.compile(
    r"^SIMCEPImages"
    r"_(?P<well>[A-Z]\d{2})"  # well: one row letter plus a two-digit column
    r"_C(?P<count>\d+)"  # cell count, the regression target
    r"_F(?P<blur>\d+)"  # focus/blur level
    r"_s(?P<sample>\d+)"  # sample index
    r"_w(?P<stain>\d+)"  # stain/channel
    r"\.TIF$"
)

# Everything printed is also collected here, then saved to the summary file.
output_lines = []


def report(text=""):
    """Print text and remember it for the summary file."""
    print(text)
    output_lines.append(str(text))


def section(title):
    """Print a visible section heading."""
    report()
    report("=" * 78)
    report(title)
    report("=" * 78)


def is_determined_by(table, key_columns, value_column):
    """Return True if each key combination maps to exactly one value."""
    return table.groupby(key_columns)[value_column].nunique().max() == 1


def correlation(path_a, path_b):
    """Pearson correlation between the pixels of two images."""
    pixels_a = np.asarray(Image.open(path_a), dtype=float).ravel()
    pixels_b = np.asarray(Image.open(path_b), dtype=float).ravel()
    return float(np.corrcoef(pixels_a, pixels_b)[0, 1])


def next_value(sorted_values, value):
    """Return the value after `value` in the list, wrapping round at the end."""
    position = sorted_values.index(value)
    return sorted_values[(position + 1) % len(sorted_values)]


# ------------------------------------------------------------------------------
# 1. Folder layout
# ------------------------------------------------------------------------------
section("1. FOLDER LAYOUT")

if not RAW_DIR.is_dir():
    raise SystemExit(f"Folder not found: {RAW_DIR}. Extract the zip first.")

# rglob("*") walks all subfolders; we keep files only.
all_files = sorted(path for path in RAW_DIR.rglob("*") if path.is_file())
top_level = sorted(path.name for path in RAW_DIR.iterdir())
extensions = Counter(path.suffix for path in all_files)

# TIFF is the only image type expected; compare in upper case to catch .tif/.TIF.
image_files = [path for path in all_files if path.suffix.upper() in (".TIF", ".TIFF")]
other_files = [path for path in all_files if path not in set(image_files)]

report(f"Root folder       : {RAW_DIR.relative_to(PROJECT_ROOT).as_posix()}")
report(f"Top-level entries : {top_level}")
report(f"Total files       : {len(all_files)}")
report(f"Extensions        : {dict(extensions)}")
report(f"Non-image files   : {len(other_files)}")
for path in other_files:
    report(f"  {path.relative_to(RAW_DIR).as_posix()} ({path.stat().st_size} bytes)")

# ------------------------------------------------------------------------------
# 2. File names: print real examples, then parse every name
# ------------------------------------------------------------------------------
section("2. FILE NAMES (task 2a, 2b)")

# Evenly spaced names, because the first 10 sorted names differ only in s and w.
step = len(image_files) // 10
report("10 real file names, verbatim (evenly spaced through the sorted list):")
for path in image_files[::step][:10]:
    report(f"  {path.name}")

report()
report("Inferred pattern: SIMCEPImages_<well>_C<count>_F<blur>_s<sample>_w<stain>.TIF")

rows = []
unparseable = []
for path in image_files:
    match = NAME_PATTERN.match(path.name)
    if match is None:
        unparseable.append(path.name)
        continue
    rows.append(
        {
            "relative_path": path.relative_to(PROJECT_ROOT).as_posix(),
            "well": match["well"],
            "count": int(match["count"]),
            "blur": int(match["blur"]),
            "sample": int(match["sample"]),
            "stain": int(match["stain"]),
        }
    )

df = pd.DataFrame(rows)

report()
report(f"Total image files : {len(image_files)}")
report(f"Parsed            : {len(df)}")
report(f"Unparseable names : {len(unparseable)}")
for name in unparseable:
    report(f"  {name}")

# Unique values and how many images have each value, for every field.
for field in ["well", "count", "blur", "sample", "stain"]:
    value_counts = df[field].value_counts().sort_index()
    report()
    report(f"Field '{field}': {len(value_counts)} unique values")
    if field == "well":
        # 384 wells are too many to list; show the range and the per-well counts.
        report(f"  from {value_counts.index[0]} to {value_counts.index[-1]}")
        report(f"  images per well: {value_counts.value_counts().to_dict()}")
    else:
        report(f"  values: {value_counts.index.tolist()}")
        report(f"  images per value: {value_counts.value_counts().to_dict()}")

# ------------------------------------------------------------------------------
# 3. Cross-tabulations
# ------------------------------------------------------------------------------
section("3. CROSS-TABULATIONS (task 2c)")

pairs = [("count", "blur"), ("count", "stain"), ("blur", "stain")]
for row_field, column_field in pairs:
    table = pd.crosstab(df[row_field], df[column_field])
    cell_values = sorted(set(table.to_numpy().ravel().tolist()))
    report()
    report(f"{row_field} x {column_field} (distinct cell values: {cell_values})")
    report(table.to_string())

# ------------------------------------------------------------------------------
# 4. Hypothesis test on file names
# ------------------------------------------------------------------------------
section("4. HYPOTHESIS, FILE NAMES (task 2d)")

report(
    'Hypothesis: "Each (cell count, sample index) pair is one simulated scene that\n'
    'appears at every blur level and in both stains."'
)

num_blurs = df["blur"].nunique()
num_stains = df["stain"].nunique()
expected_per_scene = num_blurs * num_stains

scene_keys = ["count", "sample"]
images_per_scene = df.groupby(scene_keys).size()

# Counting unique (blur, stain) pairs separately also catches duplicates: a scene
# could have the right number of images but repeat one combination and miss another.
unique_combinations = (
    df.drop_duplicates(scene_keys + ["blur", "stain"]).groupby(scene_keys).size()
)

complete_scenes = (images_per_scene == expected_per_scene) & (
    unique_combinations == expected_per_scene
)
name_test_passed = bool(complete_scenes.all())

report()
report(f"Blur levels x stains          : {num_blurs} x {num_stains} = {expected_per_scene}")
report(f"Unique scenes                 : {len(images_per_scene)}")
report(f"Scenes if all pairs exist     : {df['count'].nunique() * df['sample'].nunique()}")
report(f"Images-per-scene distribution : {images_per_scene.value_counts().to_dict()}")
report(f"Complete scenes               : {int(complete_scenes.sum())} of {len(complete_scenes)}")
report(f"Result (names only)           : {'PASS' if name_test_passed else 'FAIL'}")
report()
report("Note: this test shows the combinations are complete. It cannot show that the")
report("files really contain the same scene. Section 5 checks that on the pixels.")

# ------------------------------------------------------------------------------
# 5. Hypothesis test on pixels (small sample of scenes)
# ------------------------------------------------------------------------------
section("5. HYPOTHESIS, PIXELS (extra check for task 2d)")

# Look up any image by its four fields.
path_of = dict(
    zip(
        zip(df["count"], df["blur"], df["sample"], df["stain"]),
        df["relative_path"],
    )
)

counts = sorted(df["count"].unique().tolist())
blurs = sorted(df["blur"].unique().tolist())
samples = sorted(df["sample"].unique().tolist())
stains = sorted(df["stain"].unique().tolist())
sharpest, blurriest = blurs[0], blurs[-1]  # Lowest and highest F value.

# Random scenes. Each is compared with images that should and should not match it.
scenes = df[scene_keys].drop_duplicates().sample(n=NUM_PIXEL_SCENES, random_state=SEED)

same_scene_other_blur = []
other_sample_other_blur = []  # Control: different s, same count.
other_count_other_blur = []  # Control: same s, different count.
same_scene_other_stain = []
other_sample_other_stain = []  # Control: different s, other stain.

for count, sample in zip(scenes["count"].tolist(), scenes["sample"].tolist()):
    other_sample = next_value(samples, sample)
    other_count = next_value(counts, count)

    for stain in stains:
        other_stain = next_value(stains, stain)
        reference = PROJECT_ROOT / path_of[(count, sharpest, sample, stain)]

        # Each comparison below is (fields of the second image, list for the result).
        comparisons = [
            ((count, blurriest, sample, stain), same_scene_other_blur),
            ((count, blurriest, other_sample, stain), other_sample_other_blur),
            ((other_count, blurriest, sample, stain), other_count_other_blur),
            ((count, sharpest, sample, other_stain), same_scene_other_stain),
            ((count, sharpest, other_sample, other_stain), other_sample_other_stain),
        ]
        for fields, results in comparisons:
            results.append(correlation(reference, PROJECT_ROOT / path_of[fields]))

report(f"Pearson correlation of pixels, {NUM_PIXEL_SCENES} random scenes (seed {SEED}), both stains.")
report(f"The reference image is always at F{sharpest}. Blur comparisons use F{blurriest}.")
report()
report(f"{'comparison':<42}{'mean':>8}{'min':>8}{'max':>8}")
named_results = [
    ("same scene, other blur", same_scene_other_blur),
    ("control: other sample, other blur", other_sample_other_blur),
    ("control: other count, same s, other blur", other_count_other_blur),
    ("same scene, other stain", same_scene_other_stain),
    ("control: other sample, other stain", other_sample_other_stain),
]
for label, values in named_results:
    report(f"{label:<42}{np.mean(values):>8.3f}{np.min(values):>8.3f}{np.max(values):>8.3f}")

# PASS needs every same-scene value to be above every value of its controls.
blur_controls = other_sample_other_blur + other_count_other_blur
blur_separated = min(same_scene_other_blur) > max(blur_controls)
stain_separated = min(same_scene_other_stain) > max(other_sample_other_stain)

report()
report(f"Same scene across blur levels : {'PASS' if blur_separated else 'FAIL'}")
report(f"Same scene across stains      : {'PASS' if stain_separated else 'FAIL'}")
report(f"Checked {NUM_PIXEL_SCENES} of {len(images_per_scene)} scenes, so this is evidence, not proof.")

# ------------------------------------------------------------------------------
# 6. Well field versus the other fields
# ------------------------------------------------------------------------------
section("6. WELL FIELD (task 2e)")

# Split the well into its row letter and column number, only for this analysis.
df["well_row"] = df["well"].str[0]
df["well_column"] = df["well"].str[1:].astype(int)

report(f"Unique wells: {df['well'].nunique()}")
report(f"Well rows   : {df['well_row'].nunique()}, from {df['well_row'].min()} to {df['well_row'].max()}")
report(f"Well columns: {df['well_column'].nunique()}, from {df['well_column'].min()} to {df['well_column'].max()}")
report()

checks = [
    ("(count, blur) determines well", ["count", "blur"], "well"),
    ("well determines count", ["well"], "count"),
    ("well determines blur", ["well"], "blur"),
    ("well row determines blur", ["well_row"], "blur"),
    ("blur determines well row", ["blur"], "well_row"),
    ("well column determines count", ["well_column"], "count"),
    ("count determines well column", ["count"], "well_column"),
    ("well determines sample", ["well"], "sample"),
    ("well determines stain", ["well"], "stain"),
]
for label, keys, value in checks:
    report(f"{label:<32}: {bool(is_determined_by(df, keys, value))}")

report()
report(f"Samples per well: {df.groupby('well')['sample'].nunique().value_counts().to_dict()}")
report(f"Stains per well : {df.groupby('well')['stain'].nunique().value_counts().to_dict()}")

report()
report("Well row -> blur:")
report(df[["well_row", "blur"]].drop_duplicates().sort_values("well_row").to_string(index=False))
report()
report("Well column -> count:")
report(df[["well_column", "count"]].drop_duplicates().sort_values("well_column").to_string(index=False))

# ------------------------------------------------------------------------------
# 7. Pixel properties of 5 random images
# ------------------------------------------------------------------------------
section("7. RANDOM IMAGES (task 2f)")

report(f"{NUM_RANDOM_IMAGES} random images, seed {SEED}:")
for relative_path in df["relative_path"].sample(n=NUM_RANDOM_IMAGES, random_state=SEED):
    with Image.open(PROJECT_ROOT / relative_path) as image:
        mode = image.mode  # Pillow's pixel format, e.g. "L" = 8-bit greyscale.
        pixels = np.asarray(image)
    report(f"  {Path(relative_path).name}")
    report(
        f"    mode={mode} dtype={pixels.dtype} shape={pixels.shape} "
        f"min={pixels.min()} max={pixels.max()} mean={pixels.mean():.2f}"
    )

# ------------------------------------------------------------------------------
# 8. Save outputs
# ------------------------------------------------------------------------------
section("8. SAVED FILES (task 2g)")

index_columns = ["relative_path", "well", "count", "blur", "sample", "stain"]
df[index_columns].to_csv(INDEX_CSV, index=False)

report(f"Index   : {INDEX_CSV.relative_to(PROJECT_ROOT).as_posix()} ({len(df)} rows)")
report("          relative_path is relative to the project root")
report(f"Summary : {SUMMARY_TXT.relative_to(PROJECT_ROOT).as_posix()}")

# Written last, so the summary contains everything printed above.
SUMMARY_TXT.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
