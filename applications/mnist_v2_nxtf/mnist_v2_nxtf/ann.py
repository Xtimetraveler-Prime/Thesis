"""Keras construction helpers for the frozen P08.3 ANN contract.

This module builds and compiles the accepted reconstructed topology but does not
load MNIST, train a model, inspect the official test split, or perform conversion.
"""

from __future__ import annotations

from .policy import ANN_POLICY, validate_frozen_policy


EXPECTED_ANN_PARAMETERS = 7_006
EXPECTED_LAYER_OUTPUTS = (
    (12, 12, 14),
    (10, 10, 20),
    (4, 4, 12),
    (1, 1, 10),
)


def configure_determinism(seed: int | None = None) -> None:
    """Configure the TensorFlow process for the frozen deterministic policy."""

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required for P08.3. Install the P08 application with "
            "its 'train' extra."
        ) from exc

    chosen_seed = ANN_POLICY.random_seed if seed is None else int(seed)
    tf.keras.utils.set_random_seed(chosen_seed)
    if ANN_POLICY.deterministic_ops:
        tf.config.experimental.enable_op_determinism()


def build_ann(*, configure_seed: bool = True):
    """Build the frozen 14->20->12->10 all-convolutional Keras model."""

    validate_frozen_policy()
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required for P08.3. Install the P08 application with "
            "its 'train' extra."
        ) from exc

    if configure_seed:
        configure_determinism()

    inputs = tf.keras.Input(shape=(28, 28, 1), name="mnist_frame")
    x = inputs
    filters = (*ANN_POLICY.topology_filters, ANN_POLICY.output_classes)
    kernels = ((5, 5), (3, 3), (3, 3), (4, 4))
    strides = ((2, 2), (1, 1), (2, 2), (1, 1))

    observed_shapes: list[tuple[int, int, int]] = []
    for layer_index, (channels, kernel, stride) in enumerate(
        zip(filters, kernels, strides, strict=True), start=1
    ):
        is_output = layer_index == 4
        x = tf.keras.layers.Conv2D(
            filters=channels,
            kernel_size=kernel,
            strides=stride,
            padding="valid",
            activation=(
                ANN_POLICY.output_activation if is_output else ANN_POLICY.hidden_activation
            ),
            use_bias=ANN_POLICY.use_bias,
            name=f"conv{layer_index}",
        )(x)
        observed_shapes.append(tuple(int(dim) for dim in x.shape[1:]))
        if layer_index in ANN_POLICY.dropout_after_hidden_layers:
            x = tf.keras.layers.Dropout(
                ANN_POLICY.dropout_rate,
                seed=ANN_POLICY.random_seed + layer_index,
                name=f"dropout{layer_index}",
            )(x)

    outputs = tf.keras.layers.Flatten(name="class_scores")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="p08_nxtf_reconstruction")

    if tuple(observed_shapes) != EXPECTED_LAYER_OUTPUTS:
        raise AssertionError(
            f"ANN spatial contract drifted: {tuple(observed_shapes)} != {EXPECTED_LAYER_OUTPUTS}"
        )
    if model.count_params() != EXPECTED_ANN_PARAMETERS:
        raise AssertionError(
            f"ANN parameter contract drifted: {model.count_params()} != {EXPECTED_ANN_PARAMETERS}"
        )
    if tuple(model.output_shape) != (None, 10):
        raise AssertionError(f"ANN output shape drifted: {model.output_shape}")
    return model


def compile_ann(model=None):
    """Compile the frozen ANN with the policy's optimizer/loss contract."""

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required for P08.3. Install the P08 application with "
            "its 'train' extra."
        ) from exc

    model = build_ann() if model is None else model
    optimizer = tf.keras.optimizers.Adam(learning_rate=ANN_POLICY.learning_rate)
    model.compile(
        optimizer=optimizer,
        loss=ANN_POLICY.loss,
        metrics=["accuracy"],
    )
    return model
