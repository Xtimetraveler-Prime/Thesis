# P08-B4.2 — Original full1024 A53 source admission, physical JTAG & independent validation

**Source implementation status: NO BOARD CI ONLY.** Physical B4.2 tests
were not run by the developer: the user has only calculated **shard 0**
of 64 required full1024 independent scalar shards. The previously
Vitis-built original B2.3 full1024 A53 ELF/map were observed earlier
as read-only signed artifacts but must be **located, copied and
re-authenticated** locally. No B4.2 full1024 physical run is permitted
until all 64 scalar shards, immutable merged oracle, genuine exact
full1024 Vitis ELF/map, original accepted P03 reports, signed original
27-core source staging and user local PRE-FLIGHT all PASS.

Previously separately accepted B3 physical evidence:
- third real 16/16 KV260 full run
  /home/dna/Thesis_Evidence/p08_b3_pilot16_physical_retry_20261102T053637Z
- independently verified report
  /home/dna/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json
- SHA256 b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11

## B4.1 missing required genuine references (PC ONLY)

Update the new B4 development branch:

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b4-fullscale
git pull --ff-only origin agent/v3-p08-b4-fullscale
git status --short
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b4_1_scalar_1024.py \
  tests/test_p08_b4_2_full1024_physical.py \
  tests/test_p08_b2_4_numerical.py \
  tests/test_p08_b3_pilot16_physical.py
~~~

**Reuse exact previously PASSed shard-0 directory; do not recreate/overwrite:**

~~~bash
export P08_B4_SHARDS="$HOME/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z"
export P08_B4_A_STAGE="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P08_B4_DATA_DIR="$PWD/data/mnist_raw"
export P08_B4_FROZEN="$PWD/artifacts/p06_b24_frozen_1000"
export P08_B4_ROUTES="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P08_B4_INGRESS="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
test -f "$P08_B4_SHARDS/p08_b4_1_scalar_shard_00.json"
test "$(sha256sum "$P08_B4_FIRST16" | cut -d' ' -f1)" = \
  "13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271"
~~~

Compute ALL remaining 63 shards in order, never overwrite a prior
signed result. Each calls the real frozen B2.4 independent scalar
simulator; an interrupted batch retains already completed shards.
The loop prints exact failing ordinal and stops on any failure.

~~~bash
for i in $(seq 1 63); do
  output=$(printf '%s/p08_b4_1_scalar_shard_%02d.json' "$P08_B4_SHARDS" "$i")
  if [ -e "$output" ]; then
    echo "B4.1 REFUSE OVERWRITE: $output"
    break
  fi
  PYTHONPATH="$PWD/src" python scripts/p08_b4_1_scalar_shard.py \
    --shard "$i" \
    --frozen-dir "$P08_B4_FROZEN" \
    --a-stage "$P08_B4_A_STAGE" \
    --train-data-dir "$P08_B4_DATA_DIR" \
    --routes-dir "$P08_B4_ROUTES" \
    --ingress-dir "$P08_B4_INGRESS" \
    --first16-oracle "$P08_B4_FIRST16" \
    --out "$output" || break
done
~~~

After exactly 64 source-authenticated 16-row reports exist:

~~~bash
find "$P08_B4_SHARDS" -maxdepth 1 -type f \
  -name 'p08_b4_1_scalar_shard_*.json' | wc -l

export P08_B4_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B4_FULL_ORACLE"
PYTHONPATH="$PWD/src" python scripts/p08_b4_1_merge_scalar_1024.py \
  --shards-dir "$P08_B4_SHARDS" \
  --ingress-dir "$P08_B4_INGRESS" \
  --first16-oracle "$P08_B4_FIRST16" \
  --out "$P08_B4_FULL_ORACLE"
sha256sum "$P08_B4_FULL_ORACLE"
~~~

Expected merge:
P08_B4_1_ALL_1024_ORIGINAL_SCALAR_ROWS_ADMITTED=1
P08_B4_1_ALL_64_SHARDS_SHA_VERIFIED=1
P08_B4_1_ACCEPTED_FIRST16_SCALAR_REPRODUCED=1

## B4.2 original full1024 genuine Vitis ELF/map source

**Do NOT relink from a changed compiler model or use B3 pilot16 ELF.**
The original previously read-only admitted B2.3 full1024 source has
unique AArch64 ELF SHA-256
0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1
and map SHA-256
f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc.
These were reported previously for original genuinely built 1024-image
B2.3 candidate, but physical owner exclusivity is still unproven.

Locate local genuine prior ELF and map **by SHA only**:

~~~bash
find "$HOME/Thesis_Evidence" -type f \( -name '*.elf' -o -name '*.map' \) \
  -exec sha256sum {} + | grep -E \
  '^(0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1|f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc) '
~~~

If these exact two files are not found, **STOP**. Do not
substitute the pilot16 ELF or an unverified freshly built file.
Use the existing B2.3 local genuine Vitis build/admission workflow
or report that the original full1024 files are unavailable.

After identifying BOTH source paths, stage copies with exact canonical
full1024 filenames (replace placeholders with actual reported paths):

~~~bash
export P08_B4_ELF_SOURCE="/absolute/path/to/authenticated-original-b23-1024.elf"
export P08_B4_MAP_SOURCE="/absolute/path/to/authenticated-original-b23-1024.map"
export P08_B4_ELF_DIR="$HOME/Thesis_Evidence/p08_b4_2_signed_full1024_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B4_ELF_DIR"
mkdir -m 700 "$P08_B4_ELF_DIR"
cp -- "$P08_B4_ELF_SOURCE" "$P08_B4_ELF_DIR/p08_b4_original_full1024.elf"
cp -- "$P08_B4_MAP_SOURCE" "$P08_B4_ELF_DIR/p08_b4_original_full1024.map"
export P08_B4_ELF="$P08_B4_ELF_DIR/p08_b4_original_full1024.elf"
export P08_B4_MAP="$P08_B4_ELF_DIR/p08_b4_original_full1024.map"
test "$(sha256sum "$P08_B4_ELF" | cut -d' ' -f1)" = \
  "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
test "$(sha256sum "$P08_B4_MAP" | cut -d' ' -f1)" = \
  "f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc"
~~~

## B4.2 mandatory read-only full1024 physical admission (NO BOARD)

Reuse original signed six-source stage and accepted reports:

~~~bash
export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json"
test "$(sha256sum "$P08_B3_INDEPENDENT_REPORT" | cut -d' ' -f1)" =   "b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11"
# Keep P07_B4L_REPORTS pointing to previously accepted genuine P03 shell reports.
test -f "$P07_B4L_REPORTS/p03_2_ps_mmio.bit"

PYTHONPATH="$PWD/src" python scripts/p08_b4_2_physical_run.py \
  --mode preflight \
  --stage "$P08_B3_PILOT_STAGE" \
  --shards "$P08_B4_SHARDS" \
  --ingress "$P08_B4_INGRESS" \
  --oracle "$P08_B4_FULL_ORACLE" \
  --first16 "$P08_B4_FIRST16" \
  --b3-report "$P08_B3_INDEPENDENT_REPORT" \
  --elf "$P08_B4_ELF" \
  --linker-map "$P08_B4_MAP" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --reports "$P07_B4L_REPORTS"
~~~

Require:
P08_B4_2_ORIGINAL_ALL1024_SCALAR_AND_GENUINE_ELF_OFFLINE_PREFLIGHT_PASS=1
P08_B4_2_READONLY_BOARD_VISITED=0
P08_B4_2_DDR_BOOT_FW_DMA_OWNER_EXCLUSIVITY_PROVEN=0

**No B4 full-scale JTAG execution before this exact PASS.**

## Destructive original 1024-image KV260 JTAG experiment AFTER all above pass

User previously acknowledged residual independent FSBL/firmware/DMA,
Linux interruption and DDR/PL destructive risks; new B4.2 runner still
requires eight explicit separate YES arguments. Must use a
dedicated recovery-ready power-cycle/cold-boot JTAG session,
working local hw_server at tcp:127.0.0.1:3121 and freshly emptied
evidence root. If any risk is unacceptable, do not execute.
This full1024 image run may take substantially longer than B3;
polling has an absolute bound of 172800 x 1-second checks AND
a fail-closed 3600-poll no-completed-image watchdog; either timeout is
**NOT** success. Power-cycle KV260 after any JTAG attempt,
including failure. Do NOT resume halted Linux.

~~~bash
export P08_B4_PHYSICAL="$HOME/Thesis_Evidence/p08_b4_2_original1024_physical_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B4_PHYSICAL"
command -v xsdb
command -v vivado
ss -ltn | grep ':3121'

PYTHONPATH="$PWD/src" python scripts/p08_b4_2_physical_run.py \
  --mode execute \
  --stage "$P08_B3_PILOT_STAGE" \
  --shards "$P08_B4_SHARDS" \
  --ingress "$P08_B4_INGRESS" \
  --oracle "$P08_B4_FULL_ORACLE" \
  --first16 "$P08_B4_FIRST16" \
  --b3-report "$P08_B3_INDEPENDENT_REPORT" \
  --elf "$P08_B4_ELF" \
  --linker-map "$P08_B4_MAP" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --reports "$P07_B4L_REPORTS" \
  --evidence "$P08_B4_PHYSICAL" \
  --dedicated-jtag-owner YES \
  --discard-linux-and-halt-all-a53-approved YES \
  --unproven-boot-ddr-dma-exclusivity-risk-accepted YES \
  --six-original-ddr-transfers-overwrite-approved YES \
  --original-p03-pl-programming-approved YES \
  --low-ddr-full1024-elf-overwrite-approved YES \
  --mailbox-and-full1024-journals-overwrite-approved YES \
  --reboot-and-recovery-approved YES
~~~

Expected completion (first pass, NOT final independent provenance):

- P08_B4_FULL1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1
- P08_B4_FULL1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1
- P08_B4_FULL1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1
- P08_B4_2_FULL1024_REAL_HARDWARE_NUMERICAL_PRECHECK_PASS=1
- P08_B4_2_INDEPENDENT_PHYSICAL_PROVENANCE_VERIFICATION_PENDING=1

After KV260 reboot, **independently verify** the actual same-session
source readback, authentic XSDB, full1024 journal CRC/FNV/spikes and
all 1024 internally consistent A53 service phases:

~~~bash
export P08_B4_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b4_2_independent1024_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B4_INDEPENDENT_REPORT"
PYTHONPATH="$PWD/src" python scripts/p08_b4_2_independent_physical_verify.py \
  --evidence "$P08_B4_PHYSICAL" \
  --stage "$P08_B3_PILOT_STAGE" \
  --shards "$P08_B4_SHARDS" \
  --ingress "$P08_B4_INGRESS" \
  --oracle "$P08_B4_FULL_ORACLE" \
  --first16 "$P08_B4_FIRST16" \
  --b3-report "$P08_B3_INDEPENDENT_REPORT" \
  --elf "$P08_B4_ELF" \
  --linker-map "$P08_B4_MAP" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --reports "$P07_B4L_REPORTS" \
  --out "$P08_B4_INDEPENDENT_REPORT"
sha256sum "$P08_B4_INDEPENDENT_REPORT"
~~~

Even one genuinely independently verified 1024-image physical run is
**not** the final 6-session matched Track A/B latency benchmark:
there remain full six independent AB/BA/AB cold-boot sessions,
frame 1023 intrusive trace-scope control, correct CNTFRQ/CNTVCT
service-boundary comparison and instrumentation caveats.
No present energy, speedup, PL-only performance, exclusive firmware
DDR ownership or official MNIST TEST claims.
