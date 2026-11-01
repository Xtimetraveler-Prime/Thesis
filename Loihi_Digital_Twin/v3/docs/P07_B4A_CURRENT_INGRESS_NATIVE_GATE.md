# P07-B.4a — P03 Physical CURRENT Ingress Admission (Native Candidate)

**State:** portable C11 adapter and host fake-bus verification **CI-PASS, USER-NATIVE PENDING**. This begins the roadmap's P07-B.4 preparation, and does **not** authorize or claim a scaled KV260 run. P07-B.3c2/B.3c3 were **user-attested native PASS** on 2026-10-20; the additive evidence is `docs/P07_B3C23_USER_ACCEPTANCE_LEDGER.json`. PR #49 remains draft and unmerged. The B2 official MNIST TEST is **SEALED**. Accepted Track A/B artifacts, original P03 adapter and original P05 firmware were not modified.

## Problem and scope

Accepted B.3c2 drives three-slot LRU page/dispatch and captures packet-bank entries. B.3c3 validates/writes their NEXT events. Yet **no prior P07-B C component inserted the 784-channel B1.3 external spike input into the original P03 physical CURRENT banks**. Executing only the routing half would not be a valid MNIST inference.

The new `software/p07/include/p07_b4a_current_ingress.h` and `software/p07/p07_b4a_current_ingress.c` add this pre-dispatch adapter, incorporating any NEXT events delivered in the previous epoch. The input is the real **original `P06B13I1` frame**, not a fabricated legacy P05 one-axon diagnostic message.

### Exact authority and ordering

- The original unchanged B.2a `p07_b2_decode_ingress` revalidates the **whole** 128-byte ingress header, compiler/audit SHA, payload CRC, ordered source pixel/core/axon map and 784 original pixel bytes against a separately trusted immutable route table.
- At the start of tick `t` (before B.3a dispatch, only when cursor=0 and no pending operation), the authority for CURRENT is the **previous epoch's routed NEXT** in P03 bank `t & 1`. This source is located by the accepted B.3a `pager->resident[slot]`: if resident, read the original P03 debug event bank **6/9**; if nonresident, invalidate the appropriate original P02 DDR event span and read by a **separate, explicitly caller-supplied verified coherent `read_ddr32` callback**. The accepted original `p03_hw_io` has only a DDR *store*, so the new code does not pretend it has an already established PS read interface. A real Xilinx callback and memory-map admission are still needed.
- Compute the exact accepted `uint8-quota-phase17` external spike events for each of **25 active ticks + one external-free drain tick**. Combine previous routed axons and new external axons; sort every destination's combined CURRENT event list by **destination axon**, including repeated axons (fan-in multiplicity preserved). Enforce **4,096 maximum events per core including both sources**, source routing/registered destination-axon bitsets and all-core bank count invariants. Recompute all 27 cores before writing a single CURRENT event.
- `p07_b4a_prepare` is a two-source (previous NEXT plus current external) all-core preflight: uses a **caller-owned disjoint 27×4096 × 32-bit scratch array (442,368 bytes)**, records exact external/prior/combined counts and CRCs. On rejection it performs **no DDR or URAM event insertion** and leaves the B.3a pager and `hw->event_counts` unchanged (a failed original P03 debug read may still set the adapter's sticky error, as intended). Reading nonresident source contexts itself requires proper physical cache ownership.
- `p07_b4a_commit` checks unchanged epoch/pager state, wire CRC and staging CRC, then writes the sorted merged CURRENT event arrays. **Resident** destinations use original P03 `p03_hw_debug_word` at bank 6/9 and mark the slot dirty. **Nonresident** destinations receive direct indexed P02 DDR stores at `0x40000000 + core*0x80000 + (bank?0x58000:0x54000) + 4*event_index` followed by the original PS cache-clean and barrier callbacks. It **does not page in a nonresident destination solely to deliver input**. P03 per-core CURRENT counts are published after that core's complete writes; an independent receipt is published **only after every core has completed and P03 reports quiescent**.
- Physical writes are **not rollbackable**. Any post-preflight error permanently poisons B.3a and aborts that image; the caller must do a separately verified full physical image-state reset before another attempt. This is **preflight-before-write**, not all-or-nothing physical rollback. No unchecked nonresident read pointer or cache policy is silently assumed.

### CI and independent synthetic tests

`tests/native/p07_b4a_current_ingress_harness.c` (invoked by `tests/test_p07_b4a_current_ingress.py`) links **original P03 adapter** + B.2a ingress decoder + B.3a pager + new B.4a code with a fake 4KiB MMIO bus and a separate fake 27×0x80000 physical DDR store. Synthetic input is all-255 pixels, 784 pixel channels, two source destinations (core 0 and core 1) and registered axons; other 25 logical cores are empty.

The native gate checks:
1. Original B1.3-verified external input (1568 total routed external events) to two nonresident cores; full 784-axon original order; correct P03 DDR address stride and core counts; duplicate commit rejection.
2. A resident core's previous NEXT events are read from its authoritative slot rather than stale DDR, merged with current external events, sorted with multiplicity, returned to P03 event bank 6 and marked dirty; nonresident external fanout is still delivered to DDR.
3. Corrupted compiled SHA rejects the entire input before writing; 3313 prior + 784 external = **4097 rejected**, while 3312 + 784 = **4096 admitted**.
4. A forced failure after exactly three nonresident PS writes keeps the result receipt unpublished and the B.3a run irreversibly poisoned rather than marking the image complete.

**Verified independent GitHub Actions CI:** [run #39452217288](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/39452217288) completed **SUCCESS** (strict `-std=c11 -Wall -Wextra -Werror -pedantic`, AddressSanitizer + UndefinedBehaviorSanitizer); produced `P07_B4A_CURRENT_INGRESS_P03_FAKE_BUS_PASS=1`. The original B.3c2/B.3c3 CI simultaneously remained green. This is **native host fake-bus evidence**, not a KV260 board measurement.

### Remaining P07-B.4 NO-GO items

No complete physical launch can be claimed from this module alone. Still outstanding:

- A genuinely linked and audited **standalone A53 ELF** with Xilinx `p03_hw_xilinx_io`, P03 live FPD128/shell identity, memory ownership; actual PS DDR-read callback and coherent cache policy; P02 27 frozen records loaded through a separately authorized initialization procedure. The 442,368-byte B.4a scratch, 98,432-byte B.3c frame buffers, capture arena, stack/heap, linker LOAD/BSS, P05 staging, descriptor and result regions must be disjoint.
- A verified per-image physical neuron reset: all **signed24 state/current/voltage/refractory**, 27×2 event banks, 27 output/readout counters, trace and packet banks, the complete full P02 dynamic state and 26-tick completion. Merely reinitializing a C planner is not physical reset.
- **Actual independent HLS emitting-neuron evidence:** the original P03 64-bit packet contains a source compartment, but no independent list of all source neurons that spiked; the host B.2b/B.3c completeness validator requires that list. Until an authoritative physical source-spike trace is read and validated, do not fabricate a source list from packet words or claim full trained-network fanout parity. The source graph must retain all original **794,000 signed connections including explicit zeros**.
- Hardware back-to-back 2–5-core diagnostic probe first, then trained frozen 27-core P02 snapshot, complete 26-epoch numerical first-divergence comparison against the original independent source oracle, bounded full-255 capacity checks, physical AXI paging counters and first-error result mailbox. The **B2 official MNIST TEST stays sealed**, and P07-B.5 TRAIN-derived validation must be separate.

## User terminal commands — stop after B.4a

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New P07-B.4a real P03 adapter / CURRENT ingress native gate:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4a_current_ingress.py

# Original accepted B.3c2/3 and B.2a ingress regressions:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py \
  tests/test_p07_b3c_packet_bridge.py \
  tests/test_p07_b3b_event_owner.py \
  tests/test_p07_b3a_pager.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b2b_transaction.py \
  tests/test_p07_b2b_packets.py
```

**Stop:** B.4a native user PASS pending. Do not merge PR #49, unseal B2 official MNIST TEST or begin KV260 FPGA programming on the basis of fake-bus tests.
