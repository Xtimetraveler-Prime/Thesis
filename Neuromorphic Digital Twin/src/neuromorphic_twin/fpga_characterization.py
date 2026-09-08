"""M12.5 reproducible FPGA characterization helpers.

Characterization is deliberately separated from computational correctness.  The
M10/M11.5 core remains frozen; M12.5 consumes routed implementation reports and
passive per-tick cycle measurements from a validation-capable image.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
import math
from pathlib import Path
import re
from statistics import mean
from typing import Iterable

from .fpga_broad_regression import BroadRegressionCase, build_m12_broad_cases

M12_CHARACTERIZATION_SCHEMA = "neuromorphic-twin-m12-characterization-v1"
M12_CYCLE_MEASUREMENT_SCHEMA = "neuromorphic-twin-m12-cycle-measurements-v1"
M12_CHARACTERIZATION_CLOCK_HZ = 100_000_000
M12_CHARACTERIZATION_CLOCK_PERIOD_NS = 10.0


@dataclass(frozen=True, slots=True)
class RawTickCycleMeasurement:
    case_id: int
    case_name: str
    tick: int
    cycles: int
    external_events: int
    recurrent_events: int
    routed_events: int


@dataclass(frozen=True, slots=True)
class TickCharacterization:
    case_id: int
    case_name: str
    source_kind: str
    seed: str
    configuration_sha256: str
    tick: int
    cycles: int
    latency_ns: float
    neurons: int
    axons: int
    synapses: int
    routes: int
    external_events: int
    recurrent_events: int
    routed_events: int
    synapse_visits: int
    ticks_per_second: float
    neuron_updates_per_second: float
    input_events_per_second: float
    synapse_visits_per_second: float


@dataclass(frozen=True, slots=True)
class ImplementationCharacterization:
    target_part: str
    target_clock_hz: int
    target_period_ns: float
    worst_setup_slack_ns: float
    worst_hold_slack_ns: float
    clb_luts: int
    clb_luts_available: int
    clb_registers: int
    clb_registers_available: int
    bram_tiles_upper_bound: int
    bram_tiles_available: int
    ramb36: int
    ramb18: int
    dsps: int
    dsps_available: int
    uram: int
    uram_available: int


@dataclass(frozen=True, slots=True)
class CharacterizationSummary:
    implementation: ImplementationCharacterization
    ticks: tuple[TickCharacterization, ...]

    def to_dict(self) -> dict[str, object]:
        cycles = [row.cycles for row in self.ticks]
        latencies = [row.latency_ns for row in self.ticks]
        return {
            "schema": M12_CHARACTERIZATION_SCHEMA,
            "implementation": asdict(self.implementation),
            "measurement_count": len(self.ticks),
            "aggregate": {
                "min_cycles": min(cycles),
                "max_cycles": max(cycles),
                "mean_cycles": mean(cycles),
                "min_latency_ns": min(latencies),
                "max_latency_ns": max(latencies),
                "mean_latency_ns": mean(latencies),
            },
            "ticks": [asdict(row) for row in self.ticks],
        }


def read_cycle_measurements(path: str | Path) -> tuple[RawTickCycleMeasurement, ...]:
    source = Path(path)
    rows: list[RawTickCycleMeasurement] = []
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expected = (
            "case_id", "case_name", "tick", "cycles",
            "external_events", "recurrent_events", "routed_events",
        )
        if tuple(reader.fieldnames or ()) != expected:
            raise ValueError(f"unexpected M12.5 cycle TSV header: {reader.fieldnames}")
        for item in reader:
            row = RawTickCycleMeasurement(
                case_id=int(item["case_id"]),
                case_name=item["case_name"],
                tick=int(item["tick"]),
                cycles=int(item["cycles"]),
                external_events=int(item["external_events"]),
                recurrent_events=int(item["recurrent_events"]),
                routed_events=int(item["routed_events"]),
            )
            if row.cycles <= 0:
                raise ValueError("measured tick cycles must be positive")
            rows.append(row)
    return tuple(rows)


def synapse_visits_for_tick(case: BroadRegressionCase, tick: int) -> int:
    capture = case.workload.expected_ticks[tick - 1]
    events = (
        capture.snapshot.external_input_axons
        + capture.snapshot.recurrent_input_axons
    )
    rows = case.workload.storage.axon_row_pointers
    total = 0
    for axon in events:
        if axon >= case.workload.storage.axon_count:
            continue
        total += rows[axon + 1] - rows[axon]
    return total


def characterize_ticks(
    raw: Iterable[RawTickCycleMeasurement],
    *,
    clock_hz: int = M12_CHARACTERIZATION_CLOCK_HZ,
) -> tuple[TickCharacterization, ...]:
    cases = {case.case_id: case for case in build_m12_broad_cases()}
    period_ns = 1e9 / clock_hz
    result: list[TickCharacterization] = []
    seen: set[tuple[int, int]] = set()
    for row in raw:
        if row.case_id not in cases:
            raise ValueError(f"unknown M12.4/M12.5 case id: {row.case_id}")
        case = cases[row.case_id]
        if row.case_name != case.name:
            raise ValueError("cycle row case name does not match frozen corpus")
        if not 1 <= row.tick <= case.tick_count:
            raise ValueError("cycle row tick outside frozen case timeline")
        key = (row.case_id, row.tick)
        if key in seen:
            raise ValueError(f"duplicate cycle row: {key}")
        seen.add(key)

        expected = case.workload.expected_ticks[row.tick - 1]
        if row.external_events != expected.external_event_count:
            raise ValueError("measured external-event count disagrees with golden trace")
        if row.recurrent_events != expected.consumed_recurrent_count:
            raise ValueError("measured recurrent-event count disagrees with golden trace")
        if row.routed_events != expected.routed_recurrent_count:
            raise ValueError("measured routed-event count disagrees with golden trace")

        ticks_per_second = clock_hz / row.cycles
        visits = synapse_visits_for_tick(case, row.tick)
        input_events = row.external_events + row.recurrent_events
        workload = case.workload
        result.append(
            TickCharacterization(
                case_id=row.case_id,
                case_name=row.case_name,
                source_kind=case.source_kind,
                seed=f"0x{case.seed:016x}",
                configuration_sha256=case.configuration_sha256,
                tick=row.tick,
                cycles=row.cycles,
                latency_ns=row.cycles * period_ns,
                neurons=workload.neuron_count,
                axons=workload.storage.axon_count,
                synapses=workload.storage.synapse_count,
                routes=workload.routes.route_count,
                external_events=row.external_events,
                recurrent_events=row.recurrent_events,
                routed_events=row.routed_events,
                synapse_visits=visits,
                ticks_per_second=ticks_per_second,
                neuron_updates_per_second=workload.neuron_count * ticks_per_second,
                input_events_per_second=input_events * ticks_per_second,
                synapse_visits_per_second=visits * ticks_per_second,
            )
        )
    return tuple(result)


def parse_implementation_reports(
    utilization: str | Path,
    ram_utilization: str | Path,
    vivado_log: str | Path,
) -> ImplementationCharacterization:
    util = Path(utilization)
    ram = Path(ram_utilization)
    log = Path(vivado_log)
    clb_luts, clb_luts_available = _table_row(util, ("CLB LUTs",))
    clb_regs, clb_regs_available = _table_row(util, ("CLB Registers",))
    dsps, dsps_available = _table_row(util, ("DSPs",))
    uram, uram_available = _table_row(util, ("URAM",))
    ramb36 = _primitive_used(ram, ("RAMB36/FIFO", "RAMB36E2", "RAMB36"))
    ramb18 = _primitive_used(ram, ("RAMB18", "RAMB18E2"))
    bram_tiles = ramb36 + math.ceil(ramb18 / 2)

    text = log.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"M12\.5 routed timing check passed: WNS=([+-]?[0-9.]+) ns, WHS=([+-]?[0-9.]+) ns",
        text,
    )
    if not match:
        raise ValueError("could not find M12.5 routed timing pass marker")
    wns = float(match.group(1))
    whs = float(match.group(2))
    if wns < 0 or whs < 0:
        raise ValueError("negative routed timing slack cannot characterize an accepted image")

    return ImplementationCharacterization(
        target_part="xck26-sfvc784-2LV-c",
        target_clock_hz=M12_CHARACTERIZATION_CLOCK_HZ,
        target_period_ns=M12_CHARACTERIZATION_CLOCK_PERIOD_NS,
        worst_setup_slack_ns=wns,
        worst_hold_slack_ns=whs,
        clb_luts=clb_luts,
        clb_luts_available=clb_luts_available,
        clb_registers=clb_regs,
        clb_registers_available=clb_regs_available,
        bram_tiles_upper_bound=bram_tiles,
        bram_tiles_available=144,
        ramb36=ramb36,
        ramb18=ramb18,
        dsps=dsps,
        dsps_available=dsps_available,
        uram=uram,
        uram_available=uram_available,
    )


def write_characterization(
    summary: CharacterizationSummary,
    output_dir: str | Path,
) -> tuple[Path, Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "characterization.json"
    csv_path = output / "tick_characterization.csv"
    md_path = output / "CHARACTERIZATION_SUMMARY.md"
    json_path.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows = [asdict(row) for row in summary.ticks]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    impl = summary.implementation
    aggregate = summary.to_dict()["aggregate"]
    md_path.write_text(
        "# M12.5 FPGA Characterization Summary\n\n"
        f"- Target: `{impl.target_part}` at {impl.target_clock_hz / 1e6:.1f} MHz.\n"
        f"- Routed timing: WNS={impl.worst_setup_slack_ns:.3f} ns, WHS={impl.worst_hold_slack_ns:.3f} ns.\n"
        f"- CLB LUTs: {impl.clb_luts}/{impl.clb_luts_available}.\n"
        f"- CLB registers: {impl.clb_registers}/{impl.clb_registers_available}.\n"
        f"- BRAM tiles (conservative): <= {impl.bram_tiles_upper_bound}/{impl.bram_tiles_available} "
        f"(RAMB36={impl.ramb36}, RAMB18={impl.ramb18}).\n"
        f"- DSPs: {impl.dsps}/{impl.dsps_available}; URAM: {impl.uram}/{impl.uram_available}.\n"
        f"- Measured committed ticks: {len(summary.ticks)}.\n"
        f"- Tick cycles min/mean/max: {aggregate['min_cycles']}/"
        f"{aggregate['mean_cycles']:.2f}/{aggregate['max_cycles']}.\n"
        f"- Tick latency ns min/mean/max: {aggregate['min_latency_ns']:.1f}/"
        f"{aggregate['mean_latency_ns']:.1f}/{aggregate['max_latency_ns']:.1f}.\n\n"
        "Per-tick details are in `tick_characterization.csv`; machine-readable evidence is in `characterization.json`.\n",
        encoding="utf-8",
    )
    return json_path, csv_path, md_path


def _table_row(path: Path, prefixes: tuple[str, ...]) -> tuple[int, int]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        fields = [field.strip() for field in line.strip().strip("|").split("|")]
        if len(fields) < 5 or not any(fields[0].startswith(prefix) for prefix in prefixes):
            continue
        try:
            return int(fields[1].replace(",", "")), int(fields[4].replace(",", ""))
        except ValueError:
            continue
    raise ValueError(f"could not locate utilization row: {prefixes}")


def _primitive_used(path: Path, prefixes: tuple[str, ...]) -> int:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        fields = [field.strip() for field in line.strip().strip("|").split("|")]
        if len(fields) < 2 or not any(fields[0].startswith(prefix) for prefix in prefixes):
            continue
        try:
            return int(fields[1].replace(",", ""))
        except ValueError:
            continue
    raise ValueError(f"could not locate RAM utilization row: {prefixes}")
