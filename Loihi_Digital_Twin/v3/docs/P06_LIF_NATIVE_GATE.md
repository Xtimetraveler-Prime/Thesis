# P06 LIF pre-freeze feasibility gate — existing compiler and HLS packer

**Status: NATIVE HOST STRUCTURAL GATE ACCEPTED
BY USER (2026-10-12) after the corrected 31-spike/
310-NEXT-bank-fanin directed routing regression.**
The user reported that both the regression suite
and the actual 32-hidden packed-image and
published-size resource-limit probe commands
passed. No full test log or immutable output
artifact was provided in this thread;
this is recorded as **user-attested native
acceptance**, not independent re-execution
by the assistant. Re-run commands below
remain the standard reproduction protocol.

The two probes use only the accepted v3 Python
compiler/golden and existing P03 packed FPGA
`OneCoreHardwareImage`; **not** trained weights,
not MNIST test data, not a physical KV260
run and not a HLS synthesis result.

The *source* 2023 snnTorch Tutorial 5 is
784→1000→10 with analog static input,
float `snn.Leaky` and 25 steps.
The **one-core test network** is
a project-specific **784→32→10**
event-driven integer LIF alternative,
25 image events + one NEXT-bank drain.
They are **not the same model**.

## Native routing regression correction (user-reported failure)

The initial directed test incorrectly required **32 output
packets** from a synthetic 784-pixel all-255 stimulus
at timestep 0. That assertion confused 32 **configured
potential routes** with 32 **actual hidden-neuron spikes**.

From the unchanged deterministic synthetic weights,
hidden compartment 1 receives
`sum(1 + floor(pixel_index/240)) = 1696`,
which is **below** the existing strict
`voltage > 2048` firing threshold. Hidden
compartments 0 and 2..31 spike; therefore exactly
**31** routed NEXT-bank packets, and on the next
timestep **31 × 10 = 310** downstream synaptic
contributions, are expected.

The corrected regression **passed on the user's native host**,
and checks the **exact identities**
of firing compartments and outgoing packet sources,
their target timestep **1**, delivery equality to
the next timestep's ingress packet set, readout
target bounds, and the 310 actual fan-in
contributions. A separate **zero-event**
negative control proves that an allocated
output-route table does not generate
phantom routed packets.

No network weights, thresholds, HLS RTL,
P05 acceptance artifacts, or golden neuron
equations were changed to manufacture
32 spikes. This is a **TEST ONLY** correction.
Native test and both compiler feasibility
probe modes are **user-confirmed PASS**.
Training, accuracy, complete physical
inference and real board power remain
pending.

## 1. Check out the sandbox branch

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-lif-feasibility
git pull --ff-only origin agent/v3-p06-lif-feasibility

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
```

## 2. Run ALL associated native checks

```bash
set -o pipefail

python -m py_compile \
  scripts/p06_lif_compiler_probe.py \
  scripts/p06_lif_input_probe.py \
  tests/test_p06_lif_compiler_probe.py \
  tests/test_p06_lif_input_probe.py

PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p06_lif_compiler_probe.py \
  tests/test_p06_lif_input_probe.py \
  tests/test_p06_1_lsnn_source_audit.py \
  tests/test_p06_1_lsnn_io_contract.py \
  2>&1 | tee /tmp/v3_p06_lif_native.log
```

The existing Rao native tests remain included
as a regression safety guard, since this
branch descends from the P06.1 audit.

## 3. Construct and inspect the actual packed 32-hidden image

```bash
PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py \
  --mode probe32 \
  --out "/tmp/v3_p06_lif_probe32_$(date -u +%Y%m%dT%H%M%SZ).json" \
  2>&1 | tee /tmp/v3_p06_lif_probe32.log

PYTHONPATH="$PWD/src" python scripts/p06_lif_compiler_probe.py \
  --mode original_tutorial \
  2>&1 | tee /tmp/v3_p06_lif_original_limit.log

grep -E "PASS|FAIL|P06_LIF_FEASIBILITY" \
  /tmp/v3_p06_lif_probe32.log \
  /tmp/v3_p06_lif_original_limit.log
```

Expected **structural** result:

```text
PASS: P06 LIF one-core real compiler+HLS packed image
P06_LIF_FEASIBILITY_EXIT=0
P06_LIF_BENCHMARK_FREEZE=NO_TRAINED_WEIGHTS_NO_ACCURACY_NO_NUMERICAL_PARITY
```

The other mode must explicitly report
the original tutorial's **794,000**
possible dense synapse positions exceed
five existing 32,768-word DDR records.
An output file is only a structured
hardware-image *metadata report*;
it is **not** a bitstream or test-trained
weights. The original accepted P05
bitstream/ELF are not touched.

The 32-hidden probe should report
`image.compartment_count=42`,
`image.synapse_count=25408`,
`image.destination_axon_count=816`,
`image.route_count=32`,
`logical_core_count=1`.
All actual compiler headrooms must
be **positive**, and the routed
hidden packets must enter NEXT-bank
when run through the unchanged
LogicalChip with 784 synthetic events.
No extrapolation to MNIST accuracy,
performance, power or a published
checkpoint is supported.

## 4. Independent acceptance and next experiment

Paste:
- final pytest summary;
- all `P06_LIF_FEASIBILITY` / `PASS` /`FAIL`
  lines for two probe modes, especially
  any real HLS image resource failures.

Once accepted, P06 should tackle the
smallest **behavior-equivalent training
forward** based on the real P03 integer
24-bit arithmetic/reset/delay, using
training examples only, then first-mismatch
trace validation and application-level
A53 image scheduling. Before official MNIST
test evaluation freeze weights/data/readout,
checksum all artifacts and separately
verify software-vs-KV260 image predictions.
Do not use the published snnTorch
1000-unit tutorial's result as this
resized candidate's ground-truth accuracy.

**Submilestone disposition:** P06-A1
(compact structural compiler and routing
gate) **ACCEPTED** based on reported
native PASS. The active next step is
P06-A2 integer-equivalent training-forward/
independent reference, then P06-A3
training and P06-A4 checkpoint freeze.
The scaled P06-B work is postponed
until P07-A/P08-A physically establish
a robust compact baseline; see
[P06 two-track master plan](P06_TWO_TRACK_LIF_PLAN.md).

