"""Read-only transactional verification of *actual* generated-RTL XSim logs.

Checks two ap_start sessions on ONE Verilog DUT instance, with no hardware
reset between them: run0 late BAD_EXTERNAL=4 discards 8 provisional rows,
run1 OK=0 commits its exact 20-row trace and has no stale t8 recurrence.

Native Python tests feed SYNTHETIC transcripts, which do NOT establish XSim
proof. The Vivado-only runner invokes this file on its NEW real XSim log.
This is not a live PS/PL AXI driver or physical DMA integration.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_trace_commit import (
    RollingTraceCommitGate, RollingTraceRow,
)

ROW = re.compile(
    r"^M05_RTL_MULTI_ROW run=(\d+) tick=(\d+) neuron=(\d+) "
    r"voltage=(-?\d+) spike=(\d+) evaluated=(\d+) delivered=(\d+)$"
)
FINAL = re.compile(
    r"^M05_RTL_MULTI_FINAL run=(\d+) status=(\d+) "
    r"rows=(\d+) committed=(\d+)$"
)
PASS = re.compile(
    r"^PASS: M05 REAL RTL AXIS MULTI-RUN fail-then-success "
    r"rows=8\+20 committed=0\+20; output_stalls=(\d+)$"
)


@dataclass(frozen=True)
class MultiRunReplayResult:
    aborted_rows: int
    accepted_rows: int
    final_statuses: tuple[int, int]
    stalls: int


def parse_and_replay(log: str) -> MultiRunReplayResult:
    """Keep run boundaries and completion ordering strict and fail closed."""
    if "Fatal: RTL_STRESS_FAIL" in log or "ERROR: RTL_STRESS_FAIL" in log:
        raise ValueError("RTL simulator emitted a fatal")
    gates = (RollingTraceCommitGate(2, 12), RollingTraceCommitGate(2, 10))
    phase = 0
    counts = [0, 0]
    results = []
    stalled = None

    for line in log.splitlines():
        line = line.strip()
        match = ROW.fullmatch(line)
        if match:
            epoch, tick, neuron, voltage, spike, evaluated, delivered = (
                int(v) for v in match.groups()
            )
            if phase > 1 or epoch != phase:
                raise ValueError("trace row appeared across an uncommitted run boundary")
            index = counts[epoch]
            expected_rows = 8 if epoch == 0 else 20
            if index >= expected_rows:
                raise ValueError("more rows than expected for this run")
            expected_tick, expected_neuron = divmod(index, 2)
            expected_spike = int(
                (epoch == 0 and expected_tick == 0 and expected_neuron == 0)
                or (epoch == 1 and expected_tick == 1 and expected_neuron == 1)
            )
            expected_delivered = int(
                (epoch == 0 and expected_tick == 0)
                or (epoch == 1 and expected_tick == 1)
            )
            if (tick, neuron, voltage, spike, evaluated, delivered) != (
                expected_tick, expected_neuron, 0, expected_spike,
                expected_spike, expected_delivered
            ):
                raise ValueError(f"run {epoch} RTL trace differs from exact oracle at row {index}")
            gates[epoch].offer_row(
                RollingTraceRow(tick, neuron, voltage, spike, evaluated, delivered)
            )
            counts[epoch] += 1
            continue

        match = FINAL.fullmatch(line)
        if match:
            epoch, status, rows, committed = (int(v) for v in match.groups())
            if phase > 1 or epoch != phase:
                raise ValueError("out-of-order or duplicate completion")
            expected_rows, expected_status = ((8, 4), (20, 0))[epoch]
            expected_committed = 0 if epoch == 0 else 20
            if (status, rows, committed, counts[epoch]) != (
                expected_status, expected_rows, expected_committed, expected_rows
            ):
                raise ValueError("hardware returned incorrect rows/status/commit summary")
            result = gates[epoch].complete(status)
            if result.drained_rows != expected_rows:
                raise ValueError("host receiver missed input beats")
            if epoch == 0:
                if result.accepted or result.rows or gates[epoch].has_uncommitted_rows:
                    raise ValueError("host exposed aborted provisional rows")
            else:
                if not result.accepted or len(result.rows) != 20:
                    raise ValueError("host failed to accept full successful second run")
                if result.rows[3].spike != 1 or result.rows[17].evaluated != 0:
                    raise ValueError("run1 recovery spike/stale t8 wheel mismatch")
            results.append(result)
            phase += 1
            continue

        match = PASS.fullmatch(line)
        if match:
            if phase != 2 or stalled is not None:
                raise ValueError("PASS before both completion statuses or duplicate PASS")
            stalled = int(match.group(1))
            if stalled < 20:
                raise ValueError("no meaningful output backpressure across both runs")
            continue

        if line.startswith("M05_RTL_MULTI_") or line.startswith(
            "PASS: M05 REAL RTL AXIS MULTI-RUN"
        ):
            raise ValueError("unrecognized malformed M05.9 RTL marker")

    if phase != 2 or stalled is None or counts != [8, 20] or len(results) != 2:
        raise ValueError("missing final completion, trace rows or simulator PASS marker")
    return MultiRunReplayResult(
        aborted_rows=results[0].drained_rows,
        accepted_rows=len(results[1].rows),
        final_statuses=(results[0].status, results[1].status),
        stalls=stalled,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsim-log", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = parse_and_replay(
            args.xsim_log.read_text(encoding="utf-8", errors="replace")
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: M05 multi-run RTL trace replay: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        "PASS: M05 RTL multi-run transactional replay: "
        f"failed_run_discarded={result.aborted_rows}, "
        f"next_run_accepted={result.accepted_rows}, statuses=4,0, "
        f"output_stalls={result.stalls}, wheel_t8_clean=1"
    )


if __name__ == "__main__":
    main()
