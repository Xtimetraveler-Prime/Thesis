# MNIST-04/05 Accepted Quantization and Golden-Model Validation

**Status:** Accepted

## Purpose

This document records the accepted software-to-golden transition for the two MNIST FPGA-v1 deployment profiles. The goal is to measure the effect of converting the accepted floating-point SNN checkpoints into the project's integer encoded-weight representation and then executing the exported deployments through the validated `NeuromorphicCore`.

The floating-point SNN and quantized golden deployment are evaluated on the **same official MNIST test samples**. This avoids the subset mismatch present in earlier smoke tests and makes the reported accuracy delta a direct quantization/deployment measurement.

## Validation flow

```text
accepted float checkpoint
        |
        v
hardware-aware weight/threshold quantization
        |
        v
M08 CSR weight-storage image
        |
        v
FPGA-v1 neuron configuration
        |
        v
validated NeuromorphicCore
        |
        v
same MNIST test images as float model
```

No expected classifications, spike counts, or state traces are supplied to the golden core. It receives only the exported configuration and encoded image-event schedule.

## Full official test-set results

The accepted validation was run over all 10,000 official MNIST test images.

| Profile | Float SNN accuracy | Quantized golden accuracy | Golden - float | Prediction agreement | Stored synapses |
|---|---:|---:|---:|---:|---:|
| cropped-dense | 90.29% | 90.24% | -0.05 percentage points | 99.25% | 3,893 |
| native-sparse | 91.62% | 91.71% | +0.09 percentage points | 99.30% | 4,086 |

The changes are small enough that the quantized deployment is effectively behavior-preserving at the application level. The small positive delta for native-sparse should not be interpreted as quantization intrinsically improving the model; a small number of changed decisions happened to alter the aggregate accuracy slightly in the favorable direction.

## Quantization-induced sparsity

The accepted floating checkpoints contain:

```text
cropped-dense: 4,000 nonzero float weights
native-sparse: 4,096 nonzero float weights
```

After integer quantization, some small-magnitude values round exactly to zero:

```text
cropped-dense: 3,893 stored synapses  (107 removed by quantization)
native-sparse: 4,086 stored synapses  (10 removed by quantization)
```

This is legal under the FPGA-v1 storage contract and reduces storage/activity slightly without a meaningful loss in classification accuracy.

## Smoke-validation consistency

Before the full run, the same accepted-validation path was executed on the first 100 official test images:

| Profile | Float | Golden | Delta | Agreement | Stored synapses |
|---|---:|---:|---:|---:|---:|
| cropped-dense | 93.0% | 94.0% | +1.0 pp | 99.0% | 3,893 |
| native-sparse | 95.0% | 95.0% | 0.0 pp | 100.0% | 4,086 |

The larger apparent cropped-dense delta on 100 images disappears on the full test set, illustrating why the 10,000-image matched evaluation is the accepted result.

## Completion evidence

The accepted-validation workflow:

- validates checkpoint profile, shape, presentation length, and connection budget;
- exports the checkpoint into the existing encoded-weight and CSR storage contract;
- instantiates the actual project `NeuromorphicCore` with FPGA-v1 arithmetic;
- evaluates float and quantized models on identical source MNIST indices;
- records accuracy, prediction agreement/disagreement, confusion matrix, incorrect indices, tick-by-tick accuracy, input events, output spikes, synaptic visits, no-spike cases, and ties;
- records quantization parameters and errors in the generated deployment/validation manifests; and
- records SHA-256 hashes of accepted checkpoint/deployment artifacts for later deployment freeze.

The application pytest suite passed in the user application environment before both accepted validation runs.

## Interpretation

The accepted result supports two conclusions relevant to the thesis:

1. The hardware-aware quantization/export process preserves the trained classifiers closely enough that quantization is not the dominant source of application error.
2. The native-sparse profile remains the stronger of the two classifiers after integer conversion while preserving the full 28x28 MNIST input representation.

These results close MNIST-04 and MNIST-05. MNIST-06 freezes the exact accepted deployments, hashes, and shared FPGA-validation corpus before any physical-board application experiment begins.
