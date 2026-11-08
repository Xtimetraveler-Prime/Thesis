"""Audit local Vitis HLS evidence without importing or committing raw tool logs.

Examples:
  python3 scripts/m05_hls_evidence_audit.py --markdown --evidence "$ROLL_SYNTH" "$ROLL_COSIM"
  python3 scripts/m05_hls_evidence_audit.py --json --evidence /path/one /path/two

Reads operator-local ~/Thesis_Evidence paths; NEVER deletes or edits them.
Reports are intentionally NOT normalized into performance benchmarks when
testbench source hashes differ. Vitis HLS timing estimates are NOT routed timing.
Only the original real Vitis report can establish an actual HLS/RTL result.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


TOP_CSYNTH = "work/hls/syn/report/m05_rolling_replay_csynth.rpt"
TOP_COSIM = "work/hls/sim/report/m05_rolling_replay_cosim.rpt"
HLS_SOURCE = "hls/m05_rolling/m05_rolling.cpp"
HLS_BENCH = "hls/m05_rolling/m05_rolling_csim_tb.cpp"


@dataclass(frozen=True)
class EvidenceSummary:
    evidence_path: str
    evidence_id: str
    source_commit: str | None
    source_sha256: str | None
    testbench_sha256: str | None
    requested_clock_ns: float | None
    estimated_clock_ns: float | None
    bram18k: int | None
    lut: int | None
    ff: int | None
    dsp: int | None
    uram: int | None
    current_bram18k: int | None
    current_word_bits: int | None
    cosim_verilog_pass: bool | None
    cosim_latency_cycles: tuple[int, int, int] | None
    cosim_interval_cycles: tuple[int, int, int] | None
    cosim_total_cycles: int | None
    exit_status: int
    hls_top: str | None
    device: str | None
    is_real_vitis_2025_2_report: bool


def _safe_read(directory: Path, filename: str) -> str | None:
    path = directory / filename
    try:
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
    except OSError as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc


def _sha256(directory: Path, filename: str) -> str | None:
    path = directory / filename
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    except OSError as exc:
        raise ValueError(f"Cannot hash {path}: {exc}") from exc


def _parse_hashes(contents: str | None) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if contents:
        for line in contents.splitlines():
            # GNU sha256sum: 64 hex chars, 2 spaces, optional '*' for binary.
            match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line)
            if match:
                hashes[match.group(2).strip().replace("\\", "/")] = match.group(1).lower()
    return hashes


def _hash_for_path(hashes: dict[str, str], suffix: str) -> str | None:
    matches = [value for path, value in hashes.items()
               if path == suffix or path.endswith("/" + suffix)]
    return matches[0] if len(set(matches)) == 1 and matches else None


def _cells(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        return []
    return [x.strip() for x in line.strip().strip("|").split("|")]


def _synth_report(summary: dict[str, object], report: str) -> None:
    if "Vitis HLS Report for 'm05_rolling_replay'" not in report:
        raise ValueError("synthesis report does not identify m05_rolling_replay")
    if "* Version:" not in report or "2025.2" not in report:
        raise ValueError("synthesis report is not marked Vitis 2025.2")
    m = re.search(r"\|\s*ap_clk\s*\|\s*([\d.]+) ns\s*\|\s*([\d.]+) ns\s*\|", report)
    if not m:
        raise ValueError("missing HLS target/estimated clock row")
    summary["requested_clock_ns"] = float(m.group(1))
    summary["estimated_clock_ns"] = float(m.group(2))
    resources = []
    for line in report.splitlines():
        cells = _cells(line)
        if len(cells) == 6 and cells[0] == "Total" and all(
            re.fullmatch(r"\d+", value) for value in cells[1:]
        ):
            resources.append(cells)
    if len(resources) != 1:
        raise ValueError("ambiguous/missing top-level utilization Total row")
    c = resources[0]
    summary.update(bram18k=int(c[1]), dsp=int(c[2]), ff=int(c[3]),
                   lut=int(c[4]), uram=int(c[5]))
    mem = []
    for line in report.splitlines():
        cells = _cells(line)
        if cells and cells[0] == "current_U" and len(cells) == 10:
            mem.append(cells)
    if len(mem) != 1:
        raise ValueError("missing/ambiguous rolling current_U memory inference")
    summary["current_bram18k"] = int(mem[0][2])
    summary["current_word_bits"] = int(mem[0][7])


def _cosim_report(summary: dict[str, object], report: str) -> None:
    if "Solution" not in report or "xsim" not in report.lower():
        raise ValueError("missing Vitis XSim identification")
    results = []
    for line in report.splitlines():
        cells = _cells(line)
        if len(cells) == 9 and cells[0] == "Verilog":
            results.append(cells)
    if len(results) != 1:
        raise ValueError("ambiguous/missing Verilog XSim result")
    c = results[0]
    if c[1] != "Pass":
        raise ValueError("Verilog XSim is not PASS")
    try:
        counts = [int(x) for x in c[2:]]
    except ValueError as exc:
        raise ValueError("XSim result lacks numeric cycle counts") from exc
    summary.update(cosim_verilog_pass=True,
                   cosim_latency_cycles=tuple(counts[:3]),
                   cosim_interval_cycles=tuple(counts[3:6]),
                   cosim_total_cycles=counts[6])


def audit(directory: Path) -> EvidenceSummary:
    root = directory.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"evidence path is not a directory: {root}")
    if not root.name.startswith("neuromorphic_v1_m05_rolling_"):
        raise ValueError("not a rolling M05 evidence directory")
    result = _safe_read(root, "result.txt")
    if result is None:
        raise ValueError("missing result.txt — incomplete or unverified run")
    m = re.search(r"^exit_status=(\d+)\s*$", result.strip())
    if not m or m.group(1) != "0":
        raise ValueError("Vitis command did not return exit_status=0")
    top = _safe_read(root, "top.txt")
    top = top.strip() if top else None
    if top is not None and top != "m05_rolling_replay":
        raise ValueError("evidence top mismatch")
    part = _safe_read(root, "part.txt")
    part = part.strip() if part else None
    if part is not None and part != "xck26-sfvc784-2LV-c":
        raise ValueError("unexpected FPGA target")
    manifest = _parse_hashes(_safe_read(root, "source_sha256.txt"))
    src = _hash_for_path(manifest, HLS_SOURCE)
    tb = _hash_for_path(manifest, HLS_BENCH)
    commit = _safe_read(root, "commit.txt")
    commit = commit.strip() if commit else None
    if commit and not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid commit.txt SHA")
    synth = _safe_read(root, TOP_CSYNTH)
    cosim = _safe_read(root, TOP_COSIM)
    if synth is None and cosim is None:
        raise ValueError("no usable HLS synthesis or XSim report")
    if cosim is not None and synth is None:
        raise ValueError("XSim report without a synthesis report")
    values: dict[str, object] = {
        "evidence_path": str(root), "evidence_id": root.name,
        "source_commit": commit, "source_sha256": src,
        "testbench_sha256": tb, "requested_clock_ns": None,
        "estimated_clock_ns": None, "bram18k": None, "lut": None,
        "ff": None, "dsp": None, "uram": None, "current_bram18k": None,
        "current_word_bits": None, "cosim_verilog_pass": None,
        "cosim_latency_cycles": None, "cosim_interval_cycles": None,
        "cosim_total_cycles": None, "exit_status": 0,
        "hls_top": top, "device": part, "is_real_vitis_2025_2_report": False,
    }
    if synth is not None:
        _synth_report(values, synth)
        values["is_real_vitis_2025_2_report"] = True
    if cosim is not None:
        _cosim_report(values, cosim)
        log = _safe_read(root, "03_cosim.log")
        if log is None or "[COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***" not in log:
            raise ValueError("cosim report PASS lacks confirming cosim log")
    return EvidenceSummary(**values)  # type: ignore[arg-type]


def markdown(summaries: list[EvidenceSummary]) -> str:
    out = [
        "# M05 rolling — operator-local evidence audit",
        "",
        "Original artifacts remain unchanged; this is a derivative summary, not raw evidence.",
        "HLS clock is an **estimate**, NOT routed timing. XSim cycles are testbench transactions, NOT FPS/throughput.",
        "",
        "| Evidence directory | Git commit | Sum bits | BRAM18K | Current BRAM | LUT | FF | DSP | HLS clock ns | XSim avg cycles |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in summaries:
        latency = x.cosim_latency_cycles
        row = [x.evidence_id,
               x.source_commit[:12] if x.source_commit else "unknown",
               str(x.current_word_bits) if x.current_word_bits is not None else "—",
               str(x.bram18k) if x.bram18k is not None else "—",
               str(x.current_bram18k) if x.current_bram18k is not None else "—",
               str(x.lut) if x.lut is not None else "—",
               str(x.ff) if x.ff is not None else "—",
               str(x.dsp) if x.dsp is not None else "—",
               f"{x.estimated_clock_ns:.3f}" if x.estimated_clock_ns is not None else "—",
               str(latency[1]) if latency is not None else "—"]
        out.append("| " + " | ".join(row) + " |")
    out += ["", "## Provenance warnings", ""]
    hashes = {x.testbench_sha256 for x in summaries}
    if None in hashes or len(hashes) > 1:
        out.append("- **Latency/interval comparisons are NOT controlled**: at least one testbench SHA differs or is unrecorded. Do not infer a speedup or slowdown from XSim averages.")
    else:
        out.append("- All recorded testbench SHA256 values match, but check runtime parameters and workloads before comparing per-case XSim timing.")
    commits = {x.source_commit for x in summaries}
    if None in commits:
        out.append("- At least one source commit is unknown; request the original `commit.txt` for provenance.")
    if len(commits) > 1:
        out.append("- Multiple source commits are represented; differing source hashes are expected for optimizations.")
    out.append("- Source hashes are recorded when the runner's `source_sha256.txt` is present; they help verify exact evaluation-engine versions.")
    out.append("- Vitis tool warnings, physical timing, RTL backpressure and physical K26 results are **outside this report**.")
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, nargs="+", required=True,
                        help="one or more unmodified rolling *_synth_* or *_cosim_* evidence dirs")
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--json", action="store_true")
    output.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    try:
        summaries = [audit(p) for p in args.evidence]
    except (OSError, ValueError) as exc:
        print(f"EVIDENCE AUDIT FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if args.json:
        print(json.dumps([asdict(summary) for summary in summaries], indent=2))
    else:
        print(markdown(summaries), end="")


if __name__ == "__main__":
    main()
