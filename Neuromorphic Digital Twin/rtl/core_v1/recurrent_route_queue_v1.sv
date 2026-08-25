`timescale 1ns/1ps

// M11.5.4 standalone recurrent route engine.
//
// Spikes are scanned in ascending neuron ID. For each spiking source, its CSR
// route row is traversed in stored declaration order and target axons are
// appended to the inactive recurrent-event bank. Only S_COMMIT toggles the bank
// selector, making same-tick recurrence structurally impossible.
//
// M11.5.5 keeps both 4096 x 16 recurrent banks on canonical synchronous RAM
// ports so their trace readback does not force large LUT read muxes.
module recurrent_route_queue_v1 #(
    parameter integer MAX_NEURONS = 256,
    parameter integer MAX_AXONS   = 1024,
    parameter integer MAX_ROUTES  = 4096,
    parameter integer MAX_EVENTS  = 4096
) (
    input  logic         ap_clk,
    input  logic         ap_rst,

    input  logic         core_reset_start,
    input  logic         start,
    input  logic [8:0]   neuron_count,
    input  logic [12:0]  route_count,

    output logic         busy,
    output logic         core_reset_done,
    output logic         done,
    output logic         fault,
    output logic [7:0]   fault_code,
    output logic         current_bank,
    output logic [12:0]  current_count,
    output logic [12:0]  last_consumed_count,
    output logic [12:0]  last_routed_count,
    output logic [7:0]   active_source,
    output logic [31:0]  active_route_index,

    // Static route-image and spike preload writes. Accepted only while idle.
    input  logic         route_row_we,
    input  logic [8:0]   route_row_addr,
    input  logic [31:0]  route_row_wdata,
    input  logic         route_target_we,
    input  logic [11:0]  route_target_addr,
    input  logic [15:0]  route_target_wdata,
    input  logic         spike_we,
    input  logic [7:0]   spike_addr,
    input  logic         spike_wdata,

    // Debug read of either physical recurrent bank. Counts determine validity;
    // stale words in an inactive bank are intentionally not cleared.
    input  logic         debug_re,
    input  logic         debug_bank,
    input  logic [11:0]  debug_addr,
    output logic         debug_rvalid,
    output logic [15:0]  debug_rdata,
    output logic [12:0]  debug_bank0_count,
    output logic [12:0]  debug_bank1_count
);

    localparam logic [7:0] FAULT_NONE           = 8'h00;
    localparam logic [7:0] FAULT_CONCURRENT_CMD = 8'h01;
    localparam logic [7:0] FAULT_INVALID_COUNT  = 8'h02;
    localparam logic [7:0] FAULT_ROW_POINTER    = 8'h03;
    localparam logic [7:0] FAULT_ROUTE_TARGET   = 8'h04;
    localparam logic [7:0] FAULT_QUEUE_OVERFLOW = 8'h05;

    typedef enum logic [3:0] {
        S_IDLE,
        S_SOURCE_READ,
        S_SOURCE_VALIDATE,
        S_ROUTE_READ,
        S_ROUTE_APPEND,
        S_SOURCE_ADVANCE,
        S_COMMIT
    } route_state_t;

    route_state_t state;

    (* ram_style = "block" *) logic [31:0] route_row_mem [0:MAX_NEURONS];
    (* ram_style = "block" *) logic [15:0] route_target_mem [0:MAX_ROUTES-1];
    (* ram_style = "distributed" *) logic spike_mem [0:MAX_NEURONS-1];
    (* ram_style = "block" *) logic [15:0] recurrent_bank0 [0:MAX_EVENTS-1];
    (* ram_style = "block" *) logic [15:0] recurrent_bank1 [0:MAX_EVENTS-1];

    logic [12:0] bank0_count;
    logic [12:0] bank1_count;
    logic [8:0]  latched_neuron_count;
    logic [12:0] latched_route_count;
    logic [31:0] row_start;
    logic [31:0] row_stop;
    logic [31:0] expected_row_start;
    logic [15:0] work_target;
    logic [12:0] next_count;

    logic        bank0_mem_we;
    logic [11:0] bank0_mem_waddr;
    logic [15:0] bank0_mem_wdata;
    logic        bank0_mem_re;
    logic [11:0] bank0_mem_raddr;
    logic [15:0] bank0_mem_rdata;

    logic        bank1_mem_we;
    logic [11:0] bank1_mem_waddr;
    logic [15:0] bank1_mem_wdata;
    logic        bank1_mem_re;
    logic [11:0] bank1_mem_raddr;
    logic [15:0] bank1_mem_rdata;

    assign current_count = current_bank ? bank1_count : bank0_count;
    assign debug_bank0_count = bank0_count;
    assign debug_bank1_count = bank1_count;
    assign debug_rdata = debug_bank ? bank1_mem_rdata : bank0_mem_rdata;

    function automatic logic counts_valid;
        counts_valid =
            (neuron_count != 9'd0) &&
            (neuron_count <= MAX_NEURONS) &&
            (route_count <= MAX_ROUTES);
    endfunction

    // Each recurrent bank has one explicit synchronous read/write process.
    // The router writes only the inactive bank; debug reads are accepted only
    // while the routing engine is idle, so the two uses never compete.
    always_comb begin
        bank0_mem_we    = 1'b0;
        bank0_mem_waddr = next_count[11:0];
        bank0_mem_wdata = work_target;
        bank0_mem_re    = 1'b0;
        bank0_mem_raddr = debug_addr;

        bank1_mem_we    = 1'b0;
        bank1_mem_waddr = next_count[11:0];
        bank1_mem_wdata = work_target;
        bank1_mem_re    = 1'b0;
        bank1_mem_raddr = debug_addr;

        if (
            (state == S_ROUTE_APPEND) &&
            (work_target < MAX_AXONS) &&
            (next_count < MAX_EVENTS)
        ) begin
            if (current_bank)
                bank0_mem_we = 1'b1;
            else
                bank1_mem_we = 1'b1;
        end

        if ((!busy) && debug_re) begin
            if (debug_bank)
                bank1_mem_re = 1'b1;
            else
                bank0_mem_re = 1'b1;
        end
    end

    always_ff @(posedge ap_clk) begin
        if (bank0_mem_we)
            recurrent_bank0[bank0_mem_waddr] <= bank0_mem_wdata;
        if (bank0_mem_re)
            bank0_mem_rdata <= recurrent_bank0[bank0_mem_raddr];
    end

    always_ff @(posedge ap_clk) begin
        if (bank1_mem_we)
            recurrent_bank1[bank1_mem_waddr] <= bank1_mem_wdata;
        if (bank1_mem_re)
            bank1_mem_rdata <= recurrent_bank1[bank1_mem_raddr];
    end

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            state                  <= S_IDLE;
            busy                   <= 1'b0;
            core_reset_done        <= 1'b0;
            done                   <= 1'b0;
            fault                  <= 1'b0;
            fault_code             <= FAULT_NONE;
            current_bank           <= 1'b0;
            bank0_count            <= 13'd0;
            bank1_count            <= 13'd0;
            last_consumed_count    <= 13'd0;
            last_routed_count      <= 13'd0;
            active_source          <= 8'd0;
            active_route_index     <= 32'd0;
            latched_neuron_count   <= 9'd0;
            latched_route_count    <= 13'd0;
            row_start              <= 32'd0;
            row_stop               <= 32'd0;
            expected_row_start     <= 32'd0;
            work_target            <= 16'd0;
            next_count             <= 13'd0;
            debug_rvalid           <= 1'b0;
        end else begin
            core_reset_done <= 1'b0;
            done            <= 1'b0;
            debug_rvalid    <= 1'b0;

            if (!busy) begin
                if (route_row_we)
                    route_row_mem[route_row_addr] <= route_row_wdata;
                if (route_target_we)
                    route_target_mem[route_target_addr] <= route_target_wdata;
                if (spike_we)
                    spike_mem[spike_addr] <= spike_wdata;
                if (debug_re)
                    debug_rvalid <= 1'b1;
            end

            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (core_reset_start && start) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_CONCURRENT_CMD;
                    end else if (core_reset_start) begin
                        fault               <= 1'b0;
                        fault_code          <= FAULT_NONE;
                        current_bank        <= 1'b0;
                        bank0_count         <= 13'd0;
                        bank1_count         <= 13'd0;
                        last_consumed_count <= 13'd0;
                        last_routed_count   <= 13'd0;
                        core_reset_done     <= 1'b1;
                    end else if (start) begin
                        if (!counts_valid()) begin
                            fault      <= 1'b1;
                            fault_code <= FAULT_INVALID_COUNT;
                        end else begin
                            fault                  <= 1'b0;
                            fault_code             <= FAULT_NONE;
                            busy                   <= 1'b1;
                            latched_neuron_count   <= neuron_count;
                            latched_route_count    <= route_count;
                            last_consumed_count    <= current_bank ? bank1_count : bank0_count;
                            last_routed_count      <= 13'd0;
                            active_source          <= 8'd0;
                            active_route_index     <= 32'd0;
                            expected_row_start     <= 32'd0;
                            next_count             <= 13'd0;
                            // Logically clear the inactive bank immediately by
                            // clearing its count. Old data may remain physically.
                            if (current_bank)
                                bank0_count <= 13'd0;
                            else
                                bank1_count <= 13'd0;
                            state <= S_SOURCE_READ;
                        end
                    end
                end

                S_SOURCE_READ: begin
                    row_start <= route_row_mem[active_source];
                    row_stop  <= route_row_mem[{1'b0, active_source} + 9'd1];
                    state     <= S_SOURCE_VALIDATE;
                end

                S_SOURCE_VALIDATE: begin
                    // Enforce one canonical CSR partition: each row must begin
                    // exactly where the previous row ended, all pointers stay
                    // inside route_count, and the last row must terminate there.
                    if (
                        row_start != expected_row_start ||
                        row_start > row_stop ||
                        row_stop > latched_route_count ||
                        row_stop > MAX_ROUTES ||
                        ((({1'b0, active_source} + 9'd1) >= latched_neuron_count) &&
                         (row_stop != latched_route_count))
                    ) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_ROW_POINTER;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else begin
                        expected_row_start <= row_stop;
                        if (!spike_mem[active_source] || row_start == row_stop) begin
                            state <= S_SOURCE_ADVANCE;
                        end else begin
                            active_route_index <= row_start;
                            state              <= S_ROUTE_READ;
                        end
                    end
                end

                S_ROUTE_READ: begin
                    work_target <= route_target_mem[active_route_index[11:0]];
                    state       <= S_ROUTE_APPEND;
                end

                S_ROUTE_APPEND: begin
                    if (work_target >= MAX_AXONS) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_ROUTE_TARGET;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else if (next_count >= MAX_EVENTS) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_QUEUE_OVERFLOW;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else begin
                        next_count <= next_count + 13'd1;

                        if ((active_route_index + 32'd1) >= row_stop) begin
                            state <= S_SOURCE_ADVANCE;
                        end else begin
                            active_route_index <= active_route_index + 32'd1;
                            state              <= S_ROUTE_READ;
                        end
                    end
                end

                S_SOURCE_ADVANCE: begin
                    if (({1'b0, active_source} + 9'd1) >= latched_neuron_count) begin
                        state <= S_COMMIT;
                    end else begin
                        active_source <= active_source + 8'd1;
                        state         <= S_SOURCE_READ;
                    end
                end

                S_COMMIT: begin
                    if (current_bank)
                        bank0_count <= next_count;
                    else
                        bank1_count <= next_count;
                    current_bank      <= ~current_bank;
                    last_routed_count <= next_count;
                    busy              <= 1'b0;
                    done              <= 1'b1;
                    state             <= S_IDLE;
                end

                default: begin
                    fault      <= 1'b1;
                    fault_code <= 8'hFF;
                    busy       <= 1'b0;
                    state      <= S_IDLE;
                end
            endcase
        end
    end

endmodule
