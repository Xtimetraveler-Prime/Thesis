"""P08 topology helpers and deterministic conversion to the P06 network graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from loihi_twin_v2 import (
    CompartmentConfig,
    InputPopulationSpec,
    InputProjectionSpec,
    NetworkSpec,
    PopulationSpec,
    ProjectionConnection,
    ProjectionSpec,
)

from .config import (
    CONV1,
    CONV1_NEURONS,
    CONV2,
    CONV2_NEURONS,
    DENSE_HIDDEN,
    DENSE_OUTPUT,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    TOTAL_SPIKING_NEURONS,
    TOTAL_TRAINABLE_WEIGHTS,
)


@dataclass(frozen=True, slots=True)
class IntegerModel:
    """Integer P08 weights plus one threshold per spiking population."""

    conv1: np.ndarray
    conv2: np.ndarray
    dense1: np.ndarray
    dense2: np.ndarray
    thresholds: tuple[int, int, int, int]

    def __post_init__(self) -> None:
        expected = (
            ("conv1", self.conv1, (CONV1.kernel, CONV1.kernel, 1, CONV1.filters)),
            (
                "conv2",
                self.conv2,
                (CONV2.kernel, CONV2.kernel, CONV2.input_channels, CONV2.filters),
            ),
            ("dense1", self.dense1, (CONV2_NEURONS, DENSE_HIDDEN)),
            ("dense2", self.dense2, (DENSE_HIDDEN, DENSE_OUTPUT)),
        )
        for name, value, shape in expected:
            array = np.asarray(value)
            if array.shape != shape:
                raise ValueError(f"{name} shape {array.shape} does not match {shape}")
            if not np.issubdtype(array.dtype, np.integer):
                raise TypeError(f"{name} must contain integer weights")
        if len(self.thresholds) != 4 or any(int(value) <= 0 for value in self.thresholds):
            raise ValueError("thresholds must contain four positive integers")

    @property
    def nonzero_weights(self) -> int:
        return sum(
            int(np.count_nonzero(array))
            for array in (self.conv1, self.conv2, self.dense1, self.dense2)
        )


POPULATION_NAMES = (
    "stage0_conv1",
    "stage1_conv2",
    "stage2_dense8",
    "stage3_output10",
)


def _flat_index(y: int, x: int, channel: int, width: int, channels: int) -> int:
    return (y * width + x) * channels + channel


def _compartment(threshold: int) -> CompartmentConfig:
    # Full current decay means only same-tick input enters the voltage update.
    # Zero voltage decay produces persistent integrate-and-fire voltage.  The
    # accepted core uses hard reset-to-zero when threshold is crossed.
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=0,
        threshold=int(threshold),
        reset_voltage=0,
        refractory_ticks=0,
    )


def _conv_input_connections(weights: np.ndarray) -> tuple[ProjectionConnection, ...]:
    result: list[ProjectionConnection] = []
    for oy in range(CONV1.output_height):
        for ox in range(CONV1.output_width):
            for oc in range(CONV1.filters):
                destination = _flat_index(
                    oy, ox, oc, CONV1.output_width, CONV1.filters
                )
                for ky in range(CONV1.kernel):
                    iy = oy * CONV1.stride + ky
                    for kx in range(CONV1.kernel):
                        ix = ox * CONV1.stride + kx
                        source = iy * SOURCE_WIDTH + ix
                        weight = int(weights[ky, kx, 0, oc])
                        if weight:
                            result.append(
                                ProjectionConnection(source, destination, weight)
                            )
    return tuple(result)


def _conv2_connections(weights: np.ndarray) -> tuple[ProjectionConnection, ...]:
    result: list[ProjectionConnection] = []
    for oy in range(CONV2.output_height):
        for ox in range(CONV2.output_width):
            for oc in range(CONV2.filters):
                destination = _flat_index(
                    oy, ox, oc, CONV2.output_width, CONV2.filters
                )
                for ky in range(CONV2.kernel):
                    iy = oy * CONV2.stride + ky
                    for kx in range(CONV2.kernel):
                        ix = ox * CONV2.stride + kx
                        for ic in range(CONV2.input_channels):
                            source = _flat_index(
                                iy, ix, ic, CONV1.output_width, CONV1.filters
                            )
                            weight = int(weights[ky, kx, ic, oc])
                            if weight:
                                result.append(
                                    ProjectionConnection(source, destination, weight)
                                )
    return tuple(result)


def _dense_connections(weights: np.ndarray) -> tuple[ProjectionConnection, ...]:
    source_count, destination_count = weights.shape
    return tuple(
        ProjectionConnection(source, destination, int(weights[source, destination]))
        for source in range(source_count)
        for destination in range(destination_count)
        if int(weights[source, destination]) != 0
    )


def build_network(model: IntegerModel) -> NetworkSpec:
    """Build the exact P06 graph consumed by both Python and FPGA paths."""

    thresholds = tuple(int(value) for value in model.thresholds)
    populations = (
        PopulationSpec(
            POPULATION_NAMES[0],
            CONV1_NEURONS,
            _compartment(thresholds[0]),
        ),
        PopulationSpec(
            POPULATION_NAMES[1],
            CONV2_NEURONS,
            _compartment(thresholds[1]),
        ),
        PopulationSpec(
            POPULATION_NAMES[2],
            DENSE_HIDDEN,
            _compartment(thresholds[2]),
        ),
        PopulationSpec(
            POPULATION_NAMES[3],
            DENSE_OUTPUT,
            _compartment(thresholds[3]),
        ),
    )
    return NetworkSpec(
        populations=populations,
        input_populations=(
            InputPopulationSpec("pixels", SOURCE_HEIGHT * SOURCE_WIDTH),
        ),
        input_projections=(
            InputProjectionSpec(
                "pixels_to_conv1",
                "pixels",
                POPULATION_NAMES[0],
                _conv_input_connections(np.asarray(model.conv1)),
            ),
        ),
        projections=(
            ProjectionSpec(
                "conv1_to_conv2",
                POPULATION_NAMES[0],
                POPULATION_NAMES[1],
                _conv2_connections(np.asarray(model.conv2)),
            ),
            ProjectionSpec(
                "conv2_to_dense8",
                POPULATION_NAMES[1],
                POPULATION_NAMES[2],
                _dense_connections(np.asarray(model.dense1)),
            ),
            ProjectionSpec(
                "dense8_to_output10",
                POPULATION_NAMES[2],
                POPULATION_NAMES[3],
                _dense_connections(np.asarray(model.dense2)),
            ),
        ),
    )


def make_mapping_probe_model() -> IntegerModel:
    """Return deterministic nonzero weights for structural/resource auditing.

    Dense weights intentionally vary by source/destination to avoid accidental
    sharing that a trained model cannot be assumed to possess.  Convolution
    kernels remain spatially shared exactly as they will be after training.
    """

    conv1 = (np.arange(CONV1.weight_count, dtype=np.int16) % 31 + 1).reshape(
        CONV1.kernel, CONV1.kernel, 1, CONV1.filters
    )
    conv2 = (np.arange(CONV2.weight_count, dtype=np.int16) % 61 + 1).reshape(
        CONV2.kernel,
        CONV2.kernel,
        CONV2.input_channels,
        CONV2.filters,
    )
    dense1 = np.fromfunction(
        lambda source, destination: ((source * 17 + destination * 3) % 63) + 1,
        (CONV2_NEURONS, DENSE_HIDDEN),
        dtype=int,
    ).astype(np.int16)
    dense2 = np.fromfunction(
        lambda source, destination: ((source * 11 + destination * 5) % 63) + 1,
        (DENSE_HIDDEN, DENSE_OUTPUT),
        dtype=int,
    ).astype(np.int16)
    return IntegerModel(conv1, conv2, dense1, dense2, (64, 64, 64, 64))


def topology_report() -> Mapping[str, int]:
    return {
        "conv1_neurons": CONV1_NEURONS,
        "conv2_neurons": CONV2_NEURONS,
        "dense_hidden_neurons": DENSE_HIDDEN,
        "output_neurons": DENSE_OUTPUT,
        "total_spiking_neurons": TOTAL_SPIKING_NEURONS,
        "trainable_weights": TOTAL_TRAINABLE_WEIGHTS,
    }
