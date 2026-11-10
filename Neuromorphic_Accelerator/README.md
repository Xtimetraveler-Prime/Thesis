# Neuromorphic Accelerator — Research Workspace

This directory houses the **new, independently versioned FPGA SNN research program**, separate from the preserved [Loihi Digital Twin](../Loihi_Digital_Twin/v3/). The umbrella name leaves room for architectural research, virtualized neural-state experiments, event scheduling, and hardware/software co-design—not only a particular accelerator implementation.

## Where to start

- **[v1 README](v1/README.md):** current architecture, implemented components, test commands and acceptance boundaries.
- **[M01–M09 roadmap](v1/roadmap.md):** research objectives, milestone status, M07–M09 plans and experimental gates.
- **[Architecture design questions](v1/docs/ARCHITECTURE_DESIGN_QUESTIONS.md):** open alternatives and assumptions.
- **[Research motivation](../README.md)** and **[literature review](../LitReview.md):** thesis questions and prior-art context.
- **[Frozen v3 project](../Loihi_Digital_Twin/v3/):** previous verified Loihi-inspired implementation and historical physical evidence, not the new project's codebase.

## Current status — November 10, 2026

**Neuromorphic Accelerator v1 milestones M01–M06 are accepted in explicitly bounded scopes; M07 is planned next.**

M01–M03 established software-only residency choices, exact independent LIF models, controlled workloads and analytical traffic. M04 audited existing arithmetic. M05 produced and verified an **offline on-chip FPGA-targeted prototype**. M06 added genuine **original Vitis HLS + AMD interconnect Vivado simulation** for bounded canonical-state paging, neural/state parity, AXI fault quarantine, and explicit simulated 64 KiB image restoration with output publication only after clean commit. See the [M05 acceptance](v1/docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md) and [M06 evidence-backed acceptance](v1/docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md).

**Not yet verified in this v1 program:** actual KV260 fabric execution, physical PS DDR access and ownership, physical DMA bandwidth and latency, deployed full-system resource/timing figures, automatic durable rollback, or an acceleration/energy claim. Those require future explicitly gated hardware studies.

## Development conventions

Start work on a new branch from the latest accepted 'main'. Keep design source, executable tests, acceptance reports and experiment plans in Git, while preserving original tool outputs and vendor/board evidence under **~/Thesis_Evidence/** outside the checkout. Verify changes locally and through no-board CI; do not merge without the requested user review. The official MNIST TEST split remains sealed unless separately authorized.

No previously frozen v3 firmware, 27-logical-core mapping, or hardware test workflow becomes part of v1 automatically. JTAG and physical DDR operations require new operator approval and safety preflight, not instructions from an archived document.

**Historical development logs are preserved** in version history at [the pre-cleanup revision](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/README.md); the active README intentionally shows only the latest accepted state.
