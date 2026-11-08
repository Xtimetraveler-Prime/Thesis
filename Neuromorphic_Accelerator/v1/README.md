# Neuromorphic Accelerator v1 — Architecture Research

**Status: M01, M02 and M03 COMPLETE / USER-ACCEPTED (PC-only); M04 IN PROGRESS on an unmerged branch (v3 HLS audit and bounded host C++ numerical candidate).** No physical microarchitecture, LIF engine, RTL/bitstream, KV260 measurement or claim of accelerated performance has been accepted. This is a **new first-generation project**, not v4 of the Loihi twin. The umbrella `Neuromorphic_Accelerator` allows investigation beyond any one fixed accelerator microarchitecture.

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

## Current M04 work (host only; NOT a hardware implementation)

M01's approved provisional memory-placement baseline and tests are documented. **M02's initial v1 numerical and event-order contract is user-accepted as the current reference**, with dense and queued synaptic-delivery implementations; see the [provisional numerical contract](docs/M02_PROVISIONAL_LIF_CONTRACT.md), [21-test explanation](docs/M02_TESTS_EXPLAINED.md), [local native verification](docs/M02_PC_ONLY_VERIFICATION.md), and [current next-chat handoff](docs/M02_NEXT_CHAT_HANDOFF.md). M02 is **accepted in its PC-only neural scope**, but no event-sparse hardware engine, physical DDR model or KV260 run has been validated. **Do not interpret modeled state-access transactions as timed SNN inference.** M03 now implements synthetic role-isomorphic input/network workloads, independently matches M02 dense/event-queued traces to provably safe-sparse reference state updates, and reports a **PC-only** four-way state-versus-synapse traffic model. A 36-pair multi-seed sweep is available. **M03 user-native test PASS and scope approval are recorded.** M04 is now active on `agent/neuromorphic-accelerator-v1-m04-hls-audit`: the v3 arithmetic/interface audit identifies substantial numerical incompatibility with M02; a new stateless C++ one-neuron update candidate is under PC-only verification. **No full streaming kernel or Vitis synthesis has been established.** See [M04 next-chat handoff seed](docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md). Real KV260 performance and energy remain unmeasured.

## Repository / workflow

Root documentation is [`../../README.md`](../../README.md) and source survey is [`../../LitReview.md`](../../LitReview.md). The [frozen v3 roadmap](../../Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) and [v3 evidence / hardware workflow handoff](../../Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md) remain historical references. Use a new branch per milestone, PC-native tests and no-board CI, exact VS Code pull/testing commands, and a **mandatory docs/MXX_TESTS_EXPLAINED.md** explaining the actual tests, fixtures, pass criteria, failures, and evidence limits for each milestone. See the [M04 handoff workflow](docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md). **Do not merge or program KV260 without explicit operator approval.**

**M04 review links (working branch):** [source audit and extract/wrap/new matrix](docs/M04_HLS_ENGINE_AUDIT.md), [test-by-test explanation](docs/M04_TESTS_EXPLAINED.md), [VS Code native reproducibility](docs/M04_PC_ONLY_VERIFICATION.md), and [candidate C++ files](hls/m04_lif_eval/). This is not an approved architecture freeze: signed-64 aggregation and 32-bit decay-ratio representability limit the candidate's numerical domain, hardware II and resources are unmeasured, and merge requires the user's native PASS and explicit approval. Historical v3 files remain unchanged.

**Verified M04 no-board CI evidence:** [M04 host compilation and 13 numerical tests plus 69 accepted regressions passed at `703ac994`](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694640). Physical synthesis, programming and live FPGA performance are still not attempted; independent native user reproduction remains the next gate.
