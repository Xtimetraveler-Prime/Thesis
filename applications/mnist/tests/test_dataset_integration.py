import pytest

pytest.importorskip("tensorflow")

from mnist_app.dataset import load_mnist
from mnist_app.encoding import encode_event_schedule


def test_real_mnist_sample_encodes_repeatably():
    dataset = load_mnist()
    assert dataset.x_train.shape == (60000, 28, 28)
    assert dataset.x_test.shape == (10000, 28, 28)
    image = dataset.x_test[0]
    first = encode_event_schedule(image)
    second = encode_event_schedule(image.copy())
    assert first == second
    assert any(first)
