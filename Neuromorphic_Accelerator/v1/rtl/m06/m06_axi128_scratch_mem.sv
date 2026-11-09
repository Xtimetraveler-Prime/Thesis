// M06 standalone SIMULATION-ONLY AXI4 128-bit scratch endpoint.
//
// This is NOT a vendor SmartConnect IP model, not physical PS DDR, and not
// a synthesizable memory controller. For future original mem_sc/M00_AXI
// transaction BFM attachment. Exactly one READ and one WRITE outstanding
// independently; INCR 16-byte beats, AW/AR len <=31, no 4KiB crossing,
// 8192-byte default synthetic address region (optional 65536-byte full
// canonical 4096x16B region), deterministic READY stalls.
//
// WSTRB byte lanes are written ONLY on accepted W handshakes.
// A failed write response does NOT imply page atomicity. The protocol
// oracle must quarantine partially updated pages after errors.
module m06_axi128_scratch_mem #(
    parameter integer SCRATCH_BYTES = 8192
) (
    input  wire          aclk,
    input  wire          aresetn,
    input  wire [48:0]   s_axi_awaddr,
    input  wire [7:0]    s_axi_awlen,
    input  wire [2:0]    s_axi_awsize,
    input  wire [1:0]    s_axi_awburst,
    input  wire          s_axi_awvalid,
    output wire          s_axi_awready,
    input  wire [127:0]  s_axi_wdata,
    input  wire [15:0]   s_axi_wstrb,
    input  wire          s_axi_wlast,
    input  wire          s_axi_wvalid,
    output wire          s_axi_wready,
    output reg  [1:0]    s_axi_bresp,
    output reg           s_axi_bvalid,
    input  wire          s_axi_bready,
    input  wire [48:0]   s_axi_araddr,
    input  wire [7:0]    s_axi_arlen,
    input  wire [2:0]    s_axi_arsize,
    input  wire [1:0]    s_axi_arburst,
    input  wire          s_axi_arvalid,
    output wire          s_axi_arready,
    output reg  [127:0]  s_axi_rdata,
    output reg  [1:0]    s_axi_rresp,
    output reg           s_axi_rlast,
    output reg           s_axi_rvalid,
    input  wire          s_axi_rready,
    input  wire          inject_next_b_slverr,
    input  wire          inject_next_r_slverr
);
    reg [7:0] mem [0:SCRATCH_BYTES-1];
    reg [31:0] cycles;
    reg wr_active;
    reg [48:0] wr_address;
    reg [8:0] wr_beats_left;
    reg wr_bad_request;
    reg wr_inject_b_error;
    reg [48:0] rd_address;
    reg [8:0] rd_beats_left;
    reg rd_bad_request;
    reg rd_inject_r_error;

    integer k;
    initial begin
        for (k=0; k<SCRATCH_BYTES; k=k+1)
            mem[k] = (13*k+17) & 8'hff;
    end

    function automatic legal_request;
        input [48:0] address;
        input [7:0] len;
        input [2:0] size;
        input [1:0] burst;
        reg [49:0] byte_count;
        reg [49:0] address_end;
        begin
            byte_count = ({42'd0, len} + 50'd1) << 4;
            address_end = {1'b0,address} + byte_count;
            legal_request = (size == 3'd4) &&
                            (burst == 2'b01) &&
                            (address[3:0] == 4'd0) &&
                            (len < 8'd32) &&
                            (address_end <= SCRATCH_BYTES) &&
                            (({38'd0,address[11:0]} + byte_count) <= 50'd4096);
        end
    endfunction

    function automatic [127:0] loaded_word;
        input [48:0] address;
        integer n;
        begin
            loaded_word = 128'd0;
            if ({1'b0,address} + 50'd16 <= SCRATCH_BYTES) begin
                for (n=0; n<16; n=n+1)
                    loaded_word[8*n +: 8] = mem[address[15:0]+n];
            end
        end
    endfunction

    // Deterministic synthetic backpressure. This is a BFM test aid,
    // NOT a calibrated FPGA memory latency or vendor AXI parameter.
    wire can_accept = (cycles % 3 != 1);
    assign s_axi_awready = aresetn && !wr_active &&
                           !s_axi_bvalid && can_accept;
    assign s_axi_wready = aresetn && wr_active &&
                          !s_axi_bvalid && can_accept;
    assign s_axi_arready = aresetn && !s_axi_rvalid && can_accept;

    integer lane;
    always @(posedge aclk) begin
        if (!aresetn) begin
            cycles <= 0;
            wr_active <= 0;
            wr_address <= 0;
            wr_beats_left <= 0;
            wr_bad_request <= 0;
            wr_inject_b_error <= 0;
            s_axi_bvalid <= 0;
            s_axi_bresp <= 2'b00;
            rd_address <= 0;
            rd_beats_left <= 0;
            rd_bad_request <= 0;
            rd_inject_r_error <= 0;
            s_axi_rdata <= 0;
            s_axi_rresp <= 2'b00;
            s_axi_rlast <= 0;
            s_axi_rvalid <= 0;
        end else begin
            cycles <= cycles+1;
            if (s_axi_awvalid && s_axi_awready) begin
                wr_active <= 1;
                wr_address <= s_axi_awaddr;
                wr_beats_left <= {1'b0,s_axi_awlen}+1;
                wr_bad_request <= !legal_request(
                    s_axi_awaddr,s_axi_awlen,s_axi_awsize,s_axi_awburst);
                wr_inject_b_error <= inject_next_b_slverr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                if (!wr_bad_request &&
                    (s_axi_wlast == (wr_beats_left == 9'd1))) begin
                    for (lane=0; lane<16; lane=lane+1) begin
                        if (s_axi_wstrb[lane])
                            mem[wr_address[15:0]+lane] <=
                                s_axi_wdata[8*lane +: 8];
                    end
                end
                if (wr_beats_left == 9'd1 || s_axi_wlast) begin
                    wr_active <= 0;
                    s_axi_bvalid <= 1;
                    if (wr_bad_request)
                        s_axi_bresp <= 2'b11; // DECERR, no valid write
                    else if (wr_inject_b_error ||
                             (s_axi_wlast != (wr_beats_left == 9'd1)))
                        s_axi_bresp <= 2'b10; // SLVERR, uncertain state
                    else
                        s_axi_bresp <= 2'b00;
                end else begin
                    wr_beats_left <= wr_beats_left - 1'b1;
                    wr_address <= wr_address + 49'd16;
                end
            end
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 0;

            if (s_axi_arvalid && s_axi_arready) begin
                rd_address <= s_axi_araddr;
                rd_beats_left <= {1'b0,s_axi_arlen}+1;
                rd_bad_request <= !legal_request(
                    s_axi_araddr,s_axi_arlen,s_axi_arsize,s_axi_arburst);
                rd_inject_r_error <= inject_next_r_slverr;
                s_axi_rdata <= legal_request(
                    s_axi_araddr,s_axi_arlen,s_axi_arsize,s_axi_arburst)
                    ? loaded_word(s_axi_araddr) : 128'd0;
                s_axi_rresp <= !legal_request(
                    s_axi_araddr,s_axi_arlen,s_axi_arsize,s_axi_arburst)
                    ? 2'b11 : (inject_next_r_slverr ? 2'b10 : 2'b00);
                s_axi_rlast <= (s_axi_arlen == 0);
                s_axi_rvalid <= 1;
            end
            if (s_axi_rvalid && s_axi_rready) begin
                if (rd_beats_left == 9'd1) begin
                    s_axi_rvalid <= 0;
                    s_axi_rlast <= 0;
                end else begin
                    rd_beats_left <= rd_beats_left - 1'b1;
                    rd_address <= rd_address + 49'd16;
                    s_axi_rdata <= rd_bad_request
                        ? 128'd0 : loaded_word(rd_address+49'd16);
                    s_axi_rresp <= rd_bad_request ? 2'b11
                        : (rd_inject_r_error ? 2'b10 : 2'b00);
                    s_axi_rlast <= (rd_beats_left == 9'd2);
                end
            end
        end
    end
endmodule
