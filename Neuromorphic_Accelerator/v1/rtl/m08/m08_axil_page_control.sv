// M08.2b.2 first-party PS AXI4-Lite to ONE 256B signed16 state page.
// Single synchronous clock/reset; 12-bit aperture; ONE transaction in flight.
// A protected AXI-Lite *slave*, not a memory master or PS DDR allocator.
// Full owner hardware evidence requires genuine KV260 Vivado BD and route.
// Register offsets:
// 0x000 magic 0x4D303850 ('M08P'), 0x004 version 0x00020002
// 0x008 capability=1 (one 256B host-staged page; NO DMA/engine)
// 0x00C status {23'b0,bridge_fault,host_busy,compute_busy,dirty,valid,poisoned,phase}
// 0x010 selected logical ID (write FULL WSTRB=F)
// 0x014 command (write FULL WSTRB=F; 1=begin,2=commit,4=dispatch,8=save)
// 0x018 resident logical ID, 0x01C loaded bytes (0..256)
// 0x100..0x1FC page words, each 32-bit little-endian, WSTRB byte lanes.
// Invalid address: DECERR; unsupported/unsafe state/write: SLVERR.
// AW and W accepted INDEPENDENTLY; B/R held stable under backpressure.
// All backend read/write/command requests serialized; no AXI ID, burst,
// AXI master, kernel DMA, actual HLS compute, physical MMIO or DDR.
// Software must genuinely compare all 64 returned words before COMMIT;
// must preserve the complete DIRTY readback before SAVE. Hardware
// enforces read coverage but does not attest the software comparison.
// Physical PS-only wrapper sets ENABLE_COMPUTE=0 until a real engine
// owns the compute port; the standalone adapter preserves its tested
// default ENABLE_COMPUTE=1 debug-compute test path.
module m08_axil_page_control #(
    parameter ENABLE_COMPUTE = 1'b1
) (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 aclk CLK", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET aresetn" *)
    input wire aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 aresetn RST", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME aresetn, POLARITY ACTIVE_LOW" *)
    input wire aresetn,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, HAS_BURST 0, HAS_LOCK 0, HAS_CACHE 0, HAS_PROT 1" *)
    input wire [11:0] s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *)
    input wire [2:0] s_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input wire s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire s_axi_awready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input wire [31:0] s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input wire [3:0] s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input wire s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire s_axi_wready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output reg [1:0] s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output reg s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input wire s_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input wire [11:0] s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *)
    input wire [2:0] s_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input wire s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire s_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output reg [31:0] s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output reg [1:0] s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output reg s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input wire s_axi_rready,

    // External M08 compute service: physically NOT connected yet.
    // Its owner must assert done only after all memory ops are drained.
    input wire compute_req,
    input wire compute_write,
    input wire [5:0] compute_word,
    input wire [31:0] compute_wdata,
    input wire [3:0] compute_wstrb,
    output wire compute_ack,
    output wire [31:0] compute_rdata,
    input wire compute_done,
    input wire compute_fault,
    input wire fault_in,
    output wire dispatch_accept,
    output wire page_poisoned
);
    localparam [2:0] ST_IDLE=3'd0, ST_HOST_ISSUE=3'd1,
                     ST_HOST_WAIT=3'd2, ST_CMD_ISSUE=3'd3,
                     ST_CMD_WAIT=3'd4;
    localparam [1:0] OKAY=2'b00, SLVERR=2'b10, DECERR=2'b11;
    localparam [2:0] EMPTY=3'd0, LOADING=3'd1, READY=3'd2,
                     RUNNING=3'd3, DIRTY=3'd4;
    reg [2:0] state;
    reg aw_pending, w_pending, ar_pending;
    reg [11:0] aw_addr_q, ar_addr_q;
    reg [31:0] w_data_q;
    reg [3:0] w_strb_q;
    reg [31:0] selected_logical;
    reg op_write;
    reg [5:0] op_word;
    reg [31:0] op_data;
    reg [3:0] op_strb;
    reg [3:0] op_cmd;
    // A failed bank handshake may not lock AXI forever. The bridge
    // quarantines itself until external reset after a bounded timeout.
    reg bridge_fault;
    reg [7:0] host_wait_count;

    wire [2:0] bank_phase;
    wire bank_poisoned, bank_host_busy, bank_compute_busy;
    wire bank_page_valid, bank_page_dirty;
    wire [31:0] bank_page_logical;
    wire [8:0] bank_loaded_bytes;
    wire bank_host_ack, bank_host_error;
    wire [31:0] bank_host_rdata;
    wire bank_host_req=(state==ST_HOST_ISSUE);
    wire bank_begin=(state==ST_CMD_ISSUE && op_cmd==4'h1);
    wire bank_commit=(state==ST_CMD_ISSUE && op_cmd==4'h2);
    wire bank_dispatch=(state==ST_CMD_ISSUE && op_cmd==4'h4);
    wire bank_save=(state==ST_CMD_ISSUE && op_cmd==4'h8);
    wire [31:0] status_word={23'b0,bridge_fault,bank_host_busy,
                              bank_compute_busy,bank_page_dirty,
                              bank_page_valid,bank_poisoned,bank_phase};

    assign page_poisoned=bank_poisoned || bridge_fault;
    // A full write pair is reserved once either half has arrived.  A
    // read is not accepted until the write has been fully handled.
    assign s_axi_awready=aresetn && state==ST_IDLE && !aw_pending &&
                         !ar_pending && !s_axi_bvalid && !s_axi_rvalid;
    assign s_axi_wready=aresetn && state==ST_IDLE && !w_pending &&
                        !ar_pending && !s_axi_bvalid && !s_axi_rvalid;
    assign s_axi_arready=aresetn && state==ST_IDLE && !ar_pending &&
                         !aw_pending && !w_pending && !s_axi_awvalid &&
                         !s_axi_wvalid && !s_axi_bvalid && !s_axi_rvalid;

    m08_host_staged_page_bank bank (
        .clk(aclk),.resetn(aresetn),
        .host_begin(bank_begin),.host_begin_logical(selected_logical),
        .host_req(bank_host_req),.host_write(op_write),
        .host_word(op_word),.host_wdata(op_data),.host_wstrb(op_strb),
        .host_commit(bank_commit),.host_readback_verified(bank_commit),
        .host_save_done(bank_save),.host_ack(bank_host_ack),
        .host_error(bank_host_error),.host_rdata(bank_host_rdata),
        .dispatch_req(bank_dispatch),.dispatch_logical(selected_logical),
        .dispatch_accept(dispatch_accept),
        .compute_req(compute_req),.compute_write(compute_write),
        .compute_word(compute_word),.compute_wdata(compute_wdata),
        .compute_wstrb(compute_wstrb),.compute_ack(compute_ack),
        .compute_rdata(compute_rdata),.compute_done(compute_done),
        .compute_fault(compute_fault),.fault_in(fault_in),
        .phase(bank_phase),.poisoned(bank_poisoned),
        .host_busy(bank_host_busy),.compute_busy(bank_compute_busy),
        .page_valid(bank_page_valid),.page_dirty(bank_page_dirty),
        .page_logical(bank_page_logical),
        .loaded_byte_count(bank_loaded_bytes)
    );

    always @(posedge aclk) begin
        if(!aresetn) begin
            state<=ST_IDLE;
            aw_pending<=0;w_pending<=0;ar_pending<=0;
            aw_addr_q<=0;ar_addr_q<=0;w_data_q<=0;w_strb_q<=0;
            selected_logical<=0;
            bridge_fault<=0;host_wait_count<=0;
            op_write<=0;op_word<=0;op_data<=0;op_strb<=0;op_cmd<=0;
            s_axi_bresp<=OKAY;s_axi_bvalid<=0;
            s_axi_rresp<=OKAY;s_axi_rdata<=0;s_axi_rvalid<=0;
        end else begin
            if(s_axi_bvalid && s_axi_bready)
                s_axi_bvalid<=0;
            if(s_axi_rvalid && s_axi_rready)
                s_axi_rvalid<=0;

            if(s_axi_awvalid && s_axi_awready) begin
                aw_addr_q<=s_axi_awaddr;
                aw_pending<=1;
            end
            if(s_axi_wvalid && s_axi_wready) begin
                w_data_q<=s_axi_wdata;
                w_strb_q<=s_axi_wstrb;
                w_pending<=1;
            end
            if(s_axi_arvalid && s_axi_arready) begin
                ar_addr_q<=s_axi_araddr;
                ar_pending<=1;
            end

            case(state)
                ST_IDLE: begin
                    if(aw_pending && w_pending) begin
                        aw_pending<=0;
                        w_pending<=0;
                        if(bridge_fault) begin
                            s_axi_bresp<=SLVERR;
                            s_axi_bvalid<=1;
                        end else if(aw_addr_q[1:0]!=0) begin
                            s_axi_bresp<=DECERR;
                            s_axi_bvalid<=1;
                        end else if(aw_addr_q==12'h010) begin
                            if(w_strb_q==4'hf && bank_phase!=RUNNING &&
                               !bank_poisoned) begin
                                selected_logical<=w_data_q;
                                s_axi_bresp<=OKAY;
                            end else s_axi_bresp<=SLVERR;
                            s_axi_bvalid<=1;
                        end else if(aw_addr_q==12'h014) begin
                            if(w_strb_q!=4'hf || bank_poisoned) begin
                                s_axi_bresp<=SLVERR;
                                s_axi_bvalid<=1;
                            end else if((w_data_q==32'h1 &&
                                         (bank_phase==EMPTY || bank_phase==READY)) ||
                                        (w_data_q==32'h2 && bank_phase==LOADING) ||
                                        (w_data_q==32'h4 && bank_phase==READY &&
                                         ENABLE_COMPUTE) ||
                                        (w_data_q==32'h8 && bank_phase==DIRTY)) begin
                                op_cmd<=w_data_q[3:0];
                                state<=ST_CMD_ISSUE;
                            end else begin
                                s_axi_bresp<=SLVERR;
                                s_axi_bvalid<=1;
                            end
                        end else if(aw_addr_q[11:8]==4'h1) begin
                            if(bank_phase==LOADING && w_strb_q!=0) begin
                                op_write<=1;
                                op_word<=aw_addr_q[7:2];
                                op_data<=w_data_q;
                                op_strb<=w_strb_q;
                                state<=ST_HOST_ISSUE;
                            end else begin
                                s_axi_bresp<=SLVERR;
                                s_axi_bvalid<=1;
                            end
                        end else if(aw_addr_q==12'h000 ||
                                    aw_addr_q==12'h004 ||
                                    aw_addr_q==12'h008 ||
                                    aw_addr_q==12'h00c ||
                                    aw_addr_q==12'h018 ||
                                    aw_addr_q==12'h01c) begin
                            // Known immutable/status locations are read-only.
                            s_axi_bresp<=SLVERR;
                            s_axi_bvalid<=1;
                        end else begin
                            s_axi_bresp<=DECERR;
                            s_axi_bvalid<=1;
                        end
                    end else if(ar_pending) begin
                        ar_pending<=0;
                        if(ar_addr_q[1:0]!=0) begin
                            s_axi_rresp<=DECERR;
                            s_axi_rdata<=0;
                            s_axi_rvalid<=1;
                        end else if(ar_addr_q[11:8]==4'h1) begin
                            if(!bridge_fault && (bank_phase==LOADING ||
                               bank_phase==READY || bank_phase==DIRTY)) begin
                                op_write<=0;
                                op_word<=ar_addr_q[7:2];
                                op_data<=0;
                                op_strb<=0;
                                state<=ST_HOST_ISSUE;
                            end else begin
                                s_axi_rresp<=SLVERR;
                                s_axi_rdata<=0;
                                s_axi_rvalid<=1;
                            end
                        end else begin
                            s_axi_rresp<=OKAY;
                            s_axi_rvalid<=1;
                            case(ar_addr_q)
                                12'h000:s_axi_rdata<=32'h4d303850;
                                12'h004:s_axi_rdata<=32'h00020002;
                                12'h008:s_axi_rdata<=32'h00000001;
                                12'h00c:s_axi_rdata<=status_word;
                                12'h010:s_axi_rdata<=selected_logical;
                                12'h014:s_axi_rdata<=0;
                                12'h018:s_axi_rdata<=bank_page_logical;
                                12'h01c:s_axi_rdata<={23'd0,bank_loaded_bytes};
                                default:begin
                                    s_axi_rdata<=0;
                                    s_axi_rresp<=DECERR;
                                end
                            endcase
                        end
                    end
                end
                ST_HOST_ISSUE:begin
                    host_wait_count<=0;
                    state<=ST_HOST_WAIT;
                end
                ST_HOST_WAIT:begin
                    if(bank_host_ack || bank_host_error || bank_poisoned) begin
                        state<=ST_IDLE;
                        if(op_write) begin
                            s_axi_bresp<=(bank_host_ack && !bank_poisoned &&
                                          !bank_host_error)?OKAY:SLVERR;
                            s_axi_bvalid<=1;
                        end else begin
                            s_axi_rdata<=bank_host_ack?bank_host_rdata:0;
                            s_axi_rresp<=(bank_host_ack && !bank_poisoned &&
                                          !bank_host_error)?OKAY:SLVERR;
                            s_axi_rvalid<=1;
                        end
                    end else if(host_wait_count==8'd63) begin
                        bridge_fault<=1;
                        state<=ST_IDLE;
                        if(op_write) begin
                            s_axi_bresp<=SLVERR;
                            s_axi_bvalid<=1;
                        end else begin
                            s_axi_rdata<=0;
                            s_axi_rresp<=SLVERR;
                            s_axi_rvalid<=1;
                        end
                    end else host_wait_count<=host_wait_count+8'd1;
                end
                ST_CMD_ISSUE:state<=ST_CMD_WAIT;
                ST_CMD_WAIT:begin
                    state<=ST_IDLE;
                    // Check the actual bank state after its command edge.
                    if(bank_poisoned ||
                       ((op_cmd==4'h1) && bank_phase!=LOADING) ||
                       ((op_cmd==4'h2 || op_cmd==4'h8) && bank_phase!=READY) ||
                       ((op_cmd==4'h4) && bank_phase!=RUNNING))
                        s_axi_bresp<=SLVERR;
                    else
                        s_axi_bresp<=OKAY;
                    s_axi_bvalid<=1;
                end
                default:state<=ST_IDLE;
            endcase
        end
    end
endmodule
