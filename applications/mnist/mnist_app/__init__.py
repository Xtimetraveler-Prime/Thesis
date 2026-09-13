"""MNIST application layer for the neuromorphic digital twin."""

from .config import (
    DENSE_SYNAPSES,
    INPUT_AXONS,
    INPUT_HEIGHT,
    INPUT_WIDTH,
    OUTPUT_NEURONS,
    PRESENTATION_TICKS,
)
from .encoding import (
    center_crop_20x20,
    count_events,
    encode_binary_spikes,
    encode_event_schedule,
    quantize_spike_levels,
)

__all__ = [
    "DENSE_SYNAPSES",
    "INPUT_AXONS",
    "INPUT_HEIGHT",
    "INPUT_WIDTH",
    "OUTPUT_NEURONS",
    "PRESENTATION_TICKS",
    "center_crop_20x20",
    "count_events",
    "encode_binary_spikes",
    "encode_event_schedule",
    "quantize_spike_levels",
]
