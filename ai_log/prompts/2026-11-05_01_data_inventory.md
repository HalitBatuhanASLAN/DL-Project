# Prompt: BBBC005 data inventory

Date: 2026-11-05. Given verbatim to Claude Code (claude-opus-5-5). The text below is unchanged.

````text
Context: University deep learning project (CSE655, "green" CNN image regression, PyTorch).
Repo: C:\Users\halit\Desktop\forthYear\DL\hw\Project (Windows, PowerShell, Python 3.11,
virtual env at .venv, already set up and committed). Everything in the repo must be in English.

Dataset: BBBC005 v1 (Broad Bioimage Benchmark Collection), synthetic fluorescent cell images.
The file BBBC005_v1_images.zip (~1.8 GB) is in data/. Target for regression = cell count,
which is encoded in each file name.

This step is ONLY a data inventory. Do not make any design decisions (no subset selection,
no train/val/test split, no resizing, no model, no training).

Tasks:
1. If not already extracted, extract the zip into data/raw/ and tell me the folder layout
   (top-level folders, number of files, file extensions). Report any non-image files.

2. Write scripts/data_inventory.py that:
   a. Lists all image files and parses each file name with a regular expression.
      First print 10 real file names verbatim, then infer the naming pattern from them.
      Expected fields (verify, do not assume): well/plate position, cell count (C),
      focus/blur level (F), sample index (s), stain/channel (w).
   b. Reports: total files, number of unparseable names (print them), unique values and
      counts for every field.
   c. Cross-tabulations: cell count x blur level, cell count x stain, blur level x stain.
   d. Tests this hypothesis and prints PASS/FAIL with numbers:
      "Each (cell count, sample index) pair is one simulated scene that appears at every
      blur level and in both stains." Report the number of unique scenes and the
      distribution of images per scene.
   e. Checks how the well/plate field relates to the other fields
      (e.g. is it determined by cell count and blur level?).
   f. Opens 5 random images (fixed seed 42) and reports: mode, dtype, shape,
      min/max/mean pixel value.
   g. Saves a per-image index to data/bbbc005_index.csv
      (columns: relative_path, well, count, blur, sample, stain) and saves the full
      printed summary to results/data_inventory.txt.

3. Run the script inside .venv and show me the complete output.

Constraints:
- Use only packages already in requirements.txt (pillow, numpy, pandas).
  If TIFF reading fails with pillow, stop and tell me; do not install anything without asking.
- Keep the code simple and commented; I must be able to explain every line in an exam.
- If anything does not match the expected structure, report it clearly instead of
  working around it.
- Do not commit data/. Commit only scripts/data_inventory.py and results/data_inventory.txt
  with message "Add BBBC005 data inventory", after showing me git status.

At the end, give me a plain-text summary: folder layout, file name pattern, field value
ranges, hypothesis result, number of unique scenes, image properties, and anything unexpected.
````
