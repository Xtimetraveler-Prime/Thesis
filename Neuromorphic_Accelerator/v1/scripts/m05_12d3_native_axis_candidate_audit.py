"""Independent source-only audit of next genuine HLS AXIS-native Vivado BD.

Unlike the previous owner-PASS scalar candidate, require four *real*
inferred AXI4-Stream interface nets: no BD 41-1306 scalar override warnings.
Exactly 24 original 128/192-bit native scalar endpoint declarations are
verified by Vivado before grouped interface linking, without connecting
individual scalar pins. Six PS controls + old DMA PS/PL paths remain exact.
Original accepted owner graph and RTL are immutable.
"""
from __future__ import annotations
import argparse
from pathlib import Path

META = {
    "part": "xck26-sfvc784-2LV-c",
    "scope": "OFFLINE_PS_DMA_SHELL_REAL_HLS_NATIVE_AXI_STREAM_INTERFACE_CANDIDATE",
    "source_mgmt_mode": "All",
    "ps_vlnv": "xilinx.com:ip:zynq_ultra_ps_e:3.5",
    "dma_vlnv": "xilinx.com:ip:axi_dma:7.1",
    "smartconnect_vlnv": "xilinx.com:ip:smartconnect:1.0",
    "hls_control": "REAL_GENERATED_MODULE_REF_CANDIDATE",
    "address_map": "NOT_ASSIGNED",
    "full_bd_validation": "NOT_RUN",
    "data_width_conversion": "SMARTCONNECT_CANDIDATE_NOT_GENERATED",
    "native_hls_streams": "4_GENUINE_AXIS_INTERFACE_NETS_12_PIN_CONTRACTS",
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
    ("ctrl_sc/M05_AXI", "hls/s_axi_control"),
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
    "shell/clk", "hls/ap_clk",
}
for dma in DMA:
    CLOCK.add(f"{dma}/s_axi_lite_aclk")
for dma in ("dma_neurons", "dma_synapses", "dma_external"):
    CLOCK.add(f"{dma}/m_axi_mm2s_aclk")
CLOCK.add("dma_trace/m_axi_s2mm_aclk")
RESET_INT = {"ctrl_sc/aresetn", "mem_sc/aresetn"}
RESET_PER = {"shell/rst_n", "hls/ap_rst_n"} | {f"{dma}/axi_resetn" for dma in DMA}
RESET = RESET_INT | RESET_PER
# Clock and AXI DMA pin sets match genuine PG021 and the owner observed
# missing separate AXIS clock pin, which is specific to AXI VDMA (PG020).
RESETFEED = {"ps/pl_resetn0", "reset_inv/Op1", "reset_inv/Res", "pl_reset/ext_reset_in"}
RESETDIR = {
    "ps/pl_resetn0": "O", "reset_inv/Op1": "I",
    "reset_inv/Res": "O", "pl_reset/ext_reset_in": "I",
}
RESETCFG = {"C_EXT_RESET_HIGH": "1"}
RESETINV = {"C_OPERATION": "not", "C_SIZE": "1"}
PSCFG = {"PSU__MAXIGP0__DATA_WIDTH": "128", "PSU__SAXIGP2__DATA_WIDTH": "128"}
# Exact owner-authenticated 128/192 native TDATA without TKEEP/TLAST.
NATIVE = {
    ("shell/hls_neuron_tdata", "hls/neurons_TDATA"): "128",
    ("shell/hls_neuron_tvalid", "hls/neurons_TVALID"): "1",
    ("hls/neurons_TREADY", "shell/hls_neuron_tready"): "1",
    ("shell/hls_synapse_tdata", "hls/synapses_TDATA"): "192",
    ("shell/hls_synapse_tvalid", "hls/synapses_TVALID"): "1",
    ("hls/synapses_TREADY", "shell/hls_synapse_tready"): "1",
    ("shell/hls_external_tdata", "hls/external_events_TDATA"): "128",
    ("shell/hls_external_tvalid", "hls/external_events_TVALID"): "1",
    ("hls/external_events_TREADY", "shell/hls_external_tready"): "1",
    ("hls/trace_TDATA", "shell/hls_trace_tdata"): "192",
    ("hls/trace_TVALID", "shell/hls_trace_tvalid"): "1",
    ("shell/hls_trace_tready", "hls/trace_TREADY"): "1",
}

# Owner-observed genuine Vivado inferred interface names from warning BD 41-1306.
NATIVE_INTF = {
    ("shell/hls_neuron", "hls/neurons"),
    ("shell/hls_synapse", "hls/synapses"),
    ("shell/hls_external", "hls/external_events"),
    ("hls/trace", "shell/hls_trace"),
}
NATIVE_PINS = {}
for (src, dst), bits in NATIVE.items():
    if src in NATIVE_PINS or dst in NATIVE_PINS:
        raise RuntimeError("duplicate native top pin contract")
    NATIVE_PINS[src] = ("O", bits)
    NATIVE_PINS[dst] = ("I", bits)
if len(NATIVE_PINS) != 24:
    raise RuntimeError("expected 24 original RTL scalar pin declarations")

# The inventory is evidence of what Vivado exposes, NOT evidence of
# assigned/decoded CPU physical addresses (the previous stage lacked them).
SLAVE_INTERFACES = {
    "dma_neurons": "dma_neurons/S_AXI_LITE",
    "dma_synapses": "dma_synapses/S_AXI_LITE",
    "dma_external": "dma_external/S_AXI_LITE",
    "dma_trace": "dma_trace/S_AXI_LITE",
    "shell": "shell/s_axi",
    "hls": "hls/s_axi_control",
}



def _unique(table: dict, key, value, allowed: set, kind: str) -> None:
    if key not in allowed or key in table:
        raise ValueError(f"unexpected/duplicate {kind} {key}")
    table[key] = value


def audit_connected_candidate(report: str) -> dict[str, int]:
    if type(report) is not str or not report.endswith("\n") or len(report) > 50000:
        raise ValueError("incomplete or oversized graph evidence")
    meta, dma, links, clocks, resets, pscfg = {}, {}, {}, {}, {}, {}
    resetfeed, resetdir, resetcfg, resetinv = {}, {}, {}, {}
    native, hlsintf, native_pins = {}, {}, {}
    for lineno, line in enumerate(report.splitlines(), 1):
        fields = line.split("|")
        kind = fields[0]
        if kind in ("META", "PSCFG", "RESETCFG", "RESETINV", "RESETDIR") and len(fields) == 3:
            _, key, value = fields
            expected = {
                "META": META, "PSCFG": PSCFG, "RESETCFG": RESETCFG,
                "RESETINV": RESETINV, "RESETDIR": RESETDIR,
            }[kind]
            if value != expected.get(key):
                raise ValueError(f"unexpected {kind} value at line {lineno}")
            destination = {
                "META": meta, "PSCFG": pscfg, "RESETCFG": resetcfg,
                "RESETINV": resetinv, "RESETDIR": resetdir,
            }[kind]
            _unique(destination, key, value, set(expected), kind)
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
        elif kind == "NATIVEINTF" and len(fields) == 4:
            _, src, dst, net = fields
            if not net or len(net) > 180 or any(c.isspace() for c in net):
                raise ValueError(f"bad native AXIS interface net line {lineno}")
            _unique(native, (src, dst), net, NATIVE_INTF, kind)
        elif kind == "NATIVEPIN" and len(fields) == 4:
            _, name, direction, width = fields
            if NATIVE_PINS.get(name) != (direction, width):
                raise ValueError(f"wrong native AXIS pin direction/width line {lineno}")
            _unique(native_pins, name, (direction, width), set(NATIVE_PINS), kind)
        elif kind == "HLSINTF" and len(fields) == 3:
            _, name, role = fields
            if (name, role) != ("s_axi_control", "SLAVE"):
                raise ValueError("missing native tool-generated HLS control interface role")
            _unique(hlsintf, name, role, {"s_axi_control"}, kind)
        elif kind in ("CLK", "RESET", "RESETFEED") and len(fields) == 3:
            _, pin, net = fields
            if not net.strip() or len(net) > 180 or any(c.isspace() for c in net):
                raise ValueError(f"bad net at line {lineno}")
            allowed = {"CLK": CLOCK, "RESET": RESET, "RESETFEED": RESETFEED}[kind]
            destination = {"CLK": clocks, "RESET": resets, "RESETFEED": resetfeed}[kind]
            _unique(destination, pin, net, allowed, kind)
        else:
            raise ValueError(f"unexpected graph record at line {lineno}")
    for kind, actual, required in (
        ("META", meta, set(META)), ("DMA", dma, set(DMA)),
        ("LINK", links, LINKS), ("CLK", clocks, CLOCK),
        ("RESET", resets, RESET), ("PSCFG", pscfg, set(PSCFG)),
        ("RESETFEED", resetfeed, RESETFEED),
        ("RESETDIR", resetdir, set(RESETDIR)),
        ("RESETCFG", resetcfg, set(RESETCFG)),
        ("RESETINV", resetinv, set(RESETINV)),
        ("NATIVEINTF", native, NATIVE_INTF),
        ("NATIVEPIN", native_pins, set(NATIVE_PINS)),
        ("HLSINTF", hlsintf, {"s_axi_control"}),
    ):
        if set(actual) != required:
            missing = sorted(required - set(actual))
            extra = sorted(set(actual) - required)
            raise ValueError(f"wrong {kind} entries; missing={missing}, extra={extra}")
    if len(set(native.values())) != len(NATIVE_INTF):
        raise ValueError("native HLS AXIS interface nets alias each other")
    if set(native.values()) & set(links.values()):
        raise ValueError("native HLS scalar nets alias DMA/control/memory interfaces")
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
    if resetfeed["ps/pl_resetn0"] != resetfeed["reset_inv/Op1"]:
        raise ValueError("PS active-low reset is not connected to NOT inverter input")
    if resetfeed["reset_inv/Res"] != resetfeed["pl_reset/ext_reset_in"]:
        raise ValueError("NOT inverter output is not connected to Processor System Reset")
    if len(set(resetfeed.values())) != 2:
        raise ValueError("reset inversion requires two distinct actual Vivado nets")
    if set(resetfeed.values()) & set(resets.values()):
        raise ValueError("PS reset/inverter inputs and generated reset net aliased")
    if set(native.values()) & (set(clocks.values()) | set(resets.values()) | set(resetfeed.values())):
        raise ValueError("native neural stream net aliases clock or reset")
    if next(iter(clocks.values())) in set(resets.values()) | set(resetfeed.values()):
        raise ValueError("clock and reset unexpectedly same net")
    return {
        "stream_links": len(STREAM),
        "native_axis_interface_links": len(NATIVE_INTF),
        "native_scalar_pin_contracts": len(NATIVE_PINS),
        "control_links": len(CONTROL),
        "independent_control_banks": 6,
        "memory_links": len(MEMORY),
        "clock_consumers": len(CLOCK),
        "reset_consumers": len(RESET),
        "reset_input_pins": len(RESETFEED),
        "reset_inversion_stages": 1,
    }




def audit_address_inventory(source: str) -> dict[str, int]:
    """Only inventory six Vivado SLAVE segment lists and PS master spaces."""
    if type(source) is not str or not source.endswith("\n") or len(source) > 20000:
        raise ValueError("invalid Vivado read-only address inventory")
    lines = source.splitlines()
    if not lines or lines[0] != (
        "META|scope|OFFLINE_READ_ONLY_VIVADO_ADDRESS_INVENTORY_NOT_DECODE_PROOF"
    ):
        raise ValueError("not a read-only Vivado address discovery report")
    actual: dict[str, list[str]] = {}
    spaces: list[str] = []
    for row in lines[1:]:
        f = row.split("|")
        if len(f) == 4 and f[0] == "SLAVE":
            _, bank, intf, value = f
            if bank not in SLAVE_INTERFACES or intf != SLAVE_INTERFACES[bank]:
                raise ValueError("wrong original control slave in address inventory")
            if not value or value.isspace() or len(value) > 260:
                raise ValueError("invalid address slave segment path")
            # Vivado returns canonical bd_addr_seg object identity as
            # /<cell>/<actual AXI4-Lite interface>/<segment>. A matching
            # bank name alone is insufficient to prove which port owns it.
            full_interface = "/" + intf + "/"
            if value != "NO_BD_SEGMENT_YET" and (
                not value.startswith(full_interface)
                or not value[len(full_interface):].strip()
                or any(c.isspace() for c in value)
            ):
                raise ValueError("address segment belongs to wrong control slave interface")
            actual.setdefault(bank, []).append(value)
        elif len(f) == 3 and f[0] == "SPACE":
            if f[1] != "ps/M_AXI_HPM0_FPD" or not f[2] or len(f[2]) > 260:
                raise ValueError("not the real PS control master address space")
            spaces.append(f[2])
        elif row in ("META|address_assignment|NOT_RUN",
                     "META|physical_ddr|NOT_AUTHORIZED"):
            continue
        else:
            raise ValueError("unexpected address discovery record")
    if set(actual) != set(SLAVE_INTERFACES) or not spaces:
        raise ValueError("incomplete six slaves / PS master address inventory")
    for bank, parts in actual.items():
        if len(set(parts)) != len(parts):
            raise ValueError("duplicate Vivado address segment report")
        if len(parts) > 1 and "NO_BD_SEGMENT_YET" in parts:
            raise ValueError("contradictory missing and present Vivado segment")
    if len(set(spaces)) != len(spaces):
        raise ValueError("duplicate PS address space record")
    if lines.count("META|address_assignment|NOT_RUN") != 1 or (
        lines.count("META|physical_ddr|NOT_AUTHORIZED") != 1
    ):
        raise ValueError("missing read-only address status / physical restriction")
    return {
        "control_slave_banks_inventoried": len(actual),
        "slave_segments_exposed": sum(len([v for v in x if v != "NO_BD_SEGMENT_YET"])
                                      for x in actual.values()),
        "ps_control_address_spaces_reported": len(spaces),
        "assigned": 0,
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--inventory", type=Path, required=True)
    args = p.parse_args()
    try:
        status = audit_connected_candidate(args.report.read_text())
        inventory_status = audit_address_inventory(args.inventory.read_text())
    except (OSError, ValueError) as exc:
        p.exit(1, f"ERROR: M05.12d.3 independent genuine native AXIS interface graph audit: {exc}\n")
    print(f"PASS: M05.12d.3 independent grouped native AXIS HLS PS/PL graph audit {status} "
          f"and read-only Vivado address inventory {inventory_status} "
          "(NO ASSIGNED ADDRESS/DDR/FULL BD VALIDATION)")


if __name__ == "__main__":
    main()
