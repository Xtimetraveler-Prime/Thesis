"""P08 NxTF-oriented MNIST application."""

from .config import (
    CHARACTERIZATION_TIMESTEPS,
    PRIMARY_TIMESTEPS,
    TOTAL_SPIKING_NEURONS,
    TOTAL_TRAINABLE_WEIGHTS,
)
from .topology import IntegerModel, build_network, make_mapping_probe_model, topology_report

__all__ = [
    "CHARACTERIZATION_TIMESTEPS",
    "PRIMARY_TIMESTEPS",
    "TOTAL_SPIKING_NEURONS",
    "TOTAL_TRAINABLE_WEIGHTS",
    "IntegerModel",
    "build_network",
    "make_mapping_probe_model",
    "topology_report",
]
