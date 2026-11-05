# Model tables

Made by `scripts/layer_table.py`. See its docstring.

## own_cnn at 128x96

| layer | type | output_shape | params | receptive_field | jump | macs |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Conv2d | 16 x 96 x 128 | 144 | 3 | 1 | 1769472 |
| 2 | BatchNorm2d | 16 x 96 x 128 | 32 | 3 | 1 | 0 |
| 3 | ReLU | 16 x 96 x 128 | 0 | 3 | 1 | 0 |
| 4 | AvgPool2d | 16 x 48 x 64 | 0 | 4 | 2 | 0 |
| 5 | Conv2d | 32 x 48 x 64 | 4608 | 8 | 2 | 14155776 |
| 6 | BatchNorm2d | 32 x 48 x 64 | 64 | 8 | 2 | 0 |
| 7 | ReLU | 32 x 48 x 64 | 0 | 8 | 2 | 0 |
| 8 | AvgPool2d | 32 x 24 x 32 | 0 | 10 | 4 | 0 |
| 9 | Conv2d | 64 x 24 x 32 | 18432 | 18 | 4 | 14155776 |
| 10 | BatchNorm2d | 64 x 24 x 32 | 128 | 18 | 4 | 0 |
| 11 | ReLU | 64 x 24 x 32 | 0 | 18 | 4 | 0 |
| 12 | AvgPool2d | 64 x 12 x 16 | 0 | 22 | 8 | 0 |
| 13 | Conv2d | 64 x 12 x 16 | 36864 | 38 | 8 | 7077888 |
| 14 | BatchNorm2d | 64 x 12 x 16 | 128 | 38 | 8 | 0 |
| 15 | ReLU | 64 x 12 x 16 | 0 | 38 | 8 | 0 |
| 16 | AdaptiveAvgPool2d | 64 x 1 x 1 | 0 | whole image | - | 0 |
| 17 | Flatten | 64 | 0 | whole image | - | 0 |
| 18 | Linear | 1 | 65 | whole image | - | 64 |

## own_cnn at 256x192

| layer | type | output_shape | params | receptive_field | jump | macs |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Conv2d | 16 x 192 x 256 | 144 | 3 | 1 | 7077888 |
| 2 | BatchNorm2d | 16 x 192 x 256 | 32 | 3 | 1 | 0 |
| 3 | ReLU | 16 x 192 x 256 | 0 | 3 | 1 | 0 |
| 4 | AvgPool2d | 16 x 96 x 128 | 0 | 4 | 2 | 0 |
| 5 | Conv2d | 32 x 96 x 128 | 4608 | 8 | 2 | 56623104 |
| 6 | BatchNorm2d | 32 x 96 x 128 | 64 | 8 | 2 | 0 |
| 7 | ReLU | 32 x 96 x 128 | 0 | 8 | 2 | 0 |
| 8 | AvgPool2d | 32 x 48 x 64 | 0 | 10 | 4 | 0 |
| 9 | Conv2d | 64 x 48 x 64 | 18432 | 18 | 4 | 56623104 |
| 10 | BatchNorm2d | 64 x 48 x 64 | 128 | 18 | 4 | 0 |
| 11 | ReLU | 64 x 48 x 64 | 0 | 18 | 4 | 0 |
| 12 | AvgPool2d | 64 x 24 x 32 | 0 | 22 | 8 | 0 |
| 13 | Conv2d | 64 x 24 x 32 | 36864 | 38 | 8 | 28311552 |
| 14 | BatchNorm2d | 64 x 24 x 32 | 128 | 38 | 8 | 0 |
| 15 | ReLU | 64 x 24 x 32 | 0 | 38 | 8 | 0 |
| 16 | AdaptiveAvgPool2d | 64 x 1 x 1 | 0 | whole image | - | 0 |
| 17 | Flatten | 64 | 0 | whole image | - | 0 |
| 18 | Linear | 1 | 65 | whole image | - | 64 |

## own_cnn_ds at 128x96

| layer | type | output_shape | params | receptive_field | jump | macs |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Conv2d | 16 x 96 x 128 | 144 | 3 | 1 | 1769472 |
| 2 | BatchNorm2d | 16 x 96 x 128 | 32 | 3 | 1 | 0 |
| 3 | ReLU | 16 x 96 x 128 | 0 | 3 | 1 | 0 |
| 4 | AvgPool2d | 16 x 48 x 64 | 0 | 4 | 2 | 0 |
| 5 | Conv2d | 16 x 48 x 64 | 144 | 8 | 2 | 442368 |
| 6 | BatchNorm2d | 16 x 48 x 64 | 32 | 8 | 2 | 0 |
| 7 | ReLU | 16 x 48 x 64 | 0 | 8 | 2 | 0 |
| 8 | Conv2d | 32 x 48 x 64 | 512 | 8 | 2 | 1572864 |
| 9 | BatchNorm2d | 32 x 48 x 64 | 64 | 8 | 2 | 0 |
| 10 | ReLU | 32 x 48 x 64 | 0 | 8 | 2 | 0 |
| 11 | AvgPool2d | 32 x 24 x 32 | 0 | 10 | 4 | 0 |
| 12 | Conv2d | 32 x 24 x 32 | 288 | 18 | 4 | 221184 |
| 13 | BatchNorm2d | 32 x 24 x 32 | 64 | 18 | 4 | 0 |
| 14 | ReLU | 32 x 24 x 32 | 0 | 18 | 4 | 0 |
| 15 | Conv2d | 64 x 24 x 32 | 2048 | 18 | 4 | 1572864 |
| 16 | BatchNorm2d | 64 x 24 x 32 | 128 | 18 | 4 | 0 |
| 17 | ReLU | 64 x 24 x 32 | 0 | 18 | 4 | 0 |
| 18 | AvgPool2d | 64 x 12 x 16 | 0 | 22 | 8 | 0 |
| 19 | Conv2d | 64 x 12 x 16 | 576 | 38 | 8 | 110592 |
| 20 | BatchNorm2d | 64 x 12 x 16 | 128 | 38 | 8 | 0 |
| 21 | ReLU | 64 x 12 x 16 | 0 | 38 | 8 | 0 |
| 22 | Conv2d | 64 x 12 x 16 | 4096 | 38 | 8 | 786432 |
| 23 | BatchNorm2d | 64 x 12 x 16 | 128 | 38 | 8 | 0 |
| 24 | ReLU | 64 x 12 x 16 | 0 | 38 | 8 | 0 |
| 25 | AdaptiveAvgPool2d | 64 x 1 x 1 | 0 | whole image | - | 0 |
| 26 | Flatten | 64 | 0 | whole image | - | 0 |
| 27 | Linear | 1 | 65 | whole image | - | 64 |

## own_cnn_ds at 256x192

| layer | type | output_shape | params | receptive_field | jump | macs |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Conv2d | 16 x 192 x 256 | 144 | 3 | 1 | 7077888 |
| 2 | BatchNorm2d | 16 x 192 x 256 | 32 | 3 | 1 | 0 |
| 3 | ReLU | 16 x 192 x 256 | 0 | 3 | 1 | 0 |
| 4 | AvgPool2d | 16 x 96 x 128 | 0 | 4 | 2 | 0 |
| 5 | Conv2d | 16 x 96 x 128 | 144 | 8 | 2 | 1769472 |
| 6 | BatchNorm2d | 16 x 96 x 128 | 32 | 8 | 2 | 0 |
| 7 | ReLU | 16 x 96 x 128 | 0 | 8 | 2 | 0 |
| 8 | Conv2d | 32 x 96 x 128 | 512 | 8 | 2 | 6291456 |
| 9 | BatchNorm2d | 32 x 96 x 128 | 64 | 8 | 2 | 0 |
| 10 | ReLU | 32 x 96 x 128 | 0 | 8 | 2 | 0 |
| 11 | AvgPool2d | 32 x 48 x 64 | 0 | 10 | 4 | 0 |
| 12 | Conv2d | 32 x 48 x 64 | 288 | 18 | 4 | 884736 |
| 13 | BatchNorm2d | 32 x 48 x 64 | 64 | 18 | 4 | 0 |
| 14 | ReLU | 32 x 48 x 64 | 0 | 18 | 4 | 0 |
| 15 | Conv2d | 64 x 48 x 64 | 2048 | 18 | 4 | 6291456 |
| 16 | BatchNorm2d | 64 x 48 x 64 | 128 | 18 | 4 | 0 |
| 17 | ReLU | 64 x 48 x 64 | 0 | 18 | 4 | 0 |
| 18 | AvgPool2d | 64 x 24 x 32 | 0 | 22 | 8 | 0 |
| 19 | Conv2d | 64 x 24 x 32 | 576 | 38 | 8 | 442368 |
| 20 | BatchNorm2d | 64 x 24 x 32 | 128 | 38 | 8 | 0 |
| 21 | ReLU | 64 x 24 x 32 | 0 | 38 | 8 | 0 |
| 22 | Conv2d | 64 x 24 x 32 | 4096 | 38 | 8 | 3145728 |
| 23 | BatchNorm2d | 64 x 24 x 32 | 128 | 38 | 8 | 0 |
| 24 | ReLU | 64 x 24 x 32 | 0 | 38 | 8 | 0 |
| 25 | AdaptiveAvgPool2d | 64 x 1 x 1 | 0 | whole image | - | 0 |
| 26 | Flatten | 64 | 0 | whole image | - | 0 |
| 27 | Linear | 1 | 65 | whole image | - | 64 |

## Totals

| model | resolution | params | macs | receptive_field | params_by_hand | macs_by_hand |
| --- | --- | --- | --- | --- | --- | --- |
| own_cnn | 128x96 | 60465 | 37158976 | 38 | 60465 | 37158976 |
| own_cnn | 256x192 | 60465 | 148635712 | 38 | 60465 | 148635712 |
| own_cnn_ds | 128x96 | 8449 | 6475840 | 38 | 8449 | 6475840 |
| own_cnn_ds | 256x192 | 8449 | 25903168 | 38 | 8449 | 25903168 |
| resnet18 | 128x96 | 11170753 | 424870400 | nan | nan | nan |
| resnet18 | 256x192 | 11170753 | 1699480064 | nan | nan | nan |
| mobilenet_v3_small | 128x96 | 1518593 | 13496576 | nan | nan | nan |
| mobilenet_v3_small | 256x192 | 1518593 | 50837504 | nan | nan | nan |

## Checks

| check | result |
| --- | --- |
| own_cnn 128x96: hand params = numel | PASS |
| own_cnn 128x96: hand MACs = FlopCounterMode | PASS |
| own_cnn 128x96: params = 60465 | PASS |
| own_cnn 128x96: MACs = 37158976 | PASS |
| own_cnn 256x192: hand params = numel | PASS |
| own_cnn 256x192: hand MACs = FlopCounterMode | PASS |
| own_cnn 256x192: params = 60465 | PASS |
| own_cnn 256x192: MACs = 148635712 | PASS |
| own_cnn_ds 128x96: hand params = numel | PASS |
| own_cnn_ds 128x96: hand MACs = FlopCounterMode | PASS |
| own_cnn_ds 128x96: params = 8449 | PASS |
| own_cnn_ds 128x96: MACs = 6475840 | PASS |
| own_cnn_ds 256x192: hand params = numel | PASS |
| own_cnn_ds 256x192: hand MACs = FlopCounterMode | PASS |
| own_cnn_ds 256x192: params = 8449 | PASS |
| own_cnn_ds 256x192: MACs = 25903168 | PASS |
| resnet18 128x96: params = 11170753 | PASS |
| resnet18 128x96: MACs = 424870400 | PASS |
| resnet18 256x192: params = 11170753 | PASS |
| resnet18 256x192: MACs = 1699480064 | PASS |
| mobilenet_v3_small 128x96: params = 1518593 | PASS |
| mobilenet_v3_small 128x96: MACs = 13496576 | PASS |
| mobilenet_v3_small 256x192: params = 1518593 | PASS |
| mobilenet_v3_small 256x192: MACs = 50837504 | PASS |
| own_cnn: receptive field = 38 | PASS |
