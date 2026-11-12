#!/usr/bin/env python3
"""M08 D2 PC-only source-contract audit: PS HPM0 and Linux DT clock/AFI.

Pure read-only inspection of repo source and OPTIONAL already-collected
owner PC device tree decompilations. Does not query/read/write board registers,
open UIO, invoke SSH, generate/load firmware or authorize new MMIO.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BD = "scripts/m08_page_ps_bd_candidate.tcl"
UIO = "scripts/m08_path_a_stage_uio_overlay.py"
FAN = "scripts/m08_path_a_fan_bd_candidate.tcl"
CLOCK_KEYS = ("assigned-clocks", "assigned-clock-rates",
              "clock-names", "clocks")
AFI_KEYS = ("xlnx,afi-fpga", "config-afi")
SOURCE_PATHS = (BD, UIO, FAN)


class ContractRejected(ValueError):
    pass


def demand(condition: bool, message: str) -> None:
    if not condition:
        raise ContractRejected(message)


def read_original(path: Path) -> tuple[str, str]:
    demand(path.is_file() and not path.is_symlink(),
           "source or optional original DTS absent/symlinked: " + str(path))
    raw = path.read_bytes()
    demand(len(raw) >= 100, "implausibly short original source: " + str(path))
    return raw.decode("utf-8"), sha256(raw).hexdigest()


def extract_literal_dts(src: str) -> str:
    # Read a Python constant AST node, never import/execute staging code.
    tree = ast.parse(src)
    candidates = []
    for statement in tree.body:
        if (isinstance(statement, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "DTS"
                        for t in statement.targets)):
            demand(isinstance(statement.value, ast.Constant)
                   and isinstance(statement.value.value, str),
                   "UIO DTS is no longer a static Python source literal")
            candidates.append(statement.value.value)
    demand(len(candidates) == 1, "M08 overlay must have exactly one static DTS literal")
    return candidates[0]


def feature_matrix(dts: str) -> dict:
    return {
        "assigned_clocks": bool(re.search(r"\bassigned-clocks\s*=", dts)),
        "assigned_clock_rates": bool(re.search(r"\bassigned-clock-rates\s*=", dts)),
        "pl_clock_consumer_clocks": bool(re.search(r"(?<![A-Za-z0-9_-])clocks\s*=", dts)),
        "pl_clock_consumer_clock_names": bool(re.search(r"\bclock-names\s*=", dts)),
        "afi_fabric_config_node": '"xlnx,afi-fpga"' in dts,
        "afi_programming_properties": bool(re.search(r"\bconfig-afi\s*=", dts)),
    }


def audit(root: Path = ROOT, stock_dts: Path | None = None,
          deployed_dts: Path | None = None) -> dict:
    files, digest = {}, {}
    for name in SOURCE_PATHS:
        files[name], digest[name] = read_original(root / name)
    bd = files[BD]
    fan = files[FAN]
    dts = extract_literal_dts(files[UIO])
    # This is the original design that had an OS-wide stall. Fail if the
    # source contract changes; do NOT assume a changed design is validated.
    for literal in (
        "ps/M_AXI_HPM0_FPD", "CONFIG.PSU__USE__M_AXI_GP0 1",
        "CONFIG.PSU__FPGA_PL0_ENABLE 1",
        "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100",
        "CONFIG.PSU__MAXIGP0__DATA_WIDTH", "128",
        "ps/pl_clk0", "ps/maxihpm0_fpd_aclk", "ctrl_sc/aclk",
        "identity/aclk", "page/aclk", "pl_reset/slowest_sync_clk",
        "pl_reset/interconnect_aresetn", "pl_reset/peripheral_aresetn",
        "ps/pl_resetn0", "reset_inv/Res", "pl_reset/ext_reset_in",
        "logic_one/dout", "pl_reset/dcm_locked",
    ):
        demand(literal in bd, "M08 original BD source contract changed: " + literal)
    demand("emio_ttc0_wave_o" in fan and "M08_FAN_PWM" in fan,
           "M08 fan continuation not found in original source")
    for literal in (
        "&fpga_full", "&amba", "<&zynqmp_reset 0x74>",
        'firmware-name = "m08-v1-fan-page-uio-review.bit.bin";',
        'linux,uio-name = "m08-identity";',
        'linux,uio-name = "m08-page";',
        "reg = <0x0 0xa0000000 0x0 0x1000>;",
        "reg = <0x0 0xa0001000 0x0 0x1000>;",
    ):
        demand(literal in dts, "original M08 overlay contract changed: " + literal)
    own = feature_matrix(dts)
    demand(not any(own.values()),
           "M08 overlay now has explicit clock/AFI consumer properties; require fresh review")

    comparators = {}
    for label, path in (("stock", stock_dts), ("original_deployed_m08", deployed_dts)):
        if path is None:
            comparators[label] = {
                "status": "NOT_SUPPLIED", "runtime_proof": False}
            continue
        source, source_sha = read_original(path)
        comparators[label] = {
            "status": "OFFLINE_DTS_BYTES_READ_NOT_LIVE_PROOF",
            "sha256": source_sha,
            "features": feature_matrix(source),
            "runtime_proof": False,
        }
        # The decompiled DTS may include unrelated clocks, so the feature
        # matrix is NOT a proof a particular HPM0 port or PL0 was configured.

    return {
        "schema": "m08-d2-offline-ps-pl-source-contract-v1",
        "status": "PS_PL_RUNTIME_CONFIGURATION_AND_TIMEOUT_PROTECTION_UNPROVEN",
        "source_sha256": digest,
        "original_bd_source": {
            "hpm_interface": "M_AXI_HPM0_FPD",
            "master_width_bits_configured_in_vivado": 128,
            "pl0_clock_hz_requested_in_vivado": 100000000,
            "fabric_axi_clock_connections_in_source": True,
            "reset_source": "ps/pl_resetn0_to_reset_inv_to_proc_sys_reset",
            "dcm_locked_source": "constant_high_NOT_PLL_LOCK_MEASUREMENT",
            "runtime_clock_proven": False,
            "runtime_reset_released_proven": False,
        },
        "m08_deployed_overlay_source": {
            "declares_two_uio_windows": ["0xA0000000:0x1000",
                                          "0xA0001000:0x1000"],
            "features": own,
            "ps_pl_clock_and_afi_ownership": "NOT_DECLARED_IN_THIS_OVERLAY",
            "absence_proves_clock_stopped": False,
            "absence_proves_afi_wrong": False,
        },
        "offline_comparators": comparators,
        "amd_ug1085_atb_instance_4": {
            "scope": "FPD_main_interconnect_to_M_AXI_HPM0_FPD",
            "source": "AMD_UG1085_ATB_instances_and_programming",
            "enabled_in_failed_boot": "UNKNOWN",
            "timeout_response_type_in_failed_boot": "UNKNOWN",
            "do_not_program_without_boot_quiescence_proof": True,
        },
        "next_required_evidence": [
            "original stock K26 DTS or decompiled DTBO and M08 counterpart on PC",
            "boot firmware/Linux manager ownership of PL0 clock and HPM0 AFI",
            "failure-state ATB4 status unavailable after reboot",
            "bounded upstream AXI error/isolation even when PL clock is absent",
            "fan continuity and rollback proof prior to any new hardware test",
        ],
        "physical": {
            "stock_k26_leave_running": True,
            "original_m08_mmio_quarantined": True,
            "hardware_retest_authorized": False,
            "corrected_bitstream_prepared": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stock-dts", type=Path,
                    help="OPTIONAL already-saved PC-side stock DTS (NO board access)")
    ap.add_argument("--deployed-m08-dts", type=Path,
                    help="OPTIONAL already-saved PC-side M08 DTS (NO board access)")
    args = ap.parse_args()
    try:
        findings = audit(stock_dts=args.stock_dts, deployed_dts=args.deployed_m08_dts)
    except (ContractRejected, SyntaxError, OSError, UnicodeError) as exc:
        print("M08_D2_OFFLINE_PS_PL_CONTRACT_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(findings, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
