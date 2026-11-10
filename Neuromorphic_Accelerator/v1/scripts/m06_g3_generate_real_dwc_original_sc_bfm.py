#!/usr/bin/env python3
"""Generate TRUE AMD DWC + ORIGINAL D3 SmartConnect 32-bit AXI bridge TB.

Independent BFM -> BOTH genuine 32:256 AMD DWC SIM models ->
ORIGINAL immutable 96-port AMD SmartConnect S00 read/S03 write ->
ONE simulated 64KiB 128-bit AXI scratch endpoint.

This first combined-vendor trial does NOT instantiate M06 generated HLS.
Provenance readback calls actual original owner D3 and DWC file audits.
No physical DDR, no Vivado edits, no board/JTAG/bitstream.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from m06_generate_original_mem_sc_bfm import (
    MODULE, original_ports, required_ports,
)
from m06_g3_capture_dwc_ports import capture

ROLE = (("m06_g3_read_dwc", "S00"), ("m06_g3_write_dwc", "S03"))
DRIVER_DEFAULTS = {
    "arid": "1'b0", "awid": "1'b0",
    "arburst": "2'b01", "awburst": "2'b01",
    "arsize": "3'd2", "awsize": "3'd2",
    "arcache": "4'b0011", "awcache": "4'b0011",
    "arlock": "1'b0", "awlock": "1'b0",
    "arprot": "3'b0", "awprot": "3'b0",
    "arqos": "4'b0", "awqos": "4'b0",
    "arregion": "4'b0", "awregion": "4'b0",
    "arlen": "8'd0", "awlen": "8'd0",
    "wstrb": "4'hf",
}
# Existing authenticated M00 RAM model's exact public pin set.
MEMORY = ("awaddr awlen awsize awburst awvalid awready "
          "wdata wstrb wlast wvalid wready bresp bvalid bready "
          "araddr arlen arsize arburst arvalid arready "
          "rdata rresp rlast rvalid rready").split()


def _bit_decl(width: int) -> str:
    if not 1 <= width <= 256:
        raise ValueError("unrecognized vendor AXI pin width")
    return f"[{width-1}:0] " if width > 1 else ""


def exact_dwc_abi(sc: str, required: dict) -> dict:
    """Fully reconstruct measured 36/42-pin AMD DWC SI+MI wrapper contract.

    This is checked against independently parsed, SHA-audited original
    Vivado SIM headers; NEVER used to replace real vendor RTL.
    """
    if sc not in ("S00", "S03"):
        raise ValueError("unsupported original read/write SI role")
    source={k[len(sc+"_AXI_"):]:v for k,v in required.items()
            if k.startswith(sc+"_AXI_")}
    expected={}
    for field,(sc_direction,sc_width) in source.items():
        converter_direction="output" if sc_direction=="input" else "input"
        expected["m_axi_"+field]={
            "direction":converter_direction,"width_bits":sc_width}
        upstream_width=32 if field in ("rdata","wdata") else (
            4 if field=="wstrb" else sc_width)
        # The converter SI is a SLAVE: its declaration direction
        # matches the original SmartConnect SI (also a SLAVE).
        # The converter MI is a MASTER and must point the other way.
        expected["s_axi_"+field]={
            "direction":sc_direction,"width_bits":upstream_width}
    prefix="ar" if sc=="S00" else "aw"
    expected["m_axi_"+prefix+"region"]={"direction":"output","width_bits":4}
    expected["s_axi_"+prefix+"region"]={"direction":"input","width_bits":4}
    expected["s_axi_"+prefix+"id"]={"direction":"input","width_bits":1}
    expected["s_axi_"+("rid" if sc=="S00" else "bid")]={
        "direction":"output","width_bits":1}
    for pin in ("aclk","aresetn"):
        expected["s_axi_"+pin]={"direction":"input","width_bits":1}
    return expected



def passive_axi_probe() -> str:
    """Observe genuine handshakes and stalled responses; drive NO AXI signals."""
    reads = [("RD_SI32", "m06_g3_read_dwc_s_axi"),
             ("RD_MI256_SC_S00", "S00_AXI"),
             ("SC_M00_RAM128", "M00_AXI")]
    writes = [("WR_SI32", "m06_g3_write_dwc_s_axi"),
              ("WR_MI256_SC_S03", "S03_AXI"),
              ("SC_M00_RAM128", "M00_AXI")]
    lines = ["// PASSIVE, bounded. M00 and RAM S_AXI are THE SAME nets.",
             "integer axi_probe_printed=0, axi_probe_first_decerr=0;",
             "integer axi_probe_quiet=0;"]
    counters = []
    def trace(kind, stage, fields, args):
        fmt = f"M06_G3_AXI_TRACE kind={kind} stage={stage} t=%0t " + fields
        return ('if (axi_probe_printed < 512) $display("' + fmt + '", ' +
                ", ".join(["$time"] + args) + ');')
    lines.append("always @(posedge clk) if (resetn) begin")
    for stage, prefix in reads + writes[:-1]:  # M00 is one shared RAM link
        channels = ("AR", "R") if stage.startswith("RD_") else (
            ("AW", "W", "B") if stage.startswith("WR_") else ("AR", "R", "AW", "W", "B"))
        for channel in channels:
            counter = f"axi_{stage}_{channel}"
            counters.append(counter)
            valid, ready = prefix + "_" + channel.lower() + "valid", prefix + "_" + channel.lower() + "ready"
            fields, args = "", []
            if channel in ("AR", "AW"):
                stem = prefix + "_" + channel.lower()
                fields = "addr=%h len=%0d size=%0d burst=%b"
                args = [stem + x for x in ("addr", "len", "size", "burst")]
                if stage != "SC_M00_RAM128":
                    fields += " cache=%b"
                    args.append(stem + "cache")
                else:
                    fields += " cache=NA"
                if stage.endswith("SI32"):
                    fields += " id=%b"
                    args.append(stem + "id")
                else:
                    fields += " id=NA"
            elif channel == "W":
                fields, args = "data=%h strb=%h last=%b", [
                    prefix + "_wdata", prefix + "_wstrb", prefix + "_wlast"]
            else:
                fields, args = "resp=%b" + (" last=%b data=%h" if channel == "R" else ""), [
                    prefix + "_" + channel.lower() + "resp"]
                if channel == "R":
                    args.extend((prefix + "_rlast", prefix + "_rdata"))
            lines.extend((
                f"  if ({valid} && {ready}) begin",
                f"    {counter}={counter}+1;",
                "    " + trace(channel + ("_HS" if channel in ("R", "B") else ""),
                              stage, fields, args),
                "    axi_probe_printed=axi_probe_printed+1;",
                "  end"))
    lines.append("end")
    # Declarations are module-scope, even if they occur after an always block.
    lines.extend("integer " + counter + "=0;" for counter in counters)
    responses = [(label, prefix, "R") for label, prefix in reads] + [
        (label, prefix, "B") for label, prefix in writes]
    lines.extend(f"reg axi_seen_{label}_{kind}=0;" for label,prefix,kind in responses)
    lines.append("always @(negedge clk) if (resetn) begin")
    for stage, prefix, kind in responses:
        seen = f"axi_seen_{stage}_{kind}"
        p = prefix + "_" + kind.lower()
        fields = "resp=%b ready=%b" + (" last=%b data=%h" if kind == "R" else "")
        args = [p + "resp", p + "ready"]
        if kind == "R":
            args.extend((p + "last", p + "data"))
            if stage == "SC_M00_RAM128":
                fields += " ram_bad=%b"
                args.append("ram.rd_bad_request")
            else:
                fields += " ram_bad=NA"
        lines.extend((
            f"  if ({p}valid === 1'b1 && !{seen}) begin",
            f"    {seen}=1;",
            "    " + trace(kind + "_OBS", stage, fields, args),
            "    axi_probe_printed=axi_probe_printed+1;",
            f"    if ({p}resp === 2'b11 && !axi_probe_first_decerr) begin",
            "      axi_probe_first_decerr=1;",
            f'      $display("M06_G3_AXI_FIRST_DECERR kind={kind}_OBS stage={stage} t=%0t resp=%b ready=%b", $time, {p}resp, {p}ready);',
            "    end",
            "  end",
            f"  if ({p}valid !== 1'b1) {seen}=0;"))
    lines.append("end")
    fmt = "M06_G3_AXI_PROBE_SUMMARY " + " ".join(x + "=%0d" for x in counters) + " printed=%0d first_decerr=%0d"
    lines.extend((
        "task automatic axi_probe_summary;",
        "begin",
        '  $display("' + fmt + '",',
        "    " + ", ".join(counters + ["axi_probe_printed", "axi_probe_first_decerr"]) + ");",
        "end",
        "endtask"))
    # Local inactivity watchdog supplements, never replaces, the 2ms global one.
    lines.extend((
        "always @(posedge clk) if (resetn) begin",
        "  if ((m06_g3_read_dwc_s_axi_arvalid && m06_g3_read_dwc_s_axi_arready) ||",
        "      (m06_g3_read_dwc_s_axi_rvalid && m06_g3_read_dwc_s_axi_rready) ||",
        "      (m06_g3_write_dwc_s_axi_awvalid && m06_g3_write_dwc_s_axi_awready) ||",
        "      (m06_g3_write_dwc_s_axi_wvalid && m06_g3_write_dwc_s_axi_wready) ||",
        "      (m06_g3_write_dwc_s_axi_bvalid && m06_g3_write_dwc_s_axi_bready))",
        "    axi_probe_quiet<=0;",
        "  else axi_probe_quiet<=axi_probe_quiet+1;",
        "  if (axi_probe_quiet==1000) begin",
        "    axi_probe_summary();",
        '    $fatal(1,"M06_G3_REAL_DWC_SC_FAIL LOCAL_AXI_INACTIVITY_WATCHDOG");',
        "  end",
        "end"))
    return "\n".join(lines) + "\n"


def render(dwc_readback: dict, vendor: list[dict]) -> str:
    required = required_ports()
    actual = {p["name"]: (p["direction"], p["packed_width"]) for p in vendor}
    if actual != required or len(vendor) != 96:
        raise ValueError("original AMD 96-pin SmartConnect ABI differs")
    if set(dwc_readback["instances"]) != {role[0] for role in ROLE}:
        raise ValueError("not both original generated AMD width converters")
    lines = [
        "// TRUE AMD width converters + ORIGINAL SHA-verified SmartConnect.",
        "// DRIVER IS INDEPENDENT 32b AXI BFM (NOT generated HLS).",
        "// RAM is simulated 64KiB scratch ONLY, not PS DDR or a board.",
        chr(96)+"timescale 1ns/1ps",
        "module tb_m06_g3_real_dwc_original_sc;",
        "reg clk=0; always #5 clk=~clk;",
        "reg resetn=0;",
        "integer m00_aw=0,m00_w=0,m00_b=0,m00_ar=0,m00_r=0;",
        "integer write_ok=0,read_ok=0;",
    ]
    for name,(_,width) in required.items():
        lines.append(f"wire {_bit_decl(width)}{name};")
        if name.startswith(("S01_AXI_", "S02_AXI_")) and required[name][0]=="input":
            lines.append(f"assign {name} = {width}'d0;")

    lines.append(
        f"{MODULE} sc_dut (\n    .aclk(clk), .aresetn(resetn),\n" +
        ",\n".join(f"    .{p['name']}({p['name']})" for p in vendor) +
        "\n);"
    )
    for name,sc in ROLE:
        row = dwc_readback["instances"][name]
        if row["role"] != ("READ_ONLY" if sc=="S00" else "WRITE_ONLY"):
            raise ValueError("wrong real AMD width converter mode")
        ports = row["pins"]
        if ports != exact_dwc_abi(sc,required):
            missing=set(exact_dwc_abi(sc,required))-set(ports)
            extra=set(ports)-set(exact_dwc_abi(sc,required))
            wrong={k for k in set(ports)&set(exact_dwc_abi(sc,required))
                   if ports[k]!=exact_dwc_abi(sc,required)[k]}
            raise ValueError("actual ORIGINAL AMD DWC SIM 36/42-pin ABI drift: "
                             +f"missing={sorted(missing)} extra={sorted(extra)} "
                             +f"wrong={sorted(wrong)}")
        port_map = []
        for signal, props in sorted(ports.items()):
            d,w = props["direction"],props["width_bits"]
            if d not in ("input","output"):
                raise ValueError("unknown generated AMD DWC port direction")
            if signal=="s_axi_aclk":
                port_map.append(f".{signal}(clk)")
            elif signal=="s_axi_aresetn":
                port_map.append(f".{signal}(resetn)")
            elif signal.startswith("s_axi_"):
                net=f"{name}_{signal}"
                suffix=signal[len("s_axi_"):]
                default=DRIVER_DEFAULTS.get(suffix,"0")
                lines.append(f"{'reg' if d=='input' else 'wire'} {_bit_decl(w)}{net}"+
                             (f"={default};" if d=="input" else ";"))
                port_map.append(f".{signal}({net})")
            elif signal.startswith("m_axi_"):
                suffix=signal[len("m_axi_"):]
                target=f"{sc}_AXI_{suffix}"
                if target not in required:
                    if suffix not in ("arregion","awregion") or d!="output" or w!=4:
                        raise ValueError("unresolved AMD width-converter MI AXI port: "+signal)
                    port_map.append(f".{signal}()")
                else:
                    original_direction, original_width = required[target]
                    if w!=original_width or d==original_direction:
                        raise ValueError("original AMD DWC/SmartConnect direction/width mismatch: "+signal)
                    port_map.append(f".{signal}({target})")
            else:
                raise ValueError("unexpected genuine generated DWC pin: "+signal)
        lines.append(name+f" {name}_dut (\n    "+",\n    ".join(port_map)+"\n);")

    lines.append(
        "m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536)) ram (\n"
        " .aclk(clk), .aresetn(resetn),\n" +
        ",\n".join(f" .s_axi_{signal}(M00_AXI_{signal})" for signal in MEMORY)+
        ",\n .inject_next_b_slverr(1'b0), .inject_next_r_slverr(1'b0)\n);"
    )
    lines.append(passive_axi_probe())
    lines.append("""
reg [7:0] expected [0:65535];
integer k, byte_lane;
function automatic [31:0] word32(input integer addr);
    integer b;
    begin
        word32=0;
        for(b=0;b<4;b=b+1)
            word32[8*b+:8]=expected[addr+b];
    end
endfunction
always @(posedge clk) if(resetn) begin
    if(M00_AXI_awvalid && M00_AXI_awready) m00_aw<=m00_aw+1;
    if(M00_AXI_wvalid && M00_AXI_wready) m00_w<=m00_w+1;
    if(M00_AXI_bvalid && M00_AXI_bready) m00_b<=m00_b+1;
    if(M00_AXI_arvalid && M00_AXI_arready) m00_ar<=m00_ar+1;
    if(M00_AXI_rvalid && M00_AXI_rready) m00_r<=m00_r+1;
end

task automatic write32(input integer address, input [31:0] payload,
                       input [3:0] strobe);
    integer b;
    begin
        @(negedge clk);
        m06_g3_write_dwc_s_axi_awaddr=address;
        m06_g3_write_dwc_s_axi_awlen=0;
        m06_g3_write_dwc_s_axi_awvalid=1;
        @(posedge clk);
        while(m06_g3_write_dwc_s_axi_awready !== 1'b1) @(posedge clk);
        @(negedge clk);
        m06_g3_write_dwc_s_axi_awvalid=0;
        m06_g3_write_dwc_s_axi_wdata=payload;
        m06_g3_write_dwc_s_axi_wstrb=strobe;
        m06_g3_write_dwc_s_axi_wlast=1;
        m06_g3_write_dwc_s_axi_wvalid=1;
        @(posedge clk);
        while(m06_g3_write_dwc_s_axi_wready !== 1'b1) @(posedge clk);
        @(negedge clk);
        m06_g3_write_dwc_s_axi_wvalid=0;
        m06_g3_write_dwc_s_axi_wlast=0;
        @(posedge clk);
        while(m06_g3_write_dwc_s_axi_bvalid !== 1'b1) @(posedge clk);
        if(m06_g3_write_dwc_s_axi_bresp !== 2'b00 ||
           m06_g3_write_dwc_s_axi_bid !== 1'b0) begin
            axi_probe_summary();
            $fatal(1,"M06_G3_REAL_DWC_SC_FAIL WRITE_B addr=%h response=%b",
                   address,m06_g3_write_dwc_s_axi_bresp);
        end
        repeat(2) @(posedge clk);
        if(m06_g3_write_dwc_s_axi_bvalid !== 1'b1)
            $fatal(1,"M06_G3_REAL_DWC_SC_FAIL WRITE_B STALL");
        @(negedge clk);
        m06_g3_write_dwc_s_axi_bready=1;
        @(posedge clk);
        @(negedge clk);
        m06_g3_write_dwc_s_axi_bready=0;
        for(b=0;b<4;b=b+1)
            if(strobe[b]) expected[address+b]=payload[8*b+:8];
        write_ok=write_ok+1;
    end
endtask

task automatic read32(input integer address);
    reg [31:0] desired;
    begin
        desired=word32(address);
        @(negedge clk);
        m06_g3_read_dwc_s_axi_araddr=address;
        m06_g3_read_dwc_s_axi_arlen=0;
        m06_g3_read_dwc_s_axi_arvalid=1;
        @(posedge clk);
        while(m06_g3_read_dwc_s_axi_arready !== 1'b1) @(posedge clk);
        @(negedge clk);
        m06_g3_read_dwc_s_axi_arvalid=0;
        @(posedge clk);
        while(m06_g3_read_dwc_s_axi_rvalid !== 1'b1) @(posedge clk);
        if(m06_g3_read_dwc_s_axi_rdata !== desired ||
           m06_g3_read_dwc_s_axi_rresp !== 2'b00 ||
           m06_g3_read_dwc_s_axi_rid !== 1'b0 ||
           m06_g3_read_dwc_s_axi_rlast !== 1'b1) begin
            axi_probe_summary();
            $fatal(1,"M06_G3_REAL_DWC_SC_FAIL READ32 at=%h got=%h wanted=%h resp=%b",
                   address,m06_g3_read_dwc_s_axi_rdata,desired,
                   m06_g3_read_dwc_s_axi_rresp);
        end
        repeat(2) begin
            @(posedge clk);
            if(m06_g3_read_dwc_s_axi_rvalid !== 1'b1 ||
               m06_g3_read_dwc_s_axi_rdata !== desired)
                $fatal(1,"M06_G3_REAL_DWC_SC_FAIL READ_R STALL");
        end
        @(negedge clk);
        m06_g3_read_dwc_s_axi_rready=1;
        @(posedge clk);
        @(negedge clk);
        m06_g3_read_dwc_s_axi_rready=0;
        read_ok=read_ok+1;
    end
endtask

initial begin
    for(k=0;k<65536;k=k+1) expected[k]=(13*k+17)&255;
    repeat(12) @(negedge clk); resetn=1;
    repeat(30) @(negedge clk);
    // First verify initial full canonical memory with no physical DDR.
    read32('h0000);
    read32('h0ffc);
    read32('h1000);
    read32('hfffc); // Last legal 32-bit word (neuron 4095).
    // Both official AMD converters must address ONE original M00 scratch.
    write32('hfffc,32'h01234567,4'b0101);
    read32('hfffc);
    read32('hfff8); // Neighbor unaffected by sparse WSTRB.
    write32('h1000,32'haabbccdd,4'b1111);
    read32('h1000);
    read32('h0ffc); // Independent 4KiB boundary.
    write32('hff00,32'hdeadbeef,4'b1111);
    read32('hff00);
    read32('hfffc);
    if(write_ok!==3 || read_ok!==10 || m00_aw<3 || m00_b<3 ||
       m00_ar<10 || m00_w<3 || m00_r<10)
        $fatal(1,"M06_G3_REAL_DWC_SC_FAIL COUNTS writes=%0d reads=%0d m00aw=%0d w=%0d b=%0d ar=%0d r=%0d",
               write_ok,read_ok,m00_aw,m00_w,m00_b,m00_ar,m00_r);
    axi_probe_summary();
    $display("M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS write=%0d read=%0d m00_w=%0d m00_r=%0d high_byte=65535 shared_64k=1 NO_HLS_NO_BOARD_NO_DDR",
             write_ok,read_ok,m00_w,m00_r);
    $finish;
end
initial begin
    #2000000;
    $fatal(1,"M06_G3_REAL_DWC_SC_FAIL WATCHDOG");
end
endmodule
""")
    return "\n".join(lines)+"\n"


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-d3",required=True,type=Path)
    ap.add_argument("--original-headers",required=True,type=Path)
    ap.add_argument("--original-dwc",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("new testbench output path in existing directory required")
        vendor=original_ports(args.original_d3.resolve(strict=True),
            json.loads(args.original_headers.read_text(encoding="utf8")))
        dwc=capture(args.original_dwc)
        tb=render(dwc,vendor)
        with args.output.open("x",encoding="utf8") as fp:
            fp.write(tb)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("M06 G3 actual AMD dual converter + ORIGINAL SmartConnect TB REJECTED: "+str(exc),
              file=sys.stderr)
        return 2
    print("M06 G3 REAL 2x AMD DWC->ORIGINAL D3 SmartConnect 64KiB TB GENERATED (BFM ONLY); XSIM NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
