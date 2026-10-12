# P03.4 — First autonomous 5-over-3 KV260 attempt: WRITE_RESULT fault

**Status:** physical PASS blocked; corrective/forensic candidate not yet independently verified.  
**Evidence directory:** `/tmp/v3_p03_finish_7_20261012T041912Z` (user's Ubuntu PC)  
**Physical attempt:** 2026-10-11 local / 2026-10-12 UTC.  
**Branch:** `agent/v3-p03-autonomous-runtime`, no merge.

## What the physical evidence actually proves

The user's standalone A53 V1 ELF was downloaded and ran on the
previously accepted P03.2c FPD128/SmartConnect MMIO shell. XSDB
passively detected a terminal mailbox after two polls and read
all five full 512 KiB final DDR records from the physical PSU target.

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
PASS: P03 unified board-autonomous A53 ELF downloaded
P03 board-local terminal result=0xDEAD000B after 2 poll(s)
PASS: P03 five authoritative DDR records captured from KV260
FAIL: P03 result: actual=0xDEAD000B expected=0x600D600D
FAIL: P03 error: actual=0xB expected=0x0
FAIL: P03 fault: actual=0xC expected=0x0
FAIL: P03 runtime_phase: actual=0x13 expected=0x12
FAIL: P03 flush_outs: actual=0x800023 expected=0x3
FAIL: P03 autonomous A53 mailbox error=11 first_fault=12 fault_phase=17
P03_FINISH_VERIFY_EXIT=1
```

`first_fault=12` denotes `P03_RT_FAULT_CONTROL_PROTOCOL`, and
`fault_phase=17` denotes `P03_RT_WRITE_RESULT`. All checks reported
by the previous mailbox verifier *other than result/error/fault/phase/
flush_outs* were within expected ranges, including the independent
35-dispatch, seven-barrier and 30-packet counters. This is **strong
evidence the algorithmic loop reached finalization**, not physical
acceptance of the neural results.

The failing callback had previously folded over a dozen final checks
into one short-circuit `if (... || ...)`, discarding the precise
failure reason. `flush_outs=0x800023` is invalid for a three-slot
finalization and equals `0x800020 + 3`. A nonzero baseline is one
plausible explanation but **has not been established from this log**.
Do not claim the BSP failed to initialize BSS without stronger evidence.

**The previous verifier returned immediately on mailbox mismatch
and therefore never checked the five captured DDR records against
the frozen P02.4b physical oracle.** The original `final_ddr`
directory is still diagnostically useful and must be preserved.

## Run forensic comparison of the existing evidence — no board rerun

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
export P03_FINISH_EVIDENCE_7=/tmp/v3_p03_finish_7_20261012T041912Z

PYTHONPATH="$PWD/src" python scripts/p02_4b_ring_fixture.py verify \
  --fixture-dir "$P03_FINISH_EVIDENCE_7/fixture" \
  --dump-dir "$P03_FINISH_EVIDENCE_7/final_ddr"
```

This command performs an independent **byte-exact comparison** of
the five complete physical records and reports the first mismatch by
core, byte offset, and bank. It does not reclassify a failed P03.4
mailbox as a physical PASS. A DDR PASS would narrow the outstanding
fault to finalization/control bookkeeping; a DDR mismatch identifies
a second issue to investigate. Preserve the `identity.txt`,
`a53_run.log`, `p03_a53_result.bin`, and final DDR dumps.

## Corrective/diagnostic candidate V2

Only the **new P03 combined A53 app, strict verifier, tests, and
associated build/runner source stamp** are changed. Previously
accepted P03.2c RTL/bitstream and P03.3b3 adapter are unchanged.

1. Explicitly clear `flush_outs`, `resident_routes`,
   `last_packet`, `first_error` and the finalization diagnostics
   at `main()` entry, independent of assumptions about the
   standalone debugger/boot environment. The flush counter uses a
   `volatile` storage object and a visible reset store.
2. Replace the opaque final `if` with checks of **exactly the same
   required predicates**, each contributing a unique bit to a
   `final_diag_mask`. Retain mandatory page-out, MMIO read, protocol,
   count and quiescence checks; no relaxed acceptance.
3. On WRITE_RESULT failure only, overlay mailbox words 61/62 with
   `0xDA600000 | mask` and the *first failing check's observed
   32-bit value*. The top tag distinguishes this from the last
   genuine HLS packet in older failure mailboxes. PASS mailbox layout
   and record format remain unchanged.
4. The Python verifier decodes the tag and prints
   `P03_FINALIZE_DIAG_MASK=...` plus named predicate(s).
   Crucially, it compares all five final DDR records even if the
   mailbox has already failed and emits either
   `P03_FINAL_DDR_COMPARISON=PASS` or `...=FAIL`.
   It **still returns nonzero** for any mailbox failure.
5. The ELF carries the updated retained identity
   `P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V2`. Existing build and
   board runners reject the previous V1 executable, preventing a
   stale ELF from generating another ambiguous reproduction.
6. Added synthetic regressions for a failed `0xDEAD000B`
   `P03_RT_WRITE_RESULT` mailbox, matching/tagged diagnostic
   fields, byte-exact DDR confirmation on failure, and independent
   corrupted physical DDR diagnosis.

### Failure bit mapping

| Bit | Failed final predicate |
|---|---|
| 0 | Callback adapter context |
| 1 | Final dirty page-out operation |
| 2 | Final MMIO register read |
| 3 | Hardware ID |
| 4 | Hardware capability word |
| 5 | Prior runtime fault |
| 6 | Logical dispatches |
| 7 | Routed packets |
| 8 | Barriers |
| 9 | Timesteps completed |
| 10 | Final event-bank parity |
| 11 | Initial page-ins |
| 12 | Final flush page-out count |
| 13 | Hardware dispatch counter |
| 14 | Hardware page-operation counter |
| 15 | Last hardware page bytes |
| 16 | Global error/status |
| 17 | Hardware pending page bytes |
| 18 | Final hardware quiescence |

The first failing check's actual value accompanies the complete
bitmask in diagnostic word 62. For example, *synthetic* mask
`0x00001000` would mean `final_flush_count` and synthetic
`first_actual=0x00800023`. This is **not yet a verified A53 V2
output**.

## Gate to repeat

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p03_finish_autonomy.py \
  tests/test_p03_3b3_physical_probe.py \
  tests/test_p03_3b_hw_adapter.py \
  tests/test_p03_3a_native_runtime.py \
  tests/test_p02_4b_ring_fixture.py

export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_FINISH_BUILD_DIR="$PWD/vivado/build/p03_finish_v2_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/build_p03_finish.sh 2>&1 | tee /tmp/v3_p03_finish_v2_build.log

# Reboot KV260 before and after standalone execution.
export P03_FINISH_EVIDENCE_7="/tmp/v3_p03_finish_7_v2_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_finish.sh 7 "$P03_FINISH_EVIDENCE_7" \
  2>&1 | tee /tmp/v3_p03_finish_7_v2_physical.log
cat "$P03_FINISH_EVIDENCE_7/verify.log"
```

**Do not start the 100-timestep P03.5 gate until the seven-step
P03.4 mailbox and complete five-record oracle both pass.**
