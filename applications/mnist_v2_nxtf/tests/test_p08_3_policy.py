from __future__ import annotations

from mnist_v2_nxtf.policy import (
    ANN_POLICY,
    CONVERSION_POLICY,
    FIELD_EVIDENCE,
    OFFICIAL_TEST_POLICY,
    POLICY_STATUS,
    PROJECT_RECONSTRUCTION,
    SOURCED_EXACT,
    SOURCED_STYLE_OR_RANGE,
    UNKNOWN_NOT_CLAIMED,
    validate_frozen_policy,
)


def test_p08_3_policy_validation_passes():
    validate_frozen_policy()
    assert POLICY_STATUS == "P08_3_1_TRAINING_CONVERSION_POLICY_FROZEN"
    assert OFFICIAL_TEST_POLICY == "LOCKED_UNTIL_P08_3_CHECKPOINT_AND_CONVERSION_FREEZE"


def test_p08_3_ann_policy_is_source_compatible_and_validation_only_for_selection():
    assert ANN_POLICY.topology_filters == (14, 20, 12)
    assert ANN_POLICY.output_classes == 10
    assert ANN_POLICY.hidden_activation == "relu"
    assert ANN_POLICY.output_activation == "softmax"
    assert ANN_POLICY.use_bias is True
    assert ANN_POLICY.dropout_rate == 0.1
    assert ANN_POLICY.dropout_after_hidden_layers == (1, 2, 3)
    assert ANN_POLICY.input_scale_divisor == 255.0
    assert ANN_POLICY.optimizer == "adam"
    assert ANN_POLICY.learning_rate == 1e-3
    assert ANN_POLICY.loss == "categorical_crossentropy"
    assert ANN_POLICY.batch_size == 32
    assert ANN_POLICY.max_epochs == 30
    assert ANN_POLICY.early_stopping_patience == 5
    assert ANN_POLICY.checkpoint_metric == "val_accuracy"
    assert ANN_POLICY.checkpoint_tiebreakers == ("min_val_loss", "earliest_epoch")
    assert ANN_POLICY.validation_size == 5_000
    assert ANN_POLICY.deterministic_ops is True


def test_p08_3_conversion_policy_keeps_nxtf_anchors_and_labels_fpga_adaptations():
    assert CONVERSION_POLICY.primary_timesteps == 100
    assert CONVERSION_POLICY.characterization_timesteps == (16, 32, 64, 100)
    assert CONVERSION_POLICY.weight_bits == 8
    assert (CONVERSION_POLICY.signed_weight_min, CONVERSION_POLICY.signed_weight_max) == (-127, 127)
    assert CONVERSION_POLICY.bias_bits == 12
    assert (CONVERSION_POLICY.signed_bias_min, CONVERSION_POLICY.signed_bias_max) == (-2047, 2047)
    assert CONVERSION_POLICY.source_bias_exponent_reference == 6
    assert CONVERSION_POLICY.threshold_mantissa == 512
    assert CONVERSION_POLICY.threshold_normalization is True
    assert CONVERSION_POLICY.reset_mode == "hard_reset_to_zero_fpga_v2"
    assert CONVERSION_POLICY.desired_threshold_to_input_ratio == 8
    assert CONVERSION_POLICY.current_decay == 4096
    assert CONVERSION_POLICY.voltage_decay == 0
    assert CONVERSION_POLICY.reset_voltage == 0
    assert CONVERSION_POLICY.refractory_ticks == 0
    assert CONVERSION_POLICY.input_encoding == "deterministic_evenly_distributed_rate"
    assert CONVERSION_POLICY.decoder == "argmax_total_output_spike_count"
    assert CONVERSION_POLICY.decoder_tie_break == "lowest_class_index"


def test_p08_3_evidence_labels_keep_unknowns_and_project_choices_explicit():
    assert FIELD_EVIDENCE["ann_family"] == SOURCED_EXACT
    assert FIELD_EVIDENCE["ann_dropout_0_1"] == SOURCED_STYLE_OR_RANGE
    assert FIELD_EVIDENCE["ann_max_epochs_30"] == PROJECT_RECONSTRUCTION
    assert FIELD_EVIDENCE["ann_exact_paper_training_config"] == UNKNOWN_NOT_CLAIMED
    assert FIELD_EVIDENCE["conversion_rate_based_snn_toolbox"] == SOURCED_EXACT
    assert FIELD_EVIDENCE["conversion_historical_soft_reset"] == SOURCED_STYLE_OR_RANGE
    assert FIELD_EVIDENCE["conversion_fpga_hard_reset"] == PROJECT_RECONSTRUCTION
    assert FIELD_EVIDENCE["conversion_exact_paper_quantizer"] == UNKNOWN_NOT_CLAIMED
