# Loihi Digital Twin

This directory contains the versioned architecture implementations for the thesis.

- `v1/` is the preserved FPGA-v1 architecture and verification tree. Its computational behavior remains the historical control associated with the `fpga-v1-mnist-v1-final` preservation point.
- `v2/` is reserved for the source-backed Loihi-1 architectural digital twin developed after the FPGA-v1 preservation phase.

The repository currently retains a compatibility symlink named `Neuromorphic Digital Twin` that points to `Loihi_Digital_Twin/v1`. New work and documentation should use the canonical `Loihi_Digital_Twin/...` paths. The alias exists so historical v1 commands and application scripts do not break solely because of this organizational migration.

FPGA-v2 must be developed independently of v1: new models, mapping logic, tests, RTL/HLS, and documentation belong under `v2/` rather than modifying the preserved v1 implementation in place.
