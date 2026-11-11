# Neuromorphic Accelerator v1

**Status (November 10, 2026): M01–M07 complete in explicitly bounded scopes. M07 covers source-only policy, locality, batching and synthetic service models, NOT measured FPGA speed; physical M08 remains separately gated.** This is the active, independently versioned SNN/FPGA research program—not Loihi Digital Twin v4.

The goal is to determine the tradeoffs among **neural-state virtualization, sparse event execution, cache locality and FPGA resource limits**. The reference neural behavior is a separately checked signed-integer LIF model. The accelerator must preserve that reference while scaling logical neurons beyond the bounded resident working set.

## Start here

| Need | Reference |
| --- | --- |
| Research questions and project lineage | [Thesis overview](../../README.md) |
| Milestones, next experiment and acceptance criteria | [M01–M09 roadmap](roadmap.md) |
| **M07 source-only acceptance and reproducibility** | [M07 acceptance review](docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md), [test explanations](docs/M07_TESTS_EXPLAINED.md), [owner commands](docs/M07_PC_ONLY_VERIFICATION.md), [prior-art register](docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md) |
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
