# MNIST-06 Dual-Profile Deployment Freeze

**Status:** In progress — freeze tooling implemented; accepted local artifacts must be materialized and committed

## Purpose

MNIST-06 creates an immutable handoff between the accepted software/golden results and the physical FPGA experiments. The physical validation milestones must not depend on whichever checkpoint, deployment image, or test samples happen to exist in a local `build/` directory at run time.

The freeze therefore copies the exact accepted artifacts out of the ignored build tree, verifies them against the SHA-256 values recorded by MNIST-04/05, and stores a deterministic common FPGA-validation corpus.

## Frozen package

The accepted package is generated under:

```text
applications/mnist/frozen/mnist-v1/
```

Expected layout:

```text
mnist-v1/
├── freeze_manifest.json
├── accepted_software_validation.json
├── fpga_validation_corpus.json
├── checkpoints/
│   ├── cropped-dense_snn_float.npz
│   └── native-sparse_snn_float.npz
└── deployments/
    ├── cropped-dense/
    │   ├── deployment.json
    │   └── weight_image/
    │       ├── weight_storage.json
    │       ├── weight_formats.mem
    │       ├── weight_synapses.mem
    │       └── weight_axon_rows.mem
    └── native-sparse/
        ├── deployment.json
        └── weight_image/
            ├── weight_storage.json
            ├── weight_formats.mem
            ├── weight_synapses.mem
            └── weight_axon_rows.mem
```

The freeze manifest records the accepted validation hash, common-corpus hash, checkpoint hashes, deployment file hashes, 16-tick application contract, and compact accepted golden-result summaries.

## Common FPGA-validation corpus

The physical corpus contains exactly **30 original MNIST test indices**, and the same source indices are used for both profiles.

For each true digit class `0..9`, the selector requests three deterministic cases in this order:

1. **both-correct** — both accepted golden deployments classify the image correctly;
2. **profile-divergent** — the two accepted golden deployments produce different predictions;
3. **both-wrong** — both accepted golden deployments misclassify the image.

The first unused source index satisfying each category is selected. If a particular category is absent for a class, the selector uses the first unused class-local sample and records the fallback explicitly. This policy gives the FPGA corpus all ten classes while intentionally including easy, profile-sensitive, and difficult behavior.

The corpus file records each source test index, true label, both accepted golden predictions, correctness flags, and the selection reason. It does **not** become an FPGA expected-output input. Physical hardware still receives only static configuration and encoded external events; expected results remain host-side validation evidence.

## Generation

After the full MNIST-04/05 accepted validation artifacts are present locally, run:

```bash
python applications/mnist/scripts/freeze_deployment.py
```

Then verify the complete package independently:

```bash
python applications/mnist/scripts/validate_frozen_deployment.py
```

The validator recomputes every stored SHA-256 digest, verifies both profiles are present, verifies the 16-tick contract, and requires exactly 30 unique corpus samples with three samples from every digit class.

## Source-control policy

`applications/mnist/build/` remains generated/ignored. The `applications/mnist/frozen/mnist-v1/` package is intentionally source-controlled because it is the immutable application artifact consumed by MNIST-07 and later physical experiments.

Any retraining, re-quantization, change of test-corpus policy, or regenerated deployment whose hash differs from the accepted package constitutes a new freeze version rather than a silent replacement of `mnist-v1`.

## Relation to physical conformance

MNIST-07 will reuse the established M12 multi-tick physical-conformance boundary:

- Python/golden tooling constructs the static load image and per-tick **external** event schedule;
- the FPGA receives those physical inputs only;
- no expected state, spike, or prediction data is fed to the fabric;
- post-commit physical captures are compared host-side against independent golden traces.

The MNIST application does not introduce a second definition of FPGA correctness.

## Completion criteria

MNIST-06 closes when:

- the accepted full-test MNIST-04/05 validation artifacts are the freeze source;
- both accepted checkpoints are copied and their hashes match;
- both accepted deployment images are copied and every file hash matches;
- `fpga_validation_corpus.json` contains the frozen 30-image common corpus;
- `validate_frozen_deployment.py` passes on the materialized package;
- the entire `applications/mnist/frozen/mnist-v1/` directory is committed to the repository; and
- the application milestone document records the resulting freeze as the sole MNIST-07 input package.
