"""Loihi-1 architectural digital-twin v2 golden model."""

from .arithmetic import ArithmeticConfig, OverflowMode, round_away_from_zero
from .axon import InputAxonBinding, OutputRoute, OutputRouteEntry
from .chip import LogicalChip
from .compartment import CompartmentConfig, CompartmentState, step_compartment
from .core import LogicalCore, LogicalCoreConfig
from .hardware_p03 import (
    OneCoreHardwareImage,
    P03_PROFILE_NAME,
    P03_REQUIRED_ARITHMETIC,
    SparseWord,
    export_one_core_image,
    pack_compartment_config,
    pack_compartment_state,
    pack_output_packet,
    unpack_compartment_config,
    unpack_compartment_state,
    unpack_output_packet,
)
from .hardware_p04 import (
    P04_PHYSICAL_COMPARTMENTS,
    P04_PHYSICAL_INPUT_AXONS,
    P04_PHYSICAL_INPUT_EVENTS,
    P04_PHYSICAL_OUTPUT_PACKETS,
    P04_PHYSICAL_OUTPUT_ROUTES,
    P04_PHYSICAL_SYNAPSE_ENTRIES,
    P04_PROFILE_NAME,
    TwoCoreValidationImage,
    export_two_core_validation_image,
)
from .mapping import Deployment
from .packet import PacketClass, RouteScope, SpikePacket
from .reporting import deployment_report, trace_report
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
from .runtime import RunResult, run_deployment
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
    "RouteScope",
    "SpikePacket",
    "deployment_report",
    "trace_report",
    "RunResult",
    "run_deployment",
    "ResourceCapacityError",
    "ResourceUsage",
    "SynapseCostModel",
    "SynapseEntry",
    "SynapseTemplate",
    "OneCoreHardwareImage",
    "SparseWord",
    "P03_PROFILE_NAME",
    "P03_REQUIRED_ARITHMETIC",
    "export_one_core_image",
    "pack_compartment_config",
    "unpack_compartment_config",
    "pack_compartment_state",
    "unpack_compartment_state",
    "pack_output_packet",
    "unpack_output_packet",
    "P04_PROFILE_NAME",
    "TwoCoreValidationImage",
    "export_two_core_validation_image",
    "P04_PHYSICAL_COMPARTMENTS",
    "P04_PHYSICAL_INPUT_AXONS",
    "P04_PHYSICAL_SYNAPSE_ENTRIES",
    "P04_PHYSICAL_OUTPUT_ROUTES",
    "P04_PHYSICAL_INPUT_EVENTS",
    "P04_PHYSICAL_OUTPUT_PACKETS",
    "MAX_LOGICAL_CORES",
    "MAX_COMPARTMENTS_PER_CORE",
    "MAX_INPUT_AXONS_PER_CORE",
    "MAX_OUTPUT_ROUTES_PER_CORE",
    "MAX_SYNAPSE_MEMORY_BYTES_PER_CORE",
]
