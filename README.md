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
