"""A2.3 synthetic uncompiled SNN reference tests; no MNIST test images."""

import pytest

from loihi_twin_v2.p06_integer_oracle import LIFParameters, LIFState
from loihi_twin_v2.p06_compact_inference import (
    CompactNetwork, infer_event_schedule, infer_image,
)


def model(*, input_w=2, route_w=2, hidden_threshold=1, output_threshold=1,
          hidden_bias=0, output_bias=0, hidden_decay=4096, output_decay=4096, hidden_current_decay=4096):
    hp = LIFParameters(hidden_current_decay, hidden_decay, hidden_threshold, bias=hidden_bias)
    op = LIFParameters(4096, output_decay, output_threshold, bias=output_bias)
    return CompactNetwork.from_uniform_parameters(
        [[input_w] * 784 for _ in range(32)],
        [[route_w] * 32 for _ in range(10)], hp, op,
    )


def test_one_step_delay_no_same_step_output_reaction():
    net = model(hidden_threshold=1, output_threshold=1)
    events = [()] * 26
    events[0] = (0,)
    result = infer_event_schedule(net, events)
    first, second, third = result.traces[:3]
    assert first.hidden_spikes == tuple(range(32))
    assert first.output_spikes == ()
    assert first.received_hidden_spikes == ()
    assert first.output_synaptic_inputs == (0,) * 10
    assert second.received_hidden_spikes == tuple(range(32))
    assert second.output_synaptic_inputs == (64,) * 10
    assert second.output_spikes == tuple(range(10))
    assert third.received_hidden_spikes == ()
    assert result.output_counts == (1,) * 10
    assert result.predicted_class == 0


def test_signed_inhibition_and_no_phantom_routes():
    # A negative edge suppresses output firing, despite hidden firings.
    inhibitory = infer_event_schedule(model(route_w=-1), [(0,)] + [()] * 25)
    assert inhibitory.traces[0].hidden_spikes == tuple(range(32))
    assert inhibitory.traces[1].output_synaptic_inputs == (-32,) * 10
    assert inhibitory.output_counts == (0,) * 10
    silent = infer_image(model(hidden_threshold=10000), [0] * 784)
    assert all(not step.hidden_spikes and not step.received_hidden_spikes for step in silent.traces)
    assert all(not step.output_spikes for step in silent.traces)


def test_last_input_step_routes_to_final_drain_and_boundary_isolated():
    net = model(hidden_threshold=1, output_threshold=1)
    events = [()] * 24 + [(0,), ()]
    result = infer_event_schedule(net, events)
    assert result.traces[24].hidden_spikes == tuple(range(32))
    assert result.traces[24].output_spikes == ()
    assert result.traces[25].received_hidden_spikes == tuple(range(32))
    assert result.traces[25].output_spikes == tuple(range(10))
    assert result.output_counts == (1,) * 10
    assert result.dropped_boundary_hidden_spikes == ()
    # Current retention + delayed threshold can create final-tick spikes;
    # these must be discarded rather than delivered to a following image.
    delayed = model(input_w=1, hidden_threshold=1, hidden_decay=0, hidden_current_decay=0)
    last = infer_event_schedule(delayed, events)
    assert last.traces[24].hidden_spikes == ()
    assert last.traces[25].hidden_spikes == tuple(range(32))
    assert last.dropped_boundary_hidden_spikes == tuple(range(32))
    assert last.output_counts == (0,) * 10


def test_each_image_starts_with_cleared_state_counters_and_events():
    net = model(hidden_threshold=1, output_threshold=1)
    white = bytes([255] * 784)
    first = infer_image(net, white)
    _ = infer_image(net, [0] * 784)
    second = infer_image(net, white)
    assert first == second
    assert all(state == LIFState() for state in second.traces[0].hidden_before)
    assert all(state == LIFState() for state in second.traces[0].output_before)
    assert second.traces[0].received_hidden_spikes == ()
    assert second.traces[0].output_spike_counts == (0,) * 10
    assert len(second.traces) == 26


def test_no_undocumented_bias_spike_suppression():
    result = infer_image(model(hidden_threshold=1, output_threshold=1, hidden_bias=2, output_bias=2), [0] * 784)
    assert result.traces[0].hidden_spikes == tuple(range(32))
    assert result.traces[0].output_spikes == tuple(range(10))
    assert result.traces[0].received_hidden_spikes == ()
    assert result.output_counts == (26,) * 10


@pytest.mark.parametrize("schedule", [
    [()] * 25, [()] * 27,
    [(0, 0)] + [()] * 25,
    [(1, 0)] + [()] * 25,
    [(-1,)] + [()] * 25,
    [(784,)] + [()] * 25,
    [()] * 25 + [(0,)],
])
def test_invalid_schedule_rejected(schedule):
    with pytest.raises(ValueError):
        infer_event_schedule(model(), schedule)


def test_wrong_network_shape_or_range_rejected():
    with pytest.raises(ValueError):
        CompactNetwork.from_uniform_parameters(
            [[1] * 784] * 31, [[1] * 32] * 10,
            LIFParameters(4096, 0, 1), LIFParameters(4096, 0, 1),
        )
    with pytest.raises(ValueError):
        CompactNetwork.from_uniform_parameters(
            [[1 << 23] * 784] * 32, [[1] * 32] * 10,
            LIFParameters(4096, 0, 1), LIFParameters(4096, 0, 1),
        )
