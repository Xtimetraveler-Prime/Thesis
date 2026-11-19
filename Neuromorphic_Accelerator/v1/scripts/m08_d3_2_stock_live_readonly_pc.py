#!/usr/bin/env python3
"""Bounded, non-mutating KV260 stock physical live observation with PC-side SHA ledger.

Reads FPGA-manager state, dfx/fan services, stock overlay and temperatures.
Does not read registers or change the FPGA, fan, firmware, SSH authorization.
This is NOT stock rollback proof or passive-bitstream programming permission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

TARGET = "ubuntu@10.42.0.135"
PASSIVE_SHA = "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547"
STOCK_SHA = "f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e"
MANUAL_STATUS = "STOCK_READONLY_FIVE_PROBES_PLUS_MANUAL_XMUTIL_REVIEW_ONLY"
BEGIN = "M08_D3_2_STOCK_LIVE_BEGIN"
END = "M08_D3_2_STOCK_LIVE_END"
SCRIPT = r"""#!/usr/bin/env bash
set -u
printf 'M08_D3_2_STOCK_LIVE_BEGIN\n'
printf 'BOARD_MODEL='; tr '\000' ' ' </proc/device-tree/model; printf '\n'
printf 'FPGA_STATE='; cat /sys/class/fpga_manager/fpga0/state
printf 'DFX_SERVICE='; systemctl is-active dfx-mgr
printf 'FAN_SERVICE='; systemctl is-active fancontrol
for d in /sys/kernel/config/device-tree/overlays/*; do
    if [ -d "$d" ]; then printf 'ACTIVE_OVERLAY=%s\n' "$d"; fi
done
for f in /sys/class/hwmon/hwmon*/temp*_input; do
    if [ -f "$f" ] && [ -r "$f" ]; then printf 'TEMP=%s:' "$f"; cat "$f"; fi
done
printf 'M08_D3_2_STOCK_LIVE_END\n'
"""


class Rejected(ValueError):
    pass


def must(ok: bool, msg: str) -> None:
    if not ok:
        raise Rejected(msg)


def read(path: Path, cap=100000) -> bytes:
    must(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= cap,
         "invalid read-only input " + str(path))
    return path.read_bytes()


def review_manual_receipt(path: Path) -> dict:
    must(path.is_dir() and not path.is_symlink(), "invalid manual receipt directory")
    ledger = read(path / "99_evidence_sha256.txt", 4096).decode("ascii").splitlines()
    must(len(ledger) == 2, "manual SHA ledger must contain two files")
    for name, line in zip(("00_manual_xmutil_stdout.txt", "01_review.json"), ledger):
        must(re.fullmatch(r"[0-9a-f]{64}  " + re.escape(name), line) is not None,
             "manual SHA ledger layout invalid")
        must(line[:64] == sha256(read(path / name)).hexdigest(),
             "manual SHA receipt mismatch " + name)
    obj = json.loads(read(path / "01_review.json"))
    app = obj.get("manual_xmutil_receipt", {})
    original = obj.get("previous_stock_readonly_evidence", {})
    must(obj.get("status") == MANUAL_STATUS and
         app.get("operator_observed_stock_app") == "k26-starter-kits" and
         app.get("operator_observed_active_slot") == "0->0" and
         app.get("operator_observed_prior_m08_slot") == "-1" and
         original.get("new_passive_bit_sha256") == PASSIVE_SHA and
         original.get("stock_bit_sha256") == STOCK_SHA and
         obj.get("hardware_programming_authorized") is False and
         obj.get("new_passive_bitstream_loaded") is False and
         obj.get("stock_boot_or_rollback_independently_proven") is False,
         "manual stock receipt is not an accepted review-only baseline")
    return {
        "manual_review_sha256": sha256(read(path / "01_review.json")).hexdigest(),
        "manual_ledger_sha256": sha256(read(path / "99_evidence_sha256.txt")).hexdigest(),
        "stock_sha256": STOCK_SHA,
        "passive_unreleased_sha256": PASSIVE_SHA,
    }


def source_gate() -> None:
    must(SCRIPT.startswith("#!/usr/bin/env bash"), "bad script shebang")
    for cmd in ("sudo ", "xmutil", "program_hw_devices", "/dev/uio", "/dev/mem",
                "fpgautil", "systemctl start", "systemctl stop", "systemctl restart",
                "rm ", "echo >", "tee ", "reboot", "poweroff", "write_bitstream"):
        must(cmd not in SCRIPT, "unsafe board-side command "+cmd)
    must(SCRIPT.count(BEGIN) == SCRIPT.count(END) == 1, "live script boundary change")


def parse_observation(raw: bytes, rc: int) -> dict:
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()
    must(rc == 0 and lines and lines[0] == BEGIN and lines[-1] == END,
         "SSH exit/boundary failure")
    for needed in (
        "BOARD_MODEL=ZynqMP KV260 revB",
        "FPGA_STATE=operating",
        "DFX_SERVICE=active",
        "FAN_SERVICE=active",
        "ACTIVE_OVERLAY=/sys/kernel/config/device-tree/overlays/k26-starter-kits_image_1",
    ):
        must(needed in lines, "stock live safety baseline changed: " + needed)
    values = []
    for line in lines:
        if line.startswith("TEMP="):
            match = re.fullmatch(r"TEMP=/sys/class/hwmon/hwmon\d+/temp\d+_input:(-?\d+)", line)
            must(match is not None, "unrecognized thermal sensor output")
            values.append(int(match.group(1)))
    must(values and all(0 < t < 85000 for t in values),
         "missing/out-of-range stock sensor measurement")
    return {"temperatures_millideg_c": values, "stock_state": "PRESENT",
            "hardware_programming_authorized": False}


def capture(manual_review: Path, evidence_base: Path, target: str = TARGET,
            *, runner=subprocess.run, samples: int = 3) -> dict:
    must(os.geteuid() != 0, "PC capture must not run as root")
    must(target == TARGET and 2 <= samples <= 5, "wrong target/sample count")
    source_gate()
    src = review_manual_receipt(manual_review)
    must(evidence_base.is_dir() and not evidence_base.is_symlink() and
         evidence_base.resolve() != manual_review.resolve(),
         "bad evidence base")
    folder = Path(tempfile.mkdtemp(prefix="m08_d3_2_stock_LIVE_READONLY_", dir=evidence_base))
    (folder / "00_source.sh").write_text(SCRIPT)
    (folder / "01_inputs.json").write_text(json.dumps({
        "schema": "m08-d3-2-stock-live-readonly-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "remote": TARGET, "requested_samples": samples, **src,
        "stock_rollback_proven": False,
        "physical_fan_airflow_proven_by_sysfs": False,
        "hardware_programming_authorized": False,
    }, sort_keys=True, indent=2)+"\n")
    readings = []
    for index in range(samples):
        rc, stdout, stderr = 255, b"", b""
        try:
            result = runner(
                ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                 "-o", "ConnectTimeout=12", "-o", "ServerAliveInterval=5",
                 "-o", "ServerAliveCountMax=2", target, "bash -s"],
                input=SCRIPT.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=25)
            rc, stdout, stderr = result.returncode, result.stdout, result.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            stderr = str(exc).encode()
        prefix = f"{index+1:02}_sample"
        (folder / (prefix+".stdout.txt")).write_bytes(stdout if stdout else b"\n")
        (folder / (prefix+".stderr.txt")).write_bytes(stderr if stderr else b"\n")
        try:
            reading = parse_observation(stdout, rc)
            reading["status"] = "PASS_STOCK_ONLY"
        except Rejected as exc:
            reading = {"status": "STOP_STOCK_OBSERVATION_INVALID",
                       "error": str(exc), "hardware_programming_authorized": False}
        reading["ssh_exit_status"] = rc
        readings.append(reading)
        if reading["status"] != "PASS_STOCK_ONLY":
            break
    complete = len(readings) == samples and all(x["status"] == "PASS_STOCK_ONLY" for x in readings)
    status = "STOCK_LIVE_READONLY_OBSERVED_NO_RECONFIGURATION" if complete else "STOCK_LIVE_READONLY_STOP"
    (folder / "90_review.json").write_text(json.dumps({
        "schema": "m08-d3-2-stock-live-review-v1",
        "status": status,
        "samples": readings,
        "physical_bitstream_programmed": False,
        "stock_rollback_proven": False,
        "backup_fan_physical_airflow_proven": False,
        "hardware_programming_authorized": False,
    }, sort_keys=True, indent=2)+"\n")
    files = sorted(f for f in folder.iterdir() if f.is_file() and f.name != "99_evidence_sha256.txt")
    (folder / "99_evidence_sha256.txt").write_text(
        "".join(sha256(f.read_bytes()).hexdigest()+"  "+f.name+"\n" for f in files))
    return {"status": status, "evidence_dir": str(folder),
            "hardware_programming_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-review", type=Path, required=True)
    parser.add_argument("--evidence-base", type=Path, required=True)
    parser.add_argument("--target", default=TARGET)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    try:
        result = capture(args.manual_review, args.evidence_base, args.target, samples=args.samples)
    except (Rejected, OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print("M08_D3_2_LIVE_READONLY_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "STOCK_LIVE_READONLY_OBSERVED_NO_RECONFIGURATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
