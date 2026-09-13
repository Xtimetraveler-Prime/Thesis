# Soft-Computing Notebook Reuse

The initial MNIST application work reuses ideas and workflow from two user-authored class notebooks:

- `A-Baseline.ipynb`
- `BCD-ExpAndError-Copy1.ipynb`

The reusable pieces are the TensorFlow/Keras MNIST loader, train/test split, class-label handling, accuracy evaluation, `argmax` prediction logic, and incorrect-sample analysis pattern. The notebooks also establish conventional ANN reference results for 32-, 128-, and 512-unit hidden layers.

The deployable application does **not** copy the dense ReLU models directly. The platform requires spike-event input and LIF output dynamics, so the application training code replaces the ANN forward path with a direct spiking classifier while retaining the familiar TensorFlow dataset/training workflow.

One notebook variable named `probabilities` actually contains logits because its final `Dense(10)` layer has no softmax and the loss uses `from_logits=True`. The application code therefore avoids calling raw class scores probabilities unless an explicit softmax/calibration step is applied.

Recorded notebook reference results are retained only as conventional-ANN context:

| Model | Recorded MNIST test accuracy |
|---|---:|
| 784 -> 32 ReLU -> 10 | 95.8% |
| 784 -> 128 ReLU -> 10 | 97.7% |
| 784 -> 512 ReLU -> 10 | 98.2% |

These values are not expected SNN accuracy and are not used as FPGA correctness criteria.
