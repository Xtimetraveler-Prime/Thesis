"""Frozen application-level configuration for the first MNIST deployment."""

from __future__ import annotations

SOURCE_HEIGHT = 28
SOURCE_WIDTH = 28
CROP_BORDER = 4
INPUT_HEIGHT = 20
INPUT_WIDTH = 20
INPUT_AXONS = INPUT_HEIGHT * INPUT_WIDTH
OUTPUT_NEURONS = 10
PRESENTATION_TICKS = 16

# The first workload intentionally uses the simplest project-supported LIF
# profile: same-tick input is integrated, current is fully decayed before the
# next tick, voltage persists, reset is zero, and there is no refractory period.
CURRENT_DECAY = 4096
VOLTAGE_DECAY = 0
RESET_VOLTAGE = 0
REFRACTORY_TICKS = 0
FLOAT_THRESHOLD = 1.0

# Frozen K26 core-v1 implementation limits audited in MNIST-01.
FPGA_MAX_NEURONS = 256
FPGA_MAX_AXONS = 1024
FPGA_MAX_SYNAPSES = 4096
FPGA_MAX_ROUTES = 4096
FPGA_MAX_EVENTS_PER_TICK = 4096
FPGA_MAX_WEIGHT_FORMATS = 16

DENSE_SYNAPSES = INPUT_AXONS * OUTPUT_NEURONS
MAX_ENCODER_EVENTS_PER_TICK = INPUT_AXONS

if DENSE_SYNAPSES > FPGA_MAX_SYNAPSES:
    raise RuntimeError("frozen MNIST baseline exceeds FPGA synapse capacity")
if INPUT_AXONS > FPGA_MAX_AXONS:
    raise RuntimeError("frozen MNIST baseline exceeds FPGA axon capacity")
if OUTPUT_NEURONS > FPGA_MAX_NEURONS:
    raise RuntimeError("frozen MNIST baseline exceeds FPGA neuron capacity")
if MAX_ENCODER_EVENTS_PER_TICK > FPGA_MAX_EVENTS_PER_TICK:
    raise RuntimeError("frozen MNIST encoder exceeds FPGA event capacity")
