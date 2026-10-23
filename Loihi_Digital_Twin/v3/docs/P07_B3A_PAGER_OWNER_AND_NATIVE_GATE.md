# P07-B.3a — 27-core / 3-slot acknowledgment-driven paging plan (native candidate)

**Status:** P07-B.3a new C11 paging **design/native gate awaiting user verification**. B.1, B.2a and **corrected full B.2b** are **user-attested host-native PASS**; see additive ledgers under `docs/P07_B*.json`. Current branch: `agent/v3-p07-b-scaled-physical-inference`. PR #49 remains DRAFT/UNMERGED. B2 official MNIST TEST is **SEALED**.

## Source provenance and limits

This stage independently transcribes the existing accepted P06-B1.5 `ResidentLRU` policy from `src/loihi_twin_v2/p06_b15_paging.py`, compiles against the **real existing P03 and P05 C headers**, and preserves the P03 `p03_rt_ops` rule: a page operation must complete and be acknowledged **before** the logical slot owner can change.

The B1.5 reference performs *one engine* and **three slots** over **27 frozen B2-model logical core IDs (0–26)**, **26 epochs**, **702 dispatches**, and **26 end-of-epoch barriers**. This is a schedule/ownership **plan**, not neural inference; no P02 B2.4 initial image, trained weight, checkpoint, MONOLITHIC oracle or official TEST image is read by new B.3a tests. A53 memory ownership and hardware cache coherency are **not proven**.

### C11 source and action contract

`software/p07/include/p07_b3_pager.h`, `software/p07/p07_b3_pager.c` implement:

- Fixed **P02 record address** `0x40000000 + 0x80000 * logical_id` (27 records end at `0x40D80000`), uniquely resident in up to 3 numbered slots. A native compile-time admission binds `P03_HW_BACKING_BASE`, `P03_HW_RECORD_BYTES`, `P03_HW_FULL_PAGE_BYTES`, `P03_HW_MUTABLE_BYTES`, `P03_RT_MAX_SLOTS` and `P05_DEPLOY_MAX_CORES` to the established P03/P05 headers rather than inventing a new physical memory ABI.
- Predeclared deterministic service policies: **ascending every epoch** and **alternating ascending/descending**. Every logical core is dispatched **exactly once per epoch**. Smallest free slot first; on a miss with no free slots evict **least recently dispatched** core (tie-break lowest slot), as in the B1.5 source. There is no uncontrolled per-core user dispatch order.
- `p07_b3_next()` issues a single `PAGE_OUT` (dirty victim), `PAGE_IN`, `DISPATCH`, `BARRIER` or `FINAL_FLUSH` operation. Repeated `next()` calls return **the same pending operation** until `p07_b3_ack()`. Each planned op contains the full logical core, slot, victim ID (where relevant), tick/serial ordinal, CURRENT/NEXT event-bank parity, DDR base record address and P05 transfer size.
- `p07_b3_ack(..., success=1)` means the **eventual** actual PS/PL operation was fully acknowledged (never just a START register write). A dirty eviction must be acknowledged as `PAGE_OUT` before any new `PAGE_IN` into that slot. `DISPATCH` acknowledgment must eventually encompass authoritative HLS completion and committed B.2b packet routing; `BARRIER` acknowledgment must encompass B.2b NEXT-capacity checks, all logical cores serviced and quiescent routing/page traffic. **This native planner does not implement those acknowledgments; only the future physical adapter can.**
- A malformed ACK, `success != 1`, premature ACK or page-in/out/barrier/final-flush failure latches `first_failure_kind` and **permanently faults the run**. A dirty eviction failure does **not** clear its slot or overwrite its backing; a barrier failure does **not** advance tick/bank. There is no silent retry or reset-to-PASS. Once the 26th barrier has been ACKed, the planner demands three resident dirty `FINAL_FLUSH` acknowledgments before reporting DONE. No further dispatch follows DONE.
- Preserves the accepted P05 physically measured *per-transfer geometry only*: `0x6B000 = 438,272` bytes/full page-in and `0x1A000 = 106,496` bytes/mutable page-out, both multiples of 256B bursts. **These counters are derived/modelled, never real measured 27-core PL bytes**.

### Native regression

`tests/native/p07_b3a_pager_harness.c` performs real strict C11 operation iteration (including a repeated-plan/idempotence probe), prints every ordered action and a traffic summary, and injects forged ACK, failed initial page-in, failed dirty page-out, failed global barrier and failed LAST dirty flush. Every failure must latch and prohibit further scheduling.

`tests/test_p07_b3a_pager.py` compares **every C-issued action** against the independent accepted Python `ResidentLRU.visit` and `ResidentLRU.flush` for both scheduling policies. Thus it verifies every logical ID, tick, slot, victim, DDR record, byte amount, ordering and bank parity, not merely the totals.

| All 26 ticks and final flush | Ascending every tick | Alternating up/down |
| --- | ---: | ---: |
| Dispatches, barriers | 702, 26 | 702, 26 |
| Page-ins | 702 | 627 |
| Page hits | 0 | 75 |
| Dirty runtime page-outs | 699 | 624 |
| Final dirty outs | 3 | 3 |
| **Estimated** full+mutable PL page-engine bytes | **382,427,136** | **341,569,536** |

These values reproduce *B1.5 modeled page traffic*, not the **80-dispatch P05 historical measured bytes** or any current physical result.

## Pending work in P07-B.3

This is **B.3a scheduler planning only**. Before any physical KV260 inference: B.3b must connect accepted B.2a ingress and B.2b `P06B13R1` emissions/authoritative PL provenance to *actual per-core event banks*; implement a real page/bank ownership adapter with explicit dirty saves for routed NEXT content; prove exact first-error semantics on **physical** page failures and define cache clean/invalidate rules. B.3c must reconcile timing, readiness and event-bank swapping with the accepted P03 64-bit packet/descriptor register interface and provide verifiable host-native proofs of source-graph parity and no silent reset. Actual 27-core physical runs are P07-B.4, not B.3a.

**Important mismatch to resolve:** original `p03_runtime.c` uses a round-robin victim pointer and initial preloads, while `P06-B1.5` modeled LRU. This new scheduler **explicitly implements B1.5 LRU** and must NOT be claimed byte-identical to existing P03 runtime scheduling. Do not couple it to the original physical `p03_rt_execute` without an explicit callback/scheduler integration design and independent verification.

Neither this module nor its host tests performs MMIO, physical DDR access, actual P02 mutable saves, A53 cache operations, Vivado builds, or per-neuron computation. It does **not** guarantee that generic C pointer/ledger actions preserve the physical P02 neuron state; that is a remaining physical proof obligation. Before board tests, independently validate **ELF LOAD/BSS/heap/stack layout** and the exclusive 64 MiB DDR ownership reservation. Accepted original Track A/B files remain untouched.

## User native acceptance gate

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New B.3a independent C-to-original-B1.5 pager action/traffic oracle:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3a_pager.py

# Entire B.1/B.2 native dependency gates:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b2b_transaction.py \
  tests/test_p07_b2b_packets.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b1_owner_map.py \
  tests/test_p06_b15_paging.py \
  tests/test_p06_b13_streaming.py
```

Optional frozen B2.4 byte-level source integrity check, **read-only, not official TEST**:

```bash
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep
```

**Stop:** B.3a remains user-native **PENDING** until results are reported. Do not begin B.3b, merge PR #49, claim autonomous 27-core physical inference, or unseal B2 official MNIST TEST without the established user gates and required separate authorization.
