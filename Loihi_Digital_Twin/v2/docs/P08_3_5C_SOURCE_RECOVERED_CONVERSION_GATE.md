# P08.3.5c Source-Recovered Conversion + P06 Compile Gate

**Status:** Verification candidate  
**Official MNIST test split:** locked  
**Classification accuracy:** not evaluated in this gate

## Purpose

P08.3.5c converts the accepted ANN using the source semantics recovered and independently verified in P08.3.5b, then freezes and compiles that graph through P06.

This gate intentionally does **not** overwrite or delete the earlier P08.3.4 artifact. P08.3.4 remains an audit record of the incomplete blanket-scale reconstruction. For forward execution, P08.3.5c supersedes it with the recovered Intel NxTF/SNN-Toolbox normalization behavior.

## Source-recovered semantics carried forward

The conversion uses:

```text
frame input scale:                  255
input mode:                         BIAS-frame reconstruction
parameter percentile:              100
activation / dV/dt percentile:     99.999
desired threshold/input ratio:     8
threshold normalization:           per layer
bias scale propagation:            previous-layer slope
hidden reset:                      hard reset to zero (project FPGA-v2 adaptation)
```

The independent P08.3.5b run recovered:

```text
input threshold: 2040
conv1 threshold: 556
conv2 threshold: 512
conv3 threshold: 672
```

P08.3.5c recomputes these values from the accepted ANN/calibration corpus; it does not simply hard-code them as tuning constants.

## Ingress boundary

Intel's frame-input path uses an NxTF input layer driven by pixel bias currents. The project P06 graph keeps `pixels` as an external input population so the accepted benchmark computational graph remains:

```text
4,218 computational neurons
338,880 expanded convolutional connections
```

The host/ingress layer is therefore responsible for reproducing the recovered input-neuron behavior (`input_scale=255`, calibrated threshold, hard reset) and emitting pixel spike events into the existing external-input routes.

The 784 source pixels are not added to the P06 benchmark neuron count.

## Softmax readout boundary

Intel's public backend states that a softmax output uses its voltage trace and sets its threshold to maximum rather than treating it as an ordinary hidden spiking layer.

P08.3.5c therefore represents conv4 with:

```text
readout mode:       final membrane voltage argmax
readout threshold:  2^17 - 1 = 131071
spike-count decoder: disabled
```

The final ten conv4 compartment voltages after the 100-timestep execution window are the classification evidence. The official validation accuracy is not measured in this gate.

## Integer representation boundary

The recovered public NxTF backend quantizes layer parameters using its own per-layer scale and integer conversion before passing them to NxTF/NxSDK.

P08.3.5c stores those recovered integer values directly in the project graph. It does **not** claim that the project's synapse/bias encoding is bit-for-bit identical to native Loihi's exponent/mantissa micro-encoding. What is preserved here is the source-recovered layer-scale arithmetic at the accepted project execution boundary.

## P06 compile requirements

The gate requires the source-recovered graph to preserve:

```text
computational neurons:      4,218
expanded connections:     338,880
P06 logical cores:               5
K26 resident contexts:           3
physical HLS engines:            1
```

The graph must compile using the existing P08/P06 mapping policy (`900` compartments/core). No graph reduction is allowed to avoid paging.

## Generated local artifact

On success:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_5c_source_recovered_conversion/
├── source_backend_manifest.json
├── source_backend_parameters.npz
├── source_recovered_conversion_manifest.json
├── source_recovered_parameters.npz
├── source_recovered_network.json
└── source_recovered_compiled_deployment.json
```

Generated artifacts remain Git-ignored.

## Acceptance boundary

P08.3.5c passes only if:

1. the exact accepted P08.3.3 ANN checkpoint is used;
2. the frozen 5,500-example training-only calibration set is used;
3. per-layer recovered source normalization is recomputed;
4. hidden thresholds in the compiled graph exactly match the recovered calibration thresholds;
5. conv4 uses maximum-threshold membrane-voltage readout semantics;
6. the graph remains 4,218 neurons / 338,880 expanded connections;
7. P06 compiles the graph to exactly five logical cores;
8. parameter, network, deployment, and manifest fingerprints recompute;
9. the superseded P08.3.4 artifact is preserved rather than silently rewritten;
10. no classification accuracy is evaluated; and
11. `official_test_used=false` and `test_examples_observed=0` remain explicit.

If accepted, the next gate will execute the source-recovered artifact over validation data at 100 timesteps and decode the ten final conv4 membrane voltages. That will be the first classification measurement after the source-semantics correction.
