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

**Status:** Complete

The accepted full-test MNIST-04/05 artifacts have been materialized into the source-controlled `applications/mnist/frozen/mnist-v1/` package and independently validated.

The freeze contains:

- both accepted floating-point checkpoints;
- both exact project-native deployment images and M08 weight-memory files;
- SHA-256 hashes for checkpoints, deployments, accepted-validation evidence, and the common corpus;
- the frozen 16-tick application contract;
- the accepted full-test software/golden summaries; and
- one deterministic 30-image common FPGA-validation corpus.

The corpus contains exactly three samples for every digit `0..9`: one both-correct case, one profile-divergent case, and one both-wrong case. The accepted materialized corpus required no fallbacks. The same original MNIST test indices are used for both profiles.

`validate_frozen_deployment.py` passed in the user application environment before the package was committed. The committed `mnist-v1` directory is now the sole accepted input package for MNIST-07 and later physical experiments; any changed hash requires a new freeze version rather than a silent replacement.

See `docs/MNIST_06_DEPLOYMENT_FREEZE.md`.

---

## MNIST-07 — Single-Image FPGA Conformance

**Status:** Complete

MNIST-07 used the first frozen both-correct corpus image as a shared source anchor for both profiles. In `mnist-v1` this is official MNIST test index 3, true label 0. Both profiles were presented for 16 ticks from zero initial state using their frozen deployment images.

### MNIST-07A — Cropped-dense

The physical K26 completed all 16 committed ticks with exact agreement against the independent Python golden trace and zero architectural mismatches.

### MNIST-07B — Native-sparse

The physical K26 repeated the same 16-tick test using the frozen 784-axon / 4,086-synapse sparse deployment, including its irregular CSR rows, again with zero architectural mismatches.

The accepted run reused the existing M12.3 multi-tick capture shell and JTAG/VIO transport. FPGA-visible artifacts contained static configuration/weight/row images and per-tick external events only; independent golden state, signed-64 synaptic accumulators, spike flags, spike counts, and predictions stayed host-side.

Both physical final spike-count vectors and decoded predictions matched the corresponding Python golden results. This closes the application-level physical conformance gate for both deployment profiles.

See `docs/MNIST_07_SINGLE_IMAGE_CONFORMANCE.md`.

---

## MNIST-08 — FPGA Application Corpus

**Status:** Complete

The complete frozen 30-image source corpus was executed through both accepted physical deployment profiles:

```text
30 frozen source images x 2 profiles = 60 physical cases
60 cases x 16 ticks = 960 committed physical ticks
```

The accepted K26 run completed all 60 captures, and the independent host-side differential validator reported:

```text
MNIST-08 suite: passed=True cases=60 ticks=960 mismatches=0
profile=cropped-dense cases=30 passed=30 mismatches=0
profile=native-sparse cases=30 passed=30 mismatches=0
reason=both-correct cases=20 passed=20 mismatches=0
reason=profile-divergent cases=20 passed=20 mismatches=0
reason=both-wrong cases=20 passed=20 mismatches=0
```

Every physical tick matched the corresponding Python `NeuromorphicCore` golden trace at the accepted application/core boundary, including ordered external events, signed-64 synaptic accumulators, state-before/state-after words, spike flags, fault status, final spike counts, and decoded predictions.

Scaling from MNIST-07 exposed two validation-harness issues that were corrected without changing the architectural core. First, a single packed external-event variable exceeded Vivado's 1,000,000-bit synthesis limit; the event image was changed to two profile-banked packed ROMs with a generation-time size guard. Second, the first completed 60-case capture exposed a CLI summary-key mismatch after validation had already succeeded and written the reports; regression coverage now enforces that reporting contract. Neither issue altered neuron, synapse, arithmetic, event-order, or classification semantics.

The 30-image corpus remains a deliberately selected conformance set rather than an unbiased accuracy sample.

See `docs/MNIST_08_FPGA_APPLICATION_CORPUS.md`.

---

## MNIST-09 — Shared Runtime Host Interface

**Status:** Physical validation complete; final application pytest after the last host-side synchronization patch pending before merge

One reusable Vivado 2025.2 K26 bitstream contains both frozen `mnist-v1` deployment images while arbitrary image schedules are encoded on the host and streamed at runtime. The implementation preserves the existing M12.3 VIO shape: `capture_start` selects the frozen profile, trace space `7` appends runtime axon IDs, `capture_step` executes a buffered tick, and normal trace spaces retain their validated post-commit read semantics. The architectural core RTL and HLS neuron IP are unchanged.

The accepted physical runtime exercise used the same generated bitstream artifacts for four classifications:

```text
cropped-dense, index 3, label 0, golden prediction 0
native-sparse,  index 3, label 0, golden prediction 0
cropped-dense, index 1, label 2, golden prediction 2
native-sparse,  index 1, label 2, golden prediction 2
```

All four physical runs passed exact comparison of final output spike-count vectors and decoded predictions against the frozen Python golden result. Thus the runtime has demonstrated both profile switching and image switching without rebuilding application-specific neuron logic or regenerating the bitstream.

Two host/runtime bring-up issues were corrected without changing the core: an over-broad static-image safety grep that mistook the allowed `M12_3_MAX_EXTERNAL_EVENTS` capacity constant for compiled event data, and a trace-read synchronization ordering bug after runtime space-7 event injection. Both now have regression coverage.

JTAG/VIO transaction time remains explicitly separate from architectural FPGA execution time.

See `docs/MNIST_09_SHARED_RUNTIME.md`.

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
