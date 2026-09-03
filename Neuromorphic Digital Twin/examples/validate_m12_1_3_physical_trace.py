from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.fpga_physical_trace import (
    FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO,
    read_physical_fpga_trace_json,
)


EXPECTED_SCENARIO_ID = "m11_5_4_recurrent_chain_physical_trace_v1"
EXPECTED_COMMITTED_TICKS = (1, 2, 3, 4)


def validate_capture(path: str | Path) -> None:
    artifact = read_physical_fpga_trace_json(path)
    if artifact.scenario_id != EXPECTED_SCENARIO_ID:
        raise ValueError(
            f"unexpected M12.1.3 scenario_id: {artifact.scenario_id!r}"
        )
    if artifact.transport != FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO:
        raise ValueError(f"unexpected M12.1.3 transport: {artifact.transport!r}")

    committed_ticks = tuple(tick.snapshot.committed_tick for tick in artifact.ticks)
    if committed_ticks != EXPECTED_COMMITTED_TICKS:
        raise ValueError(
            "M12.1.3 capture must contain exactly committed ticks "
            f"{EXPECTED_COMMITTED_TICKS}; got {committed_ticks}"
        )
    if any(tick.core_fault or tick.core_fault_code != 0 for tick in artifact.ticks):
        raise ValueError("M12.1.3 physical capture contains a core fault")

    # Exercise the lossless handoff into the existing M10/M12 comparison type.
    traces = artifact.to_tick_traces()
    if tuple(trace.tick for trace in traces) != (0, 1, 2, 3):
        raise ValueError("M12.1.3 committed-tick to TickTrace translation is invalid")

    print(
        "M12.1.3 physical trace artifact validated: "
        f"device={artifact.device} ticks={len(artifact.ticks)}"
    )
    for capture, trace in zip(artifact.ticks, traces, strict=True):
        print(
            f"  committed_tick={capture.snapshot.committed_tick} "
            f"trace_tick={trace.tick} neurons={capture.snapshot.neuron_count} "
            f"external={capture.external_event_count} "
            f"consumed_recurrent={capture.consumed_recurrent_count} "
            f"routed_recurrent={capture.routed_recurrent_count}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and replay an M12.1.3 physical FPGA trace artifact."
    )
    parser.add_argument("trace_json", type=Path)
    args = parser.parse_args()
    validate_capture(args.trace_json)


if __name__ == "__main__":
    main()
