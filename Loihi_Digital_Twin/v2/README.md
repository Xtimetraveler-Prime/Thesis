# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the source-backed Loihi-1 architectural digital twin.

Development authority is split between:

- `LOIHI_TWIN_ROADMAP.md` — the active phase/deliverable tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — the normative source-backed architecture contract.

FPGA-v1 remains frozen under `../v1/`. No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts them.

## Current status — P08.5 final NxTF comparison

P00-P07 are complete. P08.1-P08.4 are now accepted for the reconstructed NxTF frame-based MNIST workload; P08.5 is the active final comparison/closure phase.

Accepted P08 foundations are:

- **P08.1:** source-bounded four-convolution reconstruction with 4,218 neurons, 7,006 trainable parameters, and 338,880 expanded convolutional connections;
- **P08.2:** deterministic paging of the five-logical-core P06 deployment over three resident K26 contexts and one physical HLS engine;
- **P08.3:** frozen ANN checkpoint plus source-recovered ANN-to-SNN conversion and 5,000-example validation at the primary 100-timestep horizon;
- **P08.4:** official-test evaluation, exact compiled paging conformance, routed host-paged K26 shell, and representative physical MNIST deep-dispatch conformance.

Accepted application measurements are:

```text
ANN validation accuracy: 0.992600
SNN validation accuracy: 0.984400
ANN official-test accuracy: 0.987400
SNN official-test accuracy: 0.982400
ANN-SNN official-test delta: 0.005000
primary SNN horizon: 100 timesteps
```

The accepted converted deployment is:

```text
logical cores:       5
resident contexts:   3
physical engines:    1
compiled fingerprint: 5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

P08.4.2 proved complete 100-timestep paging-order invariance for the representative official-test frame. P08.4.3a routed the corresponding host-paged K26 shell at 100 MHz with positive setup/hold slack and 47 URAMs. P08.4.3b then physically paged a frozen logical-core-4 MNIST snapshot into resident slot 0 and reproduced all 618 compartment states/traces and the final ten-value output evidence exactly.

The physical acceptance boundary is intentionally narrow: the project does not claim that the entire 100-timestep representative inference was replayed through JTAG. Complete paging semantics are covered by P08.4.2; physical conformance is demonstrated by the representative deep-network page replacement and dispatch in P08.4.3b.

P08.4 closure is recorded in:

```text
docs/P08_4_ACCEPTANCE.md
docs/P08_4_3B_ACCEPTANCE.md
```

P08.5 now builds the final bounded comparison against the published NxTF/Loihi result. It must keep sourced/directly comparable quantities separate from project reconstruction, FPGA-specific implementation measurements, and non-comparable quantities such as native-Loihi energy/latency where the measurement boundary is not equivalent.

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
