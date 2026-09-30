from __future__ import annotations

import pytest


tf = pytest.importorskip("tensorflow")

from mnist_v2_nxtf.ann import EXPECTED_ANN_PARAMETERS, EXPECTED_LAYER_OUTPUTS, build_ann, compile_ann


def test_p08_3_ann_builder_matches_frozen_topology_and_parameter_count():
    model = build_ann()

    assert model.input_shape == (None, 28, 28, 1)
    assert model.output_shape == (None, 10)
    assert model.count_params() == EXPECTED_ANN_PARAMETERS == 7_006

    conv_layers = [layer for layer in model.layers if isinstance(layer, tf.keras.layers.Conv2D)]
    assert [layer.filters for layer in conv_layers] == [14, 20, 12, 10]
    assert [tuple(layer.kernel_size) for layer in conv_layers] == [(5, 5), (3, 3), (3, 3), (4, 4)]
    assert [tuple(layer.strides) for layer in conv_layers] == [(2, 2), (1, 1), (2, 2), (1, 1)]
    assert [tuple(layer.output.shape[1:]) for layer in conv_layers] == list(EXPECTED_LAYER_OUTPUTS)
    assert all(layer.use_bias for layer in conv_layers)

    dropout_layers = [layer for layer in model.layers if isinstance(layer, tf.keras.layers.Dropout)]
    assert len(dropout_layers) == 3
    assert [layer.rate for layer in dropout_layers] == [0.1, 0.1, 0.1]


def test_p08_3_ann_compile_contract_uses_adam_and_categorical_crossentropy():
    model = compile_ann()

    assert isinstance(model.optimizer, tf.keras.optimizers.Adam)
    assert float(tf.keras.backend.get_value(model.optimizer.learning_rate)) == pytest.approx(1e-3)
    assert model.loss == "categorical_crossentropy"
