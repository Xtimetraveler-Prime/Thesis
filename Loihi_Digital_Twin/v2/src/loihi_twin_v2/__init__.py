"""Loihi-1 architectural digital-twin v2 golden model."""

from .arithmetic import ArithmeticConfig, OverflowMode, round_away_from_zero
from .axon import InputAxonBinding, OutputRoute, OutputRouteEntry
from .chip import LogicalChip
from .compartment import CompartmentConfig, CompartmentState, step_compartment
from .core import LogicalCore, LogicalCoreConfig
from .mapping import Deployment
from .packet import PacketClass, SpikePacket
from .resources import (
    MAX_COMPARTMENTS_PER_CORE,
    MAX_INPUT_AXONS_PER_CORE,
    MAX_LOGICAL_CORES,
    MAX_OUTPUT_ROUTES_PER_CORE,
    MAX_SYNAPSE_MEMORY_BYTES_PER_CORE,
    ResourceCapacityError,
    ResourceUsage,
    SynapseCostModel,
)
from .synapse import SynapseEntry, SynapseTemplate

__all__ = [
    "ArithmeticConfig",
    "OverflowMode",
    "round_away_from_zero",
    "InputAxonBinding",
    "OutputRoute",
    "OutputRouteEntry",
    "LogicalChip",
    "CompartmentConfig",
    "CompartmentState",
    "step_compartment",
    "LogicalCore",
    "LogicalCoreConfig",
    "Deployment",
    "PacketClass",
    "SpikePacket",
    "ResourceCapacityError",
    "ResourceUsage",
    "SynapseCostModel",
    "SynapseEntry",
    "SynapseTemplate",
    "MAX_LOGICAL_CORES",
    "MAX_COMPARTMENTS_PER_CORE",
    "MAX_INPUT_AXONS_PER_CORE",
    "MAX_OUTPUT_ROUTES_PER_CORE",
    "MAX_SYNAPSE_MEMORY_BYTES_PER_CORE",
]
