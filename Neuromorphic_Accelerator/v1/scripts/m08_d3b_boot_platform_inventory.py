#!/usr/bin/env python3
"""D3.2B.1 bounded PC-filesystem provenance inventory; never a hardware gate.

Only walks explicitly bounded local directories; hashes candidate *regular*
files without unpacking/running them. BOOT.BIN is listed as metadata only.
No FPGA, Linux devices, firmware tooling, register access or deployment.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_BASE = Path.home() / "Thesis_Evidence" / "M08"
SCHEMA = "m08-d3b-b1-pc-boot-platform-inventory-v1"
MARKER = "M08_D3B_B1_PC_INVENTORY_RECORDED_HARDWARE_BLOCKED"
PINNED = {
    "k26_starter_kits.dtbo":
        "1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1",
    "m08-v1-fan-page-uio-review.dtbo":
        "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed",
}
EXCLUDED_DIRS = frozenset({
    ".git", ".cache", ".Xil", ".venv", "venv", "__pycache__",
    "node_modules", "site-packages", ".tox", "ip_cache", "ip_user_files",
})
PROHIBITED_ROOTS = {"/", "/home", "/mnt", "/tmp", "/var", "/opt",
                    "/dev", "/proc", "/sys", "/run"}


class InventoryRejected(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise InventoryRejected(reason)


def no_symlink_ancestors(path: Path) -> Path:
    """Absolute, without resolve(): resolving first would conceal symlinks."""
    full = path.expanduser().absolute()
    for node in (full, *full.parents):
        if node.is_symlink():
            raise InventoryRejected("symlinked path component: " + str(node))
    return full


def validate_root(path: Path, *, optional: bool = False) -> Path | None:
    full = no_symlink_ancestors(path)
    require(str(full) not in PROHIBITED_ROOTS
            and full != Path.home().absolute()
            and len(full.parts) >= 4,
            "overbroad scan root: " + str(full))
    if not full.exists() and optional:
        return None
    require(full.is_dir(), "missing or non-directory scan root: " + str(full))
    return full


def validate_owner_extra(path: Path) -> Path:
    root = validate_root(path)
    home = no_symlink_ancestors(Path.home())
    require(root.is_relative_to(home), "extra-dir must be beneath owner PC HOME")
    cursor = root
    while cursor != home:
        require(not cursor.is_mount(),
                "extra-dir cannot be a mounted device or filesystem")
        cursor = cursor.parent
    return root


def category(name: str) -> str | None:
    n = name.lower()
    if n.endswith(".xsa"):
        return "XSA_HARDWARE_EXPORT_UNATTESTED"
    if n in ("psu_init.c", "psu_init.tcl", "psu_init.h", "psu_init_gpl.c"):
        return "GENERATED_PS_INIT_SOURCE_UNATTESTED"
    if n in ("boot.bin", "image.ub", "boot.pdi"):
        return "BOOT_PACKAGE_METADATA_ONLY"
    if n in ("fsbl.elf", "zynqmp_fsbl.elf", "pmufw.elf", "pmu_fw.elf",
             "bl31.elf", "u-boot.elf", "u-boot.bin"):
        return "BOOT_COMPONENT_BINARY_UNATTESTED"
    if n.endswith((".dtb", ".dtbo")):
        return "DEVICE_TREE_BINARY_UNAPPLIED"
    if n.endswith((".dts", ".dtsi")):
        return "DEVICE_TREE_SOURCE_UNAPPLIED"
    if n.endswith((".bif", ".bb", ".bbappend")):
        return "BOOT_BUILD_RECIPE_UNATTESTED"
    if n.endswith((".json", ".yaml", ".yml", ".txt", ".log", ".manifest")) and any(
        term in n for term in
        ("boot", "fsbl", "pmu", "firmware", "manifest", "vivado",
         "dfx", "kernel", "device_tree", "devicetree", "psu_init")
    ):
        return "PLATFORM_LOG_OR_MANIFEST_UNATTESTED"
    return None


def sha_regular_file(path: Path, before: os.stat_result) -> str:
    """No-follow open plus before/after stat: reject races and special files."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        started = os.fstat(fd)
        require(stat.S_ISREG(started.st_mode)
                and started.st_dev == before.st_dev
                and started.st_ino == before.st_ino
                and started.st_size == before.st_size,
                "candidate changed before hash: " + str(path))
        digest = sha256()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        finished = os.fstat(fd)
        require((finished.st_dev, finished.st_ino, finished.st_size,
                 finished.st_mtime_ns) ==
                (started.st_dev, started.st_ino, started.st_size,
                 started.st_mtime_ns),
                "candidate changed during hash: " + str(path))
        return digest.hexdigest()
    finally:
        os.close(fd)


def inventory(roots: list[tuple[str, Path]], *,
              max_entries: int = 12000, max_depth: int = 7,
              max_hash_bytes: int = 256 * 1024 * 1024,
              exclude_dir: Path | None = None) -> dict:
    require(1 <= max_entries <= 50000 and 1 <= max_depth <= 12
            and 1024 <= max_hash_bytes <= 4 * 1024**3,
            "unbounded inventory limits")
    candidates: list[dict] = []
    inspected = 0
    omitted_depth = 0
    omitted_symlinks = 0
    omitted_large_hashes = 0
    seen: set[Path] = set()
    present_roots = []
    missing_roots = []
    for label, root_path in roots:
        root = validate_root(root_path, optional=(label == "owner_m08_evidence"))
        if root is None:
            missing_roots.append({"label": label, "path": str(root_path)})
            continue
        present_roots.append({"label": label, "path": str(root)})
        stack = [(root, 0)]
        while stack:
            folder, depth = stack.pop()
            with os.scandir(folder) as it:
                entries = sorted(it, key=lambda entry: entry.name)
            for ent in entries:
                inspected += 1
                require(inspected <= max_entries,
                        "inventory entry limit exceeded; choose narrower folders")
                path = Path(ent.path)
                if ent.is_symlink():
                    omitted_symlinks += 1
                    continue
                # Do not touch a newly allocated receipt directory, even if
                # the output is nested under the default evidence root.
                if exclude_dir is not None and path == exclude_dir:
                    continue
                if ent.is_dir(follow_symlinks=False):
                    if ent.name in EXCLUDED_DIRS:
                        continue
                    if depth >= max_depth:
                        omitted_depth += 1
                        continue
                    stack.append((path, depth + 1))
                    continue
                if not ent.is_file(follow_symlinks=False) or path in seen:
                    continue
                seen.add(path)
                cls = category(ent.name)
                if cls is None:
                    continue
                st = ent.stat(follow_symlinks=False)
                require(stat.S_ISREG(st.st_mode),
                        "non-regular candidate refused")
                metadata_only = cls == "BOOT_PACKAGE_METADATA_ONLY"
                skipped_large = st.st_size > max_hash_bytes
                digest = None if metadata_only or skipped_large else sha_regular_file(path, st)
                if skipped_large:
                    omitted_large_hashes += 1
                pin = PINNED.get(ent.name.lower())
                if pin is not None and digest is not None:
                    require(digest == pin,
                            "pinned original SHA256 mismatch: " + str(path))
                elif pin is not None:
                    require(False, "pinned original not hashable: " + str(path))
                candidates.append({
                    "root_label": label,
                    "path": str(path),
                    "relative_path": str(path.relative_to(root)),
                    "evidence_class": cls,
                    "size_bytes": st.st_size,
                    "sha256": digest,
                    "hash_policy": ("BOOT_PACKAGE_METADATA_ONLY_NO_BYTES_READ"
                                    if metadata_only else
                                    "SKIPPED_SIZE_LIMIT" if skipped_large else
                                    "SHA256_STREAMED_REGULAR_FILE"),
                    "pinned_original_digest_match": pin is not None,
                    "provenance": ("PINNED_ORIGINAL_FILENAME_AND_BYTES_ONLY"
                                   if pin is not None else
                                   "LOCAL_FILE_PATH_AND_BYTES_ONLY_UNATTESTED"),
                    "boot_component_version": "UNKNOWN",
                    "deployed_or_applied": "UNKNOWN",
                    "ps_runtime_configuration_proven": False,
                })
    candidates.sort(key=lambda row: (row["root_label"], row["relative_path"], row["path"]))
    found = {Path(c["path"]).name.lower() for c in candidates}
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_PC_CANDIDATES_ONLY_NO_BOOT_OR_HARDWARE_PROOF",
        "roots_scanned": present_roots,
        "optional_roots_missing": missing_roots,
        "limits": {"max_entries": max_entries, "max_depth": max_depth,
                   "max_hash_bytes_per_file": max_hash_bytes},
        "coverage": {"entries_seen": inspected, "depth_pruned": omitted_depth,
                     "symlinks_ignored": omitted_symlinks,
                     "size_limited_hashes": omitted_large_hashes},
        "candidates": candidates,
        "pinned_originals": {
            name: {"expected_sha256": digest,
                   "status": ("LOCAL_PATH_AND_SHA256_MATCH_NOT_BOOT_PROOF"
                              if name in found else "NOT_FOUND_IN_BOUNDED_SCAN_UNKNOWN")}
            for name, digest in PINNED.items()
        },
        "evidence_semantics": {
            "xsa_or_ps_init_is_runtime_register_readback": False,
            "vivado_ps_preset_is_boot_firmware_owner_proof": False,
            "stock_dtbo_is_base_dtb": False,
            "dts_or_dtbo_is_applied_device_tree": False,
            "boot_package_filename_proves_booted_firmware": False,
        },
        "blocked_requirements": {
            key: "UNKNOWN_NOT_PROVEN" for key in (
                "ATB4_boot_enable_response_timeout_clock",
                "AIB13_isolation_ack_and_outstanding_quiescence",
                "PL0_REF_CTRL_boot_and_runtime_owner",
                "pl_resetn0_boot_and_runtime_owner",
                "HPM0_128_bit_AFI_boot_config",
                "Linux_base_and_applied_device_tree",
                "FPGA_region_driver_and_mapping_order",
                "independent_fan_cooling_and_stock_rollback",
            )
        },
        "original_m08_bit_bin_sha256_quarantined":
            "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b",
        "original_m08_image_quarantined": True,
        "atb4_hardware_proven": False,
        "aib13_hardware_proven": False,
        "linux_clock_afi_proven": False,
        "hardware_mmio_authorized": False,
        "physical_programming_authorized": False,
        "proceed_to_d3b5_native_hpm0": False,
    }


def write_receipt(out_dir: Path, report: dict) -> tuple[Path, Path]:
    out = no_symlink_ancestors(out_dir)
    require(out.is_dir() and not any(out.iterdir()),
            "output directory must exist, be NEW and EMPTY")
    report_path = out / "00_boot_platform_inventory.json"
    receipt_path = out / "99_evidence_sha256.txt"
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    for path, content in (
        (report_path, data),
        (receipt_path,
         (sha256(data).hexdigest() + "  " + report_path.name + "\n").encode()),
    ):
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
    return report_path, receipt_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extra-dir", action="append", type=Path, default=[],
                    help="Additional narrow OWNER-PC directory; no board mounts")
    ap.add_argument("--out-dir", required=True, type=Path,
                    help="Existing EMPTY unique folder under ~/Thesis_Evidence/M08")
    ap.add_argument("--max-entries", type=int, default=12000)
    ap.add_argument("--max-depth", type=int, default=7)
    args = ap.parse_args()
    try:
        base = validate_root(DEFAULT_EVIDENCE_BASE, optional=True)
        require(base is not None, "create ~/Thesis_Evidence/M08 on the PC first")
        out = no_symlink_ancestors(args.out_dir)
        require(out.parent == base and out.name.startswith("m08_d3b_b1_inventory_"),
                "receipt output must be a new sibling under owner evidence base")
        roots = [("repository_v1", ROOT), ("owner_m08_evidence", base)]
        for i, folder in enumerate(args.extra_dir):
            roots.append(("owner_extra_" + str(i + 1), validate_owner_extra(folder)))
        scanned = inventory(roots, max_entries=args.max_entries,
                            max_depth=args.max_depth, exclude_dir=out)
        report, receipt = write_receipt(out, scanned)
    except (InventoryRejected, OSError, ValueError) as exc:
        print("M08_D3B_B1_INVENTORY_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"status": MARKER, "report": str(report),
                      "receipt": str(receipt),
                      "candidate_count": len(scanned["candidates"]),
                      "hardware_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
