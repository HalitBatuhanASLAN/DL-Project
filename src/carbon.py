"""Carbon tracking helper, implementing section 10 of docs/decision_rules.md.

Every compute script runs inside tracked_run():

    with tracked_run(category="train", model="own_cnn", config={"seed": 42}) as run_dir:
        ...  # the work; run_dir is the folder runs/<run_id>/

Each run leaves emissions.csv, config.json and metrics.json in its folder and one
row in runs/index.csv.
"""

import csv
import ctypes
import hashlib
import json
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime

import codecarbon
import torch
from codecarbon import OfflineEmissionsTracker

from src.common import PROJECT_ROOT, RULES_PATH, RUNS_DIR, SPLITS_DIR, load_rules, sha256

INDEX_CSV = RUNS_DIR / "index.csv"
INDEX_COLUMNS = [
    "run_id",
    "start_time",
    "category",
    "model",
    "status",
    "duration_s",
    "energy_kwh",
    "emissions_kg",
    "short_run",
    "notes",
]


def append_index_row(row):
    """Append one run to runs/index.csv. Missing columns stay empty."""
    write_header = not INDEX_CSV.exists()
    with open(INDEX_CSV, "a", newline="", encoding="utf-8") as file:
        # extrasaction="raise" (the default) catches a misspelled column name.
        writer = csv.DictWriter(file, fieldnames=INDEX_COLUMNS, lineterminator="\n")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def git_commit():
    """Return the current git commit hash, or None if git is not available."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def power_source():
    """Return "AC", "battery" or "unknown". Windows only, otherwise "unknown"."""
    try:
        # SYSTEM_POWER_STATUS is a 12-byte struct; its first byte is the AC line status.
        status = ctypes.create_string_buffer(12)
        ctypes.windll.kernel32.GetSystemPowerStatus(status)
        return {0: "battery", 1: "AC"}.get(status.raw[0], "unknown")
    except AttributeError:  # ctypes.windll does not exist outside Windows.
        return "unknown"


def describe_environment(config):
    """Collect what config.json records about a run."""
    splits_file = SPLITS_DIR / "splits.csv"
    cuda_available = torch.cuda.is_available()
    return {
        "args": config,
        "seed": config.get("seed"),
        "command": sys.argv,
        "git_commit": git_commit(),
        "rules_sha256": sha256(RULES_PATH),
        "splits_sha256": sha256(splits_file) if splits_file.exists() else None,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "codecarbon_version": codecarbon.__version__,
        "gpu_name": torch.cuda.get_device_name(0) if cuda_available else None,
        "power_source": power_source(),
    }


@contextmanager
def tracked_run(category, model, config=None, notes=""):
    """Measure one script run and record it in runs/. Exceptions are re-raised.

    notes goes into the notes column of runs/index.csv. A script may write its own results to
    run_dir/metrics.json; they are kept, and the tracker's numbers are added to them.
    """
    config = config or {}
    rules = load_rules()["carbon"]
    if category not in rules["categories"]:
        raise ValueError(f"Unknown category: {category}")

    # hash4: the first 4 hex digits of the config, so a different config gets a new name.
    started = datetime.now()
    config_text = json.dumps(config, sort_keys=True)
    hash4 = hashlib.sha256(config_text.encode("utf-8")).hexdigest()[:4]
    run_id = f"{started:%Y%m%d-%H%M%S}_{category}_{model}_{hash4}"

    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True)
    config_path = run_dir / "config.json"
    config_path.write_text(json.dumps(describe_environment(config), indent=2), encoding="utf-8")

    tracker = OfflineEmissionsTracker(
        country_iso_code=rules["country_iso_code"],
        measure_power_secs=rules["measure_power_secs"],
        output_dir=str(run_dir),
        project_name=run_id,
    )
    tracker.start()
    start_time = time.perf_counter()
    status = "ok"
    error_type = None
    error_message = None

    try:
        yield run_dir
    except BaseException as error:  # BaseException also covers SystemExit and Ctrl+C.
        status = "failed"
        error_type = type(error).__name__
        error_message = str(error)
        raise  # The finally block below still runs before the exception leaves.
    finally:
        emissions_kg = tracker.stop()
        duration_s = time.perf_counter() - start_time
        energy_kwh = float(tracker.final_emissions_data.energy_consumed)
        short_run = duration_s < rules["short_run_factor"] * rules["measure_power_secs"]

        metrics = {
            "status": status,
            "error_type": error_type,
            "error_message": error_message,
            "duration_s": duration_s,
            "energy_kwh": energy_kwh,
            "emissions_kg": emissions_kg,
            "short_run": short_run,
        }
        metrics_path = run_dir / "metrics.json"
        if metrics_path.exists():  # The script wrote its own results: keep them.
            metrics = {**json.loads(metrics_path.read_text(encoding="utf-8")), **metrics}
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        append_index_row(
            {
                "run_id": run_id,
                "start_time": started.isoformat(timespec="seconds"),
                "category": category,
                "model": model,
                "status": status,
                "duration_s": duration_s,
                "energy_kwh": energy_kwh,
                "emissions_kg": emissions_kg,
                "short_run": short_run,
                "notes": "; ".join(text for text in (notes, error_type) if text),
            }
        )
