from __future__ import annotations

from pathlib import Path

import pytest

import neuromorphic_twin as nt
from neuromorphic_twin.fpga_core_capacity import FPGA_CORE_CAPACITY_V1
from neuromorphic_twin.fpga_synapse_reference import accumulate_frozen_weight_image_v1
from neuromorphic_twin.fpga_weight_storage import (
    FrozenWeightStorage,
    pack_synapse_word,
    pack_weight_format,
)
from neuromorphic_twin.weights import WeightFormat, WeightSignMode, encode_static_weight

ROOT = Path(__file__).resolve().parents[1]
DECODER_RTL = ROOT / "rtl" / "core_v1" / "m08_weight_decoder_v1.sv"
WALKER_RTL = ROOT / "rtl" / "core_v1" / "phase_b_synapse_accumulator_v1.sv"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_3_sim.sh"


def _storage() -> FrozenWeightStorage:
    exc = WeightFormat(exponent=0, num_weight_bits=8, sign_mode=WeightSignMode.EXCITATORY)
    inh = WeightFormat(exponent=0, num_weight_bits=8, sign_mode=WeightSignMode.INHIBITORY)
    mixed = WeightFormat(exponent=0, num_weight_bits=8, sign_mode=WeightSignMode.MIXED)
    return FrozenWeightStorage(
        format_words=(
            pack_weight_format(exc),
            pack_weight_format(inh),
            pack_weight_format(mixed),
        ),
        synapse_words=(
            pack_synapse_word(target_neuron=0, requested_mantissa=2, format_index=0),
            pack_synapse_word(target_neuron=1, requested_mantissa=-3, format_index=1),
            pack_synapse_word(target_neuron=0, requested_mantissa=5, format_index=2),
        ),
        axon_row_pointers=(0, 2, 3),
    )


def test_phase_b_reference_is_public() -> None:
    assert nt.accumulate_frozen_weight_image_v1 is accumulate_frozen_weight_image_v1
    assert nt.PhaseBAccumulationResult is not None
    assert nt.SynapseAccumulationStep is not None


def test_phase_b_preserves_external_then_recurrent_order_and_multiplicity() -> None:
    result = accumulate_frozen_weight_image_v1(
        _storage(),
        neuron_count=2,
        external_axons=(0, 1, 0),
        recurrent_axons=(1,),
    )

    # +2 excitatory -> +128. Mixed +5 quantizes to +4 -> +256.
    assert result.accumulators == (768, -384)
    assert result.external_event_count == 3
    assert result.recurrent_event_count == 1
    assert result.traversed_synapse_count == 6
    assert tuple(step.source for step in result.steps) == (
        "external",
        "external",
        "external",
        "external",
        "external",
        "recurrent",
    )
    assert tuple(step.axon_id for step in result.steps) == (0, 0, 1, 0, 0, 1)
    assert tuple(step.target_neuron for step in result.steps) == (0, 1, 0, 0, 1, 0)
    assert tuple(step.effective_weight for step in result.steps) == (
        128,
        -192,
        256,
        128,
        -192,
        256,
    )
    assert result.steps[-1].accumulator_after == 768


def test_phase_b_effective_weights_are_reconstructed_from_m08_words() -> None:
    storage = _storage()
    result = accumulate_frozen_weight_image_v1(
        storage,
        neuron_count=2,
        external_axons=(0, 1),
    )
    decoded = storage.decode_synapses()

    expected = tuple(
        encode_static_weight(
            synapse.encoding.requested_mantissa,
            synapse.encoding.weight_format,
        ).effective_weight
        for synapse in decoded
        if synapse.encoding is not None
    )
    assert tuple(step.effective_weight for step in result.steps) == expected


def test_physically_valid_unconfigured_axon_is_no_op() -> None:
    result = accumulate_frozen_weight_image_v1(
        _storage(),
        neuron_count=2,
        external_axons=(7,),
    )
    assert result.accumulators == (0, 0)
    assert result.steps == ()


def test_phase_b_rejects_target_outside_configured_neurons() -> None:
    fmt = WeightFormat()
    storage = FrozenWeightStorage(
        format_words=(pack_weight_format(fmt),),
        synapse_words=(
            pack_synapse_word(target_neuron=2, requested_mantissa=1, format_index=0),
        ),
        axon_row_pointers=(0, 1),
    )
    with pytest.raises(ValueError, match="outside configured neuron_count"):
        accumulate_frozen_weight_image_v1(
            storage,
            neuron_count=2,
            external_axons=(0,),
        )


def test_phase_b_rejects_event_outside_physical_axon_capacity() -> None:
    with pytest.raises(ValueError, match="outside M11.5 physical capacity"):
        accumulate_frozen_weight_image_v1(
            _storage(),
            neuron_count=2,
            external_axons=(FPGA_CORE_CAPACITY_V1.max_axons,),
        )


def test_phase_b_rejects_per_tick_event_capacity_overflow() -> None:
    too_many = (0,) * (FPGA_CORE_CAPACITY_V1.max_external_events_per_tick + 1)
    with pytest.raises(ValueError, match="per-tick capacity"):
        accumulate_frozen_weight_image_v1(
            _storage(),
            neuron_count=2,
            external_axons=too_many,
        )


def test_phase_b_rejects_invalid_neuron_count_and_event_types() -> None:
    with pytest.raises(ValueError, match="neuron_count must be"):
        accumulate_frozen_weight_image_v1(_storage(), neuron_count=0)
    with pytest.raises(TypeError, match="entries must be ints"):
        accumulate_frozen_weight_image_v1(
            _storage(), neuron_count=2, external_axons=(True,)
        )


def test_m11_5_3_decoder_rtl_freezes_m08_arithmetic_contract() -> None:
    text = DECODER_RTL.read_text(encoding="utf-8")
    assert "module m08_weight_decoder_v1" in text
    assert "format_word[15:10]" in text
    assert "synapse_word[31:29]" in text
    assert "precision_shift_i = 8 - num_weight_bits_i" in text
    assert "quantized_i = (magnitude_i >> precision_shift_i) << precision_shift_i" in text
    assert "aligned_units_i = quantized_i >>> (-exponent_i)" in text
    assert "WEIGHT_LIMIT = 2097088" in text


def test_m11_5_3_walker_rtl_freezes_phase_b_order_and_faults() -> None:
    text = WALKER_RTL.read_text(encoding="utf-8")
    assert "module phase_b_synapse_accumulator_v1" in text
    assert "external_event_mem" in text
    assert "recurrent_event_mem" in text
    assert "axon_row_mem" in text
    assert "synapse_mem" in text
    assert "accumulator_mem" in text
    assert "active_source      <= 1'b0" in text
    assert "active_source      <= 1'b1" in text
    assert "FAULT_EVENT_AXON" in text
    assert "FAULT_ROW_POINTER" in text
    assert "FAULT_FORMAT_INDEX" in text
    assert "FAULT_TARGET_NEURON" in text
    assert "FAULT_ACCUM_OVERFLOW" in text


def test_m11_5_3_vendor_runner_is_source_controlled() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="2025.2"' in text
    assert 'STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_3"' in text
    assert "m08_weight_decoder_v1.sv" in text
    assert "phase_b_synapse_accumulator_v1.sv" in text
    assert "tb_phase_b_synapse_accumulator_v1.sv" in text
    assert 'xsim "$SNAPSHOT" -runall' in text
