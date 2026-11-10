#!/usr/bin/env python3
"""Convert attested genuine HLS original-AMD idle TB into AXI-Lite active BFM.

ONLY deliberate bad-geometry early reject (neuron_count=0) is claimed.
The actual Vitis HLS controller must accept ap_start and publish status=1
without issuing neural memory writes or output streams. This is NOT full
neural inference/parity, faults, PS DDR or a physical FPGA run.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

CONTROL_INPUTS={
    "AWADDR":7,"AWVALID":1,"WDATA":32,"WSTRB":4,
    "WVALID":1,"BREADY":1,"ARADDR":7,"ARVALID":1,"RREADY":1,
}
OLD_START="""initial begin
    repeat(12) @(negedge clk);
    resetn=1;
    repeat(100) @(negedge clk);"""

def active_tb(idle: str, inv: dict, control: dict) -> str:
    if inv.get("status")!="REAL_HLS_RTL_AND_AMD_ABI_INVENTORIED_NOT_CONNECTED" or (
        inv.get("hls_port_count")!=125 or inv.get("g3_3_complete") is not False
    ):
        raise ValueError("genuine accepted 125-pin HLS inventory required")
    if control.get("schema")!="m06-g3-3-genuine-generated-hls-control-map-v1" or (
        control.get("status")!="REAL_HLS_AXILITE_CONTROL_OFFSETS_SHA_ATTESTED" or
        control.get("ap_ctrl")!=0 or not isinstance(control.get("ap_return"),int)
        or not 4<=control["ap_return"]<128
    ):
        raise ValueError("true generated Vitis HLS AXI-Lite control register map missing")
    top=inv.get("hls_complete_top_ports",{})
    for suffix,width in CONTROL_INPUTS.items():
        pin="s_axi_control_"+suffix
        if top.get(pin)!={"direction":"input","width_bits":width}:
            raise ValueError("HLS generated AXI-Lite port/role drift: "+pin)
    output=idle
    if output.count(OLD_START)!=1 or output.count(
        "M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS")!=1:
        raise ValueError("genuine generated-HLS idle TB anchor has changed")
    for suffix,width in CONTROL_INPUTS.items():
        name="h_s_axi_control_"+suffix
        dim=f"[{width-1}:0] " if width>1 else ""
        declaration="wire "+dim+name+";"
        if output.count(declaration)!=1:
            raise ValueError("HLS AXI-Lite wire declaration changed: "+name)
        output=output.replace(declaration,"reg "+dim+name+"=0;")
        pattern=r"(?m)^assign "+re.escape(name)+r" = \d+'d0; // IDLE: no start/inputs\n"
        output,n=re.subn(pattern,"",output)
        if n!=1:
            raise ValueError("HLS AXI-Lite inactive tieoff changed: "+name)
    output=output[:output.index(OLD_START)]
    active=r"""
integer ctrl_b_count=0, ctrl_r_count=0;
reg [31:0] observed_ctrl=0, observed_status=0;
task automatic write_start;
begin
    @(negedge clk);
    h_s_axi_control_AWADDR=7'h00;
    h_s_axi_control_AWVALID=1;
    h_s_axi_control_WDATA=32'h00000001;
    h_s_axi_control_WSTRB=4'hf;
    h_s_axi_control_WVALID=1;
    fork
        begin
            @(posedge clk);
            while (h_s_axi_control_AWREADY !== 1'b1) @(posedge clk);
            @(negedge clk); h_s_axi_control_AWVALID=0;
        end
        begin
            @(posedge clk);
            while (h_s_axi_control_WREADY !== 1'b1) @(posedge clk);
            @(negedge clk); h_s_axi_control_WVALID=0;
        end
    join
    @(posedge clk);
    while (h_s_axi_control_BVALID !== 1'b1) @(posedge clk);
    if (h_s_axi_control_BRESP !== 2'b00)
        $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL AXILITE_BRESP");
    @(negedge clk); h_s_axi_control_BREADY=1;
    @(posedge clk);
    @(negedge clk); h_s_axi_control_BREADY=0;
    ctrl_b_count=ctrl_b_count+1;
end
endtask
task automatic read_reg(input [6:0] addr, output [31:0] value);
begin
    @(negedge clk);
    h_s_axi_control_ARADDR=addr;
    h_s_axi_control_ARVALID=1;
    @(posedge clk);
    while (h_s_axi_control_ARREADY !== 1'b1) @(posedge clk);
    @(negedge clk); h_s_axi_control_ARVALID=0;
    @(posedge clk);
    while (h_s_axi_control_RVALID !== 1'b1) @(posedge clk);
    if (h_s_axi_control_RRESP !== 2'b00)
        $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL AXILITE_RRESP addr=%h",addr);
    value=h_s_axi_control_RDATA;
    @(negedge clk); h_s_axi_control_RREADY=1;
    @(posedge clk);
    @(negedge clk); h_s_axi_control_RREADY=0;
    ctrl_r_count=ctrl_r_count+1;
end
endtask
always @(posedge clk) if(resetn) begin
    if(h_m_axi_gmem_read_ARVALID || h_m_axi_gmem_write_AWVALID ||
       h_m_axi_gmem_write_WVALID || h_trace_TVALID || h_metrics_TVALID)
        $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL BAD_SHAPE_ACCESSED_MEMORY_OR_STREAM");
end
initial begin
    repeat(12) @(negedge clk); resetn=1;
    repeat(30) @(negedge clk);
    write_start();
    repeat(300) @(negedge clk);
    read_reg(7'h00,observed_ctrl);
    if (observed_ctrl[1] !== 1'b1)
        $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL AP_DONE=%h",observed_ctrl);
    read_reg(RETURN_ADDR,observed_status);
    if (observed_status !== 32'h00000001 ||
        ctrl_b_count!==1 || ctrl_r_count!==2)
        $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL STATUS=%h B=%0d R=%0d",
               observed_status,ctrl_b_count,ctrl_r_count);
    if(read_guard_fault || write_guard_fault)
        $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL ADDRESS_GUARD");
    $display("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_AXILITE_BAD_GEOMETRY_XSIM_PASS AP_DONE=1 STATUS=1 NO_CANONICAL_AXI_NO_NEURAL_PARITY_NO_BOARD");
    $finish;
end
initial begin
    #200000;
    $fatal(1,"M06_G3_3_HLS_ACTIVE_FAIL GLOBAL_WATCHDOG");
end
endmodule
"""
    output+=active.replace("RETURN_ADDR","7'h"+format(control["ap_return"],"02x"))
    output=output.replace(
        "module tb_m06_g3_3_actual_hls_original_amd_idle;",
        "module tb_m06_g3_3_actual_hls_original_amd_active;"
    )
    if "M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS" in output:
        raise ValueError("active HLS TB contains an obsolete IDLE PASS")
    return output

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idle-tb",required=True,type=Path)
    ap.add_argument("--accepted-inventory",required=True,type=Path)
    ap.add_argument("--control-map",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("output must be new file")
        value=active_tb(a.idle_tb.read_text(),
                        json.loads(a.accepted_inventory.read_text()),
                        json.loads(a.control_map.read_text()))
        a.output.write_text(value)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print("M06_G3_3_HLS_ACTIVE_CONTROL_TB_REJECTED:",error,file=sys.stderr)
        return 2
    print("M06_G3_3_ACTUAL_HLS_ACTIVE_AXILITE_BAD_GEOMETRY_TB_GENERATED NOT_XSIM_NOT_NEURAL_PARITY_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
