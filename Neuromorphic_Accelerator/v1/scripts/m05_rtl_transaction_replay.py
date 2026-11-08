"""Replay a *real direct-XSim transcript* through the M05 host commit gate.

The direct RTL late-error test prints each provisional accepted AXIS transfer
and its actual AXI-Lite final status. This strict read-only post-check verifies
that no partial inference is published when hardware returns BAD_EXTERNAL=4.

The transcript is an *offline bridge*, NOT a live AXI/PS/DMA receiver, and it
does not assert physical board behavior. Do not use fabricated logs as RTL
evidence. The existing run script invokes this on its own NEW XSim log only.
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

PROVISIONAL = re.compile(
    r"^M05_RTL_PROVISIONAL tick=(\d+) neuron=(\d+) voltage=(-?\d+) "
    r"spike=(\d+) evaluated=(\d+) delivered=(\d+)$"
)
FINAL = re.compile(
    r"^M05_RTL_FINAL status=(\d+) provisional=(\d+) committed=(\d+)$"
)
RTL_PASS = "PASS: M05 REAL RTL AXIS LATE-ERROR"


@dataclass(frozen=True)
class TransactionReplayEvidence:
    status: int
    provisional_count: int
    accepted_count: int
    first_spike: bool
    drained_rows: int


def replay_log(log: str) -> TransactionReplayEvidence:
    """Fail closed on incomplete, contradictory, invalid or duplicate logs."""
    if "Fatal: RTL_STRESS_FAIL" in log or "ERROR: RTL_STRESS_FAIL" in log:
        raise ValueError("XSim reported an RTL_STRESS_FAIL")
    rows: list[RollingTraceRow] = []
    footer = None
    pass_count = 0
    for line in log.splitlines():
        line = line.strip()
        m = PROVISIONAL.fullmatch(line)
        if m:
            if footer is not None:
                raise ValueError("provisional data after final return status")
            rows.append(RollingTraceRow(*map(int, m.groups())))
            continue
        m = FINAL.fullmatch(line)
        if m:
            if footer is not None:
                raise ValueError("multiple final status markers")
            footer = tuple(map(int, m.groups()))
            continue
        if line.startswith(RTL_PASS):
            pass_count += 1
    if footer is None or pass_count != 1:
        raise ValueError("missing/duplicate RTL PASS or final-status marker")
    status, announced_rows, announced_committed = footer
    if status != 4:
        raise ValueError(f"expected actual RTL BAD_EXTERNAL=4, got {status}")
    if len(rows) != 8 or announced_rows != len(rows):
        raise ValueError("expected exactly 8 provisional RTL trace transfers")
    if announced_committed != 0:
        raise ValueError("RTL trace falsely declared a partial commit")
    if not rows or not (
        rows[0].tick == 0 and rows[0].neuron_id == 0
        and rows[0].spike == 1 and rows[0].evaluated == 1
        and rows[0].voltage == 0 and rows[0].delivered_count == 1
    ):
        raise ValueError("missing expected valid tick0 neuron0 spike prefix")
    if "status=4 provisional=8 committed=0" not in log:
        raise ValueError("RTL PASS line does not certify final error")
    gate = RollingTraceCommitGate(neuron_count=2, ticks=12)
    for row in rows:
        gate.offer_row(row)
    result = gate.complete(status)
    if result.accepted or result.rows or result.drained_rows != 8:
        raise ValueError("host transactional receiver exposed failed run")
    if gate.has_uncommitted_rows:
        raise ValueError("failed run left staged trace rows")
    return TransactionReplayEvidence(
        status=status, provisional_count=len(rows),
        accepted_count=len(result.rows), first_spike=True,
        drained_rows=result.drained_rows
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsim-log", required=True, type=Path)
    args = parser.parse_args()
    try:
        log = args.xsim_log.read_text(encoding="utf-8", errors="replace")
        result = replay_log(log)
    except (OSError, ValueError) as exc:
        print(f"ERROR: M05 RTL transactional replay: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        "PASS: M05 RTL transactional replay: "
        f"status={result.status}, provisional={result.provisional_count}, "
        f"drained={result.drained_rows}, committed={result.accepted_count}, "
        "early_spike=1, all failure rows discarded"
    )


if __name__ == "__main__":
    main()
