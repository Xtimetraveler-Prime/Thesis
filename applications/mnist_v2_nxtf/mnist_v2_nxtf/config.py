"""Frozen P08 candidate topology and experiment constants.

The active revision was selected after the initial 3/6-filter candidate plateaued
at 88.10% validation accuracy after 50 epochs.  This revision spends a similar
parameter budget on more feature channels while still fitting the already
accepted three-context FPGA shell.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCE_HEIGHT = 28
SOURCE_WIDTH = 28
SOURCE_CHANNELS = 1
NUM_CLASSES = 10
VALIDATION_SIZE = 5_000
VALIDATION_SEED = 0x4D4E4953
PRIMARY_TIMESTEPS = 100
CHARACTERIZATION_TIMESTEPS = (16, 32, 64, 100)
BATCH_SIZE = 128
LEARNING_RATE = 1e-3
MAX_EPOCHS = 50

# Keep enough headroom for signed integer conversion while staying comfortably
# inside the P03/P05 24-bit saturating state datapath.
WEIGHT_QUANT_MAX = 63


@dataclass(frozen=True, slots=True)
class ConvStage:
    name: str
    input_height: int
    input_width: int
    input_channels: int
    filters: int
    kernel: int
    stride: int

    @property
    def output_height(self) -> int:
        return (self.input_height - self.kernel) // self.stride + 1

    @property
    def output_width(self) -> int:
        return (self.input_width - self.kernel) // self.stride + 1

    @property
    def output_neurons(self) -> int:
        return self.output_height * self.output_width * self.filters

    @property
    def weight_count(self) -> int:
        return self.kernel * self.kernel * self.input_channels * self.filters


CONV1 = ConvStage(
    name="stage0_conv1",
    input_height=28,
    input_width=28,
    input_channels=1,
    filters=12,
    kernel=5,
    stride=2,
)

CONV2 = ConvStage(
    name="stage1_conv2",
    input_height=CONV1.output_height,
    input_width=CONV1.output_width,
    input_channels=CONV1.filters,
    filters=12,
    kernel=3,
    stride=2,
)

DENSE_HIDDEN = 20
DENSE_OUTPUT = NUM_CLASSES

CONV1_NEURONS = CONV1.output_neurons
CONV2_NEURONS = CONV2.output_neurons
DENSE1_WEIGHTS = CONV2_NEURONS * DENSE_HIDDEN
DENSE2_WEIGHTS = DENSE_HIDDEN * DENSE_OUTPUT
TOTAL_SPIKING_NEURONS = CONV1_NEURONS + CONV2_NEURONS + DENSE_HIDDEN + DENSE_OUTPUT
TOTAL_TRAINABLE_WEIGHTS = CONV1.weight_count + CONV2.weight_count + DENSE1_WEIGHTS + DENSE2_WEIGHTS

# P08 intentionally uses no learned biases because P06 currently maps weighted
# projections and per-population compartment configuration, not arbitrary
# per-neuron learned bias vectors.
USE_BIAS = False

if (CONV1.output_height, CONV1.output_width, CONV1.filters) != (12, 12, 12):
    raise RuntimeError("P08 conv1 shape contract changed")
if (CONV2.output_height, CONV2.output_width, CONV2.filters) != (5, 5, 12):
    raise RuntimeError("P08 conv2 shape contract changed")
if TOTAL_SPIKING_NEURONS != 2058:
    raise RuntimeError("P08 candidate must contain exactly 2058 spiking neurons")
if TOTAL_TRAINABLE_WEIGHTS != 7796:
    raise RuntimeError("P08 candidate must contain exactly 7796 trainable weights")
