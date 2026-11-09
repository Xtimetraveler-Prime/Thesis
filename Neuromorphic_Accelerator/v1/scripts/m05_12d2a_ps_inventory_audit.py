"""M05.12d.2a independent audit of *actual* K26 PS IP CATALOG inventory.

A successful transcript checks that discovery was complete, NOT that PS ports
are enabled, clocks are configured, DDR works, or a PS/PL BD is connected.
Native fixtures are synthetic and do NOT substitute genuine Vivado evidence.
"""
from __future__ import annotations
import argparse
from pathlib import Path

PART = "xck26-sfvc784-2LV-c"
SCOPE = "UNCONNECTED_PS_CATALOG_DEFAULTS_NO_PRESET_DDR"
PORTS = {
    "M_AXI_HPM0_FPD": "MASTER", "M_AXI_HPM1_FPD": "MASTER",
    "M_AXI_HPM0_LPD": "MASTER",
    "S_AXI_HP0_FPD": "SLAVE", "S_AXI_HP1_FPD": "SLAVE",
    "S_AXI_HP2_FPD": "SLAVE", "S_AXI_HP3_FPD": "SLAVE",
    "S_AXI_HPC0_FPD": "SLAVE", "S_AXI_HPC1_FPD": "SLAVE",
    "S_AXI_LPD": "SLAVE", "S_AXI_ACP_FPD": "SLAVE",
    "S_AXI_ACE_FPD": "SLAVE",
}
PINS = {
    "pl_clk0": "O", "pl_resetn0": "O", "pl_ps_irq0": "I",
    "maxihpm0_fpd_aclk": "I", "maxihpm1_fpd_aclk": "I",
    "saxihp0_fpd_aclk": "I", "saxihpc0_fpd_aclk": "I",
}
PROPS = (
    "PCW_USE_M_AXI_GP0", "PCW_USE_M_AXI_GP1", "PCW_USE_S_AXI_HP0",
    "PCW_USE_S_AXI_HP1", "PCW_USE_S_AXI_HPC0", "PCW_USE_S_AXI_HPC1",
    "PCW_FPGA0_PERIPHERAL_FREQMHZ", "PCW_EN_CLK0_PORT",
    "PCW_USE_FABRIC_INTERRUPT",
)


def _add(table: dict, key: str, value, allowed, line: int):
    if key not in allowed or key in table:
        raise ValueError(f"unknown/duplicate field {key!r} at {line}")
    table[key] = value


def verify_ps_inventory(transcript: str) -> dict[str, int]:
    if type(transcript) is not str or not transcript.endswith("\n"):
        raise ValueError("missing/truncated PS IP report")
    meta, ports, pins, props = {}, {}, {}, {}
    for number, line in enumerate(transcript.splitlines(), 1):
        fields = line.split("|")
        if len(fields) == 3 and fields[0] == "META":
            _, key, value = fields
            _add(meta, key, value, ("part", "vlnv", "scope", "source_mgmt_mode"), number)
        elif len(fields) == 4 and fields[0] in ("IF", "PIN"):
            kind, name, present, mode = fields
            allowed = PORTS if kind == "IF" else PINS
            target = ports if kind == "IF" else pins
            if name not in allowed:
                raise ValueError(f"unknown PS {kind} name at {number}")
            if present == "0" and mode == "NA":
                pass
            elif present == "1" and mode == allowed[name]:
                pass
            else:
                raise ValueError(f"wrong activation or direction for {name}")
            _add(target, name, present, allowed, number)
        elif len(fields) == 3 and fields[0] == "PROP":
            _, name, value = fields
            if not value or len(value) > 250 or "\r" in value:
                raise ValueError(f"invalid PS property payload at {number}")
            _add(props, name, value, PROPS, number)
        else:
            raise ValueError(f"unexpected record in PS catalog at line {number}")
    if (meta.get("part") != PART or meta.get("scope") != SCOPE
            or meta.get("source_mgmt_mode") != "All"
            or not meta.get("vlnv", "").startswith("xilinx.com:ip:zynq_ultra_ps_e:")
            or len(meta) != 4):
        raise ValueError("wrong part, IP, scope or source-management mode")
    if set(ports) != set(PORTS) or set(pins) != set(PINS) or set(props) != set(PROPS):
        raise ValueError("incomplete PS interfaces, clocks or property inventory")
    return {
        "ps_to_pl_master_defaults": sum(ports[n] == "1" for n in PORTS if PORTS[n] == "MASTER"),
        "pl_to_ps_slave_defaults": sum(ports[n] == "1" for n in PORTS if PORTS[n] == "SLAVE"),
        "pin_defaults": sum(value == "1" for value in pins.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        facts = verify_ps_inventory(args.report.read_text())
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: M05.12d.2a PS catalog audit: {exc}\n")
    print(
        "PASS: M05.12d.2a independently audited Vivado PS CATALOG "
        f"default interface counts {facts} (UNCONNECTED, NOT DDR/PS CONFIGURATION)"
    )


if __name__ == "__main__":
    main()
