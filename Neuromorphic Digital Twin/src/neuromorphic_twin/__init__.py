"""Phase-1 neuromorphic digital-twin reference model."""

from .arithmetic import ArithmeticConfig, OverflowMode, round_away_from_zero
from .core import NeuromorphicCore
from .model import NeuronConfig, NeuronState, Spike, Synapse, TickTrace
from .neuron import step_neuron

__all__ = [
    "ArithmeticConfig",
    "OverflowMode",
    "NeuronConfig",
    "NeuronState",
    "NeuromorphicCore",
    "Spike",
    "Synapse",
    "TickTrace",
    "round_away_from_zero",
    "step_neuron",
]
