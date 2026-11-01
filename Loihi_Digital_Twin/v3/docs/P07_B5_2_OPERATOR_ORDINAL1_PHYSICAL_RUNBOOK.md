# P07-B.5.2 — exact physical TRAIN validation ordinal-1 runbook

**Prepared 2026-11-01, pending real operator KV260 execution.**
This file contains the *one next* experimental session. Nothing below
means the assistant has accessed the board or that ordinal1 has
passed. The operator's real PC-only B5.1 three TRAIN reference
and re-verification of physical ordinal0 **already passed**.

Experiment: **original frozen TRAIN-derived validation ordinal1**
(original canonical TRAIN index `27347`, not MNIST official TEST).
Same exact **27 logical P02 cores/3 resident slots/1 HLS engine**,
26 ticks, 702 dispatches, 26 barriers, all 1,010 compartments,
original fixed 784→1000→10 trained checkpoint.
Run the accepted original **V3 diagnostic firmware**; do NOT rebuild
or modify it. The original INPUT route and output route table
remain the same; only the frozen original TRAIN frame selected by
`--validation-ordinal 1` changes.

## Safety, one-session ownership, and independent consent

This is a **destructive** dedicated JTAG takeover of Linux/A53 plus
programming of accepted P03 PL and overwriting exact reserved original
27 × 512KiB P02 DDR contexts, binding descriptor, 80KiB/896KiB route
tables, selected full TRAIN frame, 256B mailbox, and
standalone A53 ELF PT_LOAD `[0x00000000,0x00106B00)` (1,075,968B).
The physical boot firmware's low-DDR exclusivity remains
**independently UNPROVEN**; the operator previously explicitly accepted
that risk for the original B4m workflow. This is NOT a proof of
coexistence and do NOT load on a non-disposable Linux/firmware state.

Require the actual user to own the dedicated JTAG hardware session,
reboot/power-cycle before execution, confirm the FPGA/debug cable and
recoverable board boot, and record the **12 explicit approvals** via
the existing fail-closed CLI flags. If any check changes, do not bypass
it. **After any actual JTAG takeover attempt, even on error, REBOOT
KV260; never resume the halted Linux session.** Do not run back-to-back
ordinal1→ordinal2 without a separate physical reboot and verification.

The PC-only `--mode preflight` and B5 `--mode verify` do not contact
the board. A nonzero `execute` process exit must not be converted to
PASS by manually fabricating an evidence JSON.

## Step 1 — update repository and check code (PC ONLY)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
cd Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b5_scaled_validation.py \
  tests/test_p07_b5_raw_trace_reference.py \
  tests/test_p07_b4m_v3_train0_scalar_vs_physical.py \
  tests/test_p07_b4m_diag_v3_physical_run.py
```

## Step 2 — restore exact accepted local file paths (PC ONLY)

```bash
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B4L_BINDINGS="$HOME/Thesis_Evidence/p07_b4l_b3_bindings_20261023T011829Z"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B4I_BUILD_DIR="$HOME/p07_b4i_build_20261022T161058Z"
export P07_B4M_DIAG_V3_BUILD_DIR="$HOME/p07_b4m_diag_v3_build_20261101T034702Z"
export P07_B4M_DIAG_V3_OFFLINE_REPORT="$HOME/Thesis_Evidence/p07_b4m_diag_v3_offline_20261101T034702Z.json"
export P07_B4M_DIAG_V3_ELF="$P07_B4M_DIAG_V3_BUILD_DIR/vitis_workspace/p07_b4m_diag_v3_26tick.elf"
export P07_B5_ORDINAL=1

sha256sum "$P07_B4M_DIAG_V3_ELF" "$P07_B4M_DIAG_V3_ELF".map
test "$(sha256sum "$P07_B4M_DIAG_V3_ELF" | cut -d' ' -f1)" = "66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904"
test "$(sha256sum "$P07_B4M_DIAG_V3_ELF.map" | cut -d' ' -f1)" = "148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede"
```

Note: The actual `.map` is the sibling of the ELF, with
`p07_b4m_diag_v3_26tick.map` suffix. The shell
`"$P07_B4M_DIAG_V3_ELF".map` used above produces
`...26tick.elf.map`, **not** the real accepted map, so
**use the corrected shell snippet below** rather than the exploratory
`sha256sum ... .map` lines above:

```bash
export P07_B4M_DIAG_V3_MAP="${P07_B4M_DIAG_V3_ELF%.elf}.map"
sha256sum "$P07_B4M_DIAG_V3_ELF" "$P07_B4M_DIAG_V3_MAP"
test "$(sha256sum "$P07_B4M_DIAG_V3_ELF" | cut -d' ' -f1)" = "66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904"
test "$(sha256sum "$P07_B4M_DIAG_V3_MAP" | cut -d' ' -f1)" = "148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede"
```

If any hash is wrong/missing, STOP (do not build/replace/reuse the
previous ELF).

## Step 3 — original V3 exact source and selected TRAIN1 PC admission

```bash
PYTHONPATH="$PWD/src" python scripts/p07_b4m_diag_v3_physical_run.py \
  --mode preflight \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --bindings-dir "$P07_B4L_BINDINGS" \
  --routes-dir "$P07_B4M_STAGE" \
  --offline-report "$P07_B4M_DIAG_V3_OFFLINE_REPORT" \
  --reports "$P07_B4L_REPORTS" \
  --b4i-build "$P07_B4I_BUILD_DIR" \
  --diag-build "$P07_B4M_DIAG_V3_BUILD_DIR" \
  --elf "$P07_B4M_DIAG_V3_ELF" \
  --validation-ordinal "$P07_B5_ORDINAL"
```

Require all original model/P02 metadata/ELF/route gates, marker
`P07_B4M_DIAG_V3_READ_ONLY_PREFLIGHT_PASS=1`
and `P07_B4M_KV260_ACCESSED=0`; preflight is **not**
physical acceptance. Do not call `execute` if any host gate fails.

## Step 4 — one separate real physical ordinal1 session (DESTRUCTIVE)

**POWER-CYCLE THE KV260 FIRST.** Verify fresh dedicated XSDB cable
server `tcp:127.0.0.1:3121` (e.g. `ss -ltn | grep ':3121'` on PC).
No live Linux jobs that must survive. Ensure the environment still has
all Step 2 variables. Evidence directory must NOT exist before the run.

```bash
export P07_B5_EVIDENCE="$HOME/Thesis_Evidence/p07_b5_train1_real_$(date -u +%Y%m%dT%H%M%SZ)"
echo "$P07_B5_EVIDENCE"
test ! -e "$P07_B5_EVIDENCE"
set -o pipefail
PYTHONPATH="$PWD/src" python scripts/p07_b4m_diag_v3_physical_run.py \
  --mode execute \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --bindings-dir "$P07_B4L_BINDINGS" \
  --routes-dir "$P07_B4M_STAGE" \
  --offline-report "$P07_B4M_DIAG_V3_OFFLINE_REPORT" \
  --reports "$P07_B4L_REPORTS" \
  --b4i-build "$P07_B4I_BUILD_DIR" \
  --diag-build "$P07_B4M_DIAG_V3_BUILD_DIR" \
  --elf "$P07_B4M_DIAG_V3_ELF" \
  --validation-ordinal "$P07_B5_ORDINAL" \
  --evidence "$P07_B5_EVIDENCE" \
  --dedicated-jtag-owner YES \
  --cpu-takeover-approved YES \
  --ddr-27core-overwrite-approved YES \
  --frozen-binding-overwrite-approved YES \
  --route-train-ddr-overwrite-approved YES \
  --firmware-coexistence-risk-acknowledged YES \
  --pl-program-approved YES \
  --reboot-recovery-approved YES \
  --expanded-low-ddr-1075968-footprint-approved YES \
  --unproven-boot-firmware-exclusivity-risk-accepted YES \
  --mailbox-256b-overwrite-approved YES \
  --a53-26tick-diagnostic-v3-approved YES
```

A successful physical V3 script emits
`P07_B4M_DIAG_V3_STRUCTURAL_RECEIPT_ACCEPTED=1`
and the evidence folder contains `stage.txt`,
`diag_v3_a53_run.log`, `diag_v3_physical_mailbox_256.bin`,
`diag_v3_structural_receipt.json` and actual independently
checked physical readbacks. **This is structural, not numerical
parity yet.**

**HARD-REBOOT KV260 AFTER ANY ACTUAL ATTEMPT**, even on success,
JTAG debugger failure or A53 timeout. Never reconnect to or resume
the halted Linux session. Only then inspect/validate artifacts on PC.

## Step 5 — independently validate actual TRAIN1 physical bytes (PC ONLY)

After reboot, re-run the B5 source scalar checker against the **new**
genuine physical evidence:

```bash
export P07_B5_REPORT="$HOME/Thesis_Evidence/p07_b5_verify_train1_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
  --mode verify \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --routes-dir "$P07_B4M_STAGE" \
  --run "1:$P07_B5_EVIDENCE" \
  --out "$P07_B5_REPORT"
cat "$P07_B5_REPORT"
```

Expected iff authentic original TRAIN1 proof and all scalar metrics
and 26-tick FNV64 match:
`P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1`.
The B5 checker also prints
`P07_B5_FULL_RAW_NEURON_PARITY_VERIFIED=0` and
`P07_B5_PHYSICAL_BOARD_CONTACT=0` intentionally.

If the host verifier fails, preserve the raw 256B mailbox,
structural JSON, `stage.txt`, actual XSDB logs, report and entire
DDR physical readback directory. Report the first mismatch/reason;
do not self-adjust frozen weights, readout votes or FNV to make
the run pass. Do not move to ordinal2 until this real ordinal1
data has been reviewed.

## After independently accepted ordinal1

A **separate fresh board power-cycle** precedes each next
physical attempt. Use `--validation-ordinal 2` with a **NEW**
evidence directory and `--run "2:${P07_B5_EVIDENCE2}"`
for the next image; then a further independent **ordinal0**
reboot repeat in another directory. All four evidence directories
(original accepted ordinal0, ordinal1, ordinal2, repeat ordinal0)
must be distinct. Finally run the B5 `--mode consolidate` gate.

The B5.3 strict *raw* 840,320-byte neural trace has NOT been
physically captured. It requires dedicated distinct firmware,
independent DDR trace sidecar ownership and explicit user approval.
Do not present B5.2's hash equality as B5.3 raw-neuron parity.
Official MNIST TEST remains sealed. P07-B.6 and P08-B remain gated.
