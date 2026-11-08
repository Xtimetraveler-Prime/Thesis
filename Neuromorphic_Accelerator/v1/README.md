# Neuromorphic Accelerator v1 — Architecture Research

**Status: M01–M04 COMPLETE in approved scopes (M04 merged PR #78); M05 IN PROGRESS on unmerged draft PR #79 with three host-tested HLS-oriented C++ subcomponents (streamed LIF update, signed tick accumulation and local state RAM) plus PC sparse scheduling; real Vitis synthesis/FPGA execution NOT RUN.** No synthesized PL engine, on-chip hardware scheduler, DDR/RTL/bitstream, KV260 measurement or claim of accelerated performance has been accepted. This is a **new first-generation project**, not v4 of the Loihi twin. The umbrella `Neuromorphic_Accelerator` allows investigation beyond any one fixed accelerator microarchitecture.

## Motivation and questions

The existing `Loihi_Digital_Twin/v3` proved a Loihi-inspired, DDR-backed virtualized LIF architecture and established genuine original neural/physical evidence, but large network execution exposed substantial system-level orchestration/context-transfer cost. V3 is frozen; additional A/B physical experiments and remaining milestones were canceled, except a final **deferred** optional bounded optimization milestone. Do not treat v3's unequal 42- versus 1010-neuron workloads as a matched accelerator comparison.

> How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover?

> How do DDR-backed virtualization and event-driven sparsity interact to determine the performance, scalability, and hardware efficiency of FPGA-based spiking neural network accelerators?

These are **hypotheses/questions**, not demonstrated results. The goal is to characterize virtualization rather than assume it produces acceleration.

## Guardrails carried from v3

- **Preserve independently verifiable LIF neuron dynamics**, with an explicitly chosen fixed-point/simulation-time reference. Architectural numerical changes, such as lazy accumulated leak, must be checked against that reference and documented if non-bit-exact.
- **Preserve logical-to-physical resource virtualization**, backed by DDR as a design variable—not the historical fixed-size Loihi-like virtual core format, original 27-core partitioning, or imposed Loihi hardware limits.
- **Pursue sparse, event-driven execution** (inspired by literature such as YANA, without copying its implementation), testing temporal sparsity, connectivity sparsity and **active-state locality** independently.
- **Keep inference timing and memory-traffic contracts honest.** Compare complete input-to-output service at matched networks alongside separate PL, scheduler, DDR-transfer, cache and queue metrics. Do not assume energy savings or matched YANA runtime.
- **Keep a clean provenance boundary:** source and tests in Git; accepted physical evidence in external immutable directories, new build/ELF/bitstream hashes, preflight/independent review before any claims. No physical run is authorized by this document; old v3 JTAG runbooks are archived.
- **Official MNIST TEST remains sealed** until a separately scoped evaluation.

## What is deliberately NOT decided

No mandate for fixed virtual cores, group size, neuron-to-group mapping, neuron/event pipeline, cache organization, DDR layout, CSR/CSC adjacency choice, event queue schedule, timestamp/leak arithmetic, PS/PL ownership, AXI/DMA mechanism, or HLS/RTL reuse. Those decisions will be made against a verified performance/communication cost model.

Initial architecture brainstorming: [`docs/ARCHITECTURE_DESIGN_QUESTIONS.md`](docs/ARCHITECTURE_DESIGN_QUESTIONS.md).

**Accepted M03 research:** [neural/workload and experimental contract](docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md), [28-test explanation](docs/M03_TESTS_EXPLAINED.md), [PC verification](docs/M03_PC_ONLY_VERIFICATION.md). **Authoritative next-chat handoff:** [M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md](docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md), which includes the **mandatory per-milestone test-explanation workflow**. No physical DDR measurements, trained-model results, FPGA programming or HW speedup are accepted.

**Development milestone plan:** [`roadmap.md`](roadmap.md) — M01–M09 stage gates covering virtual neuron/group/hybrid trade studies, independent LIF oracle, workloads/traffic, existing HLS reuse, event scheduling engine, DDR virtualization, policy variants, KV260 validation and final quantitative characterization. M01 passed automated tests and user-reported native PC verification; user approved **configurable block-based residency as provisional baseline**, retaining neuron-granular/hybrid controls. Review the [M01 architecture options](docs/M01_ARCHITECTURE_OPTIONS.md), [full 20-test explanation](docs/M01_TESTS_EXPLAINED.md) and [local reproduction runbook](docs/M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md).

## Accepted M04 and current M05 development (NO BOARD)

M01's approved provisional memory-placement baseline and tests are documented. **M02's initial v1 numerical and event-order contract is user-accepted as the current reference**, with dense and queued synaptic-delivery implementations; see the [provisional numerical contract](docs/M02_PROVISIONAL_LIF_CONTRACT.md), [21-test explanation](docs/M02_TESTS_EXPLAINED.md), [local native verification](docs/M02_PC_ONLY_VERIFICATION.md), and [current next-chat handoff](docs/M02_NEXT_CHAT_HANDOFF.md). M02 is **accepted in its PC-only neural scope**, but no event-sparse hardware engine, physical DDR model or KV260 run has been validated. **Do not interpret modeled state-access transactions as timed SNN inference.** M03 now implements synthetic role-isomorphic input/network workloads, independently matches M02 dense/event-queued traces to provably safe-sparse reference state updates, and reports a **PC-only** four-way state-versus-synapse traffic model. A 36-pair multi-seed sweep is available. **M03 user-native test PASS and scope approval are recorded.** M04 was accepted and merged to main as PR #78 (merge `7d97494a`). **M05** adds a new streaming C++ evaluator top and a separate exact-sparse *host* event scheduler on branch `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` (draft PR #79). **48 M05 and 91 prior named methods (139 total), plus three native-only HLS-bench smokes, passed CI; real Vitis HLS Csim/synthesis/C-RTL/board NOT RUN.** Review [v3-versus-new engine differences](docs/M05_ENGINE_V3_COMPARISON.md), [48 M05 tests explained](docs/M05_TESTS_EXPLAINED.md), [M05 PC-only verification](docs/M05_PC_ONLY_VERIFICATION.md), [K26 Vitis 2025.2 offline commands](docs/M05_HLS_OPERATOR_RUNBOOK.md) and [current handoff](docs/M05_NEXT_CHAT_HANDOFF.md). Real KV260 performance and energy remain unmeasured.

## M04.5 — Completed numerical requirements handoff (parent M04 merged)

The [M04.5 proposed K26 engine profile and M05 handoff](docs/M04_5_ENGINE_REQUIREMENTS_AND_M05_HANDOFF.md) documents one W16 physical pipeline with a 100 MHz **synthesis goal** (not a measured result), u32 decay ratio, i64 **exact aggregate** and an initial cap of 4096 individual arrivals per tick. A [known-input host preflight](src/neuromorphic_accelerator_v1/m04_profile.py) and [nine new negative/boundary test methods](tests/test_m04_handoff.py) exercise mathematical limits and rejected M02-legal workloads outside this first **hardware admission subset**. The [M04 test explanations](docs/M04_TESTS_EXPLAINED.md) and [VS Code verification runbook](docs/M04_PC_ONLY_VERIFICATION.md) now cover 22 M04 methods. **No synthesized streaming/queue hardware or runtime overflow guard is claimed; those are M05 tasks.** User reported native verification of the previous 13 M04 methods and explicitly authorized closing and merging M04 after [91-method host CI PASS](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42454052773). The nine new M04.5 methods have **CI evidence only**, not independent user-native log evidence; no HLS/physical claims.

## Repository / workflow

Root documentation is [`../../README.md`](../../README.md) and source survey is [`../../LitReview.md`](../../LitReview.md). The [frozen v3 roadmap](../../Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) and [v3 evidence / hardware workflow handoff](../../Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md) remain historical references. Use a new branch per milestone, PC-native tests and no-board CI, exact VS Code pull/testing commands, and a **mandatory docs/MXX_TESTS_EXPLAINED.md** explaining the actual tests, fixtures, pass criteria, failures, and evidence limits for each milestone. See the [M04 handoff workflow](docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md). **Do not merge or program KV260 without explicit operator approval.**

**M04 accepted reference links:** [source audit and extract/wrap/new matrix](docs/M04_HLS_ENGINE_AUDIT.md), [test-by-test explanation](docs/M04_TESTS_EXPLAINED.md), [VS Code native reproducibility](docs/M04_PC_ONLY_VERIFICATION.md), and [candidate C++ files](hls/m04_lif_eval/). This is not an approved architecture freeze: signed-64 aggregation and 32-bit decay-ratio representability limit the candidate's numerical domain, hardware II and resources are unmeasured, and no v1 HLS synthesis was performed during M04. M04 closure/merge was explicitly authorized by the user. Historical v3 files remain unchanged.

**Verified M04 no-board CI evidence:** 22 M04 methods and 69 regressions PASS on the final accepted M04 branch, then user-authorized merge PR #78. **Current M05 host CI:** [45 M05 methods plus 91 regressions PASS, three HLS benches compiled natively](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42456476435). M05 user-native verification and explicit merge authorization are pending. No physical operation.


## M05 hardware-facing subcomponents staged for Vitis (NOT synthesized)

The three independent, project-owned HLS-oriented C++ tops are [per-neuron stream evaluator](hls/m05_stream_eval/m05_stream.cpp), [signed tick accumulator](hls/m05_accumulator/m05_accumulator.cpp) and [bounded persistent state memory](hls/m05_stateful/m05_stateful.cpp). A single [no-board Vitis operator script](hls/m05_stream_eval/run_m05_offline_hls.sh) supports `--stream`, `--accumulator` and `--stateful` with cumulative `--csim`, `--synth`, `--cosim` or `--impl` stages. [Exact commands and files to return](docs/M05_HLS_OPERATOR_RUNBOOK.md). These are isolated candidate tops, **not a connected PL accelerator**: actual future-delay FIFO/router, backpressure, global tick barriers, on-chip cache-block mapping and whole-network RTL trace verification remain M05 work. User-native M05 evidence and explicit merge authorization are pending. No physical KV260 programming is authorized.


### First real HLS CSim feedback: source-path fix pending operator rerun

On 2026-11-08, Vitis 2025.2 launched correctly on the K26 for all three IPs, but **each true CSim FAILED before compilation** because workdir-relative source/testbench paths did not resolve; the old output key was also deprecated. The [diagnosis](docs/M05_HLS_CSIM_FAILURE_2026_11_08.md), [absolute-path effective-config generator](hls/m05_stream_eval/prepare_hls_config.py), corrected [runner](hls/m05_stream_eval/run_m05_offline_hls.sh) and three [path regression tests](tests/test_m05_hls_path_regression.py) are now committed. **Mock-tool/native CI PASS is not genuine Vitis CSim PASS.** The 48 M05 +91 regression source tests may pass while all three original Vitis failures remain recorded; user retest is required. [Exact operator commands](docs/M05_HLS_OPERATOR_RUNBOOK.md). No merge, no board.
