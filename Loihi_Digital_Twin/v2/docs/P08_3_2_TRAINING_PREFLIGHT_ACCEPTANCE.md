# P08.3.2 Deterministic Training-Pipeline Preflight Acceptance

**Accepted:** 2026-09-30  
**Gate:** `scripts/run_p08_3_2_training_preflight.sh`

## Independent local result

The deterministic training-pipeline gate passed locally in the dedicated P08
TensorFlow environment with:

```text
27 passed
```

Two independent one-epoch synthetic smoke-training runs produced identical
selected model weights and identical validation metrics:

```text
weights_fingerprint = 9e2d4e197f8d2228282f257602df52e8be8e025c8596b5b90c3990f14c4bfbfb
val_accuracy        = 0.150000
val_loss            = 2.226978
```

The `.keras` archive SHA-256 values differed between runs, as expected for an
archive/container whose metadata need not be byte-identical. Acceptance therefore
uses the tensor-level selected-weight fingerprint, not raw archive identity, as
the deterministic model-content check.

Both manifests reported:

```text
official_test_used      = false
test_examples_observed  = 0
selection_source        = fixed_validation_split_only
```

The synthetic smoke accuracy is not an application-quality result and is not used
as an acceptance threshold. The purpose of P08.3.2 was to prove deterministic
model construction, training/checkpoint wiring, validation-only selection,
serialization/reload, artifact fingerprints, and the official-test lock before
the real 55k/5k training run.

## Environment warnings

The local TensorFlow run reported no installed CUDA driver and fell back to CPU.
It also emitted an ignored `MapDataset` unknown-attribute compatibility message.
Neither warning changed the deterministic selected-weight fingerprint or caused a
gate failure.

## Advancement

P08.3.2 is accepted. P08.3.3 may now execute the frozen ANN training policy on the
standard MNIST 60,000-image training split partitioned deterministically into:

```text
55,000 training
 5,000 validation
```

The official 10,000-image test split remains excluded from checkpoint selection
and evaluation during this stage.
