# MNIST Application

This directory contains the MNIST application track built on top of the validated
neuromorphic digital-twin platform.

The application should consume the existing Python/FPGA core interfaces rather
than duplicate or silently modify the baseline computational model. If MNIST
exposes a genuine platform limitation, any resulting core change should be
tracked explicitly in the main platform development history instead of being
hidden inside application code.

Application progress is tracked in [`MILESTONES.md`](MILESTONES.md).

Planned work in this directory includes:

- deterministic MNIST-to-spike encoding;
- SNN training and hardware-aware quantization;
- export into the project's neuron/synapse configuration format;
- inference and evaluation on the Python golden model;
- FPGA deployment and Python/FPGA conformance testing; and
- application-level characterization and comparison with published Loihi MNIST
  results where the measurement boundaries are defensibly comparable.

Subdirectories for source, tests, FPGA integration, configuration, and generated
results will be added as those parts of the application are implemented.
