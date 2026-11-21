# Neuromorphic Accelerator v1 — authoritative research roadmap

**Updated:** 2026-11-20 | **Current milestone:** **M08.5 — matched real memory and execution experiments (ACTIVE)** | **M08.4:** PHYSICALLY ACCEPTED | **Next:** combined M08.6–M08.7 | **M09:** PLANNED.

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
| **M08** — physical KV260 system and controlled measurements | K26 synthesis, physical neural execution, authentic page virtualization, memory/strategy comparisons and repeatable measured performance | **OPEN — M08.4 ACCEPTED; M08.5 ACTIVE** |
| **M09** — analysis and thesis closeout | Reproducible plots, confidence/limits, negative results, prior-art and thesis writing | **PLANNED** |

**One research milestone (M08), TWO remaining acceptance gates after M08.4 acceptance: M08.5 and combined M08.6–M08.7.** We are deliberately **not** creating a new gate for each bug, protocol counter, RTL smoke, SHA report, page transfer, or Vivado warning. Keep work/test/evidence labels descriptive **inside** a gate. A subdivision is warranted only if a genuinely distinct failure/risk boundary prevents safe debugging or reproducible acceptance; document the necessity and the parent gate, and do not create an independently “complete” milestone simply for source progress. The [next-instance handoff](docs/M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md) repeats this requirement.

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

### **M08.4 — physically virtualized signed16 neural execution (PHYSICALLY ACCEPTED, CLOSED)**

**Goal:** More logical neuron-state pages than truly resident FPGA pages (**N>K**), with real compute-bearing M06 signed16 neurons, verified load/execute/save/evict/reload, and independent **32×4/17-event/five-edge, 512-value** M02/M03 parity.

**Completed engineering scope of this gate:** compute-facing signed16 state/page ABI **without prefilled golden outputs**; real AXI/host–compute port arbitration, bounded fault quarantine and epoch/tick ordering; actual LIF membrane decay/threshold/reset and recurrent event delivery across pages; real RTL simulator tests, mutation negatives and independent neural fixtures; **new** K26 Vivado 2025.2 project, timing/DRC/source/bitstream SHA-pinned first-original review; cooling/UART/JTAG/recovery preflight; **new** one-shot physical page-replacement/compute test with independent receipt and full numerical comparison. Do not reuse the accepted D3.D.2E bitstream as approval for a new image.

**M08.4 PHYSICAL ACCEPTANCE — FIRST OWNER ORIGINAL AND INDEPENDENT READ-ONLY AUDIT PASS, 2026-11-20:** The first-original native Vivado 2025.2 K26 run `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW` retained **15/15 original native SHA receipts**, SHA256-pinned 7,797,842-byte bit `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494`, individually reviewed **seven vendor debug/JTAG DRC warnings**, 100 MHz PS PL0 clocks, and routed **WNS +0.763 ns / WHS +0.010 ns**. Five `LUTAR-1` async-reset methodology advisories remain untraced and were accepted as bounded first-JTAG-test risk.

The owner performed the **first original one-shot real KV260 JTAG paged-neural experiment** on 2026-11-20 18:40:35–18:41:37 America/Denver. Immutable hardware evidence: `~/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ`. The exact new bit was programmed **once**; a scratch BRAM readback and distinct five-edge configuration succeeded; **six logical 256B neural pages (6+6+6+6+6+2 neurons) shared one physically resident 256B neural bank**, completing **24 real compute-bearing load/compute/full dirty-save/reload page operations across four ordered tick barriers**. The original Tcl checked **128 host-coalesced input-current values** and **384 genuinely PL-computed values** (128 voltages, 128 spike decisions, 128 recurrent currents) for **512/512 exact signed16 M02/M03 M06 oracle comparisons**; original **13/13 physical SHA receipts verified**.

The first independent read-only audit erroneously counted both Vivado's echoed Tcl marker and the actual runtime line; fixing `m08_paged_m06_lif_physical_audit.py` to match **standalone exact runtime markers in order** (with six synthetic positive/adversarial receipt regression cases) did **not alter or replay the first physical run**. [Source regression CI 44851903415](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44851903415) passed **548 M08 tests**. **The owner subsequently reran the fixed independent auditor read-only against the immutable original hardware and supplied actual output**: `original_native_15_SHA_files_checked=true`, `original_physical_sha_files_checked=13`, `original_single_JTAG_program_marker=true`, `physical_256_byte_page_dispatches_saved=24`, `ordered_tick_barriers=4`, `independent_host_coalesced_input_checks=128`, `independent_physical_pl_computed_checks=384`, `total_exact_numerical_comparisons=512`, `physical_ddr=false`. The owner reviewed this result and requested documenting completion and the next milestone. **M08.4 is formally PHYSICALLY ACCEPTED and CLOSED.**

The auditor's original result JSON intentionally says `...NUMERICAL_PASS_REVIEW_REQUIRED` / `owner_final_M08_4_acceptance_review_pending=true` because the tool is deliberately conservative **before the human acceptance decision**; these untouched historical output labels do not contradict the subsequent documented owner acceptance. **Boundary:** 17 original events were HOST-coalesced in the new paged image (not on-fabric raw FIFO); page backing was the JTAG host, **NOT genuine PS/PL DDR/DMA**. No autonomous asynchronous execution, M06 HLS implementation, hardware throughput, energy, or external-memory performance is established. Preserve the exact original source/bitstream/logs, receipts and all failed prior attempts. [Accepted first-original owner physical audit record](docs/M08_4_FIRST_OWNER_PAGED_NEURAL_PHYSICAL_2026_11_20.md).

### **M08.5 — matched real memory and execution experiments (ACTIVE)**

**Current development gate.** At matched signed16 neural semantics, network, event order, N/K, and measurement boundary, compare timestep/on-chip vs event/on-chip and genuinely memory-backed strategies **where physically feasible**. Include page locality, real transfer counts, stalls and source-matched correctness. Real DDR/DMA requires a verified live PS/PL owner, kernel-bound device/driver or equally verified PS-managed path, address-width/mask, IOMMU/cache coherency, kernel buffer lifetime and quiesce/recovery; never infer those from a device node, `/dev/mem`, or a simulated DDR array. Label JTAG-host-staged memory separately from DDR. Preserve honest negative/unavailable comparisons rather than fabricate matched points. [Consolidated execution plan](docs/M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md).

### **M08.6–M08.7 — measured reproducibility, owner review and M09 handoff (PLANNED, ONE GATE)**

Repeated original SHA-pinned raw timing and device captures, neural parity on every plotted point, real routed LUT/FF/BRAM/URAM/DSP, achieved timing and clock, PS control versus PL work, actual page bytes and queue stalls, host-end-to-end and measured uncertainty. Power/energy only with a defensible meter. Explicit owner acceptance of any narrowed scope and preserved negative evidence. **M09 starts only after this gate**.

## Working method and handoff contract

- **Keep PRs #93/#94 draft/unmerged** until explicit owner merge authorization. M08.4 accepted source remains on `agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership` and [draft PR #94](https://github.com/Xtimetraveler-Prime/Thesis/pull/94); begin M08.5 from that accepted state without rewriting history or spawning branches/PRs per experiment. Prefer complete coherent increments: code, real functional tests and adversarial failures, documentation, then owner local verification commands.
- **No new subdivided milestones** except when absolutely necessary to isolate a different physical/software failure boundary for debugging; new work is now part of M08.5 (accepted M08.4 is read-only history). Update one authoritative status paragraph instead of endlessly prepending newer “current status” banners.
- **Physical release is independent of software CI.** Original owner evidence under `~/Thesis_Evidence/M08/` stays untouched and is never overwritten/rehashed. A new hardware image needs its own exact-native source/DRC/timing/bit SHA and operator preflight, one-shot JTAG test, and read-only independent owner audit; no automatic retries and no PS DDR writes without ownership proof.
- Maintain a **single next-chat handoff** at [M08 next-instance handoff](docs/M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md), containing current branch/PR, accepted evidence, next code step, command lines and an **explicit no-sprawl instruction**. Keep the old dated histories in the archive, not inline in this overview.

## Prior work, thesis claims and limitations

Do not claim novelty for time-multiplexing, caching, sparse event pipelines, off-chip synapses or deferred leak as general mechanisms; recognize SENECA, YANA and HiAER-Spike and review each upstream license independently. The claimed **research contribution to test** is a controlled quantification of sparse execution × neural-state virtualization under a specific KV260 physical resource/latency boundary—not “the first neuromorphic FPGA” or a Loihi silicon-equivalent implementation. [Expanded literature](../../LitReview.md).

**Current accepted bottom line:** original physical 17-event FIFO + clocked M06 32-neuron/4-tick parity **accepted**; first true 6-page/1-resident-bank signed16 neural JTAG hardware **24 page operations and 512/512 comparisons independently audited and owner PHYSICALLY ACCEPTED as M08.4**. **Open:** M08.5 safe genuine memory ownership and matched physical comparisons; M08.6–7 repeatable measured performance, resources/uncertainty/possible power; M09 thesis closeout. **Next:** M08.5, then combined M08.6–7, then M09.
