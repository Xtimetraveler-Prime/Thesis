# P07-B.3c2 + B.3c3 — Native Hardware-Adapter Closure Candidates

**State: implemented and committed; USER-NATIVE VERIFICATION PENDING.** This continues P07-B.3c1 (user-attested native PASS; see `P07_B3C1_USER_ACCEPTANCE_LEDGER.json`) on existing `agent/v3-p07-b-scaled-physical-inference`, draft PR #49. The official B2 MNIST TEST remains **SEALED**. Original accepted Track A/B/P03/P05 files have **not** been modified, the development branch is unmerged, and **no KV260 27-core physical inference, standalone A53 build, FPGA programming, or physical source-spike readback has been executed**.

## B.3c2 — LRU policy drives real P03 adapter functions

New `software/p07/include/p07_b3c2_hw_scheduler.h` and `software/p07/p07_b3c2_hw_scheduler.c`.

- Runs the **previously accepted B.3a LRU** 27-core/3-slot/26-barrier planner rather than linking the old P03 `p03_rt_execute` round-robin policy or inventing a fourth slot. The P03 original per-operation drivers `p03_hw_page`, `p03_hw_dispatch`, `p03_hw_quiescent`, `p03_hw_read_packet` are **called unchanged** and must return actual completion before B.3a `p07_b3_ack(..., success=1)` advances. `p03_hw_page` already implements P03 noncoherent DDR clean/invalidate, page command DONE/error, expected byte count and zero PAGE_PENDING verification, and cycle readback; the new driver does not replace these with fabricated acceptance.
- Page-in transfers the original physical **0x6B000** resident payload; dirty page-out and mandatory final flush use original **0x1A000** mutable-only PS/PL page protocol. Correct DDR physical owner addresses are inherited from B.3a and P03. A completed mock operation during native testing is **not** equivalent to an actual board completion.
- After each successful dispatch, reads all emitted hardware 64-bit packet words via the accepted P03 debug-bank read **before another dispatch can overwrite the packet bank**. Captures into explicitly caller-owned raw-word arena (≤8192 words globally/epoch) and temporary per-dispatch scratch (4096 words); each source core gets its own view even under alternating descending service order. Capture/read errors latch a sticky fault and stop further scheduling. The separately verified B.3c1 `p07_b3c_encode_frame` builds the canonical independent B1.3 packet frame from those captured source-bound views.
- The **barrier never ACKs itself**. `p07_b3c2_barrier_ack` requires a **success receipt from B.3c3 physical NEXT insertion**, matching tick, bank and captured packet count, checks the accepted P03 adapter is quiescent and every CURRENT counter is zero, then advances one global barrier. No unverified source event may be accepted merely because a START register was written. First failure is sticky. The original P03 runtime is not changed; the LRU integration is a new policy caller of the original adapter.

## B.3c3 — Full-epoch preflight, safe NEXT ownership, immutable provenance

New `software/p07/include/p07_b3c3_next_commit.h` and `software/p07/p07_b3c3_next_commit.c`.

- `p07_b3c3_prepare` validates the **entire** B1.3 packet epoch using the independently accepted original B.2b parser, *real independently verified source-spike list supplied by caller*, frozen compiled/audit identities supplied by trusted binding, complete source-to-target routes, canonical order and fanout, NEXT-only target timing, per-source/per-destination limits and the 26th drain tick rule. It checks actual P03 configured destination axon bitmaps, empty NEXT counters, zero remaining CURRENT counts, B.3a pending barrier, full three-slot resident state and physical P03 global quiescence. Invalid packet frames or unregistered destinations are rejected **before any NEXT words are written**.
- `p07_b3c3_commit` first checks the retained frame CRC, quiescence and destination capacity again. Then routes to exactly one NEXT owner: **resident context → original P03 debug bank 6 (event0) or 9 (event1)**; **nonresident context → P02 DDR record +0x54000/+0x58000 + 4×axon-index, P03 cache-clean callback and ordered PS barrier**. It **does not page in nonresident destinations just to deliver events**. Every successful resident insertion marks that physical slot dirty, including deliveries occurring after that slot's own dispatch. Per-core P03 NEXT occupancy advances only for successfully completed insertions. A completed receipt is produced only after every write and global quiescence has succeeded.
- **Critical physical semantic limitation:** Individual AXI/debug writes are not rollbackable. If an I/O operation fails after one or more successful writes, the entire image run becomes **sticky poisoned; the barrier may never ACK**. There is intentionally **no claim of all-or-nothing DDR rollback**. Later launch firmware must clear/reset all contexts, event counts and packets before any new image after such an abort. A failure does not become a successful inference merely because the first several packets were delivered.
- **Still blocking genuine scaled physical runtime:** complete physical per-image signed24 neuron state/current/refractory/output counts reset, all B.2a CURRENT ingress events physically inserted with independent hardware ownership, and actual HLS emitting-neuron provenance (not reconstructed from packet words); validated original frozen 27 trained P02 records including all **794,000 dense source connections/signed zeros**; linker/BSP address and stack/heap buffer map, firmware sticky first-error/result mailbox and image corpus parity. A valid host B1.3 frame is not proof of any of these.

## Actual P02 mutable-state page coverage and native fake-bus model

The source-of-truth original `docs/P02_1_DDR_ABI.md` defines a **512KiB P02 context record**. The actual P03 page geometry is unchanged: **full page-in 0x6B000** resident payload and **mutable page-out 0x1A000**. The five mutable regions contributing precisely 0x1A000 are:

| Original P02 DDR offset | Length | Mutable semantic |
|---|---:|---|
| `0x05000` | `0x02000` | all 1024 × 64-bit neuron state words (state/current/refractory packing) |
| `0x54000` | `0x04000` | CURRENT/NEXT event bank 0, 4096 × 32-bit axons |
| `0x58000` | `0x04000` | CURRENT/NEXT event bank 1, 4096 × 32-bit axons |
| `0x5C000` | `0x08000` | 1024 × 256-bit trace words |
| `0x64000` | `0x08000` | 4096 × 64-bit packet words |
| **Total** | **`0x1A000`** | all five mutable resident sections |

The new `tests/native/p07_b3c23_hw_scheduler_harness.c`, invoked by `tests/test_p07_b3c23_hw_integration.py`, compiles **the unchanged real P03 adapter source** together with the new B.3c2/3 modules, B.3a pager and accepted B2b/B3c1 validator. Synthetic `p03_hw_io` fake register/DDR callbacks exercise full 26-tick, **702-dispatch** scenarios under ascending and alternating LRU schedules, source packet-bank capture, route-to-resident and route-to-nonresident event slices, full-mutable mock writeback and full fake page-in. At the end, **every logical core has 26 simulated state mutations** and the last trace word and static config survive. Models original byte counts/traffic, but no AXI waveform, physical DDR cache, FPGA computation, or hardware numerics are measured.

Failure injection checks failed page-out, malformed B1.3 packet frame, missing B.3c3 commit receipt, CRC-valid packet targeting an unregistered destination axon, resident debug-write failure, and nonresident DDR-store failure. Each must fail closed without a false barrier or fabricated success receipt. The full mock is **not a byte-for-byte reproduction of the original RTL page engine itself**: it verifies the **P02 five-region mutable layout and accepted P03 C adapter contract under fake-bus acknowledgments**. A board-level readback and actual pl-to-ps coherence check remain mandatory.

## B.3c3 — ELF memory-owner admission (read-only, real ELF still required)

New `scripts/p07_b3c3_elf_admission.py` parses actual GNU `readelf -W -l` **LOAD physical memory spans** and requires separately declared physical stack/heap and caller-owned packet/scratch/capture/DMA buffer address spans. It rejects all overlaps with reserved `[0x40000000,0x44000000)` and P03 MMIO `[0xA4000000,0xA4001000)`, and overlapping owner spans. Negative tests are in `tests/test_p07_b3c3_elf_admission.py`.

This audit **cannot be run for the new A53 program until a real standalone ELF is linked**; it cannot derive unknown runtime allocations, verify that Linux is stopped, physically reserve DDR, check boot mode, verify the XSA, or measure PS FPD128. Do **not** claim those gates are closed by synthetic readelf-text tests. Before a board run, additionally inspect linker/map/BSP stack and memory selections and the live DDR/PS/PL state.

Example *future* command (substitute the **actual** observed physical stack/heap buffer addresses, never invent them):

```bash
python scripts/p07_b3c3_elf_admission.py --elf /path/to/actual_p07_b3.elf \
  --stack 0xSTACK_START:0xSTACK_END \
  --heap 0xHEAP_START:0xHEAP_END \
  --buffer ingress=0xACTUAL_START:0xACTUAL_END \
  --buffer packet_arena=0xACTUAL_START:0xACTUAL_END
```

## User verification on native development PC (NO BOARD and NO official TEST)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New B.3c2/3 native real-P03-C adapter + fake-bus/whole-mutable-region gate:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py

# Accepted predecessor and original P03/B1.5 regressions:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3c_packet_bridge.py \
  tests/test_p07_b3b_event_owner.py \
  tests/test_p07_b3a_pager.py \
  tests/test_p07_b2b_transaction.py \
  tests/test_p07_b2b_packets.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b1_owner_map.py \
  tests/test_p06_b15_paging.py \
  tests/test_p06_b13_streaming.py
```

**Acceptance gate:** B.3c2 and B.3c3 sources are committed **native verification candidates**. Do not call B.3c fully physical-accepted, merge PR #49, program the KV260, unseal B2 official MNIST TEST, or proceed to P07-B.4 without separate user review, native verification and physical preconditions.

## 2026-10-20 — Native compile/harness correction and independent CI evidence

The user's first B.3c2/3 pytest invocation had **11 passing tests and one failed test**. The failed test terminated at the C compile subprocess, whose stderr was hidden by \`capture_output=True\`. The Python test was corrected to show the full strict-C11 compiler stderr and the native executable stderr on failure; \`-Wall -Wextra -Werror -pedantic\` remains mandatory.

The added isolated native GitHub workflow \`.github/workflows/p07_b3c23_native.yml\` exposed the exact initial failure on GCC 13.3: **C11 -pedantic does not permit implicit conversion from \`uint16_t (*)[2]\` to \`const uint16_t (*)[2]\` before C23**. The synthetic harness now supplies an explicit read-only array-pointer view without modifying source-spike fixture data or relaxing the compiler flags.

Once compilation passed, CI found \`B3C23_FAIL_LINE=220\` during tick-0/source-0 readback. The fake P03 register bus incorrectly stopped at \`0x13F\`; the original P03 debug read-data registers extend through \`0x14C\`. The fake bus now admits the complete original **0x1000-byte P03 MMIO window** without modifying original P03 adapter code. A subsequent runtime signal identified another mock-layout fault: the harness had used **0x6B000** (the PAGE_IN payload length) as the physical DDR record stride. The accepted P02 stride is **0x80000**. The mock now allocates separate 0x80000 records and copies only the original payload **[0x1000, 0x6C000)** for each accepted 0x6B000 full page-in; 0x1A000 mutable-region page-outs are unchanged.

**Independent verified CI evidence:** commit \`056477bfbeae83b5e2552d2e571c3531a5a01355\` GitHub Actions run [#39446734817](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/39446734817) returned **success**. The exact real P03 C adapter + new scheduler/commit + native 27-core fake-bus harness compiled using \`cc -std=c11 -Wall -Wextra -Werror -pedantic -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer\` and ran with leak and undefined-behavior sanitizers enabled. Terminal proof:

\`\`\`text
P07_B3C23_REAL_P03_NATIVE_FAKE_BUS_PASS=1
\`\`\`

The workflow is branch-/PR-scoped and additive, with \`contents: read\` permissions. It is **host fake-bus CI**, not a physical KV260 test, genuine trained-model inference or A53 executable build. The newly corrected user-local pytest suite has **not yet received an independent user rerun attestation**. Original accepted Track A/B files remain unchanged and B2 official MNIST TEST remains SEALED.

To verify on the development PC:

\`\`\`bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py
\`\`\`

**Acceptance state:** CI PASS, user-native B.3c2/3 PASS still pending. PR #49 stays draft and unmerged.
