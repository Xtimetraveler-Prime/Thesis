# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the source-backed Loihi-1 architectural digital twin.

Development authority is split between:

- `LOIHI_TWIN_ROADMAP.md` — the phase/deliverable and acceptance tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — the normative source-backed architecture contract.

FPGA-v1 remains frozen under `../v1/`. No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts them.

## Current status — P00-P08 complete

All planned FPGA-v2 development phases **P00 through P08 are complete** as of 2026-09-30.

P08 closed after independent reproduction of the final P08.5.3 closure gate:

```text
19 tests passed
P08.5.1 ledger fingerprint:
574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d

P08.5.2 report fingerprint:
d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0

P08.5.3 closure fingerprint:
135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce
```

Final P08 application measurements are:

```text
ANN validation accuracy:      0.992600
SNN validation accuracy:      0.984400
ANN official-test accuracy:   0.987400
SNN official-test accuracy:   0.982400
ANN-SNN official-test delta:  0.005000
primary SNN horizon:          100 timesteps
```

The accepted source-bounded reconstructed network contains:

```text
neurons:                 4,218
trainable parameters:    7,006
expanded connections: 338,880
logical cores:               5
resident K26 contexts:       3
physical HLS engines:        1
```

P08.4.2 proved complete 100-timestep paging-order invariance for the representative official-test frame. P08.4.3a routed the corresponding host-paged K26 shell at 100 MHz with positive setup/hold slack and 47 URAMs. P08.4.3b then physically paged a frozen logical-core-4 MNIST snapshot into resident slot 0 and reproduced all 618 compartment states/traces and the final ten-value output evidence exactly.

The final comparison against the published NxTF result is deliberately bounded. The accepted reconstruction is close in reported network scale but is not the unrecovered exact paper topology/checkpoint. Native-Loihi energy/latency, NxTF shared-weight accounting, and NxTF neurocore count are therefore not converted into direct FPGA efficiency ratios.

Final closure records are:

```text
docs/P08_4_ACCEPTANCE.md
docs/P08_5_1_ACCEPTANCE.md
docs/P08_5_2_ACCEPTANCE.md
docs/P08_5_3_ACCEPTANCE.md
```

## Core v2 implementation

The independent Python architecture package lives under:

```text
src/loihi_twin_v2/
```

The accepted hardware path spans the P03 one-core engine, P04 routed/barrier shell, P05 resident-context virtualization, P06 deterministic compiler/deployment format, and P08 host-paged controller/shell additions. Historical implementation and acceptance details are retained in the roadmap and phase-specific documents under `docs/`.

Install and run the general v2 software tests from this directory with:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Resource-accounting and fidelity boundary

The logical synapse-memory model (`v2-simple-32bit-entry`) is a documented project accounting choice, not a claim of exact Loihi SRAM bit packing. Logical Loihi-like occupancy and physical FPGA BRAM/URAM/LUT/register/DSP utilization are reported separately throughout the project.

The project is a source-backed architectural digital twin. It does not claim transistor-level or physical asynchronous-circuit equivalence, native-Loihi timing/energy equivalence, or bit-for-bit proprietary NxSDK/NxTF micro-encoding equivalence.

Future work may extend fidelity or add new experiments, but those are follow-on studies rather than unfinished P00-P08 development phases.
