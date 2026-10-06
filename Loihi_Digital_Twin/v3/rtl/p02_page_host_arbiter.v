`timescale 1ns/1ps

// P02.3a arbitration for P05 context-memory Port B.
//
// While page_active is asserted, the page walker owns new transactions on the
// existing P05 host/debug port and external debug access is back-pressured.
//
// Response ownership is latched per transaction.  This matters on the final
// page-walker word: page_active may deassert immediately after the walker
// samples fabric_ack, while the fabric response is still visible for the rest
// of that clock cycle.  A latched owner prevents that response from appearing
// spuriously on the debug side.
module p02_page_host_arbiter (
    input  wire         clk,
    input  wire         resetn,
    input  wire         page_active,

    input  wire         debug_req,
    input  wire         debug_write,
    input  wire [1:0]   debug_context_slot,
    input  wire [3:0]   debug_bank,
    input  wire [14:0]  debug_addr,
    input  wire [255:0] debug_wdata,
    output wire         debug_busy,
    output wire         debug_ack,
    output wire         debug_rvalid,
    output wire         debug_error,
    output wire [255:0] debug_rdata,

    input  wire         page_req,
    input  wire         page_write,
    input  wire [1:0]   page_context_slot,
    input  wire [3:0]   page_bank,
    input  wire [14:0]  page_addr,
    input  wire [255:0] page_wdata,
    output wire         page_busy,
    output wire         page_ack,
    output wire         page_rvalid,
    output wire         page_error,
    output wire [255:0] page_rdata,

    output wire         fabric_req,
    output wire         fabric_write,
    output wire [1:0]   fabric_context_slot,
    output wire [3:0]   fabric_bank,
    output wire [14:0]  fabric_addr,
    output wire [255:0] fabric_wdata,
    input  wire         fabric_busy,
    input  wire         fabric_ack,
    input  wire         fabric_rvalid,
    input  wire         fabric_error,
    input  wire [255:0] fabric_rdata
);
    reg transaction_active;
    reg transaction_page_owner;
    reg wait_request_low;

    wire selected_req = page_active ? page_req : debug_req;

    // The downstream P05 host contract is edge-sensitive. A requester may
    // legally keep its request level asserted until it observes ACK. After a
    // completed transaction, suppress that same request level until it has
    // returned low at least once. Without this fence, transaction_active can
    // re-arm on a held-high debug request while the prior fabric ACK/RVALID
    // are still visible, exposing stale response data as a phantom transaction.
    assign fabric_req = selected_req && !wait_request_low;
    assign fabric_write = page_active ? page_write : debug_write;
    assign fabric_context_slot =
        page_active ? page_context_slot : debug_context_slot;
    assign fabric_bank = page_active ? page_bank : debug_bank;
    assign fabric_addr = page_active ? page_addr : debug_addr;
    assign fabric_wdata = page_active ? page_wdata : debug_wdata;

    // A page command waits for an already-issued debug transaction to retire.
    assign page_busy =
        fabric_busy || wait_request_low ||
        (transaction_active && !transaction_page_owner);

    // Debug is blocked for the full duration of page ownership, including gaps
    // between individual scalar bank transactions.
    assign debug_busy =
        page_active || debug_req || fabric_busy || wait_request_low ||
        (transaction_active && transaction_page_owner);

    assign debug_ack =
        fabric_ack && transaction_active && !transaction_page_owner;
    assign debug_rvalid =
        fabric_rvalid && transaction_active && !transaction_page_owner;
    assign debug_error =
        fabric_error && transaction_active && !transaction_page_owner;
    assign debug_rdata =
        (transaction_active && !transaction_page_owner) ? fabric_rdata : 256'd0;

    assign page_ack =
        fabric_ack && transaction_active && transaction_page_owner;
    assign page_rvalid =
        fabric_rvalid && transaction_active && transaction_page_owner;
    assign page_error =
        fabric_error && transaction_active && transaction_page_owner;
    assign page_rdata =
        (transaction_active && transaction_page_owner) ? fabric_rdata : 256'd0;

    always @(posedge clk) begin
        if (!resetn) begin
            transaction_active <= 1'b0;
            transaction_page_owner <= 1'b0;
            wait_request_low <= 1'b0;
        end else begin
            if (wait_request_low) begin
                if (!selected_req)
                    wait_request_low <= 1'b0;
            end else if (!transaction_active && selected_req) begin
                transaction_active <= 1'b1;
                transaction_page_owner <= page_active;
            end

            if (transaction_active && fabric_ack) begin
                transaction_active <= 1'b0;
                wait_request_low <= 1'b1;
            end
        end
    end
endmodule
