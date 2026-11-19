#!/usr/bin/env python3
"""M08 D3C PC-only JTAG-AXI/BRAM source and native candidate safety reviewer.

Never loads FPGA. Source acceptance does NOT certify Vivado or physical readback.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/m08_d3c_jtag_bram_build.tcl"
RUNNER = ROOT / "scripts/run_m08_d3c_jtag_bram_pc.sh"
BIT_REL = "bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit"
EXPECTED = (
    "00_vivado.log", "01_vivado.jou", "02_vivado_exit.txt",
    "reports/10_fan_a12.xdc", "reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt", "reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt", "reports/30_native_result.txt", BIT_REL,
)
OLD_FAILED = "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b"
PREV_PASSIVE = "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547"

class Reject(ValueError):
    pass

def require(cond: bool, msg: str):
    if not cond:
        raise Reject(msg)

def read_file(p: Path, max_size: int) -> bytes:
    require(p.is_file() and not p.is_symlink(), "missing or symlinked input: " + str(p))
    require(0 < p.stat().st_size <= max_size, "empty or oversized input: " + str(p))
    return p.read_bytes()

def source(root=ROOT) -> dict:
    script = read_file(root / "scripts/m08_d3c_jtag_bram_build.tcl", 150000).decode()
    runner = read_file(root / "scripts/run_m08_d3c_jtag_bram_pc.sh", 60000).decode()
    active = [x.strip() for x in script.splitlines()
              if x.strip() and not x.lstrip().startswith("#")]
    body = "\n".join(active)
    for must_have in (
        "2025.2", "m08_d3c_jtag_link_",
        "xck26-sfvc784-2LV-c",
        "get_board_parts -quiet xilinx.com:kv260_som:part0:*",
        "CONFIG.PSU__USE__M_AXI_GP0 0",
        "CONFIG.PSU__USE__M_AXI_GP1 0",
        "CONFIG.PSU__USE__M_AXI_GP2 0",
        "ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD",
        "CONFIG.PSU__TTC0__WAVEOUT__IO EMIO",
        "CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2",
        "CONFIG.MEM_DEPTH 1024", "jtag_axi:1.2", "smartconnect:1.0",
        "axi_bram_ctrl:4.1", "blk_mem_gen:8.4",
        "ps/pl_clk0", "ps/pl_resetn0",
        "rst_pl0/peripheral_aresetn",
        "connect_bd_intf_net [get_bd_intf_pins jtag_axi/M_AXI]",
        "connect_bd_intf_net [get_bd_intf_pins link_sc/M00_AXI]",
        "connect_bd_intf_net [get_bd_intf_pins bram_ctrl/BRAM_PORTA]",
        "assign_bd_address -offset 0xA0000000 -range 0x00001000",
        "validate_bd_design -force",
        "report_drc -file",
        "report_timing_summary -file",
        "m08_d3c_jtag_bram_UNRELEASED.bit",
        "M08_D3C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED",
    ):
        require(must_have in script, "native builder missing contract: " + must_have)
    for forbidden in (
        "program_hw_devices", "open_hw_manager", "connect_hw_server",
        "refresh_hw_device", "run_hw_axi", "xmutil", "loadapp", "unloadapp",
        "scp ", "ssh ", "sudo ", "/dev/mem", "/dev/uio",
        "write_cfgmem", "write_hw_platform", "write_device_image", "fpgautil",
    ):
        require(forbidden not in body, "offline native builder contains forbidden action: " + forbidden)
    require(sum(x.startswith("write_bitstream -file $bit") for x in active) == 1,
            "offline native builder must generate one unreleased bitstream")
    require(sum(x.startswith("launch_runs synth_1") for x in active) == 1
            and sum(x.startswith("launch_runs impl_1 -to_step route_design") for x in active) == 1,
            "must synthesize and route exactly once")
    for word in ("set -euo pipefail", "mktemp -d", "m08_d3c_jtag_bram_build.tcl",
                 "m08_d3c_jtag_bram_gate.py", "99_evidence_sha256.txt",
                 "sha256sum -c"):
        require(word in runner, "native runner missing: " + word)
    for forbidden in ("program_hw_devices", "xmutil ", "sudo ", "ssh ", "scp ", "rm -rf"):
        require(forbidden not in runner, "offline shell runner unsafe: " + forbidden)
    return {
        "status": "M08_D3C_JTAG_BRAM_PC_SOURCE_ACCEPTED_NOT_BUILT",
        "builder_sha256": sha256(script.encode()).hexdigest(),
        "runner_sha256": sha256(runner.encode()).hexdigest(),
        "linux_online_required_for_test": False,
        "pl_clock_independence_proven": False,
        "native_vivado_completed": False,
        "hardware_programmed": False,
        "hardware_readback_verified": False,
    }

def native(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink()
            and re.fullmatch(r"m08_d3c_jtag_link_[A-Za-z0-9]+", folder.name) is not None
            and folder.parent.name == "M08",
            "native candidate folder not a dedicated M08 D3C run")
    ledger = read_file(folder / "99_evidence_sha256.txt", 10000).decode("ascii")
    lines = ledger.splitlines()
    require(len(lines) == len(EXPECTED), "wrong SHA receipt count")
    for name, line in zip(EXPECTED, lines):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        require(match is not None and match.group(2) == name,
                "receipt file mismatch/order: " + name)
        p = folder / name
        for part in p.relative_to(folder).parents:
            if str(part) != ".":
                require(not (folder / part).is_symlink(), "symlinked evidence parent")
        limit = 100000000 if name == BIT_REL else 12000000
        require(sha256(read_file(p, limit)).hexdigest() == match.group(1),
                "native artifact hash differs: " + name)
    require(read_file(folder/"02_vivado_exit.txt", 80).decode().strip() == "vivado_build_exit=0",
            "native Vivado returned nonzero exit code")
    text = read_file(folder/"reports/30_native_result.txt", 10000).decode()
    rows = [line.split("=", 1) for line in text.splitlines()]
    require(all(len(row) == 2 for row in rows) and len(rows) == len(dict(rows)),
            "native result has malformed/duplicate fields")
    data = dict(rows)
    for k, expected in {
        "schema": "m08-d3c-jtag-bram-offline-build-v1",
        "part": "xck26-sfvc784-2LV-c",
        "ps_to_pl_hpm": "DISABLED",
        "jtag_axi": "ENABLED_PL",
        "bram_map_base": "0xA0000000",
        "bram_map_range": "0x00001000",
        "fan_route": "TTC0_WAVEOUT2_TO_A12",
        "ps_pl0_runtime_clock_proven": "NO",
        "linux_management_compatibility": "NOT_PROVEN",
        "hardware_bitstream_programmed": "NO",
        "hardware_jtag_axil_readback_proven": "NO",
        "hardware_neural_execution_proven": "NO",
    }.items():
        require(data.get(k) == expected, "invalid native field: "+k)
    require(data.get("board_part", "").startswith("xilinx.com:kv260_som:part0:")
            and data.get("vivado_version", "").startswith("2025.2"),
            "wrong native board/Vivado")
    bit = read_file(folder/BIT_REL, 100000000)
    require(len(bit) > 100000 and str(len(bit)) == data.get("bitstream_size_bytes"),
            "missing or implausible native bit")
    digest = sha256(bit).hexdigest()
    require(digest != OLD_FAILED and digest != PREV_PASSIVE,
            "never reuse historical failing or old passive bitstream")
    log = read_file(folder/"00_vivado.log", 12000000).decode(errors="replace")
    require("M08_D3C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
            "native Vivado success marker absent")
    require(re.search(r"(?m)^ERROR:", log) is None and
            re.search(r"(?m)^CRITICAL WARNING:", log) is None,
            "native Vivado logs report error or critical warning")
    drc = read_file(folder/"reports/20_route_drc.rpt", 3000000).decode(errors="replace")
    require(re.search(r"Checks found:\s*0\b", drc) is not None,
            "native DRC has findings, cannot claim offline ready")
    return {
        "status": "M08_D3C_NATIVE_OFFLINE_JTAG_BRAM_IMAGE_HASH_ACCEPTED_NO_BOARD",
        "candidate_path": str((folder/BIT_REL).resolve()),
        "candidate_sha256": digest,
        "candidate_bytes": len(bit),
        "jtag_axi_bram_base": "0xA0000000",
        "stock_linux_compatibility": "NOT_TESTED",
        "physical_hardware_programmed": False,
        "readback_proven": False,
        "neural_inference_proven": False,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--source-only", action="store_true")
    g.add_argument("--run-dir", type=Path)
    x=ap.parse_args()
    try:
        s=source()
        if x.run_dir:
            s["native"]=native(x.run_dir)
    except (Reject, OSError, ValueError, UnicodeError, KeyError) as exc:
        print("M08_D3C_JTAG_BRAM_PC_REJECTED: "+str(exc),file=sys.stderr)
        return 2
    print(json.dumps(s, indent=2, sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
