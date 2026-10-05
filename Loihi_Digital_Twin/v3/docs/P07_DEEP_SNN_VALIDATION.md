# P07 Deeper Mapped SNN Validation

## Purpose

P07 validates that the v2 architecture can execute a deeper feed-forward spiking
network through the complete source-controlled flow established by P06:

```text
high-level network specification
        -> deterministic P06 compiler
        -> versioned compiled deployment
        -> Python logical execution
        -> P05 full-context FPGA export
        -> physical K26 execution
```

P07 does not introduce a new FPGA compute datapath. It stresses the accepted
mapper/compiler, logical routing/barrier semantics, connection sharing, and the
one-engine/three-context virtualized K26 shell with a deeper graph than the P06
three-layer compiler demonstration.

## Canonical workload

The canonical workload is defined once in:

```text
src/loihi_twin_v2/workload_p07.py
```

It contains:

- one four-channel external input population named `pixels`;
- six feed-forward neuron populations `layer0` through `layer5`;
- two neurons per layer;
- 12 mapped neurons total; and
- dense 2x2 weighted connectivity between each adjacent layer.

Every neuron uses the accepted P03-compatible arithmetic/configuration profile
through the P06 compiler. Each connection weight is 6 and each neuron threshold
is 5, so a valid input spike produces a deterministic wave through the six
layers.

## Deterministic mapping target

P07 compiles with:

```text
compartments_per_core = 4
```

This is a mapper packing policy, not a reduction of the logical core capacity.
The resulting deterministic placement is:

| Logical core | Compartments | Populations |
|---:|---:|---|
| 0 | 0-1 | layer0 |
| 0 | 2-3 | layer1 |
| 1 | 0-1 | layer2 |
| 1 | 2-3 | layer3 |
| 2 | 0-1 | layer4 |
| 2 | 2-3 | layer5 |

The five neural stage transitions therefore alternate between local and remote
transport:

```text
layer0 -> layer1   local on core 0
layer1 -> layer2   remote core 0 -> core 1
layer2 -> layer3   local on core 1
layer3 -> layer4   remote core 1 -> core 2
layer4 -> layer5   local on core 2
```

This explicitly validates both intra-core and inter-core propagation within one
deeper feed-forward graph.

## Connection sharing

All external and inter-layer fanout groups use the same normalized two-entry
weighted pattern:

```text
offset 0 -> weight 6
offset 1 -> weight 6
```

The P06 compiler keys reusable synapse templates by normalized destination-core
pattern, independent of whether the source is external or another mapped neuron.
Therefore the canonical P07 workload is expected to produce:

```text
expanded_connections         28
stored_shared_parameters      6
expanded_per_stored_parameter 28 / 6 ~= 4.667
```

The 28 expanded connections consist of eight external input connections plus 20
adjacent-layer neural connections. Each of the three destination cores retains
one shared two-entry template for its local fanout pattern.

This is a project-defined sharing abstraction. It demonstrates deterministic
parameter reuse and resource accounting; it is not a claim of native Loihi SRAM
encoding or compression ratio.

## Static traffic profile

The mapped neural graph contains ten source output-route entries at the packet
boundary:

```text
total  = 10
local  =  6
remote =  4
```

The external input population contributes four ingress routes and is reported
separately from neural output-route traffic.

## Expected spike wave

For one active input channel at timestep 0, the normalized spike wave is:

| Timestep | Logical core | Spiking compartments | Layer |
|---:|---:|---|---|
| 0 | 0 | 0, 1 | layer0 |
| 1 | 0 | 2, 3 | layer1 |
| 2 | 1 | 0, 1 | layer2 |
| 3 | 1 | 2, 3 | layer3 |
| 4 | 2 | 0, 1 | layer4 |
| 5 | 2 | 2, 3 | layer5 |
| 6 | — | none | quiescent |

The physical corpus runs three input cases:

```text
pixel0          = input 0
pixel0_pixel2   = inputs 0 and 2
all_pixels      = inputs 0, 1, 2 and 3
```

Each scenario is executed under forward and reverse legal logical-context
service order for seven algorithmic timesteps, for 42 directed physical ticks.

## Capacity-failure probe

The same canonical network is intentionally compiled under a stricter mapper
policy:

```text
compartments_per_core = 4
max_logical_cores = 2
```

Twelve neurons require three logical cores at four compartments/core, so this
must fail with:

```text
code     = logical_core_capacity
required = 3
limit    = 2
```

The expected rejection is written into the P07 analysis/evidence artifacts. This
shows that successful virtualization does not allow a mapping policy or hard
logical limit to be silently bypassed.

## Physical implementation boundary

P07 reuses the accepted P05/P06 physical shell:

```text
3 full logical contexts
1 physical HLS compute engine
47 / 64 URAM288
2 / 144 BRAM tiles
100 MHz requested PL clock
P05 routed WNS +0.588 ns
P05 routed WHS +0.011 ns
```

No new RTL/HLS architecture is introduced for P07. Reusing the accepted shell
isolates the question being tested: whether a deeper compiler-generated mapped
network behaves correctly on the existing architecture.

The P07 runner reuses `hardware/p06_physical_conformance.tcl` as the low-level
Hardware Manager checker. P07 supplies a new deeper physical-vector corpus and
wraps the accepted raw harness result in the phase-specific schema:

```text
p07-deep-mapped-snn-v1
```

The final P07 result records workload depth, logical/physical counts, sharing
metrics, the expected capacity rejection, source/deployment fingerprints, all
physical tick records, and the final PASS/FAIL result.

## Completion evidence expected

P07 can close when all of the following are true:

1. the canonical six-layer network maps deterministically to three logical cores;
2. the compiler reports the expected occupancy, sharing, and local/remote route profile;
3. the expected two-core capacity probe is rejected explicitly;
4. Python execution produces the six-layer wave under legal service-order changes;
5. the same compiled deployment is exported to the accepted FPGA context format;
6. all three input scenarios agree between Python expectations and physical K26 execution under both service orders; and
7. the physical result preserves the compiled deployment fingerprint and reports `result=PASS`.
