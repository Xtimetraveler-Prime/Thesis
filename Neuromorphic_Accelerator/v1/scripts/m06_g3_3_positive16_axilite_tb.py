#!/usr/bin/env python3
"""Generate a source-only prospective G3.3 positive-16 neural/AXI smoke.

Reuses the SHA-attested original-HLS AXI-Lite register map and the previously
verified actual-HLS/AMD connected bench. Only a one-tick/16-neuron candidate;
independent M02/M03 full trace/fault parity and owner Vivado remain OPEN.
No proprietary generated HLS/AMD RTL is synthesized, copied, or modified here.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import sys

from m06_g3_3_active_axilite_tb import active_tb

# Register *names* are architectural requirements; numeric offsets MUST come
# from original SHA-attested control_s_axi.v, not this source.
REQUIRED = (
    "CANONICAL_READ_WORDS_DATA_0", "CANONICAL_READ_WORDS_DATA_1",
    "CANONICAL_WRITE_WORDS_DATA_0", "CANONICAL_WRITE_WORDS_DATA_1",
    "NEURON_COUNT_DATA_0", "SYNAPSE_COUNT_DATA_0",
    "EXTERNAL_COUNT_DATA_0", "TICKS_DATA_0", "DECAY_NUM_DATA_0",
    "DECAY_DEN_DATA_0", "RESIDENT_SLOTS_DATA_0",
    "CANONICAL_FIRST_NEURON_DATA_0",
)
ANCHOR = "integer ctrl_b_count=0, ctrl_r_count=0;"


def positive_tb(idle: str, inventory: dict, control: dict) -> str:
    # This invokes the established original-inventory, role, and register-map
    # checks. Its negative-shape smoke is discarded; nothing is run twice.
    active = active_tb(idle, inventory, control)
    offsets = control.get("register_offsets")
    if not isinstance(offsets, dict):
        raise ValueError("positive test requires measured original register_offsets")
    keys = ("AP_CTRL", *REQUIRED)
    for key in keys:
        value = offsets.get(key)
        if type(value) is not int or not 0 <= value < 128 or value % 4:
            raise ValueError("missing/invalid original HLS AXI-Lite register: " + key)
    if offsets["AP_CTRL"] != control["ap_ctrl"]:
        raise ValueError("HLS AP_CTRL identity drift")
    if control["ap_return"] not in (
        offsets.get("AP_RETURN"), offsets.get("AP_RETURN_0")
    ):
        raise ValueError("HLS AP_RETURN identity drift")
    if len({offsets[k] for k in keys}) != len(keys):
        raise ValueError("duplicate required original HLS register addresses")
    if active.count(ANCHOR) != 1:
        raise ValueError("original active AXI-Lite task anchor changed")
    output = active[:active.index(ANCHOR)]
    for name, old, new in (
        ("h_neurons_TDATA", "wire [127:0] h_neurons_TDATA;",
         "reg [127:0] h_neurons_TDATA=0;"),
        ("h_neurons_TVALID", "wire h_neurons_TVALID;",
         "reg h_neurons_TVALID=0;"),
    ):
        if output.count(old) != 1:
            raise ValueError("original HLS stream declaration drift: " + name)
        output = output.replace(old, new)
    for old in (
        "assign h_neurons_TDATA = 128'd0; // IDLE: no start/inputs\n",
        "assign h_neurons_TVALID = 1'd0; // IDLE: no start/inputs\n",
    ):
        if output.count(old) != 1:
            raise ValueError("original HLS stream tieoff drift")
        output = output.replace(old, "")
    if output.count("module tb_m06_g3_3_actual_hls_original_amd_active;") != 1:
        raise ValueError("original active HLS top module drift")
    output = output.replace(
        "module tb_m06_g3_3_actual_hls_original_amd_active;",
        "module tb_m06_g3_3_actual_hls_original_amd_positive16;",
    )
    # Low 32-bit canonical bases are *simulation-only* 0x00000000 in the
    # independently owned 64KiB scratch. This is NOT a physical DDR address.
    # Neuron stream: 4 x signed32, assumed Vitis aggregate field0 in LSB;
    # the genuine owner trial must verify this actual HLS packing, not CI.
    tail = r"""
integer ctrl_b_count=0, ctrl_r_count=0;
integer trace_count=0, metrics_count=0;
integer read_ar_count=0, write_aw_count=0, write_b_count=0;
integer polls=0;
reg [31:0] observed_ctrl=0, observed_status=32'hffffffff;

task automatic write_reg(input [6:0] addr, input [31:0] value);
begin
    @(negedge clk);
    h_s_axi_control_AWADDR=addr;
    h_s_axi_control_AWVALID=1;
    h_s_axi_control_WDATA=value;
    h_s_axi_control_WSTRB=4'hf;
    h_s_axi_control_WVALID=1;
    fork
        begin
            @(posedge clk);
            while(h_s_axi_control_AWREADY !== 1'b1) @(posedge clk);
            @(negedge clk); h_s_axi_control_AWVALID=0;
        end
        begin
            @(posedge clk);
            while(h_s_axi_control_WREADY !== 1'b1) @(posedge clk);
            @(negedge clk); h_s_axi_control_WVALID=0;
        end
    join
    @(posedge clk);
    while(h_s_axi_control_BVALID !== 1'b1) @(posedge clk);
    if(h_s_axi_control_BRESP !== 2'b00)
        $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL AXILITE_BRESP addr=%h",addr);
    @(negedge clk); h_s_axi_control_BREADY=1;
    @(posedge clk);
    @(negedge clk); h_s_axi_control_BREADY=0;
    ctrl_b_count=ctrl_b_count+1;
end
endtask

task automatic read_reg(input [6:0] addr, output [31:0] value);
begin
    @(negedge clk); h_s_axi_control_ARADDR=addr; h_s_axi_control_ARVALID=1;
    @(posedge clk);
    while(h_s_axi_control_ARREADY !== 1'b1) @(posedge clk);
    @(negedge clk); h_s_axi_control_ARVALID=0;
    @(posedge clk);
    while(h_s_axi_control_RVALID !== 1'b1) @(posedge clk);
    if(h_s_axi_control_RRESP !== 2'b00)
        $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL AXILITE_RRESP addr=%h",addr);
    value=h_s_axi_control_RDATA;
    @(negedge clk); h_s_axi_control_RREADY=1;
    @(posedge clk);
    @(negedge clk); h_s_axi_control_RREADY=0;
    ctrl_r_count=ctrl_r_count+1;
end
endtask

task automatic feed_neurons;
integer n;
begin
    for(n=0;n<16;n=n+1) begin
        @(negedge clk);
        // {reset=0,threshold=5,bias=0,initial=(n==0 ? 1 : 0)}
        h_neurons_TDATA = (n==0) ?
            128'h00000000_00000005_00000000_00000001 :
            128'h00000000_00000005_00000000_00000000;
        h_neurons_TVALID=1;
        @(posedge clk);
        while(h_neurons_TREADY !== 1'b1) @(posedge clk);
        @(negedge clk); h_neurons_TVALID=0;
    end
end
endtask

always @(posedge clk) if(resetn) begin
    if(h_trace_TVALID && h_trace_TREADY) begin
        trace_count=trace_count+1;
        if(^h_trace_TDATA === 1'bx)
            $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL UNKNOWN_TRACE");
    end
    if(h_metrics_TVALID && h_metrics_TREADY) begin
        metrics_count=metrics_count+1;
        if(^h_metrics_TDATA === 1'bx)
            $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL UNKNOWN_METRICS");
    end
    if(h_m_axi_gmem_read_ARVALID && h_m_axi_gmem_read_ARREADY)
        read_ar_count=read_ar_count+1;
    if(h_m_axi_gmem_write_AWVALID && h_m_axi_gmem_write_AWREADY)
        write_aw_count=write_aw_count+1;
    if(h_m_axi_gmem_write_BVALID && h_m_axi_gmem_write_BREADY)
        write_b_count=write_b_count+1;
end

initial begin
    repeat(12) @(negedge clk); resetn=1;
    repeat(30) @(negedge clk);
    fork
        feed_neurons();
        begin
            write_reg(@CANONICAL_READ_WORDS_DATA_0@,32'd0);
            write_reg(@CANONICAL_READ_WORDS_DATA_1@,32'd0);
            write_reg(@CANONICAL_WRITE_WORDS_DATA_0@,32'd0);
            write_reg(@CANONICAL_WRITE_WORDS_DATA_1@,32'd0);
            write_reg(@NEURON_COUNT_DATA_0@,32'd16);
            write_reg(@SYNAPSE_COUNT_DATA_0@,32'd0);
            write_reg(@EXTERNAL_COUNT_DATA_0@,32'd0);
            write_reg(@TICKS_DATA_0@,32'd1);
            write_reg(@DECAY_NUM_DATA_0@,32'd1);
            write_reg(@DECAY_DEN_DATA_0@,32'd1);
            write_reg(@RESIDENT_SLOTS_DATA_0@,32'd1);
            write_reg(@CANONICAL_FIRST_NEURON_DATA_0@,32'd0);
            write_reg(@AP_CTRL@,32'd1);
            // AP_DONE clears on read. Poll with a bounded testbench watchdog.
            while(observed_ctrl[1] !== 1'b1 && polls < 2000) begin
                repeat(50) @(negedge clk);
                read_reg(@AP_CTRL@,observed_ctrl);
                polls=polls+1;
            end
            if(observed_ctrl[1] !== 1'b1)
                $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL AP_DONE_TIMEOUT");
            read_reg(@AP_RETURN@,observed_status);
        end
    join
    repeat(10) @(negedge clk);
    if(observed_status !== 32'd0 || ctrl_b_count !== 13)
        $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL BAD_STATUS=%h WRITES=%0d",
               observed_status,ctrl_b_count);
    if(trace_count !== 16 || metrics_count !== 1 ||
       read_ar_count < 1 || write_aw_count < 1 || write_b_count < 1)
        $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL IO_COUNTS trace=%0d metrics=%0d read=%0d write=%0d b=%0d",
               trace_count,metrics_count,read_ar_count,write_aw_count,write_b_count);
    // First canonical row: v=1, tick watermark=1; other rows were zeroed.
    if(ram.mem[0] !== 8'h01 || ram.mem[1] !== 8'h00 ||
       ram.mem[4] !== 8'h01 || ram.mem[5] !== 8'h00 ||
       ram.mem[16] !== 8'h00 || ram.mem[256] !== 8'h11)
        $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL CANONICAL_BYTES");
    if(read_guard_fault || write_guard_fault)
        $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL ADDRESS_GUARD");
    $display("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS STATUS=0 TRACE=16 METRICS=1 CANONICAL_READ_WRITE NO_M02_M03_PARITY_NO_BOARD");
    $finish;
end
initial begin
    #5000000;
    $fatal(1,"M06_G3_3_HLS_POSITIVE_FAIL GLOBAL_WATCHDOG");
end
endmodule
"""
    for key in (*keys[1:], "AP_CTRL"):
        tail = tail.replace("@" + key + "@", "7'h" + format(offsets[key], "02x"))
    tail = tail.replace("@AP_RETURN@", "7'h" + format(control["ap_return"], "02x"))
    if re.search(r"@[A-Z][A-Z0-9_]*@", tail):
        raise ValueError("unresolved original HLS register placeholder")
    return output + tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idle-tb", required=True, type=Path)
    ap.add_argument("--accepted-inventory", required=True, type=Path)
    ap.add_argument("--control-map", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("output must be new file")
        value = positive_tb(a.idle_tb.read_text(),
                            json.loads(a.accepted_inventory.read_text()),
                            json.loads(a.control_map.read_text()))
        a.output.write_text(value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("M06_G3_3_POSITIVE16_TB_REJECTED:", error, file=sys.stderr)
        return 2
    print("M06_G3_3_POSITIVE16_HLS_AMD_TB_GENERATED SOURCE_ONLY_NO_XSIM_NO_PARITY_NO_BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
