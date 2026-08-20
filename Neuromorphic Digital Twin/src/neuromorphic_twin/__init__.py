"""Phase-1 neuromorphic digital-twin reference model."""

from .arithmetic import ArithmeticConfig, OverflowMode, round_away_from_zero
from .core import NeuromorphicCore
from .fpga_weight_storage import (
    AXON_ROW_POINTER_BITS,
    FORMAT_WORD_BITS,
    FPGA_WEIGHT_STORAGE_SCHEMA,
    MAX_WEIGHT_FORMATS,
    SYNAPSE_WORD_BITS,
    FrozenWeightStorage,
    PackedSynapseFields,
    WeightStorageArtifacts,
    WeightStorageEstimate,
    estimate_weight_storage,
    freeze_encoded_synapses,
    pack_synapse_word,
    pack_weight_format,
    read_weight_storage_json,
    unpack_synapse_word,
    unpack_weight_format,
    write_weight_storage_image,
)
from .model import NeuronConfig, NeuronState, Spike, SpikeRoute, Synapse, TickTrace
from .neuron import step_neuron
from .weights import (
    StaticWeightEncoding,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)

__all__ = [
    "AXON_ROW_POINTER_BITS",
    "ArithmeticConfig",
    "FORMAT_WORD_BITS",
    "FPGA_WEIGHT_STORAGE_SCHEMA",
    "FrozenWeightStorage",
    "MAX_WEIGHT_FORMATS",
    "NeuronConfig",
    "NeuronState",
    "NeuromorphicCore",
    "OverflowMode",
    "PackedSynapseFields",
    "SYNAPSE_WORD_BITS",
    "Spike",
    "SpikeRoute",
    "StaticWeightEncoding",
    "Synapse",
    "TickTrace",
    "WeightFormat",
    "WeightSignMode",
    "WeightStorageArtifacts",
    "WeightStorageEstimate",
    "encode_static_weight",
    "estimate_weight_storage",
    "freeze_encoded_synapses",
    "pack_synapse_word",
    "pack_weight_format",
    "read_weight_storage_json",
    "round_away_from_zero",
    "step_neuron",
    "unpack_synapse_word",
    "unpack_weight_format",
    "write_weight_storage_image",
]
