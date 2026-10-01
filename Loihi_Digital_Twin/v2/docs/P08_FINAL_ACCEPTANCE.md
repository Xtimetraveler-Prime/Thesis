# P08 — Final Acceptance

**Status:** Complete  
**Completed:** 2026-09-30

P08 is the final planned application/comparison phase of FPGA-v2. It is accepted after independent reproduction of the P08.5.3 closure gate with 19 passing tests.

Final closure fingerprint:

```text
135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce
```

Accepted comparison chain:

```text
P08.5.1 ledger = 574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
P08.5.2 report = d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0
P08.5.3 closure = 135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce
```

Final accepted application result:

```text
ANN official-test accuracy: 0.987400
SNN official-test accuracy: 0.982400
ANN-SNN delta:              0.005000
primary horizon:            100 timesteps
neurons:                    4,218
trainable parameters:       7,006
expanded connections:       338,880
logical cores:              5
resident K26 contexts:      3
physical engines:           1
```

P08 establishes a source-backed architectural reconstruction and comparison, not exact proprietary NxTF/Loihi reproduction. The final claim boundary is recorded in `P08_5_3_ACCEPTANCE.md`.

With P08 accepted, all planned FPGA-v2 phases P00-P08 are complete.
