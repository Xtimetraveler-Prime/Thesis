"""M05.11a HOST-ONLY synthetic DMA packet, ABI and RTL-source tests.

Native tests do not execute RTL, DMA, Vivado, Vitis, AXI-Lite or the board.
Real packetizer RTL XSim and physical PS DMA are separate acceptance gates.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_execution_controller import (
    NeuronConfig, SynapseConfig, ExternalEvent, RunPlan
)
from neuromorphic_accelerator_v1.m05_trace_commit import RollingTraceRow
from neuromorphic_accelerator_v1.m05_dma_frame import (
    DMAFrameError, DMA_BEAT_BYTES, FOOTER_MAGIC, MAX_DMA_PACKET_BYTES,
    accept_dma_frame, build_fake_dma_packet_for_test, build_mm2s_buffers,
)


def rows(n=2, ticks=3):
    return tuple(RollingTraceRow(t, i, 0, int(t == 0 and i == 0),
                                 int(t == 0 and i == 0), int(t == 0))
                 for t in range(ticks) for i in range(n))


def capture(data, **overrides):
    options = dict(
        packet=data, session_id=42, neuron_count=2, ticks=3,
        hls_status=0, transferred_bytes=len(data),
        dma_completed=True, tlast_certified=True,
        transport_quiescent=True
    )
    options.update(overrides)
    return accept_dma_frame(**options)


class M05DMAFrameTests(unittest.TestCase):
    def test_success_requires_footer_and_exact_trace_frame(self):
        packet = build_fake_dma_packet_for_test(rows(), status=0, session_id=42)
        r = capture(packet)
        self.assertTrue(r.result.accepted)
        self.assertEqual(len(r.result.rows), 6)
        self.assertEqual(r.received_trace_beats, 6)
        self.assertEqual(r.actual_dma_bytes, 7 * 32)
        self.assertEqual(r.session_id, 42)
        self.assertEqual(r.hls_status, 0)

    def test_late_bad_external_discards_all_provisional_trace(self):
        partial = rows()[:4]
        packet = build_fake_dma_packet_for_test(partial, status=4, session_id=42)
        r = capture(packet, hls_status=4)
        self.assertEqual(r.result.rows, ())
        self.assertFalse(r.result.accepted)
        self.assertEqual(r.result.status, 4)
        self.assertEqual(r.result.drained_rows, 4)
        self.assertEqual(r.received_trace_beats, 4)

    def test_zero_trace_hardware_error_still_has_one_terminal_beat(self):
        pkt = build_fake_dma_packet_for_test((), status=3, session_id=42)
        self.assertEqual(len(pkt), 32)
        r = capture(pkt, hls_status=3)
        self.assertFalse(r.result.accepted)
        self.assertEqual(r.received_trace_beats, 0)
        self.assertEqual(r.actual_dma_bytes, 32)

    def test_success_with_zero_or_short_trace_is_never_accepted(self):
        for part in ((), rows()[:5]):
            with self.subTest(n=len(part)):
                pkt = build_fake_dma_packet_for_test(
                    part, status=0, session_id=42)
                with self.assertRaisesRegex(DMAFrameError, "truncated"):
                    capture(pkt)

    def test_nonzero_status_must_match_actual_hls_register(self):
        pkt = build_fake_dma_packet_for_test(
            rows()[:3], status=4, session_id=42)
        with self.assertRaisesRegex(DMAFrameError, "ap_return"):
            capture(pkt, hls_status=0)

    def test_wrong_session_id_or_magic_cannot_be_replayed(self):
        pkt = build_fake_dma_packet_for_test(rows(), status=0, session_id=42)
        for tampered in (
            pkt[:-16] + (43).to_bytes(8, "little") + pkt[-8:],
            pkt[:-8] + b"\0" * 8,
        ):
            with self.assertRaisesRegex(DMAFrameError, "footer"):
                capture(tampered)

    def test_footer_row_count_is_verified_against_dma_actual_bytes(self):
        pkt = bytearray(build_fake_dma_packet_for_test(
            rows(), status=0, session_id=42))
        pkt[-24:-20] = (5).to_bytes(4, "little")
        with self.assertRaisesRegex(DMAFrameError, "count"):
            capture(bytes(pkt))

    def test_invalid_footer_reserved_bits_are_rejected(self):
        pkt = bytearray(build_fake_dma_packet_for_test(
            rows(), status=0, session_id=42))
        pkt[-32] = 9
        with self.assertRaisesRegex(DMAFrameError, "reserved"):
            capture(bytes(pkt))

    def test_dma_completion_last_and_idle_fence_are_mandatory(self):
        pkt = build_fake_dma_packet_for_test(
            rows(), status=0, session_id=42)
        for flag in ("dma_completed", "tlast_certified",
                     "transport_quiescent"):
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(DMAFrameError, "DMA incomplete"):
                    capture(pkt, **{flag: False})

    def test_wrong_reported_byte_count_and_alignment_rejected(self):
        pkt = build_fake_dma_packet_for_test(rows(), status=0, session_id=42)
        with self.assertRaisesRegex(DMAFrameError, "transfer count"):
            capture(pkt, transferred_bytes=len(pkt)+32)
        with self.assertRaisesRegex(DMAFrameError, "transfer count"):
            capture(pkt[:-1], transferred_bytes=len(pkt))
        with self.assertRaisesRegex(DMAFrameError, "32-byte"):
            capture(pkt[:-1], transferred_bytes=len(pkt)-1)

    def test_corrupted_trace_padding_and_extra_rows_rejected(self):
        pkt = bytearray(build_fake_dma_packet_for_test(rows(), status=0,
                                                        session_id=42))
        pkt[24] = 0x55
        with self.assertRaisesRegex(DMAFrameError, "padding"):
            capture(bytes(pkt))
        extra = build_fake_dma_packet_for_test(
            rows() + (rows()[-1],), status=4, session_id=42)
        with self.assertRaisesRegex(DMAFrameError, "capacity"):
            capture(extra, hls_status=4)

    def test_bad_trace_fields_poison_only_whole_transaction(self):
        pkt = build_fake_dma_packet_for_test(
            rows(), status=0, session_id=42)
        word = bytearray(pkt)
        word[8:12] = (99).to_bytes(4, "little")
        with self.assertRaisesRegex(DMAFrameError, "atomic"):
            capture(bytes(word))

    def test_input_buffers_are_32byte_fixed_width_and_zero_padded(self):
        plan = RunPlan(
            neurons=(NeuronConfig(0, 0, 5, 0),
                     NeuronConfig(-1, 0, 5, 0)),
            synapses=(SynapseConfig(0, 1, -12, 8),),
            external_events=(ExternalEvent(0, 0, 5),), ticks=3
        )
        payload = build_mm2s_buffers(plan)
        self.assertEqual(tuple(map(len, (
            payload["neurons"], payload["synapses"],
            payload["external_events"]
        ))), (64, 32, 32))
        self.assertEqual(payload["neurons"][16:32], b"\0" * 16)
        self.assertEqual(payload["synapses"][24:32], b"\0" * 8)
        self.assertEqual(payload["external_events"][16:], b"\0" * 16)

    def test_no_synapse_or_external_produces_empty_dma_buffers(self):
        plan = RunPlan((NeuronConfig(0, 0, 5, 0),), (), (), ticks=1)
        x = build_mm2s_buffers(plan)
        self.assertEqual(len(x["neurons"]), 32)
        self.assertEqual(x["synapses"], b"")
        self.assertEqual(x["external_events"], b"")

    def test_real_dma_buffer_bound_works_for_full_1024x64_profile(self):
        self.assertEqual(MAX_DMA_PACKET_BYTES, 2097184)
        self.assertEqual(DMA_BEAT_BYTES, 32)
        self.assertEqual(FOOTER_MAGIC, int.from_bytes(b"M0511END", "big"))

    def test_unknown_status_and_bool_session_are_rejected(self):
        pkt = build_fake_dma_packet_for_test(rows(), status=0, session_id=42)
        for value in (7, -1, True, "0"):
            with self.subTest(value=value):
                with self.assertRaises(DMAFrameError):
                    capture(pkt, hls_status=value)
        with self.assertRaises(DMAFrameError):
            capture(pkt, session_id=True)

    def test_packetizer_source_has_all_critical_fail_closed_contracts(self):
        rtl = (ROOT / "rtl/m05_11/m05_trace_dma_packetizer.v").read_text()
        for fragment in (
            "module m05_trace_dma_packetizer",
            "FOOTER_MAGIC = 64'h4d30353131454e44",
            "assign dma_tlast = state == FOOTER",
            "assign dma_tkeep = 32'hffffffff",
            "start_expected_rows > 32'd65536",
            "captured_rows >= expected_rows",
            "FRAME_MISMATCH = 32'hffff0001",
            "BAD_RETURN = 32'hffff0002",
            "finish_valid && finish_ready",
            "state <= FAILED",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, rtl)

    def test_ingress_source_has_padding_tlast_and_overrun_guards(self):
        rtl = (ROOT / "rtl/m05_11/m05_ingress_dma_unpad.v").read_text()
        for fragment in (
            "parameter integer PAYLOAD_WIDTH = 128",
            "s_dma_tkeep == 32'hffffffff",
            "s_dma_tlast == last_expected",
            "s_dma_tdata[255:PAYLOAD_WIDTH] == 0",
            "m_hls_tvalid = active && !fault",
            "accepted_beats < expected_beats",
            "start_expected_beats == 0",
            "fault <= 1'b1",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, rtl)


if __name__ == "__main__":
    unittest.main()
