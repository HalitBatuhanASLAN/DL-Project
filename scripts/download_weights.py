"""One-time download of the ImageNet weights, section 11.1 of the rules.

The files go to checkpoints/hub/checkpoints/ (git-ignored). torchvision checks each file against
the short hash in its name; this script then prints the full SHA-256 for the README.

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\download_weights.py
"""

import json
import sys
from pathlib import Path

from torchvision.models import MobileNet_V3_Small_Weights, ResNet18_Weights

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import sha256  # noqa: E402
from src.models import HUB_DIR  # noqa: E402 (importing it also sets the download folder)

WEIGHTS = {
    "resnet18": ResNet18_Weights.IMAGENET1K_V1,
    "mobilenet_v3_small": MobileNet_V3_Small_Weights.IMAGENET1K_V1,
}


def main():
    with tracked_run(category="env", model="imagenet_weights") as run_dir:
        files = {}
        for name, weights in WEIGHTS.items():
            weights.get_state_dict(progress=False, check_hash=True)  # Downloads if not present.
            path = HUB_DIR / "checkpoints" / Path(weights.url).name
            files[name] = {
                "file": path.name,
                "url": weights.url,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            print(path.name, path.stat().st_size, files[name]["sha256"])
        (run_dir / "metrics.json").write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
