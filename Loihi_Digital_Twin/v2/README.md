# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the source-backed Loihi-1 architectural digital twin.

Development authority is split between:

- `LOIHI_TWIN_ROADMAP.md` — the active phase/deliverable tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — the normative source-backed architecture contract.

FPGA-v1 remains frozen under `../v1/`. No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts them.

## Current status — P08.4 official-test evaluation

P00-P07 are complete. P08 is the active application/comparison phase for the reconstructed NxTF frame-based MNIST workload.

Accepted P08 foundations now include:

- **P08.1:** source-bounded four-convolution reconstruction with 4,218 neurons, 7,006 trainable parameters, and 338,880 expanded convolutional connections;
- **P08.2:** deterministic paging of the five-logical-core P06 deployment over three resident K26 contexts and one physical HLS engine;
- **P08.3:** frozen ANN checkpoint plus source-recovered ANN-to-SNN conversion, followed by a 5,000-example validation measurement at the primary 100-timestep horizon.

The accepted P08.3 validation result is:

```text
ANN validation accuracy: 0.992600
SNN validation accuracy: 0.984400
ANN-SNN delta:           0.008200
```

P08.4 is now allowed to evaluate the untouched 10,000-image official MNIST test split. The accepted ANN checkpoint, integer conversion, thresholds, readout behavior, topology, and primary 100-timestep horizon are frozen and must not be changed in response to test performance.

The current gate is documented in:

```text
docs/P08_4_1_OFFICIAL_TEST_GATE.md
```

and can be run from the dedicated P08 environment with:

```bash
bash scripts/run_p08_4_1_official_test_evaluation.sh
```

## Core v2 implementation

The independent Python architecture package lives under:

```text
src/loihi_twin_v2/
```

The accepted hardware path spans the P03 one-core engine, P04 routed/barrier shell, P05 resident-context virtualization, P06 deterministic compiler/deployment format, and P08 paging/controller additions. Historical implementation and acceptance details are retained in the roadmap and phase-specific documents under `docs/`.

Install and run the general v2 software tests from this directory with:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Resource-accounting boundary

The logical synapse-memory model (`v2-simple-32bit-entry`) is a documented project accounting choice, not a claim of exact Loihi SRAM bit packing. Logical Loihi-like occupancy and physical FPGA BRAM/URAM/LUT/register/DSP utilization are reported separately throughout the project.

The project is a source-backed architectural digital twin. It does not claim transistor-level, asynchronous-circuit, native-Loihi timing, or bit-for-bit proprietary NxSDK/NxTF micro-encoding equivalence.
