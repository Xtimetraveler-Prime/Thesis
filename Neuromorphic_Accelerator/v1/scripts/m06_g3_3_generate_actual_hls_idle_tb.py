#!/usr/bin/env python3
"""Generate a G3.3.1 genuine-HLS + original AMD *idle linkage* XSim TB.

The supplied inventory came from actual Vitis 2025.2 generated RTL. The TB
instantiates the real top and existing 64->32 guards, both original AMD 32->256
DWCs, original 96-pin SmartConnect, and simulated 64KiB scratch memory. It
runs RESET/IDLE ONLY; no AXI-Lite start, input streams, neural computation,
M02/M03 parity, fault tests or board/DDR. A PASS is NOT G3.3/G4 acceptance.
Original vendor and HLS generated RTL are referenced, not copied into Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from m06_generate_original_mem_sc_bfm import MODULE, original_ports, required_ports
from m06_g3_capture_dwc_ports import capture
from m06_g3_generate_real_dwc_original_sc_bfm import (
    MEMORY, ROLE, _bit_decl, exact_dwc_abi,
)
from m06_g3_3_hls_inventory import source_inventory
from m06_paged_hls_port_audit import TOP, parse_top

SOURCE_SUFFIXES = {
    "gmem_read": {"ARREADY", "RDATA", "RID", "RRESP", "RLAST", "RVALID"},
    "gmem_write": {"AWREADY", "WREADY", "BID", "BRESP", "BVALID"},
}
READ_SIDE = ("ARID", "ARADDR", "ARLEN", "ARSIZE", "ARBURST", "ARVALID",
             "ARREADY", "RID", "RDATA", "RRESP", "RLAST", "RVALID", "RREADY")
WRITE_SIDE = ("AWID", "AWADDR", "AWLEN", "AWSIZE", "AWBURST", "AWVALID",
              "AWREADY", "WDATA", "WSTRB", "WLAST", "WVALID", "WREADY",
              "BID", "BRESP", "BVALID", "BREADY")
READ_SI = {
    "arid": "g_rd_arid", "araddr": "g_rd_araddr",
    "arlen": "g_rd_arlen", "arsize": "g_rd_arsize",
    "arburst": "g_rd_arburst", "arvalid": "g_rd_arvalid",
    "arready": "d_rd_arready", "rready": "g_rd_rready",
    "rid": "d_rd_rid", "rdata": "d_rd_rdata",
    "rresp": "d_rd_rresp", "rlast": "d_rd_rlast",
    "rvalid": "d_rd_rvalid",
}
WRITE_SI = {
    "awid": "g_wr_awid", "awaddr": "g_wr_awaddr",
    "awlen": "g_wr_awlen", "awsize": "g_wr_awsize",
    "awburst": "g_wr_awburst", "awvalid": "g_wr_awvalid",
    "awready": "d_wr_awready",
    "wdata": "g_wr_wdata", "wstrb": "g_wr_wstrb",
    "wlast": "g_wr_wlast", "wvalid": "g_wr_wvalid",
    "wready": "d_wr_wready",
    "bid": "d_wr_bid", "bresp": "d_wr_bresp",
    "bvalid": "d_wr_bvalid", "bready": "g_wr_bready",
}
ROUTE_TO_HLS = {
    "gmem_read": {
        "ARREADY": "rd_s_arready", "RID": "rd_s_rid",
        "RDATA": "rd_s_rdata", "RRESP": "rd_s_rresp",
        "RLAST": "rd_s_rlast", "RVALID": "rd_s_rvalid",
    },
    "gmem_write": {
        "AWREADY": "wr_s_awready", "WREADY": "wr_s_wready",
        "BID": "wr_s_bid", "BRESP": "wr_s_bresp",
        "BVALID": "wr_s_bvalid",
    },
}
EXPECTED_HLS = {
    "gmem_read": {"ARADDR": 64, "ARID": 1, "ARLEN": 8, "ARSIZE": 3,
                  "ARLOCK": 2, "ARREGION": 4, "ARUSER": 1, "RDATA": 32},
    "gmem_write": {"AWADDR": 64, "AWID": 1, "AWLEN": 8, "AWSIZE": 3,
                   "AWLOCK": 2, "AWREGION": 4, "AWUSER": 1,
                   "WDATA": 32, "WSTRB": 4},
}

def _decl(width: int) -> str:
    if not 1<=width<=256:
        raise ValueError("unsupported G3.3.1 signal width")
    return _bit_decl(width)

def _h(role: str, suffix: str) -> str:
    return "h_m_axi_"+role+"_"+suffix

def validate_inventory(inv: dict, generated_rtl: Path) -> dict:
    if inv.get("schema")!="m06-g3-3-real-hls-rtl-interface-inventory-v1" or (
        inv.get("status")!="REAL_HLS_RTL_AND_AMD_ABI_INVENTORIED_NOT_CONNECTED" or
        inv.get("hls_top")!=TOP or inv.get("g3_2_verified_bfm_only") is not True or
        inv.get("original_vendor_xsim_with_actual_HLS") is not False or
        inv.get("g3_3_complete") is not False
    ):
        raise ValueError("G3.3.1 demands independently accepted genuine HLS input inventory")
    sources=source_inventory(generated_rtl)
    if sources!=inv.get("hls_rtl_file_inventory") or len(sources)!=40:
        raise ValueError("real generated 40-file HLS RTL source hashes changed")
    file=generated_rtl/(TOP+".v")
    pins=parse_top(file.read_text(encoding="utf8",errors="replace"))
    listed=inv.get("hls_complete_top_ports")
    expected={k:{"direction":v[0],"width_bits":v[1]} for k,v in pins.items()}
    if expected!=listed or len(pins)!=125 or (
        hashlib.sha256(file.read_bytes()).hexdigest()!=inv.get("hls_real_top_sha256")
    ):
        raise ValueError("genuine Vitis HLS 125-pin top changed after audit")
    for bundle,needed in EXPECTED_HLS.items():
        for name,width in needed.items():
            full="m_axi_"+bundle+"_"+name
            if pins.get(full)!=(("input" if name in ("RDATA",) else "output"),width):
                raise ValueError("G3.3 HLS master pin mismatch: "+full)
    for bundle,inputs in SOURCE_SUFFIXES.items():
        for name in inputs:
            if pins.get(_h(bundle,name)[2:],(None,None))[0]!="input":
                raise ValueError("HLS master response pin missing: "+_h(bundle,name))
    for name in ("ap_clk","ap_rst_n"):
        if pins.get(name)!=("input",1):
            raise ValueError("HLS clock/reset missing: "+name)
    for name,role in (("neurons","input"),("synapses","input"),
                      ("external_events","input"),("trace","output"),("metrics","output")):
        for suffix,direction in (
            ("TDATA",role),("TVALID",role),
            ("TREADY","output" if role=="input" else "input")
        ):
            if pins.get(name+"_"+suffix,(None,None))[0]!=direction:
                raise ValueError("HLS stream pin missing: "+name+"_"+suffix)
    for k in pins:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",k):
            raise ValueError("HLS pin name is not legal")
        if k.startswith("m_axi_") and not (
            k.startswith("m_axi_gmem_read_") or k.startswith("m_axi_gmem_write_")
        ):
            raise ValueError("unexpected HLS master bundle: "+k)
    return pins

def render(pins: dict, dwc: dict, vendor: list[dict]) -> str:
    required=required_ports()
    actual={p["name"]:(p["direction"],p["packed_width"]) for p in vendor}
    if actual!=required or len(vendor)!=96:
        raise ValueError("original 96-pin SmartConnect ABI mismatch")
    if set(dwc.get("instances",{}))!={x[0] for x in ROLE}:
        raise ValueError("original dual DWC evidence missing")
    for ip,sc in ROLE:
        if dwc["instances"][ip]["pins"]!=exact_dwc_abi(sc,required):
            raise ValueError("genuine DWC "+ip+" pin ABI drift")
    lines=[
        "// TRUE generated Vitis HLS RTL plus ORIGINAL AMD: RESET/IDLE ONLY.",
        "// NO FAKE IP, NO NEURAL EXECUTION, NO PS DDR/FPGA/JTAG.",
        chr(96)+"timescale 1ns/1ps",
        "module tb_m06_g3_3_actual_hls_original_amd_idle;",
        "reg clk=0; always #5 clk=~clk;",
        "reg resetn=0;",
    ]
    for name,(_,width) in required.items():
        lines.append("wire "+_decl(width)+name+";")
        if name.startswith(("S01_AXI_","S02_AXI_")) and required[name][0]=="input":
            lines.append("assign "+name+" = "+str(width)+"'d0;")
    lines.append(MODULE+" sc_dut (\n    .aclk(clk), .aresetn(resetn),\n"+
        ",\n".join("    ."+p["name"]+"("+p["name"]+")" for p in vendor)+"\n);")
    # Declare EVERY HLS/guard net before first use by any DWC or assign.
    # The first genuine XSim idle owner log exposed 8 implicit HLS sideband
    # nets and 11 forward guard signal declarations: eliminate both.
    for name,(_,width) in sorted(pins.items()):
        if name not in ("ap_clk","ap_rst_n"):
            lines.append("wire "+_decl(width)+"h_"+name+";")
    for bundle in ("gmem_read","gmem_write"):
        for suffix,source in ROUTE_TO_HLS[bundle].items():
            hprefix="rd_s" if bundle=="gmem_read" else "wr_s"
            width=pins["m_axi_"+bundle+"_"+suffix][1]
            lines.append("wire "+_decl(width)+source+";")
    # Exact original AMD SI/MI port bindings and mandatory guard insertion.
    declared=set()
    for ip,sc in ROLE:
        port_map=[]
        side=READ_SI if sc=="S00" else WRITE_SI
        bundle="gmem_read" if sc=="S00" else "gmem_write"
        for name,props in sorted(dwc["instances"][ip]["pins"].items()):
            direction,width=props["direction"],props["width_bits"]
            if name=="s_axi_aclk":
                net="clk"
            elif name=="s_axi_aresetn":
                net="resetn"
            elif name.startswith("s_axi_"):
                suffix=name[len("s_axi_"):]
                if suffix in side:
                    net=side[suffix]
                elif suffix in ("arlock","awlock"):
                    net=_h(bundle,suffix.upper())+"[0]"
                elif suffix in ("arregion","awregion","arcache","awcache",
                                "arprot","awprot","arqos","awqos"):
                    net=_h(bundle,suffix.upper())
                else:
                    raise ValueError("unhandled original AMD DWC SI pin: "+name)
                if re.fullmatch(r"[gd]_(rd|wr)_[a-z0-9_]+",net) and net not in declared:
                    lines.append("wire "+_decl(width)+net+";")
                    declared.add(net)
            elif name.startswith("m_axi_"):
                suffix=name[len("m_axi_"):]
                net=sc+"_AXI_"+suffix
                if net not in required:
                    if suffix in ("arregion","awregion") and direction=="output" and width==4:
                        net=""  # The original 96-pin SC has no REGION input.
                    else:
                        raise ValueError("DWC MI pin cannot bind to original SC: "+name)
            else:
                raise ValueError("unexpected original AMD DWC signal: "+name)
            port_map.append("    ."+name+"("+net+")")
        lines.append(ip+" "+ip+"_dut (\n"+",\n".join(port_map)+"\n);")
    # The REAL HLS top is connected for all 125 pins, including inactive
    # masters and stream/control pins; absent signals are never left floating.
    for bundle in ("gmem_read","gmem_write"):
        for suffix,source in ROUTE_TO_HLS[bundle].items():
            lines.append("assign "+_h(bundle,suffix)+" = "+source+";")
        for name,(direction,width) in sorted(pins.items()):
            prefix="m_axi_"+bundle+"_"
            if not name.startswith(prefix) or direction!="input":
                continue
            suffix=name[len(prefix):]
            if suffix in ROUTE_TO_HLS[bundle]:
                continue
            lines.append("assign h_"+name+" = "+str(width)+"'d0;"+
                         " // Unsupported/unused channel never acknowledged")
    for name,(direction,width) in sorted(pins.items()):
        if direction!="input" or name in ("ap_clk","ap_rst_n"):
            continue
        if name.startswith("m_axi_"):
            continue
        if name.endswith("_TREADY") and name.startswith(("trace_","metrics_")):
            lines.append("assign h_"+name+" = 1'b1; // sink ready while idle")
        else:
            lines.append("assign h_"+name+" = "+str(width)+"'d0; // IDLE: no start/inputs")
    ports=[]
    for name in sorted(pins):
        net="clk" if name=="ap_clk" else "resetn" if name=="ap_rst_n" else "h_"+name
        ports.append("    ."+name+"("+net+")")
    lines.append(TOP+" hls_dut (\n"+",\n".join(ports)+"\n);")
    # READ address guard. The RD DWC SI is driven by guard m_*, while R
    # responses flow back through it to the actual generated HLS core.
    # Guard return-path wires were predeclared above before their first use.
    for prefix,names in (("g_rd",("arid","araddr","arlen","arsize","arburst",
                                 "arvalid","rready")),
                         ("g_wr",("awid","awaddr","awlen","awsize","awburst",
                                 "awvalid","wdata","wstrb","wlast","wvalid","bready"))):
        # Already declared through SI-port traversal.
        for n in names:
            if prefix+"_"+n not in declared:
                raise ValueError("guard SI net missing from genuine DWC: "+prefix+"_"+n)
    for prefix,names in (("d_rd",("arready","rid","rdata","rresp","rlast","rvalid")),
                         ("d_wr",("awready","wready","bid","bresp","bvalid"))):
        for n in names:
            if prefix+"_"+n not in declared:
                raise ValueError("DWC response net missing: "+prefix+"_"+n)
    rports={name: _h("gmem_read",name[2:].upper()) for name in READ_SIDE if name.startswith("s_")}
    rd_args = {
        "s_arid":_h("gmem_read","ARID"),"s_araddr":_h("gmem_read","ARADDR"),
        "s_arlen":_h("gmem_read","ARLEN"),"s_arsize":_h("gmem_read","ARSIZE"),
        "s_arburst":_h("gmem_read","ARBURST"),"s_arvalid":_h("gmem_read","ARVALID"),
        "s_arready":"rd_s_arready","m_arid":"g_rd_arid","m_araddr":"g_rd_araddr",
        "m_arlen":"g_rd_arlen","m_arsize":"g_rd_arsize",
        "m_arburst":"g_rd_arburst","m_arvalid":"g_rd_arvalid",
        "m_arready":"d_rd_arready",
        "m_rid":"d_rd_rid","m_rdata":"d_rd_rdata","m_rresp":"d_rd_rresp",
        "m_rlast":"d_rd_rlast","m_rvalid":"d_rd_rvalid","m_rready":"g_rd_rready",
        "s_rid":"rd_s_rid","s_rdata":"rd_s_rdata","s_rresp":"rd_s_rresp",
        "s_rlast":"rd_s_rlast","s_rvalid":"rd_s_rvalid","s_rready":_h("gmem_read","RREADY"),
        "fault_seen":"read_guard_fault",
    }
    wr_args = {
        "s_awid":_h("gmem_write","AWID"),"s_awaddr":_h("gmem_write","AWADDR"),
        "s_awlen":_h("gmem_write","AWLEN"),"s_awsize":_h("gmem_write","AWSIZE"),
        "s_awburst":_h("gmem_write","AWBURST"),"s_awvalid":_h("gmem_write","AWVALID"),
        "s_awready":"wr_s_awready","m_awid":"g_wr_awid","m_awaddr":"g_wr_awaddr",
        "m_awlen":"g_wr_awlen","m_awsize":"g_wr_awsize",
        "m_awburst":"g_wr_awburst","m_awvalid":"g_wr_awvalid",
        "m_awready":"d_wr_awready",
        "s_wdata":_h("gmem_write","WDATA"),"s_wstrb":_h("gmem_write","WSTRB"),
        "s_wlast":_h("gmem_write","WLAST"),"s_wvalid":_h("gmem_write","WVALID"),
        "s_wready":"wr_s_wready","m_wdata":"g_wr_wdata","m_wstrb":"g_wr_wstrb",
        "m_wlast":"g_wr_wlast","m_wvalid":"g_wr_wvalid","m_wready":"d_wr_wready",
        "s_bid":"wr_s_bid","s_bresp":"wr_s_bresp","s_bvalid":"wr_s_bvalid",
        "s_bready":_h("gmem_write","BREADY"),
        "m_bid":"d_wr_bid","m_bresp":"d_wr_bresp","m_bvalid":"d_wr_bvalid",
        "m_bready":"g_wr_bready","fault_seen":"write_guard_fault",
    }
    for module,inst,bindings in (
        ("m06_axi64_to32_read_guard","rd_guard",rd_args),
        ("m06_axi64_to32_write_guard","wr_guard",wr_args),
    ):
        lines.append("wire "+("read_guard_fault" if inst=="rd_guard" else "write_guard_fault")+";")
        entries=["    .aclk(clk)","    .aresetn(resetn)"]
        entries.extend("    ."+k+"("+v+")" for k,v in bindings.items())
        lines.append(module+" "+inst+" (\n"+",\n".join(entries)+"\n);")
    lines.append("m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536)) ram (\n"+
        "    .aclk(clk), .aresetn(resetn),\n"+
        ",\n".join("    .s_axi_"+s+"(M00_AXI_"+s+")" for s in MEMORY)+
        ",\n    .inject_next_b_slverr(1'b0), .inject_next_r_slverr(1'b0)\n);")
    # Wide HLS locks must not be silently truncated. Region, user, unused
    # master channels and WID are not supported by original 96-pin SC.
    lines.append("""
always @(posedge clk) if(resetn) begin
    if(read_guard_fault || write_guard_fault)
        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL GUARD_FAULT");
    if(h_m_axi_gmem_read_ARVALID &&
       (h_m_axi_gmem_read_ARLOCK!==2'b00 ||
        h_m_axi_gmem_read_ARREGION!==4'b0 ||
        h_m_axi_gmem_read_ARUSER!==1'b0))
        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL READ_SIDEBAND");
    if(h_m_axi_gmem_write_AWVALID &&
       (h_m_axi_gmem_write_AWLOCK!==2'b00 ||
        h_m_axi_gmem_write_AWREGION!==4'b0 ||
        h_m_axi_gmem_write_AWUSER!==1'b0))
        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL WRITE_SIDEBAND");
    if(h_m_axi_gmem_write_WVALID &&
       (h_m_axi_gmem_write_WUSER!==1'b0 ||
        h_m_axi_gmem_write_WID!==1'b0))
        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL W_SIDEBAND");
    if(h_m_axi_gmem_read_AWVALID || h_m_axi_gmem_read_WVALID ||
       h_m_axi_gmem_write_ARVALID)
        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL WRONG_MASTER_DIRECTION");
end
initial begin
    repeat(12) @(negedge clk);
    resetn=1;
    repeat(100) @(negedge clk);
    if(read_guard_fault || write_guard_fault)
        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL POST_IDLE_GUARD_FAULT");
    $display("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS 40_REAL_HLS_RTL 2_REAL_AMD_DWC ORIGINAL_SC 64K_SCRATCH GUARDS_CONNECTED NO_START_NO_NEURAL_NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #200000;
    $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL GLOBAL_WATCHDOG");
end
endmodule
""")
    code="\n".join(lines)+"\n"
    if code.count("module tb_m06_g3_3_actual_hls_original_amd_idle;")!=1:
        raise ValueError("bad generated TB shell")
    return code

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ("inventory","hls-verilog","original-d3","original-headers",
                "original-dwc","output"):
        ap.add_argument("--"+key,required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("output must be new in existing directory")
        inv=json.loads(a.inventory.read_text())
        pins=validate_inventory(inv,a.hls_verilog)
        vendor=original_ports(a.original_d3.resolve(strict=True),
                              json.loads(a.original_headers.read_text()))
        dwc=capture(a.original_dwc)
        code=render(pins,dwc,vendor)
        a.output.write_text(code,encoding="utf8")
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as e:
        print("M06_G3_3_REAL_HLS_LINK_GENERATOR_REJECTED:",e,file=sys.stderr)
        return 2
    print("M06_G3_3_REAL_HLS_ORIGINAL_AMD_IDLE_LINK_TB_GENERATED NOT_XSIM_NOT_NEURAL_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
