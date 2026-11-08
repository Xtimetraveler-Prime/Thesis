"""M05.11b HOST-ONLY MMIO register client tests.

Fake WordRegisterIO is NOT real Zynq MMIO, Vivado AXI VIP or AXI DMA.
A separate real standalone bus RTL testbench exercises AW/W/B/AR/R.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_11_mmio import (
    CMD, STATE, SESSION_LO, SESSION_HI, TRACE_ROWS_EXPECTED,
    NEURON_BEATS, SYNAPSE_BEATS, EXTERNAL_BEATS, FINAL_STATUS,
    TRACE_ROWS_OBSERVED, NEURON_BEATS_OBSERVED,
    SYNAPSE_BEATS_OBSERVED, EXTERNAL_BEATS_OBSERVED, FLAGS, VERSION,
    MAGIC_VERSION, IDLE, RUNNING, FINALIZING, COMPLETE, FAULT,
    START, FINISH, ACK, M0511BridgeRegisters, SessionProtocolError
)
from neuromorphic_accelerator_v1.m05_execution_controller import (
    RunPlan, NeuronConfig, ExternalEvent
)
from neuromorphic_accelerator_v1.m05_trace_commit import RollingTraceRow
from neuromorphic_accelerator_v1.m05_dma_frame import (
    DMAFrameResult, build_fake_dma_packet_for_test, accept_dma_frame
)


def plan() -> RunPlan:
    return RunPlan(
        neurons=(NeuronConfig(0, 0, 5, 0), NeuronConfig(0, 0, 5, 0)),
        synapses=(),
        external_events=(ExternalEvent(0, 0, 5),), ticks=2,
    )


def accepted_frame(session=99) -> DMAFrameResult:
    trace = tuple(RollingTraceRow(t, n, 0, int(t == 0 and n == 0),
                                  int(t == 0 and n == 0), int(t == 0))
                  for t in range(2) for n in range(2))
    data = build_fake_dma_packet_for_test(trace, status=0,
                                          session_id=session)
    return accept_dma_frame(
        data, session_id=session, neuron_count=2, ticks=2, hls_status=0,
        transferred_bytes=len(data), dma_completed=True,
        tlast_certified=True, transport_quiescent=True
    )


class FakeMMIO:
    """Only a synchronous software unit-test double for register ownership."""
    def __init__(self):
        self.reg = {VERSION: MAGIC_VERSION, STATE: IDLE}
        self.writes = []
        self.corrupt_read = None
        self.writes_enabled = True

    def read32(self, addr):
        if self.corrupt_read == addr:
            return 999
        return self.reg.get(addr, 0)

    def write32(self, addr, value):
        self.writes.append((addr, value))
        if not self.writes_enabled:
            return
        if addr == CMD:
            if value == START and self.reg[STATE] == IDLE:
                self.reg[STATE] = RUNNING
            elif value == FINISH and self.reg[STATE] == RUNNING:
                self.reg[STATE] = FINALIZING
            elif value == ACK and self.reg[STATE] == COMPLETE:
                self.reg[STATE] = IDLE
        else:
            self.reg[addr] = value

    def complete(self):
        self.reg.update({
            STATE: COMPLETE,
            TRACE_ROWS_OBSERVED: 4,
            NEURON_BEATS_OBSERVED: 2,
            SYNAPSE_BEATS_OBSERVED: 0,
            EXTERNAL_BEATS_OBSERVED: 1,
            FLAGS: 0b10101
        })


class M0511MMIOTests(unittest.TestCase):
    def test_register_map_matches_defined_rtl_documented_offsets(self):
        self.assertEqual(
            (CMD, STATE, SESSION_LO, SESSION_HI, TRACE_ROWS_EXPECTED,
             NEURON_BEATS, SYNAPSE_BEATS, EXTERNAL_BEATS, FINAL_STATUS),
            (0, 4, 8, 12, 16, 20, 24, 28, 32))
        self.assertEqual((TRACE_ROWS_OBSERVED, NEURON_BEATS_OBSERVED,
                          SYNAPSE_BEATS_OBSERVED, EXTERNAL_BEATS_OBSERVED,
                          FLAGS, VERSION),
                         (36, 40, 44, 48, 52, 56))
        self.assertEqual(MAGIC_VERSION, 0x0005110B)

    def test_successful_program_start_finish_requires_verified_frame_before_ack(self):
        io = FakeMMIO()
        driver = M0511BridgeRegisters(io)
        driver.configure(plan(), session_id=99)
        self.assertEqual(io.reg[SESSION_LO], 99)
        self.assertEqual(io.reg[TRACE_ROWS_EXPECTED], 4)
        driver.start()
        self.assertEqual(driver.state(), RUNNING)
        driver.request_finish(hls_done_latched=True, actual_hls_status=0)
        self.assertEqual(io.reg[FINAL_STATUS], 0)
        self.assertEqual(driver.state(), FINALIZING)
        with self.assertRaisesRegex(SessionProtocolError, "fully complete"):
            driver.acknowledge_success(accepted_frame())
        io.complete()
        driver.acknowledge_success(accepted_frame())
        self.assertEqual(driver.state(), IDLE)
        self.assertEqual([value for addr, value in io.writes if addr == CMD],
                         [START, FINISH, ACK])

    def test_high_session_id_is_split_low_high_correctly(self):
        io = FakeMMIO()
        drv = M0511BridgeRegisters(io)
        drv.configure(plan(), 0x123456789ABCDEF0)
        self.assertEqual(io.reg[SESSION_LO], 0x9ABCDEF0)
        self.assertEqual(io.reg[SESSION_HI], 0x12345678)

    def test_start_cannot_be_issued_twice_or_before_valid_config(self):
        io = FakeMMIO()
        drv = M0511BridgeRegisters(io)
        with self.assertRaisesRegex(SessionProtocolError, "no valid"):
            drv.start()
        drv.configure(plan(), 9)
        drv.start()
        with self.assertRaisesRegex(SessionProtocolError, "repeated start"):
            drv.start()
        self.assertEqual(len([x for x in io.writes if x == (CMD, START)]), 1)

    def test_finish_requires_real_hls_done_and_valid_status(self):
        io = FakeMMIO()
        drv = M0511BridgeRegisters(io)
        drv.configure(plan(), 9)
        drv.start()
        with self.assertRaisesRegex(SessionProtocolError, "ap_done"):
            drv.request_finish(hls_done_latched=False, actual_hls_status=0)
        for bad in (7, -1, True, "0"):
            with self.subTest(status=bad):
                with self.assertRaises(SessionProtocolError):
                    drv.request_finish(hls_done_latched=True,
                                       actual_hls_status=bad)
        drv.request_finish(hls_done_latched=True, actual_hls_status=4)
        self.assertEqual(io.reg[FINAL_STATUS], 4)
        self.assertEqual(drv.state(), FINALIZING)
        with self.assertRaisesRegex(SessionProtocolError, "no running"):
            drv.request_finish(hls_done_latched=True, actual_hls_status=4)

    def test_hardware_version_mismatch_is_fail_closed(self):
        io = FakeMMIO()
        io.reg[VERSION] = 0
        drv = M0511BridgeRegisters(io)
        with self.assertRaisesRegex(SessionProtocolError, "version"):
            drv.configure(plan(), 9)
        self.assertEqual(io.writes, [])

    def test_nonidle_bridge_refuses_configuration(self):
        io = FakeMMIO()
        io.reg[STATE] = FAULT
        with self.assertRaisesRegex(SessionProtocolError, "not idle"):
            M0511BridgeRegisters(io).configure(plan(), 9)
        self.assertEqual(io.writes, [])

    def test_config_mismatch_is_fail_closed_and_not_started(self):
        io = FakeMMIO()
        io.writes_enabled = False
        d = M0511BridgeRegisters(io)
        with self.assertRaisesRegex(SessionProtocolError, "readback mismatch"):
            d.configure(plan(), 9)
        self.assertNotIn((CMD, START), io.writes)

    def test_bad_dma_session_cannot_ack_even_if_hw_says_complete(self):
        io = FakeMMIO()
        d = M0511BridgeRegisters(io)
        d.configure(plan(), 99)
        d.start()
        d.request_finish(hls_done_latched=True, actual_hls_status=0)
        io.complete()
        with self.assertRaisesRegex(SessionProtocolError, "does not certify"):
            d.acknowledge_success(accepted_frame(100))
        self.assertEqual(d.state(), COMPLETE)

    def test_input_count_mismatch_blocks_ack(self):
        io = FakeMMIO()
        d = M0511BridgeRegisters(io)
        d.configure(plan(), 99)
        d.start()
        d.request_finish(hls_done_latched=True, actual_hls_status=0)
        io.complete()
        io.reg[EXTERNAL_BEATS_OBSERVED] = 0
        with self.assertRaisesRegex(SessionProtocolError, "ingress"):
            d.acknowledge_success(accepted_frame())
        self.assertEqual(d.state(), COMPLETE)

    def test_bridge_fault_blocks_ack(self):
        io = FakeMMIO()
        d = M0511BridgeRegisters(io)
        d.configure(plan(), 99)
        d.start()
        d.request_finish(hls_done_latched=True, actual_hls_status=0)
        io.complete()
        io.reg[FLAGS] = 0b10111
        with self.assertRaisesRegex(SessionProtocolError, "fault"):
            d.acknowledge_success(accepted_frame())

    def test_fault_cannot_be_cleared_by_merely_resetting_host_ownership(self):
        io = FakeMMIO()
        d = M0511BridgeRegisters(io)
        d.configure(plan(), 99)
        d.start()
        io.reg[STATE] = FAULT
        self.assertTrue(d.fault_requires_external_reset())
        with self.assertRaisesRegex(SessionProtocolError, "not verified"):
            d.notify_externally_verified_reset()
        self.assertNotIn((CMD, ACK), io.writes)
        # This is only a fake. Actual external supervisor MUST reset and flush
        # PS/DMA/PL before state changes to idle.
        io.reg[STATE] = IDLE
        d.notify_externally_verified_reset()
        d.configure(plan(), 100)

    def test_bad_mmio_read_types_are_rejected(self):
        io = FakeMMIO()
        io.reg[VERSION] = True
        with self.assertRaises(SessionProtocolError):
            M0511BridgeRegisters(io).configure(plan(), 2)

    def test_session_id_rejects_out_of_range_and_bool(self):
        d = M0511BridgeRegisters(FakeMMIO())
        for invalid in (-1, 1 << 64, True, "99"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    d.configure(plan(), invalid)


if __name__ == "__main__":
    unittest.main()
