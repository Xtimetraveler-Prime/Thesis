#!/usr/bin/env python3
"""M06 existing G4: REAL ORIGINAL-HLS+AMD read SLVERR / withheld B owner benches.

Source generation ONLY. Both tests require NEW genuine Vivado 2025.2 XSim.
Reuses accepted first-write-B error source-attested original HLS + AMD
integration. Does NOT use fabricated HLS or AMD functional simulation.
No physical DDR, rollback or trace-release hardware is claimed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

from m06_g4_actual_hls_write_fault_tb import generate as g4_first_b
from m06_g3_3_positive16_axilite_tb import REQUIRED, ANCHOR

MODES={
    "g4_first_r_slverr":(
        "tb_m06_g4_actual_hls_original_amd_first_r_slverr",
        "M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS"),
    "g4_stalled_b":(
        "tb_m06_g4_actual_hls_original_amd_stalled_b",
        "M06_G4_ACTUAL_HLS_AMD_STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS"),
}
TAIL_ANCHOR="// G4 condition is observable only at a REAL original AMD/HLS AXI response,"

def replace_once(s: str, a: str, b: str) -> str:
    if s.count(a)!=1:
        raise ValueError("original connected G4 testbench identity drift: "+a[:85])
    return s.replace(a,b)

def g4_fault_tb(idle: str, inventory: dict, control: dict, mode: str) -> str:
    if mode not in MODES:
        raise ValueError("unsupported G4 original-AMD connected fault case")
    base=g4_first_b(idle,inventory,control)
    if base.count(TAIL_ANCHOR)!=1 or base.count(ANCHOR)!=1:
        raise ValueError("G4 earlier accepted owner testbench drift")
    src=base[:base.index(TAIL_ANCHOR)]
    src=replace_once(src,"module tb_m06_g4_actual_hls_original_amd_first_b_slverr;",
                     "module "+MODES[mode][0]+";")
    if mode=="g4_first_r_slverr":
        src=replace_once(src,"reg inject_first_b=1'b1;",
                             "reg inject_first_r=1'b1;")
        src=replace_once(src,
            ".inject_next_b_slverr(inject_first_b), .inject_next_r_slverr(1'b0)",
            ".inject_next_b_slverr(1'b0), .inject_next_r_slverr(inject_first_r)")
    else:
        src=replace_once(src,"reg inject_first_b=1'b1;",
                             "reg hold_first_b=1'b1;")
        src=replace_once(src,
            ".inject_next_b_slverr(inject_first_b), .inject_next_r_slverr(1'b0)",
            ".inject_next_b_slverr(1'b0), .inject_next_r_slverr(1'b0)")
        # Keep ORIGINAL AMD SmartConnect/DWC untouched. Interpose only on
        # the SIMULATION-ONLY memory endpoint's first B channel. Raw RAM
        # retains a pending BVALID until the owner explicitly restores
        # service; no HLS/AMD fake response is generated or forced.
        src=replace_once(src,
            "wire M00_AXI_bready;",
            """wire M00_AXI_bready;
wire raw_ram_bvalid, raw_ram_bready;
wire [1:0] raw_ram_bresp;
assign M00_AXI_bvalid = raw_ram_bvalid && !hold_first_b;
assign M00_AXI_bresp = raw_ram_bresp;
assign raw_ram_bready = M00_AXI_bready && !hold_first_b;""")
        src=replace_once(src,
            ".s_axi_bresp(M00_AXI_bresp),",
            ".s_axi_bresp(raw_ram_bresp),")
        src=replace_once(src,
            ".s_axi_bvalid(M00_AXI_bvalid),",
            ".s_axi_bvalid(raw_ram_bvalid),")
        src=replace_once(src,
            ".s_axi_bready(M00_AXI_bready),",
            ".s_axi_bready(raw_ram_bready),")
    offsets={key:"7'h"+format(control["register_offsets"][key],"02x")
             for key in (*REQUIRED,"AP_CTRL")}
    prefix=src
    tail=READ_TAIL if mode=="g4_first_r_slverr" else STALL_TAIL
    for key,value in offsets.items():
        tail=tail.replace("@"+key+"@",value)
    if re.search(r"@[A-Z][A-Z0-9_]*@",tail):
        raise ValueError("genuine original HLS AXI-Lite map unresolved")
    return prefix+tail

# Tasks and AXI-Lite transaction helpers are included in inherited src.
# The original generated HLS contract is NOT changed.
READ_TAIL=r"""
reg g4_epoch_begin=0, g4_done=0;
wire g4_active,g4_commit,g4_poison;
wire [15:0] g4_outstanding;
integer first_ram_ar=0, ram_r_slverr=0, hls_r_slverr=0;
integer provisional_trace=0, published_trace=0, fault_polls=0;
reg first_ar_seen=0;
m06_g4_epoch_commit_gate #(.MAX_EPOCH_CYCLES(1000000)) epoch_gate (
    .aclk(clk),.aresetn(resetn),
    .epoch_begin(g4_epoch_begin),.ap_done(g4_done),.ap_return(observed_status),
    .read_guard_fault(read_guard_fault),.write_guard_fault(write_guard_fault),
    .write_aw_fire(h_m_axi_gmem_write_AWVALID && h_m_axi_gmem_write_AWREADY),
    .write_b_fire(h_m_axi_gmem_write_BVALID && h_m_axi_gmem_write_BREADY),
    .read_ar_fire(h_m_axi_gmem_read_ARVALID && h_m_axi_gmem_read_ARREADY),
    .epoch_active(g4_active),.commit_valid(g4_commit),
    .poisoned(g4_poison),.outstanding_writes(g4_outstanding)
);
always @(posedge clk) if(resetn) begin
    if(M00_AXI_arvalid && M00_AXI_arready && !first_ar_seen) begin
        first_ar_seen<=1'b1;
        inject_first_r<=1'b0;
        first_ram_ar=first_ram_ar+1;
    end
    if(M00_AXI_rvalid && M00_AXI_rready && M00_AXI_rresp===2'b10)
        ram_r_slverr=ram_r_slverr+1;
    if(h_m_axi_gmem_read_RVALID && h_m_axi_gmem_read_RREADY &&
       h_m_axi_gmem_read_RRESP===2'b10)
        hls_r_slverr=hls_r_slverr+1;
    if(h_trace_TVALID && h_trace_TREADY)
        provisional_trace=provisional_trace+1;
    if(g4_commit) begin
        published_trace=provisional_trace;
        $fatal(1,"M06_G4_FAIL READ_ERROR_FALSE_COMMIT");
    end
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
            @(negedge clk); g4_epoch_begin=1;
            @(negedge clk); g4_epoch_begin=0;
            write_reg(@AP_CTRL@,32'd1);
            while((read_guard_fault !== 1'b1 || g4_poison !== 1'b1 ||
                   ram_r_slverr<1 || hls_r_slverr<1) &&
                  fault_polls<20000) begin
                repeat(20) @(negedge clk);
                fault_polls=fault_polls+1;
            end
        end
    join
    repeat(10) @(negedge clk);
    if(first_ram_ar!==1 || first_ar_seen!==1'b1 ||
       ram_r_slverr<1 || hls_r_slverr<1 ||
       read_guard_fault!==1'b1 || g4_poison!==1'b1 ||
       g4_commit!==1'b0 || published_trace!==0 ||
       ctrl_b_count!==13)
        $fatal(1,"M06_G4_FAIL READ_SLVERR_NOT_QUARANTINED AR=%0d RAM_R=%0d HLS_R=%0d GUARD=%b POISON=%b",
               first_ram_ar,ram_r_slverr,hls_r_slverr,
               read_guard_fault,g4_poison);
    $display("M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS ORIGINAL_AMD_R_TO_HLS_GUARD_POISON NO_COMMIT NO_ROLLBACK_NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #20000000;
    $fatal(1,"M06_G4_FAIL READ_GLOBAL_WATCHDOG");
end
endmodule
"""
STALL_TAIL=r"""
reg g4_epoch_begin=0, g4_done=0;
wire g4_active,g4_commit,g4_poison;
wire [15:0] g4_outstanding;
integer first_ram_aw=0, raw_ram_b_seen=0, hls_b_seen=0;
integer provisional_trace=0, published_trace=0, fault_polls=0;
reg first_aw_seen=0;
localparam integer TEST_EPOCH_TIMEOUT=10000;
m06_g4_epoch_commit_gate #(.MAX_EPOCH_CYCLES(TEST_EPOCH_TIMEOUT)) epoch_gate (
    .aclk(clk),.aresetn(resetn),
    .epoch_begin(g4_epoch_begin),.ap_done(g4_done),.ap_return(observed_status),
    .read_guard_fault(read_guard_fault),.write_guard_fault(write_guard_fault),
    .write_aw_fire(h_m_axi_gmem_write_AWVALID && h_m_axi_gmem_write_AWREADY),
    .write_b_fire(h_m_axi_gmem_write_BVALID && h_m_axi_gmem_write_BREADY),
    .read_ar_fire(h_m_axi_gmem_read_ARVALID && h_m_axi_gmem_read_ARREADY),
    .epoch_active(g4_active),.commit_valid(g4_commit),
    .poisoned(g4_poison),.outstanding_writes(g4_outstanding)
);
always @(posedge clk) if(resetn) begin
    if(M00_AXI_awvalid && M00_AXI_awready && !first_aw_seen) begin
        first_aw_seen<=1;
        first_ram_aw=first_ram_aw+1;
    end
    if(raw_ram_bvalid && !M00_AXI_bvalid && hold_first_b)
        raw_ram_b_seen=raw_ram_b_seen+1;
    if(h_m_axi_gmem_write_BVALID && h_m_axi_gmem_write_BREADY)
        hls_b_seen=hls_b_seen+1;
    if(h_trace_TVALID && h_trace_TREADY)
        provisional_trace=provisional_trace+1;
    if(g4_commit) begin
        published_trace=provisional_trace;
        $fatal(1,"M06_G4_FAIL STALLED_B_FALSE_COMMIT");
    end
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
            @(negedge clk); g4_epoch_begin=1;
            @(negedge clk); g4_epoch_begin=0;
            write_reg(@AP_CTRL@,32'd1);
            while((g4_poison!==1'b1 || raw_ram_b_seen<1 ||
                   epoch_gate.epoch_cycles<TEST_EPOCH_TIMEOUT) &&
                  fault_polls<4000) begin
                repeat(20) @(negedge clk);
                fault_polls=fault_polls+1;
            end
        end
    join
    repeat(10) @(negedge clk);
    if(first_ram_aw!==1 || raw_ram_b_seen<1 ||
       hls_b_seen!==0 || raw_ram_bvalid!==1'b1 ||
       M00_AXI_bvalid!==1'b0 || g4_poison!==1'b1 ||
       epoch_gate.epoch_cycles<TEST_EPOCH_TIMEOUT ||
       g4_commit!==1'b0 || published_trace!==0 ||
       ctrl_b_count!==13)
        $fatal(1,"M06_G4_FAIL STALLED_WRITE_B_NOT_QUARANTINED firstAW=%0d RAM_B=%0d HLS_B=%0d POISON=%b CYCLES=%0d",
               first_ram_aw,raw_ram_b_seen,hls_b_seen,g4_poison,
               epoch_gate.epoch_cycles);
    // The AMD/HLS B handshake never completed. NO physical DDR rollback,
    // HLS ap_done, or recovery is claimed; the whole epoch is quarantined.
    $display("M06_G4_ACTUAL_HLS_AMD_STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS ORIGINAL_AMD_B_HELD NO_HLS_B NO_COMMIT NO_ROLLBACK_NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #20000000;
    $fatal(1,"M06_G4_FAIL STALLED_B_GLOBAL_WATCHDOG");
end
endmodule
"""

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",required=True,choices=sorted(MODES))
    for key in ("idle-tb","accepted-inventory","control-map","output"):
        parser.add_argument("--"+key,required=True,type=Path)
    a=parser.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("original G4 owner output must be a NEW file")
        a.output.write_text(g4_fault_tb(
            a.idle_tb.read_text(),
            json.loads(a.accepted_inventory.read_text()),
            json.loads(a.control_map.read_text()),a.mode))
    except (ValueError,KeyError,OSError,TypeError) as err:
        print("M06_G4_FAULT_MATRIX_TB_REJECTED:",err,file=sys.stderr)
        return 2
    print("M06_G4_ORIGINAL_HLS_AMD_"+a.mode.upper()+
          "_TB_GENERATED SOURCE_ONLY_NO_VENDOR_XSIM")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
