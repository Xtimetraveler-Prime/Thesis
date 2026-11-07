# P07-B.1 — Scaled KV260 owner map and feasibility contract (candidate)

**Status:** branch candidate, awaiting native user verification; **not hardware acceptance**. Based on merged `main` at `a540b68eeab0f2c4ef37d9f1680e1619deb7c98d`. Version: `p07-b1-owner-map-v1`.

## Physical facts vs proposed allocation

Accepted P02/P03/P05 facts: K26 DDR backing is `0x40000000..0x43FFFFFF` (64 MiB); each source-preserving logical core has one `0x80000` (524288-byte) record. The accepted P03.2c MMIO region is `0xA4000000..0xA4000FFF`, ID `0x4C543302`, capability word `0x0001031F`. A standalone A53 (not Linux) operates one PL HLS engine with three physical resident URAM context slots via 128-bit FPD PS master/SmartConnect to 32-bit AXI-Lite; PL P02 page engine transfers over HP0. Original P03 standalone application is **hard-coded for five logical cores, a single registered input axon per core, and a separate diagnostic result ABI**; no new 27-core firmware is implied by P03 runtime array capacity.

P07-B new **candidate allocation**: logical cores 0–25 hidden partitions, 26 readout. DDR addresses are `0x40000000 + core_id*0x80000`. First record starts `0x40000000`; last record starts `0x40D00000`; exclusive end `0x40D80000` = **14,155,776 bytes** / 27 x 512 KiB. Remaining reserved backing window `0x40D80000..0x43FDFFFF` must not be blindly repurposed: existing P03 uses run config at `0x43FE0000` and mailbox at `0x43FF0000`. The **new** P07-B frame buffers, packet/staging buffers, trace/journal, ELF/stack/heap/linker memory and DMA buffers have **no accepted final location or no-overlap proof**; they are blockers, not silently assigned addresses. Preserve `0x43FE0000`/`0x43FF0000` until a versioned A53 launcher replaces them and exact linker memory map is audited. User-local B2 frozen P02 contexts are immutable **initial provisioning input**, not a runtime writeback target; firmware operates on distinct runtime DDR records.

Each logical core is bounded by 1024 compartments, 4096 axons, 4096 routes, 32768 P03 synapse words, 4096 CURRENT events and 4096 emitted/NEXT packet slots. Exact 794,000 original signed dense connections, including explicit zero weights, remain source semantics even if packed templates share equivalent words. Resource admission must reject oversubscription **before page commands**, with no partial descriptor or event-bank ownership changes. Resident slot owners, cache dirty bits, physically backed per-core CURRENT/NEXT banks, epoch/run ID, and mutable last-writeback must be tracked in the new firmware, not inferred from the host B1.5 simulation.

## B1.3 stream boundary (implementation begins P07-B.2)

Existing **host-only** ingress bytes: 128-byte header; `P06B13I1` magic; little-endian 14 x uint32 (version 1, lengths, dimensions, CRCs, reserved); 32-byte compiled-deployment SHA; 32-byte B1.1 audit SHA; payload = sorted 6-byte `<HHH` source-pixel/core/axon routes + 784 raw bytes. Header CRC32 with its CRC word zeroed, independent payload CRC32. Proposed maximum ingress envelope is **593,696 bytes** (784 x 126 routes), NOT the actual frozen 27-core frame size; real frame buffer provisioning needs bounded route count and per-core capacity proof. A complete parser must compare the **ordered** route vector to the signed compiled mapping rather than merely checking a CRC; duplicate/order deviations and wrong deployment/audit identities must fail before mutating runtime state. Existing `P06B13R1` packet ABI is also host-only. Exact subsequent packet transport/ownership, CRC, failure atomicity, and round-trip native C versus Python oracles are **B.2**, not claimed here.

Input contract: 784 unsigned bytes, `p06-uint8-quota-phase17-v1`, 25 input ticks + 1 external-free drain = 26, signed24 saturating LIF, strict > threshold, next-tick hidden-to-readout routing, first-index argmax. Readout accumulates ten counts; per-image state/current/next/packet/bank reset required.

## Paging, counter and safety boundary

Page engine accepted physical transfer constants: page-in `0x6B000` = 438272 B = **1712 x 256 B**; dirty mutable page-out `0x1A000` = 106496 B = **416 x 256 B**. P05 final 80/80 accounting matches 136960 reads + 33280 writes = 43581440 measured PL page-engine bytes **in that original P05 test only**. New B.1 helper provides a **model calculation**, never new board measurements. A worst-order 27 x 26 = 702 logical dispatches (all cores including zero-spike cores), one engine, global barriers each tick. B1.5 paging estimates do not imply physical P07-B measurements.

Initial firmware abort classes, to preserve as sticky first fault and never auto-resume: invalid manifest/version/identities/CRC; range/alignment/linker-memory overlap; malformed route/destination/packet; per-bank/event/synapse resource overflow; stale epoch/wrong CURRENT-vs-NEXT ownership; page/AXI/MMIO error or timeout; unflushed dirty eviction; incomplete global barrier; post-failure attempt to dispatch; numerical trace divergence. Final numeric status assignments are reserved for a later versioned firmware ABI; do not reuse legacy P03/P07-A numeric codes without explicit compatibility design. No DMA, PL page read, route delivery, inference dispatch or official TEST access is allowed on failed preflight.

## Next gates and required independent evidence

**B.1 native acceptance:** `tests/test_p07_b1_admission.py` and full inherited regressions; source-constant drift detection and negative no-side-effect *planning* admissions. The planning test **does not establish board-side rollback**. Confirm physical BSPlinker section placement, standalone heap/stack, physical memory access and available build workspace before choosing staging-buffer addresses. 
**B.2:** native C parser for `P06B13I1/P06B13R1`, independent Python serialization/differential and CRC/epoch/fanout/overflow/atomicity tests.
**B.3:** deterministic three-slot 27-core paging and barrier state with byte-exact P02 mutable pages, one-tick NEXT bank routing and complete 27 x 26 dispatch trace; independently compare source oracle.
**B.4:** bounded synthetic KV260 bring-up, negative faults and training-derived frame parity. Old bitstream/ELF remain accepted baseline, not new test results.
**B.5:** predeclared TRAIN-derived physical validation before any official TEST unseal.
**B.6:** physical acceptance, independently measured page-engine counters, timing scopes, P08-B handoff.

**GO:** host planning/test work only. **NO-GO:** scaled hardware deployment/inference, official B2 MNIST TEST, new physical page/latency/power claims. Never mutate Track A, B2.4 freeze/33 assets, accepted P05 artifacts or original official TEST protocol.
