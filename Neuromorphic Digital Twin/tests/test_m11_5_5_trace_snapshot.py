from __future__ import annotations

import pytest

from neuromorphic_twin.fpga_core_capacity import pack_neuron_state_word
from neuromorphic_twin.fpga_trace_snapshot import (
    FPGA_TRACE_SNAPSHOT_SCHEMA,
    FpgaTickTraceSnapshot,
)
from neuromorphic_twin.model import NeuronState, Spike


def _snapshot() -> FpgaTickTraceSnapshot:
    before = (
        pack_neuron_state_word(NeuronState(current=10, voltage=-3, refractory_remaining=0)),
        pack_neuron_state_word(NeuronState(current=-7, voltage=5, refractory_remaining=2)),
    )
    after = (
        pack_neuron_state_word(NeuronState(current=14, voltage=0, refractory_remaining=1)),
        pack_neuron_state_word(NeuronState(current=-9, voltage=-4, refractory_remaining=1)),
    )
    return FpgaTickTraceSnapshot(
        committed_tick=7,
        external_input_axons=(4, 4, 1),
        recurrent_input_axons=(3, 2),
        synaptic_input=(11, -13),
        state_before_words=before,
        state_after_words=after,
        spikes=(True, False),
        routed_output_axons=(8, 7, 8),
    )


def test_trace_snapshot_schema_and_tick_translation_are_frozen() -> None:
    snapshot = _snapshot()
    assert FPGA_TRACE_SNAPSHOT_SCHEMA == "neuromorphic-twin-fpga-trace-snapshot-v1"
    assert snapshot.committed_tick == 7
    assert snapshot.trace_tick == 6
    assert snapshot.neuron_count == 2

    # Unsigned-32 hardware wrap still maps to the immediately preceding
    # software trace tick without inventing an out-of-band value.
    wrapped = FpgaTickTraceSnapshot(
        committed_tick=0,
        external_input_axons=(),
        recurrent_input_axons=(),
        synaptic_input=(0,),
        state_before_words=(pack_neuron_state_word(NeuronState()),),
        state_after_words=(pack_neuron_state_word(NeuronState()),),
        spikes=(False,),
        routed_output_axons=(),
    )
    assert wrapped.trace_tick == (1 << 32) - 1


def test_snapshot_losslessly_reconstructs_m10_tick_trace_fields() -> None:
    snapshot = _snapshot()
    trace = snapshot.to_tick_trace()

    assert trace.tick == 6
    assert trace.external_input_axons == (4, 4, 1)
    assert trace.recurrent_input_axons == (3, 2)
    assert trace.input_axons == (4, 4, 1, 3, 2)
    assert trace.synaptic_input == (11, -13)
    assert trace.current_before == (10, -7)
    assert trace.voltage_before == (-3, 5)
    assert trace.current_after == (14, -9)
    assert trace.voltage_after == (0, -4)
    assert trace.refractory_after == (1, 1)
    assert trace.spikes == (Spike(tick=6, neuron_id=0),)
    assert trace.routed_output_axons == (8, 7, 8)


def test_snapshot_preserves_event_order_and_multiplicity() -> None:
    snapshot = _snapshot()
    assert snapshot.input_axons == (4, 4, 1, 3, 2)
    assert snapshot.external_input_axons.count(4) == 2
    assert snapshot.routed_output_axons.count(8) == 2


def test_snapshot_requires_one_consistent_per_neuron_image() -> None:
    state = pack_neuron_state_word(NeuronState())
    with pytest.raises(ValueError, match="state_before_words length"):
        FpgaTickTraceSnapshot(1, (), (), (0,), (), (state,), (False,), ())
    with pytest.raises(ValueError, match="synaptic_input length"):
        FpgaTickTraceSnapshot(1, (), (), (), (state,), (state,), (False,), ())
    with pytest.raises(ValueError, match="spikes length"):
        FpgaTickTraceSnapshot(1, (), (), (0,), (state,), (state,), (), ())


def test_snapshot_rejects_values_outside_physical_or_word_capacity() -> None:
    state = pack_neuron_state_word(NeuronState())
    with pytest.raises(ValueError, match="signed-64"):
        FpgaTickTraceSnapshot(
            1, (), (), (1 << 63,), (state,), (state,), (False,), ()
        )
    with pytest.raises(ValueError, match="physical capacity"):
        FpgaTickTraceSnapshot(
            1, (1024,), (), (0,), (state,), (state,), (False,), ()
        )
    with pytest.raises(ValueError, match="fit 64 bits"):
        FpgaTickTraceSnapshot(
            1, (), (), (0,), (1 << 64,), (state,), (False,), ()
        )


def test_snapshot_rejects_boolean_values_where_integer_words_are_required() -> None:
    state = pack_neuron_state_word(NeuronState())
    with pytest.raises(TypeError, match="committed_tick"):
        FpgaTickTraceSnapshot(True, (), (), (0,), (state,), (state,), (False,), ())
    with pytest.raises(TypeError, match="synaptic_input"):
        FpgaTickTraceSnapshot(1, (), (), (True,), (state,), (state,), (False,), ())
    with pytest.raises(TypeError, match="spikes entries"):
        FpgaTickTraceSnapshot(1, (), (), (0,), (state,), (state,), (1,), ())
