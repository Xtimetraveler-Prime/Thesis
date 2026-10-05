# P08.5.2 — Final NxTF / FPGA-v2 Comparison Gate

## Purpose

P08.5.1 froze the evidence and comparability policy before interpretation. P08.5.2 consumes that accepted ledger and produces the thesis-facing final comparison without changing any experiment, model, conversion, mapping, or physical result.

The independently accepted P08.5.1 ledger identity is:

```text
schema:      p08-nxtf-comparison-ledger-v1
rows:        24
fingerprint: 574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
```

P08.5.2 is implemented in:

```text
applications/mnist_v2_nxtf/mnist_v2_nxtf/final_comparison.py
```

and is validated by:

```text
applications/mnist_v2_nxtf/tests/test_p08_5_final_comparison.py
Loihi_Digital_Twin/v2/scripts/run_p08_5_2_final_comparison.sh
```

## Interpretation policy

The report may not invent a second comparison policy. Every quantity is inherited from the accepted P08.5.1 ledger.

Only three cross-system numerical differences are promoted into thesis-facing quantitative interpretation:

```text
ANN test-error gap:              0.52 percentage points
SNN test-error gap:              0.97 percentage points
ANN-to-SNN conversion-loss gap: 0.45 percentage points
```

All three remain `COMPARABLE_WITH_RECONSTRUCTION_CAVEAT` because the exact unpublished NxTF benchmark topology/checkpoint was not recovered.

The aggregate structural quantities are described only as scale correspondence:

```text
NxTF neurons:               approximately 4,000
FPGA-v2 reconstruction:     4,218

NxTF trainable parameters:  approximately 7,000
FPGA-v2 reconstruction:     7,006

NxTF discrete connections:  approximately 341,000
FPGA-v2 reconstruction:     338,880
```

No exact structural ratio/delta is claimed because the published paper values are rounded and the exact benchmark graph is unavailable.

## Context-only quantities

The following are deliberately retained as contextual side-by-side values without a derived efficiency statement:

```text
NxTF shared weights:       6,746
P06 stored/shared entries: 64,235

NxTF Loihi neurocores:     14
P06 logical cores:          5
```

The storage representations, partitioners, compiler behavior, and modeled resource limits are not equivalent. P08.5.2 therefore rejects any attempt to turn those pairs into a cross-system efficiency ratio.

## Project-specific implementation observations

P08.5.2 separately reports the accepted FPGA-v2 implementation boundary:

```text
logical cores:                         5
resident K26 contexts:                 3
physical HLS engines:                  1
representative forward page loads:   497
representative internal packets:  17,910
requested PL clock:                  100 MHz
representative physical dispatch:  3,865 cycles
representative dispatch time:       38.65 us
K26 URAM288 use:                       47
routed WNS:                        +0.734 ns
```

The `38.65 us` value is the accepted `3,865 cycles / 100 MHz` calculation for one logical-core-4 timestep-99 dispatch. It is not end-to-end sample latency.

## Native-Loihi physical metrics

The published NxTF values:

```text
0.66 mJ/sample
6.65 ms/sample
```

remain `NOT_COMPARABLE` because P08 has no equivalent workload-specific K26 energy measurement and no equivalent end-to-end K26 sample-latency measurement. They remain useful paper context but do not support a faster/slower or lower/higher-energy conclusion.

## Physical-conformance scope

P08.4.2 proves the complete 100-timestep five-logical-core execution under deterministic paging and legal service order in compiled software.

P08.4.3b physically proves one real deep-network page replacement and logical-core-4 timestep-99 dispatch on the K26, including exact agreement for all 618 checked compartment state/trace words and final output evidence.

P08.5.2 preserves the distinction:

```text
complete 100-timestep paged software conformance: true
representative physical K26 deep dispatch:        true
full end-to-end 100-timestep JTAG replay:          false
```

## Generated artifacts

A successful gate creates:

```text
applications/mnist_v2_nxtf/artifacts/p08_5_2_final_comparison/
├── p08_5_final_comparison.json
└── p08_5_final_comparison.md
```

The JSON report contains the accepted ledger fingerprint, allowed numeric comparison set, forbidden derived-comparison set, bounded findings, explicit non-claims, and a deterministic report fingerprint.

The Markdown report is rendered from that validated machine-readable summary and is intended to be directly useful when writing the final thesis results/discussion section.

The gate generates both artifacts twice and requires byte identity before promoting them to the final artifact directory.

## Run

With `.venv-p08` active:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_5_2_final_comparison.sh
```

## Acceptance boundary

P08.5.2 can be accepted when:

- all P08.5.1 and P08.5.2 focused tests pass;
- the accepted ledger fingerprint remains exactly `574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d`;
- two independent final-report generations are byte-identical;
- the report fingerprint recomputes exactly;
- the 0.52 / 0.97 / 0.45 percentage-point interpretations are reproduced;
- structural quantities remain approximate-scale comparisons rather than precision ratios;
- shared-weight/core-count ratios remain forbidden;
- native-Loihi energy/latency remain non-comparable;
- the representative dispatch remains explicitly distinct from end-to-end sample latency; and
- the full-JTAG-replay guard remains false.

Acceptance of P08.5.2 will unlock only P08.5.3 final closure/documentation. It will not trigger additional training, conversion, official-test evaluation, or hardware retuning.
