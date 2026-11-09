"""Host-only HLS ABI layout tests: not Vivado RTL or physical AXI DMA."""
from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_execution_abi import (
    NEURON_BYTES, SYNAPSE_BYTES, EXTERNAL_BYTES, TRACE_BYTES,
    encode_neuron, encode_synapse, encode_external, decode_trace,
    encode_trace_for_native_test,
)
from neuromorphic_accelerator_v1.m05_execution_controller import (
    NeuronConfig, SynapseConfig, ExternalEvent
)
from neuromorphic_accelerator_v1.m05_trace_commit import (
    RollingTraceRow, RollingTraceCommitGate
)


class M05ControllerABITests(unittest.TestCase):
    def test_exact_hls_tdata_widths(self):
        self.assertEqual((NEURON_BYTES, SYNAPSE_BYTES, EXTERNAL_BYTES,
                          TRACE_BYTES), (16, 24, 16, 24))

    def test_neuron_four_i32_native_fields(self):
        word = encode_neuron(NeuronConfig(-32768, -1, 32767, -5))
        self.assertEqual(len(word), 16)
        self.assertEqual(struct.unpack("<iiii", word),
                         (-32768, -1, 32767, -5))
        self.assertEqual(word[:4], b"\x00\x80\xff\xff")

    def test_synapse_delay_alignment_preserves_padding(self):
        word = encode_synapse(SynapseConfig(1, 2, -32768, 8))
        self.assertEqual(len(word), 24)
        self.assertEqual(word[0:4], (1).to_bytes(4, "little"))
        self.assertEqual(word[4:8], (2).to_bytes(4, "little"))
        self.assertEqual(word[8:12], (-32768).to_bytes(
            4, "little", signed=True))
        self.assertEqual(word[12:16], b"\x00" * 4)
        self.assertEqual(word[16:24], (8).to_bytes(8, "little"))
        self.assertEqual(struct.unpack("<IIi4xQ", word), (1, 2, -32768, 8))

    def test_external_tick_is_low_64_bits(self):
        word = encode_external(ExternalEvent(63, 4, -123))
        self.assertEqual(len(word), 16)
        self.assertEqual(struct.unpack("<QIi", word), (63, 4, -123))

    def test_trace_padding_and_delivery_count_at_top_bits(self):
        row = RollingTraceRow(8, 2, -32768, 1, 1, 4096)
        word = encode_trace_for_native_test(row)
        self.assertEqual(len(word), 24)
        self.assertEqual(word[:8], (8).to_bytes(8, "little"))
        self.assertEqual(word[8:12], (2).to_bytes(4, "little"))
        self.assertEqual(word[12:16], b"\x00\x80\xff\xff")
        self.assertEqual(word[16:18], b"\x01\x01")
        self.assertEqual(word[18:20], b"\x00\x00")
        self.assertEqual(word[20:24], (4096).to_bytes(4, "little"))
        self.assertEqual(decode_trace(word), row)

    def test_trace_padding_may_be_nonzero_and_is_not_semantic(self):
        row = RollingTraceRow(1, 0, 0, 0, 0, 0)
        word = bytearray(encode_trace_for_native_test(row))
        word[18:20] = b"\xab\xcd"  # uninitialized C padding is ignored
        self.assertEqual(decode_trace(bytes(word)), row)

    def test_decode_trace_validates_bytes_and_width(self):
        for bad in (b"", b"0"*23, b"0"*25, bytearray(24), True, "0"*24):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaises(ValueError):
                    decode_trace(bad)

    def test_abi_encoder_validates_packet_types(self):
        for encoder, data in (
            (encode_neuron, (0, 0, 5, 0)),
            (encode_synapse, (0, 1, 5, 8)),
            (encode_external, (1, 0, 5)),
        ):
            with self.assertRaises(TypeError):
                encoder(data)

    def test_decoded_trace_feeds_atomic_existing_receiver(self):
        gate = RollingTraceCommitGate(1, 2)
        for t in (0, 1):
            word = encode_trace_for_native_test(
                RollingTraceRow(t, 0, 0, int(t == 0),
                                int(t == 0), int(t == 0))
            )
            gate.offer_row(decode_trace(word))
        result = gate.complete(0)
        self.assertTrue(result.accepted)
        self.assertEqual(len(result.rows), 2)

    def test_decode_invalid_values_does_not_bypass_commit_gate(self):
        word = encode_trace_for_native_test(
            RollingTraceRow(0, 0, 32768, 0, 0, 0))
        gate = RollingTraceCommitGate(1, 1)
        gate.offer_row(decode_trace(word))
        self.assertFalse(gate.complete(0).accepted)


if __name__ == "__main__":
    unittest.main()
