# P08.3.3 Full ANN Training Gate

## Purpose

P08.3.3 executes the already-frozen P08.3.1 ANN policy on the real MNIST training
split after the deterministic training/checkpoint machinery was accepted in
P08.3.2.

This gate does not tune hyperparameters and does not evaluate the official MNIST
test split.

## Frozen execution boundary

```text
source split:             official MNIST 60,000-image training split
training subset:          deterministic 55,000 images
validation subset:        deterministic stratified 5,000 images
validation seed:          0x4D4E4953
model parameters:         7,006
batch size:               32
optimizer:                Adam
learning rate:            1e-3
maximum epochs:           30
early-stop patience:      5
checkpoint selection:     maximum val_accuracy
first tie-breaker:        minimum val_loss
second tie-breaker:       earliest epoch
official test evaluation: prohibited
```

The ANN topology and training choices are unchanged from
`P08_3_TRAINING_CONVERSION_FREEZE.md`.

## Predeclared sanity floor

Before observing the real validation result, P08.3.3 defines:

```text
minimum accepted best validation accuracy = 0.95
```

This is a project engineering sanity floor, **not** a target accuracy, a claim
about the NxTF benchmark, or permission to retune the frozen policy. Its purpose
is only to catch a grossly broken data/model/training path before conversion.

If the frozen run is below 95%, first investigate implementation correctness.
Do not change topology, optimizer, batch size, dropout, epoch policy, or other
frozen choices merely to make this gate pass. If the implementation is correct
and the reconstruction genuinely underperforms, record that discrepancy rather
than tuning against validation until it disappears.

The observed validation result above the sanity floor is reported as-is.

## Required artifact

The canonical local candidate directory is:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_3_full_ann/
```

It contains at minimum:

```text
selected_ann.keras
training_manifest.json
training.log
gate_result.json
```

Generated model artifacts are intentionally ignored by Git. Their identities are
recorded through SHA-256 and tensor-level fingerprints so later conversion can
bind to the exact locally accepted checkpoint without committing a binary model.

## Acceptance checks

The full-training gate must verify all of the following after training:

1. `mode == full-55k-5k`;
2. 55,000 training examples and 5,000 validation examples;
3. zero test examples observed by training/checkpoint-selection logic;
4. `official_test_used == false`;
5. checkpoint selection source is exactly `fixed_validation_split_only`;
6. model parameter count remains 7,006;
7. maximum epoch policy remains 30 and early-stop patience remains 5;
8. selected epoch is within the recorded history;
9. selected validation accuracy/loss equal the best record under the frozen
   ordering: highest accuracy, then lowest loss, then earliest epoch;
10. best validation accuracy is at least the predeclared 0.95 sanity floor;
11. selected checkpoint SHA-256 matches the manifest;
12. reloaded model tensor fingerprint matches the manifest;
13. manifest fingerprint recomputes exactly; and
14. all required metrics are finite.

Passing this gate accepts one ANN checkpoint for the subsequent conversion stage.
The official test split remains locked after P08.3.3; full ANN test accuracy is
reserved for P08.4 after conversion policy and converted SNN are also frozen.
