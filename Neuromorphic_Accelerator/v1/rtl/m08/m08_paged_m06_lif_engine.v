// M08.4 source candidate: REAL signed16 LIF across 6 logical 256B pages
// in ONE physically modeled AXI host-staged RAM bank. Unlike the earlier
// XOR probe, this computes membrane, spike and signed recurrent delivery.
// Original M06 32-neuron x4 tick, five positive-delay signed16 synapses;
// external currents are currently HOST-COALESCED, not original M32Q raw FIFO.
// All source tests use real Icarus + independent M02/M03 numerical oracle.
// NO Vivado timing/DRC/bitstream/physical K26/DDR/asynchronous proof yet.
// One 100-MHz-target synchronous clk, explicit owner load/readback/dispatch.
// Page ABI see scripts/m08_paged_m06_lif_fixture.py. Goldens never loaded.
module m08_paged_m06_lif_engine (
    input wire clk,
    input wire resetn,
    input wire dispatch_accept,
    input wire compute_ack,
    input wire [31:0] compute_rdata,
    output wire compute_req,
    output wire compute_write,
    output wire [5:0] compute_word,
    output wire [31:0] compute_wdata,
    output wire [3:0] compute_wstrb,
    output wire compute_done,
    output wire compute_fault,
    output reg [31:0] completed_neurons,
    output reg [31:0] completed_pages,
    output reg [31:0] computed_synaptic_events
);
    localparam [2:0] S_IDLE=3'd0, S_ISSUE=3'd1,
                     S_WAIT=3'd2, S_HANDLE=3'd3,
                     S_DONE=3'd4, S_FAULT=3'd5;
    localparam [3:0] K_MAGIC=4'd0, K_ID=4'd1,
                     K_COUNT=4'd2, K_TICK=4'd3,
                     K_EDGE=4'd4, K_EDGE_VALIDATE=4'd5,
                     K_FIELD=4'd6,
                     K_WRITE_MEM=4'd7,
                     K_WRITE_SPIKE=4'd8,
                     K_WRITE_SYN=4'd9;
    localparam [31:0] M6NF=32'h4D364E46;
    localparam [31:0] M6EG=32'h4D364547;

    reg [2:0] state;
    reg [3:0] stage;
    reg [5:0] address;
    reg txn_write;
    reg [31:0] txn_data, observed;
    reg [4:0] wait_cycles;

    reg [31:0] page_magic, page_id, page_count, page_tick;
    reg edge_configured;
    reg [3:0] edge_count;
    reg [31:0] pre [0:7];
    reg [31:0] post [0:7];
    reg signed [31:0] weight [0:7];
    reg [31:0] delay [0:7];
    reg [5:0] edge_word_idx;

    reg [2:0] expected_page;
    reg [2:0] expected_tick;
    reg [2:0] local_neuron;
    reg [2:0] field_idx;
    reg signed [15:0] v_state, bias, threshold, reset_voltage;
    reg signed [31:0] external_current;
    reg [3:0] old_spike_mask;
    reg signed [15:0] result_v;
    reg result_fire;
    reg signed [31:0] result_syn;

    // This is a small globally resident 32x4 SPIKE HISTORY, NOT 32
    // replicated neuron-state records; state and currents live in the
    // exclusive one-slot paged RAM and owner backing images.
    reg [3:0] global_spikes [0:31];
    integer i;
    integer k;
    reg bad_edges;
    reg signed [19:0] syn_sum;
    reg [3:0] contributing_edges;

    wire [5:0] global_neuron=({3'd0,expected_page} * 6'd6) +
                               {3'd0,local_neuron};
    wire signed [31:0] v_extended={{16{v_state[15]}},v_state};
    wire signed [31:0] three_scaled=v_extended*32'sd3;
    wire signed [31:0] leaked=
        three_scaled<0 ? -((-three_scaled) >>> 2) : (three_scaled >>> 2);

    always @* begin
        syn_sum=20'sd0;
        contributing_edges=4'd0;
        for(k=0;k<8;k=k+1) begin
            if(edge_configured && k < edge_count &&
               pre[k]<32 && post[k]==global_neuron &&
               delay[k]>=1 && delay[k]<=3 &&
               delay[k]<=expected_tick &&
               global_spikes[pre[k]][expected_tick-delay[k]]) begin
                syn_sum=syn_sum+
                    $signed({{4{weight[k][15]}},weight[k][15:0]});
                contributing_edges=contributing_edges+4'd1;
            end
        end
    end
    wire signed [33:0] exact_total =
          $signed({{2{leaked[31]}},leaked})
        + $signed({{18{bias[15]}},bias})
        + $signed({{2{external_current[31]}},external_current})
        + $signed({{14{syn_sum[19]}},syn_sum});
    wire signed [15:0] clipped =
        exact_total>34'sd32767 ? 16'sd32767 :
        exact_total< -34'sd32768 ? -16'sd32768 :
        exact_total[15:0];
    wire fire_now=(clipped>=threshold);
    wire signed [15:0] next_v=fire_now?reset_voltage:clipped;
    wire [3:0] next_spike_mask=old_spike_mask |
                             (fire_now ? (4'b0001<<expected_tick) : 4'b0000);
    wire valid_signed_word=(observed[31:16]=={16{observed[15]}});
    wire [5:0] base_word={local_neuron,3'b000}+
                         {local_neuron,1'b0}; // index x10 (0..50)

    assign compute_req=(state==S_ISSUE);
    assign compute_write=txn_write;
    assign compute_word=address;
    assign compute_wdata=txn_data;
    assign compute_wstrb=txn_write?4'hF:4'h0;
    assign compute_done=(state==S_DONE);
    assign compute_fault=(state==S_FAULT);

    always @* begin
        bad_edges=1'b0;
        for(integer m=0;m<8;m=m+1) begin
            if(m<edge_count) begin
                if(pre[m]>=32 || post[m]>=32 ||
                   delay[m]<1 || delay[m]>3 ||
                   weight[m][31:16]!={16{weight[m][15]}})
                    bad_edges=1'b1;
            end else begin
                if(pre[m]!=0 || post[m]!=0 || weight[m]!=0 || delay[m]!=0)
                    bad_edges=1'b1;
            end
        end
    end

    always @(posedge clk) begin
        if(!resetn) begin
            state<=S_IDLE;stage<=K_MAGIC;
            address<=0;txn_write<=0;txn_data<=0;observed<=0;
            wait_cycles<=0;page_magic<=0;page_id<=0;page_count<=0;
            page_tick<=0;edge_configured<=0;edge_count<=0;
            edge_word_idx<=0;expected_page<=0;expected_tick<=0;
            local_neuron<=0;field_idx<=0;
            v_state<=0;bias<=0;threshold<=0;reset_voltage<=0;
            external_current<=0;old_spike_mask<=0;
            result_v<=0;result_fire<=0;result_syn<=0;
            completed_neurons<=0;completed_pages<=0;
            computed_synaptic_events<=0;
            for(i=0;i<8;i=i+1) begin
                pre[i]<=0;post[i]<=0;weight[i]<=0;delay[i]<=0;
            end
            for(i=0;i<32;i=i+1)
                global_spikes[i]<=0;
        end else begin
            case(state)
                S_IDLE: if(dispatch_accept) begin
                    stage<=K_MAGIC;
                    address<=6'd60;
                    txn_write<=0;
                    state<=S_ISSUE;
                end
                S_ISSUE: begin
                    wait_cycles<=0;
                    state<=S_WAIT;
                end
                S_WAIT: begin
                    if(compute_ack) begin
                        if(!txn_write)
                            observed<=compute_rdata;
                        state<=S_HANDLE;
                    end else if(wait_cycles==5'd15)
                        state<=S_FAULT;
                    else
                        wait_cycles<=wait_cycles+5'd1;
                end
                S_HANDLE: begin
                    case(stage)
                        K_MAGIC: begin
                            page_magic<=observed;
                            stage<=K_ID;
                            address<=6'd61;
                            txn_write<=0;
                            state<=S_ISSUE;
                        end
                        K_ID: begin
                            page_id<=observed;
                            stage<=K_COUNT;
                            address<=6'd62;
                            txn_write<=0;
                            state<=S_ISSUE;
                        end
                        K_COUNT: begin
                            page_count<=observed;
                            stage<=K_TICK;
                            address<=6'd63;
                            txn_write<=0;
                            state<=S_ISSUE;
                        end
                        K_TICK: begin
                            page_tick<=observed;
                            if(page_magic==M6EG && !edge_configured &&
                               page_id==32'hffffffff &&
                               page_count==32'd5 && observed==0 &&
                               expected_page==0 && expected_tick==0) begin
                                edge_count<=page_count[3:0];
                                edge_word_idx<=0;
                                stage<=K_EDGE;
                                address<=0;
                                txn_write<=0;
                                state<=S_ISSUE;
                            end else if(page_magic==M6NF &&
                                        edge_configured &&
                                        page_id=={29'b0,expected_page} &&
                                        observed=={29'b0,expected_tick} &&
                                        page_count==
                                          (expected_page==3'd5?
                                           32'd2:32'd6) &&
                                        expected_tick<4) begin
                                local_neuron<=0;
                                field_idx<=0;
                                stage<=K_FIELD;
                                address<=0;
                                txn_write<=0;
                                state<=S_ISSUE;
                            end else state<=S_FAULT;
                        end
                        K_EDGE: begin
                            case(edge_word_idx[1:0])
                                2'd0:pre[edge_word_idx[5:2]]<=observed;
                                2'd1:post[edge_word_idx[5:2]]<=observed;
                                2'd2:weight[edge_word_idx[5:2]]<=observed;
                                2'd3:delay[edge_word_idx[5:2]]<=observed;
                            endcase
                            if(edge_word_idx==6'd31) begin
                                stage<=K_EDGE_VALIDATE;
                                state<=S_HANDLE;
                            end else begin
                                edge_word_idx<=edge_word_idx+6'd1;
                                address<=edge_word_idx+6'd1;
                                txn_write<=0;
                                state<=S_ISSUE;
                            end
                        end
                        K_EDGE_VALIDATE: begin
                            if(bad_edges)
                                state<=S_FAULT;
                            else begin
                                edge_configured<=1;
                                state<=S_DONE;
                            end
                        end
                        K_FIELD: begin
                            case(field_idx)
                                3'd0: if(!valid_signed_word)
                                    state<=S_FAULT;
                                else v_state<=observed[15:0];
                                3'd1: if(!valid_signed_word)
                                    state<=S_FAULT;
                                else bias<=observed[15:0];
                                3'd2: if(!valid_signed_word ||
                                          $signed(observed)<=0)
                                    state<=S_FAULT;
                                else threshold<=observed[15:0];
                                3'd3: if(!valid_signed_word ||
                                          $signed(observed)>=
                                          $signed({{16{threshold[15]}},threshold}))
                                    state<=S_FAULT;
                                else reset_voltage<=observed[15:0];
                                3'd4: external_current<=observed;
                                3'd5: begin
                                    if(observed[31:4]!=0 ||
                                       observed[3:0]!=global_spikes[global_neuron])
                                        state<=S_FAULT;
                                    else begin
                                        old_spike_mask<=observed[3:0];
                                        result_v<=next_v;
                                        result_fire<=fire_now;
                                        result_syn<={{12{syn_sum[19]}},syn_sum};
                                        address<=base_word;
                                        txn_write<=1;
                                        txn_data<={{16{next_v[15]}},next_v};
                                        stage<=K_WRITE_MEM;
                                        state<=S_ISSUE;
                                    end
                                end
                                default:state<=S_FAULT;
                            endcase
                            if(field_idx<5 && state!=S_FAULT) begin
                                field_idx<=field_idx+3'd1;
                                if(field_idx==3'd3)
                                    address<=base_word+6'd4+{3'd0,expected_tick};
                                else if(field_idx==3'd4)
                                    address<=base_word+6'd8;
                                else
                                    address<=base_word+{3'd0,field_idx}+6'd1;
                                txn_write<=0;
                                state<=S_ISSUE;
                            end
                        end
                        K_WRITE_MEM: begin
                            address<=base_word+6'd8;
                            txn_data<={28'd0,
                                (old_spike_mask |
                                  (result_fire?
                                      (4'b0001 << expected_tick):4'b0000))};
                            txn_write<=1;
                            stage<=K_WRITE_SPIKE;
                            state<=S_ISSUE;
                        end
                        K_WRITE_SPIKE: begin
                            address<=base_word+6'd9;
                            txn_data<=result_syn;
                            txn_write<=1;
                            stage<=K_WRITE_SYN;
                            state<=S_ISSUE;
                        end
                        K_WRITE_SYN: begin
                            global_spikes[global_neuron][expected_tick]<=result_fire;
                            completed_neurons<=completed_neurons+32'd1;
                            computed_synaptic_events<=computed_synaptic_events+
                                                       {28'd0,contributing_edges};
                            if(local_neuron+3'd1<page_count[2:0]) begin
                                local_neuron<=local_neuron+3'd1;
                                field_idx<=0;
                                address<=base_word+6'd10;
                                txn_write<=0;
                                stage<=K_FIELD;
                                state<=S_ISSUE;
                            end else begin
                                completed_pages<=completed_pages+32'd1;
                                if(expected_page==3'd5) begin
                                    expected_page<=0;
                                    expected_tick<=expected_tick+3'd1;
                                end else expected_page<=expected_page+3'd1;
                                state<=S_DONE;
                            end
                        end
                        default:state<=S_FAULT;
                    endcase
                end
                S_DONE: state<=S_IDLE;
                S_FAULT: state<=S_FAULT;
                default: state<=S_FAULT;
            endcase
        end
    end
endmodule
