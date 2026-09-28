from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from neuromorphic_twin.fpga_multitick_conformance import (
    build_m12_multitick_cases,
    compare_m12_multitick_capture,
)
from neuromorphic_twin.fpga_physical_trace import read_physical_fpga_trace_json


REPLAY_CASE_ID = 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify deterministic M12.3 reset/replay for the recurrent-loop anchor."
    )
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    args = parser.parse_args()

    case = build_m12_multitick_cases()[REPLAY_CASE_ID]
    first = read_physical_fpga_trace_json(args.first)
    replay = read_physical_fpga_trace_json(args.replay)

    first_report = compare_m12_multitick_capture(case, first)
    replay_report = compare_m12_multitick_capture(case, replay)
    if not first_report.passed or not replay_report.passed:
        print(
            "M12.3 reset/replay FAILED golden differential: "
            f"first_mismatches={len(first_report.mismatches)} "
            f"replay_mismatches={len(replay_report.mismatches)}"
        )
        return 1

    if first.ticks != replay.ticks:
        print("M12.3 reset/replay FAILED: typed physical tick sequences differ")
        return 1
    if first.to_tick_traces() != replay.to_tick_traces():
        print("M12.3 reset/replay FAILED: reconstructed TickTrace sequences differ")
        return 1

    first_bytes = args.first.read_bytes()
    replay_bytes = args.replay.read_bytes()
    if first_bytes != replay_bytes:
        print(
            "M12.3 reset/replay note: semantic traces match but serialized artifacts "
            "are not byte-identical (typically device/session metadata)."
        )
    first_sha = hashlib.sha256(first_bytes).hexdigest()
    replay_sha = hashlib.sha256(replay_bytes).hexdigest()
    print(
        "M12.3 reset/replay passed: "
        f"case={REPLAY_CASE_ID:02d} name={case.name} ticks={case.tick_count} "
        f"semantic_exact=1 first_sha256={first_sha} replay_sha256={replay_sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
