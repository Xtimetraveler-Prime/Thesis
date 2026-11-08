"""Derive M05 RTL stress-test AXI-Lite addresses from the real Vitis driver.

Never assume 0x10/0x18/... across tool releases. The generated *_hw.h is
the authority for this one HLS build. This tool is read-only except for a
new (exclusive) output .svh in the separate evidence directory.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re


REQUIRED = (
    "AP_CTRL", "NEURON_COUNT_DATA", "SYNAPSE_COUNT_DATA",
    "EXTERNAL_COUNT_DATA", "TICKS_DATA", "DECAY_NUM_DATA",
    "DECAY_DEN_DATA", "AP_RETURN",
)


def parse_registers(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(
            r"^\s*#define\s+[A-Za-z0-9_]+_CONTROL_ADDR_"
            r"([A-Z0-9_]+)\s+(0[xX][0-9A-Fa-f]+)\b", line
        )
        if not match:
            continue
        name, value = match.groups()
        if name not in REQUIRED:
            continue
        if name in result:
            raise ValueError(f"duplicate AXI-Lite register: {name}")
        result[name] = int(value, 16)
    missing = set(REQUIRED) - result.keys()
    if missing:
        raise ValueError("HLS driver lacks required register offsets: "
                         + ", ".join(sorted(missing)))
    values = list(result.values())
    if len(set(values)) != len(values):
        raise ValueError("register offsets collide")
    if result["AP_CTRL"] != 0:
        raise ValueError("unexpected ap_ctrl register offset")
    if any(not 0 <= v < 128 or v % 4 for v in values):
        raise ValueError("register offset exceeds 7-bit AXI-Lite address bus")
    return result


def format_svh(mapping: dict[str, int]) -> str:
    preface = [
        "// GENERATED FROM ACTUAL VITIS 2025.2 DRIVER HEADER.",
        "// Source-only simulation parameters; not manually guessed register map.",
        "// To regenerate use scripts/m05_axis_regmap.py.",
    ]
    for name in REQUIRED:
        preface.append(f"`define M05_ADDR_{name} 7'h{mapping[name]:02x}")
    return "\n".join(preface) + "\n"


def find_header(impl_root: Path) -> Path:
    root = impl_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("implementation evidence must be a directory")
    paths = list(root.glob("work/**/xm05_rolling_replay_hw.h"))
    if not paths:
        paths = list(root.glob("work/**/*m05_rolling_replay*_hw.h"))
    if not paths:
        raise ValueError("generated *_hw.h control map missing; "
                         "inspect work/hls/impl/ip/drivers and exported IP")
    parsed = {}
    for path in paths:
        try:
            mapping = parse_registers(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        parsed.setdefault(tuple(sorted(mapping.items())), []).append(path)
    if not parsed:
        raise ValueError("found HLS headers but none has a complete register map")
    if len(parsed) != 1:
        raise ValueError("conflicting HLS register maps across driver headers")
    return sorted(next(iter(parsed.values())))[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--impl-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    header = find_header(args.impl_evidence)
    contents = format_svh(parse_registers(header.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        out.write(contents)
    print(f"PASS: derived AXI-Lite register offsets from {header}")
    print(f"PASS: wrote unique simulation include {args.output}")


if __name__ == "__main__":
    main()
