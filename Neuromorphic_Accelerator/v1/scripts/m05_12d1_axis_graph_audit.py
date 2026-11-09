"""M05.12d.1 independent, fail-closed parser of actual Vivado AXIS net report.

The parser's native tests use synthetic transcripts, not real Vivado/DDR.
Accepted original Vivado must separately prove every required net exists.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from m05_12_dma_candidate_audit import (
    PART, VLNV, ROLES, expected_config,
)

SCOPE = "CONNECTED_PL_AXIS_ONLY_NO_HLS_PS_DDR"
SHELL_MODULE = "m05_12d_axis_shell_ref"
LINKS = {
    "dma_neurons/M_AXIS_MM2S": "shell/S_AXIS_NEURONS",
    "dma_synapses/M_AXIS_MM2S": "shell/S_AXIS_SYNAPSES",
    "dma_external/M_AXIS_MM2S": "shell/S_AXIS_EXTERNAL",
    "dma_trace/S_AXIS_S2MM": "shell/M_AXIS_TRACE",
}


def verify_axis_graph_report(report: str) -> int:
    if type(report) is not str or not report.endswith("\n"):
        raise ValueError("incomplete Vivado stream graph transcript")
    meta: dict[str, str] = {}
    cells: dict[str, str] = {}
    config: dict[str, dict[str, str]] = {name: {} for name in ROLES}
    links: dict[str, tuple[str, str]] = {}
    for i, line in enumerate(report.splitlines(), start=1):
        values = line.split("|")
        if len(values) == 3 and values[0] == "META":
            _, name, value = values
            if name not in ("part", "vlnv", "scope") or name in meta:
                raise ValueError(f"invalid or duplicate metadata line {i}")
            meta[name] = value
        elif len(values) == 3 and values[0] == "CELL":
            _, name, value = values
            if name in cells or name not in (*ROLES, "shell"):
                raise ValueError(f"unexpected or duplicated cell line {i}")
            cells[name] = value
        elif len(values) == 4 and values[0] == "CFG":
            _, cell, key, value = values
            if cell not in ROLES or cell not in cells:
                raise ValueError(f"unregistered DMA config line {i}")
            expected = expected_config(ROLES[cell])
            if key not in expected or key in config[cell]:
                raise ValueError(f"unknown or duplicate DMA config line {i}")
            config[cell][key] = value
        elif len(values) == 4 and values[0] == "LINK":
            _, source, destination, net = values
            if (source in links or source not in LINKS
                    or not net or not net.strip()
                    or not net.replace("_", "").isalnum()):
                raise ValueError(f"unexpected or duplicate AXIS link line {i}")
            links[source] = (destination, net)
        else:
            raise ValueError(f"invalid, malformed or unknown graph line {i}")
    if meta != {"part": PART, "vlnv": VLNV, "scope": SCOPE}:
        raise ValueError("wrong part, IP version or unconnected scope boundary")
    wanted = {**ROLES, "shell": SHELL_MODULE}
    if cells != wanted:
        raise ValueError("not exactly four DMA directions and one module shell")
    for cell, role in ROLES.items():
        if config[cell] != expected_config(role):
            raise ValueError(f"{cell} configured DMA width/direction/length wrong")
    if set(links) != set(LINKS):
        raise ValueError("not exactly four DMA-to-shell AXIS links")
    net_names = set()
    for source, expected_dest in LINKS.items():
        dest, net = links[source]
        if dest != expected_dest or net in net_names:
            raise ValueError("miswired or shared AXIS net")
        net_names.add(net)
    return 4


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        count = verify_axis_graph_report(args.report.read_text())
    except (ValueError, OSError) as exc:
        p.exit(1, f"ERROR: M05.12d.1 original Vivado four-AXIS graph audit: {exc}\n")
    print(
        f"PASS: M05.12d.1 independent Vivado graph audit connections={count}, "
        "3 MM2S plus 1 S2MM 256-bit connected to existing shell "
        "(PARTIAL PL ONLY; NO HLS/PS/DDR/clock/reset)"
    )


if __name__ == "__main__":
    main()
