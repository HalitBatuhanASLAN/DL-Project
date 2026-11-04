"""Environment check: library versions, CUDA availability and a CodeCarbon smoke test.

Usage (from the project root, inside the activated .venv):
    python scripts/check_env.py
"""
import platform
import sys
import time
from pathlib import Path

import codecarbon
import numpy as np
import torch
import torchvision
from codecarbon import OfflineEmissionsTracker
from codecarbon.external.hardware import CPU, GPU

ROOT = Path(__file__).resolve().parents[1]
SMOKE_SECONDS = 10.0
MATRIX_SIZE = 4096  # 3 x 64 MB float32 tensors, fits easily in 4 GB VRAM


def print_versions() -> bool:
    cuda_ok = torch.cuda.is_available()
    cudnn = torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
    print("=== Versions ===")
    print(f"Python             : {sys.version.split()[0]} ({platform.system()} {platform.release()})")
    print(f"torch              : {torch.__version__}")
    print(f"torch CUDA version : {torch.version.cuda}")
    print(f"cuDNN version      : {cudnn}")
    print(f"torchvision        : {torchvision.__version__}")
    print(f"numpy              : {np.__version__}")
    print(f"codecarbon         : {codecarbon.__version__}")
    print("=== CUDA ===")
    print(f"torch.cuda.is_available(): {cuda_ok}")
    if cuda_ok:
        props = torch.cuda.get_device_properties(0)
        print(f"GPU name           : {torch.cuda.get_device_name(0)}")
        print(f"GPU memory         : {props.total_memory / 1024**3:.2f} GB")
        print(f"Compute capability : {props.major}.{props.minor}")
    return cuda_ok


def smoke_test(device: torch.device) -> None:
    out_dir = ROOT / "runs" / "_env_check"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== CodeCarbon smoke test ({SMOKE_SECONDS:.0f} s of matmuls on {device}) ===")

    a = torch.randn(MATRIX_SIZE, MATRIX_SIZE, device=device)
    b = torch.randn(MATRIX_SIZE, MATRIX_SIZE, device=device)

    tracker = OfflineEmissionsTracker(
        country_iso_code="TUR",
        project_name="env_check",
        output_dir=str(out_dir),
        log_level="error",
    )
    tracker.start()
    iters = 0
    t0 = time.perf_counter()
    try:
        while time.perf_counter() - t0 < SMOKE_SECONDS:
            c = a @ b
            if device.type == "cuda":
                torch.cuda.synchronize()
            iters += 1
    finally:
        emissions_kg = tracker.stop()
    elapsed = time.perf_counter() - t0

    data = tracker.final_emissions_data
    hardware = getattr(tracker, "_hardware", [])
    gpu_measured = any(isinstance(h, GPU) for h in hardware)
    cpu_modes = [getattr(h, "_mode", "?") for h in hardware if isinstance(h, CPU)]
    tflops = 2 * MATRIX_SIZE**3 * iters / elapsed / 1e12

    print(f"Iterations         : {iters} in {elapsed:.1f} s (~{tflops:.2f} TFLOP/s), checksum {c.sum().item():.3e}")
    print(f"Energy consumed    : {data.energy_consumed:.8f} kWh")
    print(f"  CPU / GPU / RAM  : {data.cpu_energy:.8f} / {data.gpu_energy:.8f} / {data.ram_energy:.8f} kWh")
    print(f"Emissions          : {emissions_kg:.8f} kg CO2eq")
    print(f"Country / region   : {data.country_name} ({data.country_iso_code})")
    print(f"GPU seen by CC     : {data.gpu_model or '-'} (count={data.gpu_count:.0f})")
    if gpu_measured:
        print("GPU energy         : MEASURED via NVML (pynvml)")
    else:
        print("GPU energy         : NOT measured (no NVIDIA GPU detected by CodeCarbon)")
    for mode in cpu_modes:
        how = "ESTIMATED from CPU TDP (constant mode)" if mode == "constant" else f"measured ({mode})"
        print(f"CPU energy         : {how}")
    print("RAM energy         : ESTIMATED (CodeCarbon RAM power model)")
    print(f"emissions.csv      : {out_dir / 'emissions.csv'}")


def main() -> int:
    cuda_ok = print_versions()
    device = torch.device("cuda" if cuda_ok else "cpu")
    if not cuda_ok:
        print("\nWARNING: CUDA is not available; running the smoke test on CPU.")
    smoke_test(device)
    return 0 if cuda_ok else 1


if __name__ == "__main__":
    sys.exit(main())
