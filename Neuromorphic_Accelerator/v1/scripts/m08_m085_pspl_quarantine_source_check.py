#!/usr/bin/env python3
"""M08.5 FAIL-CLOSED offline first-party PS HPM0 / PL HP0 topology source audit.

This never invokes Vivado, opens an XSA, contacts the board or validates the
live Linux DMA API. It checks only source provenance/intent and hard-0 trust
pins; genuine 2025.2 native block-design validation remains owner-only.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
TCL=ROOT/"scripts/m08_m085_pspl_quarantine_bd.tcl"
RUN=ROOT/"scripts/run_m08_m085_pspl_quarantine_bd_pc.sh"
RTL=ROOT/"rtl/m08/m08_m085_axil_managed_neural_candidate.v"
SOURCES=(
    "m08_host_staged_page_bank.sv",
    "m08_paged_m06_lif_engine.v",
    "m08_m085_ddr_page_admission.v",
    "m08_m085_axi128_page_engine.v",
    "m08_m085_axi128_page_candidate.v",
    "m08_m085_axi_bank_bridge.v",
    "m08_m085_axi_neural_shell.v",
    "m08_m085_kernel_dma_lease_fence.v",
    "m08_m085_trusted_control_abi.v",
    "m08_m085_work_command_sequencer.v",
    "m08_m085_axil_control_candidate.v",
    "m08_m085_axil_managed_neural_candidate.v",
)
TRUST=(
    "accel/csr_trusted",
    "accel/driver_bound_verified",
    "accel/control_route_verified",
    "accel/interconnect_drain_ack",
)


class UnsafeTopology(ValueError):
    """Contract was loosened, missing, aliased, or not source-only."""


def require_all(source: str, labels: tuple[str, ...], context: str) -> None:
    for needle in labels:
        if needle not in source:
            raise UnsafeTopology(context + ": missing " + needle)


def audit(tcl: str, rtl: str, runner: str) -> dict:
    if any(type(s) is not str or not s.strip() for s in (tcl,rtl,runner)):
        raise UnsafeTopology("empty or non-text first-party source")
    # Exclude comment-only lines from forbidden-command scans.
    active_tcl="\n".join(x for x in tcl.splitlines()
                         if not x.lstrip().startswith("#"))
    active_sh="\n".join(x for x in runner.splitlines()
                        if not x.lstrip().startswith("#"))
    for forbidden in (
        "open_hw_manager", "connect_hw_server", "program_hw_devices",
        "refresh_hw_device", "write_bitstream ", "write_cfgmem",
        "write_hw_platform", "launch_runs ", "open_run ",
        "xmutil", "sudo ", "ssh ", "/dev/mem", "/dev/uio", "reboot ",
    ):
        if forbidden in active_tcl or forbidden in active_sh:
            raise UnsafeTopology("forbidden physical/synthesis action: " + forbidden)
    match=re.search(r"set source_names\s*\{([^{}]+)\}",active_tcl)
    if not match or tuple(match.group(1).split())!=SOURCES:
        raise UnsafeTopology("not the exact 12 first-party neural RTL source files")
    require_all(active_tcl,(
        "if {![string match \"2025.2*\" [version -short]]}",
        "set part xck26-sfvc784-2LV-c",
        "m08_m085_pspl_bd_[A-Za-z0-9_]+",
        "create_project m08_m085_pspl_quarantine_bd",
        "set_property BOARD_PART",
        "apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e",
        "CONFIG.PSU__USE__M_AXI_GP0 {1}",
        "CONFIG.PSU__MAXIGP0__DATA_WIDTH {128}",
        "CONFIG.PSU__USE__M_AXI_GP1 {0}",
        "CONFIG.PSU__USE__M_AXI_GP2 {0}",
        "CONFIG.PSU__USE__S_AXI_GP2 {1}",
        "CONFIG.PSU__SAXIGP2__DATA_WIDTH {128}",
        "CONFIG.PSU__USE__FABRIC__RST {0}",
        "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}",
        "CONFIG.PSU__TTC0__WAVEOUT__IO EMIO",
        "m08_m085_axil_managed_neural_candidate accel",
        "set hpm0 [exactly_one_intf ps/M_AXI_HPM0_FPD]",
        "set hp0 [exactly_one_intf ps/S_AXI_HP0_FPD]",
        'if {$hpm_width ne "128" || $hp_width ne "128"}',
        'ne "32"',
        "get_property CONFIG.PROTOCOL $dut_control",
        "ps/maxihpm0_fpd_aclk",
        "ps/saxihp0_fpd_aclk",
        "get_bd_intf_pins -quiet $name",
        "connect_bd_intf_net $hpm0 [exactly_one_intf control_sc/S00_AXI]",
        "connect_bd_intf_net [exactly_one_intf control_sc/M00_AXI] $dut_control",
        "connect_bd_intf_net $dut_ddr [exactly_one_intf hp0_sc/S00_AXI]",
        "connect_bd_intf_net [exactly_one_intf hp0_sc/M00_AXI] $hp0",
        "CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}",
        "assign_bd_address -offset 0xA4000000 -range 0x00001000",
        "assign_bd_address -offset 0x00000000 -range 0x80000000",
        "get_bd_addr_segs -quiet ps/SAXIGP2/HP0_DDR_LOW",
        "validate_bd_design -force",
        "get_bd_nets -quiet -of_objects",
        "CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}",
        "connect_bd_net $deny_pin [exactly_one_pin $p]",
        "set dn [get_bd_nets -quiet -of_objects $deny_pin]",
        "if {[llength $n] != 1 || $n ne $dn}",
        "set_property PACKAGE_PIN A12",
        "set_property IOSTANDARD LVCMOS33",
        "M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM",
        "status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY",
        "native_route=NOT_RUN",
        "bitstream=NOT_CREATED",
        "board_programming=NOT_PERFORMED",
    ),"quarantined Vivado PS/PL route")
    if set(TRUST)!=set(re.findall(r"^\s*(accel/(?:csr_trusted|driver_bound_verified|control_route_verified|interconnect_drain_ack))\s*$",tcl,re.M)):
        raise UnsafeTopology("expected exactly four hard-low platform/drain pins")
    require_all(active_sh,(
        "mktemp -d",
        "vivado -mode batch -source",
        "sha256sum",
        "99_evidence_sha256.txt",
        "M08_5_OFFLINE_BD_INCOMPLETE_OR_REJECTED_NO_PHYSICAL_RELEASE",
        "status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY",
        "vivado_exit_status",
        "bitstream_candidate",
    ),"offline owner PC runner")
    if "Vivado" not in runner or "2025.2" not in runner:
        raise UnsafeTopology("offline runner does not guard actual Vivado 2025.2")
    require_all(rtl,(
        'XIL_INTERFACENAME clk, ASSOCIATED_BUSIF S_AXI:M_AXI, ASSOCIATED_RESET resetn',
        "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12",
        "XIL_INTERFACENAME M_AXI, PROTOCOL AXI4, DATA_WIDTH 128, ADDR_WIDTH 49",
        "MAX_BURST_LENGTH 16",
        ".ENABLE_WORK_COMMANDS(1)",
        ".USE_RUNTIME_WINDOW(1)",
        "m08_m085_axi_neural_shell",
    ),"real signed16 7-slot top AXI metadata")
    # The 19 + 37 explicit AXI4/AXI4-Lite interface annotations must survive
    # each source edit; annotated instance is the one wired by Vivado IPI.
    attrs=re.findall(r'X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 (S_AXI|M_AXI) ([A-Z0-9]+)"',rtl)
    if len(attrs)!=56 or len(set(attrs))!=56:
        raise UnsafeTopology("expected exactly 56 distinct annotated AXI signal ports")
    ctrl=[name for prefix,name in attrs if prefix=="S_AXI"]
    data=[name for prefix,name in attrs if prefix=="M_AXI"]
    if len(ctrl)!=19 or len(data)!=37:
        raise UnsafeTopology("incomplete 19-channel AXI-Lite or 37-signal AXI4 pin mapping")
    return {
        "schema":"m08-m085-kv260-pspl-source-audit-v1",
        "status":"SOURCE_TOPOLOGY_GUARDS_PASS_NATIVE_BD_NOT_YET_VERIFIED",
        "new_k26_bitstream_or_board_authorized":False,
        "owner_kernel_dma_allocation_verified":False,
        "physical_axi_outstanding_drain_verified":False,
        "synthesis_route_timing_verified":False,
        "quarantine_trust_pins_held_low":list(TRUST),
        "control":"PS_HPM0_FPD_128_TO_M08_AXIL_32_SMARTCONNECT",
        "data":"M08_AXI4_128_TO_PS_HP0_FPD_128_SMARTCONNECT",
        "sha256":{
            "scripts/m08_m085_pspl_quarantine_bd.tcl":sha256(tcl.encode()).hexdigest(),
            "scripts/run_m08_m085_pspl_quarantine_bd_pc.sh":sha256(runner.encode()).hexdigest(),
            "rtl/m08/m08_m085_axil_managed_neural_candidate.v":sha256(rtl.encode()).hexdigest(),
        },
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-only",action="store_true",required=True)
    p.parse_args()
    try:
        for path in (TCL,RUN,RTL):
            if path.is_symlink() or not path.is_file():
                raise UnsafeTopology("missing or linked source: "+str(path))
        print(json.dumps(audit(TCL.read_text(),RTL.read_text(),
                               RUN.read_text()),indent=2,sort_keys=True))
    except (UnsafeTopology,OSError) as exc:
        print("M08_5_PSPL_SOURCE_BLOCKED: "+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
