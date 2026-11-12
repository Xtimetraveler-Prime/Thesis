#!/usr/bin/env python3
"""D2 owner-PC-only original KV260/M08 DTBO SHA locator, optional decompiler.

Default operation: read-only scanning of known owner PC evidence/repository
folders, exact filename+SHA256 identification. --prepare explicitly creates a
NEW sibling evidence folder and decompiles matched copies with local dtc.
No remote connection, FPGA manager, UIO mapping, register access or board activity.
This can only compare saved DT overlays: not a failed-boot live DT/PS state.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

EXPECTED = {
    "stock": (
        "k26_starter_kits.dtbo",
        "1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1"),
    "m08": (
        "m08-v1-fan-page-uio-review.dtbo",
        "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed"),
}
# K26 archival route/firmware and other large trees are not crawled.
SKIP_DIRS = frozenset({
    ".git", ".venv", ".venv-mnist", ".cache", "__pycache__", "node_modules",
    "Vivado", "Xilinx", ".local", "build", "builds", ".tox", ".mypy_cache",
})
MAX_SCAN_FILES = 100000


class OfflineReject(ValueError):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise OfflineReject(why)


def check_pc() -> None:
    require(platform.system() == "Linux", "Linux owner PC required")
    model = Path("/proc/device-tree/model")
    if model.exists():
        require("KV260" not in model.read_bytes().decode(errors="replace"),
                "M08 D2 DTBO work is prohibited on KV260")


def hash_file(path: Path) -> str:
    value = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def locate(roots: list[Path]) -> dict:
    check_pc()
    found = {"stock": [], "m08": []}
    expected_by_name = {name: (key, digest)
                        for key, (name, digest) in EXPECTED.items()}
    seen = set()
    visited = 0
    for root in roots:
        require(root.is_dir() and not root.is_symlink(),
                "missing/symlinked owner PC search root: " + str(root))
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs
                             if d not in SKIP_DIRS
                             and not (Path(current) / d).is_symlink())
            for name in sorted(files):
                visited += 1
                require(visited <= MAX_SCAN_FILES,
                        "bounded search limit exceeded; narrow --search-root")
                if name not in expected_by_name:
                    continue
                target = Path(current) / name
                if not target.is_file() or target.is_symlink():
                    continue
                normalized = str(target.resolve())
                if normalized in seen:
                    continue
                seen.add(normalized)
                key, expected_sha = expected_by_name[name]
                actual = hash_file(target)
                found[key].append({
                    "path": normalized,
                    "sha256": actual,
                    "matches_original_sha256": actual == expected_sha,
                })
    for key in found:
        found[key].sort(key=lambda x: x["path"])
    return {
        "schema": "m08-d2-owner-pc-original-dtbo-locator-v1",
        "status": "OFFLINE_FILES_ONLY_NOT_FAILED_BOOT_PS_CONFIGURATION",
        "roots": [str(x.resolve()) for x in roots],
        "expected_sha256": {key: val[1] for key, val in EXPECTED.items()},
        "matches": found,
        "all_originals_located": all(any(
            row["matches_original_sha256"] for row in found[key]) for key in EXPECTED),
        "source_dtbo_is_not_applied_device_tree": True,
        "physical_hardware_accessed": False,
        "original_m08_quarantine_active": True,
    }


def receipt(folder: Path) -> None:
    rows = [f"{hash_file(file)}  {file.name}" for file in sorted(folder.iterdir())
            if file.is_file() and file.name != "99_evidence_sha256.txt"]
    (folder / "99_evidence_sha256.txt").write_text("\n".join(rows) + "\n")


def prepare(inspection: dict, base: Path, *, m08_only: bool = False) -> tuple[Path, bool]:
    require(base.is_dir() and not base.is_symlink(),
            "existing, non-symlinked owner PC evidence-base required")
    require(str(base.resolve()) not in ("/", "/boot", "/etc", "/dev",
                                       "/sys", "/proc", "/run"),
            "unsafe evidence output parent")
    selected = {}
    for key in (("m08",) if m08_only else tuple(EXPECTED)):
        options = [x for x in inspection["matches"][key] if x["matches_original_sha256"]]
        require(len(options) == 1,
                "need exactly one original SHA-matched " + key
                + " DTBO; narrow --search-root if duplicates")
        selected[key] = Path(options[0]["path"])
    require(shutil.which("dtc") is not None,
            "dtc is not installed on owner PC (sudo apt install device-tree-compiler)")
    folder = Path(tempfile.mkdtemp(prefix="m08_d2_OWNER_DTBO_OFFLINE_", dir=base.resolve()))
    records = {}
    all_ok = True
    for key, source in selected.items():
        (name, original_sha) = EXPECTED[key]
        require(source.is_file() and not source.is_symlink() and
                source.name == name and hash_file(source) == original_sha,
                "original source DTBO changed after locator: " + key)
        dst = folder / ("11_stock.dts" if key == "stock" else "12_m08.dts")
        result = subprocess.run(
            ["dtc", "-I", "dtb", "-O", "dts", "-o", str(dst), str(source)],
            cwd=folder, text=True, capture_output=True, check=False, timeout=60)
        (folder / ("21_stock_dtc_stderr.txt" if key == "stock"
                   else "22_m08_dtc_stderr.txt")).write_text(result.stderr)
        ok = result.returncode == 0 and dst.is_file() and dst.stat().st_size > 100
        records[key] = {
            "original_path": str(source),
            "original_sha256": original_sha,
            "original_verified_again_after_dtc": hash_file(source) == original_sha,
            "dtc_exit_status": result.returncode,
            "decompiled_file": str(dst) if ok else None,
            "decompiled_sha256": hash_file(dst) if ok else None,
        }
        all_ok &= ok and records[key]["original_verified_again_after_dtc"]
    (folder / "00_review.json").write_text(json.dumps({
        "schema": "m08-d2-owner-pc-dtbo-decompile-v1",
        "status": (("ORIGINAL_M08_DTS_COPY_CREATED_STOCK_ABSENT_NO_BOARD"
                    if m08_only else "ORIGINAL_STOCK_AND_M08_DTS_COPIES_CREATED_NO_BOARD")
                   if all_ok else "DECOMPILATION_FAILED_REVIEW_LOGS_NO_BOARD"),
        "stock_dtbo_compared": not m08_only,
        "m08_only": m08_only,
        "originals_unchanged": all(x["original_verified_again_after_dtc"]
                                   for x in records.values()),
        "files": records,
        "runtime_clock_reset_hpm0_afi_or_atb_verified": False,
        "hardware_retry_authorized": False,
        "original_quarantined_image_reloaded": False,
    }, sort_keys=True, indent=2) + "\n")
    receipt(folder)
    return folder, bool(all_ok)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-root", type=Path, action="append",
                        help="Existing owner PC folder; repeat for multiple search roots")
    parser.add_argument("--m08-only", action="store_true",
                        help="Allow --prepare with only the SHA-verified original M08 DTBO, stock remains unknown")
    parser.add_argument("--prepare", action="store_true",
                        help="Use dtc to decompile two exact SHA-matched originals into NEW owner PC evidence")
    parser.add_argument("--evidence-base", type=Path,
                        default=Path.home() / "Thesis_Evidence" / "M08",
                        help="Existing owner PC evidence parent (only with --prepare)")
    args = parser.parse_args()
    roots = args.search_root or [
        Path.home() / "Thesis_Evidence" / "M08",
        Path.home() / "Git" / "Thesis",
    ]
    try:
        require(not args.m08_only or args.prepare, "--m08-only requires --prepare")
        result = locate(roots)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.prepare:
            folder, accepted = prepare(result, args.evidence_base, m08_only=args.m08_only)

            print("M08_D2_OFFLINE_DTBO_EVIDENCE_DIR=" + str(folder))
            print("M08_D2_OFFLINE_DTBO_DECOMPILATION=" + (
                "COMPLETE_NOT_RUNTIME_PROOF" if accepted else "FAILED_REVIEW_LOGS"))
            return 0 if accepted else 3
        return 0
    except (OfflineReject, OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print("M08_D2_OFFLINE_DTBO_REJECTED_NO_BOARD: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
