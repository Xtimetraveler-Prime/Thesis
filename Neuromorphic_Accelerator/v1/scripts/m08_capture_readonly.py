#!/usr/bin/env python3
"""M08.1 immutable read-only host/ON-BOARD Linux inventory; NO PROGRAMMING.

On development PC: --mode host
On a booted KV260 *itself*: --mode board-local
No JTAG, sudo, /dev/mem, Vivado implementation or DMA writes; no network.
Capture existence/integrity is not proof of correctly deployed hardware.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m08_entry import (
    SCHEMA, PhysicalReadiness, archive_inventory, sha_file,
)


def _run(argv: tuple[str, ...], *, cwd: Path | None = None,
         timeout: int = 20) -> dict:
    """Allowlisted, shell-free local introspection only."""
    permitted = {
        ("git", "rev-parse", "HEAD"),
        ("git", "status", "--porcelain=v1"),
        ("uname", "-a"),
        ("lsusb",),
        ("vivado", "-version"),
        ("vitis_hls", "-version"),
        ("xmutil", "listapps"),
        ("xmutil", "boardid"),
        ("xmutil", "bootfw_status"),
        ("xmutil", "platformstats"),
    }
    if argv not in permitted:
        raise ValueError("not an approved read-only inventory command")
    if shutil.which(argv[0]) is None:
        return {"argv": list(argv), "status": "COMMAND_NOT_FOUND",
                "returncode": None, "stdout": "", "stderr": ""}
    try:
        r = subprocess.run(argv, cwd=cwd, text=True, errors="replace",
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, check=False)
        return {"argv": list(argv), "status": (
            "OK" if r.returncode == 0 else "EXIT_NONZERO"),
            "returncode": r.returncode, "stdout": r.stdout[:30000],
            "stderr": r.stderr[:10000]}
    except subprocess.TimeoutExpired:
        return {"argv": list(argv), "status": "TIMEOUT",
                "returncode": None, "stdout": "", "stderr": ""}


def _read(path: Path, *, limit: int = 100000) -> dict:
    """Read bounded, named OS/DT evidence only; no arbitrary device nodes."""
    permitted = {
        "/proc/device-tree/model", "/proc/cmdline", "/proc/meminfo",
        "/etc/os-release", "/proc/version",
    }
    if str(path) not in permitted:
        raise ValueError("read-only board file not allowlisted")
    if not path.is_file():
        return {"status": "MISSING", "text": ""}
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        return {"status": "TOO_LARGE", "text": ""}
    return {"status": "OK", "text": data.replace(b"\x00", b"\n").decode(
        "utf-8", errors="replace")}


def capture(mode: str, *, source_root: Path, originals: Path | None,
            runner=_run, reader=_read) -> dict:
    if mode not in ("host", "board-local"):
        raise ValueError("unknown inventory mode")
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "schema": SCHEMA, "mode": mode, "utc": now,
        "state": "READ_ONLY_OBSERVATIONS_NOT_HARDWARE_ACCEPTANCE",
        "kv260_programmed_by_this_tool": False,
        "physical_dma_issued_by_this_tool": False,
        "ready_for_physical_ddr": False,
        "physical_readiness": PhysicalReadiness().assess(),
        "platform": {"machine": platform.machine(), "system": platform.system(),
                     "python": platform.python_version()},
        "commands": {}, "board_files": {},
        "accepted_original_archive_inventory": {"status": "NOT_SCANNED",
                                                   "all_sha256_match": False,
                                                   "items": []},
        "source_sha256": {},
        "notes": [
            "LOCAL observations, NOT remote device attestation",
            "No original vendor simulation, bitstream, JTAG, DMA or DDR operation",
            "Linux /dev/mem or bare physical base address is never authorized",
        ],
    }
    if mode == "host":
        if not source_root.is_dir() or not (source_root / "src").is_dir():
            raise ValueError("valid v1 source repository path required")
        for cmd in (
            ("git", "rev-parse", "HEAD"),
            ("git", "status", "--porcelain=v1"),
            ("uname", "-a"),
            ("lsusb",),
            ("vivado", "-version"),
            ("vitis_hls", "-version"),
        ):
            result["commands"][" ".join(cmd)] = runner(
                cmd, cwd=source_root)
        for rel in (
            "src/neuromorphic_accelerator_v1/m08_entry.py",
            "scripts/m08_capture_readonly.py",
        ):
            result["source_sha256"][rel] = sha_file(source_root / rel)
        result["accepted_original_archive_inventory"] = archive_inventory(originals)
        # A nonempty checkout or unverified toolchain is an open issue,
        # not an automatic permission to build or program a device.
        result["git_clean"] = (
            result["commands"]["git status --porcelain=v1"]["status"] == "OK"
            and result["commands"]["git status --porcelain=v1"]["stdout"] == "")
        result["vivado_version_observed"] = (
            result["commands"]["vivado -version"]["status"] == "OK")
        result["board_identity_observed"] = False
    else:
        for path in (
            "/proc/device-tree/model", "/proc/cmdline", "/proc/meminfo",
            "/etc/os-release", "/proc/version",
        ):
            result["board_files"][path] = reader(Path(path))
        for command in (
            ("uname", "-a"),
            ("xmutil", "listapps"),
            ("xmutil", "boardid"),
            ("xmutil", "bootfw_status"),
            ("xmutil", "platformstats"),
        ):
            result["commands"][" ".join(command)] = runner(command)
        # This is an observation, NOT unloadapp or firmware modification.
        # Some OS images require sudo for xmutil; failures are preserved.
        result["accelerator_inventory_observed"] = (
            result["commands"]["xmutil listapps"]["status"] == "OK")
        model = result["board_files"]["/proc/device-tree/model"]
        result["board_identity_observed"] = (model["status"] == "OK"
                                            and "kv260" in model["text"].lower())
        result["board_linux_boot_observed"] = (
            result["board_files"]["/proc/cmdline"]["status"] == "OK")
        result["fpga_manager_sysfs_present"] = Path(
            "/sys/class/fpga_manager").is_dir()
        result["source_sha256"] = {}
        result["accepted_original_archive_inventory"] = {
            "status": "NOT_SCANNED_BOARD_LOCAL",
            "items": [], "all_sha256_match": False}
    return result


def write_capture(output_dir: Path, report: dict) -> Path:
    """Exclusive fresh folder, restricted permissions; never mutate past evidence."""
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("M08 evidence folder already exists")
    if not output_dir.parent.is_dir():
        raise ValueError("M08 evidence parent must already exist")
    output_dir.mkdir(mode=0o700)
    path = output_dir / "m08_readonly_inventory.json"
    with path.open("x", encoding="utf-8") as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write("\n")
    (output_dir / "m08_readonly_inventory.sha256").write_text(
        sha_file(path) + "  m08_readonly_inventory.json\n",
        encoding="ascii")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("host", "board-local"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--accepted-evidence-dir", type=Path)
    args = parser.parse_args()
    if args.mode == "board-local" and args.accepted_evidence_dir is not None:
        parser.error("accepted archives are checked from the host only")
    os.umask(0o077)
    try:
        report = capture(args.mode, source_root=args.source_root,
                         originals=args.accepted_evidence_dir)
        path = write_capture(args.output_dir, report)
    except (OSError, ValueError) as e:
        print("M08_READONLY_CAPTURE_FAILED:", str(e), file=sys.stderr)
        return 2
    print("M08_READONLY_CAPTURE_RECORDED_NOT_BOARD_ACCEPTANCE", str(path))
    print("M08_INITIAL_BLOCKERS",
          ",".join(report["physical_readiness"]["missing"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
