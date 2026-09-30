# P08.3 ANN training and ANN-to-SNN conversion acceptance

**Status:** Accepted  
**Accepted:** 2026-09-30

## Scope

P08.3 freezes the reconstructed NxTF-style MNIST ANN training policy, selects one ANN checkpoint using only the deterministic validation split, reconstructs the surviving public SNN-Toolbox/NxTF conversion semantics, compiles the converted graph through P06, and measures the converted SNN on the same frozen 5,000-example validation partition before any official-test evaluation.

The official 10,000-image MNIST test split remained locked throughout P08.3.

## Accepted ANN checkpoint

The accepted P08.3.3 ANN artifact is:

```text
checkpoint_sha256=61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2
weights_fingerprint=e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce
epochs_ran=18
best_epoch=13
validation_accuracy=0.992600
validation_loss=0.030356
trainable_parameters=7006
```

Checkpoint selection used only the deterministic 55,000/5,000 train/validation partition. No official-test example, metric, or decision entered checkpoint selection.

## Accepted source-recovered conversion

P08.3.5b/c superseded the earlier blanket-scale P08.3.4 forward artifact after recovering the public NxTF/SNN-Toolbox normalization and readout behavior more faithfully.

Accepted source-recovered conversion properties:

```text
calibration_examples=5500
input_threshold=2040
hidden_thresholds=[556, 512, 672]
softmax_readout_mode=final_membrane_voltage_argmax
softmax_readout_threshold=131071
softmax_output_spike_count_decoder=false
logical_cores=5
resident_contexts=3
physical_engines=1
neurons=4218
expanded_connections=338880
```

Accepted artifact identities:

```text
parameter_fingerprint=9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network_fingerprint=6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled_fingerprint=5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

The earlier P08.3.4 artifact is preserved for audit history but is not the forward-execution artifact for P08.4.

## Accepted validation measurement

P08.3.5d evaluated the exact accepted source-recovered artifact on all 5,000 examples in the frozen validation partition at the primary 100-algorithmic-timestep horizon.

```text
validation_examples=5000
timesteps=100
snn_validation_accuracy=0.984400
ann_validation_reference_accuracy=0.992600
ann_minus_snn_accuracy=0.008200
readout_ties=0
all_equal_evidence_examples=0
zero_evidence_examples=0
final_evidence_range=[-4776,2264]
```

Observed aggregate activity:

```text
input_spikes=5763023
conv1_spikes=3973035
conv2_spikes=2253956
conv3_spikes=245103
stage_active_examples=[5000,5000,5000,5000]
```

Deterministic result identities:

```text
prediction_fingerprint=b71774c429c2418322761e5637280d947fb3299bcfbf6e488795d4be9eee5da2
evidence_fingerprint=06fe833bb68bc3b38f49d27f26b073dc8a3358cb3740fc22ceffc1100878762c
```

There was deliberately no SNN validation-accuracy acceptance threshold and no post-conversion parameter tuning. The measurement was observational: the already-frozen conversion was executed and recorded.

## Data-boundary confirmation

All P08.3 gates report:

```text
official_test_used=false
test_examples_observed=0
```

The official test split was not used for topology selection, ANN checkpoint selection, conversion calibration, threshold selection, readout selection, timestep selection, or validation-based tuning.

## Acceptance decision

P08.3 is accepted.

The ANN checkpoint, source-recovered integer parameters, thresholds, input semantics, readout semantics, 100-timestep primary horizon, P06 mapping, and validation behavior are now frozen for P08.4. P08.4 may evaluate the untouched official test split, but it must not alter these frozen choices in response to test accuracy.
