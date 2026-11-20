#!/usr/bin/env python3
"""M08 D3.D.1: fail-closed standalone real LIF/JTAG native-image reviewer.

PC-only: never accesses or programs a KV260. r2 D3.C image is not accepted.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import m08_d3c_jtag_bram_gate as d3c

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/m08_d3d_neuron_build.tcl"
RUNNER = ROOT / "scripts/run_m08_d3d_neuron_pc.sh"
LIF_RTL = ROOT / "rtl/m08/m08_d3d_lif_axil.v"
POR_RTL = ROOT / "rtl/m08_d3c_fabric_por.v"
BIT_REL = "bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit"
EXPECTED = (
    "00_vivado.log", "01_vivado.jou", "02_vivado_exit.txt",
    "reports/10_fan_a12.xdc", "reports/11_fabric_por.v",
    "reports/12_lif_axil.v", "reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt", "reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt", "reports/30_native_result.txt", BIT_REL,
)
SCHEMA = "m08-d3d-neural-jtag-offline-build-v1"
R2_BIT_SHA = "87e04662b038ded01bd020141c541a33d62370df02bdeaacdad695b17c9d00a1"

class Reject(ValueError):
    pass

def check(cond: bool, message: str) -> None:
    if not cond:
        raise Reject(message)

def read(path: Path, limit: int = 12000000) -> bytes:
    check(path.is_file() and not path.is_symlink(), "missing/symlinked: " + str(path))
    check(0 < path.stat().st_size <= limit, "empty/oversized: " + str(path))
    return path.read_bytes()

def source() -> dict:
    check(LIF_RTL.suffix == ".v" and not (ROOT / "rtl/m08/m08_d3d_lif_axil.sv").exists(),
          "Vivado module-reference top must be native Verilog .v, not SystemVerilog .sv")
    builder = read(BUILDER, 200000).decode()
    runner = read(RUNNER, 60000).decode()
    lif = read(LIF_RTL, 50000).decode()
    por = read(POR_RTL, 20000).decode()
    active = "\n".join(x for x in builder.splitlines()
                       if x.strip() and not x.lstrip().startswith("#"))
    check("m08_d3d_lif_axil.sv" not in active and "12_lif_axil.sv" not in active,
          "native builder must use Verilog .v module reference and evidence")
    # Actual owner Vivado picked a DIFFERENT wrapper after a typo in the
    # hardcoded top name, even though route and bitgen succeeded. This exact
    # source boundary catches that error BEFORE any new native build.
    top_commands = [line.strip() for line in active.splitlines()
                    if re.match(r"^set_property\\s+top\\s+", line.strip())]
    check(top_commands == ["set_property top $wrapper_top [current_fileset]"],
          "unsafe/mismatched Vivado explicit top setting: " + repr(top_commands))
    for top_token in (
        "set wrapper_path [lindex $wrapper 0]",
        "set wrapper_top [file rootname [file tail $wrapper_path]]",
        'if {$wrapper_top ne "m08_d3d_lif_jtag_wrapper"}',
        'set resolved_top [get_property top [current_fileset]]',
        'if {$resolved_top ne $wrapper_top}',
        "M08_D3D_NATIVE_TOP_WRAPPER_VALIDATED|$wrapper_top",
        "puts $f {wrapper_top=m08_d3d_lif_jtag_wrapper}",
    ):
        check(top_token in active, "missing native verified wrapper top: " + top_token)
    check("m08_d3d_neuron_wrapper" not in active,
          "obsolete hardcoded wrong Vivado top retained")
    for token in (
        "2025.2", "m08_d3d_neuron_", "xck26-sfvc784-2LV-c",
        "get_board_parts -quiet xilinx.com:kv260_som:part0:*",
        "CONFIG.PSU__USE__M_AXI_GP0 0",
        "CONFIG.PSU__USE__M_AXI_GP1 0",
        "CONFIG.PSU__USE__M_AXI_GP2 0",
        "CONFIG.PSU__TTC0__WAVEOUT__IO EMIO",
        "CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2",
        "CONFIG.NUM_SI 1 CONFIG.NUM_MI 2",
        "m08_d3d_lif_axil lif",
        "m08_d3c_fabric_por fabric_por",
        "connect_bd_intf_net [get_bd_intf_pins link_sc/M01_AXI]",
        "[get_bd_intf_pins lif/S_AXI]",
        "lif/aclk", "lif/aresetn", "fabric_por/aresetn",
        "assign_bd_address -offset 0xA0000000 -range 0x00001000",
        "assign_bd_address -offset 0xA0001000 -range 0x00001000",
        "bram_ctrl/BRAM_PORTA", "ps/pl_clk0", "ps/emio_ttc0_wave_o",
        "M08_D3D_NATIVE_FABRIC_POR_AND_BRAM_DERIVED_CHECK=PASS",
        "get_bd_addr_segs -quiet -of_objects $space",
        "m08_d3d_lif_jtag_UNRELEASED.bit",
        "fabric_por_rtl_sha256", "lif_rtl_sha256", "builder_sha256",
        "validate_bd_design -force", "report_drc -file",
        "report_timing_summary -file", "write_bitstream -file $bit",
        "M08_D3D_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED",
    ):
        check(token in active, "neural builder missing: " + token)
    for forbidden in (
        "program_hw_devices", "open_hw_manager", "connect_hw_server",
        "run_hw_axi", "xmutil", "loadapp", "unloadapp", "sudo ",
        "ssh ", "scp ", "/dev/mem", "/dev/uio", "write_cfgmem",
        "write_device_image", "fpgautil", "ps/M_AXI_HPM0_FPD",
    ):
        # The HPM interface name appears in an *absence assertion*; that
        # explicit fail-closed assertion is required, not forbidden.
        if forbidden == "ps/M_AXI_HPM0_FPD":
            check("ps/M_AXI_HPM0_FPD ps/M_AXI_HPM1_FPD ps/M_AXI_HPM0_LPD" in builder,
                  "missing HPM disable check")
            continue
        check(forbidden not in active, "offline builder unsafe: " + forbidden)
    check("connect_bd_net $reset_out" not in active and
          "rst_pl0/peripheral_aresetn" not in active,
          "LIF must not restore PS reset dependency")
    check(builder.count("write_bitstream -file $bit") == 1 and
          builder.count("launch_runs synth_1") == 1 and
          builder.count("launch_runs impl_1 -to_step route_design") == 1,
          "neural native implementation must build once")
    check('set allowed_precreated {00_vivado.log 01_vivado.jou}' in builder,
          "unsafe pre-created evidence contents")
    for token in (
        "set -euo pipefail", "mktemp -d",
        "m08_d3d_neuron_build.tcl", "m08_d3d_neuron_gate.py",
        "99_evidence_sha256.txt", 'sha256sum -c',
        "reports/12_lif_axil.v", "m08_d3d_lif_jtag_UNRELEASED.bit",
    ):
        check(token in runner, "neural PC runner missing: " + token)
    for forbidden in ("program_hw_devices", "run_hw_axi", "xmutil", "sudo ", "ssh ", "rm -rf"):
        check(forbidden not in runner, "offline PC runner unsafe: " + forbidden)
    check(runner.index('-log "$RUN/00_vivado.log"') <
          runner.index('-tclargs "$RUN"') and
          runner.index('-journal "$RUN/01_vivado.jou"') <
          runner.index('-tclargs "$RUN"'),
          "Vivado logging flags must precede -tclargs")

    for token in (
        "module m08_d3d_lif_axil", "input  wire        aclk",
        "input  wire        aresetn", "PROTOCOL AXI4LITE",
        "AWVALID", "WVALID", "BVALID", "RVALID",
        "membrane <= next_voltage;", "trace_voltage[tick] <= next_voltage;",
        "spike_mask[tick] <= fired;", "run_count <= run_count + 1;",
        "if (done) s_axi_rdata <= result_nonce",
        "s_axi_rresp <= SLVERR", "wire config_valid = cfg_nonce != 0",
        "half_trunc", "currents[tick]",
    ):
        check(token in lif, "compute RTL lacks required property: " + token)
    check("module m08_d3c_fabric_por" in por and
          "assign aresetn = released" in por,
          "missing proven fabric POR")
    check("m08_d3c_jtag_bram_r2_UNRELEASED.bit" not in active and
          "m08_d3c_jtag_bram_r2_UNRELEASED.bit" not in runner,
          "old BRAM bitstream not a neural candidate")
    return {
        "status": "M08_D3D_SOURCE_ACCEPTED_PC_ONLY_NOT_BUILT",
        "hardware_neural_inference_proven": False,
        "hardware_programmed": False,
        "builder_sha256": sha256(builder.encode()).hexdigest(),
        "lif_rtl_sha256": sha256(lif.encode()).hexdigest(),
        "fabric_por_sha256": sha256(por.encode()).hexdigest(),
    }

def native(folder: Path) -> dict:
    check(folder.is_dir() and not folder.is_symlink() and
          re.fullmatch(r"m08_d3d_neuron_[A-Za-z0-9]+", folder.name) is not None
          and folder.parent.name == "M08",
          "not a fresh dedicated D3.D owner run folder")
    lines = read(folder / "99_evidence_sha256.txt", 12000).decode("ascii").splitlines()
    check(len(lines) == len(EXPECTED), "neural evidence receipt has wrong file count")
    for wanted, line in zip(EXPECTED, lines):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        check(match is not None and match.group(2) == wanted,
              "missing/out-of-order evidence receipt: " + wanted)
        p = folder / wanted
        check(not p.parent.is_symlink(), "symlink evidence parent")
        data = read(p, 100000000 if wanted == BIT_REL else 12000000)
        check(sha256(data).hexdigest() == match.group(1),
              "original evidence SHA mismatch: " + wanted)
    check(read(folder / "02_vivado_exit.txt", 80).decode().strip() ==
          "vivado_build_exit=0", "native Vivado returned a failure")
    kv = read(folder/"reports/30_native_result.txt", 10000).decode()
    rows = [x.split("=", 1) for x in kv.splitlines()]
    check(all(len(x) == 2 for x in rows) and len(rows) == len(dict(rows)),
          "malformed/duplicate native result")
    values = dict(rows)
    for key, val in {
        "schema": SCHEMA,
        "wrapper_top": "m08_d3d_lif_jtag_wrapper",
        "part": "xck26-sfvc784-2LV-c",
        "ps_to_pl_hpm": "DISABLED",
        "jtag_axi": "ENABLED_PL",
        "ps_pl0_clock_request_hz": "100000000",
        "ps_pl0_runtime_clock_proven": "NO",
        "bram_map_base": "0xA0000000",
        "bram_map_range": "0x00001000",
        "lif_base": "0xA0001000",
        "lif_map_range": "0x00001000",
        "reset_mode": "FABRIC_POR_256_CYCLES",
        "ps_reset_dependency": "NO",
        "ps_clock_dependency": "YES",
        "neural_mode": "SINGLE_NEURON_FOUR_TICKS_SIGNED16",
        "decay_modes": "ZERO_HALF_ONE",
        "lif_requires_hardware_execution": "YES",
        "bram_depth_words": "1024",
        "bram_width_bits": "32",
        "fan_route": "TTC0_WAVEOUT2_TO_A12",
        "linux_management_compatibility": "NOT_PROVEN",
        "hardware_bitstream_programmed": "NO",
        "hardware_jtag_axil_readback_proven": "NO",
        "hardware_neural_execution_proven": "NO",
        "hardware_lif_readback_proven": "NO",
    }.items():
        check(values.get(key) == val, "wrong native receipt: " + key)
    for name, content in (
        ("builder_sha256", read(BUILDER, 200000)),
        ("fabric_por_rtl_sha256", read(POR_RTL, 20000)),
        ("lif_rtl_sha256", read(LIF_RTL, 50000)),
    ):
        check(values.get(name) == sha256(content).hexdigest(),
              "neural source provenance mismatch: " + name)
    for filename, original in (("11_fabric_por.v", POR_RTL),
                               ("12_lif_axil.v", LIF_RTL)):
        check(sha256(read(folder/"reports"/filename, 50000)).hexdigest() ==
              sha256(read(original, 50000)).hexdigest(),
              "native evidence RTL differs from source: " + filename)
    check(values.get("vivado_version", "").startswith("2025.2") and
          values.get("board_part", "").startswith("xilinx.com:kv260_som:part0:"),
          "wrong Vivado or KV260 preset")
    depth = values.get("bram_controller_derived_depth", "")
    check(depth.isdecimal() and int(depth) > 0, "unverified BRAM geometry")
    bit = read(folder / BIT_REL, 100000000)
    check(len(bit) >= 100000 and
          str(len(bit)) == values.get("bitstream_size_bytes"),
          "missing/invalid neural bitstream")
    digest = sha256(bit).hexdigest()
    check(digest not in (R2_BIT_SHA, d3c.OLD_FAILED, d3c.PREV_PASSIVE),
          "never reuse non-compute or quarantined bitstream")
    log = read(folder/"00_vivado.log").decode(errors="replace")
    check("M08_D3D_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
          "no native neural bitstream completion marker")
    check("M08_D3D_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d_lif_jtag_wrapper" in log,
          "no native proof generated top was selected and verified")
    errors = [(n, x.strip()) for n, x in enumerate(log.splitlines(), 1)
              if re.match(r"^(ERROR:|CRITICAL WARNING:)", x)]
    check(not errors, "native fatal diagnostics: " + repr(errors[:2]))
    drc = read(folder/"reports/20_route_drc.rpt", 3000000).decode(errors="replace")
    timing = read(folder/"reports/21_route_timing.rpt", 3000000).decode(errors="replace")
    try:
        drc_check = d3c.inspect_drc(drc)
        timing_check = d3c.inspect_timing(timing)
    except d3c.Reject as exc:
        raise Reject("native DRC/timing rejected: " + str(exc)) from exc
    return {
        "status": "M08_D3D_NATIVE_NEURON_IMAGE_ACCEPTED_OFFLINE_NO_BOARD",
        **drc_check, **timing_check,
        "candidate_path": str((folder/BIT_REL).resolve()),
        "candidate_sha256": digest, "candidate_bytes": len(bit),
        "neural_register_base": "0xA0001000",
        "transport_bram_base": "0xA0000000",
        "hardware_programmed": False, "neural_execution_proven": False,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-only", action="store_true")
    group.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    try:
        result = source()
        if args.run_dir is not None:
            result["native"] = native(args.run_dir)
    except (Reject, OSError, UnicodeError, ValueError, KeyError) as exc:
        print("M08_D3D_NEURON_PC_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
