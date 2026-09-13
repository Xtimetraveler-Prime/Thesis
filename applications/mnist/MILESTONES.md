# MNIST Application Milestones

## Purpose

This file tracks the MNIST application rollout separately from the baseline
neuromorphic digital-twin platform milestones in the repository root.

The application goal is to demonstrate that a trained spiking neural network can
be mapped onto the validated Python/FPGA neuromorphic platform without silently
changing its frozen behavioral contract.

Application-specific code belongs under `applications/mnist/`. Changes that are
truly generic platform capabilities should be evaluated separately and, if
accepted, tracked in the main platform development history.

---

## MNIST-01 — Capacity Audit and Application Architecture

**Status:** Complete

Establish the smallest useful MNIST network that fits the current platform and
freeze the application-level interface before training begins.

### Goals

- Audit current limits for physical neurons, axon IDs, synapse storage,
  external events per tick, recurrent events, route storage, and generated FPGA
  memory images.
- Select the first network topology, with `784 input axons -> 10 output neurons`
  as the preferred baseline if existing storage permits it.
- Define a fallback such as downsampled `14 x 14` input if required by current
  storage limits.
- Freeze the number of presentation ticks per image.
- Freeze the initial deterministic spike-encoding method.
- Define the output decoding rule, initially based on output-neuron spike count
  with a deterministic tie-break.

### Completion result

The physical FPGA-v1 profile is `256 neurons / 1024 axons / 4096 synapses /
4096 routes / 4096 events per tick`. A dense `784 -> 10` network would require
7,840 synapses and therefore does not fit. The largest simple square dense input
that fits ten outputs is `20 x 20 = 400` axons, requiring 4,000 synapses.

The first application is frozen as a 20x20 center crop, 400 direct input axons,
10 LIF output neurons, 16 presentation ticks, deterministic rate encoding,
full current decay, persistent membrane voltage, zero reset/refractory/bias,
no recurrent routes, and highest-spike-count decoding with lowest-ID tie-break.

See `docs/MNIST_01_CAPACITY_AUDIT.md` for the full audit.

---

## MNIST-02 — Deterministic MNIST Spike Encoder

**Status:** In progress — implementation complete; local real-MNIST integration validation required

Convert MNIST pixel data into the exact per-tick external axon-event sequences
accepted by the existing neuromorphic core.

### Goals

- Load the standard MNIST train/test datasets.
- Map input pixels deterministically to external axon IDs.
- Convert grayscale intensity into a deterministic spike schedule over the
  frozen presentation window.
- Preserve event multiplicity and ordering according to the core contract.
- Add tests proving repeatability for identical input images.
- Provide small human-readable fixtures showing image, pixel intensity, and
  generated axon events.

### Current progress

`mnist_app/encoding.py` implements exact 20x20 cropping, integer intensity-to-
spike-level quantization, deterministic per-tick distribution, row-major axon
mapping, and direct event schedules for `NeuromorphicCore.step()`.

Source-only tests cover empty/dense inputs, exact per-pixel spike counts,
repeatability, ordering, uniqueness, shape validation, and range validation.
An optional TensorFlow-backed test loads an actual MNIST image and verifies the
same repeatability contract. `scripts/inspect_encoding.py` provides a
human-readable real-image fixture once MNIST is available locally.

### Completion criteria

- The same image always produces the same event schedule.
- Encoded schedules can be passed directly to `NeuromorphicCore.step()` without
  application-specific changes to the core.
- Encoder tests pass for empty, sparse, dense, and representative MNIST images.

---

## MNIST-03 — Software SNN Training Baseline

**Status:** In progress — training implementation complete; first accepted local training run required

Train a small SNN for MNIST using a conventional training framework while
keeping the network architecture compatible with the selected deployment
boundary.

### Goals

- Implement the selected network in a suitable training framework.
- Establish a floating-point or high-precision software baseline before
  project-specific quantization.
- Save trained weights and relevant neuron parameters in a reproducible format.
- Record training configuration, random seeds, dataset split, and baseline test
  accuracy.
- Keep the first network intentionally simple; avoid hidden layers unless the
  direct input-to-output network is demonstrably inadequate.

### Current progress

`mnist_app/training.py` reuses the TensorFlow/Keras MNIST workflow from the
user-authored class notebooks but replaces the ReLU ANN forward path with a
400-to-10 integrate-and-fire SNN. The forward pass uses hard spikes with a
surrogate gradient, the frozen 16-tick encoder, full current decay, persistent
voltage, hard zero reset, and output spike-count logits. The training script
records the fixed seed, hyperparameters, per-epoch accuracy/activity, and a
portable NumPy checkpoint.

A TensorFlow/MNIST run cannot be executed in the current development sandbox,
so baseline SNN accuracy is intentionally not claimed yet.

### Completion criteria

- Training is reproducible from source-controlled scripts and configuration.
- A baseline test-set accuracy is recorded.
- The trained topology matches the architecture frozen in MNIST-01.

---

## MNIST-04 — Hardware-Aware Quantization and Export

**Status:** In progress — implementation complete; trained checkpoint and accuracy-loss measurement required

Translate the trained software network into parameters that are exactly legal
for the project's integer neuromorphic model.

### Goals

- Quantize trained weights into the supported project weight representation.
- Map neuron threshold, decay, reset, bias, and refractory parameters into the
  existing configuration contract.
- Export the network as project-native neuron, synapse, and axon configuration.
- Detect out-of-range or non-representable parameters instead of silently
  clipping them without documentation.
- Measure accuracy loss introduced by quantization.
- If needed, add quantization-aware retraining or fine-tuning while preserving
  the frozen hardware rules.

### Current progress

`mnist_app/export.py` maps float weights to two existing exponent-zero encoded
weight formats (excitatory/inhibitory), scales the threshold into the same
integer state units, constrains scale using both mantissa range and conservative
SAT24 headroom, emits the existing M08 FPGA weight-storage image, and writes a
machine-readable deployment manifest. Pure quantization tests pass locally.
An optional platform integration test exports a synthetic checkpoint and runs
it through the actual project core when `neuromorphic_twin` is installed.

### Completion criteria

- The exported network can be instantiated by the existing Python golden model.
- Every exported parameter is legal under the current platform specification.
- Quantization effects on test accuracy are measured and documented.

---

## MNIST-05 — Python Golden-Model MNIST Inference

**Status:** In progress — inference implementation complete; trained exported network required

Run the exported trained network through the actual project
`NeuromorphicCore`, making the validated golden model the application inference
authority.

### Goals

- Reset the core for each image.
- Present encoded MNIST events over the frozen number of ticks.
- Count output-neuron spikes and produce a predicted digit.
- Evaluate the complete MNIST test set or another explicitly frozen evaluation
  corpus.
- Record accuracy, confusion matrix, spikes per image, input events per image,
  synaptic activity, and prediction behavior versus presentation length.
- Preserve representative full per-tick traces for regression use.

### Current progress

`mnist_app/inference.py` loads the exported M08 storage, reconstructs encoded
synapses, instantiates the real `NeuromorphicCore` with
`FPGA_CORE_ARITHMETIC_V1`, resets between images, feeds the deterministic event
schedule, counts output spikes, and performs deterministic argmax decoding.
`scripts/evaluate_golden.py` evaluates a finite test corpus and records accuracy,
confusion matrix, mean input events, and mean output spikes.

### Completion criteria

- Python inference runs end-to-end from MNIST image to predicted digit.
- Test-set accuracy and application activity metrics are reproducible.
- Results come from the existing project core rather than from the training
  framework's inference implementation.

---

## MNIST-06 — Hardware-Fit Optimization

**Status:** Planned

Resolve any deployment pressure revealed by the exact Python workload while
keeping application and platform responsibilities explicit.

### Goals

- Measure final neuron, axon, synapse, route, and event requirements.
- Reduce storage or activity through retraining, sparsification, input
  downsampling, or parameter adjustment if needed.
- Prefer application-level optimization before changing the frozen core.
- If a genuine reusable platform limitation is reached, document the proposed
  platform enhancement separately before implementing it.
- Freeze one deployment network and evaluation corpus for FPGA validation.

### Completion criteria

- A trained network fits within the selected FPGA configuration limits.
- The deployment network has a frozen checksum/version and known Python
  accuracy.
- No undocumented application-specific modification to core semantics is
  required.

---

## MNIST-07 — Single-Image FPGA Conformance

**Status:** Planned

Deploy one frozen MNIST inference case through the existing physical FPGA
validation path and prove exact agreement with the Python golden model.

### Goals

- Generate the FPGA-visible static network configuration and per-tick external
  event schedule for one representative image.
- Execute the complete presentation window on the physical FPGA.
- Capture architectural state, spikes, and relevant event traces using the
  existing validation infrastructure.
- Compare every committed tick against the independent Python golden trace.
- Verify identical final spike counts and prediction.

### Completion criteria

- One complete MNIST image passes exact Python/FPGA differential comparison.
- The FPGA receives inputs and configuration, not expected outputs.
- The predicted digit and output spike counts match the golden model exactly.

---

## MNIST-08 — FPGA Application Corpus

**Status:** Planned

Extend the single-image proof into a useful physical application corpus.

### Goals

- Select a deterministic corpus containing all ten digit classes and a mix of
  correct and difficult examples.
- Run each image on the physical FPGA using the frozen deployed network.
- Require Python/FPGA equivalence for predictions and application-level spike
  outputs.
- Preserve machine-readable physical results for later analysis.
- Expand the corpus as practical without making slow debug transport part of
  the claimed architectural execution time.

### Completion criteria

- The frozen application corpus executes successfully on hardware.
- Python and FPGA outputs agree for every accepted case.
- Any discrepancy is classified and resolved before characterization proceeds.

---

## MNIST-09 — Runtime Host Interface

**Status:** Planned

Make the FPGA application usable without regenerating or rebuilding a bitstream
for each input image.

### Goals

- Define a runtime path for loading encoded image events into the existing
  hardware design.
- Reuse the current core rather than forking application-specific neuron logic.
- Provide a host command/script that accepts an MNIST image or dataset sample,
  runs inference, and returns output spike counts and the predicted digit.
- Separate host/JTAG/transport overhead from PL architectural execution time.
- Retain a debug mode that can capture detailed traces for conformance work.

### Completion criteria

- Multiple arbitrary test images can be evaluated with one programmed hardware
  image.
- A source-controlled host workflow produces predictions without Vivado project
  regeneration per image.
- Runtime output remains consistent with the Python golden model.

---

## MNIST-10 — Application Characterization and Loihi Comparison

**Status:** Planned

Characterize the completed MNIST workload and compare it with published Loihi
MNIST evidence only where the experimental boundaries are defensibly aligned.

### Goals

- Measure classification accuracy of the frozen deployed network.
- Measure PL cycles and latency per image and per presentation tick.
- Measure spike count, input-event count, synaptic visits/activity, and relevant
  FPGA resource utilization.
- Measure power or energy only if the available procedure supports a defensible
  result.
- Document accuracy-versus-ticks/latency tradeoffs.
- Review published Loihi MNIST experiments and distinguish:
  - directly comparable quantities;
  - quantities requiring normalization or methodological caveats; and
  - quantities that should remain qualitative/non-comparable.
- Avoid presenting shared use of MNIST as an apples-to-apples performance
  comparison when network, training, encoding, hardware scale, or measurement
  definitions differ.

### Completion criteria

- Reproducible application-level accuracy and hardware-characterization
  artifacts are preserved.
- The thesis can state clearly what the FPGA digital twin accomplishes on MNIST.
- Any Loihi comparison is explicitly bounded by the evidence and experimental
  differences.
