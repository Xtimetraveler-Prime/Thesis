"""M05.12d.3 independent audit of real offline K26 *partial* PS/PL graph.

This verifies link membership and clock/reset group readbacks from Vivado.
It explicitly CANNOT verify real DDR, generated SmartConnect width adaptation,
address segments, shell↔HLS neural coupling, Linux buffers or device timing.
"""
from __future__ import annotations
import argparse
from pathlib import Path

META = {
    "part": "xck26-sfvc784-2LV-c",
    "scope": "OFFLINE_PS_DMA_SHELL_INTERCONNECT_CANDIDATE_NO_HLS_OR_ADDRESSES",
    "source_mgmt_mode": "All",
    "ps_vlnv": "xilinx.com:ip:zynq_ultra_ps_e:3.5",
    "dma_vlnv": "xilinx.com:ip:axi_dma:7.1",
    "smartconnect_vlnv": "xilinx.com:ip:smartconnect:1.0",
    "hls_control": "MISSING_GENERATED_RTL",
    "address_map": "NOT_ASSIGNED",
    "full_bd_validation": "NOT_RUN",
    "data_width_conversion": "SMARTCONNECT_CANDIDATE_NOT_GENERATED",
}
DMA = {
    "dma_neurons": "MM2S", "dma_synapses": "MM2S",
    "dma_external": "MM2S", "dma_trace": "S2MM",
}
STREAM = {
    ("dma_neurons/M_AXIS_MM2S", "shell/S_AXIS_NEURONS"),
    ("dma_synapses/M_AXIS_MM2S", "shell/S_AXIS_SYNAPSES"),
    ("dma_external/M_AXIS_MM2S", "shell/S_AXIS_EXTERNAL"),
    ("shell/M_AXIS_TRACE", "dma_trace/S_AXIS_S2MM"),
}
CONTROL = {
    ("ps/M_AXI_HPM0_FPD", "ctrl_sc/S00_AXI"),
    ("ctrl_sc/M00_AXI", "dma_neurons/S_AXI_LITE"),
    ("ctrl_sc/M01_AXI", "dma_synapses/S_AXI_LITE"),
    ("ctrl_sc/M02_AXI", "dma_external/S_AXI_LITE"),
    ("ctrl_sc/M03_AXI", "dma_trace/S_AXI_LITE"),
    ("ctrl_sc/M04_AXI", "shell/s_axi"),
}
MEMORY = {
    ("dma_neurons/M_AXI_MM2S", "mem_sc/S00_AXI"),
    ("dma_synapses/M_AXI_MM2S", "mem_sc/S01_AXI"),
    ("dma_external/M_AXI_MM2S", "mem_sc/S02_AXI"),
    ("dma_trace/M_AXI_S2MM", "mem_sc/S03_AXI"),
    ("mem_sc/M00_AXI", "ps/S_AXI_HP0_FPD"),
}
LINKS = STREAM | CONTROL | MEMORY
CLOCK = {
    "ps/pl_clk0", "ps/maxihpm0_fpd_aclk", "ps/saxihp0_fpd_aclk",
    "ctrl_sc/aclk", "mem_sc/aclk", "pl_reset/slowest_sync_clk",
    "shell/clk",
}
for dma in DMA:
    CLOCK.add(f"{dma}/s_axi_lite_aclk")
for dma in ("dma_neurons", "dma_synapses", "dma_external"):
    CLOCK.update({f"{dma}/m_axi_mm2s_aclk", f"{dma}/m_axis_mm2s_aclk"})
CLOCK.update({"dma_trace/m_axi_s2mm_aclk", "dma_trace/s_axis_s2mm_aclk"})
RESET_INT = {"ctrl_sc/aresetn", "mem_sc/aresetn"}
RESET_PER = {"shell/rst_n"} | {f"{dma}/axi_resetn" for dma in DMA}
RESET = RESET_INT | RESET_PER
PSCFG = {"PSU__MAXIGP0__DATA_WIDTH": "128", "PSU__SAXIGP2__DATA_WIDTH": "128"}


def _unique(table: dict, key, value, allowed: set, kind: str) -> None:
    if key not in allowed or key in table:
        raise ValueError(f"unexpected/duplicate {kind} {key}")
    table[key] = value


def audit_connected_candidate(report: str) -> dict[str, int]:
    if type(report) is not str or not report.endswith("\n") or len(report) > 50000:
        raise ValueError("incomplete or oversized graph evidence")
    meta, dma, links, clocks, resets, pscfg = {}, {}, {}, {}, {}, {}
    for lineno, line in enumerate(report.splitlines(), 1):
        fields = line.split("|")
        kind = fields[0]
        if kind in ("META", "PSCFG") and len(fields) == 3:
            _, key, value = fields
            expected = META if kind == "META" else PSCFG
            if value != expected.get(key):
                raise ValueError(f"unexpected {kind} value at line {lineno}")
            _unique(meta if kind == "META" else pscfg, key, value,
                    set(expected), kind)
        elif kind == "DMA" and len(fields) == 6:
            _, name, role, axis, addr, length = fields
            if role != DMA.get(name) or (axis, addr, length) != ("256", "32", "24"):
                raise ValueError(f"bad original DMA configuration at line {lineno}")
            _unique(dma, name, role, set(DMA), kind)
        elif kind == "LINK" and len(fields) == 4:
            _, src, dst, net = fields
            if not net.strip() or len(net) > 180 or any(c.isspace() for c in net):
                raise ValueError(f"invalid interface net at line {lineno}")
            _unique(links, (src, dst), net, LINKS, kind)
        elif kind in ("CLK", "RESET") and len(fields) == 3:
            _, pin, net = fields
            if not net.strip() or len(net) > 180 or any(c.isspace() for c in net):
                raise ValueError(f"bad net at line {lineno}")
            allowed = CLOCK if kind == "CLK" else RESET
            _unique(clocks if kind == "CLK" else resets, pin, net, allowed, kind)
        else:
            raise ValueError(f"unexpected graph record at line {lineno}")
    for kind, actual, required in (
        ("META", meta, set(META)), ("DMA", dma, set(DMA)),
        ("LINK", links, LINKS), ("CLK", clocks, CLOCK),
        ("RESET", resets, RESET), ("PSCFG", pscfg, set(PSCFG)),
    ):
        if set(actual) != required:
            missing = sorted(required - set(actual))
            extra = sorted(set(actual) - required)
            raise ValueError(f"wrong {kind} entries; missing={missing}, extra={extra}")
    if len(set(links.values())) != len(LINKS):
        raise ValueError("AXI/AXIS point-to-point links reuse the same net")
    if len(set(clocks.values())) != 1:
        raise ValueError("not all PL clock consumers share one actual Vivado net")
    if len({resets[k] for k in RESET_INT}) != 1:
        raise ValueError("SmartConnect resets are not on same interconnect reset net")
    if len({resets[k] for k in RESET_PER}) != 1:
        raise ValueError("all DMA/shell reset pins do not share a peripheral reset net")
    if next(iter({resets[k] for k in RESET_INT})) == next(iter({resets[k] for k in RESET_PER})):
        raise ValueError("processor-reset interconnect/peripheral domains must remain distinguished")
    if next(iter(clocks.values())) in set(resets.values()):
        raise ValueError("clock and reset unexpectedly same net")
    return {
        "stream_links": len(STREAM),
        "control_links": len(CONTROL),
        "memory_links": len(MEMORY),
        "clock_consumers": len(CLOCK),
        "reset_consumers": len(RESET),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        status = audit_connected_candidate(args.report.read_text())
    except (OSError, ValueError) as exc:
        p.exit(1, f"ERROR: M05.12d.3 independent partial PS/PL graph audit: {exc}\n")
    print(f"PASS: M05.12d.3 independent partial PS/PL graph audit {status} "
          "(NO HLS/ADDRESS/DDR/PHYSICAL BD VALIDATION)")


if __name__ == "__main__":
    main()
