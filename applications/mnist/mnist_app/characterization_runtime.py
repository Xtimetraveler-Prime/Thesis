from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .characterization import (
    BASE_CYCLES_PER_NEURON,
    BASE_FIXED_CYCLES,
    INPUT_EVENT_CYCLES,
    OUTPUT_NEURONS,
    SYNAPSE_VISIT_CYCLES,
)
from .inference import load_deployment
from .runtime import RuntimeRequest


_SOURCE_MODULE = "module m12_3_multitick_capture_controller_v1 ("
_TARGET_MODULE = "module m12_5_characterization_capture_controller_v1 ("
_PORT_ANCHOR = "    output logic [12:0]  observed_external_event_count,\n"
_PORT_INSERT = (
    "    output logic [12:0]  observed_external_event_count,\n"
    "    output logic [31:0]  observed_last_tick_cycles,\n"
)
_COUNT_ANCHOR = "    logic [23:0] watchdog;\n"
_COUNT_INSERT = (
    "    logic [23:0] watchdog;\n"
    "    // Passive MNIST-10 architectural timing witness. This counter is not\n"
    "    // connected to the computational datapath and follows the M12.5 timing\n"
    "    // boundary: accepted tick_start through observed outer-core tick_done.\n"
    "    logic [31:0] tick_cycle_counter;\n"
    "    logic        tick_cycle_active;\n"
)
_ASSIGN_ANCHOR = "    assign observed_external_event_count = trace_external_event_count;\n"
_ASSIGN_INSERT = """    assign observed_external_event_count = trace_external_event_count;

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            tick_cycle_counter        <= 32'd0;
            tick_cycle_active         <= 1'b0;
            observed_last_tick_cycles <= 32'd0;
        end else if (tick_start) begin
            tick_cycle_counter <= 32'd0;
            tick_cycle_active  <= 1'b1;
        end else if (tick_cycle_active) begin
            if (tick_done) begin
                observed_last_tick_cycles <= tick_cycle_counter + 32'd1;
                tick_cycle_active         <= 1'b0;
            end else begin
                tick_cycle_counter <= tick_cycle_counter + 32'd1;
            end
        end
    end
"""


def patch_runtime_controller_for_timing(text: str) -> str:
    """Adapt accepted MNIST-09 runtime shell to the proven M12.5 timing VIO shape."""

    if text.count(_SOURCE_MODULE) != 1:
        raise ValueError("unexpected MNIST-09 runtime module declaration")
    if text.count(_PORT_ANCHOR) != 1:
        raise ValueError("unexpected MNIST-09 observed-event port anchor")
    if text.count(_COUNT_ANCHOR) != 1:
        raise ValueError("unexpected MNIST-09 watchdog anchor")
    if text.count(_ASSIGN_ANCHOR) != 1:
        raise ValueError("unexpected MNIST-09 observed-event assignment anchor")

    patched = text.replace(_SOURCE_MODULE, _TARGET_MODULE, 1)
    patched = patched.replace(_PORT_ANCHOR, _PORT_INSERT, 1)
    patched = patched.replace(_COUNT_ANCHOR, _COUNT_INSERT, 1)
    patched = patched.replace(_ASSIGN_ANCHOR, _ASSIGN_INSERT, 1)

    if "observed_last_tick_cycles <= tick_cycle_counter + 32'd1" not in patched:
        raise AssertionError("MNIST-10 cycle counter was not inserted")
    if "module m12_3_multitick_capture_controller_v1" in patched:
        raise AssertionError("MNIST-09 module name survived characterization patch")
    return patched


def write_timing_runtime_controller(source: str | Path, output: str | Path) -> Path:
    source_path = Path(source)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        patch_runtime_controller_for_timing(source_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return target


def expected_tick_synapse_visits(
    request: RuntimeRequest,
    frozen_root: str | Path,
) -> tuple[int, ...]:
    """Exact CSR visits implied by one feed-forward runtime event schedule."""

    deployment = (
        Path(frozen_root)
        / "deployments"
        / request.profile
        / "deployment.json"
    )
    runtime = load_deployment(deployment)
    row_lengths: Sequence[int] = runtime.row_lengths
    visits: list[int] = []
    for events in request.external_schedule:
        visits.append(sum(int(row_lengths[axon]) for axon in events))
    return tuple(visits)


def expected_tick_cycles(
    request: RuntimeRequest,
    frozen_root: str | Path,
) -> tuple[int, ...]:
    """Expected physical cycle counts from the M12.5 no-route decomposition."""

    visits = expected_tick_synapse_visits(request, frozen_root)
    base = BASE_CYCLES_PER_NEURON * OUTPUT_NEURONS + BASE_FIXED_CYCLES
    return tuple(
        base
        + INPUT_EVENT_CYCLES * len(events)
        + SYNAPSE_VISIT_CYCLES * tick_visits
        for events, tick_visits in zip(request.external_schedule, visits, strict=True)
    )


def validate_timing_result(
    request: RuntimeRequest,
    frozen_root: str | Path,
    payload: dict[str, object],
) -> dict[str, object]:
    from .runtime import validate_runtime_result

    functional = validate_runtime_result(request, payload)
    measured = tuple(int(value) for value in payload.get("tick_cycles", []))
    expected = expected_tick_cycles(request, frozen_root)
    mismatches = list(functional["mismatches"])
    if measured != expected:
        mismatches.append("tick_cycles")

    return {
        **functional,
        "passed": not mismatches,
        "mismatches": mismatches,
        "expected_tick_cycles": list(expected),
        "physical_tick_cycles": list(measured),
        "expected_total_cycles": sum(expected),
        "physical_total_cycles": sum(measured),
        "clock_hz": 100_000_000,
        "expected_latency_ms": sum(expected) / 100_000.0,
        "physical_latency_ms": sum(measured) / 100_000.0,
        "timing_boundary": "PL tick_start acceptance through outer-core tick_done; excludes host/JTAG/VIO",
    }
