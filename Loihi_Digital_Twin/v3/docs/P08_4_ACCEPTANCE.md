# P08.4 Acceptance Record — Official Test Evaluation and K26 Conformance

**Status:** Complete / accepted  
**Completed:** 2026-09-30

## Scope

P08.4 closes the frozen-evaluation and hardware-conformance stage for the reconstructed NxTF frame-based MNIST workload. It binds the already accepted P08.3 ANN/SNN artifacts to the untouched official MNIST test split, verifies the exact compiled deployment under legal paging/service schedules, implements the host-paged physical K26 shell, and physically checks a frozen deep-network MNIST dispatch against the accepted software architecture.

No model, conversion, threshold, decoder, topology, timestep, or checkpoint selection was performed after official-test results were observed.

## P08.4.1 — Frozen official-test evaluation

The official 10,000-image MNIST test split was opened only after P08.3 training, checkpoint selection, source-recovered conversion, quantization, thresholds, readout, and the primary 100-timestep horizon were frozen.

Accepted result:

```text
ANN accuracy:       0.987400
SNN accuracy:       0.982400
ANN-SNN delta:      0.005000
examples:           10000
timesteps:          100
SNN readout ties:   1
all-equal evidence: 0
zero evidence:      0
```

Agreement breakdown:

```text
both correct: 9797
ANN only:       77
SNN only:       27
both wrong:     99
```

All 10,000 examples were active through all tracked SNN stages.

Frozen artifact identities:

```text
ANN semantic weights = e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce
parameters           = 9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network              = 6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled deployment  = 5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

The SNN test error is 1.76%. The NxTF paper reports 0.79% converted-SNN test error. P08 does not treat those as like-for-like proof because the exact unpublished paper topology/checkpoint/partitioning is unavailable and the project graph is explicitly a source-bounded reconstruction.

## P08.4.2 — Exact compiled execution conformance

The representative physical/conformance frame was fixed as official-test index 0, label 7.

The complete 100-timestep compiled deployment was executed as:

- unpaged logical reference;
- paged forward logical-core service/drain; and
- paged reverse logical-core service/drain.

All three produced the same normalized trace fingerprint:

```text
a81844443b6e5f6c278167a4aafc46dcfd74f7df5498179312b1fc39edba09d6
```

and exactly the same final evidence:

```text
[-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
```

with prediction 7.

Paging was exercised substantially:

```text
forward page loads:    497
forward evictions:     497
reverse page loads:    499
reverse evictions:     499
logical cores:           5
resident contexts:       3
physical engines:        1
```

The compiled execution matched the source-recovered simulator exactly at the accepted architectural boundary.

## P08.4.3a — Host-paged K26 shell

A physical K26 shell was built around the accepted P03 HLS engine, three full resident context memories, and the P08 paged-dispatch controller. Cross-page routing and the global algorithmic barrier remain host-owned, matching the P08.2/P08.4.2 execution contract.

Accepted routed implementation:

```text
WNS:                 +0.734 ns
WHS:                 +0.010 ns
URAM:                47
logical backing:      5
resident contexts:    3
physical engines:     1
host-paged dispatch:  true
on-fabric cross-page router: false
```

Physical artifact identities:

```text
p08_host_paged.bit SHA-256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83
p08_host_paged.ltx SHA-256 = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

## P08.4.3b — Representative physical MNIST conformance

The accepted physical gate loaded the real logical-core-4 state for official-test index 0 immediately before timestep 99 into physical slot 0 after first writing and verifying a distinct decoy logical-core-0 marker.

Accepted physical result:

```text
logical core:           4
physical slot:          0
timestep:              99
input events:           2
compartments checked: 618
dispatch cycles:     3865
spikes:                 0
packets:                0
state/trace exact:   true
packet image exact:  true
output evidence exact:true
prediction:             7
```

Physical output evidence matched P08.4.2 bit-for-bit:

```text
[-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
```

The physical wrapper independently validated its result file after Vivado returned before emitting the final success marker.

## Accepted claim boundary

P08.4 supports the following claim chain:

1. the frozen reconstructed ANN reaches 98.74% official-test accuracy;
2. the frozen converted SNN reaches 98.24% official-test accuracy at 100 timesteps;
3. the exact five-logical-core deployment reproduces the source-recovered SNN under complete 100-timestep paging in software;
4. the host-paged K26 implementation routes successfully at 100 MHz with the accepted physical resource boundary; and
5. a frozen real MNIST deep-network context replacement/dispatch on the physical K26 reproduces the accepted state, trace, packet, and final evidence exactly.

P08.4 does **not** claim that the full 100-timestep/approximately-500-dispatch representative inference was replayed entirely through JTAG on hardware. That exhaustive paging proof belongs to P08.4.2; the physical proof is the representative deep-dispatch conformance of P08.4.3b.

P08.4 also does not establish native-Loihi latency or energy equivalence, exact NxTF partitioning, native Loihi synapse-memory packing, or the unpublished exact NxTF benchmark topology/checkpoint.

## Next phase

P08.5 performs the final bounded NxTF comparison and P08 closure. It must separate directly sourced/comparable quantities from project reconstruction, project-specific implementation measurements, and non-comparable quantities rather than collapsing them into a single performance ranking.
