from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1" / "recurrent_route_queue_v1.sv"
TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_recurrent_route_queue_v1.sv"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_4_sim.sh"


def test_m11_5_4_rtl_has_csr_and_two_recurrent_banks() -> None:
    text = RTL.read_text(encoding="utf-8")
    assert "module recurrent_route_queue_v1" in text
    assert 'logic [31:0] route_row_mem' in text
    assert 'logic [15:0] route_target_mem' in text
    assert 'logic [15:0] recurrent_bank0' in text
    assert 'logic [15:0] recurrent_bank1' in text
    assert 'logic spike_mem' in text
    assert "expected_row_start" in text


def test_m11_5_4_bank_swap_occurs_only_at_commit() -> None:
    text = RTL.read_text(encoding="utf-8")
    assert "S_COMMIT" in text
    assert "current_bank      <= ~current_bank;" in text
    # Logical inactive-bank clear prevents stale physical words from replaying.
    assert "bank0_count <= 13'd0" in text
    assert "bank1_count <= 13'd0" in text
    assert "last_consumed_count" in text
    assert "last_routed_count" in text


def test_m11_5_4_rtl_has_required_route_faults() -> None:
    text = RTL.read_text(encoding="utf-8")
    assert "FAULT_INVALID_COUNT" in text
    assert "FAULT_ROW_POINTER" in text
    assert "FAULT_ROUTE_TARGET" in text
    assert "FAULT_QUEUE_OVERFLOW" in text
    assert "row_start != expected_row_start" in text
    assert "row_stop != latched_route_count" in text


def test_m11_5_4_testbench_checks_next_tick_and_stale_bank_behavior() -> None:
    text = TB.read_text(encoding="utf-8")
    assert "expected[0] = 6" in text
    assert "expected[1] = 8" in text
    assert "expected[2] = 7" in text
    assert "expected[3] = 9" in text
    assert "expected[4] = 6" in text
    assert "last_consumed_count !== 13'd5" in text
    assert "stale recurrent events replayed" in text
    assert "M11.5.4 recurrent-route RTL tests passed:" in text


def test_m11_5_4_runner_is_vivado_2025_2_and_checks_pass_marker() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="2025.2"' in text
    assert 'STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_4"' in text
    assert "recurrent_route_queue_v1.sv" in text
    assert "tb_recurrent_route_queue_v1.sv" in text
    assert 'grep -Fq "$PASS_MARKER" simulate.log' in text
