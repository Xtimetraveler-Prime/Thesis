#!/usr/bin/env python3
"""M06 existing G4: genuine original HLS+AMD fail/discard/restore/clean-run XSim.

Start with an injected REAL scratch read R SLVERR, demand original-HLS read
guard and fail-closed output-quarantine, then externally reset HLS+AMD,
explicitly overwrite all 64KiB simulated canonical bytes with an independently
known pristine image and rerun original HLS. Demand exact 16 clean trace
records, one metrics word and ONLY postcommit external release.
NO automatic rollback, physical PS DDR, JTAG, board, synthesis or timing claim.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

from m06_g4_actual_hls_fault_matrix_tb import g4_fault_tb, READ_TAIL
from m06_g3_3_positive16_axilite_tb import REQUIRED

TOP="tb_m06_g4_actual_hls_original_amd_discard_restore"
PASS="M06_G4_ACTUAL_HLS_AMD_FAULT_DISCARD_RESTORE_CLEAN_COMMIT_XSIM_PASS"
ORIGINAL_TOP="module tb_m06_g4_actual_hls_original_amd_first_r_slverr;"
BASE_TAIL="reg g4_epoch_begin=0, g4_done=0;"
START="initial begin\n    repeat(12) @(negedge clk); resetn=1;"

def recovery_tb(idle: str,inventory: dict,control: dict) -> str:
    original=g4_fault_tb(idle,inventory,control,"g4_first_r_slverr")
    if original.count(BASE_TAIL)!=1 or original.count(ORIGINAL_TOP)!=1:
        raise ValueError("previous original HLS/AMD read fault bench identity drift")
    if READ_TAIL.count(START)!=1 or original.count(START)!=1:
        raise ValueError("original read error owner stimulus anchor drift")
    pre=original[:original.index(BASE_TAIL)]
    pre=pre.replace(ORIGINAL_TOP,"module "+TOP+";")
    common=original[original.index(BASE_TAIL):original.index(START)]
    if common.count('if(g4_commit) begin')!=1 or common.count(
            'if(q_trace_valid && q_trace_ready)')!=1:
        raise ValueError("genuine output buffer / commit monitor anchor drift")
    # First invalid run may NEVER release. Second clean run is the
    # ONLY run allowed to publish after the real supervisor's valid token.
    common=common.replace(
        'if(g4_commit) begin\n        published_trace=provisional_trace;\n'
        '        $fatal(1,"M06_G4_FAIL READ_ERROR_FALSE_COMMIT");\n    end',
        'if(g4_commit && phase==1)\n'
        '        $fatal(1,"M06_G4_RECOVER_FAIL FAILED_EPOCH_COMMITTED");')
    if "FAILED_EPOCH_COMMITTED" not in common:
        raise ValueError("original fail-closed commit monitor changed")
    common=common.replace("integer first_ram_ar=0, ram_r_slverr=0, hls_r_slverr=0;",
                          "integer first_ram_ar=0, ram_r_slverr=0, hls_r_slverr=0;\n"
                          "integer phase=1, published_metrics=0, expected_id=0;")
    common=common.replace(
        "    if(q_trace_valid && q_trace_ready)\n        published_trace=published_trace+1;",
        """    if(q_trace_valid && q_trace_ready) begin
        if(phase!=2 || q_trace_data[63:0]!==64'd0 ||
           q_trace_data[95:64]!==expected_id ||
           q_trace_data[127:96]!==((expected_id==0) ? 32'd1 : 32'd0) ||
           q_trace_data[135:128]!==8'd0 ||
           q_trace_data[143:136]!==((expected_id==0) ? 8'd1 : 8'd0) ||
           q_trace_data[191:160]!==32'd0)
            $fatal(1,"M06_G4_RECOVER_FAIL DIRTY_OR_UNEXPECTED_TRACE id=%0d got=%h",
                   expected_id,q_trace_data);
        expected_id=expected_id+1;
        published_trace=published_trace+1;
    end
    if(q_metrics_valid && q_metrics_ready) begin
        if(phase!=2 || expected_id!=16)
            $fatal(1,"M06_G4_RECOVER_FAIL METRICS_BEFORE_CLEAN_TRACE");
        published_metrics=published_metrics+1;
    end""")
    if "DIRTY_OR_UNEXPECTED_TRACE" not in common:
        raise ValueError("original trace publication hook changed")
    offsets={key:"7'h"+format(control["register_offsets"][key],"02x")
             for key in (*REQUIRED,"AP_CTRL")}
    offsets["AP_RETURN"]="7'h"+format(control["ap_return"],"02x")
    tail=RESTORE_TAIL
    for name,actual in offsets.items():
        tail=tail.replace("@"+name+"@",actual)
    if re.search(r"@[A-Z][A-Z0-9_]*@",tail):
        raise ValueError("original owner HLS AXI-Lite register map missing")
    return pre+common+tail

RESTORE_TAIL=r"""
integer image_byte=0;
initial begin
    repeat(12) @(negedge clk); resetn=1;
    repeat(30) @(negedge clk);
    // FIRST epoch: genuine original HLS+AMD read-SLVERR, quarantine.
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
                   ram_r_slverr<1 || hls_r_slverr<1 ||
                   q_quarantined!==1'b1) &&
                  fault_polls<20000) begin
                repeat(20) @(negedge clk);
                fault_polls=fault_polls+1;
            end
        end
    join
    repeat(10) @(negedge clk);
    if(read_guard_fault!==1'b1 || g4_poison!==1'b1 ||
       q_quarantined!==1'b1 || ram_r_slverr<1 ||
       hls_r_slverr<1 || published_trace!==0 ||
       published_metrics!==0 || g4_commit!==1'b0)
        $fatal(1,"M06_G4_RECOVER_FAIL FIRST_FAULT_NOT_QUARANTINED");

    // EXPLICIT testbench OWNER DISCARD + RESTORE, NOT automatic FPGA/DDR
    // rollback. Assert common reset to drain/discard HLS/AMD in flight
    // transactions; reconstruct EVERY byte of a pristine 64KiB image.
    phase=2;
    @(negedge clk); resetn=0; g4_done=0; g4_epoch_begin=0;
    h_neurons_TVALID=0; h_neurons_TDATA=0; inject_first_r=0;
    repeat(15) @(negedge clk);
    for(image_byte=0;image_byte<65536;image_byte=image_byte+1)
        ram.mem[image_byte]=(13*image_byte+17)&8'hff;
    if(ram.mem[0]!==8'h11 || ram.mem[65535]!==8'h04)
        $fatal(1,"M06_G4_RECOVER_FAIL OWNER_RESTORE_IMAGE");
    @(negedge clk); resetn=1;
    repeat(30) @(negedge clk);
    if(g4_poison!==1'b0 || q_quarantined!==1'b0 ||
       q_protocol_fault!==1'b0 || read_guard_fault!==1'b0 ||
       write_guard_fault!==1'b0 || q_published_count!==0 ||
       q_buffered_count!==0)
        $fatal(1,"M06_G4_RECOVER_FAIL STALE_FAULT_AFTER_EXTERNAL_RESTORE");
    provisional_trace=0;
    published_trace=0;
    published_metrics=0;
    expected_id=0;
    observed_ctrl=0;
    observed_status=32'hffffffff;
    polls=0;
    // SECOND epoch: no memory fault, full original generated-HLS positive16
    // followed by genuine CONTROL register AP_DONE/status0.
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
            while(observed_ctrl[1] !== 1'b1 && polls < 2000) begin
                repeat(50) @(negedge clk);
                read_reg(@AP_CTRL@,observed_ctrl);
                polls=polls+1;
            end
            if(observed_ctrl[1]!==1'b1)
                $fatal(1,"M06_G4_RECOVER_FAIL CLEAN_AP_DONE_TIMEOUT");
            read_reg(@AP_RETURN@,observed_status);
            if(observed_status!==32'd0)
                $fatal(1,"M06_G4_RECOVER_FAIL CLEAN_HLS_STATUS");
            // Original external owner interprets actual AXI-Lite AP_DONE
            // + AP_RETURN_0. Gate's done pulse is CONTROL-PLANE supplied,
            // not tied to a fabricated internal h_ap_done pin.
            @(negedge clk); g4_done=1;
            @(negedge clk); g4_done=0;
        end
    join
    repeat(120) @(negedge clk);
    if(g4_commit!==1'b1 || g4_poison!==1'b0 ||
       q_quarantined!==1'b0 || q_protocol_fault!==1'b0 ||
       q_published_done!==1'b1 ||
       q_published_count!==32'd16 || published_trace!==16 ||
       published_metrics!==1 || expected_id!==16 ||
       provisional_trace!==16 ||
       read_guard_fault!==1'b0 || write_guard_fault!==1'b0 ||
       ram.mem[0]!==8'h01 || ram.mem[4]!==8'h01 ||
       ram.mem[16]!==8'h00 || ram.mem[256]!==8'h11)
        $fatal(1,"M06_G4_RECOVER_FAIL CLEAN_REPLAY_STALE_OR_EARLY_RELEASE commit=%b poison=%b done=%b count=%0d pub=%0d metrics=%0d",
               g4_commit,g4_poison,q_published_done,q_published_count,
               published_trace,published_metrics);
    $display("M06_G4_ACTUAL_HLS_AMD_FAULT_DISCARD_RESTORE_CLEAN_COMMIT_XSIM_PASS FIRST_R_SLVERR_POISON NO_FAILED_TRACE_RELEASE EXPLICIT_64K_IMAGE_RESTORE HLS_AP_DONE_STATUS0 CLEAN_16_TRACE_1_METRICS POSTCOMMIT_ONLY NO_AUTO_ROLLBACK_NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #30000000;
    $fatal(1,"M06_G4_RECOVER_FAIL GLOBAL_WATCHDOG");
end
endmodule
"""

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("idle-tb","accepted-inventory","control-map","output"):
        parser.add_argument("--"+key,required=True,type=Path)
    a=parser.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("G4 restore owner TB must be NEW in existing folder")
        a.output.write_text(recovery_tb(
            a.idle_tb.read_text(),
            json.loads(a.accepted_inventory.read_text()),
            json.loads(a.control_map.read_text())))
    except (ValueError,OSError,KeyError,TypeError) as err:
        print("M06_G4_RECOVERY_TB_REJECTED:",err,file=sys.stderr)
        return 2
    print("M06_G4_REAL_HLS_AMD_FAULT_DISCARD_RESTORE_TB_GENERATED "
          "SOURCE_ONLY_NO_VENDOR_XSIM_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
