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

The current FPGA-v1 capacity is:

```text
neurons:                 256
axons:                  1024
synapses:               4096
weight formats:           16
routes:                  4096
external events/tick:   4096
recurrent events/tick:  4096
```

A dense 784x10 classifier requires 7,840 synapses and does not fit. Two hardware-fit profiles are frozen:

### MNIST-01A — Native-sparse

```text
28x28 native MNIST
784 input axons
10 output neurons
<=4096 stored sparse/pruned synapses
16 presentation ticks
0 recurrent routes
```

This is the stronger Loihi-facing profile because the source MNIST representation is preserved.

### MNIST-01B — Cropped-dense

```text
28x28 native MNIST
center crop [4:24, 4:24]
400 input axons
10 output neurons
<=4000 dense synapses
16 presentation ticks
0 recurrent routes
```

Both profiles use `current_decay=4096`, `voltage_decay=0`, zero reset/bias/refractory, deterministic rate encoding, and highest output-spike count with lowest neuron ID as the tie-break.

See `docs/MNIST_01_CAPACITY_AUDIT.md`.

---

## MNIST-02 — Shared Dataset and Deterministic Spike Encoding

**Status:** Complete

One shared profile-aware encoder is implemented in `mnist_app/encoding.py`.

### MNIST-02A — Native-sparse encoding

- preserves all 28x28 pixels;
- maps row-major pixels directly to axons `0..783`;
- converts uint8 intensity into deterministic spike counts over 16 ticks.

### MNIST-02B — Cropped-dense encoding

- applies the exact center crop `[4:24, 4:24]`;
- maps row-major cropped pixels to axons `0..399`;
- uses the identical deterministic intensity-to-spike rule.

### Completion evidence

Source-level tests cover both profiles: black/white images, exact spike count per pixel, deterministic ordering, uniqueness, profile-specific axon limits, exact crop behavior, preservation of the native image, outer-border behavior, input validation, and equivalence to the notebook-style `pixel / 255.0` normalization concept.

The TensorFlow-backed real-MNIST integration tests and the full application pytest suite were independently run successfully in the user application environment. Full accepted training runs also consumed the standard MNIST dataset through both encoders without profile or event-bound failures.

---

## MNIST-03 — Software SNN Training Baselines

**Status:** Complete

`mnist_app/training.py` repurposes the user-authored notebook workflow where it remains appropriate: TensorFlow/Keras MNIST loading, Adam optimization, sparse categorical cross-entropy, elapsed training time, final test accuracy, `argmax` predictions, and incorrect-sample indexing. The dense ReLU forward path is replaced by explicit integrate-and-fire output dynamics with a surrogate gradient.

The accepted methodology reserves a deterministic stratified 5,000-sample validation set from the official 60,000-sample MNIST training split. Per-epoch checkpoint selection uses validation accuracy only. The official 10,000-image test set is not consulted until the selected model is frozen.

### MNIST-03A — Cropped-dense SNN

The accepted direct `400 -> 10` spiking classifier uses the full 4,000-connection matrix. Ten initial epochs were run; epoch 10 was selected from validation performance.

```text
best validation accuracy:   0.8912
final official test accuracy: 0.9029
nonzero weights:            4000
```

### MNIST-03B — Native-sparse SNN

The accepted native profile was trained and selected as follows:

1. train the full software `784 -> 10` direct SNN;
2. restore the best dense checkpoint using validation accuracy;
3. deterministically magnitude-prune to 4,096 connections;
4. record the immediate post-prune validation result;
5. reset Adam and fine-tune only surviving weights;
6. select between post-prune and fine-tuned candidates using validation accuracy;
7. evaluate the official test set once after final selection.

The best dense checkpoint was initial epoch 8 at 0.9028 validation accuracy. Immediate pruning reduced validation accuracy to 0.8250. Masked fine-tuning recovered to a best validation accuracy of 0.9092 at fine-tune epoch 2.

```text
selected sparse stage:       masked-finetune epoch 2
final official test accuracy: 0.9162
nonzero weights:             4096
```

The native-sparse accepted model therefore outperforms cropped-dense by 1.33 percentage points on the official test set while remaining inside essentially the same physical synapse budget.

See `docs/MNIST_03_TRAINING_BASELINES.md` for the full accepted methodology and results.

---

## MNIST-04 — Hardware-Aware Quantization and Export

**Status:** Implementation complete; accepted-checkpoint validation and matched accuracy-loss measurement pending

`mnist_app/export.py` accepts either profile and maps accepted float checkpoints into the existing Loihi-style encoded weight representation and M08 CSR storage.

### MNIST-04A — Cropped-dense export

- accepts the `400 -> 10` trained matrix;
- supports up to 4,000 stored synapses;
- retains the full 400-row axon table.

### MNIST-04B — Native-sparse export

- requires the float checkpoint to already satisfy the <=4,096 nonzero-connection budget;
- rejects an accidentally unpruned 7,840-connection native matrix;
- retains all 784 axon rows, including valid empty rows;
- exports at most 4,096 stored synapses.

Pure quantization tests cover both profiles, signed mantissa range, state headroom, shape validation, and sparse-budget enforcement.

`mnist_app/comparison.py` and `scripts/compare_float_golden.py` evaluate the float SNN and quantized golden deployment on the exact same official test samples and report accuracy delta, prediction agreement/disagreement, activity metrics, and deployed synapse count.

### Completion criteria

- both accepted trained checkpoints export successfully;
- every parameter is legal under FPGA-v1;
- exact stored synapse counts and quantization errors are recorded;
- floating-SNN versus quantized/golden accuracy loss is measured on one matched corpus.

---

## MNIST-05 — Python Golden-Model Evaluation

**Status:** Implementation complete; accepted trained/exported deployments required

`mnist_app/inference.py` loads either deployment into the actual validated `NeuromorphicCore`; no application-specific neuron simulator is used.

### MNIST-05A — Cropped-dense golden inference

Evaluate the cropped-dense deployment over the frozen test corpus.

### MNIST-05B — Native-sparse golden inference

Evaluate the native-sparse deployment over the same source MNIST indices.

### Implemented metrics

Golden evaluation records:

- final accuracy and confusion matrix;
- notebook-style predictions and incorrect-sample indices;
- accuracy after every presentation tick;
- mean input events/image;
- mean output spikes/image;
- exact CSR synapse visits/image from the deployed row lengths;
- no-spike image count;
- tied-winner image count.

Pure tests verify profile selection, event behavior, synaptic-visit counting, tick-by-tick predictions, and error-index reporting. The real `neuromorphic_twin` integration tests have run successfully in the user application environment for both profiles using development checkpoints.

### Completion criteria

Both accepted trained/exported profiles run end-to-end from MNIST image to golden-model prediction, and their full evaluation artifacts are preserved.

---

## MNIST-06 — Dual-Profile Deployment Freeze

**Status:** Planned

Compare the two accepted software/golden results and freeze both rather than selecting one winner.

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

Both profiles must produce exact Python/FPGA state/spike agreement and identical final spike counts/predictions. The FPGA receives configuration and input events, never expected outputs.

---

## MNIST-08 — FPGA Application Corpus

**Status:** Planned

### MNIST-08A — Cropped-dense corpus

Run the frozen physical corpus through the cropped-dense deployment.

### MNIST-08B — Native-sparse corpus

Run the same source MNIST indices through the native-sparse deployment.

Every accepted case must agree with Python at the required application/trace boundary, and machine-readable physical results must be preserved.

---

## MNIST-09 — Shared Runtime Host Interface

**Status:** Planned

Create one runtime host flow capable of selecting either profile without rebuilding application-specific neuron logic.

Target interface concept:

```text
classify_fpga --profile native-sparse --index N
classify_fpga --profile cropped-dense --index N
```

Transport/debug overhead remains separate from PL architectural execution time.

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
