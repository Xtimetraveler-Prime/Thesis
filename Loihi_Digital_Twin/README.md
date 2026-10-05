# Loihi Digital Twin

This directory contains the versioned architecture implementations for the thesis.

- `v1/` is the preserved FPGA-v1 architecture and verification tree. Its computational behavior remains the historical control associated with the `fpga-v1-mnist-v1-final` preservation point. The completed M1-M13 development record is kept in `v1/MILESTONES.md`.
- `v2/` is the completed source-backed Loihi-1 architectural digital-twin baseline. All planned v2 phases P00-P08 are accepted; its final development/acceptance record is in `v2/LOIHI_TWIN_ROADMAP.md`, with `v2/docs/LOIHI1_TARGET_SPEC.md` as the normative architecture contract.
- `v3/` is the active follow-on development tree. It begins from the accepted v2 implementation and targets KV260/K26-local DDR-backed virtualization, board-local PS/PL execution control, stronger physical regression/application testing, a better-specified published MNIST benchmark, and latency/power/energy characterization. Current sequencing is in `v3/LOIHI_TWIN_ROADMAP.md`.

The repository retains a compatibility symlink named `Neuromorphic Digital Twin` that points to `Loihi_Digital_Twin/v1`. New work and documentation should use the canonical `Loihi_Digital_Twin/...` paths. The alias exists so historical v1 commands and application scripts do not break solely because of this organizational migration.

Accepted v1/v2 evidence must remain preserved. New v3 work belongs under `v3/` and must not silently rewrite prior acceptance records or retroactively change v2 claims.
