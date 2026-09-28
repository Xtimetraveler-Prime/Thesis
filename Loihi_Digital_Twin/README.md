# Loihi Digital Twin

This directory contains the versioned architecture implementations for the thesis.

- `v1/` is the preserved FPGA-v1 architecture and verification tree. Its computational behavior remains the historical control associated with the `fpga-v1-mnist-v1-final` preservation point. The completed M1-M13 development record is kept in `v1/MILESTONES.md`.
- `v2/` is the active source-backed Loihi-1 architectural digital-twin development tree. Current objectives and development sequencing are maintained in `v2/LOIHI_TWIN_ROADMAP.md`, while `v2/docs/LOIHI1_TARGET_SPEC.md` is the normative architecture contract.

The repository retains a compatibility symlink named `Neuromorphic Digital Twin` that points to `Loihi_Digital_Twin/v1`. New work and documentation should use the canonical `Loihi_Digital_Twin/...` paths. The alias exists so historical v1 commands and application scripts do not break solely because of this organizational migration.

FPGA-v2 must be developed independently of v1: new models, mapping logic, tests, RTL/HLS, and documentation belong under `v2/` rather than modifying the preserved v1 implementation in place.
