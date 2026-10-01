# FPGA-v2 NxTF MNIST Emulation Application

This directory contains the completed P08 application for the Loihi architectural digital twin v2. It is intentionally separate from the frozen FPGA-v1 MNIST application under `applications/mnist_baseline/`.

P08 was realigned on 2026-09-29 after the first three hand-designed candidates showed that matching only the published parameter count was not a sufficient basis for comparison. The accepted goal became to emulate the published NxTF frame-based MNIST work as closely as public evidence and FPGA-v2 permit, while explicitly labeling reconstruction choices and non-comparable quantities.

Authoritative records include:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
Loihi_Digital_Twin/v2/docs/P08_NXTF_SOURCE_AUDIT.md
Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md
Loihi_Digital_Twin/v2/docs/P08_CONTEXT_PAGING.md
Loihi_Digital_Twin/v2/docs/P08_3_ACCEPTANCE.md
Loihi_Digital_Twin/v2/docs/P08_4_ACCEPTANCE.md
Loihi_Digital_Twin/v2/docs/P08_5_1_ACCEPTANCE.md
Loihi_Digital_Twin/v2/docs/P08_5_2_ACCEPTANCE.md
Loihi_Digital_Twin/v2/docs/P08_5_3_ACCEPTANCE.md
Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
```

## Status — Complete

P08.1 through P08.5.3 are accepted. The final closure gate was independently reproduced with 19 passing tests and closure fingerprint:

```text
135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce
```

The accepted `PROJECT_RECONSTRUCTION` is:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid) -> 12x12x14
 -> Conv2D(20, 3x3, stride 1, valid) -> 10x10x20
 -> Conv2D(12, 3x3, stride 2, valid) ->  4x4x12
 -> Conv2D(10, 4x4, stride 1, valid) ->  1x1x10
```

Accepted structural totals:

```text
neurons:                 4,218
convolution weights:     6,950
bias parameters:            56
trainable parameters:    7,006
expanded connections: 338,880
primary timesteps:          100
```

The exact paper topology remains unpublished/unrecovered and is not claimed.

## Accepted training/conversion result

The accepted ANN checkpoint was selected using only the deterministic 55,000/5,000 training-validation partition. Its fixed-validation accuracy was 0.992600.

Source recovery of Intel's public NxTF/SNN-Toolbox backend established per-layer parameter/threshold normalization and softmax voltage readout. The accepted source-recovered thresholds are:

```text
input BIAS threshold: 2040
conv1 threshold:       556
conv2 threshold:       512
conv3 threshold:       672
conv4 readout:         final membrane voltage
conv4 suppress-spike threshold: 131071
```

The accepted converted SNN validation result at 100 timesteps is:

```text
examples:      5000
accuracy:      0.984400
ANN reference: 0.992600
delta:         0.008200
ties:          0
```

## Official MNIST test result

P08.4 opened the untouched 10,000-image official test set only after the ANN checkpoint, conversion, thresholds, readout, topology, and timestep policy were frozen.

Accepted result:

```text
ANN official-test accuracy: 0.987400
SNN official-test accuracy: 0.982400
ANN-SNN delta:              0.005000
SNN test error:             0.017600
readout ties:               1
selection decisions after test: 0
```

Artifact identities:

```text
ANN semantic weights = e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce
parameters           = 9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network              = 6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled deployment  = 5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

## Accepted mapping and paging boundary

```text
logical/backing cores: 5
resident K26 contexts: 3
physical HLS engines:  1
expanded connections:  338,880
```

For official-test index 0 (label 7), P08.4.2 executed the complete 100-timestep compiled deployment under unpaged, forward-paged, and reverse-paged schedules. All schedules produced the same normalized trace fingerprint and final evidence:

```text
trace = a81844443b6e5f6c278167a4aafc46dcfd74f7df5498179312b1fc39edba09d6
evidence = [-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
prediction = 7
forward page loads/evictions = 497/497
reverse page loads/evictions = 499/499
```

## Physical K26 acceptance

P08.4.3a built the host-paged physical shell with:

```text
requested PL clock: 100 MHz
WNS: +0.734 ns
WHS: +0.010 ns
URAM: 47
logical backing contexts: 5
resident context slots:   3
physical engines:         1
cross-page routing:       host owned
global barrier:           host owned
```

Accepted physical artifacts:

```text
p08_host_paged.bit SHA-256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83
p08_host_paged.ltx SHA-256 = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

P08.4.3b physically replaced resident slot 0 with the real logical-core-4 state for official-test index 0 immediately before timestep 99 and dispatched that context through the K26 HLS engine. The physical run matched all 618 compartment states and traces, the complete packet image, and the ten-class evidence exactly. The dispatch took 3,865 synchronous PL cycles, or 38.65 microseconds at the requested 100 MHz clock.

That observation is one representative deep-core dispatch, not end-to-end sample latency. Full paging semantics are proven by P08.4.2; the physical gate proves the deep-network page-replacement, memory-image, arithmetic, trace, packet, and output-state boundary.

## Final bounded NxTF comparison

P08.5.1 froze the comparison ledger:

```text
574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
```

P08.5.2 froze the thesis-facing comparison report:

```text
d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0
```

The accepted reconstruction-bounded quantitative differences from the published NxTF result are:

```text
ANN test-error gap:              0.52 percentage points
SNN test-error gap:              0.97 percentage points
ANN-to-SNN conversion-loss gap: 0.45 percentage points
```

The paper's approximately 4k neurons, approximately 7k parameters, and approximately 341k expanded connections are treated as scale correspondence only. The paper's 6,746 shared weights versus the project's 64,235 P06 stored entries and 14 Loihi neurocores versus five P06 logical cores are contextual only because the representation/compiler models differ.

The native-Loihi 0.66 mJ/sample and 6.65 ms/sample measurements remain published context. P08 has no equivalent end-to-end K26 workload-specific energy/latency measurement, so no direct FPGA-versus-Loihi energy or latency conclusion is drawn.

## Environment

The dedicated P08 environment remains the reproducibility environment:

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
```

P08 is complete. Any additional topology recovery, energy instrumentation, full end-to-end physical replay, or higher-fidelity Loihi features are follow-on experiments rather than unfinished P08 deliverables.
