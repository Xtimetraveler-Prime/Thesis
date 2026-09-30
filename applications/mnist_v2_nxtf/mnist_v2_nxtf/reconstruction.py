"""Deterministic, source-bounded P08.1 topology reconstruction helpers.

This module does not claim to recover the unpublished layer dimensions of the
NxTF paper's frame-based MNIST benchmark. It keeps the published aggregate
anchors separate from a project reconstruction that reuses the surviving
public NxTF tutorial's four-convolution scaffold.

No training or official-test evaluation belongs in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import nsmallest
from math import prod


RECONSTRUCTION_STATUS = "ACCEPTED_P08_1_SOURCE_BOUNDED"

# Published NxTF frame-based MNIST anchors. The paper prints the neuron and
# trainable-parameter counts approximately ("~4k", "~7k") and the connection
# counts as 341k discrete versus 6,746 shared weights.
PAPER_NEURON_TARGET = 4_000
PAPER_TRAINABLE_PARAMETER_TARGET = 7_000
PAPER_EXPANDED_CONNECTION_TARGET = 341_000
PAPER_SHARED_WEIGHT_TARGET = 6_746
PAPER_TIMESTEPS = 100
PAPER_LOIHI_NEUROCORES = 14

# The surviving Intel NxTF MNIST tutorial uses this all-convolutional scaffold:
# 28 -> Conv5/s2 -> 12 -> Conv3/s1 -> 10 -> Conv3/s2 -> 4 -> Conv4 -> 1.
# The paper does not publish that its benchmark used these exact kernels or
# strides; using this scaffold is therefore PROJECT_RECONSTRUCTION, not
# SOURCED_EXACT.
TUTORIAL_KERNELS = (5, 3, 3, 4)
TUTORIAL_STRIDES = (2, 1, 2, 1)
TUTORIAL_OUTPUT_SPATIAL = ((12, 12), (10, 10), (4, 4), (1, 1))
OUTPUT_CLASSES = 10

# Search bounds are a project policy. Sixty-four is the largest channel count
# in the surviving public Intel MNIST tutorial and comfortably contains the
# aggregate-matching solutions of interest.
FILTER_SEARCH_MIN = 1
FILTER_SEARCH_MAX = 64


@dataclass(frozen=True, slots=True)
class ReconstructionMetrics:
    filters: tuple[int, int, int]
    output_channels: tuple[int, int, int, int]
    layer_neurons: tuple[int, int, int, int]
    neuron_count: int
    kernel_weights: int
    bias_count: int
    trainable_parameters: int
    expanded_connections: int
    normalized_l1_score: float

    @property
    def relative_errors(self) -> dict[str, float]:
        return {
            "neurons": (self.neuron_count - PAPER_NEURON_TARGET) / PAPER_NEURON_TARGET,
            "trainable_parameters": (
                self.trainable_parameters - PAPER_TRAINABLE_PARAMETER_TARGET
            )
            / PAPER_TRAINABLE_PARAMETER_TARGET,
            "expanded_connections": (
                self.expanded_connections - PAPER_EXPANDED_CONNECTION_TARGET
            )
            / PAPER_EXPANDED_CONNECTION_TARGET,
            "shared_weights": (
                self.kernel_weights - PAPER_SHARED_WEIGHT_TARGET
            )
            / PAPER_SHARED_WEIGHT_TARGET,
        }


def metrics_for_filters(filters: tuple[int, int, int]) -> ReconstructionMetrics:
    """Return aggregate metrics for one tutorial-scaffold channel tuple.

    ``kernel_weights`` is the ordinary convolution-kernel coefficient count.
    It is compared to the paper's 6,746 shared-weight anchor only as a
    reconstruction objective. It is not claimed to be byte-for-byte identical
    to NxTF/Loihi connection-sharing storage or to P06 shared-parameter counts.
    """

    f1, f2, f3 = filters
    if any(not FILTER_SEARCH_MIN <= value <= FILTER_SEARCH_MAX for value in filters):
        raise ValueError(
            f"filters must be in [{FILTER_SEARCH_MIN}, {FILTER_SEARCH_MAX}]"
        )

    channels = (f1, f2, f3, OUTPUT_CLASSES)
    layer_neurons = tuple(
        height * width * channels[index]
        for index, (height, width) in enumerate(TUTORIAL_OUTPUT_SPATIAL)
    )
    neuron_count = sum(layer_neurons)

    # Four valid-convolution stages, including the 10-class 4x4 output conv.
    kernel_weights = (
        5 * 5 * 1 * f1
        + 3 * 3 * f1 * f2
        + 3 * 3 * f2 * f3
        + 4 * 4 * f3 * OUTPUT_CLASSES
    )
    bias_count = sum(channels)
    trainable_parameters = kernel_weights + bias_count

    # Every output unit receives kernel_h * kernel_w * input_channels expanded
    # connections. This is the ordinary discrete graph edge count before any
    # convolutional sharing/compression.
    input_channels = (1, f1, f2, f3)
    expanded_connections = sum(
        layer_neurons[index]
        * TUTORIAL_KERNELS[index]
        * TUTORIAL_KERNELS[index]
        * input_channels[index]
        for index in range(4)
    )

    normalized_l1_score = (
        abs(neuron_count - PAPER_NEURON_TARGET) / PAPER_NEURON_TARGET
        + abs(trainable_parameters - PAPER_TRAINABLE_PARAMETER_TARGET)
        / PAPER_TRAINABLE_PARAMETER_TARGET
        + abs(expanded_connections - PAPER_EXPANDED_CONNECTION_TARGET)
        / PAPER_EXPANDED_CONNECTION_TARGET
        + abs(kernel_weights - PAPER_SHARED_WEIGHT_TARGET)
        / PAPER_SHARED_WEIGHT_TARGET
    )

    return ReconstructionMetrics(
        filters=filters,
        output_channels=channels,
        layer_neurons=layer_neurons,
        neuron_count=neuron_count,
        kernel_weights=kernel_weights,
        bias_count=bias_count,
        trainable_parameters=trainable_parameters,
        expanded_connections=expanded_connections,
        normalized_l1_score=normalized_l1_score,
    )


def _rank_key(item: ReconstructionMetrics) -> tuple[object, ...]:
    return (
        item.normalized_l1_score,
        abs(item.expanded_connections - PAPER_EXPANDED_CONNECTION_TARGET),
        abs(item.kernel_weights - PAPER_SHARED_WEIGHT_TARGET),
        abs(item.trainable_parameters - PAPER_TRAINABLE_PARAMETER_TARGET),
        abs(item.neuron_count - PAPER_NEURON_TARGET),
        item.filters,
    )


def _candidate_stream():
    for f1 in range(FILTER_SEARCH_MIN, FILTER_SEARCH_MAX + 1):
        for f2 in range(FILTER_SEARCH_MIN, FILTER_SEARCH_MAX + 1):
            for f3 in range(FILTER_SEARCH_MIN, FILTER_SEARCH_MAX + 1):
                yield metrics_for_filters((f1, f2, f3))


def ranked_reconstructions(limit: int | None = None) -> tuple[ReconstructionMetrics, ...]:
    """Enumerate tutorial-scaffold candidates under the frozen project score.

    The score gives equal weight to relative error against the four published
    aggregate anchors. This weighting is a deterministic project convention,
    not a claim about how the NxTF authors selected their network.
    """

    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        return tuple(nsmallest(limit, _candidate_stream(), key=_rank_key))
    return tuple(sorted(_candidate_stream(), key=_rank_key))


# Accepted P08.1 project reconstruction. The exact paper topology remains
# unknown/not claimed; this tuple is frozen for subsequent P08 architecture,
# training, conversion, and comparison work unless new primary evidence appears.
PROPOSED_FILTERS = (14, 20, 12)
PROPOSED_METRICS = metrics_for_filters(PROPOSED_FILTERS)


def validate_proposed_reconstruction() -> None:
    """Guard against accidental drift in the accepted project reconstruction."""

    best = ranked_reconstructions(limit=1)[0]
    if best.filters != PROPOSED_FILTERS:
        raise AssertionError(
            f"reconstruction drift: expected {PROPOSED_FILTERS}, selected {best.filters}"
        )
    if prod(TUTORIAL_OUTPUT_SPATIAL[-1]) * OUTPUT_CLASSES != 10:
        raise AssertionError("output scaffold must contain exactly ten class units")
