# DL-Project

CSE655 term project: "green" CNN regression of the cell count in BBBC005 v1 synthetic fluorescence images.
Three CNNs (own KirazNet = `own_cnn`, MobileNetV3-Small, ResNet-18) are compared with a mean and a brightness
baseline on accuracy (MAE) and on the energy and CO2eq of every run, measured with CodeCarbon.

## Setup

Windows PowerShell, Python 3.11, NVIDIA GPU (driver with CUDA 12.4 support or newer).

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install the CUDA build of PyTorch
pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124

# 3. Install the remaining dependencies
pip install -r requirements.txt

# 4. Check the environment (versions, GPU, CodeCarbon smoke test)
python scripts/check_env.py
```

## ImageNet weights

Downloaded once inside `tracked_run` (category env) by `scripts/download_weights.py`, to
`checkpoints/hub/checkpoints/` (git-ignored). Run `20261105-233510_env_imagenet_weights_4413`.

| Model | File | Bytes | SHA-256 |
| --- | --- | --- | --- |
| ResNet-18 (IMAGENET1K_V1) | `resnet18-f37072fd.pth` | 46,830,571 | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |
| MobileNetV3-Small (IMAGENET1K_V1) | `mobilenet_v3_small-047dcff4.pth` | 10,306,551 | `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f` |

Source: `https://download.pytorch.org/models/`.

## Reproducing every number

Run all commands from the project root with the virtual environment (`.venv\Scripts\python.exe`, written
`python` below). Every script that measures something runs inside `src/carbon.py:tracked_run`. That writes
a run folder `runs/<run_id>/` (`config.json`, `emissions.csv`, plus `metrics.json`/`eval_log.csv` where
relevant) and appends one row to `runs/index.csv`. The rules every step follows are in
`docs/decision_rules.md` and `configs/rules.json`. The tag is the git tag at which that step's outputs
were committed. Check it out (`git checkout <tag>`) to see the exact code that produced them.

| # | Step | Command | Outputs | Tag |
| --- | --- | --- | --- | --- |
| 0 | Data | Download `BBBC005_v1_images.zip` (about 1.8 GB) from the Broad Bioimage Benchmark Collection, <https://bbbc.broadinstitute.org/BBBC005>. Put it in `data/` and extract it so that the TIFs are in `data/raw/BBBC005_v1_images/`. | 19,200 `.TIF` files (+ one `.htaccess`) | - |
| 1 | Data inventory | `python scripts/data_inventory.py` | `data/bbbc005_index.csv` (not committed), `results/data_inventory.txt` | `split-v1` (first run: commit `bbb3055`) |
| 2 | Split | `python scripts/make_split.py` | `splits/splits.csv`, `splits/splits.sha256`, `results/split_summary.csv` | `split-v1` |
| 3 | Visual checks | `python scripts/check_stain.py`<br>`python scripts/check_resolution.py`<br>`python scripts/check_blur.py` | `results/decisions/{stain,resolution,blur_levels}.json`, `results/visual_check/` | `data-v2` (rules-v1.1; first version `data-v1`) |
| 4 | Image cache | `python scripts/build_cache.py` | `data/cache/{split}_{WxH}.npz` (not committed), `results/norm_stats.json`, `results/cache_manifest.json` | `cache-v1` |
| 5 | Baselines (val) | `python scripts/baselines.py` | `results/baselines/`, `results/baselines_val.json`, `results/baselines_val_per_blur.csv`, `results/val_predictions/baselines.csv` | `infra-v1` (first run `cache-v1`) |
| 6 | Weights | `python scripts/download_weights.py` | `checkpoints/hub/checkpoints/*.pth` (not committed, hashes above) | `infra-v1` |
| 7 | Layer table | `python scripts/layer_table.py` | `results/model_tables/` (`layers_<model>_<res>.csv`, `totals.csv`, `model_tables.md`) | `infra-v1` |
| 8 | Init and reproducibility checks | `python scripts/init_check.py`<br>`python scripts/repro_check.py` | `results/init_check.json`, `results/repro_check.json` | `infra-v1.1` (rules `rules-v2.1`) |
| 9 | LR search | `python scripts/lr_search.py --model own_cnn`<br>`python scripts/lr_search.py --model mobilenet_v3_small`<br>`python scripts/lr_search.py --model resnet18` | `results/lr_search/<model>.json`, one run folder per candidate LR | `search-v1` |
| 10 | Final training | `python scripts/train.py --model own_cnn --seed 42 --lr 3e-3 --category train` (and `--seed 43`, `--seed 44`)<br>`python scripts/train.py --model mobilenet_v3_small --seed 42 --lr 3e-3 --category train` (and `--seed 43`, `--seed 44`)<br>`python scripts/train.py --model resnet18 --seed 42 --lr 1e-3 --category train` | `checkpoints/<run_id>.pt` (not committed), `runs/<run_id>/eval_log.csv`, `runs/<run_id>/metrics.json`, `results/val_predictions/<run_id>.csv` | `train-v1` |
| 11 | Ablations (seed 42, parent LR) | `python scripts/train.py --model own_cnn --lr 3e-3 --resolution 256x192`<br>`python scripts/train.py --model own_cnn_ds --lr 3e-3 --resolution 128x96`<br>`python scripts/train.py --model resnet18 --lr 1e-3 --amp`<br>`python scripts/train.py --model resnet18 --lr 1e-3 --max-steps 600`<br>`python scripts/bn_diagnostic.py --checkpoint checkpoints/<seed-42 run>.pt [--order cache]` | as step 10, plus `results/bn_diagnostic/` | `ablation-v1` |
| 12 | Measurement (latency, energy per prediction) | `python scripts/measure.py --model mean`<br>`python scripts/measure.py --model brightness`<br>`python scripts/measure.py --model own_cnn --checkpoint checkpoints/20261110-231256_train_own_cnn_73cc.pt`<br>`python scripts/measure.py --model mobilenet_v3_small --checkpoint checkpoints/20261110-231518_train_mobilenet_v3_small_c673.pt`<br>`python scripts/measure.py --model resnet18 --checkpoint checkpoints/20261110-232008_train_resnet18_c1c4.pt` | `results/measure/<model>.json` | `test-v1` |
| 13 | Test evaluation | `python scripts/evaluate_test.py --model mean`, then `--model brightness`, then `--model own_cnn`, `mobilenet_v3_small` and `resnet18`, each with `--checkpoint` as in step 12 | `results/test_log.csv`, `results/test_predictions/`, `runs/<run_id>/metrics.json` | `test-v1` |
| 14 | Results table | `python scripts/results.py` | `results/results.csv`, `results/results_summary.json`, `results/test_mae_by_blur.csv`, `results/test_residuals_by_count.csv` | `test-v1` |
| 15 | Diagnostics (val only) | `python scripts/diagnostics.py` | `results/diagnostics/` | `analysis-v1` |
| 16 | Figures | `python scripts/figures.py` | `results/figures/*.png` (300 dpi) and `*.pdf`, `results/figures/main_points.csv` | `analysis-v2` (v1: `analysis-v1`) |
| 17 | Savings | `python scripts/savings.py` | `results/savings.json` | `analysis-v2` |
| 18 | Summary | `python scripts/summary.py` | `results/summary.md` (every number the report cites, with its source file) | `analysis-v2` |

Notes:

- **Step 13 runs once per model and is already done.** Section 9 of `docs/decision_rules.md` allows one
  test run per final model. The five runs are in `results/test_log.csv` (`20261111-190407` to
  `20261111-190521`). `evaluate_test.py` refuses a second run unless `--force --reason "..."` is given. To
  reproduce the reported test numbers, use the committed `results/test_predictions/` and run step 14. Do
  not run step 13 again.
- Final models are the seed-42 runs at 128x96: `20261110-231256_train_own_cnn_73cc`,
  `20261110-231518_train_mobilenet_v3_small_c673`, `20261110-232008_train_resnet18_c1c4`.
- GPU training is not bit-exact across machines. `results/repro_check.json` shows how close two runs on
  this machine are. Energy and CO2eq depend on the hardware and on the grid intensity in `configs/rules.json`.
- Some steps ran more than once (bug fixes, re-runs under revised rules). Every run stays in `runs/index.csv`,
  and the reasons are in `ai_log/sessions/`. The table lists the command that produced the committed output.
- The report is in `report/` (`main.tex`, `ai_usage_report.tex`). It reads figures from `results/figures/`
  and `results/visual_check/`. Compile it from inside `report/`.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | Shared code: `carbon.py` (CodeCarbon `tracked_run`, run folders, `runs/index.csv`), `common.py` (paths, rules, hashing), `data.py` (cache loading), `metrics.py` (MAE/RMSE/R2, scene bootstrap CIs), `models.py` (the three CNNs and `own_cnn_ds`) |
| `scripts/` | One script per step in the table above, plus `check_env.py` |
| `configs/rules.json`, `docs/decision_rules.md` | Frozen decision rules (machine-readable / explained), versions `rules-v1` to `rules-v2.1` |
| `splits/` | `splits.csv` (one row per image, source of truth) and its SHA-256 |
| `results/` | Every committed output: decisions, visual checks, baselines, model tables, LR search, val/test predictions, measurements, results table, figures, diagnostics, savings, `summary.md` |
| `runs/` | One folder per tracked run (`config.json`, `emissions.csv`, metrics) and `index.csv` with all runs |
| `report/` | LaTeX sources of the report and the AI usage report |
| `ai_log/` | Prompts, session logs, masked transcripts, AI notes (index: `ai_log/log.md`) |
| `data/`, `checkpoints/` | Raw images, image cache, model checkpoints, ImageNet weights (git-ignored) |

## How to verify the split and cache hashes

`.gitattributes` stores `splits/`, `configs/` and `docs/` files byte for byte (no CRLF conversion), so the
hashes hold on Windows too.

```powershell
# Split: must print 43fee5789616aa731391b037575ed58695cdcc80cab4aa19bdf73f6b400a3690
Get-FileHash splits\splits.csv -Algorithm SHA256
Get-Content splits\splits.sha256
```

```powershell
# Cache: compares every data/cache/*.npz with the SHA-256 in results/cache_manifest.json
.\.venv\Scripts\python.exe -c "import json,hashlib,pathlib; m=json.load(open('results/cache_manifest.json')); [print(f['file'], 'OK' if hashlib.sha256((pathlib.Path(m['cache_dir'])/f['file']).read_bytes()).hexdigest()==f['sha256'] else 'MISMATCH') for f in m['files']]"
```

All 8 cache files (4 splits x 2 resolutions) should print `OK`. Every run's `config.json` also records the
hashes of the split and of the rules file it used.
