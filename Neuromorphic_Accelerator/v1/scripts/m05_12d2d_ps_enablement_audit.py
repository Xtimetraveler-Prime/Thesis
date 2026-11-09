"""M05.12d.2d independent real-Vivado report audit, NOT PS/DDR proof.

The true verification gate checks both PS CONFIG and actual BD interface pins.
Synthetic native tests cannot certify Vivado/PS/DDRx. No physical driver.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

META = {
    "part": "xck26-sfvc784-2LV-c",
    "vlnv": "xilinx.com:ip:zynq_ultra_ps_e:3.5",
    "source_mgmt_mode": "All",
    "scope": "SCRATCH_PS_PORT_ENABLE_ONLY_NO_PRESET_DDR",
}
DEFAULT = {"PSU__USE__M_AXI_GP0": "0", "PSU__USE__S_AXI_GP2": "0"}
READBACK = {
    "PSU__USE__M_AXI_GP0": "1",
    "PSU__USE__S_AXI_GP2": "1",
    "PSU__USE__M_AXI_GP2": "1",
}
BEFORE = {
    "M_AXI_HPM0_FPD": ("0", "NA"),
    "S_AXI_HP0_FPD": ("0", "NA"),
    "M_AXI_HPM0_LPD": ("1", "MASTER"),
}
AFTER = {
    "M_AXI_HPM0_FPD": ("1", "MASTER"),
    "S_AXI_HP0_FPD": ("1", "SLAVE"),
    "M_AXI_HPM0_LPD": ("1", "MASTER"),
}
PIN = {
    "pl_clk0": ("1", "O"),
    "pl_resetn0": ("1", "O"),
    "maxihpm0_fpd_aclk": ("1", "I"),
    "saxihp0_fpd_aclk": ("1", "I"),
}
WIDTH = {
    "PSU__MAXIGP0__DATA_WIDTH": "128",
    "PSU__SAXIGP2__DATA_WIDTH": "128",
}
CLOCKCFG = (
    "PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ",
    "PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ",
)


def audit_trial(report: str) -> dict[str, object]:
    if type(report) is not str or not report.endswith("\n") or len(report) > 32768:
        raise ValueError("incomplete/oversized D2d evidence")
    expected = {
        "META": META, "DEFAULT": DEFAULT, "READBACK": READBACK,
        "BEFORE": BEFORE, "AFTER": AFTER, "PIN": PIN,
        "WIDTH": WIDTH, "CLOCKCFG": {k: None for k in CLOCKCFG},
    }
    found: dict[str, dict] = {k: {} for k in expected}
    for i, row in enumerate(report.splitlines(), 1):
        parts = row.split("|")
        kind = parts[0]
        if kind not in expected or len(parts) != (4 if kind in ("BEFORE", "AFTER", "PIN") else 3):
            raise ValueError(f"unexpected D2d record at {i}")
        key = parts[1]
        group = found[kind]
        if key not in expected[kind] or key in group:
            raise ValueError(f"unknown/duplicate D2d {kind} {key} at {i}")
        value = tuple(parts[2:]) if kind in ("BEFORE", "AFTER", "PIN") else parts[2]
        if kind == "CLOCKCFG":
            try:
                number = Decimal(value)
            except (InvalidOperation, TypeError) as e:
                raise ValueError(f"invalid clock property {key}") from e
            if not number.is_finite() or number <= 0 or number > 1000:
                raise ValueError(f"impossible positive PS clock value {key}")
        elif value != expected[kind][key]:
            raise ValueError(f"wrong D2d {kind} actual readback for {key}: {value}")
        group[key] = value
    for kind, table in expected.items():
        if set(found[kind]) != set(table):
            raise ValueError(f"missing D2d {kind} fields")
    return {
        "fpm_master_enabled": "M_AXI_HPM0_FPD",
        "hp_memory_slave_enabled": "S_AXI_HP0_FPD",
        "master_width_bits": 128,
        "slave_width_bits": 128,
        "pl_clock_request_mhz": found["CLOCKCFG"][CLOCKCFG[0]],
        "pl_clock_ip_actual_mhz": found["CLOCKCFG"][CLOCKCFG[1]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        facts = audit_trial(args.report.read_text())
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: M05.12d.2d PS enablement audit: {exc}\n")
    print(
        "PASS: M05.12d.2d independent K26 PS interface configuration trial "
        "HPM0_FPD MASTER + HP0_FPD SLAVE both 128bit (NO PRESET/DDR/BOARD)"
    )
    print(f"PS_CLOCK_REQUEST_MHZ={facts['pl_clock_request_mhz']}")
    print(f"PS_CLOCK_IP_ACTUAL_MHZ={facts['pl_clock_ip_actual_mhz']}")


if __name__ == "__main__":
    main()
