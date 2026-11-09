"""Read-only M05.12c audit of actual Vivado 2025.2 IP readbacks.

Native tests are synthetic: neither the parser nor its CI prove configured IP,
a connected block diagram, AXI DMA transfers, PS, DDR, timing or hardware.
"""
from __future__ import annotations
import argparse
from pathlib import Path

PART = "xck26-sfvc784-2LV-c"
VLNV = "xilinx.com:ip:axi_dma:7.1"
SCOPE = "UNCONNECTED_OFFLINE_CANDIDATE_NO_PS_DDR"
ROLES = {"dma_neurons": "MM2S", "dma_synapses": "MM2S",
         "dma_external": "MM2S", "dma_trace": "S2MM"}
PINS = ("M_AXIS_MM2S", "S_AXIS_S2MM", "M_AXI_MM2S", "M_AXI_S2MM", "S_AXI_LITE")
COMMON = {"c_include_sg": "0", "c_sg_length_width": "24",
          "c_addr_width": "32", "c_prmry_is_aclk_async": "0",
          "c_micro_dma": "0", "c_include_mm2s_dre": "0",
          "c_include_s2mm_dre": "0"}


def expected_config(role: str) -> dict[str, str]:
    if role not in ("MM2S", "S2MM"):
        raise ValueError("unexpected DMA direction")
    return {**COMMON,
            "c_include_mm2s": "1" if role == "MM2S" else "0",
            "c_include_s2mm": "1" if role == "S2MM" else "0",
            **({"c_m_axi_mm2s_data_width": "256",
                "c_m_axis_mm2s_tdata_width": "256"} if role == "MM2S"
               else {"c_m_axi_s2mm_data_width": "256",
                     "c_s_axis_s2mm_tdata_width": "256"})}


def expected_pins(role: str) -> dict[str, str]:
    return {pin: str(int(pin == "S_AXI_LITE" or
                         (role == "MM2S" and pin in ("M_AXIS_MM2S", "M_AXI_MM2S")) or
                         (role == "S2MM" and pin in ("S_AXIS_S2MM", "M_AXI_S2MM"))))
            for pin in PINS}


def verify_candidate_report(report: str) -> tuple[int, int]:
    if not report.endswith("\n"):
        raise ValueError("partial report / missing newline")
    metadata = {}
    roles = {}
    configs = {name: {} for name in ROLES}
    pins = {name: {} for name in ROLES}
    for i, line in enumerate(report.splitlines(), 1):
        items = line.split("|")
        if len(items) == 3 and items[0] == "META":
            _, key, value = items
            if key not in ("part", "vlnv", "scope") or key in metadata:
                raise ValueError(f"unknown/duplicate metadata {i}")
            metadata[key] = value
        elif len(items) == 3 and items[0] == "CELL":
            _, name, role = items
            if name not in ROLES or name in roles:
                raise ValueError(f"unknown/duplicate DMA instance {i}")
            roles[name] = role
        elif len(items) == 4 and items[0] in ("CFG", "PIN"):
            tag, name, key, value = items
            if name not in roles or name not in ROLES:
                raise ValueError(f"property before/without DMA instance {i}")
            expected = expected_config(ROLES[name]) if tag == "CFG" else expected_pins(ROLES[name])
            bucket = configs[name] if tag == "CFG" else pins[name]
            if key not in expected or key in bucket:
                raise ValueError(f"unknown/duplicate property or pin {i}")
            bucket[key] = value
        else:
            raise ValueError(f"malformed Vivado report {i}")
    if metadata != {"part": PART, "vlnv": VLNV, "scope": SCOPE}:
        raise ValueError("part, IP, scope or metadata mismatch")
    if roles != ROLES:
        raise ValueError("incorrect number/direction of DMA instances")
    for name, role in ROLES.items():
        if configs[name] != expected_config(role) or pins[name] != expected_pins(role):
            raise ValueError(f"wrong width, length, direct mode or pins on {name}")
    return 3, 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify_candidate_report(args.report.read_text())
    except (OSError, ValueError) as err:
        p.exit(1, f"ERROR: M05.12c Vivado candidate audit: {err}\n")
    print(f"PASS: M05.12c independent readback MM2S={result[0]} S2MM={result[1]} "
          "256-bit length24 direct SG0, unconnected offline (NOT PS/DDR/DMA/board)")


if __name__ == "__main__":
    main()
