# Applications

Application workloads are separated by architectural generation.

- `mnist_baseline/` is the preserved FPGA-v1 MNIST reference workload. Its frozen deployment, evidence, scripts, and historical documentation remain available for regression and comparison.
- Future deeper-MNIST work for the Loihi-like FPGA-v2 architecture should use a separate application directory rather than modifying the baseline in place.

The immutable pre-rename source state is tagged `fpga-v1-mnist-v1-final`.
