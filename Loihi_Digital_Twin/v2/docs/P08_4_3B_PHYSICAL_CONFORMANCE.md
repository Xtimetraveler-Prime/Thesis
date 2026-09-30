# P08.4.3b Representative K26 Physical Conformance

## Status

**Phase:** P08.4.3b  
**Implementation state:** physical verification candidate  
**Prerequisites:** accepted P08.4.2 compiled execution and accepted P08.4.3a routed host-paged shell

P08.4.3b is the physical-fabric counterpart to the exhaustive P08.4.2 software conformance gate. P08.4.2 already proved the complete 100-timestep five-logical-core execution, including forward and reverse paging schedules, against the source-recovered SNN. P08.4.3b does not repeat all 497 software page loads over the slow VIO/JTAG debug transport. Instead it freezes exact timestep-99 architectural snapshots from that accepted execution and dispatches representative contexts through the real K26 datapath.

## Frozen physical shell

The board gate accepts only the routed P08.4.3a artifacts with these hashes:

```text
p08_host_paged.bit
3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83

p08_host_paged.ltx
e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

The shell contains three complete resident context slots and one P03-compatible HLS engine. Cross-page packet routing and the algorithmic barrier remain host responsibilities; there is no on-fabric cross-page router.

## Fixed representative frame

P08.4.3b inherits the representative frame from P08.4.2 without re-selection:

```text
official MNIST test index: 0
label:                     7
algorithmic timestep:      99
physical resident slot:    2
expected prediction:       7
expected final evidence:   [-284, -1203, 104, 109, -2253,
                            -599, -2659, 1446, -436, -63]
```

No training, checkpoint, conversion, quantization, threshold, decoder, or model-selection decision is made after observing the official test set.

## Physical paging sequence

The fixed sequence is:

```text
ingress_core0_t99 -> output_core4_t99 -> ingress_core0_t99
```

All three dispatches use physical slot 2. This deliberately separates logical identity from resident-slot identity and causes two real page replacements. The final core-0 dispatch reloads the previously evicted backing image and must reproduce the first core-0 state/trace/packet result exactly.

Core 0 was chosen as the reload context because it exercises the live ingress side of the accepted compiled deployment while avoiding a redundant second transfer of one of the much larger deep synapse tables. Core 4 is the deep output context: under the accepted P06 mapping it contains all ten scalar `conv4_c*` output populations used for the final evidence vector.

## Generated corpus

`mnist_v2_nxtf.physical_conformance` regenerates the physical corpus from:

- the accepted P08.3.5c compiled deployment;
- the accepted P08.4.2 input-spike schedule and conformance manifest; and
- the exact timestep-99 architectural state obtained by replaying that fixed compiled execution.

For each selected logical context it emits:

- full compartment configuration;
- exact pre-dispatch compartment state;
- sparse input-axon descriptors;
- complete shared synapse table;
- sparse route descriptors and route words;
- exact current-timestep input event list;
- expected post-dispatch state words;
- expected trace words; and
- expected packet words.

The generated context metadata uses the accepted P05/P08 layout and the original logical core ID even though both contexts are materialized into physical slot 2.

## Board checks

`hardware/p08_4_3b_physical_conformance.tcl` performs the following checks on the K26:

1. program the exact accepted P08.4.3a bitstream and debug probes;
2. verify reset release and PL heartbeat;
3. host-load each backing context into physical slot 2;
4. clear sparse route descriptors before each replacement so no evicted route state can leak into the new context;
5. dispatch the selected logical context through the physical HLS engine;
6. verify logical-core ID, physical slot, event bank, HLS status, packet count, spike count, controller error flags, and nonzero dispatch cycles;
7. read every live post-dispatch compartment state and trace word and compare it exactly with the architectural reference;
8. read all emitted packet words and compare the packet multiset exactly;
9. for logical core 4, read the ten conv4 state words, decode their signed 24-bit voltages, and require the exact accepted evidence vector and prediction; and
10. reload logical core 0 after its eviction and require the same exact state/trace/packet result again.

## Acceptance boundary

P08.4.3b can be accepted only if the board result records:

```text
physical dispatches = 3
page replacements   = 2
reload exact         = true
final evidence exact = true
prediction           = 7
result               = PASS
```

This gate establishes representative physical equivalence of the accepted P08 arithmetic/memory/dispatch boundary on the K26. The exhaustive full-run paging invariance remains the P08.4.2 software result; P08.4.3b is intentionally a representative physical corpus rather than a claim that all 100 timesteps were transported through VIO/JTAG.