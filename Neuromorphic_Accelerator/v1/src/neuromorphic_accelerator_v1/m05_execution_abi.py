"""M05.10 CPU-side AXIS payload layout for one VERIFIED Vitis 2025.2 top.

Bit positions come from the real M05 generated-Verilog direct-XSim benches,
not a generic AXI specification. The 128/192/128/192-bit TDATA words are
little-endian *lane interpretations* of HLS native C struct layouts.

Synapse: [31:0] pre, [63:32] post, [95:64] signed weight,
         [127:96] padding, [191:128] delay.
Trace: [63:0] tick, [95:64] ID, [127:96] signed voltage,
       [135:128] spike, [143:136] evaluated, [159:144] padding,
       [191:160] delivered_count.

This is a byte representation for a future transport adapter, not a real
DMA driver. AXI-stream word ordering, bus-width adaptation, byte alignment,
TLAST framing and host/PS endianness still require actual integration proof.
"""
from __future__ import annotations

import struct

from .m05_execution_controller import (
    NeuronConfig, SynapseConfig, ExternalEvent,
)
from .m05_trace_commit import RollingTraceRow

NEURON_BYTES = 16
SYNAPSE_BYTES = 24
EXTERNAL_BYTES = 16
TRACE_BYTES = 24


def encode_neuron(neuron: NeuronConfig) -> bytes:
    if type(neuron) is not NeuronConfig:
        raise TypeError("expected validated NeuronConfig")
    return struct.pack("<iiii", neuron.initial_voltage, neuron.bias,
                       neuron.threshold, neuron.reset_voltage)


def encode_synapse(synapse: SynapseConfig) -> bytes:
    if type(synapse) is not SynapseConfig:
        raise TypeError("expected validated SynapseConfig")
    return struct.pack("<IIi4xQ", synapse.pre, synapse.post,
                       synapse.weight, synapse.delay)


def encode_external(event: ExternalEvent) -> bytes:
    if type(event) is not ExternalEvent:
        raise TypeError("expected validated ExternalEvent")
    return struct.pack("<QIi", event.tick, event.neuron_id, event.current)


def decode_trace(word: bytes) -> RollingTraceRow:
    if type(word) is not bytes or len(word) != TRACE_BYTES:
        raise ValueError("expected exactly 24 bytes of captured trace TDATA")
    tick, neuron, voltage, spike, evaluated, delivered_count = struct.unpack(
        "<QIiBB2xI", word
    )
    # Further semantic, per-run tick/neuron framing and range checks are
    # performed by RollingTraceCommitGate, NOT silently normalized here.
    return RollingTraceRow(
        tick, neuron, voltage, spike, evaluated, delivered_count
    )


def encode_trace_for_native_test(row: RollingTraceRow) -> bytes:
    """TEST VECTOR ONLY: generate known TDATA bytes, not a host write port."""
    if type(row) is not RollingTraceRow:
        raise TypeError("expected RollingTraceRow")
    return struct.pack("<QIiBB2xI", row.tick, row.neuron_id, row.voltage,
                       row.spike, row.evaluated, row.delivered_count)
