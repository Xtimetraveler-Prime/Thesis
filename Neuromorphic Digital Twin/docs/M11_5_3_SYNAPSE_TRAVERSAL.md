# M11.5.3 — M08 Synapse Traversal and Exact Accumulation

**Status:** In progress  
**Started:** 2026-08-24  
**Repository evidence:** branch `agent/m11-5-core-integration`

## Goal

Replace the testbench-preloaded signed-64 accumulators used by M11.5.2 with a
real FPGA Phase-B path that consumes the frozen M08.5 weight image and produces
the exact accumulator image required by M10 before neuron updates begin.

The normative data path is:

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
```

M11.5.3 must not redefine M08 weight semantics. The hardware consumes exactly:

```text
weight_formats.mem     16-bit shared format words
weight_synapses.mem    32-bit requested-mantissa/format/target words
weight_axon_rows.mem   32-bit CSR row pointers
```

and must reconstruct the same effective integer produced by
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
the 1,024-row physical profile is a fault.

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

The hardware reconstruction is the M08 encoder contract:

1. validate sign-mode mantissa bounds;
2. derive the precision shift;
3. truncate the requested mantissa toward zero to the configured precision;
4. apply the signed exponent;
5. apply the fixed six-bit weight alignment;
6. clip only the effective static weight to `[-2,097,088, +2,097,088]`;
7. add the resulting integer to the signed-64 target accumulator.

For negative exponents, an arithmetic right shift is required because the M08
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

The physical profile proof bounds the worst possible absolute mathematical sum
below `2^46`, so signed-64 overflow cannot occur for a legal image/event set.
The software and RTL still keep an explicit overflow guard to make violations
visible rather than silently wrapping.

## Verification order

### M11.5.3.1 — packed-memory software oracle

`src/neuromorphic_twin/fpga_synapse_reference.py` consumes
`FrozenWeightStorage` directly and returns:

- the complete signed-64 accumulator tuple;
- a deterministic contribution trace containing source/event/axon/synapse,
  target, format index, requested mantissa, effective weight, and accumulator
  value after the contribution.

Focused tests cover external-before-recurrent ordering, multiplicity, mixed
positive/negative accumulation, M08 effective-weight reconstruction, legal
unconfigured-axon no-op behavior, configured-neuron target checks, and physical
event-capacity checks.

### M11.5.3.2 — standalone RTL weight decoder + CSR walker

Add source-controlled RTL that owns the first weight-format, synapse, axon-row,
event, and signed-64 accumulator arrays. A standalone XSIM test will preload a
small frozen image and require exact accumulator values from the RTL walker.

### M11.5.3.3 — deterministic Python/RTL differential corpus

Generate packed M08 memory/event images from Python, run them through the RTL
walker, and compare complete accumulator memories plus selected traversal/fault
observations.

### M11.5.3.4 — integrate Phase B with the M11.5.2 controller

Replace testbench accumulator preloads with the real walker. Phase C may start
only after Phase B has completed every event/synapse contribution. Run the real
packaged HLS IP and compare post-tick state/spikes against Python expectations.

## Completion criteria

- [ ] Frozen packed-memory software oracle passes focused and full Python tests.
- [ ] RTL reconstructs M08 effective weights exactly for directed boundaries.
- [ ] RTL traverses axon CSR rows and preserves event multiplicity.
- [ ] RTL produces exact signed-64 per-neuron accumulator values.
- [ ] Python-generated differential images match RTL accumulator memories.
- [ ] Invalid counts, row pointers, event axons, format indices, and neuron
      targets produce deterministic faults instead of truncation/wrap.
- [ ] The Phase-B walker is integrated ahead of the M11.5.2 Phase-C controller.
- [ ] One real-HLS integrated tick matches the Python golden path without
      testbench-preloaded accumulators.
- [ ] Completion evidence is recorded before starting M11.5.4.
