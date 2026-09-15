# MNIST-12 — Catalyst N1 Matched Hardware Comparison

**Status:** Planned

## Goal

MNIST-12 extends the matched comparison from a Loihi emulator to an **independent Loihi-class neuromorphic processor implementation** that can itself be built on a Kria-class FPGA.

The first target is **Catalyst N1**, not because Catalyst is Intel Loihi, but because it provides an independently developed digital neuromorphic architecture with:

- current-based LIF neurons;
- fixed-point state/weights;
- sparse/event-driven execution;
- an open Python SDK/reference simulator;
- open Verilog RTL;
- an explicit Kria K26 FPGA target; and
- a relatively simple N1 neuron model compared with later Catalyst generations.

The main research question is:

> How does the same frozen native-sparse MNIST graph behave when translated onto an independently designed Loihi-class architecture, and—if a faithful mapping is possible—how do functional behavior and on-device execution characteristics compare when both designs are implemented on K26-class FPGA hardware?

This experiment must distinguish **matched workload** from **matched dynamics**. The same graph/inputs can be deployed even if Catalyst's LIF arithmetic is not identical to FPGA-v1, but any semantic difference must remain explicit.

## External source / provenance

Primary project references at planning time:

- Catalyst N1 repository: https://github.com/catalyst-neuromorphic/catalyst-n1
- Catalyst Neurocore overview: https://github.com/catalyst-neuromorphic/catalyst-neurocore
- Catalyst benchmark repository: https://github.com/catalyst-neuromorphic/catalyst-benchmarks

The N1 repository currently describes a parameterized Verilog processor with a Python SDK and a Kria K26 target. Its published K26 configuration is two cores with 256 neurons/core. The repository is Apache-2.0 licensed.

Because Catalyst is a new and rapidly changing 2026 project, MNIST-12 must pin an exact upstream commit and verify every relevant capability locally rather than treating website/README claims as experimental evidence.

Catalyst is **not Intel Loihi**. Results belong in the thesis as an independent Loihi-class hardware comparison, not as a substitute for a real Loihi measurement.

---

## Frozen comparison contract

The primary workload remains the accepted `native-sparse` deployment from `mnist-v1`:

```text
input image:             original 28x28 MNIST
input axons:             784
output neurons:          10
stored connections:      4,086
presentation:            16 ticks
input schedule:          exact existing deterministic encoder output
recurrent routes:        none
readout:                 spike counts, lowest-ID tie break
training:                no retraining in the primary matched experiment
```

The desired hierarchy is:

```text
same image
  -> same 16-tick host event schedule
  -> same source/target connectivity graph
  -> same accepted effective signed weights where representable
  -> target-native deterministic parameter translation
  -> same spike-count decoder
```

If Catalyst cannot represent the exact FPGA-v1 neuron dynamics or weight scaling, the experiment must separate:

1. **graph/input matched** results; and
2. **dynamics matched** results, if exact/equivalent dynamics are achievable.

Do not retrain first and then call the result a matched architecture comparison.

---

## MNIST-12.1 — Upstream freeze and K26 feasibility audit

Before touching the MNIST adapter:

1. pin the exact Catalyst N1 repository commit;
2. record license and dependency versions;
3. run the upstream software regression suite;
4. inspect the N1 SDK network/deployment format;
5. inspect the Kria build target and target-part/board assumptions;
6. verify that the user's exact K26/Vivado 2025.2 environment can build or can be adapted without changing N1 computational behavior;
7. audit per-core neuron, synapse, routing, event-buffer, and host-injection capacities against the frozen MNIST workload.

Do not assume that the upstream label “Kria K26” guarantees drop-in compatibility with the exact board files/part string used by this thesis. The upstream target must be reproduced locally.

Capacity questions that must be answered explicitly:

- Do 784 input axon identifiers require physical neuron slots or only event addresses?
- Can 4,086 connections fit the N1 memory organization without pruning?
- Can all ten output neurons remain on one core?
- If two cores are required, does partitioning alter timing or event semantics?
- Can a 16-tick externally supplied schedule be injected deterministically without host timing affecting algorithmic timing?

**Acceptance gate:** upstream N1 software tests pass and there is a documented deployment plan for the exact frozen network, or a documented capacity blocker.

---

## MNIST-12.2 — Catalyst semantic mapping audit

Build a mapping table parallel to MNIST-11. At minimum classify:

- membrane/current representation;
- leak/decay representation;
- threshold and comparison rule;
- reset behavior;
- refractory behavior;
- signed weight range/scaling;
- accumulation width/saturation;
- event delivery timing;
- neuron update schedule;
- tick boundary;
- state initialization;
- spike readout timing.

Use the same labels:

```text
EXACT
EQUIVALENT
TRANSLATED
UNREPRESENTABLE
NOT_USED
```

The comparison must identify which differences come from FPGA-v1 vs Loihi-like semantics and which are Catalyst-specific architecture choices.

**Acceptance gate:** deterministic conversion from `mnist-v1` to Catalyst parameters is defined, with every lossy/approximate field labeled.

---

## MNIST-12.3 — Catalyst CPU/reference-backend matched experiment

Use Catalyst's own CPU/reference SDK backend before using its RTL.

Replay:

1. the directed arithmetic cases from MNIST-11 where applicable;
2. the existing 30-image frozen corpus; and
3. the full 10,000-image test set if the adapter is stable.

Compare against both:

- FPGA-v1 Python golden; and
- Brian2Loihi result from MNIST-11.

Required outputs:

- prediction agreement;
- spike-count-vector agreement;
- per-tick output spikes;
- state traces where the SDK exposes equivalent state;
- first-divergence classification;
- accuracy under the unchanged frozen network.

CPU wall time is a software implementation metric only and is not compared to FPGA architectural latency.

**Acceptance gate:** the target-native software behavior of the exact translated graph is reproducible and understood before physical deployment.

---

## MNIST-12.4 — Physical Catalyst N1 deployment on K26

Build the pinned Catalyst N1 hardware image for the user's K26 and deploy the same translated native-sparse network.

The hardware experiment should begin with the same indices used for FPGA-v1 runtime/timing acceptance:

```text
MNIST index 3, label 0
MNIST index 1, label 2
```

Then expand to the 30-image frozen conformance corpus if stable.

For each physical case record:

- exact input schedule identity/hash;
- translated network/deployment hash;
- final spike-count vector;
- decoded prediction;
- agreement against Catalyst CPU reference;
- agreement against FPGA-v1 golden;
- algorithmic tick count;
- on-device cycle/timing boundary, if exposed or instrumentable;
- faults/dropped events/queue overflow status.

The primary correctness rule is Catalyst hardware versus Catalyst's own CPU/reference model. FPGA-v1 agreement is a cross-architecture result and may legitimately differ if the semantic audit identified target-native dynamics differences.

**Acceptance gate:** at least the two runtime anchor images execute physically with no transport/core faults and match the pinned Catalyst software reference. Expand to the 30-image corpus if practical.

---

## MNIST-12.5 — Same-K26 implementation characterization

If the Catalyst build exposes a defensible hardware timing boundary, collect a same-device-family comparison against FPGA-v1.

Record from locally generated Vivado reports rather than copying upstream tables:

```text
LUT
FF/registers
BRAM/URAM
DSP
WNS / achieved frequency
processor/core count used
static network memory footprint
```

For latency, define both designs' boundaries explicitly and exclude host/JTAG/UART/PCIe transport unless both measurements deliberately include equivalent transport.

A latency ratio is only admissible if:

1. graph/input presentation is matched;
2. the number of algorithmic ticks is matched;
3. measurement boundaries are equivalent; and
4. semantic differences are stated beside the ratio.

### Energy policy

Do not compare board TDP or Vivado estimated power to measured energy/inference. If Catalyst only provides an implementation power estimate, record it as an **estimate** and do not convert it into a headline energy advantage unless the same method/boundary is applied to FPGA-v1.

---

## MNIST-12.6 — Final matched comparison matrix

The final thesis-facing table should distinguish at least these execution targets:

| Target | Role |
| --- | --- |
| FPGA-v1 Python golden | project semantic authority |
| FPGA-v1 physical K26 | project hardware implementation |
| Brian2Loihi | published Loihi-1 software emulator/reference |
| Catalyst N1 CPU backend | independent architecture software reference |
| Catalyst N1 physical K26 | independent Loihi-class FPGA implementation |
| Published Intel Loihi/NxTF | external literature context only |

Comparison columns should include:

- source image/dataset;
- graph/topology identity;
- weight identity/translation status;
- neuron-dynamics mapping status;
- ticks;
- prediction accuracy;
- prediction agreement with FPGA-v1;
- spike/state agreement level;
- hardware timing boundary and latency, where valid;
- resources, where locally measured;
- energy status (`measured`, `estimated`, or `not measured`);
- evidence class.

The table should explicitly distinguish:

```text
MATCHED GRAPH + MATCHED DYNAMICS
MATCHED GRAPH + TRANSLATED DYNAMICS
UNMATCHED LITERATURE REFERENCE
```

This prevents the earlier loose Loihi comparison from being confused with the stronger experiments introduced by MNIST-11/12.

---

## MNIST-12 completion criterion

MNIST-12 is complete when:

1. an exact Catalyst N1 revision/environment is frozen;
2. capacity and semantic mapping are documented;
3. the frozen native-sparse graph is executed through the Catalyst software reference without retraining;
4. the translated graph is run on physical Catalyst N1 FPGA hardware if the K26 path is feasible;
5. software/hardware Catalyst agreement is measured;
6. FPGA-v1/Brian2Loihi/Catalyst results are assembled under one explicit comparison contract; and
7. no performance ratio is claimed across incompatible timing/workload boundaries.

A documented K26 capacity/toolchain blocker may close the feasibility portion but does **not** count as a physical comparison result.

---

## Follow-on decision: actual Intel Loihi / Lava

MNIST-11 and MNIST-12 still do not constitute a direct experiment on Intel Loihi silicon:

- Brian2Loihi emulates Loihi-1 in software.
- Catalyst is an independent Loihi-class architecture.

Intel currently positions **Lava** as the open-source software framework associated with Loihi 2. If authenticated Loihi-2 hardware/cloud access becomes available, the natural follow-on is a separate milestone to port the same frozen comparison contract into Lava/Loihi 2.

That follow-on should be created only once actual hardware/access constraints are known; it should not be silently folded into MNIST-12.
