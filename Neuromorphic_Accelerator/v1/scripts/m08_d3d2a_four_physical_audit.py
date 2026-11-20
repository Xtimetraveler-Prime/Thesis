#!/usr/bin/env python3
"""Read-only original-owner four-neuron JTAG/LIF hardware M02 receipt audit.

No FPGA connection, no programming, no hardware control and no evidence writes.
Requires original accepted, SHA-pinned native image, six ORIGINAL HW SHA entries,
exact executed Tcl, actual physical Vivado log markers and all independently
computed M02 4 neuron * 4 tick voltage/spike words for BOTH workloads.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import m08_d3d2a_four_gate as gate
from m08_d3d2a_four_vectors import FIXTURES, format_fixture

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / "scripts/m08_d3d2a_four_readback_once.tcl"
FILES = (
    "00_executed_source.tcl", "01_jtag_neuron.log", "02_jtag_neuron.jou",
    "03_exit.txt", "10_m02_golden.txt", "80_neural_parity_readback.txt",
)
HEADER = {
    "schema": "m08-d3d2a-hardware-four-neurons-four-ticks-v1",
    "result": "TWO_HARDWARE_FOUR_NEURON_FIXTURES_MATCHED_M02",
    "target": "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
    "device": "xck26_0",
    "debug_axi": "hw_axi_1",
    "neural_execution_tested": "YES_FOUR_NEURONS_FOUR_TICKS_TWO_CASES",
    "no_ps_axi_ddr_ssh_used": "YES",
    "reset_mode": "FABRIC_POR_256_CYCLES",
    "ps_clock_dependency": "YES",
    "synapse_routing_tested": "NO",
    "full_m06_paging_tested": "NO",
}


class Reject(ValueError):
    pass


def check(value: bool, error: str) -> None:
    if not value:
        raise Reject(error)


def read(file: Path, maximum: int = 12000000) -> bytes:
    check(file.is_file() and not file.is_symlink(),
          "missing/symlinked original evidence file " + str(file))
    check(0 < file.stat().st_size <= maximum,
          "empty/oversized original evidence file " + str(file))
    return file.read_bytes()


def expected_golden() -> str:
    return ("# schema=m08-d3d2a-m02-four-neuron-v1\n"
            "# independent_dense_vs_queued=PASS\n"
            + "\n".join(format_fixture(f) for f in FIXTURES) + "\n")


def expected_lines() -> list[str]:
    lines = []
    for fixture in FIXTURES:
        fields = format_fixture(fixture).split("|")
        volts = []
        masks = []
        for n in range(4):
            o = 35 + 5*n
            volts.append(",".join(fields[o:o+4]))
            masks.append(fields[o+4])
        lines.append(
            f"fixture={fixture.name} nonce={fields[1]} decay={fields[2]} "
            f"voltages={';'.join(volts)} spike_masks={','.join(masks)} hardware=PASS")
    return lines


def verify(native: Path, hw: Path) -> dict:
    try:
        accepted = gate.native(native)
    except (gate.Reject, OSError, ValueError, KeyError) as exc:
        raise Reject("native original four-neuron image not accepted: " + str(exc)) from exc
    check(hw.is_dir() and not hw.is_symlink() and
          hw.parent == native.parent and hw.parent.name == "M08" and
          re.fullmatch(r"m08_d3d2a_four_HW_[A-Za-z0-9]+", hw.name) is not None,
          "incorrect/new original physical evidence directory location")
    ledger_lines = read(hw/"99_evidence_sha256.txt", 10000).decode("ascii").splitlines()
    check(len(ledger_lines) == len(FILES),
          "expected exactly six native HW evidence SHA entries")
    for file, line in zip(FILES, ledger_lines):
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        check(m is not None and m.group(2) == file,
              "missing/renamed/reordered hardware SHA receipt entry: " + file)
        check(sha256(read(hw/file)).hexdigest() == m.group(1),
              "original physical file SHA mismatch: " + file)

    check(read(hw/"03_exit.txt", 100).decode().strip() ==
          "vivado_physical_exit=0", "owner physical Vivado did not return zero")
    script = read(hw/"00_executed_source.tcl", 30000)
    check(script == read(TCL, 30000),
          "executed physical Tcl differs from independently reviewed Tcl")
    check(len(re.findall(rb"(?m)^\s*program_hw_devices \$fpga\s*$", script)) == 1,
          "physical Tcl must program exactly once")
    check(b"run_hw_axi" in script and
          b"xmutil" not in script.split(b"if {![info exists")[1] and
          b"ps/axim" not in script.lower(),
          "readback Tcl outside permitted JTAG-only channel")
    check(read(hw/"10_m02_golden.txt", 12000).decode("ascii") ==
          expected_golden(), "original golden fixtures not identical to M02 oracle")

    rows = read(hw/"80_neural_parity_readback.txt", 12000).decode("ascii").splitlines()
    check(len(rows) == len(HEADER) + 1 + len(FIXTURES),
          "wrong original physical result row count")
    meta_rows = [x.split("=", 1) for x in rows[:len(HEADER)+1]]
    check(all(len(x) == 2 for x in meta_rows) and
          len(dict(meta_rows)) == len(meta_rows),
          "invalid/duplicated physical result metadata")
    meta = dict(meta_rows)
    required = dict(HEADER)
    required["candidate_sha256"] = accepted["candidate_sha256"]
    check(meta == required, "hardware result header/bitstream/target mismatch")
    check(rows[len(meta_rows):] == expected_lines(),
          "actual physical neuron/tick voltages/spikes do not match M02")
    log = read(hw/"01_jtag_neuron.log").decode(errors="replace")
    for token in (
        "M08_D3D2A_IMAGE_HASH_VERIFIED|" + accepted["candidate_sha256"],
        "M08_D3D2A_GOLDEN_FOUR_NEURON_FIXTURES_VERIFIED|2",
        "M08_D3D2A_DEVICE|xck26_0|xck26",
        "M08_D3D2A_PROGRAM_COMPLETED",
        "M08_D3D2A_AXI_MASTER|hw_axi_1",
        "M08_D3D2A_BRAM_TRANSPORT_REGRESSION_PASS",
        "M08_D3D2A_FOUR_NEURON_LIF_IDENTITY_PASS",
        "M08_D3D2A_HW_RESULT_PC_RECEIPT=",
    ):
        check(token in log, "missing genuine physical test log marker: " + token)
    for f in FIXTURES:
        check(log.count(
            "M08_D3D2A_HW_FOUR_NEURON_M02_PARITY_PASS|" + f.name + "|") == 1,
            "missing/duplicated hardware voltage/spike comparison: " + f.name)
    check(not any(re.match(r"^(ERROR:|CRITICAL WARNING:)", line)
                  for line in log.splitlines()),
          "original physical JTAG log has ERROR or CRITICAL WARNING")
    return {
        "status": "M08_D3D2A_PHYSICAL_FOUR_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED",
        "candidate_sha256": accepted["candidate_sha256"],
        "fixtures": 2,
        "neuron_timestep_voltages_verified": 32,
        "neuron_timestep_spike_decisions_verified": 32,
        "hardware_execution_verified": True,
        "synapse_routing_verified": False,
        "full_m06_neuromorphic_accelerator_verified": False,
        "physical_ddr_verified": False,
        "ps_clock_independence_verified": False,
        "no_linux_ssh_needed_for_result_channel": True,
        "scope": "4 independent signed16 LIF neurons x 4 ticks, 2 cases; no synapse routing or DDR",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--hw-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify(args.run_dir, args.hw_dir)
    except (Reject, ValueError, OSError, UnicodeError, KeyError) as exc:
        print("M08_D3D2A_HW_AUDIT_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
