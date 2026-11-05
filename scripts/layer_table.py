"""Per-layer tables of the own CNNs, parameters and MACs of all CNNs, section 11.1 and 11.7.

For each layer of the own CNNs the numbers are computed by hand formulas, so they can be repeated
on paper, and the totals are then cross-checked against two independent sources:
    parameters: sum(p.numel()) over the model
    MACs:       torch.utils.flop_counter.FlopCounterMode, 2 flops = 1 MAC

Formulas, for a layer with input C x H x W:
    Conv2d    params = k * k * C_in / groups * C_out      MACs = params * H_out * W_out
    BatchNorm params = 2 * C (scale and shift)            MACs = 0
    Linear    params = in * out + out                     MACs = in * out
    Pool      no params                                   MACs = 0
Receptive field r and jump j, starting from r = 1, j = 1:
    r = r + (k - 1) * j     then     j = j * stride

Uses no data and no ImageNet weights: only zero tensors of the right size.

Output: results/model_tables/layers_<model>_<resolution>.csv     one table per model and resolution
        results/model_tables/totals.csv                          all totals and checks
        results/model_tables/model_tables.md                     the same as Markdown

Run with the project virtual environment, after committing this script:
    .venv\\Scripts\\python.exe scripts\\layer_table.py
"""

import sys
from pathlib import Path

import pandas as pd
import torch
from torch import nn
from torch.utils.flop_counter import FlopCounterMode

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # Lets Python find the src package.

from src.carbon import tracked_run  # noqa: E402 (needs the line above)
from src.common import RESULTS_DIR, load_rules  # noqa: E402
from src.models import ALL_MODELS, OWN_MODELS, build_model  # noqa: E402

OUT_DIR = RESULTS_DIR / "model_tables"
RESOLUTIONS = ["128x96", "256x192"]

# (params, MACs at 128x96, MACs at 256x192), from the rules and the rules-v2 size check.
EXPECTED = {
    "own_cnn": (60465, 37158976, 148635712),
    "own_cnn_ds": (8449, 6475840, 25903168),
    "resnet18": (11170753, 424870400, 1699480064),
    "mobilenet_v3_small": (1518593, 13496576, 50837504),
}
EXPECTED_RF = 38  # Receptive field at the last conv of the own CNN (section 11.1).


def input_tensor(resolution):
    """Return a zero tensor 1 x 1 x H x W for a name such as "128x96" (width x height)."""
    width, height = (int(side) for side in resolution.split("x"))
    return torch.zeros(1, 1, height, width)


def layer_row(index, layer, in_shape, out_shape, rf, jump):
    """Return one table row and the new (rf, jump), using the hand formulas above."""
    channels, height, width = in_shape[1], in_shape[-2], in_shape[-1]
    params, macs = 0, 0
    kernel, stride = None, None

    if isinstance(layer, nn.Conv2d):
        kernel, stride = layer.kernel_size[0], layer.stride[0]
        params = kernel**2 * channels // layer.groups * layer.out_channels
        macs = params * out_shape[-2] * out_shape[-1]
    elif isinstance(layer, nn.BatchNorm2d):
        params = 2 * channels
    elif isinstance(layer, nn.AvgPool2d):
        kernel, stride = layer.kernel_size, layer.stride
    elif isinstance(layer, nn.Linear):
        params = layer.in_features * layer.out_features + layer.out_features
        macs = layer.in_features * layer.out_features

    is_global = isinstance(layer, (nn.AdaptiveAvgPool2d, nn.Flatten, nn.Linear))
    if kernel is not None:
        rf = rf + (kernel - 1) * jump
        jump = jump * stride

    row = {
        "layer": index,
        "type": type(layer).__name__,
        "output_shape": " x ".join(str(side) for side in out_shape[1:]),
        "params": params,
        # After global pooling every output sees the whole image.
        "receptive_field": "whole image" if is_global else rf,
        "jump": "-" if is_global else jump,
        "macs": macs,
    }
    return row, rf, jump


def per_layer_table(model, resolution):
    """Pass a zero tensor through the layers one by one and return the table as a DataFrame."""
    layers = list(model.features) + [model.head]
    x = input_tensor(resolution)
    rf, jump = 1, 1
    rows = []
    with torch.no_grad():
        for index, layer in enumerate(layers, start=1):
            in_shape = tuple(x.shape)
            x = layer(x)
            row, rf, jump = layer_row(index, layer, in_shape, tuple(x.shape), rf, jump)
            rows.append(row)
    return pd.DataFrame(rows)


def counted_macs(model, resolution):
    """Return the MACs from FlopCounterMode. Eval mode, so BatchNorm counts as 0 (section 11.7)."""
    model.eval()
    with torch.no_grad(), FlopCounterMode(model, display=False) as counter:
        model(input_tensor(resolution))
    return counter.get_total_flops() // 2


def markdown_table(table):
    """Return a DataFrame as a Markdown table (pandas' own version needs an extra package)."""
    columns = [str(column) for column in table.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in table.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def main():
    rules = load_rules()
    config = {"rules_version": rules["version"], "resolutions": RESOLUTIONS}
    with tracked_run(category="measure", model="layer_table", config=config):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        markdown = ["# Model tables", "", "Made by `scripts/layer_table.py`. See its docstring."]
        totals = []
        checks = {}

        for name in ALL_MODELS:
            model = build_model(name, pretrained=False)  # Sizes do not depend on the weights.
            params_counted = sum(p.numel() for p in model.parameters())

            for position, resolution in enumerate(RESOLUTIONS):
                macs_counted = counted_macs(model, resolution)
                row = {
                    "model": name,
                    "resolution": resolution,
                    "params": params_counted,
                    "macs": macs_counted,
                }

                if name in OWN_MODELS:
                    table = per_layer_table(model, resolution)
                    table.to_csv(
                        OUT_DIR / f"layers_{name}_{resolution}.csv", index=False, lineterminator="\n"
                    )
                    markdown += ["", f"## {name} at {resolution}", "", markdown_table(table)]

                    # The last Conv2d row gives the receptive field at the last conv.
                    convs = table[table["type"] == "Conv2d"]
                    row["receptive_field"] = int(convs["receptive_field"].iloc[-1])
                    row["params_by_hand"] = int(table["params"].sum())
                    row["macs_by_hand"] = int(table["macs"].sum())
                    checks[f"{name} {resolution}: hand params = numel"] = (
                        row["params_by_hand"] == params_counted
                    )
                    checks[f"{name} {resolution}: hand MACs = FlopCounterMode"] = (
                        row["macs_by_hand"] == macs_counted
                    )

                expected_params, *expected_macs = EXPECTED[name]
                checks[f"{name} {resolution}: params = {expected_params}"] = (
                    params_counted == expected_params
                )
                checks[f"{name} {resolution}: MACs = {expected_macs[position]}"] = (
                    macs_counted == expected_macs[position]
                )
                totals.append(row)

        totals = pd.DataFrame(totals)
        own_128 = totals[(totals["model"] == "own_cnn") & (totals["resolution"] == "128x96")]
        checks[f"own_cnn: receptive field = {EXPECTED_RF}"] = (
            own_128["receptive_field"].iloc[0] == EXPECTED_RF
        )

        totals.to_csv(OUT_DIR / "totals.csv", index=False, lineterminator="\n")
        check_table = pd.DataFrame(
            [{"check": name, "result": "PASS" if ok else "FAIL"} for name, ok in checks.items()]
        )
        markdown += ["", "## Totals", "", markdown_table(totals.fillna("-").astype(str))]
        markdown += ["", "## Checks", "", markdown_table(check_table), ""]
        (OUT_DIR / "model_tables.md").write_text("\n".join(markdown), encoding="utf-8", newline="\n")

        print(totals.to_string(index=False))
        print(check_table.to_string(index=False))
        # Inside the tracked block, so that a failed check gives a run with status "failed".
        if not all(checks.values()):
            raise SystemExit("At least one layer-table check failed.")


if __name__ == "__main__":
    main()
