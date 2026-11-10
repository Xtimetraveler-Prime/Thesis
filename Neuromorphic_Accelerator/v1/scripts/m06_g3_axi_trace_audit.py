#!/usr/bin/env python3
"""Read-only M06 G3.2 genuine XSim AXI trace extractor; NEVER grants PASS."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

TRACE = "M06_G3_AXI_TRACE "
FIRST = "M06_G3_AXI_FIRST_DECERR "
SUMMARY = "M06_G3_AXI_PROBE_SUMMARY "
KINDS = {"AR", "R_OBS", "R_HS", "AW", "W", "B_OBS", "B_HS"}
STAGES = {"RD_SI32", "RD_MI256_SC_S00", "WR_SI32",
          "WR_MI256_SC_S03", "SC_M00_RAM128"}


def fields(text: str) -> dict[str, str]:
    result = {}
    for token in text.strip().split():
        if "=" not in token:
            raise ValueError("malformed AXI probe token")
        name, value = token.split("=", 1)
        if not name or not value or name in result:
            raise ValueError("duplicate/empty AXI probe field")
        result[name] = value
    return result


def analyze(text: str) -> tuple[list[str], dict]:
    collected, events, first, summaries = [], [], [], []
    for line in text.splitlines():
        if TRACE in line:
            row = fields(line.split(TRACE, 1)[1])
            if row.get("kind") not in KINDS or row.get("stage") not in STAGES:
                raise ValueError("unknown AXI probe kind/stage")
            if not row.get("t", "").isdigit():
                raise ValueError("missing/non-numeric timestamp")
            if row["kind"] in ("R_OBS", "R_HS", "B_OBS", "B_HS"):
                if row.get("resp") not in ("00", "01", "10", "11"):
                    raise ValueError("invalid AXI response bits")
            if row["kind"] in ("AR", "AW"):
                if not all(k in row for k in ("addr", "len", "size", "burst")):
                    raise ValueError("missing AXI address metadata")
            events.append(row)
            collected.append(line[line.index(TRACE):])
        elif FIRST in line:
            first.append(fields(line.split(FIRST, 1)[1]))
            collected.append(line[line.index(FIRST):])
        elif SUMMARY in line:
            summaries.append(fields(line.split(SUMMARY, 1)[1]))
            collected.append(line[line.index(SUMMARY):])
    if len(first) > 1:
        raise ValueError("duplicate first DECERR marker")
    if first:
        f = first[0]
        if f.get("resp") != "11" or f.get("kind") not in ("R_OBS", "B_OBS"):
            raise ValueError("invalid first DECERR marker")
        if not any(e["kind"] == f["kind"] and e["stage"] == f.get("stage") and
                   e.get("resp") == "11" for e in events):
            raise ValueError("first DECERR marker lacks response observation")
    def seen(stage: str, kind: str, resp: str | None = None) -> list[dict]:
        return [e for e in events if e["stage"] == stage and e["kind"] == kind
                and (resp is None or e.get("resp") == resp)]
    ram_ar = seen("SC_M00_RAM128", "AR")
    ram_err = seen("SC_M00_RAM128", "R_OBS", "11")
    sc_err = seen("RD_MI256_SC_S00", "R_OBS", "11")
    si_err = seen("RD_SI32", "R_OBS", "11")
    if ram_ar and any(e.get("ram_bad") == "1" for e in ram_err):
        location = "RAM_ENDPOINT_REJECTED_OBSERVED_REQUEST"
    elif ram_err:
        location = "M00_DECERR_RAM_VALIDATOR_NOT_CONFIRMED"
    elif sc_err:
        location = "DECERR_AT_S00_WITHOUT_OBSERVED_M00_DECERR"
    elif si_err:
        location = "DECERR_AT_DWC_SI_WITHOUT_OBSERVED_MI_DECERR"
    else:
        location = "NO_READ_DECERR_OBSERVED_OR_TRACE_INCOMPLETE"
    result = {
        "scope": "XSim_DIAGNOSTIC_ONLY_NOT_G3_2_PASS",
        "root_cause_proven": False,
        "location_hypothesis_from_observations": location,
        "event_count": len(events),
        "first_decerr": first[0] if first else None,
        "counter_summary": summaries[-1] if summaries else None,
        "memory_ar_observed": bool(ram_ar),
        "memory_decerr_observed": bool(ram_err),
        "by_stage_kind": {
            stage: {kind: len(seen(stage, kind)) for kind in sorted(KINDS)}
            for stage in sorted(STAGES)
        },
        "trace_truncated_or_incomplete": (
            not events or not summaries or
            any(int(s.get("printed", "0")) > 512 for s in summaries)
        ),
    }
    return collected, result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xsim-log", type=Path, required=True)
    ap.add_argument("--trace-output", type=Path, required=True)
    ap.add_argument("--summary-output", type=Path, required=True)
    args = ap.parse_args()
    try:
        if not args.xsim_log.is_file():
            raise ValueError("no genuine XSim log")
        if args.trace_output.exists() or args.summary_output.exists():
            raise ValueError("refusing overwrite of existing diagnostic evidence")
        if args.trace_output.parent != args.summary_output.parent:
            raise ValueError("trace outputs must share owner evidence folder")
        collected, result = analyze(args.xsim_log.read_text(errors="replace"))
        args.trace_output.write_text("\n".join(collected) + ("\n" if collected else ""))
        args.summary_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError) as exc:
        print("M06_G3_AXI_TRACE_AUDIT_FAIL " + str(exc), file=sys.stderr)
        return 2
    print("M06_G3_AXI_PROBE_EXTRACTED events=" + str(result["event_count"]) +
          " location=" + result["location_hypothesis_from_observations"] +
          " NOT_G3_2_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
