from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.fpga_physical_trace_reproducibility import (
    compare_physical_fpga_trace_files,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two independently captured physical FPGA traces for exact "
            "M12.1.4 reproducibility."
        )
    )
    parser.add_argument("first_trace", type=Path)
    parser.add_argument("second_trace", type=Path)
    args = parser.parse_args()

    result = compare_physical_fpga_trace_files(args.first_trace, args.second_trace)
    print(
        "M12.1.4 physical trace reproducibility passed: "
        f"scenario={result.scenario_id} device={result.device} "
        f"transport={result.transport} ticks={result.tick_count} "
        f"bytes={result.byte_count} sha256={result.sha256_hex}"
    )
    print(f"  capture_a={args.first_trace}")
    print(f"  capture_b={args.second_trace}")


if __name__ == "__main__":
    main()
