# Soft-Computing Notebook Reuse

The MNIST application deliberately repurposes software patterns from two user-authored class notebooks:

- `A-Baseline.ipynb`
- `BCD-ExpAndError-Copy1.ipynb`

The notebooks are treated as source material for this application track rather than as external reference code.

## Directly reusable workflow

The following pieces carry over with little or no conceptual change:

- `tf.keras.datasets.mnist.load_data()` and the standard 60,000/10,000 train/test split;
- NumPy/TensorFlow array handling;
- the normalization concept `pixel / 255.0`;
- TensorFlow/Keras training infrastructure;
- Adam optimization;
- `SparseCategoricalCrossentropy(from_logits=True)`;
- training-time measurement with `time.perf_counter()`;
- test-set accuracy evaluation;
- `np.argmax(..., axis=1)` class prediction;
- `np.where(predicted != y_test)[0]` incorrect-sample indexing;
- inspection/visualization of difficult or incorrectly classified samples.

The application keeps these familiar pieces where they remain appropriate, while changing the forward model and deployment constraints.

## What must change for the neuromorphic application

The notebook models use `Flatten -> Dense(ReLU) -> Dropout -> Dense(10)`. That forward path is not the deployable network because the project core consumes spike events and implements LIF-style state, threshold, reset, decay, integer weights, and repeated algorithmic ticks.

The application therefore replaces the ANN forward pass with direct spiking classifiers while retaining the notebook training/evaluation workflow around them.

Two profiles are trained:

```text
cropped-dense: 400 inputs -> 10 LIF outputs, <=4000 stored synapses
native-sparse: 784 inputs -> 10 LIF outputs, <=4096 stored synapses
```

The native-sparse profile additionally adds magnitude pruning and masked fine-tuning after initial training.

## Notebook reference results

The class experiments provide useful conventional-ANN context:

| Model | Recorded MNIST test accuracy |
|---|---:|
| 784 -> 32 ReLU -> 10 | 95.8% |
| 784 -> 128 ReLU -> 10 | 97.7% |
| 784 -> 512 ReLU -> 10 | 98.2% |

These are reference ANN results only. They are not expected SNN accuracy and are not FPGA correctness criteria.

## Terminology correction carried into the application

`BCD-ExpAndError-Copy1.ipynb` stores `modelC.predict(x_test)` in a variable named `probabilities`, but the final layer is `Dense(10)` without softmax and the loss uses `from_logits=True`. Those values are logits, not calibrated probabilities.

The application therefore uses neutral terms such as `scores`, `spike_counts`, or `logits` as appropriate. A value is called a probability only after an explicit probability transformation/calibration step.

## Why the reuse is valuable

Keeping the notebook's dataset, optimizer, loss, evaluation, timing, and error-analysis structure reduces unnecessary reinvention. At the same time, isolating the changed SNN forward path makes it easier to attribute differences between the class ANN results, floating SNNs, quantized golden-model deployments, and eventual FPGA results.
