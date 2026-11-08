# Neuromorphic Accelerator — Research Workspace

This top-level directory houses the **new, independently versioned research program** arising from the Loihi-inspired FPGA digital-twin work. The umbrella name `Neuromorphic_Accelerator` is provisional and deliberately broad enough to include architectural exploration, virtualization experiments, and hardware/software co-design even if a strict accelerator is not the eventual final contribution.

- [`v1/`](v1/) — **first-generation new architecture**, currently in design and experimental-planning phase; not `Loihi_Digital_Twin/v4`.
- [Previous verified Loihi-inspired work](../Loihi_Digital_Twin/v3/) — preserved historical results, implementation and independently accepted physical evidence; it is **not** moved or renamed.
- [Root research questions and potential contributions](../README.md).
- [Research literature and novelty boundary](../LitReview.md).

**Project status:** New folder and conceptual notes only; there is NO new tested neuron engine, RTL, bitstream, throughput, power result or approved physical JTAG procedure. No old v3 firmware or fixed 27-core mapping is automatically imported into v1.

For code changes, develop in a new branch from current `main`; use native no-board regressions and explicit evidence/CI checks before requesting separately authorized FPGA measurements. Preserve old evidence, source hashes and official MNIST TEST seal.
