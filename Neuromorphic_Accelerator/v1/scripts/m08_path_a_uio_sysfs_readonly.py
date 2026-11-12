#!/usr/bin/env python3
"""M08.2b: READ-ONLY named UIO sysfs mapping inspector for KV260.

Zero device opens, memory mapping, register reads/writes, driver or FPGA
changes. 'present' only proves sysfs metadata, NOT bus correctness.
No fixed /dev/uioX assumptions; each name and physical map must agree.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

REGIONS = {
    "m08-identity": (0xA0000000, 0x1000),
    "m08-page": (0xA0001000, 0x1000),
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def read_text(path: Path) -> str:
    require(path.is_file(), f"missing read-only sysfs attribute {path}")
    return path.read_text(encoding="utf-8").strip()


def read_uint(path: Path) -> int:
    text = read_text(path)
    try:
        value = int(text, 0)
    except ValueError as e:
        raise ValueError(f"invalid numeric sysfs attribute {path}") from e
    require(0 <= value <= 0xFFFFFFFFFFFFFFFF, f"out-of-range sysfs attribute {path}")
    return value


def overlap(a: int, an: int, b: int, bn: int) -> bool:
    return a < b + bn and b < a + an


def inventory(sysfs_root: Path, expected: str = "absent") -> dict:
    """Inspect only sysfs metadata. An installed PL may still be unresponsive."""
    require(expected in ("absent", "present"), "invalid expected UIO state")
    require(sysfs_root.is_dir(), "UIO sysfs directory missing; no fallback to raw memory")
    devices = []
    for item in sorted(sysfs_root.iterdir(), key=lambda p: p.name):
        if not re.fullmatch(r"uio[0-9]+", item.name):
            continue
        require(item.is_dir(), "UIO device sysfs entry is not a directory")
        name = read_text(item / "name")
        maps = item / "maps"
        require(maps.is_dir(), "UIO maps sysfs directory missing")
        data = []
        for entry in sorted(maps.iterdir(), key=lambda p: p.name):
            if not re.fullmatch(r"map[0-9]+", entry.name):
                continue
            address, size = (
                read_uint(entry / "addr"),
                read_uint(entry / "size"),
            )
            require(size > 0 and address + size <= 0x10000000000000000,
                    f"invalid UIO mapping: {item.name}/{entry.name}")
            data.append({
                "map_index": int(entry.name[3:]),
                "physical_base": f"0x{address:016x}",
                "bytes": size,
            })
        devices.append({
            "uio": item.name,
            "name": name,
            "maps": data,
        })

    matches = {}
    for dev in devices:
        for name, (address, length) in REGIONS.items():
            for mmap in dev["maps"]:
                base = int(mmap["physical_base"], 16)
                size = mmap["bytes"]
                if not overlap(base, size, address, length):
                    continue
                require(dev["name"] == name and base == address and size == length
                        and mmap["map_index"] == 0,
                        f"unexpected UIO mapping overlaps {name}: {dev['uio']} ({dev['name']})")
                require(name not in matches,
                        f"duplicate UIO mapping claims {name}")
                matches[name] = dev["uio"]
    for dev in devices:
        if dev["name"] in REGIONS:
            name = dev["name"]
            require(matches.get(name) == dev["uio"] and len(dev["maps"]) == 1,
                    f"named M08 UIO device missing its exact single map0: {name}")

    if expected == "absent":
        require(not matches, "M08 UIO unexpectedly present before approved PL deployment")
    else:
        require(set(matches) == set(REGIONS),
                "both separately mapped M08 UIO devices are required")

    return {
        "schema": "m08-kv260-uio-sysfs-discovery-v1",
        "status": "UIO_SYSFS_METADATA_INSPECTED_NO_MMIO",
        "expected": expected,
        "existing_devices": devices,
        "m08_bindings": matches,
        "physical_fpga_programming": "NOT_PERFORMED_BY_THIS_TOOL",
        "register_readback": "NOT_PERFORMED",
        "driver_behavior": "NOT_VERIFIED",
        "fan_continuity": "NOT_VERIFIED",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sysfs-root", type=Path,
                    default=Path("/sys/class/uio"))
    ap.add_argument("--expected", choices=("absent", "present"),
                    default="absent")
    args = ap.parse_args()
    try:
        result = inventory(args.sysfs_root, args.expected)
    except (ValueError, OSError) as e:
        print("M08_UIO_SYSFS_DISCOVERY_REJECTED:", e, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
