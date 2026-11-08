# Neuromorphic Accelerator v1 — Architecture Research (PLANNING)

**Status: INITIAL DESIGN DISCUSSION — no source implementation, hardware bitstream or claims of accelerated performance.** This is a **new first-generation project**, not v4 of the Loihi twin. The umbrella `Neuromorphic_Accelerator` allows investigation beyond any one fixed accelerator microarchitecture.

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

## Next step (planning, NOT implementation)

Specify a reference LIF and event-order contract; prototype a trace-driven latency/DDR-traffic cost model for sparse virtual-neuron working sets; then compare candidate state-storage and grouping/scheduling strategies before selecting hardware interfaces. A minimal on-chip-versus-DDR and timestep-versus-event-driven control matrix should be planned before writing hardware.

## Repository / workflow

Root documentation is [`../../README.md`](../../README.md) and source survey is [`../../LitReview.md`](../../LitReview.md). The [frozen v3 roadmap](../../Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) and [v3 evidence / hardware workflow handoff](../../Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md) remain historical references. Use a new branch per milestone, PC-native tests and no-board CI, and exact local VS Code pull/testing commands with each implementation change. **Do not merge or program KV260 without explicit operator approval.**
