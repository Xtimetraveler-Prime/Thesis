# MNIST Application Milestones

## Purpose

This file tracks the MNIST application rollout separately from the baseline neuromorphic digital-twin platform milestones in the repository root.

The application goal is to demonstrate that trained spiking classifiers can be mapped onto the validated Python/FPGA platform without silently changing its frozen behavioral contract. Application code belongs under `applications/mnist/`; genuinely reusable platform changes must be evaluated separately in the main development track.

The rollout intentionally keeps two FPGA-v1 application profiles alive under the same 4,096-synapse limit:

- **native-sparse** — preserve the original 28x28 / 784-pixel MNIST representation and constrain connectivity to at most 4,096 nonzero synapses;
- **cropped-dense** — center-crop to 20x20 / 400 pixels and retain full 400x10 dense connectivity for exactly 4,000 possible synapses.

Both profiles use the same dataset source, deterministic rate encoder, 16 presentation ticks, ten LIF output neurons, and highest-spike-count decoder. The two profiles therefore isolate a useful hardware-constrained tradeoff: preserve sensory resolution with sparse connectivity versus preserve dense connectivity with reduced input resolution.

---

## MNIST-01 — Capacity Audit and Dual-Profile Architecture

**Status:** Complete

Audit the current FPGA-v1 capacities and freeze both application profiles before training.

### Frozen capacity boundary

```text
neurons:                 256
axons:                  1024
synapses:               4096
weight formats:           16
routes:                  4096
external events/tick:   4096
recurrent events/tick:  4096
```

A dense 784x10 network requires 7,840 synapses and does not fit. Two hardware-fit profiles are therefore frozen:

### MNIST-01A — Native-sparse profile

```text
source image:           28x28 native MNIST
input axons:            784
output neurons:         10
stored synapses:        <=4096
connectivity:           sparse/pruned
presentation ticks:     16
routes:                 0
```

This profile is the stronger Loihi-facing reference because it preserves the original MNIST pixel representation.

### MNIST-01B — Cropped-dense profile

```text
source image:           28x28 native MNIST
preprocessing:          center crop [4:24, 4:24]
input axons:            400
output neurons:         10
stored synapses:        <=4000
connectivity:           dense
presentation ticks:     16
routes:                 0
```

This profile is the simplest near-capacity dense FPGA-v1 classifier.

Both profiles freeze the same neuron/application semantics: `current_decay=4096`, `voltage_decay=0`, zero reset/bias/refractory, deterministic rate encoding, and highest output-spike count with lowest neuron ID as the tie-break.

See `docs/MNIST_01_CAPACITY_AUDIT.md`.

---

## MNIST-02 — Shared Dataset and Deterministic Spike Encoding

**Status:** In progress

Build one dataset/encoder layer that supports both frozen profiles without changing core semantics.

### MNIST-02A — Native-sparse encoding

- Load standard MNIST using the same TensorFlow/Keras dataset path used in the user-authored class notebooks.
- Preserve all 28x28 pixels.
- Map row-major pixel IDs directly to axons `0..783`.
- Convert raw uint8 intensities to deterministic spike counts over 16 ticks.

### MNIST-02B — Cropped-dense encoding

- Apply the frozen exact 20x20 center crop.
- Map row-major cropped pixels to axons `0..399`.
- Use the same deterministic intensity-to-spike rule and tick schedule as the native profile.

### Completion criteria

- Identical input always produces an identical schedule.
- Both schedules can be consumed directly by `NeuromorphicCore.step()`.
- Tests cover black, white, sparse, dense, real MNIST, ordering, exact spike counts, and profile-specific axon bounds.

---

## MNIST-03 — Software SNN Training Baselines

**Status:** Planned

Reuse the TensorFlow/Keras loading, optimization, evaluation, timing, `argmax`, and error-analysis workflow from the user-authored notebooks while replacing the ANN forward path with the frozen spiking model.

### MNIST-03A — Cropped-dense SNN

Train a `400 -> 10` direct spiking classifier with all 4,000 connections trainable. This is the simpler training/debug baseline and should be accepted before the sparse profile.

### MNIST-03B — Native-sparse SNN

Train a native `784 -> 10` classifier, then constrain it to at most 4,096 stored nonzero synapses. Initial strategy:

1. train the full 7,840-weight direct SNN;
2. magnitude-prune the weakest weights to the 4,096-synapse budget;
3. freeze the pruning mask;
4. fine-tune only surviving weights;
5. verify the final nonzero count does not exceed the physical limit.

### Completion criteria

For each profile, preserve a reproducible checkpoint, random seed, training configuration, training time, per-epoch metrics, test accuracy, mean output spikes/image, predictions, and incorrect-sample indices. Raw class scores/spike counts must not be mislabeled as probabilities.

---

## MNIST-04 — Hardware-Aware Quantization and Export

**Status:** Planned

Translate both trained profiles into parameters exactly legal under the existing integer core and M08 storage contract.

### MNIST-04A — Cropped-dense export

Quantize/export the `400 -> 10` trained network and measure floating-SNN to quantized-SNN accuracy loss.

### MNIST-04B — Native-sparse export

Export only surviving sparse connections, retaining exactly 784 axon rows and at most 4,096 synapse records. Empty axon rows are valid and must remain addressable.

### Completion criteria

- Both deployments instantiate the existing `NeuromorphicCore` without application-specific core changes.
- Every neuron/weight parameter is legal under FPGA-v1.
- Each deployment records exact synapse count, quantization error, checksum/version, and accuracy delta.

---

## MNIST-05 — Python Golden-Model Evaluation

**Status:** Planned

Run both exported networks through the actual validated `NeuromorphicCore` and make that path the application inference authority.

### MNIST-05A — Cropped-dense golden inference

Evaluate the cropped-dense deployment over the frozen test corpus.

### MNIST-05B — Native-sparse golden inference

Evaluate the native-sparse deployment over the same source MNIST indices.

### Completion criteria

Record for both profiles: accuracy, confusion matrix, predictions, incorrect-sample indices, input events/image, output spikes/image, synaptic visits/activity, tie/no-spike frequency, and accuracy versus presentation tick. Preserve representative full tick traces.

---

## MNIST-06 — Dual-Profile Deployment Freeze

**Status:** Planned

Compare the two accepted software/golden results and freeze both rather than selecting one winner.

### Completion criteria

For both profiles preserve:

- trained/quantized network checksum;
- exact encoder profile and presentation length;
- weight-storage image;
- neuron configuration;
- known golden-model accuracy;
- common FPGA-validation corpus using the same original MNIST sample indices.

Any discovered need to alter baseline core semantics must be proposed outside the application track.

---

## MNIST-07 — Single-Image FPGA Conformance

**Status:** Planned

### MNIST-07A — Cropped-dense conformance

Run one frozen cropped-dense image through the physical FPGA and require exact per-tick agreement with the Python golden trace.

### MNIST-07B — Native-sparse conformance

Repeat for the native-sparse deployment, including irregular and empty CSR rows where present.

### Completion criteria

Both profiles must produce exact Python/FPGA state/spike agreement and identical final spike counts/predictions. The FPGA receives configuration and input events, never expected outputs.

---

## MNIST-08 — FPGA Application Corpus

**Status:** Planned

### MNIST-08A — Cropped-dense corpus

Run the frozen physical corpus through the cropped-dense deployment.

### MNIST-08B — Native-sparse corpus

Run the same source MNIST indices through the native-sparse deployment.

### Completion criteria

Every accepted case agrees with Python at the required application/trace boundary, and machine-readable physical results are preserved for later analysis.

---

## MNIST-09 — Shared Runtime Host Interface

**Status:** Planned

Create one runtime host flow capable of selecting either profile without rebuilding the core per image.

Target interface concept:

```text
classify_fpga --profile native-sparse --index N
classify_fpga --profile cropped-dense --index N
```

### Completion criteria

Multiple arbitrary test images can be classified with one programmed hardware image or an explicitly documented profile-loading flow; transport/debug overhead remains separated from PL architectural execution time.

---

## MNIST-10 — Characterization and Loihi Comparison

**Status:** Planned

### MNIST-10A — Internal FPGA profile comparison

Compare native-sparse and cropped-dense on the same FPGA core: accuracy, cycles/image, latency, events/image, synapse visits/image, spikes/image, memory use, and power/energy only when defensibly measurable.

### MNIST-10B — Native-sparse Loihi-facing comparison

Use the full 28x28 native-sparse profile as the primary external comparison because the starting MNIST representation is aligned. Explicitly document remaining differences in topology, encoding, training, precision, scale, timing definitions, and measurement method.

### MNIST-10C — Cropped-dense interpretation

Treat the cropped-dense result primarily as a controlled FPGA-v1 hardware-fit baseline, not as the primary apples-to-apples Loihi comparison.

### Completion criteria

The thesis must clearly separate: directly comparable quantities, quantities requiring normalization/caveats, and qualitative-only comparisons. Shared use of MNIST alone is never presented as proof of identical experimental conditions.
