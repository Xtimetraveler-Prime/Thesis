#!/usr/bin/env python3
"""Independently verify genuine D3.D.1 JTAG/LIF PC hardware receipts (NO BOARD).

Requires native Vivado candidate acceptance, original immutable SHA ledger,
exact executed Tcl source, and actual four-fixture per-tick M02 numeric parity.
This script NEVER connects to JTAG/FPGA or alters receipt directories.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import m08_d3d_neuron_gate as native_gate
from m08_d3d_neuron_vectors import FIXTURES, format_fixture

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d3d_neuron_readback_once.tcl"
EXPECTED = (
    "00_executed_source.tcl", "01_jtag_neuron.log", "02_jtag_neuron.jou",
    "03_exit.txt", "10_m02_golden.txt", "80_neural_parity_readback.txt",
)
SCHEMA = "m08-d3d-hardware-lif4-ticks-v1"
SUCCESS = "FOUR_HARDWARE_NEURON_FIXTURES_MATCHED_M02"

class Reject(ValueError):
    pass

def check(condition: bool, msg: str) -> None:
    if not condition:
        raise Reject(msg)

def read(path: Path, limit: int = 12000000) -> bytes:
    check(path.is_file() and not path.is_symlink(), "missing/symlinked: " + str(path))
    check(0 < path.stat().st_size <= limit, "empty/oversized: " + str(path))
    return path.read_bytes()

def verify(native: Path, hw: Path) -> dict:
    try:
        accepted = native_gate.native(native)
    except native_gate.Reject as exc:
        raise Reject("native D3.D evidence failed: " + str(exc)) from exc
    check(hw.is_dir() and not hw.is_symlink() and
          hw.parent.name == "M08" and hw.parent == native.parent and
          re.fullmatch(r"m08_d3d_neuron_HW_[A-Za-z0-9]+", hw.name) is not None,
          "hardware evidence must be a separate original M08 D3.D run")
    ledger = read(hw/"99_evidence_sha256.txt", 10000).decode("ascii").splitlines()
    check(len(ledger) == len(EXPECTED), "invalid hardware receipt file count")
    for name, line in zip(EXPECTED, ledger):
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_./-]+)", line)
        check(match is not None and match.group(2) == name,
              "incorrect original hardware receipt entry/order: " + name)
        check(sha256(read(hw/name)).hexdigest() == match.group(1),
              "original hardware receipt SHA mismatch: " + name)
    check(read(hw/"03_exit.txt", 100).decode().strip() == "vivado_physical_exit=0",
          "native physical Vivado exit not zero")
    executed = read(hw/"00_executed_source.tcl", 50000)
    check(executed == read(SCRIPT, 50000),
          "physical executed source is not current one-shot review")
    check(executed.count(b"program_hw_devices $fpga") == 1,
          "physical script not a single programming call")

    goldens = read(hw/"10_m02_golden.txt", 10000).decode("ascii")
    expected_rows = [format_fixture(f) for f in FIXTURES]
    check(goldens == ("# schema=m08-d3d-m02-golden-v1\n"
                      "# independent_dense_vs_event=PASS\n"
                      + "\n".join(expected_rows) + "\n"),
          "original physical golden fixtures do not match current M02 oracle")

    result = read(hw/"80_neural_parity_readback.txt", 10000).decode("ascii")
    lines = result.splitlines()
    check(len(lines) == 16, "incorrect hardware neural result row count")
    kv = [x.split("=", 1) for x in lines[:12]]
    check(all(len(p) == 2 for p in kv) and len(dict(kv)) == len(kv),
          "malformed neural hardware result header")
    data = dict(kv)
    for key, val in {
        "schema": SCHEMA,
        "result": SUCCESS,
        "candidate_sha256": accepted["candidate_sha256"],
        "target": "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
        "device": "xck26_0",
        "debug_axi": "hw_axi_1",
        "neural_execution_tested": "YES_SINGLE_NEURON_FOUR_TICKS",
        "no_ps_axi_ddr_ssh_used": "YES",
        "reset_mode": "FABRIC_POR_256_CYCLES",
        "ps_clock_dependency": "YES",
        "synapse_routing_tested": "NO",
        "full_m06_paging_tested": "NO",
    }.items():
        check(data.get(key) == val, "incorrect actual hardware result: " + key)

    expected_fixture_lines = []
    for fixture in FIXTURES:
        fields = format_fixture(fixture).split("|")
        expected_fixture_lines.append(
            f"fixture={fixture.name} nonce={fields[1]} "
            f"voltages={','.join(fields[11:15])} "
            f"spike_mask={fields[15]} hardware=PASS")
    check(lines[len(kv):] == expected_fixture_lines,
          "hardware-derived voltage/spike trace differs from M02 oracle")
    log = read(hw/"01_jtag_neuron.log").decode(errors="replace")
    for token in (
        "M08_D3D_PROGRAM_COMPLETED",
        "M08_D3D_BRAM_TRANSPORT_REGRESSION_PASS",
        "M08_D3D_AXI_MASTER|hw_axi_1",
        "M08_D3D_PHYSICAL_NEURAL_RESULT_PC_RECEIPT=",
    ):
        check(token in log, "hardware JTAG log missing: " + token)
    for fixture in FIXTURES:
        check(("M08_D3D_HW_NEURAL_M02_PARITY_PASS|" + fixture.name + "|") in log,
              "hardware log missing a particular computed fixture")
    check(not any(re.match(r"^(ERROR:|CRITICAL WARNING:)", ln)
                  for ln in log.splitlines()),
          "original hardware JTAG log has fatal diagnostics")
    return {
        "status": "M08_D3D_PHYSICAL_SINGLE_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED",
        "candidate_sha256": accepted["candidate_sha256"],
        "fixtures": len(FIXTURES),
        "hardware_execution_verified": True,
        "full_m06_neuromorphic_accelerator_verified": False,
        "physical_ddr_verified": False,
        "no_linux_ssh_needed_for_result_channel": True,
        "ps_clock_independence_verified": False,
        "scope": "single signed16 LIF neuron, 4 ticks, no synapse routing or DDR",
    }

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--hw-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = verify(args.run_dir, args.hw_dir)
    except (Reject, OSError, ValueError, UnicodeError) as exc:
        print("M08_D3D_HARDWARE_AUDIT_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
