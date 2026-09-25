# MNIST-v1 Preservation Completion

Status: COMPLETE
Date: 2026-09-25

This completion note supersedes the earlier in-progress status in
MNIST_V1_PRESERVATION_AUDIT.md.

Preservation results:
- archived MNIST-09 physical reruns: PASS for both profiles
- archived MNIST-10 physical timing reruns: PASS for both profiles
- fresh-clone HLS regeneration: PASS
- fresh-clone MNIST-09 rebuild: PASS
- fresh-clone MNIST-10 rebuild: PASS
- rebuilt MNIST-09 physical reruns: PASS for both profiles
- rebuilt MNIST-10 physical timing reruns: PASS for both profiles
- final tracked-source status after rebuild: clean

The full artifact hashes, package hashes, environment capture, implementation
reports, Vivado logs, and physical-run logs are retained in the external
preservation archive created during the audit.

No further FPGA execution is required for this preservation phase.

Remaining repository-management work is to create the final source tag, publish
the preservation bundles and checksum manifest as release assets, rename the
first MNIST application as the historical baseline, and then begin the Loihi-1
target-architecture phase.
