from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.fpga_characterization import (
    CharacterizationSummary,
    characterize_ticks,
    parse_implementation_reports,
    read_cycle_measurements,
    write_characterization,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble M12.5 timing/resource/cycle characterization evidence."
    )
    parser.add_argument("--cycles", type=Path, required=True)
    parser.add_argument("--utilization", type=Path, required=True)
    parser.add_argument("--ram-utilization", type=Path, required=True)
    parser.add_argument("--vivado-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    raw = read_cycle_measurements(args.cycles)
    ticks = characterize_ticks(raw)
    implementation = parse_implementation_reports(
        args.utilization,
        args.ram_utilization,
        args.vivado_log,
    )
    summary = CharacterizationSummary(implementation=implementation, ticks=ticks)
    json_path, csv_path, md_path = write_characterization(summary, args.output_dir)

    aggregate = summary.to_dict()["aggregate"]
    print(
        "M12.5 characterization assembled: "
        f"ticks={len(ticks)} cycles_min={aggregate['min_cycles']} "
        f"cycles_mean={aggregate['mean_cycles']:.2f} cycles_max={aggregate['max_cycles']} "
        f"WNS={implementation.worst_setup_slack_ns:.3f}ns "
        f"WHS={implementation.worst_hold_slack_ns:.3f}ns"
    )
    print(f"M12.5 characterization JSON: {json_path}")
    print(f"M12.5 characterization CSV: {csv_path}")
    print(f"M12.5 characterization Markdown: {md_path}")


if __name__ == "__main__":
    main()
