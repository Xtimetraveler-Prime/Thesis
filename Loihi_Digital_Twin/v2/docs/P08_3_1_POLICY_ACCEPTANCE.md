# P08.3.1 Training/Conversion Policy Freeze Acceptance

**Accepted:** 2026-09-30  
**Branch:** `agent/p08.3-training-conversion-freeze`  
**Status:** accepted; P08.3.2 training-pipeline development may proceed

## Acceptance basis

P08.3.1 froze the ANN-training and ANN-to-SNN conversion policy before any new
training run. Diego independently reran `scripts/run_p08_3_policy_preflight.sh`
after the stale moving-phase assertion in `test_data_contract.py` was corrected
and reported that the gate completed successfully.

The accepted policy preserves the P08.1 reconstruction and the P08.2 execution
boundary:

```text
ANN topology:          14 -> 20 -> 12 -> 10 all-convolutional reconstruction
trainable parameters:  7,006
P06 logical cores:     5
resident K26 contexts: 3
physical HLS engines:  1
primary SNN horizon:   100 algorithmic timesteps
```

## Frozen ANN policy

The accepted ANN policy uses TensorFlow/Keras, ReLU hidden convolutional layers,
a softmax output convolution, learned biases, 0.1 dropout after the first three
convolutions, Adam with learning rate `1e-3`, categorical cross-entropy, batch
size 32, at most 30 epochs, and validation-only checkpoint selection. A fixed
5,000-image stratified validation subset is removed from the official 60,000
MNIST training split; the remaining 55,000 images are the only examples used for
weight updates.

The exact 30-epoch/early-stopping schedule is a project reconstruction decision,
not a recovered NxTF benchmark fact.

## Frozen conversion policy

The accepted conversion policy retains the paper's 100-timestep primary horizon
and SNN-Toolbox-style rate-conversion target. Historical public Loihi examples
support the selected 8-bit weight, 12-bit bias, threshold-normalization, and
threshold-mantissa references. FPGA-v2 keeps its already validated hard
reset-to-zero compartment behavior rather than claiming equivalence to the
historical SNN Toolbox soft-reset configuration.

All source-backed, source-style, project-reconstruction, and unknown fields are
classified explicitly in `mnist_v2_nxtf/policy.py` and
`docs/P08_3_TRAINING_CONVERSION_FREEZE.md`.

## Test-set lock

The official 10,000-image MNIST test split remains locked. P08.3.2 may train,
select checkpoints, and prepare conversion calibration only from the training
remainder and fixed validation split. No test-set accuracy may be observed until
the checkpoint and conversion/decoder contract are frozen for P08.4 evaluation.

## Next gate

P08.3.2 must first prove the training pipeline itself before the full ANN run:

1. deterministic train/validation preparation;
2. validation-only checkpoint selection using the frozen primary metric and
   tie-breakers;
3. bounded early stopping;
4. model/checkpoint serialization;
5. immutable run manifest and artifact fingerprints;
6. explicit `official_test_used=false` evidence; and
7. a small deterministic smoke training run that exercises the same pipeline
   without selecting policy from its result.

Only after that gate is independently accepted should the full 55k/5k ANN
training run be used to choose the P08 checkpoint.
