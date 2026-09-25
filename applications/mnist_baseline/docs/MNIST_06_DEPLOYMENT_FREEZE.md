# MNIST-06 Dual-Profile Deployment Freeze

**Status:** Complete

## Purpose

MNIST-06 creates an immutable handoff between the accepted software/golden results and the physical FPGA experiments. The physical validation milestones must not depend on whichever checkpoint, deployment image, or test samples happen to exist in a local `build/` directory at run time.

The freeze therefore copies the exact accepted artifacts out of the ignored build tree, verifies them against the SHA-256 values recorded by MNIST-04/05, and stores a deterministic common FPGA-validation corpus.

## Frozen package

The accepted package is committed under:

```text
applications/mnist/frozen/mnist-v1/
```

Layout:

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

## Accepted freeze evidence

The materialized `mnist-v1` package was generated from the accepted full-test MNIST-04/05 artifacts, independently validated in the user application environment, and committed to `agent/mnist-06-deployment-freeze`.

Key immutable identifiers are:

```text
accepted_software_validation.json SHA-256:
  ae0ea737338c8c7a9f11d0783542858faec2833b3c3a5bbe07571dfa57fc5734

fpga_validation_corpus.json SHA-256:
  ee5ea48bfec7f120f702455f68aabe02dd20860d49708b27370d14ebd1fefc4f

cropped-dense checkpoint SHA-256:
  a0a116e638c410c92f49948cc4c608525fb11fe400f9e80fa0600e9b62d90d22

native-sparse checkpoint SHA-256:
  d70bfec246b9fa0e391531bebaf4608d96e33616e7b8c49238ec380c09c93361
```

The frozen deployment summaries retain the accepted full-test results:

| Profile | Float accuracy | Golden accuracy | Stored synapses | Prediction agreement |
|---|---:|---:|---:|---:|
| cropped-dense | 90.29% | 90.24% | 3,893 | 99.25% |
| native-sparse | 91.62% | 91.71% | 4,086 | 99.30% |

## Common FPGA-validation corpus

The physical corpus contains exactly **30 original MNIST test indices**, and the same source indices are used for both profiles.

For each true digit class `0..9`, the selector requests three deterministic cases in this order:

1. **both-correct** — both accepted golden deployments classify the image correctly;
2. **profile-divergent** — the two accepted golden deployments produce different predictions;
3. **both-wrong** — both accepted golden deployments misclassify the image.

The materialized accepted corpus contains all three requested categories for every digit class; no fallback case was required. The resulting indices are frozen in `fpga_validation_corpus.json`.

The corpus file records each source test index, true label, both accepted golden predictions, correctness flags, and the selection reason. It does **not** become an FPGA expected-output input. Physical hardware still receives only static configuration and encoded external events; expected results remain host-side validation evidence.

## Generation and validation

The package is generated with:

```bash
python applications/mnist/scripts/freeze_deployment.py
```

and independently checked with:

```bash
python applications/mnist/scripts/validate_frozen_deployment.py
```

The validator recomputes every stored SHA-256 digest, verifies both profiles are present, verifies the 16-tick contract, and requires exactly 30 unique corpus samples with three samples from every digit class. The accepted materialized package passed this validator before being committed.

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

## Closure

All MNIST-06 completion criteria are satisfied. The committed `applications/mnist/frozen/mnist-v1/` package is the sole accepted input package for MNIST-07 and later FPGA application milestones.
