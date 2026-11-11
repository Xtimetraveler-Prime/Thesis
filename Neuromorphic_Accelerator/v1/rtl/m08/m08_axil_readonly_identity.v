// M08.2 standalone candidate: PS-readable, SIDE-EFFECT-FREE PL identity.
// This is NOT integrated into a KV260 Vivado BD or a physical bitstream.
// It has no AXI master, no address-generation, no DMA, no neuron update.
// Every AXI-Lite write is rejected with SLVERR (2'b10); AW and W may arrive
// in any order and are paired before the single acknowledged B response.
// Reads respond with fixed 32-bit words and stable RDATA/RRESP under stalls.
// BUILD_ID is provisioned only by later verified real design integration;
// default ZERO is NOT evidence of a particular firmware/version/bitstream.
module m08_axil_readonly_identity #(
    parameter [31:0] BUILD_ID0 = 32'h00000000,
    parameter [31:0] BUILD_ID1 = 32'h00000000,
    parameter [31:0] BUILD_ID2 = 32'h00000000,
    parameter [31:0] BUILD_ID3 = 32'h00000000
) (
    input  wire        aclk,
    input  wire        aresetn,
    input  wire [7:0]  s_axi_awaddr,
    input  wire [2:0]  s_axi_awprot,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,
    output reg  [1:0]  s_axi_bresp,
    output reg         s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [7:0]  s_axi_araddr,
    input  wire [2:0]  s_axi_arprot,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,
    output reg  [31:0] s_axi_rdata,
    output reg  [1:0]  s_axi_rresp,
    output reg         s_axi_rvalid,
    input  wire        s_axi_rready
);
    // Deliberately do not connect AWPROT/ARPROT, WSTRB or WDATA to any
    // writable register. They are protocol inputs, not write authority.
    reg aw_seen;
    reg w_seen;

    assign s_axi_awready = aresetn && !aw_seen && !s_axi_bvalid;
    assign s_axi_wready  = aresetn && !w_seen  && !s_axi_bvalid;
    assign s_axi_arready = aresetn && !s_axi_rvalid;

    wire aw_fire = s_axi_awvalid && s_axi_awready;
    wire w_fire  = s_axi_wvalid  && s_axi_wready;
    wire ar_fire = s_axi_arvalid && s_axi_arready;

    always @(posedge aclk) begin
        if (!aresetn) begin
            aw_seen <= 1'b0;
            w_seen <= 1'b0;
            s_axi_bvalid <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            s_axi_rresp <= 2'b00;
            s_axi_rdata <= 32'b0;
        end else begin
            if (s_axi_bvalid) begin
                if (s_axi_bready) begin
                    s_axi_bvalid <= 1'b0;
                    s_axi_bresp <= 2'b00;
                end
            end else begin
                if (aw_fire)
                    aw_seen <= 1'b1;
                if (w_fire)
                    w_seen <= 1'b1;
                if ((aw_seen || aw_fire) && (w_seen || w_fire)) begin
                    aw_seen <= 1'b0;
                    w_seen <= 1'b0;
                    s_axi_bvalid <= 1'b1;
                    // Always SLVERR, even for a legal read-only register.
                    s_axi_bresp <= 2'b10;
                end
            end

            if (s_axi_rvalid) begin
                if (s_axi_rready) begin
                    s_axi_rvalid <= 1'b0;
                    s_axi_rdata <= 32'b0;
                    s_axi_rresp <= 2'b00;
                end
            end else if (ar_fire) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp <= 2'b00; // OKAY for exact implemented address
                case (s_axi_araddr)
                    8'h00: s_axi_rdata <= 32'h4D303831; // ASCII M081
                    8'h04: s_axi_rdata <= 32'h00010000; // protocol v1.0
                    8'h08: s_axi_rdata <= 32'h00000000; // no master/DMA
                    8'h0c: s_axi_rdata <= 32'h00000000; // reserved
                    8'h10: s_axi_rdata <= BUILD_ID0;
                    8'h14: s_axi_rdata <= BUILD_ID1;
                    8'h18: s_axi_rdata <= BUILD_ID2;
                    8'h1c: s_axi_rdata <= BUILD_ID3;
                    default: begin
                        s_axi_rdata <= 32'b0;
                        s_axi_rresp <= 2'b11; // DECERR, no aliasing
                    end
                endcase
            end
        end
    end
endmodule
