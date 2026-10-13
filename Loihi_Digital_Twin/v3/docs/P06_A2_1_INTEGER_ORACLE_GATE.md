# P06-A2.1 — Independent integer LIF scalar reference (native verification gate)

**Status: IMPLEMENTED / COMMITTED — USER NATIVE ACCEPTANCE PENDING.**

Branch: `agent/v3-p06-lif-feasibility`. This is the first, deliberately
limited submilestone of P06-A2. It does **not** close P06-A2.

## Scope

`src/loihi_twin_v2/p06_integer_oracle.py` implements P03's *accepted*
scalar numerical contract without calling or importing
`arithmetic.py`, `compartment.py`, or any existing Loihi runtime:

- legal signed 24-bit current, voltage, threshold, bias, reset values and
  signed-24 saturation on wide intermediates;
- decay on a 4096 fixed-point denominator, rounding signed quotients
  **away from zero**, with current addition/saturation **before** decay;
- pre-decay working current contributing to the voltage update;
- saturating voltage update **before strict `>` threshold** evaluation;
- hard voltage reset, explicit 16-bit refractory state, suppressed spikes
  during refractory ticks but continued current integration;
- signed 24-bit weight inputs expanded into a signed 64-bit accumulator
  with explicit `ap_int<64>` wrap arithmetic (unreachable under the legal
  maximum 4096 input events x 32768 synapses x signed-24 weights).

The independent types are `LIFParameters`, `LIFState`, and `LIFStep`.
`lif_step` returns the next neural state, spike flag, working current,
and pre-threshold voltage when applicable.

The *test adapter*, not the oracle implementation, invokes the accepted
`step_compartment` and P03 binary pack/unpack functions. No accepted
P05 golden or HLS source was altered.

## Evidence and failure conditions

`tests/test_p06_a2_integer_oracle.py` includes:

1. Hand-calculated threshold-equality/crossing, positive and negative
   rounding, negative synaptic contribution, positive/negative saturation,
   current-decay update order, and a multi-tick refractory sequence.
2. Signed-64 accumulator wrapping and strict input validation (rejecting
   impossible state, decay, bias, weight, refractory or accumulator values).
3. Directed differential vectors versus accepted `step_compartment`.
4. 1000 seeded boundary-biased independent-vs-existing neural steps.
5. P03 packed configuration/state round-trip and differential-step checks.

A single disagreement is a failure. Do not weaken tests or alter the
accepted Python/HLS arithmetic to force agreement.

### Native reproduction

Run from a clean working tree if possible:

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
  src/loihi_twin_v2/p06_integer_oracle.py \
  tests/test_p06_a2_integer_oracle.py

PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p06_a2_integer_oracle.py \
  tests/test_compartment_compatibility.py \
  tests/test_p03_hardware_image.py \
  tests/test_p06_lif_compiler_probe.py \
  tests/test_p06_lif_input_probe.py \
  2>&1 | tee /tmp/v3_p06_a2_1_native.log

PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py --mode probe32
PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py --mode original_tutorial
```

**Acceptance rule:** report the final pytest summary and both feasibility
probe PASS/fail lines. Only user confirmation of the real native repo run
can close P06-A2.1.

## Evidence classification

Author-side check: 19 pytest cases passed using a *local mirror of the
retrieved scalar Python and P03 packing functions*, not a live checkout of
the entire current repository. The author-side check is useful for basic
test sanity but is **not** independently reproduced native-repository
verification, actual Vitis HLS cosimulation, or physical KV260 evidence.
The user's native suite above is the required acceptance gate.

## Deferred to P06-A2.2+

Deterministic pixel encoding, axon expansion, NEXT-bank packet scheduling,
per-image state/event reset, output readout, complete network differential
traces and training-forward parity have **not** been added by A2.1.

No MNIST training or official test-set evaluation has occurred.
