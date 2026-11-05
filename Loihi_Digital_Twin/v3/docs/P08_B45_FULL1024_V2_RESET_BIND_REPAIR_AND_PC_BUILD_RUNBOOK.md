# P08-B4.5 unprotected FULL1024 V2 A53 startup / reset-bind repair (PC-ONLY build gate)

> **2026-11-05 independent-verifier CLI repair (NO BOARD).** The
> operator successfully executed a genuine V2 `once` full1024 A53
> physical session: original six DDR physical readbacks, strict
> 1024-frame terminal, 3x1024 timing/journal/reset-profile records,
> 27 postrun backup physical captures, and *in-run* original scalar/FNV
> and backup PASS. The separately invoked PC-only independent reviewer
> DID NOT RUN: argparse rejected `--pilot-once-report` and
> `--pilot-unchecked-report` passed by existing
> `P08_B45_FULL_COMMON`. These are actually required by
> `bench.admission(args)`. Fixed the independent reviewer's CLI to
> **require both flags**, preserving all original source SHA pins.
> New native parser regression covers `once` and `unchecked`.
> The V2 once report is still PENDING independent acceptance.
> The operator reported unchecked physical execution in progress;
> **no unchecked outcome is claimed at this update**.
> Do not restart, switch branches, or modify files locally while
> an active XSDB physical runner is using this checkout; after the
> physical attempt ends, power-cycle the KV260 as prescribed,
> `git pull --ff-only` and re-run ONLY independent PC verification
> with the previously defined `P08_B45_FULL_COMMON` unchanged.
> No fresh ELF or physical repeat is required for this CLI fix.
>


## Accepted failure diagnosis and limits

Operator's real 2026-11-05 original A53 once full1024 JTAG session:
`/home/dna/Thesis_Evidence/p08_b45_perf_once_full1024_physical_20261105T172141Z/`.
Independent read-only failed-run JSON:
`/home/dna/Thesis_Evidence/p08_b45_failure_diagnostic_20261105T174301Z.json`,
user-reported SHA `e500d8a6507ff4319216fc9e6a3ca1b7fce8a46e6d58d333f9e73b86a3324fb3`.
Failure mailbox SHA `8b7aa5810c9bf5977218936a0314a1fcfac3b07073b6dd8d4da625e9147e7231`.
Genuine A53 FAIL `0xDEAD0823`, fault `105`, frame `0xFFFFFFFF`
BEFORE the first image, decoded `-bind_result=1` i.e.
`p08_b45_perf_reset_bind` returned `P08_B45_RESET_INVALID=-1`.
This **does not** mean one completed image: all three genuine original
1024x256B journal/timing/reset profile captures contain 1024 ZERO
rows. Full reference prediction/FNV test never started and is not
failed numerical parity. The 27 backup records were never reread
after this aborted run.

**Important extra evidence:** `pager.counters.dispatches=702` and
`pager.counters.barriers=26` in the PRE-LOOP FAILURE mailbox.
Inspection of both original A53 mains shows that the pager is
initialized ONLY later inside per-image `prepare_new_scheduler()`,
which did not run. These 702/26 counters strongly support stale
bare-metal global/BSS state on the new JTAG launch
(`rst -processor` issued a reset-vector warning). We cannot
prove the precise failing bind-validation branch or preexisting
`reset_state.magic` from the old 256B mailbox, which did not record
it. Thus the fix is a narrow, evidence-based **fresh-state startup
repair**, not a claim that a specific magic value was observed.

## Reviewed V2 fix to BOTH original full1024 unprotected variants

New branch `agent/v3-p08-b45-full1024-reset-bind-repair`.
`once` and `unchecked` A53 full1024 mains retain original
27-core P02/26tick/702 neural logic, same 1024 frozen TRAIN scalar
oracle, every 256B journal/timer/reset sidecar, no XMPU,
no restored security guarantee and same 27 backup postrun
readback requirement. **No physical ELF yet built or tested.**

* A single `prepare_first_entry_workspaces()` call explicitly zeros
  all original A53 static workspace/pager/scheduler/metadata buffers,
  outside the measured service interval, before P03 initialization
  and first image. Crucially it does NOT blanket-zero the reset state
  or user/backing DDR or original backup.
* New `p08_b45_perf_startup.c/.h` checks the exact original 27x
  512KiB mutable/backup geometry, both 14,155,776-byte physical
  disjoint ranges, reset-state and trusted SHA pointer exclusion,
  required cache/quiescence/barrier callbacks and mode requirements
  **before touching the reset state**. It records old magic,
  generation and poison, and clears only the isolated state once
  per newly loaded standalone entry. Original
  `p08_b45_perf_reset_bind` remains fail-closed if the
  configuration is still invalid; the protected-mode kernel and
  accepted pilot16 binaries/sources are untouched.
* Real A53 `fault 105` ONLY gains new *failure-only* mailbox
  words: word14 `0x504D4244` signature, word15 detailed
  startup reason (0 valid, 1–9 specific invalid causes), word16
  original magic before zeroing, words17/18 prior generation/poison,
  words19/20 prior pager dispatch/barrier counters, word21
  whether state was safely initialized. The original PASS
  mailbox and neural result format is UNCHANGED.
  New saved-run postmortem decodes both original V1 and this V2.
* V2 genuine ELF mode identity `P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V2`
  or `P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V2`
  is required by the Vitis builder, offline ELF/map admission and
  XSDB physical capture Tcl. **Original V1 ELF cannot pass the new
  admission**; reusing the previous build directory is refused.
* Native strict C11 tests exercise stale reset magic, reset-poison,
  both modes, missing SHA, overlapping memory, invalid geometry,
  callback failures, original guard preservation, new V2 linker
  gate, independent first16 and V1 failed-capture decoders.
  CI runs on PC/GitHub only; it does NOT attest Vitis or KV260.

## User: PC VS Code terminal — pull + tests (NO PuTTY)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-full1024-reset-bind-repair
git pull --ff-only origin agent/v3-p08-b45-full1024-reset-bind-repair
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b45_full1024_reset_bind_repair.py \
  tests/test_p08_b45_perf_full1024.py \
  tests/test_p08_b45_perf_full1024_tcl.py \
  tests/test_p08_b45_full1024_failed_run_postmortem.py \
  tests/test_p08_b45_perf_pilot16.py \
  tests/test_p08_b45_reset_variants.py
```

## User: build TWO genuine V2 A53 ELFs on PC, new output directories

Reuse the accepted source env values from prior full1024 original
runbook, including `P08_B45_ORIGINAL_ELF`,
`P08_B2_RESET_PINS` and `P07_B4L_REPORTS`.
See section B of
[original full1024 runbook](P08_B45_UNPROTECTED_FULL1024_PHYSICAL_WITH_LIVE_MONITOR_RUNBOOK.md)
for **ALL** prior `export` commands after opening a fresh terminal.
These are only file reads and Vitis 2025.2 builds on PC.

```bash
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"

export P08_B45_MODE=once
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_b45_perf_full1024.sh
export P08_B45_FULL_ONCE_BUILD="$P08_B45_BUILD_DIR"

export P08_B45_MODE=unchecked
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_full1024_V2_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_b45_perf_full1024.sh
export P08_B45_FULL_UNCHECKED_BUILD="$P08_B45_BUILD_DIR"
```

Expected genuine Vitis source stage and fresh ELF/map static
admission marker `P08_B45_PERF_1024_GENUINE_A53_ELF_STATIC_ADMISSION_PASS=1`.
Examine actual SHA and new V2 identity:

```bash
grep -aF P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V2 \
 "$P08_B45_FULL_ONCE_BUILD/vitis_workspace/p08_b45_perf_once_full1024.elf"
grep -aF P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V2 \
 "$P08_B45_FULL_UNCHECKED_BUILD/vitis_workspace/p08_b45_perf_unchecked_full1024.elf"
sha256sum \
 "$P08_B45_FULL_ONCE_BUILD/vitis_workspace/p08_b45_perf_once_full1024.elf" \
 "$P08_B45_FULL_UNCHECKED_BUILD/vitis_workspace/p08_b45_perf_unchecked_full1024.elf"
```

Recreate `P08_B45_FULL_COMMON` only from section D of the
original full1024 runbook (includes frozen 64 scalar shards, both
successful original 16 physical reports and original 1024 B4.4
physical baseline). Perform BOTH existing V2-compatible
`--mode preflight` calls after new ELFs:
```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_physical_run.py \
 --experiment once --build "$P08_B45_FULL_ONCE_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" --mode preflight

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_physical_run.py \
 --experiment unchecked --build "$P08_B45_FULL_UNCHECKED_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" --mode preflight
```

**NO physical JTAG yet on the basis of this code change alone.**
Once both *new genuine V2* ELF builds and both PC preflights PASS,
operator can deliberately approve fresh dedicated JTAG session(s)
using the same VS Code 2-terminal host-progress workflow already
reviewed, and physically POWER CYCLE after ANY attempt. However,
do not re-run the old V1 ELF or automatically launch unchecked if
once failed. Preserve old failed original capture and incident JSON.
Do not relax hash or source expected values to get a PASS.
The original protected-memory guard remains fail-closed and
original official MNIST TEST SEALED. No draft PR merges.

## Is any extra diagnostic needed BEFORE the V2 rebuild?

**No board-side diagnostic is needed right now.** The old
mailbox and three zero journals have already isolated the
failure to pre-image-0 bind and shown stale pager counters.
A read-only review of the old operator V1 ELF/map could further
investigate exact placement, but will NOT recover the
unrecorded prezero reset-state magic. The V2 failure mailbox
is explicit if another bind failure occurs. Stop at offline
build/preflight failures and paste those PC logs for repair.
