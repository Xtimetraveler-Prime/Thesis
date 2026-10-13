# P05.2e — Core 3 packet-bank physical-layout mismatch and surgical remedy

> **Subsequent independent verification (2026-10-12):** The user
> completed the non-destructive retained-KV260-evidence recheck and
> reported `P05_2E_RECHECK_EXIT=0`: all five complete DDR records,
> 40 state checkpoints, 48 packets (24 resident/24 nonresident), and
> original evidence preservation PASS. See
> [P05.2e physical recheck acceptance](P05_2E_RECHECK_ACCEPTANCE.md).
> This document retains the original first-run FAIL and pending-recheck
> instructions **as historical incident context**, not current status.
> Reproduced native pytest totals were not included in that user output.
>
**Status:** Original physical test **FAILED complete DDR golden check**;
source-level cause identified; **existing physical evidence MUST be
independently reverified before declaring P05.2e accepted**.
Original evidence:
`/tmp/v3_p05_2_composite_20261012T190000Z`.
This is a *test-reference/physical-layout translation bug*, not grounds
to dismiss or hide mismatched DDR bytes.

## Observed on physical KV260 (2026-10-12)

The accepted P03.2c FPD128 bitstream was programmed, the same
P05-configurable Cortex-A53 image launched, and the A53 terminal
was `0x600D600D` after two passive host polls. All five *real*
final 512 KiB DDR records were downloaded via PSU physical target.

Original strict verifier:

```text
P05_2E_COMPOSITE_FINAL_DDR=FAIL core 3 final record mismatch at 0x64000 (packet): actual=0x04 expected=0x00
P05_2_COMPOSITE_VERIFY_EXIT=1
```

The A53 completed the full eight-step workload and reported normal
successful status; that does not alone imply DDR correctness. The
old verifier exited nonzero for the first unexpected byte, which
was the **correct fail-closed response** given its old physical
memory expectation. No other difference was yet reported because
the comparison stopped at the first mismatch.

## Source-level diagnosis

There are **two different valid packet orderings**:

- The independent `LogicalChip` normalizes its packet trace by
  sorting `CoreTrace.packets_out` with `packet.logical_key`;
  the primary key includes `destination_core`.
  See `src/loihi_twin_v2/core.py`.
- The packed FPGA `route_words` are written by
  `src/loihi_twin_v2/hardware_p03.py` **in the exact
  original `OutputRouteEntry.routes` iteration order**.
  The physical HLS packet RAM output slots follow those
  registered route descriptor positions.
- Previously accepted triangle/all-to-all three-core cases
  had already-sorted routes, so this ordering distinction
  was not observable in the complete-record golden.
- P05.2e has 5-core wraparound: core 3's registered routes are
  **destination `[4,0]`**, whereas the independent logical
  `CoreTrace.packets_out` sequence is sorted as
  **`[0,4]`**. Other four cores have already-sorted
  destinations `[1,2]`, `[2,3]`, `[3,4]`, `[0,1]`.

The inherited `scripts/p02_4b_ring_fixture.py` writes
the *normalized* `trace.packets_out` into the raw packet
DDR bank starting at `0x64000`. That is valid for earlier
single-route/sorted fanout workloads but **wrong as a
physical RAM oracle for this new route-wraparound case**.

First byte predicted from source configuration and original
model-only vectors, **without using physical DDR to compute
expectations**:

```text
                           packet[0]  packet[1]
Original logical order       core 0     core 4
Real route RAM order         core 4     core 0
Physical observed byte      0x04      (check whole word during reverify)
Old logical expected byte   0x00
```

The observed first byte `0x04` is exactly consistent with
the source-level memory-indexing difference. This explains
the **first** reported failure. Only rechecking all five
complete actual DDR dumps can confirm it was the **only**
cause; we do not assert that prematurely.

## Corrective implementation — NO change to accepted logic

The new `scripts/p05_2_packet_layout.py` derives a
**separate immutable physical packet-RAM golden** using
only the original independent P02 LogicalChip Tcl
`P02B_EXPECT_PACKETS` vectors and the **actual packed
hardware 32-bit route words** from the source configuration.
It matches packet destinations against the configured
per-core order, requires exactly the same packet multiset,
and preserves all neural membrane/state, event, trace,
static configuration and non-packet memory bytes.
It corrects only the two 64-bit packet words [0,1] for
core3, and requires all four other 512 KiB final records
to be entirely unchanged. The golden is written to
`composite_physical_golden/` along with
`p05_2_packet_layout_ledger.json`, *beside* rather than
overwriting `composite_golden/`.

A new strict `scripts/p05_2_composite_verify.py`
uses this model-derived physical golden to compare **all
five COMPLETE 512 KiB DDR records**; it also checks
the same original neural model, state checkpoints,
paging/packet counters, P05G CRC and SHA identities,
and A53 result mailbox. There is **no blanket packet-bank
exclusion, relaxed compare or fabricated PASS**.

`scripts/recheck_p05_2_composite_evidence.py` is a
host-only tool that can reverify the **previously captured
failed** physical evidence. It verifies original
P05G, mailbox, sorted-model reference and physical
dump SHA-256s are unchanged before and after deriving
the route-ordered reference; it rejects missing or
different original `0x04` versus `0x00` evidence.
It creates only a *new* physical-golden directory and
ledger; it does not require reprogramming the board
or overwriting the original `verify.log`.

## Native tests and evidence recheck

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_2_composite.py \
  tests/test_p05_2_fanout.py \
  tests/test_p05_2_order.py \
  tests/test_p05_2_fast.py \
  tests/test_p05_2_fault.py

export P05_2_FAILED="/tmp/v3_p05_2_composite_20261012T190000Z"
set -o pipefail
python scripts/recheck_p05_2_composite_evidence.py \
  --directory "$P05_2_FAILED" \
  2>&1 | tee "$P05_2_FAILED/verify_route_order.log"

cat "$P05_2_FAILED/verify_route_order.log"
```

**Do not rerun the board yet.** If the independent recheck
reports `P05_2E_RECHECK_EXIT=0`, the retained physical
evidence is sufficient to accept P05.2e with the now-correct
physical-memory layout, because every physical output byte
and model checkpoint is rechecked, not merely the reported
first mismatch.

If the recheck reveals **another mismatch**, keep original
physical and new recheck logs, **do not mark acceptance**,
inspect the next offset/bank/actual/expected, and distinguish
another reference translation defect from genuine PS/PL
packet/paging state corruption. Do not modify golden
images to match arbitrary physical bytes.

## Effect on other phases

The accepted P02 physical baseline, P03 scheduler/DDR adapter,
P05 A53 executable, FPD128 bitstream, and unchanged Python
logical model semantics remain frozen. Original P05.2a-d
physical acceptances are unaffected. The amended P05.2e
fixture also pins both the original logical reference
SHA-256s and separately route-ordered physical reference
SHA-256s at offline preparation.

**This correction is necessary to support a claim of
whole-record physical equality in the new dual-route
wraparound topology.** It does not imply the original
A53 success terminal was a false positive; that terminal
covers runtime counters and checking state0, not raw
output packet RAM ordering.
