# P08.4.3b Acceptance Record — Representative Physical MNIST Conformance

**Status:** Accepted  
**Accepted:** 2026-09-30  
**Branch:** `agent/p08.4.3b-physical-mnist-conformance`

## Accepted result

P08.4.3b physically validated the frozen representative MNIST execution snapshot on the accepted host-paged K26 shell. The gate used official MNIST test index 0 (label 7), logical core 4, algorithmic timestep 99, and physical resident slot 0. The representative case was fixed by index before physical execution and was not selected by confidence, correctness, class, or any post-test performance criterion.

The physical run completed successfully with:

```text
logical core:       4
algorithmic timestep: 99
resident slot:      0
evicted marker:     logical core 0
dispatch cycles:    3865
spikes:             0
packets:            0
compartments checked: 618
```

The K26 output evidence matched the accepted P08.4.2 software result exactly:

```text
[-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
```

The physical prediction is class 7.

## Identity binding

The accepted physical shell identities are:

```text
p08_host_paged.bit SHA-256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83
p08_host_paged.ltx SHA-256 = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
compiled deployment       = 5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

The physical harness refuses to report success if these identities drift.

## Independent physical evidence

The independently reproduced run reported:

```text
PASS: P08.4.3b K26 reset/clock heartbeat 3233634->5822962
PASS: P08.4.3b decoy residency logical_core=0 slot=0 marker_verified=true
PASS: P08.4.3b page replacement slot=0 evicted_logical_core=0 loaded_logical_core=4
PASS: P08.4.3b physical dispatch logical_core=4 timestep=99 cycles=3865 spikes=0 packets=0
PASS: P08.4.3b exact state/trace compartments=618
PASS: P08.4.3b exact packet image count=0
PASS: P08.4.3b physical MNIST evidence=-284 -1203 104 109 -2253 -599 -2659 1446 -436 -63 exact_match=true
PASS: P08.4.3b result exact state_trace=true packets=true evidence=true
PASS: P08.4.3b physical evidence [-284,-1203,104,109,-2253,-599,-2659,1446,-436,-63] prediction=7
PASS: P08.4.3b test-use boundary selection_decisions_after_test=0
P08.4.3b physical MNIST conformance gate completed successfully.
```

The wrapper performs a second validation after Vivado returns. It requires a generated physical result file containing `result=PASS`, the exact compiled identity, the frozen test/timestep/slot/logical-core fields, exact state/trace match, exact packet match, exact evidence match, and zero model/conversion selection after test observation before the final success line is emitted.

The harness also archives the physical result, raw Vivado log, generated vector corpus, vector summary, route metrics when available, and SHA-256 identities under a timestamped `hardware/evidence/p08_4_3b_physical_*` directory.

## Claim boundary

This acceptance does **not** claim that the host/JTAG harness physically replayed the entire 100-timestep inference or all approximately 500 logical-core dispatch opportunities on programmable logic.

The accepted evidence chain is intentionally split:

- **P08.4.2:** exhaustive 100-timestep compiled execution, five logical cores over three resident contexts, paging-order invariance, and exact source-versus-compiled evidence in software;
- **P08.4.3a:** routed/timing-clean physical host-paged K26 shell with five logical backing contexts, three resident slots, and one HLS engine;
- **P08.4.3b:** representative real MNIST deep-core page replacement and physical dispatch with exact state, trace, packet-image, and output-evidence conformance.

Therefore the defensible physical claim is that the accepted K26 implementation reproduces the frozen architectural computation exactly for the representative deep-network physical dispatch, while complete 100-timestep paging semantics are established by P08.4.2 rather than by an end-to-end JTAG replay.

No post-test model, conversion, threshold, decoder, topology, timestep, or representative-case selection was performed.
