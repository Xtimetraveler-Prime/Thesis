"""Phase-1 neuromorphic digital-twin reference model."""

from .arithmetic import ArithmeticConfig, OverflowMode, round_away_from_zero
from .core import NeuromorphicCore
from .model import NeuronConfig, NeuronState, Spike, Synapse, TickTrace
from .neuron import step_neuron
from .weights import (
    StaticWeightEncoding,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)

__all__ = [
    "ArithmeticConfig",
    "OverflowMode",
    "NeuronConfig",
    "NeuronState",
    "NeuromorphicCore",
    "Spike",
    "StaticWeightEncoding",
    "Synapse",
    "TickTrace",
    "WeightFormat",
    "WeightSignMode",
    "encode_static_weight",
    "round_away_from_zero",
    "step_neuron",
]
