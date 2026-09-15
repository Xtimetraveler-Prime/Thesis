# MNIST Application Milestones

## Purpose

This file tracks the MNIST application rollout separately from the baseline neuromorphic digital-twin platform milestones in the repository root. Application code must consume the validated core rather than silently changing its behavior.

The application carries two FPGA-v1 profiles under the same 4,096-synapse physical ceiling:

- **native-sparse** — original 28x28 MNIST, 784 input axons, at most 4,096 sparse/pruned synapses;
- **cropped-dense** — exact 20x20 center crop, 400 input axons, at most 4,000 dense synapses.

Both use the same deterministic 16-tick rate encoder, ten LIF output neurons, and highest-spike-count decoding with lowest neuron ID as the deterministic tie-break.

---

## MNIST-01 — Capacity Audit and Dual-Profile Architecture

**Status:** Complete

The frozen FPGA-v1 application boundary is 256 neurons, 1,024 axons, 4,096 synapses, 4,096 routes, and 4,096 external/recurrent events per tick. A dense 784x10 classifier requires 7,840 synapses and therefore does not fit.

The two accepted profiles are:

```text
native-sparse:  28x28 -> 784 axons -> <=4096 synapses -> 10 outputs
cropped-dense:  20x20 -> 400 axons -> <=4000 synapses -> 10 outputs
```

Both freeze `current_decay=4096`, `voltage_decay=0`, zero reset/bias/refractory, 16 presentation ticks, zero recurrent routes, and spike-count decoding.

See `docs/MNIST_01_CAPACITY_AUDIT.md`.

---

## MNIST-02 — Shared Dataset and Deterministic Spike Encoding

**Status:** Complete

One profile-aware encoder supports both mappings. Native-sparse preserves all 784 pixels and maps them row-major to axons `0..783`; cropped-dense applies `[4:24,4:24]` and maps the 400 retained pixels to axons `0..399`.

The same integer cumulative-rate rule produces deterministic spike schedules for both profiles. Source-level tests and TensorFlow-backed real-MNIST integration tests passed in the user application environment, and full accepted training runs consumed the standard dataset without event-bound or profile failures.

---

## MNIST-03 — Software SNN Training Baselines

**Status:** Complete

Training reuses the valid parts of the user-authored TensorFlow/Keras notebook workflow: standard MNIST loading, Adam, sparse categorical cross-entropy, elapsed-time measurement, `argmax` classification, and incorrect-sample indexing. The ANN forward path is replaced by explicit integrate-and-fire dynamics with a surrogate gradient.

Model selection uses a deterministic stratified 5,000-image validation split from the official 60,000-image training set. The official 10,000-image test split is evaluated only after model selection is frozen.

### MNIST-03A — Cropped-dense

Ten epochs were trained with all 4,000 connections. The validation-selected checkpoint achieved:

```text
best validation accuracy:      89.12%
final official test accuracy:  90.29%
nonzero float weights:          4,000
```

### MNIST-03B — Native-sparse

The full 7,840-weight software network was trained, the best dense checkpoint restored, magnitude-pruned to 4,096 connections, and then fine-tuned under a frozen mask with a reset Adam optimizer. Immediate pruning reduced validation accuracy from 90.28% to 82.50%; masked fine-tuning recovered to 90.92% at fine-tune epoch 2.

```text
selected stage:                masked-finetune epoch 2
final official test accuracy:  91.62%
nonzero float weights:          4,096
```

Native-sparse therefore finishes 1.33 percentage points above cropped-dense while remaining inside essentially the same physical synapse budget.

See `docs/MNIST_03_TRAINING_BASELINES.md`.

---

## MNIST-04 — Hardware-Aware Quantization and Export

**Status:** Complete

Both accepted checkpoints were exported into the existing project-native encoded-weight representation and M08 CSR storage contract. Export validates profile, shape, connection budget, signed mantissa range, threshold/state scale, and conservative SAT24 headroom.

The full 10,000-image matched evaluation produced:

| Profile | Float accuracy | Stored synapses | Quantized/golden accuracy | Delta |
|---|---:|---:|---:|---:|
| cropped-dense | 90.29% | 3,893 | 90.24% | -0.05 pp |
| native-sparse | 91.62% | 4,086 | 91.71% | +0.09 pp |

Some small trained weights quantized exactly to zero, reducing the stored synapse count from 4,000 to 3,893 for cropped-dense and from 4,096 to 4,086 for native-sparse. The resulting accuracy changes are negligible.

See `docs/MNIST_04_05_ACCEPTED_VALIDATION.md`.

---

## MNIST-05 — Python Golden-Model Evaluation

**Status:** Complete

Both accepted exported deployments were executed through the actual validated `NeuromorphicCore` using FPGA-v1 arithmetic; no application-specific neuron simulator was substituted.

On the full official 10,000-image test set:

| Profile | Float accuracy | Golden accuracy | Prediction agreement |
|---|---:|---:|---:|
| cropped-dense | 90.29% | 90.24% | 99.25% |
| native-sparse | 91.62% | 91.71% | 99.30% |

Golden evaluation preserves final accuracy, confusion matrix, predictions, incorrect indices, accuracy after every presentation tick, input events/image, output spikes/image, exact CSR synapse visits/image, no-spike count, and tied-winner count. The full application pytest suite passed before accepted validation.

See `docs/MNIST_04_05_ACCEPTED_VALIDATION.md`.

---

## MNIST-06 — Dual-Profile Deployment Freeze

**Status:** In progress — freeze tooling and corpus policy implemented; materialized accepted package pending

Freeze both accepted deployments rather than selecting one winner.

### Implemented

- `mnist_app/deployment_freeze.py` verifies accepted MNIST-04/05 hashes and copies the exact checkpoints and deployment images out of the ignored build tree.
- `scripts/freeze_deployment.py` generates the versioned `applications/mnist/frozen/mnist-v1/` package.
- A deterministic 30-image common FPGA corpus selects three source images per digit: one both-correct case, one profile-divergent case, and one both-wrong case, with explicit deterministic fallback if a category is absent.
- `mnist_app/frozen_validation.py` and `scripts/validate_frozen_deployment.py` independently re-hash the complete package and verify the 30-case/three-per-digit corpus contract.
- Unit tests cover corpus selection, hash-verified copying, complete-package validation, and tamper detection.

### Completion criteria

- The accepted full-test MNIST-04/05 validation is the freeze source.
- Both accepted checkpoints and both project-native deployment images are hash-verified and copied.
- The common 30-image FPGA-validation corpus is generated.
- The frozen package passes independent validation.
- `applications/mnist/frozen/mnist-v1/` is committed to the repository and becomes the sole MNIST-07 input package.

See `docs/MNIST_06_DEPLOYMENT_FREEZE.md`.

---

## MNIST-07 — Single-Image FPGA Conformance

**Status:** Planned — M12 multi-tick physical-conformance reuse path identified

### MNIST-07A — Cropped-dense

Run one frozen cropped-dense image through the physical FPGA and require exact per-tick agreement with the Python golden trace.

### MNIST-07B — Native-sparse

Repeat for the native-sparse deployment, including irregular and empty CSR rows where present.

The implementation will reuse the existing M12 multi-tick physical-conformance boundary: FPGA-visible artifacts contain static load images and per-tick external-event schedules only; independent golden state/spike/trace data remains host-side. Both profiles must produce exact Python/FPGA state/spike agreement and identical final spike counts/predictions.

---

## MNIST-08 — FPGA Application Corpus

**Status:** Planned

Run the common frozen source-image corpus through both physical deployments. Every accepted case must agree with Python at the required application/trace boundary, and machine-readable physical results must be preserved.

---

## MNIST-09 — Shared Runtime Host Interface

**Status:** Planned

Create one runtime host flow capable of selecting either frozen profile without rebuilding application-specific neuron logic. Transport/debug overhead remains separate from PL architectural execution time.

Target interface concept:

```text
classify_fpga --profile native-sparse --index N
classify_fpga --profile cropped-dense --index N
```

---

## MNIST-10 — Characterization and Loihi Comparison

**Status:** Planned

### MNIST-10A — Internal FPGA profile comparison

Compare native-sparse and cropped-dense on the same FPGA core: accuracy, cycles/image, latency, events/image, synapse visits/image, spikes/image, memory use, and power/energy only when defensibly measurable.

### MNIST-10B — Native-sparse Loihi-facing comparison

Use the full 28x28 native-sparse profile as the primary external comparison because the starting MNIST representation is aligned. Explicitly document remaining differences in topology, encoding, training, precision, scale, timing definitions, and measurement method.

### MNIST-10C — Cropped-dense interpretation

Treat the cropped-dense result primarily as a controlled FPGA-v1 hardware-fit baseline, not as the primary apples-to-apples Loihi comparison.

The thesis must clearly separate directly comparable quantities, quantities requiring normalization/caveats, and qualitative-only comparisons. Shared use of MNIST alone is never presented as proof of identical experimental conditions.
