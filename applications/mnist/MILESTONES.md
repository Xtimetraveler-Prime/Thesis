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

**Status:** Planned

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

### Completion criteria

- A documented, resource-compatible network architecture is selected.
- Input encoding, presentation length, and output decoding are fixed for the
  first baseline experiment.
- Any required platform change is identified explicitly rather than hidden in
  application code.

---

## MNIST-02 — Deterministic MNIST Spike Encoder

**Status:** Planned

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

### Completion criteria

- The same image always produces the same event schedule.
- Encoded schedules can be passed directly to `NeuromorphicCore.step()` without
  application-specific changes to the core.
- Encoder tests pass for empty, sparse, dense, and representative MNIST images.

---

## MNIST-03 — Software SNN Training Baseline

**Status:** Planned

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

### Completion criteria

- Training is reproducible from source-controlled scripts and configuration.
- A baseline test-set accuracy is recorded.
- The trained topology matches the architecture frozen in MNIST-01.

---

## MNIST-04 — Hardware-Aware Quantization and Export

**Status:** Planned

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

### Completion criteria

- The exported network can be instantiated by the existing Python golden model.
- Every exported parameter is legal under the current platform specification.
- Quantization effects on test accuracy are measured and documented.

---

## MNIST-05 — Python Golden-Model MNIST Inference

**Status:** Planned

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
