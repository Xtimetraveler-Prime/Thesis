# P06 LIF pre-freeze feasibility gate — existing compiler and HLS packer

**Status: HOST NATIVE VERIFICATION PENDING.**
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
