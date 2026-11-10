// M06 G3 SYNTHESIZABLE candidate: bounded 64-bit HLS AXI word addresses to
// original 32-bit AMD converter S_AXI. Single outstanding per direction.
// Legal: base-zero 64KiB scratch only, aligned 32-bit INCR, <=16 beats,
// no 4KiB crossing. Illegal requests generate DECERR, never touch AMD IP.
// Sticky fault needs a separate tested trace/epoch supervisor; neither a
// fault pin nor a source-only test proves final run atomicity or real DDR.
module m06_axi64_to32_read_guard (
    input wire aclk, input wire aresetn,
    input wire [0:0] s_arid, input wire [63:0] s_araddr,
    input wire [7:0] s_arlen, input wire [2:0] s_arsize,
    input wire [1:0] s_arburst, input wire s_arvalid,
    output wire s_arready,
    output wire [0:0] m_arid, output wire [31:0] m_araddr,
    output wire [7:0] m_arlen, output wire [2:0] m_arsize,
    output wire [1:0] m_arburst, output wire m_arvalid,
    input wire m_arready,
    input wire [0:0] m_rid, input wire [31:0] m_rdata,
    input wire [1:0] m_rresp, input wire m_rlast,
    input wire m_rvalid, output wire m_rready,
    output wire [0:0] s_rid, output wire [31:0] s_rdata,
    output wire [1:0] s_rresp, output wire s_rlast,
    output wire s_rvalid, input wire s_rready,
    output reg fault_seen
);
    localparam [1:0] IDLE=2'd0, PASS=2'd1, DECERR=2'd2;
    reg [1:0] state;
    reg [8:0] remaining;
    reg [0:0] original_id;

    function automatic is_legal;
        input [63:0] addr;
        input [7:0] len;
        input [2:0] size;
        input [1:0] burst;
        reg [16:0] num_bytes;
        begin
            num_bytes=({9'b0,len}+17'd1)<<2;
            is_legal=(addr[63:16]==48'b0 && addr[1:0]==2'b0 &&
                      size==3'd2 && burst==2'b01 && len<=8'd15 &&
                      ({1'b0,addr[15:0]}+num_bytes<=17'd65536) &&
                      ({5'b0,addr[11:0]}+num_bytes<=17'd4096));
        end
    endfunction
    wire legal_request = is_legal(s_araddr,s_arlen,s_arsize,s_arburst) && !fault_seen;
    assign s_arready = (state==IDLE) && (legal_request ? m_arready : 1'b1);
    assign m_arvalid = (state==IDLE) && s_arvalid && legal_request;
    assign m_arid=s_arid;
    assign m_araddr=s_araddr[31:0]; // forwarded only when bounded/allowed
    assign m_arlen=s_arlen;
    assign m_arsize=s_arsize;
    assign m_arburst=s_arburst;
    assign m_rready = (state==PASS) && s_rready;
    assign s_rvalid = (state==PASS) ? m_rvalid : (state==DECERR);
    assign s_rid = (state==PASS) ? m_rid : original_id;
    assign s_rdata = (state==PASS) ? m_rdata : 32'b0;
    assign s_rresp = (state==PASS) ? m_rresp : 2'b11;
    assign s_rlast = (state==PASS) ? m_rlast : remaining==9'd1;

    always @(posedge aclk) begin
        if (!aresetn) begin
            state<=IDLE;
            remaining<=0;
            original_id<=0;
            fault_seen<=0;
        end else begin
            case(state)
                IDLE: if (s_arvalid && s_arready) begin
                    remaining<={1'b0,s_arlen}+9'd1;
                    original_id<=s_arid;
                    if (legal_request) state<=PASS;
                    else begin
                        state<=DECERR;
                        fault_seen<=1'b1;
                    end
                end
                PASS: if (m_rvalid && m_rready) begin
                    if (m_rresp!=2'b00 || m_rlast!=(remaining==9'd1) ||
                        m_rid!=original_id)
                        fault_seen<=1'b1;
                    if (remaining!=0) remaining<=remaining-9'd1;
                    if (m_rlast || remaining==9'd1) state<=IDLE;
                end
                DECERR: if (s_rvalid && s_rready) begin
                    if (remaining!=0) remaining<=remaining-9'd1;
                    if (remaining==9'd1) state<=IDLE;
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule

module m06_axi64_to32_write_guard (
    input wire aclk, input wire aresetn,
    input wire [0:0] s_awid, input wire [63:0] s_awaddr,
    input wire [7:0] s_awlen, input wire [2:0] s_awsize,
    input wire [1:0] s_awburst, input wire s_awvalid,
    output wire s_awready,
    output wire [0:0] m_awid, output wire [31:0] m_awaddr,
    output wire [7:0] m_awlen, output wire [2:0] m_awsize,
    output wire [1:0] m_awburst, output wire m_awvalid,
    input wire m_awready,
    input wire [31:0] s_wdata, input wire [3:0] s_wstrb,
    input wire s_wlast, input wire s_wvalid, output wire s_wready,
    output wire [31:0] m_wdata, output wire [3:0] m_wstrb,
    output wire m_wlast, output wire m_wvalid, input wire m_wready,
    input wire [0:0] m_bid, input wire [1:0] m_bresp,
    input wire m_bvalid, output wire m_bready,
    output wire [0:0] s_bid, output wire [1:0] s_bresp,
    output wire s_bvalid, input wire s_bready,
    output reg fault_seen
);
    localparam [2:0] IDLE=3'd0, WRITE=3'd1, AWAIT_B=3'd2,
                     DISCARD=3'd3, DECERR=3'd4;
    reg [2:0] state;
    reg [8:0] remaining;
    reg [0:0] original_id;

    function automatic is_legal;
        input [63:0] addr;
        input [7:0] len;
        input [2:0] size;
        input [1:0] burst;
        reg [16:0] num_bytes;
        begin
            num_bytes=({9'b0,len}+17'd1)<<2;
            is_legal=(addr[63:16]==48'b0 && addr[1:0]==2'b0 &&
                      size==3'd2 && burst==2'b01 && len<=8'd15 &&
                      ({1'b0,addr[15:0]}+num_bytes<=17'd65536) &&
                      ({5'b0,addr[11:0]}+num_bytes<=17'd4096));
        end
    endfunction
    wire legal_request = is_legal(s_awaddr,s_awlen,s_awsize,s_awburst) && !fault_seen;
    assign s_awready=(state==IDLE) && (legal_request ? m_awready : 1'b1);
    assign m_awvalid=(state==IDLE) && s_awvalid && legal_request;
    assign m_awid=s_awid;
    assign m_awaddr=s_awaddr[31:0]; // high bits never forwarded when invalid
    assign m_awlen=s_awlen;
    assign m_awsize=s_awsize;
    assign m_awburst=s_awburst;
    assign s_wready=(state==WRITE) ? m_wready : (state==DISCARD);
    assign m_wvalid=(state==WRITE) && s_wvalid;
    assign m_wdata=s_wdata;
    assign m_wstrb=s_wstrb;
    assign m_wlast=s_wlast;
    assign s_bvalid=(state==AWAIT_B) ? m_bvalid : (state==DECERR);
    assign s_bid=(state==AWAIT_B) ? m_bid : original_id;
    assign s_bresp=(state==AWAIT_B) ? m_bresp : 2'b11;
    assign m_bready=(state==AWAIT_B) && s_bready;

    always @(posedge aclk) begin
        if (!aresetn) begin
            state<=IDLE;
            remaining<=0;
            original_id<=0;
            fault_seen<=0;
        end else begin
            case(state)
                IDLE: if (s_awvalid && s_awready) begin
                    remaining<={1'b0,s_awlen}+9'd1;
                    original_id<=s_awid;
                    if (legal_request) state<=WRITE;
                    else begin
                        state<=DISCARD;
                        fault_seen<=1'b1;
                    end
                end
                WRITE: if (s_wvalid && s_wready) begin
                    if (s_wlast!=(remaining==9'd1)) fault_seen<=1'b1;
                    if (remaining!=0) remaining<=remaining-9'd1;
                    if (remaining==9'd1) state<=AWAIT_B;
                end
                DISCARD: if (s_wvalid && s_wready) begin
                    if (s_wlast!=(remaining==9'd1)) fault_seen<=1'b1;
                    if (remaining!=0) remaining<=remaining-9'd1;
                    if (remaining==9'd1) state<=DECERR;
                end
                AWAIT_B: if (m_bvalid && m_bready) begin
                    if (m_bresp!=2'b00 || m_bid!=original_id)
                        fault_seen<=1'b1;
                    state<=IDLE;
                end
                DECERR: if (s_bvalid && s_bready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
