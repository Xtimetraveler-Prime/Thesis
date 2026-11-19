#!/usr/bin/env python3
"""Correlate original 5/6 read-only KV260 evidence with separately authenticated xmutil.

OFFLINE PC reviewer only. No network calls, root, programming, board mutation,
password collection, or retroactive alteration of original evidence.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import tempfile

EXPECTED_STOCK_BIT_SHA = "f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e"
EXPECTED_STOCK_DTBO_SHA = "1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1"
EXPECTED_PASSIVE_SHA = "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547"
EXPECTED_PROBES = (
    "board_identity", "stock_pl_manager", "installed_apps", "stock_firmware_files",
    "sensors", "overlay_and_uio_names",
)
ORIGINAL_FILES = (
    "00_stock_board_readonly.sh", "01_inputs.json", "02_manual_operator_record.json",
    "03_board_stdout.log", "04_board_stderr.log", "05_ssh_exit_status.txt",
    "06_readonly_review.json",
)


class ManualReviewRejected(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ManualReviewRejected(reason)


def read_bytes(path: Path, limit: int = 500_000) -> bytes:
    require(path.is_file() and not path.is_symlink(), "missing or symlinked input: " + str(path))
    require(0 < path.stat().st_size <= limit, "empty/oversized input: " + str(path))
    return path.read_bytes()


def audit_original(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink(), "invalid original evidence directory")
    ledger = read_bytes(folder / "99_evidence_sha256.txt", 4096).decode("ascii")
    rows = ledger.splitlines()
    require(len(rows) == len(ORIGINAL_FILES), "original evidence receipt entry count changed")
    for expected_name, row in zip(ORIGINAL_FILES, rows):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", row)
        require(match is not None and match.group(2) == expected_name,
                "original evidence receipt filename/order mismatch")
        require(sha256(read_bytes(folder / expected_name)).hexdigest() == match.group(1),
                "original evidence hash mismatch: " + expected_name)

    inputs = json.loads(read_bytes(folder / "01_inputs.json"))
    review = json.loads(read_bytes(folder / "06_readonly_review.json"))
    stdout = read_bytes(folder / "03_board_stdout.log").decode("utf-8", errors="replace")
    stderr = read_bytes(folder / "04_board_stderr.log", 500_000).decode("utf-8", errors="replace")
    exit_status = read_bytes(folder / "05_ssh_exit_status.txt", 100).decode("ascii")
    require(inputs.get("candidate_sha256") == EXPECTED_PASSIVE_SHA and
            inputs.get("physical_programming_authorized") is False and
            inputs.get("original_sha_99_98_96_verified") is True,
            "original PC candidate pin/safety claim invalid")
    require(review.get("status") == "STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP" and
            review.get("ssh_exit_status") == 0 and
            review.get("hardware_programming_authorized") is False and
            exit_status == "exit_status=0\n" and not stderr.strip(),
            "original read-only session must be SSH complete and nonprogramming")
    lines = stdout.splitlines()
    require(lines[0] == "M08_D3_2_STOCK_READONLY_BEGIN" and
            lines[-1] == "M08_D3_2_STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES",
            "original probe transcript boundary missing")
    codes = {}
    for label in EXPECTED_PROBES:
        beg = "M08_D3_2_PROBE_BEGIN|" + label
        ends = [line for line in lines if line.startswith("M08_D3_2_PROBE_END|" + label + "|rc=")]
        require(lines.count(beg) == 1 and len(ends) == 1,
                "missing or duplicate original probe: " + label)
        match = re.fullmatch(r"M08_D3_2_PROBE_END\|" + re.escape(label) + r"\|rc=(\d+)",
                             ends[0])
        require(match is not None, "malformed original probe return code")
        codes[label] = int(match.group(1))
    require(codes["installed_apps"] == 1 and
            all(rc == 0 for k, rc in codes.items() if k != "installed_apps"),
            "original capture must have only unprivileged xmutil failure")
    require("xmutil should be called with root privileges" in stdout,
            "original failure reason missing")
    for evidence in (
        "MODEL=ZynqMP KV260 revB",
        "FPGA_STATE=operating", "DFX_SERVICE=active", "FAN_SERVICE=active",
        "k26-starter-kits_image_1",
        EXPECTED_STOCK_BIT_SHA, EXPECTED_STOCK_DTBO_SHA,
    ):
        require(evidence in stdout, "required actual stock baseline evidence missing: "+evidence)
    return {
        "original_capture_status": review["status"],
        "original_ssh_exit": 0,
        "original_probe_rc": codes,
        "original_ledger_sha256": sha256(ledger.encode("ascii")).hexdigest(),
        "original_stdout_sha256": sha256(stdout.encode("utf-8")).hexdigest(),
        "stock_bit_sha256": EXPECTED_STOCK_BIT_SHA,
        "stock_dtbo_sha256": EXPECTED_STOCK_DTBO_SHA,
        "new_passive_bit_sha256": EXPECTED_PASSIVE_SHA,
    }


def audit_manual_xmutil(raw: bytes, operator_exit: int) -> dict:
    require(operator_exit == 0, "manual xmutil SSH command exit was not 0")
    text = raw.decode("utf-8", errors="replace").replace("\r", "")
    require("Accelerator" in text and "slot->handle" in text,
            "xmutil inventory header missing")
    require("password is required" not in text and "Permission denied" not in text,
            "manual xmutil privilege/authentication failed")
    rows = {}
    for line in text.splitlines():
        match = re.match(r"^\s*(m08-v1-fan-page-uio-review|k26-starter-kits|k24-starter-kits)\s+",
                         line)
        if match:
            name = match.group(1)
            require(name not in rows, "duplicate app in manual xmutil inventory: " + name)
            rows[name] = line.strip()
    require("k26-starter-kits" in rows and "m08-v1-fan-page-uio-review" in rows,
            "manual inventory missing stock or historic M08 app")
    require(re.search(r"\b0->0,?\s*$", rows["k26-starter-kits"]) is not None,
            "stock k26-starter-kits is not active in 0->0")
    require(re.search(r"\s-1\s*$", rows["m08-v1-fan-page-uio-review"]) is not None,
            "historic M08 app not confirmed inactive")
    require(all("0->" not in line for key, line in rows.items() if key != "k26-starter-kits"),
            "more than stock app appears active")
    return {
        "operator_observed_stock_app": "k26-starter-kits",
        "operator_observed_active_slot": "0->0",
        "operator_observed_prior_m08_app": "m08-v1-fan-page-uio-review",
        "operator_observed_prior_m08_slot": "-1",
        "operator_recorded_xmutil_ssh_exit": operator_exit,
        "operator_transcript_sha256": sha256(raw).hexdigest(),
        "manual_output_provenance": "OWNER_PC_TERMINAL_CAPTURE_NOT_INDEPENDENT_KERNEL_ATTESTATION",
        "app_rows": rows,
    }


def create_receipt(original: Path, manual: Path, manual_exit: int, evidence_base: Path) -> dict:
    baseline = audit_original(original)
    manual_bytes = read_bytes(manual, 100_000)
    app_review = audit_manual_xmutil(manual_bytes, manual_exit)
    require(evidence_base.is_dir() and not evidence_base.is_symlink(),
            "missing safe PC evidence base")
    require(original.resolve() not in evidence_base.resolve().parents and
            evidence_base.resolve() != original.resolve(),
            "refuse original evidence as destination")
    result_folder = Path(tempfile.mkdtemp(prefix="m08_d3_2_xmutil_MANUAL_REVIEW_", dir=evidence_base))
    (result_folder / "00_manual_xmutil_stdout.txt").write_bytes(manual_bytes)
    report = {
        "schema": "m08-d3-2-manual-xmutil-correlation-v1",
        "status": "STOCK_READONLY_FIVE_PROBES_PLUS_MANUAL_XMUTIL_REVIEW_ONLY",
        "original_evidence_dir": str(original.resolve()),
        "manual_xmutil_receipt": app_review,
        "previous_stock_readonly_evidence": baseline,
        "operator_sudo_was_interactive": True,
        "automatic_six_probe_baseline_accepted": False,
        "stock_boot_or_rollback_independently_proven": False,
        "physical_backup_fan_independently_proven": False,
        "new_passive_bitstream_loaded": False,
        "hardware_programming_authorized": False,
        "axil_mmio_authorized": False,
    }
    (result_folder / "01_review.json").write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
    receipt = "\n".join(
        sha256((result_folder / name).read_bytes()).hexdigest() + "  " + name
        for name in ("00_manual_xmutil_stdout.txt", "01_review.json")
    ) + "\n"
    (result_folder / "99_evidence_sha256.txt").write_text(receipt)
    return {"status": report["status"], "evidence_dir": str(result_folder),
            "hardware_programming_authorized": False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-baseline", type=Path, required=True)
    ap.add_argument("--manual-transcript", type=Path, required=True)
    ap.add_argument("--manual-ssh-exit", type=int, required=True)
    ap.add_argument("--evidence-base", type=Path, required=True)
    args = ap.parse_args()
    try:
        report = create_receipt(args.original_baseline, args.manual_transcript,
                                args.manual_ssh_exit, args.evidence_base)
    except (ManualReviewRejected, OSError, UnicodeError, ValueError,
            json.JSONDecodeError, IndexError) as exc:
        print("M08_D3_2_MANUAL_XMUTIL_REJECTED: "+str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
