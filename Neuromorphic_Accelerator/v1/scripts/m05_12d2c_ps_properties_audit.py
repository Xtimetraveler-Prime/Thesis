"""M05.12d.2c independent fail-closed PS property catalog report parser.

Genuine original Vivado evidence proves only queried config PROPERTY NAMES and
DEFAULT values exist; it does not prove a PS preset, enabled DDR or PS boot.
All native test fixtures are synthetic; no actual IP is used in CI.
"""
from __future__ import annotations
import argparse
import base64
import binascii
from pathlib import Path
import re

PART = "xck26-sfvc784-2LV-c"
SCOPE = "UNCONFIGURED_K26_PS_PROPERTY_CATALOG_NO_PRESET_OR_DDR"
KEY_RE = re.compile(
    r"^PSU__(?:USE__|CRL_APB__PL0_REF_CTRL__|FPGA_PL0_ENABLE|MAXIGP|SAXIGP)[A-Za-z0-9_]*$"
)
TARGETS = (
    "PSU__USE__M_AXI_GP0", "PSU__USE__M_AXI_GP1",
    "PSU__USE__M_AXI_GP2",
    "PSU__USE__S_AXI_GP0", "PSU__USE__S_AXI_GP1",
    "PSU__USE__S_AXI_GP2", "PSU__USE__S_AXI_GP3",
    "PSU__USE__S_AXI_GP4", "PSU__USE__S_AXI_GP5",
    "PSU__USE__S_AXI_GP6", "PSU__USE__IRQ0",
    "PSU__USE__FABRIC__RST",
    "PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ",
    "PSU__FPGA_PL0_ENABLE",
)


def verify_ps_property_report(raw: str) -> dict[str, object]:
    if type(raw) is not str or not raw.endswith("\n"):
        raise ValueError("incomplete original Vivado property report")
    if len(raw) > 400000:
        raise ValueError("unbounded PS report")
    meta: dict[str, str] = {}
    targets: dict[str, int] = {}
    values: dict[str, str] = {}
    for lineno, line in enumerate(raw.splitlines(), 1):
        fields = line.split("|")
        if len(fields) != 3:
            raise ValueError(f"malformed line {lineno}")
        kind, key, value = fields
        if kind == "META":
            if key not in {"part", "vlnv", "scope", "source_mgmt_mode",
                           "property_count"} or key in meta:
                raise ValueError(f"unexpected/duplicate metadata at {lineno}")
            meta[key] = value
        elif kind == "TARGET":
            if key not in TARGETS or key in targets or value not in ("0", "1"):
                raise ValueError(f"missing/duplicate or incorrect target at {lineno}")
            targets[key] = int(value)
        elif kind == "PROP":
            if not KEY_RE.fullmatch(key) or key in values:
                raise ValueError(f"unknown/duplicate PS property at {lineno}")
            if value == "~":
                decoded = ""
            else:
                try:
                    payload = base64.b64decode(value, validate=True)
                    decoded = payload.decode("utf-8")
                except (UnicodeDecodeError, ValueError, binascii.Error) as exc:
                    raise ValueError(f"invalid base64 PS value at {lineno}") from exc
                if len(payload) > 4096 or not payload or base64.b64encode(payload).decode("ascii") != value:
                    raise ValueError(f"noncanonical/oversized PS value at {lineno}")
            if any(ord(c) < 32 for c in decoded):
                raise ValueError(f"control characters in PS value at {lineno}")
            values[key] = decoded
        else:
            raise ValueError(f"unexpected line type {lineno}")
    if meta != {
        "part": PART, "vlnv": meta.get("vlnv"),
        "scope": SCOPE, "source_mgmt_mode": "All",
        "property_count": str(len(values)),
    } or not re.fullmatch(r"xilinx\.com:ip:zynq_ultra_ps_e:\d+(?:\.\d+)*", meta.get("vlnv", "")):
        raise ValueError("wrong K26/PS IP/scope/source management/property count")
    if len(values) < 1 or len(values) > 1024 or set(targets) != set(TARGETS):
        raise ValueError("missing or oversized PS property catalog/target coverage")
    # Match Tcl's default "lsort" (case-sensitive/code-point ordering).
    # "PSU__USE__STM" precedes "PSU__USE__S_AXI_ACE" in the original
    # owner Vivado 2025.2 report. casefold/lower would wrongly reverse them.
    if list(values) != sorted(values):
        raise ValueError("property records not sorted as the original Tcl contract")
    for key, enabled in targets.items():
        if enabled != int(key in values):
            raise ValueError(f"target presence contradicts actual PS property catalog: {key}")
    return {
        "property_count": len(values),
        "targets_present": sum(targets.values()),
        "target_values": {
            key: (values[key] if key in values else None)
            for key in TARGETS
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        status = verify_ps_property_report(args.report.read_text())
    except (OSError, ValueError) as exc:
        p.exit(1, f"ERROR: M05.12d.2c PS property catalog audit: {exc}\n")
    print(
        "PASS: M05.12d.2c independent K26 PS CONFIG catalog audit "
        f"properties={status['property_count']} candidate_keys_found={status['targets_present']} "
        "(UNCONFIGURED IP, NO PS PRESET/DDR/BOARD)"
    )
    for key, value in status["target_values"].items():
        print(f"TARGET_DEFAULT|{key}|{value if value is not None else 'ABSENT'}")


if __name__ == "__main__":
    main()
