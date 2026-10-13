# P06-A2.2–A2.4 — Native acceptance gate (not yet user-accepted)

**Branch:** `agent/v3-p06-lif-feasibility`

**Status:** IMPLEMENTED / COMMITTED; independent native verification **PENDING**.
P06-A2.1 scalar reference was user-accepted on 2026-10-13 after native
pytest PASS and both compiler-probe PASS results. P06-A2 overall is NOT
complete; P06-A2.5 differentiable training-forward compatibility remains next.

## Implementation scope

### A2.2 — Explicit event and readout contract

`src/loihi_twin_v2/p06_input_contract.py` fixes the candidate protocol:

- 28x28 MNIST uint8 row-major pixel indexing 0..783; no normalization,
  dataset labels, stochastic samples, or floating analog input.
- For pixel `p`, 25 input steps, each with phase
  `(t+17*pixel_index)%25`; an input spike is emitted when
  `floor((phase+1)*p/255)>floor(phase*p/255)`.
- Exactly `floor(25*p/255)` spikes per pixel over steps 0..24;
  step 25 is empty external input, reserved for NEXT-bank drain.
- Ascending unique pixel IDs; one event per active input axon per step.
- Versioned `p06-uint8-quota-phase17-v1` input and
  `p06-26tick-count-argmax-first-v1` output protocols.
- SHA-256 of canonical *test fingerprint* serialization: for each
  of 26 ticks, little-endian uint16 count then little-endian uint16
  pixel indices. This is NOT the A53/P03 event descriptor ABI.
- Exactly 10 output spike counts, maximum wins, smallest index wins ties,
  including all-silent -> digit/class 0.

This re-expresses but does not modify accepted P06-A1
`scripts/p06_lif_input_probe.py`. A new native regression must confirm
both encoder and readout implementations agree.

### A2.3 — Independent complete-image inference

`src/loihi_twin_v2/p06_compact_inference.py` holds a **separate,
uncompiled 784x32 and 32x10 signed-24 weight matrix**, with per-neuron
integer LIF configuration. It calls only the independent A2.1 scalar
oracle and the new input protocol; it never imports LogicalChip,
compiler, P03 image packer, or accepted neuron implementation.

It returns explicit 26-step first-mismatch-ready traces of external
events, previous-tick received hidden spikes, per-neuron signed
synaptic sums, before/after states, firing neuron IDs, output spike
counts, classification, and intentionally discarded t=25 hidden routes.

Every call constructs fresh state and event banks, preventing cross-image
contamination. Tick t hidden spikes affect output only at tick t+1
(including same-core self-routing), never retroactively at tick t.

### A2.4 — Independent P03 packed-image replay/differential

`src/loihi_twin_v2/p06_packed_replay.py` decodes existing packed 128-bit
configuration, 64-bit state/axon/synapse words, route descriptors and
32-bit route words **without** using `hardware_p03` unpackers or
`LogicalChip`. It independently expands axon rows, accumulates signed
64-bit contributions, uses A2.1 scalar arithmetic, emits following-step
self-route packets, and counts output spikes.

`tests/test_p06_a2_packed_replay.py` has hand-built word fixtures and
a *native-only integration test* that constructs the REAL synthetic
784->32->10 network through existing `compile_network` and
`export_one_core_image`, and compares full-frame traces for silent,
fully active, and heterogeneous uint8 frames against BOTH the separate
dense oracle and `LogicalChip`. These use synthetic weights, not
MNIST images or an accepted trained checkpoint. Logical and physical
packet order are compared as normalized multisets where appropriate;
no P05 routing goldens are rewritten.

## Preliminary author-side verification boundary

A local harness mirrored the accepted P06-A2.1 scalar module but did
not contain the entire v3 checkout. The following results were observed:

- 14 A2.2 unit tests PASSED;
- 13 A2.3 unit tests PASSED;
- 3 self-contained A2.4 unit tests PASSED (including negative packed synapses and frame-reset);
- 19 prior A2.1 unit tests PASSED.

**49 tests PASSED, 1 native-repository integration test DESELECTED.**
The extra two native A2 encoder-vs-A1 contract tests were also not run
in this mirror. These are NOT proof that the complete native repository
suite, real compiled image, Vitis HLS, or actual KV260 works.

## Required independent native verification

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-lif-feasibility
git pull --ff-only origin agent/v3-p06-lif-feasibility
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

python -m py_compile \
  src/loihi_twin_v2/p06_input_contract.py \
  src/loihi_twin_v2/p06_compact_inference.py \
  src/loihi_twin_v2/p06_packed_replay.py \
  tests/test_p06_a2_input_contract.py \
  tests/test_p06_a2_compact_inference.py \
  tests/test_p06_a2_packed_replay.py \
  tests/test_p06_a2_native_contract.py

PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p06_a2_integer_oracle.py \
  tests/test_p06_a2_input_contract.py \
  tests/test_p06_a2_compact_inference.py \
  tests/test_p06_a2_packed_replay.py \
  tests/test_p06_a2_native_contract.py \
  tests/test_compartment_compatibility.py \
  tests/test_p03_hardware_image.py \
  tests/test_p06_compiler.py \
  tests/test_p06_lif_compiler_probe.py \
  tests/test_p06_lif_input_probe.py \
  2>&1 | tee /tmp/v3_p06_a2_2_to_4_native.log

PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py --mode probe32
PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py --mode original_tutorial
```

**Acceptance:** every invoked test passes, both structural probes retain
their PASS exits and headroom, and actual integration identifies no
first-mismatch in spikes, signed synaptic sums, neuron states, packet
destinations, or ten-class counts for the three synthetic input frames.
If any fail, preserve the first failing trace and investigate before
altering any golden or accepting A2.2–A2.4.

## Remaining next step

P06-A2.5 must establish *differentiable* train-time forward semantics,
independent integer inference parity and an agreed treatment of
per-neuron learned biases and quantized weight export. The existing
high-level compiler's population-level shared `CompartmentConfig`
still lacks per-neuron parameter support. Do not train on or inspect
official MNIST test labels or claim physical MNIST accuracy here.
