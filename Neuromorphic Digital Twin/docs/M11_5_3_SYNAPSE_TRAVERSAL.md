# M11.5.3 — M08 Synapse Traversal and Exact Accumulation

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-5-core-integration`

## Goal

Replace the testbench-preloaded signed-64 accumulators used by M11.5.2 with a
real FPGA Phase-B path that consumes the frozen M08.5 weight image and produces
the exact accumulator image required by M10 before neuron updates begin.

The completed data path is:

```text
external events, then recurrent events
              |
              v
       axon-row CSR memory
              |
              v
       32-bit synapse word
       + 16-bit format word
              |
              v
   reconstruct M08 effective weight
              |
              v
 signed-64 accumulator[target_neuron]
              |
              v
   M11.5.2 Phase-C controller
              |
              v
 real packaged neuron_step_v1 IP
```

M11.5.3 does not redefine M08 weight semantics. Hardware consumes the frozen
M08 representation directly:

```text
weight_formats.mem     16-bit shared format words
weight_synapses.mem    32-bit requested-mantissa/format/target words
weight_axon_rows.mem   32-bit CSR row pointers
```

and reconstructs the same effective integer produced by
`encode_static_weight()`.

## Frozen Phase-B ordering

The implementation preserves the M10 ordering contract even though the final
mathematical sum is commutative:

1. clear all configured-neuron accumulators;
2. consume external event entries in ascending buffer index;
3. consume recurrent event entries in ascending buffer index;
4. for each event, traverse its CSR synapse row from start to terminal pointer;
5. preserve repeated events and repeated synapse records;
6. add each reconstructed effective weight to the target neuron's signed-64
   accumulator;
7. do not saturate or wrap the accumulator.

A physically valid axon ID with no configured row is a no-op. An axon outside
the 1,024-row physical profile is a deterministic fault.

## M08 effective-weight reconstruction

For one packed synapse:

```text
requested mantissa = signed synapse_word[8:0]
format index       = synapse_word[12:9]
target neuron      = synapse_word[28:13]
```

The referenced 16-bit format supplies:

```text
exponent        = signed format_word[3:0]
num_weight_bits = format_word[7:4]
sign mode       = format_word[9:8]
```

`m08_weight_decoder_v1.sv` implements the frozen M08 encoder contract:

1. validate sign-mode mantissa bounds and reserved fields;
2. derive the precision shift;
3. truncate the requested mantissa toward zero to the configured precision;
4. apply the signed exponent;
5. apply the fixed six-bit weight alignment;
6. clip only the effective static weight to `[-2,097,088, +2,097,088]`;
7. add the resulting integer to the signed-64 target accumulator.

For negative exponents, an arithmetic right shift is used because the M08
contract uses floor division for negative aligned values. A logical shift or
round-toward-zero division would not be equivalent.

## Capacity guards

M11.5.3 uses the M11.5.1 profile:

```text
neurons                 <= 256
axon rows               <= 1024
synapses                <= 4096
weight formats          <= 16
external events/tick    <= 4096
recurrent events/tick   <= 4096
accumulator width       = signed 64 bits
```

The M11.5.1 physical-capacity proof bounds the worst possible absolute
mathematical sum below `2^46`, so signed-64 is sufficient for every legal image
and event set. Software and RTL nevertheless retain an explicit overflow guard
so a violated assumption cannot silently wrap.

## How the milestone was met

M11.5.3 was closed in four progressively stronger verification layers rather
than jumping directly from a hand-authored RTL walker to the full core.

### M11.5.3.1 — packed-memory software oracle

`src/neuromorphic_twin/fpga_synapse_reference.py` consumes
`FrozenWeightStorage` directly and returns the complete signed-64 accumulator
image plus a deterministic contribution trace. Each trace entry identifies the
source queue, event index, axon ID, synapse index, target neuron, format index,
requested mantissa, reconstructed effective weight, and accumulator value after
the contribution.

The focused tests prove:

- external events are consumed before recurrent events;
- multiplicity is preserved;
- positive and negative contributions accumulate exactly;
- effective weights are reconstructed from the packed requested mantissa plus
  shared M08 format rather than from a precomputed hardware-only weight;
- physically valid but unconfigured axons are no-ops;
- invalid neuron targets, event IDs, counts, and capacities are rejected.

**Completion evidence:** the requested focused Python tests and complete Python
regression suite were independently run on 2026-08-24 and both passed with zero
failures. No exact pytest count is recorded because only pass status was
reported.

### M11.5.3.2 — standalone RTL decoder + CSR walker

`m08_weight_decoder_v1.sv` reconstructs M08 effective weights and
`phase_b_synapse_accumulator_v1.sv` implements a deliberately serialized Phase-B
engine with format, synapse, row-pointer, external-event, recurrent-event, and
signed-64 accumulator memories.

The directed XSIM test verifies decoder boundaries, CSR traversal,
external-before-recurrent ordering, repeated event/synapse contributions,
accumulator clearing between transactions, legal unconfigured-axon no-op
behavior, and deterministic capacity faults.

**Completion evidence:** the standalone vendor RTL gate was independently run
with Vivado/XSIM 2025.2 on 2026-08-24 and passed. The scripted success marker is:

```text
M11.5.3 Phase-B RTL tests passed: decoder boundaries + CSR traversal + multiplicity + capacity fault
M11.5.3 standalone Phase-B RTL simulation completed successfully.
```

### M11.5.3.3 — deterministic Python/RTL accumulator differential

`examples/generate_m11_5_3_vectors.py` generates twelve deterministic packed
M08/CSR/event cases using seed `0x4D313533`. The corpus includes a directed
extreme case plus reproducible randomized cases covering positive and negative
exponents, precision settings, mixed/excitatory/inhibitory sign modes, empty
rows, repeated events, recurrent events, and physically valid unconfigured
axons.

`tb_phase_b_synapse_accumulator_differential_v1.sv` reloads the complete packed
image for every case and compares every configured neuron's complete signed-64
accumulator word with the Python oracle. The runner regenerates the expectations
on every invocation so stale expected data cannot hide a model change.

**Completion evidence:** the differential XSIM gate was independently run and
passed on 2026-08-24 with:

```text
M11.5.3 Python/RTL accumulator differential passed: cases=12, seed=0x4d313533
M11.5.3 Python-to-RTL differential simulation completed successfully.
```

This establishes exact agreement on the Phase-B memory image rather than only a
few hand-authored accumulator values.

### M11.5.3.4 — packed M08 Phase B integrated with the real HLS neuron IP

`integrated_core_controller_v1.sv` composes the verified Phase-B walker and the
M11.5.2 serialized neuron controller. For each accepted tick it latches the
complete command/count boundary, runs Phase B to completion, transfers the
resulting signed-64 accumulator image internally, then starts Phase C through
the real M11.4 packaged `neuron_step_v1` IP.

The integration boundary deliberately exposes no host/testbench accumulator
preload port. Therefore the HLS `synaptic_input` values in this test can only
come from the packed M08 format/synapse/row memories and the external/recurrent
event buffers.

`generate_m11_5_3_integrated_vectors.py` composes the Python Phase-B oracle with
`step_packed_neuron_array_v1()` to produce the final expected state and spike
image. The Vivado project instantiates the actual packaged HLS IP and uses the
explicit four-signal `ap_ctrl_hs` wiring already proven in M11.5.2.

**Completion evidence:** the K26-targeted real-IP gate was independently run and
passed on 2026-08-24 with:

```text
M11.5.3 packed-M08 real-HLS block design validated successfully.
M11.5.3 packed-M08 + real-HLS integrated tick passed: neurons=16, axons=8, synapses=16, tag=0x4d353349
M11.5.3 packed-M08 + real packaged HLS IP simulation completed successfully.
```

The final marker proves the complete simulated path from packed M08 storage and
events through exact signed-64 Phase-B accumulation into the real packaged HLS
neuron transition, with final packed neuron state and spikes matching Python.

## Completion criteria

- [x] Frozen packed-memory software oracle passes focused and full Python tests.
- [x] RTL reconstructs M08 effective weights exactly for directed boundaries.
- [x] RTL traverses axon CSR rows and preserves event multiplicity.
- [x] RTL produces exact signed-64 per-neuron accumulator values.
- [x] Python-generated differential images match RTL accumulator memories.
- [x] Invalid counts, row pointers, event axons, format indices, neuron targets,
      weight words, and accumulator-overflow conditions have explicit fault
      paths instead of silent truncation/wrap.
- [x] The Phase-B walker is integrated ahead of the M11.5.2 Phase-C controller.
- [x] One real-HLS integrated tick matches the Python golden path without
      testbench-preloaded accumulators.
- [x] Completion evidence is recorded before starting M11.5.4.

## Remaining implementation note

The M11.5.3 composition intentionally preserves the separately verified Phase-B
and Phase-C blocks and transfers accumulator words between them. This duplicates
accumulator storage temporarily. M11.5.5 system/resource cleanup must either
collapse this into shared physical storage or explicitly account for the extra
memory before accepting the final integrated synthesis baseline. This is a
resource-organization issue; it does not weaken the M11.5.3 behavioral evidence.
