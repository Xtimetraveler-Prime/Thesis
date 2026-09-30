"""Frozen P08.3 ANN-training and ANN-to-SNN conversion policy.

The policy intentionally distinguishes values supported by the NxTF paper or
surviving public NxTF/SNN-Toolbox examples from explicit project reconstruction
choices. The official MNIST test split is not part of any selection or
calibration policy defined here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import CHARACTERIZATION_TIMESTEPS, PRIMARY_TIMESTEPS, VALIDATION_SEED
from .reconstruction import PROPOSED_FILTERS


POLICY_STATUS = "P08_3_1_TRAINING_CONVERSION_POLICY_FROZEN"
OFFICIAL_TEST_POLICY = "LOCKED_UNTIL_P08_3_CHECKPOINT_AND_CONVERSION_FREEZE"

SOURCED_EXACT = "SOURCED_EXACT"
SOURCED_STYLE_OR_RANGE = "SOURCED_STYLE_OR_RANGE"
PROJECT_RECONSTRUCTION = "PROJECT_RECONSTRUCTION"
UNKNOWN_NOT_CLAIMED = "UNKNOWN_NOT_CLAIMED"


@dataclass(frozen=True, slots=True)
class AnnTrainingPolicy:
    framework: str
    topology_filters: tuple[int, int, int]
    output_classes: int
    hidden_activation: str
    output_activation: str
    use_bias: bool
    dropout_rate: float
    dropout_after_hidden_layers: tuple[int, ...]
    input_scale_divisor: float
    optimizer: str
    learning_rate: float
    loss: str
    batch_size: int
    max_epochs: int
    early_stopping_patience: int
    checkpoint_metric: str
    checkpoint_mode: str
    checkpoint_tiebreakers: tuple[str, ...]
    validation_size: int
    random_seed: int
    deterministic_ops: bool
    shuffle_training: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConversionPolicy:
    method: str
    calibration_source: str
    calibration_stride: int
    primary_timesteps: int
    characterization_timesteps: tuple[int, ...]
    weight_bits: int
    weight_sign_mode: str
    weight_quantization_step: int
    weight_rounding: str
    signed_weight_min: int
    signed_weight_max: int
    weight_exponent: int
    bias_bits: int
    signed_bias_min: int
    signed_bias_max: int
    source_bias_exponent_reference: int
    threshold_mantissa: int
    threshold_normalization: bool
    reset_mode: str
    reset_reason: str
    desired_threshold_to_input_ratio: int
    current_decay: int
    voltage_decay: int
    reset_voltage: int
    refractory_ticks: int
    input_encoding: str
    decoder: str
    decoder_tie_break: str
    synapse_encoding_reference: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


ANN_POLICY = AnnTrainingPolicy(
    framework="tensorflow.keras>=2.21,<2.22",
    topology_filters=PROPOSED_FILTERS,
    output_classes=10,
    hidden_activation="relu",
    output_activation="softmax",
    use_bias=True,
    dropout_rate=0.1,
    dropout_after_hidden_layers=(1, 2, 3),
    input_scale_divisor=255.0,
    optimizer="adam",
    learning_rate=1e-3,
    loss="categorical_crossentropy",
    batch_size=32,
    max_epochs=30,
    early_stopping_patience=5,
    checkpoint_metric="val_accuracy",
    checkpoint_mode="max",
    checkpoint_tiebreakers=("min_val_loss", "earliest_epoch"),
    validation_size=5_000,
    random_seed=VALIDATION_SEED,
    deterministic_ops=True,
    shuffle_training=True,
)


CONVERSION_POLICY = ConversionPolicy(
    method="SNN-Toolbox-style rate ANN-to-SNN reconstruction",
    calibration_source="training_remainder_only",
    calibration_stride=10,
    primary_timesteps=PRIMARY_TIMESTEPS,
    characterization_timesteps=CHARACTERIZATION_TIMESTEPS,
    weight_bits=8,
    # Loihi mixed-sign 8-bit mantissas use one sign bit and therefore a
    # two-count precision step: {-256, -254, ..., 0, ..., 252, 254}.
    # This is distinct from a conventional two's-complement int8 range.
    weight_sign_mode="mixed",
    weight_quantization_step=2,
    weight_rounding="toward_zero",
    signed_weight_min=-256,
    signed_weight_max=254,
    weight_exponent=0,
    bias_bits=12,
    # Keep the existing conservative project bias range until a later source
    # audit needs the full native Loihi bias-mantissa range.
    signed_bias_min=-2047,
    signed_bias_max=2047,
    source_bias_exponent_reference=6,
    threshold_mantissa=512,
    threshold_normalization=True,
    reset_mode="hard_reset_to_zero_fpga_v2",
    reset_reason="accepted FPGA-v2 compartment profile does not implement reset-by-subtraction",
    desired_threshold_to_input_ratio=8,
    current_decay=4096,
    voltage_decay=0,
    reset_voltage=0,
    refractory_ticks=0,
    input_encoding="deterministic_evenly_distributed_rate",
    decoder="argmax_total_output_spike_count",
    decoder_tie_break="lowest_class_index",
    synapse_encoding_reference="sparse/shared project representation; not native NxTF packing",
)


FIELD_EVIDENCE = {
    "ann_family": SOURCED_EXACT,
    "ann_framework_keras": SOURCED_EXACT,
    "ann_relu_hidden": SOURCED_STYLE_OR_RANGE,
    "ann_softmax_output": SOURCED_STYLE_OR_RANGE,
    "ann_learned_biases": SOURCED_STYLE_OR_RANGE,
    "ann_dropout_0_1": SOURCED_STYLE_OR_RANGE,
    "ann_optimizer_adam": SOURCED_STYLE_OR_RANGE,
    "ann_loss_categorical_crossentropy": SOURCED_STYLE_OR_RANGE,
    "ann_batch_size_32": SOURCED_STYLE_OR_RANGE,
    "ann_max_epochs_30": PROJECT_RECONSTRUCTION,
    "ann_validation_checkpoint_rule": PROJECT_RECONSTRUCTION,
    "ann_exact_paper_training_config": UNKNOWN_NOT_CLAIMED,
    "conversion_rate_based_snn_toolbox": SOURCED_EXACT,
    "conversion_primary_100_timesteps": SOURCED_EXACT,
    "conversion_weight_bits_8": SOURCED_STYLE_OR_RANGE,
    "conversion_loihi_mixed_weight_range": SOURCED_STYLE_OR_RANGE,
    "conversion_loihi_mixed_weight_step_2": SOURCED_STYLE_OR_RANGE,
    "conversion_static_weight_round_toward_zero": SOURCED_STYLE_OR_RANGE,
    "conversion_bias_bits_12": SOURCED_STYLE_OR_RANGE,
    "conversion_bias_exp_6_reference": SOURCED_STYLE_OR_RANGE,
    "conversion_threshold_mantissa_512": SOURCED_STYLE_OR_RANGE,
    "conversion_threshold_normalization": SOURCED_STYLE_OR_RANGE,
    "conversion_historical_soft_reset": SOURCED_STYLE_OR_RANGE,
    "conversion_fpga_hard_reset": PROJECT_RECONSTRUCTION,
    "conversion_hard_reset_threshold_input_ratio_8": SOURCED_STYLE_OR_RANGE,
    "conversion_deterministic_input_rate_schedule": PROJECT_RECONSTRUCTION,
    "conversion_output_spike_count_decoder": SOURCED_EXACT,
    "conversion_exact_paper_quantizer": UNKNOWN_NOT_CLAIMED,
}


def validate_frozen_policy() -> None:
    """Fail loudly if a later edit silently changes the accepted P08.3 rules."""

    if ANN_POLICY.topology_filters != (14, 20, 12):
        raise AssertionError("P08.3 policy must use the accepted P08.1 topology")
    if ANN_POLICY.output_classes != 10:
        raise AssertionError("MNIST policy must retain ten output classes")
    if ANN_POLICY.validation_size != 5_000:
        raise AssertionError("validation split must remain 5,000 images")
    if ANN_POLICY.batch_size != 32:
        raise AssertionError("frozen P08.3 ANN batch size drifted")
    if ANN_POLICY.dropout_rate != 0.1:
        raise AssertionError("frozen P08.3 dropout policy drifted")
    if CONVERSION_POLICY.primary_timesteps != 100:
        raise AssertionError("NxTF comparison horizon must remain 100 timesteps")
    if CONVERSION_POLICY.weight_bits != 8 or CONVERSION_POLICY.bias_bits != 12:
        raise AssertionError("frozen Loihi-style integer precision drifted")
    if (
        CONVERSION_POLICY.weight_sign_mode != "mixed"
        or CONVERSION_POLICY.weight_quantization_step != 2
        or CONVERSION_POLICY.weight_rounding != "toward_zero"
        or (CONVERSION_POLICY.signed_weight_min, CONVERSION_POLICY.signed_weight_max)
        != (-256, 254)
    ):
        raise AssertionError("Loihi mixed-sign weight mantissa contract drifted")
    if CONVERSION_POLICY.threshold_mantissa != 512:
        raise AssertionError("frozen threshold mantissa drifted")
    if CONVERSION_POLICY.reset_mode != "hard_reset_to_zero_fpga_v2":
        raise AssertionError("P08.3 must preserve the accepted FPGA-v2 reset semantics")
    if OFFICIAL_TEST_POLICY != "LOCKED_UNTIL_P08_3_CHECKPOINT_AND_CONVERSION_FREEZE":
        raise AssertionError("official-test lock must remain explicit during P08.3")
