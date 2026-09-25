# MNIST-03 Accepted Software SNN Training Baselines

**Status:** Complete

## Purpose

MNIST-03 establishes reproducible floating-point SNN baselines for both FPGA-v1
application profiles before project-specific quantization. The training workflow
reuses the user-authored TensorFlow/Keras MNIST lab structure where appropriate
(dataset loading, Adam optimization, sparse categorical cross-entropy, elapsed
training time, argmax predictions, and incorrect-sample indexing) while replacing
the ANN forward path with the application's explicit integrate-and-fire dynamics.

## Accepted methodology

The accepted runs use a deterministic stratified validation split drawn only
from the official 60,000-image MNIST training split:

```text
55,000 training images
 5,000 validation images
10,000 official test images
```

The validation split is generated with the application seed `0x4D4E4953` and is
used for all checkpoint/model-selection decisions. The official test split is
not evaluated until the selected checkpoint is frozen.

Both profiles use:

```text
presentation ticks: 16
optimizer:           Adam
learning rate:       1e-3
batch size:          128
float threshold:     1.0
output decoder:      argmax(output spike count), lowest ID breaks ties
```

The accepted runs were executed in the dedicated MNIST virtual environment with
TensorFlow 2.21. CUDA was unavailable, so TensorFlow used its CPU path; this does
not change the application model semantics.

The full MNIST application pytest suite passed before the accepted runs.

## MNIST-03A — Cropped-dense

Architecture:

```text
28x28 MNIST
 -> exact center crop [4:24, 4:24]
 -> 400 deterministic spike-encoded input axons
 -> 4,000 trainable connections
 -> 10 integrate-and-fire output neurons
```

Ten initial training epochs were run. Model selection used validation accuracy
only. The best checkpoint was epoch 10:

```text
best epoch:                 10
best validation accuracy:   0.8912
final official test accuracy: 0.9029
nonzero weights:            4000
```

The accepted checkpoint therefore uses the complete dense 400x10 connectivity
matrix and remains below the physical 4,096-synapse limit.

## MNIST-03B — Native-sparse

Architecture before pruning:

```text
28x28 native MNIST
 -> 784 deterministic spike-encoded input axons
 -> 7,840 software connections
 -> 10 integrate-and-fire output neurons
```

The dense software model was trained for ten epochs. Validation-only selection
restored epoch 8 as the best initial checkpoint:

```text
best initial epoch:               8
best initial validation accuracy: 0.9028
```

That checkpoint was magnitude-pruned deterministically to the physical budget:

```text
connections after pruning:         4096
post-prune validation accuracy:    0.8250
```

The pruning mask was then frozen and Adam was reset before five masked
fine-tuning epochs. The best fine-tuned checkpoint was epoch 2:

```text
best fine-tune epoch:              2
best fine-tune validation accuracy: 0.9092
final official test accuracy:      0.9162
nonzero weights:                   4096
```

Fine-tuning recovered 8.42 percentage points of validation accuracy relative to
the immediate post-prune network and ultimately exceeded the best dense
software validation result by 0.64 percentage points.

## Dual-profile result

The accepted floating-point baselines are:

| Profile | Input representation | Stored/trainable deployment connections | Validation-selected accuracy | Official test accuracy |
|---|---|---:|---:|---:|
| cropped-dense | 20x20 center crop | 4,000 | 89.12% | 90.29% |
| native-sparse | native 28x28 | 4,096 | 90.92% | 91.62% |

The native-sparse profile is 1.33 percentage points more accurate on the official
test set while satisfying essentially the same physical synapse budget. This is
an application-level result, not yet a hardware-performance result: MNIST-04 and
MNIST-05 must still quantify project-weight quantization and execution through
the validated integer `NeuromorphicCore` on the same test corpus.

## Completion decision

MNIST-03A and MNIST-03B are complete. Both profiles now have accepted,
validation-selected floating-point SNN checkpoints with reproducible training
configuration, fixed connection counts, and one final official test result.
