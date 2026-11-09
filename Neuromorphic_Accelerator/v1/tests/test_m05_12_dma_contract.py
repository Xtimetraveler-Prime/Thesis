"""M05.12a synthetic host DMA admission/lifecycle tests; never physical IO."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuromorphic_accelerator_v1.m05_execution_controller import (
    RunPlan, NeuronConfig, SynapseConfig, ExternalEvent,
)
from neuromorphic_accelerator_v1.m05_dma_frame import (
    build_fake_dma_packet_for_test,
)
from neuromorphic_accelerator_v1.m05_trace_commit import RollingTraceRow
from neuromorphic_accelerator_v1.m05_12_dma_contract import (
    DMAAdmissionError, DMALifecycleError, DMALimits, DMAStage,
    S2MMEvidence, DMASessionLedger, prepare_dma_run,
)


def plan(n=2, ticks=12, synapses=(), events=()):
    return RunPlan(
        neurons=tuple(NeuronConfig(0, 0, 5, 0) for _ in range(n)),
        synapses=tuple(synapses),
        external_events=tuple(events),
        ticks=ticks,
    )


def packet(p, session, status=0, rows=None):
    if rows is None:
        rows = tuple(RollingTraceRow(t, i, 0, 0, 0, 0)
                     for t in range(p.ticks) for i in range(len(p.neurons)))
    return build_fake_dma_packet_for_test(rows, status=status, session_id=session)


def receipt(data, **overrides):
    fields = dict(
        packet=data, actual_bytes=len(data), dma_completed=True,
        tlast_seen=True, cpu_cache_invalidated=True,
        no_outstanding_writes=True, transport_quiescent=True,
    )
    fields.update(overrides)
    return S2MMEvidence(**fields)


def active(p=None, sid=0x123456789ABCDEF0):
    p = p or plan()
    prepared = prepare_dma_run(p, session_id=sid, limits=DMALimits(24))
    ledger = DMASessionLedger(prepared)
    ledger.arm_receive(device_owns_buffer=True)
    ledger.start_session()
    return prepared, ledger


def inputs_done(prepared, ledger):
    for desc in prepared.sources:
        ledger.complete_input(
            desc.port, actual_bytes=desc.transfer_bytes,
            dma_completed=True, tlast_seen=True, device_cache_ready=True,
        )


class M0512DMAContractTests(unittest.TestCase):
    def test_exact_packed_buffers_s2mm_worst_case_and_source_counts(self):
        p = plan(synapses=(SynapseConfig(0, 1, 5, 8),),
                 events=(ExternalEvent(0, 0, 5),))
        d = prepare_dma_run(p, session_id=0x123456789ABCDEF0,
                            limits=DMALimits(24))
        self.assertEqual([(s.port, s.transfer_bytes) for s in d.sources], [
            ("neurons", 64), ("synapses", 32), ("external_events", 32)])
        self.assertEqual(d.s2mm_capacity_bytes, (2 * 12 + 1) * 32)
        self.assertEqual(d.source_length("synapses"), 32)
        self.assertEqual(d.session_id, 0x123456789ABCDEF0)
        self.assertTrue(all(len(x.payload) % 32 == 0 for x in d.sources))

    def test_zero_count_mm2s_skipped_not_zero_length_submitted(self):
        d = prepare_dma_run(plan(), session_id=1, limits=DMALimits(24))
        self.assertEqual(tuple(x.port for x in d.sources), ("neurons",))
        self.assertEqual(d.source_length("synapses"), 0)
        self.assertEqual(d.source_length("external_events"), 0)
        self.assertEqual(d.source_length("neurons"), 64)

    def test_receive_capacity_includes_terminal_footer(self):
        p = plan(n=1024, ticks=64)
        with self.assertRaisesRegex(DMAAdmissionError, "S2MM"):
            prepare_dma_run(p, session_id=1, limits=DMALimits(21))
        d = prepare_dma_run(p, session_id=1, limits=DMALimits(22))
        self.assertEqual(d.s2mm_capacity_bytes, 2_097_184)

    def test_length_width_does_not_silently_split_stream_into_early_tlast(self):
        p = plan(n=1024, ticks=1)
        with self.assertRaisesRegex(DMAAdmissionError, "neurons"):
            prepare_dma_run(p, session_id=1, limits=DMALimits(14))
        d = prepare_dma_run(p, session_id=1, limits=DMALimits(24))
        self.assertEqual(len(d.sources), 1)
        self.assertEqual(d.sources[0].transfer_bytes, 32768)

    def test_unsupported_ip_mode_width_or_identity_fail_closed(self):
        for wrong in (-1, 7, 27, True, 1.2):
            with self.subTest(length_width=wrong):
                with self.assertRaises(DMAAdmissionError):
                    DMALimits(wrong)
        for bad in (
            {"stream_width_bits": 128},
            {"scatter_gather": True},
            {"micro_mode": True},
            {"micro_mode": 1},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(DMAAdmissionError):
                    DMALimits(24, **bad)
        for sid in (True, -1, 1 << 64, "1"):
            with self.subTest(session=sid):
                with self.assertRaises(DMAAdmissionError):
                    prepare_dma_run(plan(), session_id=sid, limits=DMALimits(24))

    def test_receive_must_be_armed_before_start_and_sticky_fault(self):
        d = prepare_dma_run(plan(), session_id=1, limits=DMALimits(24))
        ledger = DMASessionLedger(d)
        with self.assertRaises(DMALifecycleError):
            ledger.start_session()
        self.assertEqual(ledger.stage, DMAStage.FAULT)
        with self.assertRaises(DMALifecycleError):
            ledger.arm_receive(device_owns_buffer=True)

    def test_receive_buffer_ownership_before_arm(self):
        d = prepare_dma_run(plan(), session_id=1, limits=DMALimits(24))
        ledger = DMASessionLedger(d)
        with self.assertRaises(DMALifecycleError):
            ledger.arm_receive(device_owns_buffer=False)
        self.assertEqual(ledger.stage, DMAStage.FAULT)

    def test_positive_success_uses_actual_packet_and_full_input_completion(self):
        p = plan()
        d, ledger = active(p)
        inputs_done(d, ledger)
        ledger.record_hls_done(0)
        ledger.request_finish()
        frame = ledger.complete_receive(receipt(packet(p, d.session_id)))
        self.assertTrue(frame.result.accepted)
        self.assertEqual(len(frame.result.rows), 24)
        self.assertEqual(frame.actual_dma_bytes, d.s2mm_capacity_bytes)
        self.assertEqual(ledger.stage, DMAStage.VERIFIED)
        with self.assertRaises(DMALifecycleError):
            ledger.start_session()
        self.assertEqual(ledger.stage, DMAStage.FAULT)

    def test_duplicate_mm2s_and_false_dma_or_cache_proof_are_sticky(self):
        for extra in ("duplicate", "short", "bad_tlast", "stale_cache", "zero"):
            with self.subTest(extra=extra):
                d, ledger = active()
                desc = d.sources[0]
                if extra == "duplicate":
                    ledger.complete_input(
                        desc.port, actual_bytes=desc.transfer_bytes,
                        dma_completed=True, tlast_seen=True,
                        device_cache_ready=True)
                kwargs = dict(
                    actual_bytes=desc.transfer_bytes,
                    dma_completed=True, tlast_seen=True,
                    device_cache_ready=True)
                if extra == "short":
                    kwargs["actual_bytes"] -= 32
                if extra == "bad_tlast":
                    kwargs["tlast_seen"] = False
                if extra == "stale_cache":
                    kwargs["device_cache_ready"] = False
                if extra == "zero":
                    desc = replace(desc, port="external_events")
                with self.assertRaises(DMALifecycleError):
                    ledger.complete_input(desc.port, **kwargs)
                self.assertEqual(ledger.stage, DMAStage.FAULT)

    def test_hls_completion_must_be_latched_before_footer(self):
        _, ledger = active()
        with self.assertRaises(DMALifecycleError):
            ledger.request_finish()
        self.assertEqual(ledger.stage, DMAStage.FAULT)
        for bad in (-1, 7, True, None):
            with self.subTest(status=bad):
                _, fresh = active()
                with self.assertRaises(DMALifecycleError):
                    fresh.record_hls_done(bad)

    def test_success_rejects_missing_mm2s_completion(self):
        p = plan()
        d, ledger = active(p)
        ledger.record_hls_done(0)
        ledger.request_finish()
        with self.assertRaises(DMALifecycleError):
            ledger.complete_receive(receipt(packet(p, d.session_id)))
        self.assertEqual(ledger.stage, DMAStage.FAULT)

    def test_fail_closed_on_missing_tlast_cache_invalidity_or_write_fence(self):
        p = plan()
        for bad in (
            {"tlast_seen": False},
            {"cpu_cache_invalidated": False},
            {"no_outstanding_writes": False},
            {"transport_quiescent": False},
            {"dma_completed": False},
            {"actual_bytes": 0},
            {"actual_bytes": 33},
        ):
            with self.subTest(bad=bad):
                d, ledger = active(p)
                inputs_done(d, ledger)
                ledger.record_hls_done(0)
                ledger.request_finish()
                with self.assertRaises(DMALifecycleError):
                    ledger.complete_receive(receipt(packet(p, d.session_id),
                                                    **bad))
                self.assertEqual(ledger.stage, DMAStage.FAULT)

    def test_status4_partial_frame_never_commits_and_requires_reset(self):
        p = plan(events=(ExternalEvent(0, 0, 5),))
        d, ledger = active(p)
        partial = tuple(RollingTraceRow(t, n, 0, 0, 0, 0)
                        for t in range(4) for n in range(2))
        ledger.record_hls_done(4)
        ledger.request_finish()
        frame = ledger.complete_receive(receipt(
            packet(p, d.session_id, status=4, rows=partial)))
        self.assertFalse(frame.result.accepted)
        self.assertEqual(frame.result.rows, ())
        self.assertEqual(frame.result.drained_rows, 8)
        self.assertEqual(ledger.stage, DMAStage.FAULT)
        with self.assertRaises(DMALifecycleError):
            ledger.start_session()

    def test_wrong_session_or_truncated_success_never_published(self):
        p = plan()
        for corrupt in ("session", "truncated", "extra"):
            with self.subTest(corrupt=corrupt):
                d, ledger = active(p)
                inputs_done(d, ledger)
                ledger.record_hls_done(0)
                ledger.request_finish()
                if corrupt == "session":
                    data = packet(p, d.session_id + 1)
                elif corrupt == "truncated":
                    data = packet(p, d.session_id)[:-32]
                else:
                    data = packet(p, d.session_id) + b"\0" * 32
                with self.assertRaises(DMALifecycleError):
                    ledger.complete_receive(receipt(data))
                self.assertEqual(ledger.stage, DMAStage.FAULT)

    def test_explicit_abort_is_sticky_and_no_auto_recovery(self):
        _, ledger = active()
        with self.assertRaisesRegex(DMALifecycleError, "timeout"):
            ledger.abort("timeout before missing TLAST")
        with self.assertRaises(DMALifecycleError):
            ledger.record_hls_done(0)
        self.assertEqual(ledger.stage, DMAStage.FAULT)


if __name__ == "__main__":
    unittest.main()
