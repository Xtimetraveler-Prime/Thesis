# P07-A4.2c — Prespecified sustained persistent TRAIN validation1024 gate

**FROZEN 2026-10-17 BEFORE the first physical 1024-image launch.**
The user independently accepted the preceding persistent validation128
cold-reboot gate; that result is documented in
`P07_A4_2C_VAL128_RESTART_ACCEPTANCE.md`.
**Current 1024 gate: PRIMARY AND INDEPENDENT COLD-REBOOT
REPEAT USER-ACCEPTED 2026-10-17.** Both physical
runs reported full independent oracle and DDR readback
pass; 1MiB journals and 64KiB selected traces
byte-identical. See
`P07_A4_2C_VAL1024_PRIMARY_ACCEPTANCE.md` and
`P07_A4_2C_VAL1024_RESTART_ACCEPTANCE.md`.
**Overall A4.2c remains OPEN** pending the separate
physical fail-closed negative gate. TEST SEALED.
Canonical independent MNIST t10k TEST remains **SEALED**; no official
TEST download/IDX opening/prediction/accuracy is authorized here.

## Frozen population, trace and immutable A53 identifiers

- **EXACT 1024 distinct images**, positions `0..1023` in the
  existing precommitted **P06-A3 seeded TRAIN-derived validation
  partition order**, taking `split.validation_indices[:1024]`.
  The pixel data and uint8 class labels come exclusively from
  the original two `train-*.gz` canonical MNIST **TRAIN**
  archives. No shuffle, class balancing, sorting or selected errors.
  The first 128 records must match the already accepted A3.3
  source ID sequence byte-for-byte. These 1024 images are **not
  MNIST official TEST** and are not 1024 *new* examples beyond
  the prior 128: the 128 are included in the first1024.
- **ONE selected 26×42×256-bit full neural trace at input
  ordinal 1023**, the **last** image in the run, to exercise
  trace capture after 1023 other completed images; all
  1024 frames retain 26×10 output spike bits, ten counts,
  packet routing, per-image CRC and progress journal status.
- Original accepted, unchanged persistent A4.2b Cortex-A53 ELF:
  SHA256 `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`
  at `/tmp/v3_p07_a4_persistent_20261017T190943/vitis_workspace/p07_a4_board.elf`.
- Accepted existing P03.2c FPGA XSA SHA256
  `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`
  and frozen 512KiB DDR SHA256
  `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
  Existing 64MiB JTAG-only reserved DDR contract, neuron
  arithmetic, input mapping, 25+1 tick schedule, NEXT routing,
  trained weights, and software oracle remain **unchanged**.
- **Precommitted launches**: `val1024_primary`, then only
  if all primary gates pass, reboot independently and execute
  `val1024_repeat` on byte-identical input and firmware.
  Two successful runs mean **2048 physical frame executions**
  over **1024 distinct validation images**; **not**
  independent official TEST observations.

## Acceptance rules — no post hoc accuracy threshold

1. User-native preflight of exact canonical TRAIN 50k/10k split,
   first1024 source IDs, image/ledger SHA256, 1023 selected trace,
   distinct 1MiB zero initial journal and accepted P07A1 ingress,
   official TEST seal unchanged. Any source manifest or prior
   first128 divergence = STOP.
2. Each physical run follows guarded accepted A4.2c path:
   independent bare-metal KV260 reboot, reserved 64MiB
   JTAG DDR ownership (NEVER Linux concurrently), full binary
   staged readbacks, accepted FPD128 P03.2c bitstream and
   **ONE new persistent A53 ELF launch** for all 1024 images.
   No host-led frame/tick restarts.
3. Every original physical `P07A4R01` journal must be
   terminal success `0x600D600D`, `completed=1024`,
   no first-failure entry, 1024 ordered complete 96B
   CRC-protected records, zero unowned trailing journal
   bytes. Independent P03 packed replay must show EXACT
   correspondence of **all 26×10 output spike flags
   for each 1024-frame instance**, predicted class, ten
   spike counts, silence, NEXT hidden routing, discarded
   boundary packets and external input event totals.
   The selected **last image 1023** must show an EXACT
   **26×42** full-compartment trace (including before,
   accumulator, after, spike/reserved bits).
4. The independent original physical evidence reader requires
   accepted ELF/XSA/master/input hashes, original immutable
   provision/program/PS width/A53 run/oracle verification
   logs, all six original binary DDR staging readbacks,
   complete physical 1MiB result journal and 64KiB trace.
   The host cannot falsely claim physical execution from
   a synthetic or incomplete report.
5. After a **second independent physical reboot**, repeat
   identical input/ELF, preserve separate evidence, rerun
   complete independent oracle and original readback checks.
   Require full **1MiB result journal + 64KiB final-frame
   trace BYTE-FOR-BYTE** equality to primary (not merely
   predictions or count totals). Stop on the first failure;
   never omit, silently retry, renumber, retune or replace
   a validation image.
6. Report diagnostic accuracy only for the **1024 unique
   TRAIN-derived** validation images, if reported at all,
   with explicit selection bias and no official TEST claim.
   Physical full-compartment visibility is only for the
   one preselected last image per run, not all 1024.
   No latency, power or energy claims follow from launch
   completion; these belong to P08.
7. **Physical fault-handling still separate:** after the
   successful larger-run gate, predeclare a dedicated
   negative test that intentionally corrupts a reserved
   input *only after* original JTAG provisioning/readback,
   expects fail-closed A53 `0xDEADxxxx` rather than
   `0x600D600D`, preserves the full original raw
   failure journal and never calls a negative run
   successful inference. Do **not** corrupt canonical
   TRAIN source, accepted primary evidence or frozen ELF.
   This fault experiment has not yet been performed.
   Until accepted, **overall A4.2c remains OPEN**.

## User VS Code native preflight (no board required)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-a-784-axon-streaming
git pull --ff-only origin agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3
set -o pipefail

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a4_val1024.py \
  tests/test_p07_a4_val1024_gate.py \
  tests/test_p07_a4_restart.py \
  tests/test_p07_a4_crosscheck.py \
  tests/test_p07_a4_stream.py

export P07_A4_BUILD_DIR=/tmp/v3_p07_a4_persistent_20261017T190943
export P03_2C_EXPECTED_XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
export P07_A4_STAGE_DIR="$PWD/artifacts/p07_a4_2c_val1024_first_v1"

# NEW, immutable host-only candidate staging dir. Run just ONCE:
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --validation-first 1024 --trace-index 1023 \
  --data-dir data/mnist_raw \
  --out "$P07_A4_STAGE_DIR"

PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir "$P07_A4_STAGE_DIR"
```

Already-created stage must be reused; NEVER overwrite or
recreate previous A3.3/A4.2c acceptance artifacts. The
`p07_a4_2_prepare.py` program accepts only the frozen
first16/128/1024 population choices and exactly trace1023
for 1024 images. No official t10k source is opened.

## A4.2c larger PRIMARY physical launch, once preflight passes

Confirm same P03.2c accepted `$P03_DIAG_REPORTS`,
the same ELF identity and JTAG tools. Create a NEW absolute
evidence directory. Reboot KV260 into the dedicated
bare-metal JTAG-only environment; Linux must not own
the DDR reservation.

```bash
export P07_A4_TIMEOUT=7200
export P07_A4_RUN_DIR="/tmp/v3_p07_a4_val1024_primary_$(date +%Y%m%dT%H%M%S)"
export P07_A4_VAL1024_PRIMARY_EVIDENCE="$P07_A4_RUN_DIR"

# Confirm FPGA's 0x40000000..0x43FFFFFF DDR exclusively
# belongs to JTAG/A53 before executing:
export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a4_physical.sh
```

The physical wrapper checks the accepted XSA/ELF bytes,
hardware width, complete stage and six binary DDR readbacks
before allowing the A53 to execute, then runs the independent
original P03 packed oracle against all 1024 frames.
**Do not continue** if it times out or fails; preserve the
evidence and reboot even on failure. Expected markers:

```text
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A4_2C_PHYSICAL_FRAMES=1024
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
```

**After reboot** (offline, requires preserved original hardware
files, no new JTAG writes):

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_val1024_verify.py \
  --stage-dir "$P07_A4_STAGE_DIR" \
  --primary-dir "$P07_A4_VAL1024_PRIMARY_EVIDENCE"
```

The strict primary evidence gate must return
`P07_A4_2C_1024_PRIMARY_PHYSICAL_GATE_PASS=1`,
`P07_A4_2C_1024_SELECTED_FINAL_TRACE_INDEX=1023` and
`P07_A4_OFFICIAL_TEST=SEALED` before a second run.

## Primary physically accepted — 2026-10-17

The user has reported this exact original primary physical evidence:

```text
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P07_A4_2C_PHYSICAL_FRAMES=1024
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1
P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1
P07_A4_2C_1024_PRIMARY_ORACLE_LOGS_EXACT=1
P07_A4_2C_1024_PRIMARY_DDR_PROVENANCE_EXACT=1
P07_A4_2C_1024_PRIMARY_PHYSICAL_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
```

Original immutable user-local source:
`/tmp/v3_p07_a4_val1024_primary_20261017T200134`.
Preserve the directory; do not rerun or replace the
accepted primary. Only the independently rebooted REPEAT
is pending for this exact 1024-image workload. Once
the repeat passes, this **sustained/restart sub-gate**
can be marked complete; the independent pre-dispatch
physical negative-test `0xDEADxxxx` and fault provenance
remain to close **overall A4.2c**.

## Independent COLD-REBOOT REPEAT — only after accepted primary

Reboot the KV260 independently into JTAG-only mode.
Use the **exact same** staged first1024 pixels and
compiled ELF, a **NEW** evidence directory:

```bash
export P07_A4_RUN_DIR="/tmp/v3_p07_a4_val1024_repeat_$(date +%Y%m%dT%H%M%S)"
export P07_A4_VAL1024_REPEAT_EVIDENCE="$P07_A4_RUN_DIR"

export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a4_physical.sh
```

**Reboot KV260 after this run too**, even if the runner
fails. Then rerun the read-only strict dual evidence gate:

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_val1024_verify.py \
  --stage-dir "$P07_A4_STAGE_DIR" \
  --primary-dir "$P07_A4_VAL1024_PRIMARY_EVIDENCE" \
  --repeat-dir "$P07_A4_VAL1024_REPEAT_EVIDENCE" \
  --report "$P07_A4_VAL1024_REPEAT_EVIDENCE/p07_a4_2c_1024_physical_restart.json" \
  | tee "$P07_A4_VAL1024_REPEAT_EVIDENCE/restart_verify.log"
```

Expected:

```text
P07_A4_2C_1024_PRIMARY_ORACLE_LOGS_EXACT=1
P07_A4_2C_1024_REPEAT_ORACLE_LOGS_EXACT=1
P07_A4_2C_1024_PHYSICAL_LAUNCHES=2/2
P07_A4_2C_1024_HARDWARE_IMAGE_EXECUTIONS=2048
P07_A4_2C_1024_JOURNAL_1M_BYTE_EXACT=1
P07_A4_2C_1024_TRACE_64K_BYTE_EXACT=1
P07_A4_2C_1024_RESTART_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
```

**The above cold-repeat acceptance targets were observed
by the user on 2026-10-17.** Complete original terminal
output, 2/2 exact journal/trace repeat markers and
physical acceptance JSON path are recorded in
`P07_A4_2C_VAL1024_RESTART_ACCEPTANCE.md`.
Original read-only physical evidence remains on
the user's PC; it was not uploaded here. This
completes the sustained 1024 repeated inference gate
only. The separate one-word synthetic descriptor
corruption physical gate remains pending before
overall A4.2c closes. No TEST unseal authorized.
