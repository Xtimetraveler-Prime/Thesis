from __future__ import annotations

import numpy as np
import pytest

import mnist_v2_nxtf.training as training
from mnist_v2_nxtf.policy import ANN_POLICY, OFFICIAL_TEST_POLICY
from mnist_v2_nxtf.training import (
    EpochRecord,
    FULL_TRAINING_MODE,
    TrainingArrays,
    checkpoint_is_better,
    make_smoke_training_arrays,
    train_arrays,
)


def test_training_module_does_not_expose_broad_test_loader():
    # P08.3 training imports only the training-only loader. The broad load_mnist
    # helper is reserved for later P08.4 evaluation.
    assert "load_mnist" not in training.__dict__
    assert OFFICIAL_TEST_POLICY == "LOCKED_UNTIL_P08_3_CHECKPOINT_AND_CONVERSION_FREEZE"


def test_checkpoint_selection_uses_frozen_metric_and_tiebreakers():
    epoch1 = EpochRecord(1, 1.0, 0.5, 0.4, 0.90)
    epoch2 = EpochRecord(2, 0.8, 0.6, 0.5, 0.91)
    epoch3 = EpochRecord(3, 0.7, 0.7, 0.3, 0.91)
    epoch4 = EpochRecord(4, 0.6, 0.8, 0.3, 0.91)

    assert checkpoint_is_better(epoch1, None)
    assert checkpoint_is_better(epoch2, epoch1)  # higher val accuracy
    assert checkpoint_is_better(epoch3, epoch2)  # equal acc, lower val loss
    assert not checkpoint_is_better(epoch4, epoch3)  # exact tie -> earlier epoch


def test_smoke_corpus_is_deterministic_balanced_and_not_mnist_sized():
    first = make_smoke_training_arrays()
    second = make_smoke_training_arrays()
    assert first.mode == "deterministic-smoke"
    assert first.x_train.shape == (80, 28, 28, 1)
    assert first.y_train.shape == (80, 10)
    assert first.x_validation.shape == (20, 28, 28, 1)
    assert first.y_validation.shape == (20, 10)
    assert np.array_equal(first.x_train, second.x_train)
    assert np.array_equal(first.y_train, second.y_train)
    assert first.dataset_fingerprint == second.dataset_fingerprint
    assert first.split_fingerprint == second.split_fingerprint
    assert np.allclose(first.y_train.sum(axis=0), np.full(10, 8.0))
    assert np.allclose(first.y_validation.sum(axis=0), np.full(10, 2.0))


def test_full_training_cannot_silently_use_shortened_epoch_policy(tmp_path):
    tiny = TrainingArrays(
        x_train=np.zeros((1, 28, 28, 1), dtype=np.float32),
        y_train=np.eye(10, dtype=np.float32)[[0]],
        x_validation=np.zeros((1, 28, 28, 1), dtype=np.float32),
        y_validation=np.eye(10, dtype=np.float32)[[0]],
        split_fingerprint="split",
        dataset_fingerprint="dataset",
        mode=FULL_TRAINING_MODE,
    )
    with pytest.raises(ValueError, match="frozen maximum epoch policy"):
        train_arrays(tiny, tmp_path, max_epochs=1)


def test_training_policy_limits_are_still_frozen():
    assert ANN_POLICY.batch_size == 32
    assert ANN_POLICY.max_epochs == 30
    assert ANN_POLICY.early_stopping_patience == 5
    assert ANN_POLICY.checkpoint_metric == "val_accuracy"
    assert ANN_POLICY.checkpoint_tiebreakers == ("min_val_loss", "earliest_epoch")
