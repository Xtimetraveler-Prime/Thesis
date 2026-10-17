# P07-A4.2b/c — Persistent A53 standalone application and KV260 entry gates

**Branch:** `agent/v3-p07-a-784-axon-streaming`. **A4.2a
CLOSED / USER-ACCEPTED 2026-10-17**. A4.2b C11 firmware
and isolated Vitis builder: **IMPLEMENTED / CI NATIVE PASS**,
**USER VITIS/A53 ELF BUILD PENDING**. A4.2c guarded
physical XSDB and independent journal oracle scripts:
**IMPLEMENTED / CI HOST-ONLY PASS, PHYSICAL KV260 NOT RUN**.
**OFFICIAL CANONICAL MNIST TEST REMAINS SEALED.**

## Why there are TWO new gates

A4.2b introduces a distinct `P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1`
standalone A53 ELF. It is NOT the old
`P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX` ELF;
neither are their memory maps interchangeable. The accepted
P03.2c FPD128 bitstream and **all accepted A2/P03 neural
source files** are unchanged. New A53 board code is in
`software/p07/p07_a4_board.c`, and links directly to
accepted `p07_a2_run_frame` and the accepted P03 HLS/adapter.

The new `p07_a4_supervisor.c` enforces this order on
every image **within ONE autonomous A53 launch**:

1. Verify whole `P07A4P01` descriptor, frozen 784-axon
   mapping, every raw image CRC, frozen 512KiB master SHA256
   and PS/FPD128 hardware capability **before dispatch**.
2. For image index 0..N-1, reconstruct byte-exact accepted
   `P07A1IN1` ingress; restore entire frozen P02 core DDR
   and all event-bank/neuron states, then invoke existing
   `p07_a2_run_frame()` for 26 ticks.
3. Pack complete `P07A4R01` 96B physical result with 260
   per-tick output spike bits, ten spike counts, class,
   silence, raw pixel CRC32, NEXT route/drop counts.
   Flush CRC-protected physical record **before** reporting
   `completed=N` in the independently CRC-protected
   256B journal header.
4. On the first image or journal failure, emit a nonterminal
   `0xDEADxxxx` state with immutable original completed
   prefix and first-failure image index, then stop. No
   skip/retry/renumbering or falsely successful completion.
5. Only after all frames pass, write
   `status=0x600D600D` and `completed=N`.
   The selected one image's **full 26×42×256-bit**
   compartment trace is stored at `0x43FF0000`; all
   images retain **26×10 physical output spike flags**,
   route counts and per-image records in 1MiB journal.

**Research observability note:** unlike original A2 batches,
this single launch captures just **one full compartment
trace for the selected image**, NOT 625 full per-image
compartment traces for 10,000 images. The final A4
acceptance protocol must explicitly report this difference.
We must independently approve the whole-dataset oracle
comparison and chosen diagnostic trace policy before
unsealing. Do not retroactively claim hardware full-state
agreement for every image when only output spikes/routes
were physically recorded.

## A4.2b native regression and Vitis build — user gate

From user's VS Code terminal (the last successful P07
branch), first pull and verify the C11 tests:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-a-784-axon-streaming
git pull --ff-only origin agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a4_persistent_board.py \
  tests/test_p07_a4_stream.py \
  tests/test_p07_a4_physical_gate.py \
  tests/test_p07_a2_board_build.py \
  tests/test_p07_a2_runtime.py
```

A4.2b **Vitis-native** cross-build needs the **same accepted
FPD128 XSA** from A2/A3. Set toolchain environment as
previously verified on this machine (`which vitis` and
`which readelf` must succeed). Then:

```bash
export P07_A4_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P07_A4_XSA_SHA256=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
export P07_A4_BUILD_DIR="/tmp/v3_p07_a4_persistent_$(date +%Y%m%dT%H%M%S)"
bash scripts/build_p07_a4.sh

sha256sum "$P07_A4_BUILD_DIR/vitis_workspace/p07_a4_board.elf"
```

Expected native output **not already claimed as achieved**:

```text
P07_A4_A53_VITIS_BUILD_PASS=1
P07_A4_VITIS_NATIVE_GATE_PASS=1
P07_A4_KV260_STATUS=NOT_RUN
```

Shell pins XSA full SHA, refuses overwriting older build,
checks new firmware marker within ELF and LOAD sections
against 0x40000000–0x43FFFFFF reserved DDR, and
retains staged source+ELF fingerprints.

**Do not launch on hardware until the above native gate
passes on the user's Vitis toolchain.** The absence of a
user-built ELF is not a hardware failure.

## A4.2c independent HOST-ONLY admission and hardware entry

New files:
- `vivado/p07_a4_xsdb_prepare.tcl` — JTAG write/readback
  exact master, fixed raw pixels, descriptor, map, 1MiB
  initialized journal and 64KiB zero trace; checks each.
- `vivado/p07_a4_xsdb_run.tcl` — one A53 ELF
  download/launch and status poll at journal header
  offset 16; read 1MiB journal + 64KiB selected trace.
- `scripts/run_p07_a4_physical.sh` — immutable
  guarded one-run wrapper checking accepted XSA/bitstream/
  routed metric, all staged A53 source headers, DDR SHA
  and candidate input scope. Refuses physical execution
  unless user explicitly confirms reserved DDR overwrite.
- `scripts/p07_a4_2_verify.py` — independent frozen
  P03 packed replay checks every image's **26×10
  output spike bits**, readout, routing/drain counters,
  encoder event count; all **26×42 selected-image
  compartment words**, including before/current/after,
  spike/reserved bits; fresh canonical TRAIN-only
  image/source-index/label provenance (validation only).

For a FIRST physical experiment **after** the native
A4.2b acceptance and complete A4.2c host preflight:

```bash
# Reuse already independently accepted A4.2a synthetic stage:
export P07_A4_STAGE_DIR="$PWD/artifacts/p07_a4_2a_ramp16_v1"
# Use the same accepted A2/A3 routed P03_DIAG_REPORTS and XSA gate.
export P03_2C_EXPECTED_XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
export P07_A4_RUN_DIR="/tmp/v3_p07_a4_ramp16_$(date +%Y%m%dT%H%M%S)"

# SAFE; no board use:
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir "$P07_A4_STAGE_DIR"
bash -n scripts/run_p07_a4_physical.sh
```

**Only after a fresh board reboot into dedicated JTAG,
Linux NOT co-owning the reserved 0x40000000–0x43FFFFFF,
and a new distinct evidence directory**, the separate
physical shell can be run with:

```bash
export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a4_physical.sh
```

No unattended loop, restart bypass, or host per-image
JTAG dispatch. The physical wrapper runs a **single**
autonomous A53 dataset launch and independently verifies
every frame before printing the real physical acceptance
marker:

```text
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1
P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1
```

**None of these physical markers has yet been observed.**
Preserve the whole evidence directory; reboot KV260
AFTER the run even on error. User must independently
accept ramp16 before the real 128 validation frames,
then independent cold-run repeats and larger-population
reliability tests before concluding A4.2c.

## Stop / scope

- A4.2b C11/native CI pass is **not** Vitis ELF
  or actual KV260 verification.
- A4.2c CI/pass shell syntax is **not** numerical FPGA
  evidence; physical acceptance is still pending.
- No original signed-off P07-A2/A3 experiment evidence is
  modified and no merge to `main` was authorized.
- A4.3 official **TEST unseal** is prohibited until
  A4.2c complete physical acceptance, fixed
  monitoring/trace coverage and explicit user authorization.
