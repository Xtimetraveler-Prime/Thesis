# P08.5.2 — Final Comparison Acceptance

## Status

**Accepted:** 2026-09-30

P08.5.2 is accepted after independent reproduction of the thesis-facing NxTF/project comparison gate on the frozen P08.5.1 ledger.

## Independently reproduced result

The accepted candidate produced:

```text
13 passed in 0.09s
ledger fingerprint = 574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
report fingerprint = d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0
```

The accepted cross-system quantitative interpretation is limited to the three ledger-authorized accuracy quantities:

```text
ANN test-error gap:                 0.52 percentage points
SNN test-error gap:                 0.97 percentage points
ANN→SNN error-increase gap:         0.45 percentage points
```

These are reported as project-minus-NxTF differences. They remain subject to the P08 reconstruction caveat because the exact unpublished NxTF benchmark topology/checkpoint and native compiler mapping were not recovered.

## Structural interpretation

The final comparison records scale correspondence rather than exact reproduction:

```text
NxTF neurons:                  approximately 4,000
FPGA-v2 reconstruction:       4,218

NxTF trainable parameters:    approximately 7,000
FPGA-v2 reconstruction:       7,006

NxTF expanded connections:    approximately 341,000
FPGA-v2 reconstruction:       338,880
```

No exact ratio claim is derived from these rounded/sourced-approximate reference quantities.

The following remain contextual only and are not ratioed:

```text
NxTF shared weights:          6,746
P06 stored shared entries:   64,235

NxTF Loihi neurocores:           14
P06 logical cores:                5
```

Their storage/compiler/accounting boundaries differ materially.

## Accepted project-specific implementation observations

```text
logical cores:                     5
resident K26 contexts:             3
physical HLS engines:              1
representative forward page loads:497
representative internal packets: 17,910
PL clock:                        100 MHz
representative dispatch cycles: 3,865
representative dispatch time:    38.65 us
K26 URAM288 use:                  47
routed WNS:                      +0.734 ns
```

The 3,865-cycle / 38.65-us observation is one representative logical-core-4 physical dispatch at timestep 99. It is not an end-to-end per-sample inference latency measurement.

## Frozen non-claims

P08.5.2 preserves all P08.5.1 comparison guardrails:

- no direct FPGA-versus-Loihi energy comparison;
- no direct native-Loihi-versus-K26 latency comparison;
- no shared-weight efficiency ratio;
- no mapped-core efficiency ratio;
- no interpretation of one physical dispatch as full-sample latency;
- no claim that the complete 100-timestep representative inference was physically replayed end-to-end over JTAG;
- no post-test topology, checkpoint, conversion, threshold, decoder, or timestep tuning.

## Accepted physical scope

The final comparison distinguishes two accepted conformance scopes:

1. P08.4.2 proves the complete 100-timestep five-logical-core paging execution in compiled software, including legal paging/service-order invariance.
2. P08.4.3b physically proves representative deep-network page replacement and exact K26 dispatch conformance for a real MNIST execution snapshot.

These two results form one evidence chain but are not conflated into a claim of full end-to-end physical JTAG replay.

## Acceptance boundary

P08.5.2 freezes the final quantitative comparison and interpretation used by P08 closure. P08.5.3 may summarize, bind, and archive these accepted results, but must not introduce new performance ratios or change the comparison boundary.
