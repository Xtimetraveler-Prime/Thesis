# P08.4.1 — Frozen ANN/SNN official MNIST test evaluation

**Status:** Verification pending  
**Phase:** P08.4 — full software evaluation and physical K26 conformance

## Purpose

P08.4.1 is the first phase permitted to inspect classification performance on the official 10,000-image MNIST test split.

The gate evaluates two already-frozen artifacts on exactly the same untouched test labels:

1. the accepted P08.3.3 ANN checkpoint; and
2. the accepted P08.3.5c source-recovered SNN conversion at 100 algorithmic timesteps.

This is an evaluation gate, not a model-selection or tuning gate.

## Preconditions

P08.3 was accepted on 2026-09-30 after completing the full 5,000-image validation measurement.

Accepted ANN identity:

```text
checkpoint_sha256=61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2
weights_fingerprint=e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce
```

Accepted source-recovered SNN identities:

```text
parameter_fingerprint=9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network_fingerprint=6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled_fingerprint=5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
input_threshold=2040
hidden_thresholds=[556,512,672]
readout=final_membrane_voltage_argmax
primary_timesteps=100
```

The accepted P08.3 validation result was:

```text
ANN validation accuracy=0.992600
SNN validation accuracy=0.984400
ANN-SNN validation delta=0.008200
```

Those values are prior evidence only. They are not acceptance targets for the official test result.

## Test-use rules

The official test split becomes observable only after all artifact identity checks pass.

P08.4.1 must not perform any of the following after observing test results:

- further ANN training;
- checkpoint reselection;
- conversion recalibration;
- weight or bias requantization;
- threshold changes;
- decoder changes;
- timestep selection or horizon changes;
- topology or mapping changes intended to improve test accuracy.

The manifest therefore records:

```text
evaluation_only_no_selection=true
selection_decisions_after_test=0
post_test_training=false
post_test_conversion_tuning=false
post_test_threshold_tuning=false
post_test_decoder_tuning=false
post_test_timestep_tuning=false
accuracy_acceptance_threshold=null
```

## Dataset boundary

P08.4.1 uses the standard Keras MNIST official test split:

```text
images=10000
shape=28x28
labels=0..9
```

The test images are normalized to `[0,1]` for the ANN.

For the SNN, the complete 10,000-image normalized corpus is scaled once into the recovered NxTF unsigned 8-bit BIAS input domain before execution batching:

```text
encoded = int(image / corpus_max * 255)
```

Batch size affects execution only. It must not affect the corpus-level input scale.

## Measurements

The gate records:

- ANN official-test accuracy;
- SNN official-test accuracy;
- ANN minus SNN accuracy delta;
- ANN and SNN correct counts;
- ANN/SNN disagreement categories;
- per-class accuracy and confusion matrices;
- SNN final readout ties and degenerate-evidence counts;
- aggregate input/hidden spike activity;
- stage active-example counts;
- deterministic label, ANN-prediction, SNN-prediction, and SNN-evidence fingerprints;
- exact accepted ANN/conversion/network/deployment identities.

No minimum accuracy is encoded into the gate. A poor but structurally valid result is still evidence and must be reviewed rather than tuned away.

## Local artifact paths

Inputs:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_3_full_ann/
applications/mnist_v2_nxtf/artifacts/p08_3_5c_source_recovered_conversion/
```

Candidate/final P08.4.1 output:

```text
applications/mnist_v2_nxtf/artifacts/p08_4_1_official_test/
```

The artifact root remains git-ignored.

## Verification command

Run from the accepted `.venv-p08` environment:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_4_1_official_test_evaluation.sh
```

## Acceptance condition

P08.4.1 may be accepted when:

1. all contract/regression tests pass;
2. exact P08.3 ANN and source-recovered SNN identities are verified before test loading;
3. all 10,000 official test examples are evaluated for both ANN and SNN;
4. the primary SNN horizon remains exactly 100 timesteps;
5. ANN and SNN metrics/result fingerprints are internally reproducible;
6. SNN execution is nondegenerate and propagates activity through all hidden stages; and
7. the manifest confirms zero post-test selection/tuning decisions.

P08.4.1 acceptance does not complete P08.4. The remaining P08.4 work is deterministic ordering/conformance validation for the exact deployment and representative physical K26 execution with PL-cycle/resource evidence.
