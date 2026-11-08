# Neuromorphic Accelerator — Research Workspace

This top-level directory houses the **new, independently versioned research program** arising from the Loihi-inspired FPGA digital-twin work. The umbrella name `Neuromorphic_Accelerator` is provisional and deliberately broad enough to include architectural exploration, virtualization experiments, and hardware/software co-design even if a strict accelerator is not the eventual final contribution.

- [`v1/`](v1/) — **first-generation new architecture**, currently in design and experimental-planning phase; not `Loihi_Digital_Twin/v4`. See the [v1 development roadmap](v1/roadmap.md) and [open architecture design questions](v1/docs/ARCHITECTURE_DESIGN_QUESTIONS.md).
- [Previous verified Loihi-inspired work](../Loihi_Digital_Twin/v3/) — preserved historical results, implementation and independently accepted physical evidence; it is **not** moved or renamed.
- [Root research questions and potential contributions](../README.md).
- [Research literature and novelty boundary](../LitReview.md).

**Project status:** M01 **PC-only architectural trade study is complete and user-accepted**; M02 **initial PC-only neural-reference behavior is accepted by user**; M03 **analytical workload and traffic experimentation is active, not yet user-accepted**, with no selected hardware architecture. There is NO new implemented LIF evaluation engine, verified SNN inference, RTL, bitstream, physical throughput/power result or approved physical JTAG procedure. [Accepted M01 decision memo](v1/docs/M01_ARCHITECTURE_OPTIONS.md); [current M03 matched workload/measurement contract](v1/docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md) and [native no-board verification](v1/docs/M03_PC_ONLY_VERIFICATION.md). No old v3 firmware or fixed 27-core mapping is automatically imported into v1.

For code changes, develop in a new branch from current `main`; use native no-board regressions and explicit evidence/CI checks before requesting separately authorized FPGA measurements. Preserve old evidence, source hashes and official MNIST TEST seal.
