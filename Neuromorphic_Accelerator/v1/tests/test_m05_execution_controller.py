"""M05.10 controller tests, *entirely host simulated*, NO AXI or FPGA.

Finite-FIFO scripted transport validates cooperative ingress + output drain,
completion framing, status, timeout, explicit recovery and error quarantine.
The real PS DMA integration is a separate future hardware gate.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_execution_controller import (
    ControllerState, ExecutionController, RunPlan, NeuronConfig,
    SynapseConfig, ExternalEvent,
)
from neuromorphic_accelerator_v1.m05_execution_sim import (
    ScriptedRun, ScriptedTransport,
)
from neuromorphic_accelerator_v1.m05_trace_commit import RollingTraceRow


def plan(n=2, ticks=10, synapses=(), events=()):
    return RunPlan(
        neurons=tuple(NeuronConfig(0, 0, 5, 0) for _ in range(n)),
        synapses=tuple(synapses),
        external_events=tuple(events),
        ticks=ticks,
    )


def zero_rows(n=2, ticks=10):
    return tuple(RollingTraceRow(t, i, 0, 0, 0, 0)
                 for t in range(ticks) for i in range(n))


def recovery_rows():
    return tuple(
        RollingTraceRow(t, i, 0, int(t == 1 and i == 1),
                        int(t == 1 and i == 1), int(t == 1))
        for t in range(10) for i in range(2)
    )


class M05ExecutionControllerTests(unittest.TestCase):
    def test_success_waits_for_full_output_after_hardware_done(self):
        p = plan()
        fake = ScriptedTransport((
            ScriptedRun(zero_rows(), receive_stride=6),
        ))
        result = ExecutionController(fake).execute(p)
        self.assertTrue(result.result.accepted)
        self.assertEqual(len(result.result.rows), 20)
        self.assertEqual(result.sent_neurons, 2)
        self.assertEqual(result.sent_synapses, 0)
        self.assertEqual(result.sent_external, 0)
        self.assertEqual(fake.begin_calls, 1)
        self.assertGreater(fake.completion_observed_with_queued_rows, 0)
        self.assertGreater(fake.output_stalls, 0)
        self.assertEqual(fake.active, None)

    def test_all_input_streams_are_serviced_while_trace_drains(self):
        p = plan(n=3, ticks=4, synapses=(
            SynapseConfig(0, 1, 2, 8),
            SynapseConfig(1, 2, -2, 1)
        ), events=(
            ExternalEvent(0, 0, 1),
            ExternalEvent(2, 2, 0),
        ))
        fake = ScriptedTransport((
            ScriptedRun(zero_rows(3, 4), receive_stride=5,
                        input_capacity=1),
        ))
        report = ExecutionController(fake).execute(p)
        self.assertTrue(report.result.accepted)
        self.assertEqual((report.sent_neurons, report.sent_synapses,
                          report.sent_external), (3, 2, 2))
        self.assertEqual(len(report.result.rows), 12)
        self.assertGreater(fake.input_stalls, 0)
        self.assertGreater(fake.output_stalls, 0)

    def test_error_status_rolls_back_partials_and_quarantines(self):
        p = plan(ticks=12, events=(ExternalEvent(0, 0, 5),))
        rows = tuple(RollingTraceRow(t, i, 0, int(t == 0 and i == 0),
                                    int(t == 0 and i == 0),
                                    int(t == 0))
                     for t in range(4) for i in range(2))
        fake = ScriptedTransport((
            ScriptedRun(rows, status=4, receive_stride=1,
                        completion_before_output_drained=False),
            ScriptedRun(recovery_rows(), receive_stride=1),
        ))
        ctrl = ExecutionController(fake)
        first = ctrl.execute(p)
        self.assertFalse(first.result.accepted)
        self.assertEqual(first.result.rows, ())
        self.assertEqual(first.result.drained_rows, 8)
        self.assertEqual(first.result.status, 4)
        self.assertEqual(ctrl.state, ControllerState.FAULTED)
        self.assertEqual(fake.begin_calls, 1)
        with self.assertRaisesRegex(RuntimeError, "recovery"):
            ctrl.execute(plan())
        self.assertEqual(fake.begin_calls, 1)
        ctrl.recover()
        self.assertEqual(fake.recovery_calls, 1)
        self.assertEqual(ctrl.state, ControllerState.IDLE)
        second = ctrl.execute(plan())
        self.assertTrue(second.result.accepted)
        self.assertEqual(len(second.result.rows), 20)
        self.assertEqual(second.result.rows[3].spike, 1)
        self.assertEqual(second.result.rows[17].delivered_count, 0)
        self.assertEqual(fake.begin_calls, 2)

    def test_early_error_halts_feeds_and_requires_reset_flush(self):
        p = plan(n=3, ticks=10, synapses=(
            SynapseConfig(0, 1, 5, 8),
        ), events=(ExternalEvent(0, 0, 1),))
        fake = ScriptedTransport((
            ScriptedRun((), status=3, receive_stride=1),
        ))
        ctrl = ExecutionController(fake)
        r = ctrl.execute(p)
        self.assertEqual(r.observed_status, 3)
        self.assertFalse(r.result.accepted)
        self.assertTrue(r.needs_recovery)
        ctrl.recover()
        self.assertEqual(fake.recovery_calls, 1)

    def test_timeout_stays_faulted_and_does_not_publish_partial(self):
        p = plan(ticks=64)
        rows = tuple(RollingTraceRow(t, i, 0, 0, 0, 0)
                     for t in range(50) for i in range(2))
        fake = ScriptedTransport((ScriptedRun(rows, never_complete=True),))
        ctrl = ExecutionController(fake)
        r = ctrl.execute(p, max_service_steps=500)
        self.assertFalse(r.result.accepted)
        self.assertEqual(r.result.rows, ())
        self.assertIsNone(r.observed_status)
        self.assertIn("service-step budget", r.result.reason)
        self.assertEqual(r.service_steps, 500)
        self.assertEqual(ctrl.state, ControllerState.FAULTED)
        with self.assertRaises(RuntimeError):
            ctrl.execute(p)
        ctrl.recover()
        self.assertEqual(ctrl.state, ControllerState.IDLE)

    def test_complete_success_with_missing_output_is_not_accepted(self):
        fake = ScriptedTransport((
            ScriptedRun(zero_rows()[:-1], status=0, receive_stride=1),
        ))
        ctrl = ExecutionController(fake)
        out = ctrl.execute(plan(), max_service_steps=300)
        self.assertFalse(out.result.accepted)
        self.assertIn("service-step", out.result.reason)
        self.assertEqual(ctrl.state, ControllerState.FAULTED)

    def test_out_of_order_spikes_extra_or_invalid_trace_fail_closed(self):
        original = list(zero_rows())
        variants = []
        wrong_id = original.copy()
        wrong_id[1] = RollingTraceRow(1, 1, 0, 0, 0, 0)
        variants.append(wrong_id)
        invalid_width = original.copy()
        invalid_width[0] = RollingTraceRow(0, 0, 32768, 0, 0, 0)
        variants.append(invalid_width)
        extra = original.copy() + [original[-1]]
        variants.append(extra)
        for rows in variants:
            with self.subTest(rows=rows[:3]):
                fake = ScriptedTransport((
                    ScriptedRun(tuple(rows), receive_stride=1),))
                ctrl = ExecutionController(fake)
                r = ctrl.execute(plan(), max_service_steps=1000)
                self.assertFalse(r.result.accepted)
                self.assertEqual(r.result.rows, ())
                self.assertEqual(ctrl.state, ControllerState.FAULTED)

    def test_success_requires_real_quiescence_fence(self):
        fake = ScriptedTransport((
            ScriptedRun(zero_rows(1, 1), receive_stride=1,
                        quiescent_delay=80),
        ))
        ctrl = ExecutionController(fake)
        r = ctrl.execute(plan(n=1, ticks=1), max_service_steps=200)
        self.assertTrue(r.result.accepted)
        self.assertGreaterEqual(r.service_steps, 80)
        self.assertGreater(fake.quiescent_checks, 0)

    def test_unknown_completion_code_forces_abort(self):
        class BadStatus(ScriptedTransport):
            def poll_completion(self):
                x = super().poll_completion()
                return 700 if x is not None else None
        ctrl = ExecutionController(
            BadStatus((ScriptedRun(zero_rows(1, 1), receive_stride=1),))
        )
        r = ctrl.execute(plan(n=1, ticks=1))
        self.assertFalse(r.result.accepted)
        self.assertIn("invalid/unknown", r.result.reason)
        self.assertIsNone(r.observed_status)

    def test_inconsistent_latched_status_forces_abort(self):
        class Inconsistent(ScriptedTransport):
            def poll_completion(self):
                x = super().poll_completion()
                if x is None:
                    return None
                return 4 if self.clock > 7 else 0
        p = plan(n=1, ticks=1)
        fake = Inconsistent((ScriptedRun(zero_rows(1, 1),
                                      quiescent_delay=30),))
        ctrl = ExecutionController(fake)
        r = ctrl.execute(p)
        self.assertFalse(r.result.accepted)
        self.assertTrue(r.needs_recovery)

    def test_backend_exception_is_quarantined_not_leaked(self):
        for operation in ("begin", "try_send", "try_receive", "poll_completion",
                          "advance", "is_quiescent"):
            with self.subTest(op=operation):
                class Broken(ScriptedTransport):
                    pass
                def explode(*args, **kwargs):
                    raise RuntimeError("injected DMA transfer fault")
                setattr(Broken, operation, explode)
                fake = Broken((ScriptedRun(zero_rows(1, 1),
                                           receive_stride=1),))
                ctrl = ExecutionController(fake)
                r = ctrl.execute(plan(n=1, ticks=1))
                self.assertFalse(r.result.accepted)
                self.assertIn("transport exception", r.result.reason)
                self.assertTrue(r.needs_recovery)

    def test_recovery_failure_stays_faulted(self):
        class BrokenReset(ScriptedTransport):
            def reset_and_verify_idle(self):
                raise RuntimeError("device did not become idle")
        fake = BrokenReset((ScriptedRun((), status=4),))
        ctrl = ExecutionController(fake)
        self.assertFalse(ctrl.execute(plan(n=1, ticks=1)).result.accepted)
        with self.assertRaisesRegex(RuntimeError, "did not become idle"):
            ctrl.recover()
        self.assertEqual(ctrl.state, ControllerState.FAULTED)

    def test_recover_when_idle_is_rejected(self):
        ctrl = ExecutionController(ScriptedTransport(()))
        with self.assertRaisesRegex(RuntimeError, "prior fault"):
            ctrl.recover()

    def test_invalid_service_budget_and_deadline_rejected_before_begin(self):
        fake = ScriptedTransport((ScriptedRun(zero_rows(1, 1)),))
        ctrl = ExecutionController(fake)
        for bad in (0, -1, True, 1.5, 10000001):
            with self.subTest(steps=bad):
                with self.assertRaises(ValueError):
                    ctrl.execute(plan(n=1, ticks=1), max_service_steps=bad)
        for bad in (0, -1, True, None, 4000, "3"):
            with self.subTest(deadline=bad):
                with self.assertRaises(ValueError):
                    ctrl.execute(plan(n=1, ticks=1), wall_timeout_s=bad)
        self.assertEqual(fake.begin_calls, 0)
        self.assertEqual(ctrl.state, ControllerState.IDLE)

    def test_reject_shape_without_any_hardware_access(self):
        n = NeuronConfig(0, 0, 5, 0)
        valid = plan()
        bad = (
            dict(neurons=(), synapses=(), external_events=(), ticks=1),
            dict(neurons=(n,)*1025, synapses=(), external_events=(), ticks=1),
            dict(neurons=(n,), synapses=(SynapseConfig(0, 1, 1, 1),),
                 external_events=(), ticks=1),
            dict(neurons=(n,), synapses=(), external_events=(), ticks=65),
            dict(neurons=(n,), synapses=(), external_events=(
                ExternalEvent(1, 0, 2), ExternalEvent(0, 0, 2)), ticks=2),
            dict(neurons=(n,), synapses=(), external_events=(
                ExternalEvent(2, 0, 2),), ticks=2),
            dict(neurons=(n,), synapses=(), external_events=(), ticks=1,
                 decay_num=2, decay_den=1),
        )
        for item in bad:
            with self.subTest(bad=item):
                with self.assertRaises(ValueError):
                    RunPlan(**item)
        self.assertEqual(len(valid.neurons), 2)

    def test_type_width_and_exact_bounds_checked(self):
        for params in (
            (0, 0, 0, 0), (0, 0, 5, 5), (32768, 0, 5, 0),
            (0, True, 5, 0), (0, 0, 5, -32769)
        ):
            with self.subTest(neuron=params):
                with self.assertRaises(ValueError):
                    NeuronConfig(*params)
        for params in (
            (0, 0, 32768, 1), (0, 0, 0, 0), (0, 0, 0, 9),
            (True, 0, 0, 1)
        ):
            with self.subTest(synapse=params):
                with self.assertRaises(ValueError):
                    SynapseConfig(*params)
        for params in ((0, 0, 32768), (-1, 0, 0), (0, True, 0)):
            with self.subTest(external=params):
                with self.assertRaises(ValueError):
                    ExternalEvent(*params)

    def test_script_transport_does_not_infer_hardware_timing(self):
        fake = ScriptedTransport((
            ScriptedRun(zero_rows(), output_stride=4, receive_stride=7),
        ))
        ctrl = ExecutionController(fake)
        r = ctrl.execute(plan())
        self.assertTrue(r.result.accepted)
        self.assertGreater(r.service_steps, 20)
        self.assertNotEqual(r.service_steps, len(r.result.rows))
        self.assertFalse(r.needs_recovery)

    def test_source_keeps_readiness_and_recovery_separate_from_rtl(self):
        source = (ROOT / "src/neuromorphic_accelerator_v1/"
                  "m05_execution_controller.py").read_text()
        for term in (
            "RollingTraceCommitGate(", "try_send(", "try_receive(",
            "poll_completion(", "is_quiescent(", "reset_and_verify_idle(",
            "ControllerState.FAULTED", "wall_timeout_s", "service-step",
            "transport exception",
        ):
            with self.subTest(term=term):
                self.assertIn(term, source)
        self.assertNotIn("program_hw_devices", source)


if __name__ == "__main__":
    unittest.main()
