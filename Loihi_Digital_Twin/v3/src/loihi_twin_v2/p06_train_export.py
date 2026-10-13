"""P06-A2.5 bridge: independent integer CompactNetwork -> accepted P06 compiler.

This adapter does not modify the compiler, hardware image, or accepted P05
runtime. High-level PopulationSpec currently supports only a single shared
compartment configuration per population; nonuniform neuron parameters fail
closed rather than silently lose configuration values.
"""
from __future__ import annotations

from .compartment import CompartmentConfig
from .compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec,
    PopulationSpec, ProjectionConnection, ProjectionSpec,
)
from .p06_compact_inference import CompactNetwork
from .p06_integer_oracle import LIFParameters


def _convert_params(params: LIFParameters) -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=params.current_decay,
        voltage_decay=params.voltage_decay,
        threshold=params.threshold,
        bias=params.bias,
        reset_voltage=params.reset_voltage,
        refractory_ticks=params.refractory_ticks,
    )


def compact_to_compiler_spec(model: CompactNetwork) -> NetworkSpec:
    """Preserve every learned edge, including zeros, for first parity gate.

    Connectivity remains dense and destination-major. Future explicit sparsity
    selection, weight pruning or graph compression needs a distinct acceptance.
    """
    if not isinstance(model, CompactNetwork):
        raise TypeError("expected a P06 CompactNetwork")
    if len(set(model.hidden_params)) != 1 or len(set(model.output_params)) != 1:
        raise ValueError("compiler requires a uniform LIF config per population; per-neuron parameters cannot be lost")
    hidden, output = model.hidden_params[0], model.output_params[0]
    return NetworkSpec(
        populations=(
            PopulationSpec("hidden", 32, _convert_params(hidden)),
            PopulationSpec("readout", 10, _convert_params(output)),
        ),
        input_populations=(InputPopulationSpec("pixels", 784),),
        input_projections=(InputProjectionSpec(
            "pixels_to_hidden", "pixels", "hidden",
            tuple(
                ProjectionConnection(source, dest, model.input_to_hidden[dest][source])
                for source in range(784) for dest in range(32)
            ),
        ),),
        projections=(ProjectionSpec(
            "hidden_to_readout", "hidden", "readout",
            tuple(
                ProjectionConnection(source, dest, model.hidden_to_output[dest][source])
                for source in range(32) for dest in range(10)
            ),
        ),),
    )
