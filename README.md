# DL-Project

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
