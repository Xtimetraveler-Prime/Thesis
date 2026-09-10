`timescale 1ns/1ps

// M13.4 audit-only testbench for pinned Catalyst scalable_core_v2.
// Positive and negative probes use separate neurons because rst_n resets core
// control state but intentionally does not clear the Catalyst state SRAMs.
module tb_m13_4_catalyst_cuba;
    localparam NUM_NEURONS = 2;
    localparam NEURON_BITS = 1;
    localparam DATA_WIDTH = 16;
    localparam POOL_DEPTH = 4;
    localparam POOL_ADDR_BITS = 2;
    localparam COUNT_BITS = 2;
    localparam REV_FANIN = 2;
    localparam REV_SLOT_BITS = 1;
    localparam CLK_PERIOD = 10;

    reg clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    reg rst_n, start;
    reg learn_enable, graded_enable, dendritic_enable, threefactor_enable;
    reg noise_enable, skip_idle_enable, scale_u_enable;
    reg signed [DATA_WIDTH-1:0] reward_value;
    reg ext_valid;
    reg [NEURON_BITS-1:0] ext_neuron_id;
    reg signed [DATA_WIDTH-1:0] ext_current;
    reg pool_we;
    reg [POOL_ADDR_BITS-1:0] pool_addr_in;
    reg [NEURON_BITS-1:0] pool_src_in, pool_target_in;
    reg signed [DATA_WIDTH-1:0] pool_weight_in;
    reg [1:0] pool_comp_in;
    reg index_we;
    reg [NEURON_BITS-1:0] index_neuron_in;
    reg [POOL_ADDR_BITS-1:0] index_base_in;
    reg [COUNT_BITS-1:0] index_count_in;
    reg [1:0] index_format_in;
    reg delay_we;
    reg [POOL_ADDR_BITS-1:0] delay_addr_in;
    reg [5:0] delay_value_in;
    reg ucode_prog_we;
    reg [7:0] ucode_prog_addr;
    reg [31:0] ucode_prog_data;
    reg prog_param_we;
    reg [NEURON_BITS-1:0] prog_param_neuron;
    reg [4:0] prog_param_id;
    reg signed [DATA_WIDTH-1:0] prog_param_value;
    reg probe_read;
    reg [NEURON_BITS-1:0] probe_neuron;
    reg [4:0] probe_state_id;
    reg [POOL_ADDR_BITS-1:0] probe_pool_addr;

    wire signed [DATA_WIDTH-1:0] probe_data;
    wire probe_valid;
    wire timestep_done, spike_out_valid;
    wire [NEURON_BITS-1:0] spike_out_id;
    wire [7:0] spike_out_payload;
    wire [5:0] state_out;
    wire [31:0] total_spikes, timestep_count;
    wire core_idle;

    scalable_core_v2 #(
        .NUM_NEURONS(NUM_NEURONS), .NEURON_BITS(NEURON_BITS),
        .DATA_WIDTH(DATA_WIDTH), .POOL_DEPTH(POOL_DEPTH),
        .POOL_ADDR_BITS(POOL_ADDR_BITS), .COUNT_BITS(COUNT_BITS),
        .REV_FANIN(REV_FANIN), .REV_SLOT_BITS(REV_SLOT_BITS), .NEURON_WIDTH(24)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .learn_enable(learn_enable), .graded_enable(graded_enable),
        .dendritic_enable(dendritic_enable), .threefactor_enable(threefactor_enable),
        .noise_enable(noise_enable), .skip_idle_enable(skip_idle_enable),
        .scale_u_enable(scale_u_enable), .reward_value(reward_value),
        .ext_valid(ext_valid), .ext_neuron_id(ext_neuron_id), .ext_current(ext_current),
        .pool_we(pool_we), .pool_addr_in(pool_addr_in), .pool_src_in(pool_src_in),
        .pool_target_in(pool_target_in), .pool_weight_in(pool_weight_in), .pool_comp_in(pool_comp_in),
        .index_we(index_we), .index_neuron_in(index_neuron_in), .index_base_in(index_base_in),
        .index_count_in(index_count_in), .index_format_in(index_format_in),
        .delay_we(delay_we), .delay_addr_in(delay_addr_in), .delay_value_in(delay_value_in),
        .ucode_prog_we(ucode_prog_we), .ucode_prog_addr(ucode_prog_addr), .ucode_prog_data(ucode_prog_data),
        .prog_param_we(prog_param_we), .prog_param_neuron(prog_param_neuron),
        .prog_param_id(prog_param_id), .prog_param_value(prog_param_value),
        .probe_read(probe_read), .probe_neuron(probe_neuron), .probe_state_id(probe_state_id),
        .probe_pool_addr(probe_pool_addr), .probe_data(probe_data), .probe_valid(probe_valid),
        .timestep_done(timestep_done), .spike_out_valid(spike_out_valid), .spike_out_id(spike_out_id),
        .spike_out_payload(spike_out_payload), .state_out(state_out), .total_spikes(total_spikes),
        .timestep_count(timestep_count), .core_idle(core_idle)
    );

    reg signed [15:0] last_probe;
    reg [1:0] spike_seen;
    always @(posedge clk) begin
        if (!rst_n)
            spike_seen <= 0;
        else if (spike_out_valid)
            spike_seen[spike_out_id] <= 1'b1;
    end

    task init_inputs;
    begin
        start=0; learn_enable=0; graded_enable=0; dendritic_enable=0;
        threefactor_enable=0; noise_enable=0; skip_idle_enable=0; scale_u_enable=0; reward_value=0;
        ext_valid=0; ext_neuron_id=0; ext_current=0;
        pool_we=0; pool_addr_in=0; pool_src_in=0; pool_target_in=0; pool_weight_in=0; pool_comp_in=0;
        index_we=0; index_neuron_in=0; index_base_in=0; index_count_in=0; index_format_in=0;
        delay_we=0; delay_addr_in=0; delay_value_in=0;
        ucode_prog_we=0; ucode_prog_addr=0; ucode_prog_data=0;
        prog_param_we=0; prog_param_neuron=0; prog_param_id=0; prog_param_value=0;
        probe_read=0; probe_neuron=0; probe_state_id=0; probe_pool_addr=0;
        spike_seen=0;
    end
    endtask

    task reset_core;
    begin
        rst_n=0; repeat(4) @(posedge clk); rst_n=1; repeat(3) @(posedge clk);
    end
    endtask

    task set_param;
        input [NEURON_BITS-1:0] neuron;
        input [4:0] pid;
        input signed [15:0] value;
    begin
        @(posedge clk); prog_param_we<=1; prog_param_neuron<=neuron; prog_param_id<=pid; prog_param_value<=value;
        @(posedge clk); prog_param_we<=0; prog_param_id<=0; prog_param_value<=0;
        @(posedge clk);
    end
    endtask

    task run_tick;
        input integer has_input;
        input [NEURON_BITS-1:0] neuron;
        input signed [15:0] value;
    begin
        spike_seen=0;
        if (has_input != 0) begin
            @(posedge clk); ext_valid<=1; ext_neuron_id<=neuron; ext_current<=value;
            @(posedge clk); ext_valid<=0; ext_current<=0;
        end
        @(posedge clk); start<=1;
        @(posedge clk); start<=0;
        wait(timestep_done); @(posedge clk);
    end
    endtask

    task read_probe;
        input [NEURON_BITS-1:0] neuron;
        input [4:0] sid;
    begin
        probe_neuron<=neuron; probe_state_id<=sid; probe_read<=1;
        @(posedge clk); probe_read<=0; wait(probe_valid); last_probe=$signed(probe_data); @(posedge clk);
    end
    endtask

    task emit_tick;
        input [8*32-1:0] case_name;
        input [NEURON_BITS-1:0] neuron;
        input integer native_tick;
        reg signed [15:0] cur, volt, refr;
        reg seen;
    begin
        seen=spike_seen[neuron];
        read_probe(neuron,5'd13); cur=last_probe;
        read_probe(neuron,5'd0);  volt=last_probe;
        read_probe(neuron,5'd4);  refr=last_probe;
        $display("M13_4_CUBA|case=%0s|native_tick=%0d|current=%0d|voltage=%0d|refractory=%0d|spike=%0d",
                 case_name,native_tick,cur,volt,refr,seen);
    end
    endtask

    integer t;
    initial begin
        init_inputs;
        reset_core;

        // Configure separate zero-initialized state slots before either probe.
        // Neuron 0: positive isolated impulse, canonical dI=dV=2048, W=+512, T=8192.
        set_param(0,5'd0,16'sd8193); set_param(0,5'd2,16'sd0); set_param(0,5'd3,16'sd0);
        set_param(0,5'd16,16'sd2048); set_param(0,5'd17,16'sd2048);
        // Neuron 1: negative rounding, canonical dI=1025,dV=0,W=-64,T=8192.
        set_param(1,5'd0,16'sd8193); set_param(1,5'd2,16'sd0); set_param(1,5'd3,16'sd0);
        set_param(1,5'd16,16'sd0); set_param(1,5'd17,16'sd1025);

        run_tick(1,0,16'sd512); emit_tick("positive",0,0);
        for(t=1;t<5;t=t+1) begin run_tick(0,0,16'sd0); emit_tick("positive",0,t); end

        run_tick(1,1,-16'sd64); emit_tick("negative",1,0);
        for(t=1;t<4;t=t+1) begin run_tick(0,1,16'sd0); emit_tick("negative",1,t); end

        $display("M13_4_CUBA_DONE");
        $finish;
    end

    initial begin
        #3000000; $display("M13_4_CUBA_TIMEOUT"); $finish(2);
    end
endmodule
