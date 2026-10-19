# P06-B2.1 — Independent scaled training foundation (NOT TRAINED)

Status: B1 host-software gates B1.1–B1.6 **CLOSED, user-attested on 2026-10-19**. B2.1 **code and synthetic numerical tests committed; native user verification PENDING**. Source branch: agent/v3-p06-b2-training-foundation, stacked on B1 closeout (draft PR #46 still unmerged).

## B2 research identity, experiment boundaries

Independent NEW project 784→1000→10 dense LIF model. Track A accepted 784→32→10 checkpoint, source, tensor hashes, official 94.56% FPGA TEST accuracy and accepted physical baseline remain read-only. No retraining/re-scoring Track A. The official MNIST TEST archive is SEALED for B2 training/hyperparameters/validation. Real B2 training, actual validation accuracy, checkpoints, signed weight freeze and physical deployment have NOT occurred.

Preserve raw uint8 28×28 (784 channels), original quota+phase17 input formula for exactly 25 ticks, a 26th external-free drain tick, signed24 saturating integer recurrence with strict threshold, neural NEXT delivery, reset each image, ten output spike counts and lowest-index tie. Reuse the accepted TRAIN-only canonical gzip IDX parser (strict=True, MD5 verified) with train-derived 50,000 train/10,000 validation split seeded 20261013, not TEST.

## B2.1 deliverables

The frozen Track A IntegerForwardSNN and compact_to_compiler_spec hard-code hidden width 32. A new isolated module, src/loihi_twin_v2/p06_b21_training_foundation.py, now provides:
- B21IntegerSNN: explicit 1–1000 hidden neurons, default 1000; H×784 and 10×H independent trainable weights, same accepted P06-A2.5 signed24 STE/fast-sigmoid numerical kernels imported READ-ONLY. Float64 integer-forward sums and exact 25+1 recurrence.
- B21Settings: PREDECLARED development defaults H=1000, seed=20261019, 8 epochs, batch=64, learning rate=0.05, surrogate width=16 and validation-GO floor=0.60. These are NOT observed performance or final frozen B2.2 hyperparameters until the user approves a real training run.
- Separate graph export to a true P06 NetworkSpec preserving ALL dense edges including zero weights, signed int24 weight bounds, and 10-neuron readout population; B1.2 mapper accepts its output without Track A changes.
- Versioned dimension-bound signed32LE effective integer weight SHA256 and SEEDED_UNTRAINED only metadata; NO checkpoint saved or marked frozen.
- require_train_only_split: canonical 60k TRAIN provenance, 50k/10k disjoint split seed/MD5 metadata and still-sealed TEST admission; this complements, never substitutes for, the strict checksum-verifying existing TRAIN loader.

Independent tests in tests/test_p06_b21_training_foundation.py check new width/seed identity without Track A mutation; strict unsigned-byte inputs and negative/signed24/nonfinite guards; finite surrogate gradients; independent 26-tick source graph monolithic LIF readout counts equal PyTorch integer-forward for signed seeded samples; B1.2 exact packed resource fit, source/packet parity; rejection of synthetic/noncanonical splits. Optional full 1000-hidden graph export/packing is a resource-intensive UNTRAINED synthetic structure gate.

scripts/p06_b21_foundation_probe.py runs small integer-forward and independent oracle parity, optional full B1.2 packing, and always prints B2 training NOT_STARTED / official TEST SEALED.

## Future B2 user-gated stages

B2.2 — Separate actual canonical TRAIN-only fit with deterministic optimizer and full 50k/10k train-derived validation; inspect resource/time feasibility first. Optimize hyperparameters and epoch selection from TRAIN/validation only; measure validation GO and silent rate, never official TEST. No printed validation score predicted here.

B2.3 — Checkpoint integrity, source weight hashing, exact quantized signed24 parity, actual B1.2 core packing and independent B1.4 26-tick validation-image neuron/packet parity; fail closed instead of truncating oversized weights or edges.

B2.4 — Freeze new B2-specific checkpoint, independently checked source/effective tensor SHA256, 27-core or honestly revised packing, per-core exact P02 initial DDR SHA256, validation results, selected TRAIN-derived image IDs, and *predeclared* official TEST protocol before P07-B.

B2.5 — B2 software acceptance and P07-B separate operator-controlled physical plan; no FPGA scaled physical claims before that separately accepted run. If 1000-hidden packing or training fails, predeclare/reassess an intermediate topology without relabeling the model.

## Native PC verification

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/v3-p06-b1-scalable-packing
    git pull --ff-only origin agent/v3-p06-b1-scalable-packing
    git switch agent/v3-p06-b2-training-foundation
    git pull --ff-only origin agent/v3-p06-b2-training-foundation
    source ~/Git/Thesis/.venv-p08/bin/activate
    cd ~/Git/Thesis/Loihi_Digital_Twin/v3

    PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b21_training_foundation.py
    PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b15_paging.py tests/test_p06_b14_differential.py tests/test_p06_b13_streaming.py tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py tests/test_p06_lif_compiler_probe.py tests/test_p06_lif_input_probe.py
    PYTHONPATH="$PWD/src" python -m compileall -q src/loihi_twin_v2/p06_b21_training_foundation.py tests/test_p06_b21_training_foundation.py scripts/p06_b21_foundation_probe.py
    PYTHONPATH="$PWD/src" python scripts/p06_b21_foundation_probe.py --hidden 40 --pack

    # Optional RAM/CPU intensive source/packing only, NO real train:
    P06_B21_1000_SHAPE=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b21_training_foundation.py -k opt_in_full_1000_hidden_dense_graph_export_and_packing
    PYTHONPATH="$PWD/src" python scripts/p06_b21_foundation_probe.py --hidden 1000 --no-numerical --pack

Expected: P06_B21_TRAINING_FOUNDATION_PASS=1 / P06_B21_TRAINING_STATUS=NOT_STARTED / P06_B21_OFFICIAL_TEST_STATUS=SEALED. User native acceptance PENDING; no CI or physical runs performed by assistant. Both B1 and B2 PRs require explicit separate merge authorization.
