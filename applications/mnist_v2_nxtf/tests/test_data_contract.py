from __future__ import annotations

import numpy as np

from mnist_v2_nxtf import PRIMARY_TIMESTEPS, TOPOLOGY_STATUS
from mnist_v2_nxtf.data import encode_binary_spikes, stratified_train_validation_indices


def test_p08_reconstruction_is_accepted_while_p08_2_is_pending():
    assert TOPOLOGY_STATUS == "P08_1_RECONSTRUCTION_ACCEPTED_P08_2_PENDING"
    assert PRIMARY_TIMESTEPS == 100


def test_p08_split_is_stratified_and_deterministic():
    labels = np.repeat(np.arange(10, dtype=np.int64), 6000)
    train_a, val_a = stratified_train_validation_indices(labels)
    train_b, val_b = stratified_train_validation_indices(labels)
    assert np.array_equal(train_a, train_b)
    assert np.array_equal(val_a, val_b)
    assert len(train_a) == 55_000
    assert len(val_a) == 5_000
    assert np.bincount(labels[val_a], minlength=10).tolist() == [500] * 10


def test_p08_rate_encoding_is_deterministic_and_exact_count():
    image = np.zeros((28, 28), dtype=np.uint8)
    image[0, 0] = 255
    image[0, 1] = 128
    spikes = encode_binary_spikes(image, timesteps=100)
    assert spikes.shape == (1, 100, 784)
    assert int(spikes[0, :, 0].sum()) == 100
    assert int(spikes[0, :, 1].sum()) == 50
    assert np.array_equal(spikes, encode_binary_spikes(image, timesteps=100))
