# Neuromorphic Accelerator v1 — authoritative research roadmap

**Updated:** 2026-11-20 | **Current milestone:** **M08.4 — physical signed16 neural-state virtualization (OPEN)** | **Next:** M08.5 | **M09:** PLANNED.

> **Read this current roadmap first.** The former 171 KB dated run-by-run status journal has been preserved **verbatim** (apart from an archive heading) at [the full historical roadmap](docs/archive/M08_ROADMAP_CHRONICLE_THROUGH_2026_11_20.md). Its historical `OPEN`, `NOT PROGRAMMED`, and `PENDING` statements describe past observations and **do not override** current accepted evidence. No historical source, original Vivado report, bitstream, or owner evidence was changed by the roadmap cleanup.

## Research question and test boundaries

**Primary question:** Under identical neuromorphic numerical semantics, synapses, event workload, and physical measurement boundaries, how does virtualizing neural state beyond FPGA on-chip residency interact with sparse event-driven execution? Can fewer active updates compensate for page-transfer and synchronization costs, and under what locality regimes?

Use **independent M02 dense/event and M03 sparse numerical references** for correctness; preserve signed16 M06 behavior (including 3/4 truncate-toward-zero leak, spike threshold/reset, five positive-delay recurrent edges, 17 original external events). Separate host staging, on-chip state, genuine PS/PL DDR, and physical performance; **a PC model, simulator, JTAG register readback, and DDR transfer are not interchangeable**.

## Milestone status (keep milestones broad)

| Milestone | Acceptance scope | Status |
| --- | --- | --- |
| **M01–M03** — residency alternatives, neural oracle, workload/traffic controls | Analytical/model and independent exact reference foundations | **COMPLETE (PC)** |
| **M04–M06** — arithmetic/HLS, on-chip event engine, canonical virtual residency | Original bounded HLS/AMD RTL simulations, independent M02/M03 neural and original SHA evidence, G4 fault quarantine. **Not physical DDR** | **COMPLETE (offline)** |
| **M07** — caching/scheduling, policy and matched ablations | Four-way PC controls, locality and bounded service-model ablations, negative cases | **COMPLETE (PC)** |
| **M08** — physical KV260 system and controlled measurements | K26 synthesis, physical neural execution, authentic page virtualization, memory/strategy comparisons and repeatable measured performance | **OPEN — currently M08.4** |
| **M09** — analysis and thesis closeout | Reproducible plots, confidence/limits, negative results, prior-art and thesis writing | **PLANNED** |

**One research milestone (M08), three remaining acceptance gates.** We are deliberately **not** creating a new gate for each bug, protocol counter, RTL smoke, SHA report, page transfer, or Vivado warning. Keep work/test/evidence labels descriptive **inside** a gate. A subdivision is warranted only if a genuinely distinct failure/risk boundary prevents safe debugging or reproducible acceptance; document the necessity and the parent gate, and do not create an independently “complete” milestone simply for source progress. The [next-instance handoff](docs/M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md) repeats this requirement.

## Completed M08 physical foundations (accepted, do not rerun)

The owner performed **one original** KV260 JTAG experiment for the accepted M08 D3.D.2E queued 32-neuron network, then repaired a **software receipt newline-matching bug** and independently re-audited the *same immutable original* hardware capture. This is the current **bounded physical neural/event baseline**, not paged neural execution:

| Original physical requirement | Accepted owner evidence |
| --- | --- |
| Genuine Vivado 2025.2 K26 bit | SHA256 `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`; exact native K26 routed/DRC/timing acceptance; WNS +1.844 ns, WHS +0.010 ns |
| First original physical experiment | `~/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN`, with **6/6 original hardware SHA receipts OK**; first native `m08_d3d2e_queue_GFz0SbiC` |
| Actual event scheduling | **17 signed input events accepted and serviced** by a fabric 32-entry FIFO; **128 live buckets zero before service**; four ordered synchronous tick barriers **5/5/4/3** |
| Exact numerical neural parity | **128 fabric input currents, 128 voltages, 128 spike decisions, 128 recurrent currents = 512/512**, 32 neurons ×4 ticks, five recurrent edges |
| Independent audit | `M08_D3D2E_PHYSICAL_M06_17_QUEUED_EVENT_128_BUCKET_384_NEURAL_ACCEPTED` |

[Full first-owner physical acceptance record](docs/M08_D3D2E_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md). D3.D.2A–E are accepted **historical experiment identifiers**, not active or future milestone divisions. The original image has **not been reprogrammed** after acceptance. This establishes clocked FPGA computation with PS-provided PL clock, **not** independent asynchronous clocking, streaming/DMA, physical DDR, original M06 HLS paging, energy or measured throughput.

Earlier owner-confirmed M08 results also include read-only inventory, safe PS/PL identity and page BD/route, conservative JTAG physical experiments (four-neuron, recurrent routing, raw event ingress) and accepted Loihi-v2 KV260 host-paging precedent. These original files and all failures remain immutable; see [archived chronological evidence](docs/archive/M08_ROADMAP_CHRONICLE_THROUGH_2026_11_20.md), [M08 phase history](docs/M08_PHASED_HARDWARE_PLAN.md), and [first-party Loihi memory-ownership crosswalk](docs/M08_3_LOIHI_KV260_MEMORY_OWNERSHIP_REUSE_2026_11_11.md).

## Remaining M08 acceptance gates (no further milestone sprawl)

### **M08.4 — physically virtualized signed16 neural execution (ACTIVE)**

**Goal:** More logical neuron-state pages than truly resident FPGA pages (**N>K**), with real compute-bearing M06 signed16 neurons, verified load/execute/save/evict/reload, and independent **32×4/17-event/five-edge, 512-value** M02/M03 parity.

**Engineering work within this one gate:** compute-facing signed16 state/page ABI **without prefilled golden outputs**; real AXI/host–compute port arbitration, bounded fault quarantine and epoch/tick ordering; actual LIF membrane decay/threshold/reset and recurrent event delivery across pages; real RTL simulator tests, mutation negatives and independent neural fixtures; **new** K26 Vivado 2025.2 project, timing/DRC/source/bitstream SHA-pinned first-original review; cooling/UART/JTAG/recovery preflight; **new** one-shot physical page-replacement/compute test with independent receipt and full numerical comparison. Do not reuse the accepted D3.D.2E bitstream as approval for a new image.

**M08.4 FIRST PHYSICAL RUN HARDWARE PASS, FINAL INDEPENDENT AUDIT PENDING (2026-11-20):** The exact first post-fix owner K26 native original `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW` has 15/15 preserved SHA receipt files, 7,797,842-byte bit SHA256 `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494`, new-image-specific 7 vendor debug/JTAG warning review, routed WNS **+0.763 ns**, WHS **+0.010 ns**, and nominal PS PL0 **100 MHz**. Five `LUTAR-1` async-reset methodology warnings remain untraced, disclosed and accepted as bounded first-JTAG-test risk by owner.

The **first actual owner KV260 JTAG physical run** on 2026-11-20 **18:40:35–18:41:37 America/Denver**, immutable original folder `~/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ`, successfully programmed exactly one new K26 image, proved JTAG AXI BRAM `55AA22DD`, identified the real paged-neural register ABI, configured five recurrent edges, and completed **24 actual 256-byte page LOAD/COMMIT/compute/DIRTY readback/SAVE cycles, six logical pages × four ordered tick barriers** through **one resident state bank**. First original Tcl printed `M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS`, comprising **128 HOST-coalesced input currents + 128 PL membrane + 128 PL spikes + 128 PL recurrent currents =512 exact M02/M03 comparisons**, and the owner console verified **13/13 original physical SHA receipt files OK**. Physical paging is **on-chip RAM with JTAG host backing**, not actual DDR/DMA, not independent async event service and not reimplementation of the older raw-event FIFO. The independent Python original receipt audit then falsely rejected `M08_4_NEW_IMAGE_PROGRAM_ONCE_START` because it counted both Vivado's echoed Tcl comment and the actual runtime marker; **no second hardware run should occur**. The independent auditor now matches **whole standalone log lines and exact marker order**, with six synthetic full-receipt/adversarial regression tests; source CI passed **548 M08 tests** ([run 44851903415](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44851903415)). **M08.4 formal physical acceptance remains OPEN until the owner reruns that fixed auditor READ-ONLY on the unchanged original `zhUx7lLJ` 13 files and returns exit 0.** [First-original physical evidence and exact read-only command](docs/M08_4_FIRST_OWNER_PAGED_NEURAL_PHYSICAL_2026_11_20.md).

**Gate remains OPEN pending just the original read-only receipt re-audit:** first actual owner paged neural hardware has completed 24/24 pages with 512/512 console comparisons and 13/13 original SHA rows, but a successful independent fixed original auditor result is still required before closing M08.4 or activating M08.5.

### **M08.5 — matched real memory and execution experiments (PLANNED)**

At matched signed16 neural semantics, network, event order, N/K, and measurement boundary, compare timestep/on-chip vs event/on-chip and genuinely memory-backed strategies **where physically feasible**. Include page locality, real transfer counts, stalls and source-matched correctness. Real DDR/DMA requires a verified live PS/PL owner, kernel-bound device/driver or equally verified PS-managed path, address-width/mask, IOMMU/cache coherency, kernel buffer lifetime and quiesce/recovery; never infer those from a device node, `/dev/mem`, or a simulated DDR array. Label JTAG-host-staged memory separately from DDR. Preserve honest negative/unavailable comparisons rather than fabricate matched points. [Consolidated execution plan](docs/M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md).

### **M08.6–M08.7 — measured reproducibility, owner review and M09 handoff (PLANNED, ONE GATE)**

Repeated original SHA-pinned raw timing and device captures, neural parity on every plotted point, real routed LUT/FF/BRAM/URAM/DSP, achieved timing and clock, PS control versus PL work, actual page bytes and queue stalls, host-end-to-end and measured uncertainty. Power/energy only with a defensible meter. Explicit owner acceptance of any narrowed scope and preserved negative evidence. **M09 starts only after this gate**.

## Working method and handoff contract

- **Keep PRs #93/#94 draft/unmerged** until explicit owner merge authorization; continue M08.4 within the existing `agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership` branch and [draft PR #94](https://github.com/Xtimetraveler-Prime/Thesis/pull/94), not a new PR per task. Prefer complete coherent increments: code, real functional tests and adversarial failures, documentation, then owner local verification commands.
- **No new subdivided milestones** except when absolutely necessary to isolate a different physical/software failure boundary for debugging; any such temporary experiment remains part of M08.4 or M08.5. Update one authoritative status paragraph instead of endlessly prepending newer “current status” banners.
- **Physical release is independent of software CI.** Original owner evidence under `~/Thesis_Evidence/M08/` stays untouched and is never overwritten/rehashed. A new hardware image needs its own exact-native source/DRC/timing/bit SHA and operator preflight, one-shot JTAG test, and read-only independent owner audit; no automatic retries and no PS DDR writes without ownership proof.
- Maintain a **single next-chat handoff** at [M08 next-instance handoff](docs/M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md), containing current branch/PR, accepted evidence, next code step, command lines and an **explicit no-sprawl instruction**. Keep the old dated histories in the archive, not inline in this overview.

## Prior work, thesis claims and limitations

Do not claim novelty for time-multiplexing, caching, sparse event pipelines, off-chip synapses or deferred leak as general mechanisms; recognize SENECA, YANA and HiAER-Spike and review each upstream license independently. The claimed **research contribution to test** is a controlled quantification of sparse execution × neural-state virtualization under a specific KV260 physical resource/latency boundary—not “the first neuromorphic FPGA” or a Loihi silicon-equivalent implementation. [Expanded literature](../../LitReview.md).

**Current accepted bottom line:** physically accepted prior clocked FIFO-service 32-neuron/4-tick M06 run; **new first paged signed16 neural physical JTAG hardware PASS** with 24 page saves and 512 comparisons, **final independent original evidence read-only audit pending**. **Open:** independent M08.4 acceptance, safe genuine DDR, matched physical controls, measured performance and energy. **Next:** original read-only M08.4 re-audit and acceptance, **then** activate M08.5, **then** M08.6–7 and M09.
