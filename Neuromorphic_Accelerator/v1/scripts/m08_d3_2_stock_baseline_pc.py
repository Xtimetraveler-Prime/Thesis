#!/usr/bin/env python3
"""M08 D3.2 guarded PC capture of STOCK BOARD READ-ONLY baseline.

Physical test stage 0 ONLY. Explicitly DOES NOT program FPGA, create/install
firmware/DTBO, alter Linux, run MMIO or certify a recovery procedure.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BOARD_SH = ROOT / "scripts/m08_d3_2_stock_board_baseline_readonly.sh"
EXPECTED_BIT_SHA = "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547"
OLD_QUARANTINED_SHA = "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b"
EXPECTED_BIT_BYTES = 7797839
BOARD_TARGET = "ubuntu@10.42.0.135"
LABELS = (
    "board_identity", "stock_pl_manager", "installed_apps",
    "stock_firmware_files", "sensors", "overlay_and_uio_names",
)
READINESS = (
    "independent_backup_fan_powered_and_airflow_observed",
    "local_serial_console_connected_and_logging",
    "owner_has_known_stock_boot_and_power_cycle_recovery",
    "owner_has_checked_board_is_not_in_a_stalled_state",
    "owner_authorizes_read_only_stock_baseline_only",
)


class BaselineRejected(ValueError):
    pass


def must(check: bool, message: str) -> None:
    if not check:
        raise BaselineRejected(message)


def load_bit_gate():
    path = ROOT / "scripts/m08_d3_2_passive_bitstream_gate.py"
    spec = importlib.util.spec_from_file_location("m08_d3_2_phys_bit_parent", path)
    must(spec is not None and spec.loader is not None, "missing original bitgen auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_file(path: Path, cap: int) -> bytes:
    must(path.is_file() and not path.is_symlink(),
         "missing or symlinked PC readiness input: " + str(path))
    must(0 < path.stat().st_size <= cap, "empty/oversized PC readiness input: " + str(path))
    return path.read_bytes()


def candidate_audit(run: Path) -> dict:
    gate = load_bit_gate()
    try:
        gate.source_gate()
        report = gate.native_candidate(run)
    except gate.Rejected as exc:
        raise BaselineRejected("original bitgen SHA/review rejected: " + str(exc)) from exc
    must(report["status"] == "M08_D3_2_UNRELEASED_PASSIVE_BITSTREAM_SHA_ACCEPTED_NO_BOARD",
         "candidate has no accepted original SHA receipt")
    must(report["bitstream_sha256"] == EXPECTED_BIT_SHA and
         report["bitstream_size_bytes"] == EXPECTED_BIT_BYTES and
         report["bitstream_sha256"] != OLD_QUARANTINED_SHA,
         "candidate bytes do not match exact new unreleased passive image")
    must(report["physical_programming_authorized"] is False,
         "candidate illegally marked hardware authorized")
    return {
        "candidate_sha256": EXPECTED_BIT_SHA,
        "candidate_size_bytes": EXPECTED_BIT_BYTES,
        "candidate_kind": "PASSIVE_FAN_NO_PS_TO_PL_AXI_UNRELEASED",
        "original_sha_99_98_96_verified": True,
        "physical_programming_authorized": False,
    }


def check_script() -> bytes:
    sh = read_file(BOARD_SH, 50_000)
    src = sh.decode("utf-8")
    must(src.startswith("#!/usr/bin/env bash\n"), "board script requires Bash shebang")
    for required in (
        "M08_D3_2_STOCK_READONLY_BEGIN",
        "M08_D3_2_STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES",
        "xmutil listapps", "systemctl is-active dfx-mgr",
        "systemctl is-active fancontrol", "fpga0/state",
    ):
        must(required in src, "board read-only source contract missing: " + required)
    active = "\n".join(x for x in src.splitlines()
                       if x.strip() and not x.lstrip().startswith("#"))
    for forbidden in (
        "sudo ", "xmutil loadapp", "xmutil unloadapp",
        "program_hw_devices", "write_bitstream", "fpgautil",
        "echo > /sys", "/dev/uio", "/dev/mem", "dd if=", "rm -rf", "systemctl stop",
        "systemctl start", "systemctl restart", "reboot", "poweroff",
    ):
        must(forbidden not in active, "board baseline includes unsafe operation: " + forbidden)
    must(src.count("probe ") == len(LABELS),
         "board read-only probe count changed")
    return sh


def parse_readiness(path: Path, bit_sha: str) -> dict:
    obj = json.loads(read_file(path, 20_000))
    must(isinstance(obj, dict) and
         obj.get("schema") == "m08-d3-2-owner-physical-readiness-v1",
         "bad owner safety record schema")
    must(obj.get("candidate_bit_sha256") == bit_sha,
         "owner checklist does not pin exact passive candidate")
    for name in READINESS:
        must(obj.get(name) is True, "manual readiness not explicitly confirmed: " + name)
    must(obj.get("owner_confirms_no_programming_in_this_step") is True,
         "owner has not limited stage 0 to read-only baseline")
    return obj


def parse_capture(raw: bytes, exit_status: int) -> dict:
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    must(lines and lines[0] == "M08_D3_2_STOCK_READONLY_BEGIN" and
         lines[-1] == "M08_D3_2_STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES",
         "missing board capture boundary markers")
    codes = {}
    for label in LABELS:
        begin = "M08_D3_2_PROBE_BEGIN|" + label
        found = [x for x in lines if x == begin]
        ends = [x for x in lines if x.startswith("M08_D3_2_PROBE_END|" + label + "|rc=")]
        must(len(found) == len(ends) == 1, "missing/duplicate probe boundary: " + label)
        match = re.fullmatch(r"M08_D3_2_PROBE_END\|" + re.escape(label) +
                             r"\|rc=(\d+)", ends[0])
        must(match is not None, "unparseable probe code: " + label)
        codes[label] = int(match.group(1))
    must(exit_status == 0 and all(rc == 0 for rc in codes.values()),
         "SSH/board read-only probe incomplete (no programming)")
    # Stock runtime state is interpreted by a human, not guessed from one grep.
    return {
        "status": "STOCK_BOARD_READONLY_CAPTURE_COMPLETE_HUMAN_REVIEW_REQUIRED",
        "probes": codes,
        "ssh_exit_status": exit_status,
        "stock_boot_verified": False,
        "linux_pl_ownership_reviewed": False,
        "fan_physical_verification_automated": False,
        "hardware_programming_authorized": False,
    }


def capture(args, *, subprocess_runner=subprocess.run) -> dict:
    must(os.geteuid() != 0, "PC operator must not run capture as root")
    must(args.target == BOARD_TARGET, "new board target requires source review")
    candidate = candidate_audit(args.candidate_run)
    source = check_script()
    readiness = parse_readiness(args.readiness, candidate["candidate_sha256"])
    base = args.evidence_base
    must(base.is_dir() and not base.is_symlink(), "missing owner PC evidence base")
    must(base.resolve() != args.candidate_run.resolve(),
         "never write into accepted bitstream candidate")
    folder = Path(tempfile.mkdtemp(prefix="m08_d3_2_stock_READONLY_", dir=base))
    (folder / "00_stock_board_readonly.sh").write_bytes(source)
    (folder / "01_inputs.json").write_text(json.dumps({
        "schema": "m08-d3-2-stock-readonly-pc-evidence-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "board_target": BOARD_TARGET,
        "script_sha256": sha256(source).hexdigest(),
        "manual_readiness_sha256": sha256(read_file(args.readiness, 20_000)).hexdigest(),
        "owner_readiness_is_not_independent_boot_proof": True,
        **candidate,
    }, indent=2, sort_keys=True)+"\n")
    (folder / "02_manual_operator_record.json").write_text(
        json.dumps(readiness, indent=2, sort_keys=True)+"\n")
    rc = 255
    stderr = b""
    stdout = b""
    try:
        res = subprocess_runner(
            ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12",
             "-o", "StrictHostKeyChecking=yes", "-o", "ServerAliveInterval=5",
             "-o", "ServerAliveCountMax=2", BOARD_TARGET, "bash -s"],
            input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=75, check=False)
        rc, stdout, stderr = res.returncode, res.stdout, res.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        stderr = ("SSH read-only capture exception: " + str(exc)).encode()
    (folder / "03_board_stdout.log").write_bytes(stdout if stdout else b"\n")
    (folder / "04_board_stderr.log").write_bytes(stderr if stderr else b"\n")
    (folder / "05_ssh_exit_status.txt").write_text("exit_status=" + str(rc) + "\n")
    try:
        status = parse_capture(stdout, rc)
    except BaselineRejected as exc:
        status = {
            "status": "STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP",
            "error": str(exc),
            "ssh_exit_status": rc,
            "hardware_programming_authorized": False,
        }
    (folder / "06_readonly_review.json").write_text(json.dumps(status, indent=2, sort_keys=True)+"\n")
    inputs = ["00_stock_board_readonly.sh", "01_inputs.json",
              "02_manual_operator_record.json", "03_board_stdout.log",
              "04_board_stderr.log", "05_ssh_exit_status.txt",
              "06_readonly_review.json"]
    lines = [sha256((folder / f).read_bytes()).hexdigest()+"  "+f
             for f in inputs]
    (folder / "99_evidence_sha256.txt").write_text("\n".join(lines)+"\n")
    return {
        "new_pc_evidence_dir": str(folder),
        "status": status["status"],
        "board_programmed": False,
        "no_bitstream_copied_to_board": True,
        "next_step": "HUMAN_STOCK_AND_BOOT_REVIEW_REQUIRED_BEFORE_NEW_PL_LOAD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-run", type=Path, required=True)
    ap.add_argument("--readiness", type=Path, required=True)
    ap.add_argument("--evidence-base", type=Path, required=True)
    ap.add_argument("--target", default=BOARD_TARGET)
    args = ap.parse_args()
    try:
        result = capture(args)
    except (BaselineRejected, ValueError, TypeError, OSError,
            KeyError, UnicodeError) as exc:
        print("M08_D3_2_STOCK_READONLY_PREFLIGHT_REJECTED: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "STOCK_BOARD_READONLY_CAPTURE_COMPLETE_HUMAN_REVIEW_REQUIRED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
