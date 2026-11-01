# P07-B.5.2 — remaining TRAIN2 and rebooted TRAIN0-repeat physical experiments

**Prepared 2026-11-01; neither new experiment executed in this document.**
Read this before running destructive JTAG tests. Original TRAIN0 and
TRAIN1 26-tick real KV260 physical/independent scalar FNV64 numerical
fingerprint checks have already PASSED. TRAIN1 has label2/class2,
702 dispatches, 26 barriers, actual mailbox
SHA256 \`4410de8c57df98250b0184d352e8edccaeb74bd23a91610579142a44cabf0d95\`.
Original frozen TRAIN3? **No:** only pre-registered ordinal0/1/2
TRAIN-derived validation images are permitted. MNIST official TEST
remains sealed.

## Mandatory physical-session boundaries

Each of the TWO new runs is **separate and destructive** to
the current KV260 standalone/Linux execution state. The accepted
V3 original A53 diagnostic ELF lives in physical low DDR
\`[0,0x00106B00)\`; independent boot-firmware ownership of that range
is **UNPROVEN**. The original V3 CLI requires all **12**
explicit operator approvals to acknowledge that risk and separate
overwrite approvals. Do not infer Linux or boot firmware coexistence
from the previous runs. Confirm dedicated JTAG ownership, recoverable
power cycle and the same accepted original P03 hardware.

**POWER-CYCLE the KV260 BEFORE EACH new hardware takeover. POWER-CYCLE
it AGAIN AFTER ANY hardware takeover attempt (successful OR failed),
before interacting with Linux. Never resume halted Linux.** Do not
re-use or delete any original failed/success evidence directory; each
new run needs a fresh path. If a preflight, physical run or independent
verification fails, preserve the evidence and **stop** instead of
automatically running the next test. P07-B.5 has NOT been closed.

## Prepare Linux VS Code shell and verify pinned original build (PC-only)

\`\`\`bash
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

export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B4L_BINDINGS="$HOME/Thesis_Evidence/p07_b4l_b3_bindings_20261023T011829Z"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B4I_BUILD_DIR="$HOME/p07_b4i_build_20261022T161058Z"
export P07_B4M_DIAG_V3_BUILD_DIR="$HOME/p07_b4m_diag_v3_build_20261101T034702Z"
export P07_B4M_DIAG_V3_OFFLINE_REPORT="$HOME/Thesis_Evidence/p07_b4m_diag_v3_offline_20261101T034702Z.json"
export P07_B4M_DIAG_V3_ELF="$P07_B4M_DIAG_V3_BUILD_DIR/vitis_workspace/p07_b4m_diag_v3_26tick.elf"
export P07_B4M_DIAG_V3_MAP="\${P07_B4M_DIAG_V3_ELF%.elf}.map"

test "$(sha256sum "$P07_B4M_DIAG_V3_ELF" | cut -d' ' -f1)" = "66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904"
test "$(sha256sum "$P07_B4M_DIAG_V3_MAP" | cut -d' ' -f1)" = "148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede"
\`\`\`

If any command fails, STOP and inspect, do not replace the original
signed model, accepted XSA/bitstream, V3 ELF or GNU map.
No Vitis rebuild is required for these two original TRAIN runs.

## A — original frozen TRAIN validation ordinal2 (new physical run)

First run PC-only preflight for **ordinal 2**:

\`\`\`bash
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
  --validation-ordinal 2
\`\`\`

Require \`P07_B4M_DIAG_V3_READ_ONLY_PREFLIGHT_PASS=1\`.
**Now power-cycle KV260**, confirm fresh dedicated XSDB and
actual board recovery, and deliberately invoke this **one** destructive
session:

\`\`\`bash
export P07_B5_RUN2="$HOME/Thesis_Evidence/p07_b5_train2_real_$(date -u +%Y%m%dT%H%M%SZ)"
echo "$P07_B5_RUN2"
test ! -e "$P07_B5_RUN2" || { echo "evidence directory already exists"; false; }

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
  --validation-ordinal 2 \
  --evidence "$P07_B5_RUN2" \
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
\`\`\`

**Now REBOOT KV260** regardless of outcome. Do not resume the halted
Linux session. On success, the host receives
\`P07_B4M_DIAG_V3_STRUCTURAL_RECEIPT_ACCEPTED=1\`.
Then run the read-only independent original TRAIN2 scalar check:

\`\`\`bash
export P07_B5_VERIFY2="$HOME/Thesis_Evidence/p07_b5_verify_train2_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
  --mode verify \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --routes-dir "$P07_B4M_STAGE" \
  --run "2:$P07_B5_RUN2" \
  --out "$P07_B5_VERIFY2"
cat "$P07_B5_VERIFY2"
\`\`\`

Require \`P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1\`;
confirm all seven individual numerical comparisons are TRUE and
all real 702 dispatches/26 barriers are in the report. Keep
\`P07_B5_FULL_RAW_NEURON_PARITY_VERIFIED=0\` as the honest
raw-trace status. Save the exact new evidence-dir and report paths.

**STOP after TEST A** for independent numerical evidence review
if any new run, reboot or scalar check is uncertain or fails.
Do not force a mismatch to pass.

## B — genuine independent COLD-REBOOT repeat of original TRAIN0

This second hardware test is separate: **after A succeeded and the
board was rebooted**, deliberately perform an **additional fresh
power-cycle** immediately before launching the repeat, and record
the operator-observed reboot in the lab notebook. The existing
V3 verifier does not independently sense or prove the reboot.

Run the same exact hash check and a **new PC-only preflight for
ordinal 0**, then a fresh path and destructive run:

\`\`\`bash
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
  --validation-ordinal 0
\`\`\`

Require \`P07_B4M_DIAG_V3_READ_ONLY_PREFLIGHT_PASS=1\`.
**Now POWER-CYCLE KV260 again immediately before this experiment.**

\`\`\`bash
export P07_B5_RUN0_REPEAT="$HOME/Thesis_Evidence/p07_b5_train0_reboot_repeat_real_$(date -u +%Y%m%dT%H%M%SZ)"
echo "$P07_B5_RUN0_REPEAT"
test ! -e "$P07_B5_RUN0_REPEAT" || { echo "evidence directory already exists"; false; }

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
  --validation-ordinal 0 \
  --evidence "$P07_B5_RUN0_REPEAT" \
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
\`\`\`

**REBOOT KV260 AFTER the second JTAG attempt**, success or
failure. Then run this PC-only independent check:

\`\`\`bash
export P07_B5_VERIFY0_REPEAT="$HOME/Thesis_Evidence/p07_b5_verify_train0_repeat_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
  --mode verify \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --routes-dir "$P07_B4M_STAGE" \
  --run "0:$P07_B5_RUN0_REPEAT" \
  --out "$P07_B5_VERIFY0_REPEAT"
cat "$P07_B5_VERIFY0_REPEAT"
\`\`\`

Require marker \`P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1\`.
Since this is original TRAIN0, the physical class, full ten counts,
spike and packet totals and combined trace hash must match the
original accepted ordinal0 evidence: class **1**, readout counts
\`[0,25,0,0,0,0,0,0,0,0]\`, 31,512 CURRENT events,
1,514 spikes, 1,489 routed packets, cumulative
FNV64 \`0xB59CA8594D6E64AD\`.

## C — independent 4-session original TRAIN consolidation (PC ONLY)

Only after original TRAIN0, TRAIN1, TRAIN2 and TRAIN0-repeat each
has a **separate physically captured/independently verified**
evidence folder. This command **reopens** each original raw
256B physical mailbox, each original signed frozen 27-core DDR
readback/binding/route/selected TRAIN frame, and replays the scalar
integer LIF oracle; it does not trust prior JSON "PASS" as a
substitute for the real bytes:

\`\`\`bash
export P07_B5_RUN0="$HOME/Thesis_Evidence/p07_b4m_diag_v3_real_20261101T041302Z"
export P07_B5_RUN1="$HOME/Thesis_Evidence/p07_b5_train1_real_20261101T045754Z"
export P07_B5_SUMMARY="$HOME/Thesis_Evidence/p07_b5_fourrun_original_train_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
  --mode consolidate \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --routes-dir "$P07_B4M_STAGE" \
  --run "0:$P07_B5_RUN0" \
  --run "1:$P07_B5_RUN1" \
  --run "2:$P07_B5_RUN2" \
  --run "0:$P07_B5_RUN0_REPEAT" \
  --out "$P07_B5_SUMMARY"
cat "$P07_B5_SUMMARY"
\`\`\`

Success marker, iff all original physical sessions verified and
numerically identical to their independent scalar references:
\`P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1\`.
Required report fields:
\`genuine_independently_verified_sessions=4\`,
\`distinct_train_validation_frames=3\`,
\`train0_repeat_physical_metrics_and_FNV64_equal=true\`,
\`all_independent_fingerprint_gate_conditions_pass=true\`.
\`cold_reboot_between_runs_independently_proven=false\` remains
intentionally honest in the read-only software-only checker;
the operator must separately attest to the cold power cycle.
No 840,320B RAW FPGA trace was captured by the original V3
mailbox; \`full_raw_per_neuron_hardware_trace_directly_compared=false\`.
This remains an explicit P07-B.5.3 acceptance item, **not**
a reason to call an authentic B5.2 PASS a numerical failure.

## D — B5.3 raw-trace completion is a separate real FPGA test

The original V3 firmware only exposes an FNV64 summary of 26×1010
32-byte HLS neuron-trace words. It is excellent for broad regression
coverage, but **does not export the underlying 840,320B** physical
per-neuron transcript. A strict raw bytewise reference check requires
separately built, hash-pinned, explicitly DDR-owned B5 sidecar
firmware, a physical JTAG readback, a genuine-source verifier, and
additional explicit operator approval. The independent scalar
raw-trace generator and first mismatch decoder exist at
\`scripts/p07_b5_raw_trace_reference.py\`.

Do not introduce a new ELF or sidecar DDR range into these two
V3-only multi-frame experiments. After B5.2 consolidation,
review the raw-trace implementation and physical risk envelope
separately. The B5.4 final acceptance remains pending until
that requirement is physically completed or the operator
explicitly approves a **narrower fingerprint-only acceptance**;
never silently turn a trace-FNV match into "byte-for-byte parity".
Official B2 TEST SEALED; P07-B.6/P08-B not started.
