from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "rtl" / "core_v1" / "recurrent_route_queue_v1.sv"
TB = ROOT / "rtl" / "core_v1" / "tb" / "tb_m12_2_recurrent_debug_bank_latch.sv"


def test_recurrent_debug_bank_is_latched_for_synchronous_response() -> None:
    route = ROUTE.read_text(encoding="utf-8")

    assert "logic        debug_bank_latched;" in route
    assert (
        "assign debug_rdata = debug_bank_latched ? bank1_mem_rdata : bank0_mem_rdata;"
        in route
    )
    assert "debug_bank_latched <= debug_bank;" in route
    assert "Callers are not required to keep debug_bank stable after debug_re falls" in route
    assert "assign debug_rdata = debug_bank ? bank1_mem_rdata : bank0_mem_rdata;" not in route


def test_behavioral_regression_releases_live_bank_selector_before_response() -> None:
    tb = TB.read_text(encoding="utf-8")

    assert "debug_bank=1; debug_addr=0; debug_re=1;" in tb
    assert "debug_re=0; debug_bank=0;" in tb
    assert "debug_rdata !== 16'd1" in tb
    assert "bank1 payload survives selector release" in tb
