# P06-A2.5 — Integer-equivalent differentiable forward / native gate

**Status:** USER-ACCEPTED (2026-10-13), based on user's explicit confirmation that P06-A2 tests were verified and authorization to close P06-A2.
**Branch:** `agent/v3-p06-lif-feasibility`.
**Scope:** Synthetic test inputs and weight fixtures only; no actual MNIST
training, official test labels, FPGA execution, accuracy or energy data.

## Implemented

- `src/loihi_twin_v2/p06_train_forward.py`:
  `IntegerForwardSNN(nn.Module)` runs **25 deterministic event-input ticks +
  1 drain tick** on a 784→32→10 network. It preserves NEXT-tick hidden→output
  propagation, exact P03 signed-24 saturation, signed fixed-point
  round-away-from-zero decay, strict `voltage > threshold`, reset,
  refractory, and per-frame clear.
- Trainable tensors are float32 **only as optimization parameters**. Before
  inference, they are rounded half-away-from-zero and saturated to signed
  24-bit weights using straight-through estimators (STE). Actual forward
  sums and state updates use float64 so all legal integer products/sums in
  this compact graph are exactly representable (no implicit float32
  accumulation or AMP). The output is a **[batch, 10] integer-valued
  float64 spike-count tensor**, not logits.
- `_StrictSpike` performs the hardware's exact strict comparison during
  forward propagation and uses a fast-sigmoid surrogate derivative in
  backward propagation. STE gradients through rounding/saturation and the
  hard spike reset are deliberately approximate. **Training gradients are
  NOT hardware-exact and are not validated as a learning-performance
  guarantee.**
- `to_integer_network()` rejects nonfinite and out-of-signed24-range
  parameters rather than silently accepting a lossy checkpoint; exports
  the independently defined `CompactNetwork`.
- `src/loihi_twin_v2/p06_train_export.py` converts that integer network
  into the **existing, unchanged** `NetworkSpec` compiler boundary. Every
  logical edge (including zero weights) is explicitly retained for parity.
  Any per-neuron parameter variation is **rejected**, because current
  `PopulationSpec` accepts one `CompartmentConfig` per layer.
  Thus this initial training profile has *fixed and uniform within-layer*
  LIF parameters (which may include fixed layer-level biases) and trains
  **synaptic weights only**. No compiler or accepted P05/HLS modification.

## Differential regressions

`tests/test_p06_a2_train_forward.py` (7 tests): independent integer oracle
agreement on silence, maximal input, signed and negative half-integer
weights, 24-bit extremes, mixed deterministic random weights/pixels,
refractory/decay boundaries, fresh-frame reset, strictly integral spike
counts, gradients flowing through **both** quantized layers, a one-step
optimizer smoke, and invalid input/nonfinite/range rejection.

`tests/test_p06_a2_train_export.py` (2 **native-only** tests):
export actual nonuniform-by-weight 784→32→10 graph through the existing
compiler, build the existing P03 packed one-core image, and compare
26-tick model / independently decoded packed-image / existing
`LogicalChip` / PyTorch **count, state, accumulation, packet and spike
traces** for synthetic blank, all-bright and heterogeneous frames.
The maximal frame explicitly must produce hidden and output spikes
(avoids a vacuous all-silent pass). A separate negative gate rejects
nonuniform per-neuron parameter configurations.

A local **partial** checkout with Python 3.13 and PyTorch 2.10.0+cpu
ran **56 tests passing, 1 native-compiler test deselected** across the
earlier A2.1–A2.4 mirrored unit corpus and A2.5 forward unit tests. This
did **not** execute the two A2.5 train-export tests against the real
repository compiler, nor the user's full regression tree. No test claims
about real FPGA hardware are made here.

## Required native verification on user's PC

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-lif-feasibility
git pull --ff-only origin agent/v3-p06-lif-feasibility

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

# This check MUST succeed. A2.5 cannot be accepted with Torch tests skipped.
python -c 'import torch; print("PyTorch", torch.__version__)'

python -m py_compile \
    src/loihi_twin_v2/p06_train_forward.py \
    src/loihi_twin_v2/p06_train_export.py \
    tests/test_p06_a2_train_forward.py \
    tests/test_p06_a2_train_export.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
    tests/test_p06_a2_integer_oracle.py \
    tests/test_p06_a2_input_contract.py \
    tests/test_p06_a2_compact_inference.py \
    tests/test_p06_a2_packed_replay.py \
    tests/test_p06_a2_native_contract.py \
    tests/test_p06_a2_train_forward.py \
    tests/test_p06_a2_train_export.py \
    tests/test_compartment_compatibility.py \
    tests/test_p03_hardware_image.py \
    tests/test_p06_compiler.py \
    tests/test_p06_lif_compiler_probe.py \
    tests/test_p06_lif_input_probe.py \
    2>&1 | tee /tmp/v3_p06_a2_5_native.log

PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py --mode probe32
PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py --mode original_tutorial
```

**Acceptance condition:** all indicated regressions pass, **no A2.5 Torch
skip**, packed/export parity of the signed/synthetic dense model passes,
and both old feasibility modes preserve the accepted PASS. Send back the
pytest summary, any first divergent assertion, and the two probe exits.

## User acceptance (2026-10-13)

The user explicitly stated, "I verified the tests. we can close p06-A2."
This is the native verification acceptance for A2.5. The full pytest
summary/count and two new compiler integration transcripts were not
included in this specific message, so their exact statistics are not
independently attested by the assistant. No physical board/FPGA test is
inferred. **P06-A2 is now formally closed** at the native software
numerical/training-forward contract level; all physical MNIST gates remain.

## Next research stage (P06-A3 after independent acceptance)

Select and hash a legitimate MNIST **train/validation** split (never use
official test labels for hyperparameter selection). Choose training seeds,
optimizer, batch shape, surrogate width, initial nonzero weights, loss,
learning-rate policy and predeclared validation-only GO/NO-GO floor.
Record training environment and device. The current zero-valued model
constructor is an untrained blank state; it is **not** an appropriate
unexamined random initialization for full training.

The learned weight tensors, fixed LIF configs, event encoder version,
readout protocol and full 26-tick execution must all be persisted with
the checkpoint. `nn.Module.state_dict()` **alone does NOT serialize**
the `hidden_config`, `output_config` or `surrogate_width` Python
attributes. A3/A4 require a versioned manifest with these fields and
content hashes. The official 10,000-image test remains sealed until A4.
