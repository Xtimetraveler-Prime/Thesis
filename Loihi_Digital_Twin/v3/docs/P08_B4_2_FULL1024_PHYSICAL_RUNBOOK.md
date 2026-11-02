# P08-B4.2 — Original full1024 A53 source admission, physical JTAG & independent validation

## B4.2 ACCEPTED: genuine independently verified first 1024-image physical KV260 inference, 2026-11-02

Operator ran the full ORIGINAL frozen B2.4 1,024-image A53 physical
experiment, then separately executed the PC-only independent same-session
physical provenance, scalar neural output and timing verification.
All mandatory original full1024 markers PASS:

~~~text
P08_B4_FULL1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1
P08_B4_2_FULL1024_REAL_HARDWARE_NUMERICAL_PRECHECK_PASS=1
P08_B4_2_ALL_1024_ORIGINAL_NEURAL_AND_SPIKE_VECTORS_PHYSICAL_PARITY_PASS=1
P08_B4_2_ALL_1024_A53_SERVICE_TIMERS_PHYSICAL_CAPTURE_VALID=1
P08_B4_2_INDEPENDENT_SAME_SESSION_PHYSICAL_PROVENANCE_PASS=1
P08_B4_2_SIX_SESSION_TRACKB_LATENCY_BENCHMARK_ACCEPTED=0
~~~

Immutable operator external receipt (preserve, NEVER overwrite):

- Independent full1024 report:
  /home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json
- Independent report SHA256:
  **297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032**
- Frozen original full1024 scalar JSON:
  /home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json
- Frozen full scalar SHA256:
  **7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8**.
- Exact original *physical session evidence path* was NOT pasted in
  the user transcript; use the original already set P08_B4_PHYSICAL variable,
  not a guessed directory name.

The independently verified genuine same-session JTAG evidence covers
original 27 mutable P02 512KiB model contexts, 27 separately staged
immutable backup contexts, bindings/routing and raw1024 matched TRAIN-only
data; exact 1024/1024 A53 terminal; all 1024 neural journal/spike vector/
26tick x 1010-neuron FNV fingerprints agreeing with independent frozen
original scalar simulation; and all 1024 internally consistent A53
service timing rows.

**Accepted: SINGLE-SESSION genuine physical 1024-image numerical/FNV
equivalence and timing consistency.** NOT accepted: six-session repeated
counterbalanced Track A/B physical latency, direct complete raw neural
trace, energy, PL-only speedup or independently proved boot/firmware/PS/
PL-DMA DDR ownership. Official MNIST TEST still SEALED.

### KEEP FOREVER: Non-intrusive PC-only live mailbox progress monitor

The original full1024 XSDB Tcl emits no per-image console progress after
downloading the ELF. It polls A53 mailbox via JTAG from the ORIGINAL
single JTAG owner, then writes a **PC-side copy** to:

- <exact active session>/full1024_capture/mailbox_poll.tmp
- Once terminal is observed, it renames that PC copy to
  mailbox_terminal_physical.bin.

The 256-byte record has 64 little-endian uint32 words:
word 2 status (0xC0DE0000 progress; 0x600D0823 terminal success;
0xDEAD0823 terminal failure); word 3 most recently completed ordinal
(0xFFFFFFFF before the first image); word 4 fault; word 5 images
completed out of 1024; word 63 DONE sentinel 0xC0DEF00D.
**DONE alone does NOT mean SUCCESS**; every intermediate progress message
also contains DONE. A successful terminal requires status SUCCESS,
ordinal 1023, zero fault, completed 1024.

**Second PC terminal while original session CONTINUES uninterrupted:**

~~~bash
# Reuse the variable from the running shell, or set explicitly to the
# actual active session. Never accidentally monitor an older run.
export P08_B4_MONITOR="$P08_B4_PHYSICAL"
test -d "$P08_B4_MONITOR/full1024_capture"

cd ~/Git/Thesis/Loihi_Digital_Twin/v3
python scripts/p08_b4_2_monitor_mailbox_pc_only.py \
  --evidence "$P08_B4_MONITOR" --samples 2 --interval 20
~~~

If the session variable is missing, use read-only FILE discovery,
identify the matching ACTIVE session, then explicitly set the variable:

~~~bash
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
  -name 'p08_b4_2_original1024_physical_*' -printf '%T@ %p\n' | sort -nr
# export P08_B4_MONITOR="/home/dna/Thesis_Evidence/<EXACT CURRENT SESSION>"
~~~

The original useful *direct Python command* is also saved here for
cases where the wrapper has not been pulled yet. It reads only files
the running XSDB already wrote on the PC; it opens NO JTAG connection.

~~~bash
python - <<'PY'
import os, struct, time
from pathlib import Path

directory = Path(os.environ["P08_B4_MONITOR"]) / "full1024_capture"
for sample in range(2):
    print(f"\n--- PC-only snapshot {sample+1} ---")
    for name in ("mailbox_terminal_physical.bin", "mailbox_poll.tmp"):
        try:
            raw = (directory / name).read_bytes()
        except FileNotFoundError:
            continue
        if len(raw) != 256:
            print("Temporary partial write; recheck:", len(raw))
            break
        w = struct.unpack("<64I", raw)
        states = {0xC0DE0000: "PROGRESS",
                  0x600D0823: "SUCCESS",
                  0xDEAD0823: "FAILURE"}
        state = states.get(w[2], f"UNKNOWN 0x{w[2]:08X}")
        print("File:", name, "Status:", state)
        print("Completed:", w[5], "/ 1024",
              "Last frame:", w[3], "Fault:", w[4])
        print("DONE:", hex(w[63]))
        if w[0] != 0x50384232 or w[1] != 1 or w[63] != 0xC0DEF00D:
            print("Incomplete/invalid snapshot; do not infer success")
        if state == "SUCCESS" and (w[3], w[4], w[5]) != (1023, 0, 1024):
            print("Invalid terminal fields; do not infer success")
        break
    else:
        print("Snapshot temporarily absent; XSDB may be replacing it")
    if sample == 0:
        time.sleep(20)
PY
~~~

Both commands are read-only reads of PC-side evidence. Never open
another XSDB, reset or halt the A53, or cancel the active runner to
check progress. The XSDB worker deletes/recreates mailbox_poll.tmp
approximately once per second, so a short-lived missing/partial
snapshot is normal. An unchanged count over 20 seconds alone is
NOT proof of a hang. The ORIGINAL full1024 Tcl has a fail-closed
3600-poll no-completed-image watchdog and an independent absolute
poll bound. Always preserve evidence and REBOOT KV260 after any
destructive JTAG attempt; never resume the halted Linux.

---

## Latest operator results: ALL 1024 original scalar rows and original full1024 ELF/map verified

**B4.1 is now accepted** on genuine operator-local artifacts: 64/64 independent original B2.4 scalar shards, merge PASS, accepted first16 continuity. Full original scalar oracle
`/home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json`;
SHA256 **`7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8`**. The B4.2 source runner now independently rehashes this exact SHA and re-merges all 64 original signed chunks.

Operator original B2.3 genuinely-built matching ELF:
`/home/dna/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf`, with SHA
`0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1`.
Original matching map:
`/home/dna/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.map`,
SHA `f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc`.

For a new operator session, **skip the previous "find ELF" and "compute 63 shards" steps**; these are preserved completed original assets. Set:

~~~bash
export P08_B4_SHARDS="$HOME/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z"
export P08_B4_INGRESS="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
export P08_B4_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
export P08_B4_ELF_SOURCE="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B4_MAP_SOURCE="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.map"
export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json"
export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
sha256sum "$P08_B4_FULL_ORACLE" "$P08_B4_ELF_SOURCE" "$P08_B4_MAP_SOURCE" "$P08_B3_INDEPENDENT_REPORT"
~~~

After confirming the exact SHA pins above, create the **new** original full1024 canonical ELF/map copies as described in the later section (no need to recompile). Then run **read-only B4.2 preflight**; don't contact KV260 until it prints the signed full1024 acceptance marker. The board must be rebooted and dedicated before destructive JTAG.

**Source implementation status: NO BOARD CI ONLY.** Physical B4.2
has NOT yet been attempted, although the operator has now genuinely
generated and SHA-256 authenticated **64/64 original scalar shards** and
the complete original B2.4 1,024-image scalar oracle and located the
SHA-verified genuine full1024 B2.3 Vitis ELF/map. A new canonical
copy of the latter plus authentic *local read-only B4.2 preflight*
remain mandatory before any B4.2 destructive JTAG. Original P03 reports,
signed original 27core source staging and separately accepted B3
independent physical report must pass the source gate.

Previously separately accepted B3 physical evidence:
- third real 16/16 KV260 full run
  /home/dna/Thesis_Evidence/p08_b3_pilot16_physical_retry_20261102T053637Z
- independently verified report
  /home/dna/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json
- SHA256 b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11

## B4.1 original references accepted (historical generation procedure; PC ONLY)

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

**Already completed (64/64): preserve exact original shard directory; do not recreate/overwrite:**

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

**Historical command only; do NOT recompute the 63 already accepted shards.**\n\nCompute ALL remaining 63 shards in order, never overwrite a prior
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
