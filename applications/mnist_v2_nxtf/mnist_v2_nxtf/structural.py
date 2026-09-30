"""P06 structural mapping probe for the proposed P08.1 NxTF reconstruction.

The graph built here is connectivity-only.  Integer ``weight`` values are stable
kernel-coefficient identity tokens so the P06 sharing model can distinguish
learned convolution coefficients while recognizing repeated spatial use.  They
are not trained inference weights and this graph must not be used for accuracy
or official-test evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from loihi_twin_v2 import (
    CompartmentConfig,
    InputPopulationSpec,
    InputProjectionSpec,
    MappingOptions,
    NetworkSpec,
    PopulationSpec,
    ProjectionConnection,
    ProjectionSpec,
    compile_network,
)

from .reconstruction import OUTPUT_CLASSES, PROPOSED_FILTERS, PROPOSED_METRICS


P06_STRUCTURAL_COMPARTMENTS_PER_CORE = 900


@dataclass(frozen=True, slots=True)
class _ConvStage:
    name: str
    input_height: int
    input_width: int
    input_channels: int
    output_height: int
    output_width: int
    output_channels: int
    kernel: int
    stride: int


def _stages() -> tuple[_ConvStage, ...]:
    f1, f2, f3 = PROPOSED_FILTERS
    return (
        _ConvStage("conv1", 28, 28, 1, 12, 12, f1, 5, 2),
        _ConvStage("conv2", 12, 12, f1, 10, 10, f2, 3, 1),
        _ConvStage("conv3", 10, 10, f2, 4, 4, f3, 3, 2),
        _ConvStage("conv4", 4, 4, f3, 1, 1, OUTPUT_CLASSES, 4, 1),
    )


def _channel_population(layer: str, channel: int) -> str:
    return f"{layer}_c{channel:02d}"


def _spatial_index(y: int, x: int, width: int) -> int:
    return y * width + x


@lru_cache(maxsize=1)
def build_structural_network() -> NetworkSpec:
    """Build the proposed four-convolution graph for P06 resource accounting.

    Each convolution output channel is a separate P06 population.  Keras-style
    Conv2D biases are one learned value per output channel, so this population
    granularity leaves a clean path to assign channel-specific compartment bias
    values later without pretending that the current zero-bias structural probe
    already contains trained parameters.
    """

    # A neutral, non-inference compartment profile.  P08.3 will freeze actual
    # converted-SNN threshold/decay/reset/bias behavior after P08.2 can host the
    # graph.  The current probe exists only to exercise P06 placement/resources.
    structural_neuron = CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=1_000_000,
        bias=0,
    )

    populations: list[PopulationSpec] = []
    projections: list[ProjectionSpec] = []
    input_projections: list[InputProjectionSpec] = []

    weight_base = 0
    for stage_index, stage in enumerate(_stages(), start=1):
        spatial_size = stage.output_height * stage.output_width
        for output_channel in range(stage.output_channels):
            populations.append(
                PopulationSpec(
                    name=_channel_population(stage.name, output_channel),
                    size=spatial_size,
                    compartment=structural_neuron,
                )
            )

        for output_channel in range(stage.output_channels):
            destination_population = _channel_population(stage.name, output_channel)
            for input_channel in range(stage.input_channels):
                if stage_index == 1:
                    source_name = "pixels"
                else:
                    source_name = _channel_population(
                        f"conv{stage_index - 1}", input_channel
                    )

                connections: list[ProjectionConnection] = []
                for output_y in range(stage.output_height):
                    for output_x in range(stage.output_width):
                        destination_index = _spatial_index(
                            output_y, output_x, stage.output_width
                        )
                        for kernel_y in range(stage.kernel):
                            input_y = output_y * stage.stride + kernel_y
                            for kernel_x in range(stage.kernel):
                                input_x = output_x * stage.stride + kernel_x
                                source_index = _spatial_index(
                                    input_y, input_x, stage.input_width
                                )
                                kernel_index = (
                                    (
                                        output_channel * stage.input_channels
                                        + input_channel
                                    )
                                    * stage.kernel
                                    * stage.kernel
                                    + kernel_y * stage.kernel
                                    + kernel_x
                                )
                                # Stable coefficient-identity token.  Repeated
                                # spatial uses of one convolution coefficient get
                                # the same token; distinct coefficients do not.
                                structural_weight = weight_base + kernel_index + 1
                                connections.append(
                                    ProjectionConnection(
                                        source_index=source_index,
                                        destination_index=destination_index,
                                        weight=structural_weight,
                                    )
                                )

                projection_name = f"{source_name}_to_{destination_population}"
                if stage_index == 1:
                    input_projections.append(
                        InputProjectionSpec(
                            name=projection_name,
                            source_input="pixels",
                            destination_population=destination_population,
                            connections=tuple(connections),
                        )
                    )
                else:
                    projections.append(
                        ProjectionSpec(
                            name=projection_name,
                            source_population=source_name,
                            destination_population=destination_population,
                            connections=tuple(connections),
                        )
                    )

        weight_base += (
            stage.output_channels
            * stage.input_channels
            * stage.kernel
            * stage.kernel
        )

    if weight_base != PROPOSED_METRICS.kernel_weights:
        raise AssertionError(
            "structural coefficient identity count does not match reconstruction audit"
        )

    return NetworkSpec(
        populations=tuple(populations),
        projections=tuple(projections),
        input_populations=(InputPopulationSpec(name="pixels", size=28 * 28),),
        input_projections=tuple(input_projections),
    )


def compile_structural_probe():
    """Compile the unchanged graph under the deterministic P08.1 P06 probe policy.

    The stock 1,024-compartment first-fit policy overfills synapse memory on this
    graph.  A 900-compartment placement preserves the network and still reaches
    the five-core lower bound implied by 4,218 neurons / 1,024 compartments.
    This is a mapping policy, not a network-design constraint.
    """

    return compile_network(
        build_structural_network(),
        MappingOptions(compartments_per_core=P06_STRUCTURAL_COMPARTMENTS_PER_CORE),
    )
