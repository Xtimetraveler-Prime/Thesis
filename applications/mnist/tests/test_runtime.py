from __future__ import annotations

from pathlib import Path
import re

from mnist_app.runtime import (
    RuntimeRequest,
    parse_event_rows,
    validate_runtime_result,
    write_runtime_request,
)
from mnist_app.runtime_static import RuntimeStaticProfile, write_runtime_static_include


def _request() -> RuntimeRequest:
    # Preserve multiplicity explicitly on selected ticks.
    rows = [() for _ in range(16)]
    rows[0] = (3, 3, 7)
    rows[5] = (1,)
    rows[15] = (9, 2)
    return RuntimeRequest(
        profile="native-sparse",
        profile_id=1,
        mnist_test_index=42,
        label=4,
        external_schedule=tuple(rows),
        golden_prediction=4,
        golden_spike_counts=(0, 0, 0, 0, 5, 0, 0, 0, 0, 0),
    )


def test_runtime_request_tsv_roundtrip_preserves_order_and_multiplicity(tmp_path: Path) -> None:
    request = _request()
    _, tsv = write_runtime_request(request, tmp_path)
    assert parse_event_rows(tsv) == request.external_schedule
    assert request.total_events == 6


def test_runtime_result_exact_match_passes() -> None:
    request = _request()
    payload = {
        "schema": "neuromorphic-twin-mnist-runtime-result-v1",
        "profile": "native-sparse",
        "mnist_test_index": 42,
        "ticks": 16,
        "total_events": 6,
        "spike_counts": [0, 0, 0, 0, 5, 0, 0, 0, 0, 0],
        "prediction": 4,
    }
    report = validate_runtime_result(request, payload)
    assert report["passed"] is True
    assert report["mismatches"] == []


def test_runtime_result_reports_prediction_and_count_mismatch() -> None:
    request = _request()
    payload = {
        "schema": "neuromorphic-twin-mnist-runtime-result-v1",
        "profile": "native-sparse",
        "mnist_test_index": 42,
        "ticks": 16,
        "total_events": 5,
        "spike_counts": [0, 0, 0, 1, 4, 0, 0, 0, 0, 0],
        "prediction": 3,
    }
    report = validate_runtime_result(request, payload)
    assert report["passed"] is False
    assert set(report["mismatches"]) == {"total_events", "spike_counts", "prediction"}


def test_runtime_static_include_contains_two_profiles_and_no_event_schedule(tmp_path: Path) -> None:
    profiles = (
        RuntimeStaticProfile(
            profile="cropped-dense",
            profile_id=0,
            config_words=(1, 2),
            initial_state_words=(0, 0),
            format_words=(3,),
            synapse_words=(4, 5),
            weight_rows=(0, 1, 2),
            route_rows=(0, 0, 0),
            route_targets=(),
        ),
        RuntimeStaticProfile(
            profile="native-sparse",
            profile_id=1,
            config_words=(11, 12),
            initial_state_words=(0, 0),
            format_words=(13,),
            synapse_words=(14, 15, 16),
            weight_rows=(0, 1, 2, 3),
            route_rows=(0, 0, 0),
            route_targets=(),
        ),
    )
    output = write_runtime_static_include(profiles, tmp_path / "runtime.svh")
    text = output.read_text(encoding="utf-8")
    assert "M12_3_CASE_COUNT = 2" in text
    assert "M12_3_MAX_AXONS = 3" in text
    assert "M12_3_MAX_SYNAPSES = 3" in text
    # Capacity metadata is allowed, but concrete runtime event arrays are not.
    assert "M12_3_MAX_EXTERNAL_EVENTS = 4096" in text
    assert re.search(r"M12_3_EXTERNAL_(COUNTS|ROWS|EVENTS)\s*\[", text) is None
    assert "M12_3_EXPECTED" not in text


def test_runtime_bitstream_guard_distinguishes_capacity_from_event_arrays() -> None:
    script = Path(__file__).parents[1] / "fpga" / "run_mnist_09_bitstream.sh"
    text = script.read_text(encoding="utf-8")
    assert "M12_3_EXTERNAL_(COUNTS|ROWS|EVENTS)[[:space:]]*\\[" in text
    assert "M12_3_EXPECTED|EXTERNAL_EVENTS|RECURRENT_SCHEDULE" not in text


def test_runtime_controller_reserves_trace_space_seven_for_event_append() -> None:
    controller = Path(__file__).parents[1] / "fpga" / "mnist_09_runtime_controller_v1.sv"
    text = controller.read_text(encoding="utf-8")
    assert "RUNTIME_APPEND_SPACE = 3'd7" in text
    assert "normal_trace_req_pulse" in text
    assert "external_wdata = {4'b0, trace_read_addr}" in text
