# P08.5.1 Acceptance — NxTF Comparison Ledger and Comparability Freeze

## Status

**Accepted:** 2026-09-30  
**Independently verified candidate:** `2f06abfd37d620bc0d2b06a0a75d2ffb49aafc55`

P08.5.1 is accepted after independent reproduction of the deterministic comparison-ledger gate. This acceptance record does not modify the tested ledger generator, classification policy, or regression tests.

## Independently reproduced result

The user independently ran:

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_5_1_comparison_ledger.sh \
    | tee /tmp/p08_5_1_comparison.log
```

and reproduced:

```text
6 passed in 0.05s
PASS: P08.5.1 ledger rows=24 fingerprint=574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
PASS: P08.5.1 classifications COMPARABLE_WITH_RECONSTRUCTION_CAVEAT=7 CONTEXT_ONLY=2 DIRECTLY_COMPARABLE=3 NOT_COMPARABLE=2 PROJECT_SPECIFIC=10
PASS: P08.5.1 safe delta metric=ann_test_error delta=0.005200 class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT
PASS: P08.5.1 safe delta metric=snn_test_error delta=0.009700 class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT
PASS: P08.5.1 safe delta metric=ann_to_snn_error_increase delta=0.004500 class=COMPARABLE_WITH_RECONSTRUCTION_CAVEAT
PASS: P08.5.1 guardrails energy_direct=false latency_direct=false shared_weight_ratio=false core_count_ratio=false dispatch_is_sample_latency=false full_jtag_replay=false post_test_tuning=false
PASS: P08.5.1 deterministic ledger fingerprint=574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
PASS: P08.5.1 comparison boundaries direct=3 caveated=7 context=2 project_specific=10 not_comparable=2
PASS: P08.5.1 accuracy anchors nxtf_ann_error=0.007400 project_ann_error=0.012600 nxtf_snn_error=0.007900 project_snn_error=0.017600
PASS: P08.5.1 structure anchors neurons=4000~vs4218 params=7000~vs7006 connections=341000~vs338880
PASS: P08.5.1 noncomparability guards energy=true latency=true shared_weight_ratio=true mapped_core_ratio=true dispatch_not_sample_latency=true full_jtag_replay=false
P08.5.1 comparison-ledger gate completed successfully.
```

## Frozen ledger identity

```text
schema:      p08-nxtf-comparison-ledger-v1
rows:        24
fingerprint: 574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
```

Comparison-class counts:

```text
DIRECTLY_COMPARABLE=3
COMPARABLE_WITH_RECONSTRUCTION_CAVEAT=7
CONTEXT_ONLY=2
PROJECT_SPECIFIC=10
NOT_COMPARABLE=2
```

## Accepted safe quantitative deltas

Only rows whose frozen ledger explicitly sets `allow_numeric_delta=true` may be used for cross-system numerical differences. The independently reproduced cross-system accuracy deltas are:

```text
ANN test error difference:          0.005200 fraction = 0.52 percentage points
SNN test error difference:          0.009700 fraction = 0.97 percentage points
ANN-to-SNN error-increase difference: 0.004500 fraction = 0.45 percentage points
```

These remain **comparison-with-reconstruction-caveat** results. They do not establish that the FPGA-v2 reconstruction is an exact reproduction of the unpublished NxTF benchmark model.

## Accepted non-comparability guards

P08.5.1 explicitly freezes the following claim boundaries:

- native-Loihi energy is not a direct FPGA energy comparison;
- native-Loihi latency is not a direct FPGA latency comparison;
- NxTF shared-weight count and P06 stored/shared-parameter count do not use the same storage model;
- NxTF neurocore count and P06 logical-core count do not use the same compiler/resource model;
- the 3,865-cycle representative K26 dispatch is not full-sample inference latency;
- the full 100-timestep representative inference was not physically replayed end-to-end over JTAG; and
- no model/conversion selection occurred after official-test observation.

## Acceptance decision

P08.5.1 is complete. The ledger is the frozen evidence and comparability authority for P08.5.2. The next sub-phase may render thesis-facing tables and interpretation from this ledger, but it must not reclassify metrics or introduce cross-system ratios/deltas that the ledger forbids.
