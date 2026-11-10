"""The CNNs of section 11.1 and 11.5 of the rules.

Own CNN, input 1 x 96 x 128:
    block 16 - pool - block 32 - pool - block 64 - pool - block 64 - global average pool - linear
Depthwise-separable variant: blocks 2-4 are split into a depthwise and a 1x1 convolution.
Standard models: ResNet-18 and MobileNetV3-Small with ImageNet weights, 1 input channel, 1 output.

Every model returns a tensor of shape (N, 1) and predicts count / 100.
"""

import torch
from torch import nn
from torchvision import models

from src.common import PROJECT_ROOT, load_rules

# Downloaded ImageNet weights stay inside the project: checkpoints/hub/checkpoints/ (git-ignored).
HUB_DIR = PROJECT_ROOT / "checkpoints" / "hub"
torch.hub.set_dir(str(HUB_DIR))

OUTPUT_BIAS = load_rules()["training"]["output_bias_init"]  # 0.5005 = train mean count / 100.
# rules-v2.1: the output weights start at 0, so every model starts at the mean baseline.
assert load_rules()["training"]["output_weight_init"] == "zeros"
OWN_MODELS = ["own_cnn", "own_cnn_ds"]
STANDARD_MODELS = ["resnet18", "mobilenet_v3_small"]
ALL_MODELS = OWN_MODELS + STANDARD_MODELS


def conv_block(in_channels, out_channels):
    """Block of the own CNN: 3x3 conv (padding 1 keeps H and W, no bias), BatchNorm, ReLU."""
    return [
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    ]


def separable_block(in_channels, out_channels):
    """Depthwise-separable block (section 11.5): 3x3 depthwise, BN, ReLU, 1x1, BN, ReLU."""
    return [
        # groups=in_channels: each channel gets its own 3x3 filter, nothing mixes channels.
        nn.Conv2d(
            in_channels, in_channels, kernel_size=3, padding=1, groups=in_channels, bias=False
        ),
        nn.BatchNorm2d(in_channels),
        nn.ReLU(inplace=True),
        # The 1x1 convolution mixes the channels and sets the output width.
        nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    ]


class OwnCNN(nn.Module):
    """Own CNN. depthwise=True gives the depthwise-separable variant (block 1 stays normal)."""

    def __init__(self, depthwise=False):
        super().__init__()
        block = separable_block if depthwise else conv_block
        self.features = nn.Sequential(
            *conv_block(1, 16),
            nn.AvgPool2d(2),
            *block(16, 32),
            nn.AvgPool2d(2),
            *block(32, 64),
            nn.AvgPool2d(2),
            *block(64, 64),
            nn.AdaptiveAvgPool2d(1),  # Global average pooling: 64 x H x W -> 64 x 1 x 1.
            nn.Flatten(),  # 64 x 1 x 1 -> 64.
        )
        self.head = nn.Linear(64, 1)

    def forward(self, x):
        return self.head(self.features(x))


def one_channel_conv(old):
    """Copy a 3-channel conv as a 1-channel conv, with its weights summed over RGB (section 6)."""
    new = nn.Conv2d(
        1,
        old.out_channels,
        kernel_size=old.kernel_size,
        stride=old.stride,
        padding=old.padding,
        bias=False,
    )
    # Weight shape: out_channels x 3 x k x k. keepdim keeps the middle axis, now with size 1.
    new.weight.data = old.weight.data.sum(dim=1, keepdim=True)
    return new


def build_standard(name, pretrained=True):
    """ResNet-18 or MobileNetV3-Small with 1 input channel and 1 output.

    pretrained=False skips the ImageNet weights. Only for counting parameters and MACs and for
    loading our own checkpoints, where every weight is replaced anyway.
    """
    if name == "resnet18":
        weights = models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.resnet18(weights=weights)
        model.conv1 = one_channel_conv(model.conv1)
        model.fc = nn.Linear(model.fc.in_features, 1)
    elif name == "mobilenet_v3_small":
        weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.mobilenet_v3_small(weights=weights, dropout=0.0)  # Section 11.1.
        model.features[0][0] = one_channel_conv(model.features[0][0])
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 1)
    else:
        raise ValueError(f"Unknown standard model: {name}")
    return model


def output_layer(model):
    """Return the last linear layer of any of the models."""
    if isinstance(model, OwnCNN):
        return model.head
    if isinstance(model, models.ResNet):
        return model.fc
    return model.classifier[-1]


def build_model(name, pretrained=True):
    """Build any model by name and start its output at the mean target (section 11.1).

    Head weights 0 and bias 0.5005: at step 0 every image gets 0.5005, i.e. 50.05 cells.
    """
    if name == "own_cnn":
        model = OwnCNN(depthwise=False)
    elif name == "own_cnn_ds":
        model = OwnCNN(depthwise=True)
    else:
        model = build_standard(name, pretrained)
    head = output_layer(model)
    nn.init.zeros_(head.weight)  # rules-v2.1: the output ignores the features at the start.
    nn.init.constant_(head.bias, OUTPUT_BIAS)
    return model


@torch.no_grad()
def predict(model, images, batch_size=32):
    """Return the raw predictions in cells as a CPU tensor. Eval mode, no clipping (section 6)."""
    was_training = model.training
    model.eval()  # BatchNorm uses its running statistics.
    outputs = [
        model(images[start : start + batch_size]).squeeze(1).float()
        for start in range(0, len(images), batch_size)
    ]
    model.train(was_training)
    return torch.cat(outputs).cpu() * 100  # Model output is count / 100.
