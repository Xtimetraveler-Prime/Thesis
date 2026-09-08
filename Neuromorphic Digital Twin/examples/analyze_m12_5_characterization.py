from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from neuromorphic_twin.fpga_characterization import (
    CharacterizationSummary,
    TickCharacterization,
    characterize_ticks,
    parse_implementation_reports,
    read_cycle_measurements,
    write_characterization,
)


def write_case_scaling(ticks: tuple[TickCharacterization, ...], output_dir: Path) -> Path:
    grouped: dict[tuple[int, str], list[TickCharacterization]] = defaultdict(list)
    for row in ticks:
        grouped[(row.case_id, row.case_name)].append(row)

    path = output_dir / "case_scaling.csv"
    fieldnames = [
        "case_id",
        "case_name",
        "source_kind",
        "seed",
        "configuration_sha256",
        "ticks",
        "neurons",
        "axons",
        "configured_synapses",
        "routes",
        "total_input_events",
        "total_synapse_visits",
        "total_routed_events",
        "min_cycles",
        "mean_cycles",
        "max_cycles",
        "mean_tick_latency_ns",
        "mean_ticks_per_second",
        "mean_neuron_updates_per_second",
        "mean_input_events_per_second",
        "mean_synapse_visits_per_second",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key in sorted(grouped):
            rows = grouped[key]
            first = rows[0]
            cycles = [row.cycles for row in rows]
            writer.writerow(
                {
                    "case_id": first.case_id,
                    "case_name": first.case_name,
                    "source_kind": first.source_kind,
                    "seed": first.seed,
                    "configuration_sha256": first.configuration_sha256,
                    "ticks": len(rows),
                    "neurons": first.neurons,
                    "axons": first.axons,
                    "configured_synapses": first.synapses,
                    "routes": first.routes,
                    "total_input_events": sum(
                        row.external_events + row.recurrent_events for row in rows
                    ),
                    "total_synapse_visits": sum(row.synapse_visits for row in rows),
                    "total_routed_events": sum(row.routed_events for row in rows),
                    "min_cycles": min(cycles),
                    "mean_cycles": f"{mean(cycles):.6f}",
                    "max_cycles": max(cycles),
                    "mean_tick_latency_ns": f"{mean(row.latency_ns for row in rows):.6f}",
                    "mean_ticks_per_second": f"{mean(row.ticks_per_second for row in rows):.6f}",
                    "mean_neuron_updates_per_second": f"{mean(row.neuron_updates_per_second for row in rows):.6f}",
                    "mean_input_events_per_second": f"{mean(row.input_events_per_second for row in rows):.6f}",
                    "mean_synapse_visits_per_second": f"{mean(row.synapse_visits_per_second for row in rows):.6f}",
                }
            )
    return path


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
    scaling_path = write_case_scaling(ticks, args.output_dir)

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
    print(f"M12.5 characterization scaling CSV: {scaling_path}")
    print(f"M12.5 characterization Markdown: {md_path}")


if __name__ == "__main__":
    main()
