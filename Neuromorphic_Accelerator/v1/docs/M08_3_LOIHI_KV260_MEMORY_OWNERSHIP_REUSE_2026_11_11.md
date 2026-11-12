# M08.3 — Reuse the accepted Loihi v2 KV260 host-paging ownership boundary

**Reviewed November 11, 2026.** This is an evidence crosswalk grounded in accepted Loihi v2 repository sources, not a new hardware claim. Loihi v2 remains unchanged; its HLS arithmetic and state format do not automatically implement M08 signed16 semantics.

## Confirmed achievements and reusable components

| Proven system | Original source/evidence | What to reuse for M08 |
| --- | --- | --- |
| Routed K26 host-paged shell | Loihi_Digital_Twin/v2/docs/P08_4_3A_ACCEPTANCE.md. Five logical backing contexts, three resident full-context memory slots, one P03 HLS engine; timing WNS +0.734 ns and WHS +0.010 ns, 47 URAM. | Proven board preset, reset, memory-bank arrangement, and host/compute arbitration strategy. These are **Loihi-specific measurements**. |
| Host-owned backing and barrier | Loihi_Digital_Twin/v2/docs/P08_CONTEXT_PAGING.md section 5 and docs/P08_4_3A_HOST_PAGED_K26_SHELL.md. Host selects page victim; saves state/event-bank contents; loads new logical image; owns cross-page packet routing, next-events, and global timestep barrier. | Prioritize one-at-a-time host-paged M08 signed16 conformance, without first inventing a new physical page allocator. |
| Exclusive host and engine access | Loihi_Digital_Twin/v2/rtl/p03_memory_host_bridge.v implements a host-busy interlock and rejects transactions while compute is busy; rtl/p08_paged_dispatch_controller.v admits dispatch only when host is idle and valid metadata is loaded. | Reuse this *control protocol* with M08-specific pins and state width, not raw Loihi signed24 RTL. |
| Actual hardware page replacement | Loihi_Digital_Twin/v2/docs/P08_4_3B_ACCEPTANCE.md and hardware/p08_4_3b_physical_conformance.tcl. Frozen representative logical core 4 is loaded into physical slot 0 after a decoy-marker readback; dispatch and 618 compartment/trace checks match. | Reuse decoy → overwrite/readback → dispatch → state/trace verification pattern for M08 signed16; physical Loihi proof does not establish M08 equality. |
| M08 signed16 numerical and fault behavior | Neuromorphic_Accelerator/v1/docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md: signed16 HLS, AMD SmartConnect and explicit poison/output quarantine/reset and full-rewrite controls with an **offline simulated 64 KiB memory image**. | Preserve the already accepted M06 signed16 model/RTL safety and B-before-AR ordering when integrating later hardware. |

## What “memory ownership” means here

**Proven (Loihi):** operator-controlled VIO/JTAG host *debug-bank memory access*, decoy/real page replacement and actual routed K26 compute with the host and compute engine mutually excluded. Host software holds backing context snapshots. The accepted P08.4.3b physical run tests a *representative single dispatch*, not full 100-timestep JTAG execution.

**Proven (M06):** a software canonical-page lease and original HLS/AMD offline AXI transaction model, fault containment, and independently checked neural results. The DDR-like external state is still simulated, not a verified physical Linux buffer.

**Not yet proven for M08:** bound kernel driver for a newly connected M08 PL master, DMA API or DMA-BUF allocation/attachment and mapping, DMA mask, coherent/streaming synchronization, IOMMU/address translation where applicable, and safe quiesce/reset before buffer release. The presence of a Linux DMA heap or a platform device is not kernel-owned memory proof.

**Decision:** Loihi host staging is a valid earlier physical M08 experimental path *without Linux DDR access*. Do not make a brand-new Linux DMA stack a prerequisite for a first M08 signed16 host-staged real PL proof. Keep physical-DDR and DMA ownership as a separate required gate for performance experiments that actually use DDR.

## Concrete source-only reuse implemented

M08.3.2 now includes a host-paging control model in src/neuromorphic_accelerator_v1/m08_host_page_ownership.py and negative/positive tests in tests/test_m08_host_page_ownership.py.

- Explicit one-software-host lease, idle-only host access and computed dispatch mutually exclusive; logical IDs are independent of resident slot IDs.
- Stage a backing image into a slot; the model requires an asserted host-readback SHA-256 before dispatch.
- Model compute completion with correctly sized updated image and an explicit packet-drained assertion; uncertain/incomplete result poisons the session.
- Save dirty updated state to host backing *before* page eviction. Mismatched asserted readback poisons without canonically committing; no silent stale-state reuse.
- Global barrier cannot advance until every logical context completed and all dirty states were saved. A newly poisoned model cannot be reset or marked ready in-place.
- A 3-logical/2-resident simulated page replacement and negative race/error cases test the protocol.

**Limits:** software-only buffer contents and readback assertions, not a real VIO transaction, OS memory allocation, HLS signed16 dispatch, packet interpretation, event-bank flip, readback attestation, physical PS DDR or K26 timing. All receipts say kernel_dma_buffer_owned=false, physical_dma_ready=false and hardware_dispatch_measured=false.

## Ordered next hardware work

1. Read-only owner board-local M08.3.1 kernel/platform inventory using docs/M08_3_DMA_READINESS_RUNBOOK.md. This confirms actual OS/driver context, not buffer ownership.
2. Review Loihi's accepted VIO memory-port arbitration and the original M06 signed16 G4, design an **M08-specific** host-staged physical conformance shell with verified clock/reset, bounded resident-page size, byte-lane/endianness and conflict-free host/compute handoff. Do not copy the Loihi .bit file or signed24 layout.
3. Perform genuine routed K26 full-system integration (M08.2b) and separately pinned M08 signed16 bitstream/host probe evidence; only then stage safe single-page physical conformance. Source model does not satisfy this.
4. Introduce kernel-bound DMA ownership for a real new M08 PL master only when connected, independently verified and needed. Host-staged JTAG and Linux kernel-owned DDR are distinct latency/performance boundaries.
5. Match numerical precision, workload, memory placement and timing boundary before making FPGA speedup or power claims.

**Related:** docs/M08_2_IDENTITY_BD_SCOPED_ACCEPTANCE_2026_11_11.md, docs/M08_PHASED_HARDWARE_PLAN.md, and accepted Loihi v2 P08.4.3a/b original records. Preserve both projects' accepted evidence and never overwrite the seven existing M08.2 owner folders.
