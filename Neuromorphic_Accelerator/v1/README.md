# D3.D.2B owner physical result (2026-11-20)

> **ACTIVE D3.D.2C M06 32-neuron RTL/PC source phase (2026-11-20; NO BOARD).** D3.D.2B original physical recurrent routing is accepted (owner six-file SHA + M02 triple-trace independent audit; original HW `m08_d3d2b_synaptic_HW_Pw3KKKXl`, bit SHA `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14`). A NEW stacked branch `agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron` adds distinct **32 signed16 neuron ×4 ticks** AXI RTL (`M32N` v4), signed truncate-to-zero **3/4** decay, up to eight positive-delay weighted recurrent edges, original **M06 G3.3 five-edge/17-external-event** oracle with M02 dense/event + M03 exact sparse cross-check, full 128-voltage/128-spike/128-hardware-syn-current Icarus readback bench, and new **offline-only** Vivado candidate builder + fail-closed first native image review. The 17 events are **host-coalesced** to signed32 external neuron/tick currents; fabric computes recurrent synaptic deliveries itself. This is **not** the original M06 paged-HLS physical engine, event-stream hardware, DDR/paging or physical KV260 32-neuron result. A new bitstream, first owner Vivado DRC/timing/source/image SHA review, and separately audited one-shot physical test are still required. **No D3.D.2C programming, no D3.D.2B rebuild, no inherited warning waiver**. See [D3.D.2C staged next hardware test](docs/M08_D3D2C_M06_32_NEURON_PHYSICAL_PLAN_2026_11_20.md). M08 OPEN/M09 PLANNED; all stacked PRs draft/unmerged.


**2026-11-20 10:36–10:37 MST — OWNER ORIGINAL D3.D.2B PHYSICAL RECURRENT SYNAPSE PARITY PASS.** The owner supplied the genuine Linux PC / Vivado 2025.2 one-shot terminal transcript (not a direct assistant read of owner filesystem). The original read-only native gate returned exit **0** with 12/12 original SHA ledger entries OK and nested `M08_D3D2B_NATIVE_ROUTED_SYNAPSE_CANDIDATE_ACCEPTED_NO_BOARD`. The original bitstream was **not rebuilt**: SHA256 `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14`, 7,797,847 bytes, owner native `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO`, original reviewed 7 vendor/debug warnings (only first 15 displayed RTSTAT paths individually reviewed), WNS **+0.136 ns**, WHS **+0.012 ns**, TNS/THS 0. The original third PDCN-1569 LUT warning used the exact `SWITCH_N_EXT_BSCAN.id_state[0]_i_1/I0` path and `is not included` text; narrowly corrected synthetic-gate assumptions were accepted without changing RTL, builder or image.

**Genuine board observation:** `xck26_0` on `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, configuration startup HIGH, `M08_D3D2B_PROGRAM_COMPLETED`, `hw_axi_1` 32-bit JTAG AXI, BRAM echo `55AA22DD`, and new synaptic engine ID `M4SN` / `0x00030000`. Both real on-device recurrent networks passed: `chain_recurrent` spike masks `[1,2,4,8]` and `inhibition_half_decay` spike masks `[1,10,4,8]`. **32/32 voltages, 32/32 per-tick spike decisions, and 32/32 hardware-delivered synaptic currents** matched independently generated M02 dense/event reference. The first one-shot physical folder is **immutable**: `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_HW_Pw3KKKXl`. Its original **6/6** physical SHA ledger entries checked `OK`, independent physical audit returned `M08_D3D2B_PHYSICAL_RECURRENT_SYNAPTIC_ROUTING_M02_PARITY_ACCEPTED`, runner printed `M08_D3D2B_HARDWARE_RECURRENT_SYNAPSE_M02_PARITY_SUCCEEDED`, and `M08_D3D2B_PHYSICAL_RUN_EXIT=0`. This report establishes *bounded* recurrent routed synaptic computation on fabric; it does **not** prove physical 32-neuron M06, physical DDR/paging, Linux/PS compatibility, PS-clock independence, sustained cooling, performance, or energy. **D3.D.2B PHYSICAL COMPLETE; M08 OPEN, M09 PLANNED. D3.D.2C next: distinct 32-neuron ×4-tick RTL/ABI/synapse-capacity design with independent M02/M06 oracle, Icarus, then separate genuine native+owner physical gates.** Earlier "pending" entries below remain historical and are superseded by this owner-supplied original pass. Draft PR stack remains unmerged.

---

# Neuromorphic Accelerator v1

> **CURRENT D3.D.2B EXACT OWNER DRC REVIEW — 2026-11-20:** Genuine owner routed synapse image in `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO` is already successfully bitgen-complete, 12/12 original SHA entries OK. Full report reviewed: seven *vendor JTAG/debug warnings only* (3 XSDB PDCN-1569, REQP-1857 JTAG rx_fifo once, REQP-1858 JTAG rd_cmd + wr_cmd twice, RTSTAT-10 39 unroutable nets/37 listed, first 15 actually printed and individually reviewed). All timing constraints met: WNS +0.136 ns, WHS +0.012 ns, TNS/THS 0. **NO RTL REWORK OR NEW BITSTREAM NEEDED BASED ON THIS REPORT.** Unmodified original .bit SHA256 `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14` (7,797,847 bytes), RTL SHA `2894f33a1c0054a0cf0231e1c4970e5eaea377bbe7524e4c57717c033b5ad88b`, builder SHA `82ba3b226e16ac579cfc2527216f8acb02f9b13d3f42c5574344fcc9ce49e1a8` now pinned by revised source/native gate and one-shot physical runner. Native acceptance **still requires owner to rerun exact new read-only gate on original directory**, and **D3.D.2B PHYSICAL JTAG SYNAPSE ROUTING NOT YET DONE**. Next: read-only local tests/native gate, then fresh cooling/UART/identity preflight, then one protected one-shot FPGA JTAG test. Preserve original first exit-2 DRC warning rejection. [Authoritative next-chat handoff](docs/M08_D3D2B_NEXT_CHAT_PHYSICAL_HANDOFF_2026_11_20.md). M08 OPEN/M09 PLANNED; D3.D.2C 32-neuron architecture NOT physically built.


> **D3.D.2B FIRST OWNER NATIVE BITGEN SUCCEEDED; DRC acceptance pending (2026-11-20 00:50 MST).** Original new Vivado 2025.2 routed recurrent-synapse image `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO/bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit` was written successfully; all 12 original SHA evidence checks passed. First new `m08_d3d2b_synaptic_gate.py` native check correctly returned `D3D2B_NEW_DRC_REVIEW_REQUIRED` (seven ORIGINAL new DRC findings) and exit 2; no board programmed and native acceptance not granted. The submitted stdout does NOT include actual DRC entries, the new bitstream digest or the routed timing values. **Preserve and inspect this original folder read-only; do not rebuild or waive the findings by rule count.** If original details prove to be vendor-only, review and pin exact bitstream+warning profile, then physically verify four-neuron recurrent routing before beginning separate M06 32-neuron D3.D.2C architecture. [Read-only original report commands](docs/M08_D3D2B_RECURRENT_SYNAPSE_PHYSICAL_PLAN_2026_11_20.md).

> **D3.D.2B next hardware candidate, source-only (2026-11-20):** Following owner-accepted genuine D3.D.2A four-neuron physical M02 parity, a separate stacked development branch adds eight configurable signed16 weighted positive-delay (1–3 tick) synapses across four neurons, true recurrent/parallel/inhibitory routing, and *hardware-generated* delivered-current trace. New peripheral `M4SN` v3, new RTL/testbench, dual M02 dense+queued exact trace fixtures, separate PC-only Vivado 2025.2 builder, new fail-closed original native gate and staged one-shot physical Tcl/auditor. **No D3.D.2B owner native bitstream or physical pass yet**; first new DRC report requires separate review and bitstream SHA acceptance. D3.D.2A original files/bitstream/evidence remain untouched. After source CI/owner Icarus, next step is a new owner native Vivado run, then reviewed JTAG physical test. [Detailed register map, fixture expectations and operator commands](docs/M08_D3D2B_RECURRENT_SYNAPSE_PHYSICAL_PLAN_2026_11_20.md). M08 OPEN; M09 PLANNED; draft PR stack unmerged.

> **CURRENT OWNER-REPORTED PHYSICAL ACCEPTANCE — D3.D.2A PASSED (2026-11-20 00:02–00:03 MST).** Genuine KV260 `xck26_0` programmed with unchanged accepted four-neuron bitstream SHA256 `3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411` (7,797,843 bytes; owner native `~/Thesis_Evidence/M08/m08_d3d2a_four_w4YfdBuE`). Live JTAG `hw_axi_1`, startup HIGH, BRAM echo `55AA22DD`, four-LIF magic/version `0x4D344C46/0x00020000`, two distinct four-neuron × four-tick workloads returned full M02-matching voltages and spike masks. **All 32 individual membrane voltages and 32 per-neuron/tick spike decisions passed**, nonce/status/count 1→2 passed. `independent_half_decay` masks `[2,1,0,0]`; `independent_unit_decay` masks `[2,1,2,0]`. Owner's original six physical SHA ledger entries checked `OK`; independent `m08_d3d2a_four_physical_audit.py` returned `status=M08_D3D2A_PHYSICAL_FOUR_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED`, `hardware_execution_verified=true`, and launcher `M08_D3D2A_PHYSICAL_RUN_EXIT=0`. Original physical evidence path **`~/Thesis_Evidence/M08/m08_d3d2a_four_HW_UBi3VCax` is immutable**. This conclusion is sourced to the owner's supplied original Vivado/host terminal transcript, not to direct local file reads here. **Bounded result: four independent neurons, no synaptic routing, M06 network/DDR/PS-clock independence/throughput or energy. Next D3.D.2B: implement genuine positive-delay signed weighted synaptic routing and recurrent/cancellation M02 parity before new native/physical tests.** M08 OPEN, M09 PLANNED. D3.C and D3.D.1 original evidence remains preserved; drafts unmerged.


> **Current D3.D.2A boundary (2026-11-19):** Four-neuron ×four-tick RTL/Icarus passes on GitHub CI, genuine owner original routed candidate exists with 12/12 original SHA receipt checks, exact reviewed seven vendor/debug DRC warnings, positive timing and new SHA-pinned physical JTAG readback/auditor scripts. **Historical pre-physical status; superseded by the D3.D.2A actual hardware acceptance above.** Exact bit SHA256 `3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411`, original native folder `m08_d3d2a_four_w4YfdBuE`. [Next owner original-gate and one-shot JTAG commands](docs/M08_D3D2A_FOUR_NEURON_PLAN_2026_11_19.md).

> **D3.D.2A (NEW SOURCE ONLY, November 19 2026):** After independently accepted physical one-neuron LIF parity, the next development branch adds a four-neuron ×four-tick AXI-Lite hardware prototype, two M02 dense/queued fixtures, directed Icarus testbench, and a separate native-PC Vivado builder. **Historical pre-native statement; actual D3.D.2A physical FPGA and M02 parity now PASSED as reported above.** The existing D3.D.1 bitstream and physical evidence remain accepted and untouched; do not claim new multi-neuron physical proof. [Owner D3.D.2A verification steps](docs/M08_D3D2A_FOUR_NEURON_PLAN_2026_11_19.md).


**Current status (November 19, 2026): M01–M07 accepted within their bounded scopes; M08 IN PROGRESS. D3.C JTAG→AXI→BRAM FOUR-WORD READBACK PHYSICALLY PASSED, and D3.D.1 genuine KV260 FPGA signed16 LIF neural computation PHYSICALLY PASSED.** Owner's one-shot hardware evidence `~/Thesis_Evidence/M08/m08_d3d_neuron_HW_NMgBWpCj` shows real `xck26_0` programming with bitstream SHA256 `b071adcec0ba33077cdf70543d5cc9c354f6746bcc8138e8c741c41a3cbb1c8b`, BRAM echo, four distinct single-neuron × four-tick hardware membrane/spike traces exactly matching the M02 dense/event reference, 6/6 original physical SHA ledger checks and independently accepted physical audit. **Next: D3.D.2 multiple neurons, state scheduling and synapse routing toward M06 32-neuron ×4-tick parity.** Hardware DDR/paging, complete M06 network, PS-clock independence, Linux-manager compatibility, throughput and energy are **NOT** proven. This remains the independent SNN/FPGA research program—not Loihi Digital Twin v4.

The goal is to determine the tradeoffs among **neural-state virtualization, sparse event execution, cache locality and FPGA resource limits**. The reference neural behavior is a separately checked signed-integer LIF model. The accelerator must preserve that reference while scaling logical neurons beyond the bounded resident working set.

## Start here

| Need | Reference |
| --- | --- |
| Research questions and project lineage | [Thesis overview](../../README.md) |
| Milestones, next experiment and acceptance criteria | [M01–M09 roadmap](roadmap.md) |
| **D3.D.1 physical LIF PARITY ACCEPTED; NEXT D3.D.2 multi-neuron** | [Physical LIF evidence and next-stage plan](docs/M08_D3D_PHYSICAL_NEURAL_PARITY_PLAN_2026_11_19.md), [historical preflight handoff](docs/M08_D3D_1_PHYSICAL_LIF_NEXT_CHAT_HANDOFF_2026_11_19.md), [D3.C physical JTAG communication](docs/M08_D3C_JTAG_BRAM_PL_LINK_2026_11_19.md). **Owner physical readback and M02 audit PASS; original single-neuron scope only.** |
| **M08 physical roadmap and first hardware entry** | [M08 phased plan](docs/M08_PHASED_HARDWARE_PLAN.md), [owner first PC/UART runbook](docs/M08_FIRST_PC_KV260_RUNBOOK.md), [M08 tests explained](docs/M08_TESTS_EXPLAINED.md); M07 acceptance preserved [here](docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md) |
| M05 signed32 on-chip engine verification | [M05 acceptance review](docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md) |
| M06 original HLS+AMD paging/fault/recovery evidence | [M06 acceptance review](docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md) |
| Exact LIF semantics and event ordering | [M02 reference contract](docs/M02_PROVISIONAL_LIF_CONTRACT.md) |
| Matched neural workloads and measurement definitions | [M03 experimental contract](docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md) |
| Prior-art comparisons | [Thesis literature review](../../LitReview.md) |
| Complete historical milestone chronology | [Pre-cleanup v1 README](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/README.md) and [roadmap](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/roadmap.md) |

## Architecture in brief

1. **Independent numerical contract.** The M02 dense and queued references establish exact LIF updates, signed synaptic accumulation, recurrent delays and event ordering. Quiet-neuron behavior is checked explicitly.
2. **Workload and traffic controls.** M03 generates reproducible, role-isomorphic synthetic networks that vary activity locality while preserving neural work, and estimates state/synaptic traffic without pretending it is a physical DDR measurement.
3. **On-chip prototype.** M04 audited reusable arithmetic; M05 built an FPGA-targeted signed32 rolling/event-oriented inference path with original HLS/RTL verification and host-facing stream/control experiments.
4. **Virtualized state.** M06 models a canonical **64 KiB scratch-backed image** with bounded resident slots, page fills, dirty evictions and actual original HLS AXI reads/writes through original AMD SmartConnect/width converters **in offline simulation**.
5. **Fault/commit boundaries.** M06 guard RTL detects original AXI read/write error responses, a watchdog poisons epochs with missing acknowledgment, and a bounded trace/metrics quarantine releases output only after successful completion. A separate verified recovery test uses an **explicit testbench-owner reset and entire simulated image rewrite**; it is not automatic hardware rollback.

6. **M07 policy and synthetic-service closeout.** M07.1–M07.5 add direct vs LRU, four-way logical M03 controls, fixed-byte-budget locality sweeps, one experimental causal history eviction candidate, and source-only queue/event-batching/synapse-record sensitivity. All final neural traces match accepted M02/M03. Completed M06 **software** state transfers are modeled using explicit assumed cycle costs and bounded FIFO backpressure, not observed AXI/DDR timing, measured performance or resource-matched FPGA implementation. [M07 scope-limited acceptance](docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md).

### What has been verified

| Milestone | Accepted result | Evidence |
| --- | --- | --- |
| M01 | PC-only block/individual/hybrid residency tradeoffs; block grouping selected provisionally | [M01 design options](docs/M01_ARCHITECTURE_OPTIONS.md) |
| M02 | PC-only exact integer LIF reference and independent event-queued cross-check | [M02 tests](docs/M02_TESTS_EXPLAINED.md) |
| M03 | PC-only synthetic workloads, safe-sparse equivalence and four-way analytical traffic | [M03 contract](docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md) |
| M04 | HLS engine numerical/interface reuse audit and bounded host candidate; no M04 synthesis required | [M04 audit](docs/M04_HLS_ENGINE_AUDIT.md) |
| M05 | Offline signed32 on-chip inference and original integrated HLS/RTL simulation | [M05 accepted evidence](docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md) |
| M06 | Five original Vivado 2025.2 HLS+AMD owner PASS archives: G3.3 32 neurons ×4 ticks/one-slot neural and state parity; G4 write/read SLVERR, held-B watchdog, and simulated restore plus clean 16-trace/1-metrics postcommit publication | [M06 accepted evidence, SHAs and nonclaims](docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md) |
| M07 | PC-only cache policy and locality/capacity/batching ablations, source-traced M06 synchronous service and explicitly assumed FIFO/queue timing; physical metrics unmeasured | [M07 scope-limited acceptance](docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md) |

**Important scope limit:** Real vendor *simulation* is not a programmed board. **No actual PS DDR-backed inference, physical KV260/JTAG run, real DMA transfer/latency, deployed overall resource/timing/energy measurement, automatic crash-atomic rollback or measured acceleration is established by M06.** The simulation's 1024-cycle watchdog is a directed test threshold, not a measured DDR service deadline. M08 has separately gated physical tests.

## Source and development workflow

| Path | Purpose |
| --- | --- |
| 'src/neuromorphic_accelerator_v1/' | Independent neural, residency, workload and traffic models |
| 'hls/' | FPGA-oriented neural engines, Vitis HLS projects and source |
| 'rtl/' | Local transport, control, AXI guard, memory/residency and quarantine RTL |
| 'scripts/' | Host model runs, exact toolchain/owner experiment runners and evidence packaging |
| 'tests/' | Unit, regression, negative-contract and testbench source tests |
| 'docs/' | Architecture decisions, test explanations, runbooks and immutable evidence reviews |
| '.github/workflows/' (repository root) | Separate no-board milestone CI workflows |

Start a new milestone on its own branch from the accepted 'main'; do not overwrite proven source or rerun accepted owner experiments without a reason. With an updated checkout:

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch main
git pull --ff-only origin main
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
~~~

For a broader host regression (without hardware):

~~~bash
python3 -m unittest discover -s tests -v
~~~

Icarus-dependent RTL tests may require 'iverilog' and 'vvp'. They verify local RTL only; declaration-only stubs do **not** simulate actual HLS or AMD behavior. Genuine original AMD/HLS evidence comes from operator-run Vivado; original generated source, XCI/dat assets and original logs remain preserved in **~/Thesis_Evidence/**, outside Git.

For each future milestone, maintain an 'MXX_TESTS_EXPLAINED.md' explaining actual test purpose, fixtures, outcomes, negative cases and what success does **not** prove. Attach original SHA-pinned evidence before accepting a tool or hardware claim. Accept and merge only with explicit user approval.

## Next: M07 and later physical validation

**M07 — scheduling/cache variants and controlled ablations:** build a simple no-cache or fixed-residency baseline, a simple FIFO/LRU-class policy, and optionally one activity/locality-aware scheduler; measure matched timestep/on-chip, event/on-chip, timestep/DDR-style and event/DDR-style configurations with **identical network and neural semantics**. Vary context locality independently of total spikes and report counters/negative results. See [full M07 acceptance criteria](roadmap.md#4-m07--schedulingcache-policy-variants-and-ablation-controls).

**M08** (after new operator authorization): physical KV260 integration, resource/timing closure and true DDR/end-to-end measurements. **M09:** quantitative virtualization penalty, sparsity benefit, locality and interaction analysis with uncertainty and reproduced raw captures.

**Physical safety:** No archived JTAG/DDR instructions authorize a new physical operation. Obtain a separate, session-specific operator preflight before any board memory or boot/JTAG action. The official MNIST TEST remains sealed.

## Project origin and history

The original Loihi-inspired [v3 digital twin](../../Loihi_Digital_Twin/v3/) established real historical FPGA/PS architecture and measurements; it is **frozen**. This new v1 does not copy its 27 logical-core constraint or claim Loihi/YANA novelty or silicon fidelity. Keep comparisons scientifically matched and cite [YANA, SENECA, HiAER-Spike and other prior art](../../LitReview.md).

A long chronological sequence of accepted/failed M05 and M06 experiments was previously embedded above this README. **Nothing was deleted from Git history.** The complete prior document is available at the [SHA-pinned pre-cleanup revision](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/README.md), while milestone-specific details remain in 'docs/'. See [documentation cleanup index](docs/REPOSITORY_DOCS_CLEANUP_2026_11_10.md).
