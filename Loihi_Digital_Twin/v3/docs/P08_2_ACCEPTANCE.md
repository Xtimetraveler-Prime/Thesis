# P08.2 Acceptance Record — Context Paging and FPGA-v2 Adaptation

**Status:** Accepted  
**Accepted:** 2026-09-30  
**Branch:** `agent/p08.2-context-paging`  
**Accepted topology:** P08.1 `14 -> 20 -> 12 -> 10` all-convolutional reconstruction

## Accepted result

P08.2 proves that the accepted P08.1 workload does not need to be reduced to fit
the K26's three retained P05 context slots. The frozen structural graph compiles
through P06 to five logical cores, while the physical implementation boundary
remains three resident context slots serviced by one HLS compute engine.

```text
P06 logical cores / backing contexts: 5
K26 resident context slots:           3
physical HLS compute engines:         1
logical capacity changed:             no
```

The accepted paging layer preserves logical-core identity independently from
resident slot identity, saves/restores architectural state around evictions,
keeps current/next event semantics explicit, routes packets by logical
destination ID even when the destination is nonresident, and leaves the global
algorithmic barrier above physical page residency.

## Verification evidence

The P08.2 software contract includes directed tests for:

- five logical backing contexts over three resident slots;
- preservation of the exact P06 resource footprint from P08.1;
- legal routes to nonresident logical destinations;
- deterministic page hit/load/eviction accounting;
- state preservation across eviction and reload;
- normalized-trace invariance across legal service, paging, and packet-drain
  order; and
- rejection of the same five-core deployment by the legacy all-resident P05/P06
  hardware-image path.

The P08 RTL dispatch primitive was locally verified on 2026-09-30 with Vivado
2025.2. The accepted simulation emitted:

```text
PASS: p08_paged_dispatch_controller
P08 paged dispatch controller simulation gate completed successfully.
```

The directed RTL test includes logical core 4 executing through resident physical
slot 2, metadata/timestep/event-bank preservation, host/compute exclusion,
completion accounting, metadata rejection, packet-overflow reporting, and
nonzero HLS-status reporting.

The first version of this RTL testbench exposed a simulation race in its stimulus
and sampling sequence. The testbench was corrected to use the same race-resistant
clocking style as the accepted P05 directed simulation. The corrected test passes
cleanly; the controller implementation did not need to be weakened to satisfy the
test.

## NxTF 14-core versus P06 5-core comparison boundary

The NxTF paper reports **14 Loihi neurocores** for its frame-based MNIST mapping.
The accepted P08 reconstruction maps to **5 project logical cores** under P06.
These counts are intentionally retained as different results rather than forced
to match.

The five P06 logical cores are Loihi-like at the main architectural capacity
boundary: the project enforces 1,024 compartments, 4,096 input axon IDs, 4,096
output-route slots, and a 128 KiB modeled synaptic storage budget per logical
core. However, P06 is not the NxTF compiler and the project's synapse-storage
model is not native Loihi SRAM packing. P06 currently uses a deterministic
first-fit style placement with project-defined shared-template accounting,
whereas NxTF performs convolution-aware partitioning subject to neuron, axon,
synapse, sharing, and partition-shape constraints.

Therefore the accepted comparison is:

```text
NxTF paper mapping:                 14 Loihi neurocores
P08 reconstructed topology:        4,218 neurons
P08/P06 project mapping:            5 logical cores
P08 K26 resident contexts:          3
P08 K26 physical compute engines:   1
```

The 5-versus-14 difference is a documented mapping/model discrepancy, not an
accuracy claim and not evidence that five real Loihi cores would reproduce the
published NxTF placement. Likely contributors include the reconstructed rather
than recovered-exact topology, different convolution partitioning policy,
different axon/sharing representation, and different synaptic storage/compression
accounting.

P08 will report both numbers in the final comparison. It will not artificially
force P06 to use 14 cores merely to reproduce the paper's count, because doing so
would create agreement for the wrong architectural reason.

## Acceptance boundary

P08.2 is accepted as the FPGA-v2 execution adaptation for the current reconstructed
workload. This acceptance establishes that workloads larger than the resident
three-context shell can be serviced without changing their logical graph.

It does **not** claim:

- NxTF-equivalent partitioning;
- native Loihi synapse-memory packing;
- final trained MNIST accuracy;
- physical K26 execution of the trained MNIST deployment; or
- direct energy/latency equivalence with native Loihi.

Those remaining questions belong to P08.3-P08.5.

## Next gate

P08.3 may now begin. Before training starts, freeze the ANN training and ANN-to-SNN
conversion policy using source evidence plus explicit project reconstruction
choices. The official 10,000-image MNIST test split remains locked until the
training, checkpoint-selection, conversion, quantization, threshold, timestep,
and decoder policies are frozen without test-set feedback.
