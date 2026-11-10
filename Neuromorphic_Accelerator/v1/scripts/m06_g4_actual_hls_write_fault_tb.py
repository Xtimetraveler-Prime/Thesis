#!/usr/bin/env python3
"""Existing M06 G4 first ORIGINAL HLS+AMD write-SLVERR quarantine owner XSim.

Uses genuine original Vitis generated RTL + original AMD SmartConnect/DWCs,
the already verified positive16 AXIS/AXI-Lite setup, the simulation-only
64KiB endpoint's existing deterministic first-B error injection, and a
SEPARATE synthesizable fault-acceptance gate. No physical PS DDR or board.
Source-only Icarus syntax declarations are NOT a functional owner run.

Important: no atomic rollback, full trace buffer, recovery, or exception
status on original-HLS AP_RETURN is claimed by this experiment.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

from m06_g3_3_positive16_axilite_tb import positive_tb, REQUIRED, ANCHOR

NAME="tb_m06_g4_actual_hls_original_amd_first_b_slverr"
PASS="M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS"
PREFIX_FAIL='if(read_guard_fault || write_guard_fault)\n        $fatal(1,"M06_G3_3_HLS_LINK_IDLE_FAIL GUARD_FAULT");'
POSITIVE_ALWAYS="always @(posedge clk) if(resetn) begin"

def generate(idle: str, inventory: dict, control: dict) -> str:
    # Preserve all earlier genuine original HLS pin and AXI-Lite identity
    # checks. This merely replaces one previously accepted *testbench*.
    positive=positive_tb(idle,inventory,control)
    if positive.count(ANCHOR)!=1:
        raise ValueError("positive16 source or testbench anchor drift")
    prefix,remaining=positive.split(ANCHOR,1)
    old_top="module tb_m06_g3_3_actual_hls_original_amd_positive16;"
    if prefix.count(old_top)!=1 or prefix.count(PREFIX_FAIL)!=1:
        raise ValueError("original connected HLS/AMD source/guard anchor drift")
    if prefix.count(".inject_next_b_slverr(1'b0), .inject_next_r_slverr(1'b0)")!=1:
        raise ValueError("original scratch fault injection port contract drift")
    if prefix.count("reg resetn=0;")!=1:
        raise ValueError("original bench reset contract drift")
    prefix=prefix.replace(old_top, "module "+NAME+";")
    prefix=prefix.replace("reg resetn=0;","reg resetn=0;\nreg inject_first_b=1'b1;")
    prefix=prefix.replace(PREFIX_FAIL,
       'if(1\\'b0) $fatal(1,"M06_G4_FAIL GUARD_MONITOR_DISABLED");')
    prefix=prefix.replace(
        ".inject_next_b_slverr(1'b0), .inject_next_r_slverr(1'b0)",
        ".inject_next_b_slverr(inject_first_b), .inject_next_r_slverr(1'b0)")
    if remaining.count(POSITIVE_ALWAYS)!=1:
        raise ValueError("positive16 task/monitor anchor drift")
    tasks=ANCHOR+remaining.split(POSITIVE_ALWAYS,1)[0]
    regs=control["register_offsets"]
    keys=(*REQUIRED,"AP_CTRL")
    offsets={key:"7'h"+format(regs[key],"02x") for key in keys}
    offsets["AP_RETURN"]="7'h"+format(control["ap_return"],"02x")
    tail=r"""
// G4 condition is observable only at a REAL original AMD/HLS AXI response,
// not by forced guard/fault pins. First 128-bit AMD RAM AW samples SLVERR.
reg g4_epoch_begin=0, g4_done=0;
wire g4_active,g4_commit,g4_poison;
wire [15:0] g4_outstanding;
integer injected_aw=0, ram_b_slverr=0, hls_b_slverr=0;
integer provisional_trace=0, published_trace=0, g4_polls=0;
reg first_aw_seen=0;

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
    if(M00_AXI_awvalid && M00_AXI_awready && !first_aw_seen) begin
        first_aw_seen<=1;
        inject_first_b<=0;
        injected_aw=injected_aw+1;
    end
    if(M00_AXI_bvalid && M00_AXI_bready && M00_AXI_bresp===2'b10)
        ram_b_slverr=ram_b_slverr+1;
    if(h_m_axi_gmem_write_BVALID && h_m_axi_gmem_write_BREADY &&
       h_m_axi_gmem_write_BRESP===2'b10)
        hls_b_slverr=hls_b_slverr+1;
    if(h_trace_TVALID && h_trace_TREADY)
        provisional_trace=provisional_trace+1;
    // This is a verification-only RELEASE MONITOR, not an implemented
    // 128-row hardware buffer or proof of physical DDR transactionality.
    if(g4_commit)
        published_trace=provisional_trace;
    if(g4_commit)
        $fatal(1,"M06_G4_FAIL COMMIT_EVER_ASSERTED_DURING_FAULT");
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
            // Explicit epoch ownership is testbench-controlled here; do
            // NOT pretend the independent G4 gate is wired into HLS RTL.
            @(negedge clk); g4_epoch_begin=1;
            @(negedge clk); g4_epoch_begin=0;
            write_reg(@AP_CTRL@,32'd1);
            while((write_guard_fault !== 1'b1 || g4_poison !== 1'b1 ||
                   ram_b_slverr==0 || hls_b_slverr==0) &&
                  g4_polls<20000) begin
                repeat(20) @(negedge clk);
                g4_polls=g4_polls+1;
            end
            if(write_guard_fault !== 1'b1 || g4_poison !== 1'b1 ||
               ram_b_slverr<1 || hls_b_slverr<1)
                $fatal(1,"M06_G4_FAIL NO_END_TO_END_SLVERR firstAW=%0d ramB=%0d hlsB=%0d guard=%b poison=%b",
                       injected_aw,ram_b_slverr,hls_b_slverr,
                       write_guard_fault,g4_poison);
        end
    join
    repeat(12) @(negedge clk);
    if(injected_aw!==1 || first_aw_seen!==1 ||
       ram_b_slverr!==1 || hls_b_slverr<1 ||
       ctrl_b_count!==13 || write_guard_fault!==1'b1 ||
       g4_poison!==1'b1 || g4_commit!==1'b0 || published_trace!==0)
        $fatal(1,"M06_G4_FAIL INJECTED_B_RESP_NOT_QUARANTINED");
    // A partial canonical RAM write may have landed before a SLVERR.
    // It must be considered corrupt until EXTERNAL image discard/restore.
    // Do not assert memory rollback or HLS AP_DONE on this failed epoch.
    $display("M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS ORIGINAL_AMD_B_TO_HLS_GUARD_POISON NO_COMMIT NO_ROLLBACK_NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #20000000;
    $fatal(1,"M06_G4_FAIL GLOBAL_WATCHDOG");
end
endmodule
"""
    for key,value in offsets.items():
        tail=tail.replace("@"+key+"@",value)
    if re.search(r"@[A-Z][A-Z0-9_]*@",tail):
        raise ValueError("original HLS AXI-Lite offset unresolved")
    return prefix+tasks+tail

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("idle-tb","accepted-inventory","control-map","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("genuine G4 owner testbench must be a NEW output")
        output=generate(args.idle_tb.read_text(),
                        json.loads(args.accepted_inventory.read_text()),
                        json.loads(args.control_map.read_text()))
        args.output.write_text(output)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print("M06_G4_ORIGINAL_HLS_FAULT_TB_REJECTED:",error,file=sys.stderr)
        return 2
    print("M06_G4_ORIGINAL_HLS_AMD_FIRST_B_SLVERR_TB_GENERATED "
          "SOURCE_ONLY_NO_VENDOR_SIM_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
