// M06 EXISTING G4: bounded synthesizable candidate HLS trace/metrics staging.
// ALL output stays PRIVATE until external fault gate's commit_valid + exact
// expected trace count + one metrics word. Poison discards without publication.
// Does not implement physical DDR rollback, AXI fault routing, host ownership,
// or crash-atomic commits; no timing/BRAM utilization is claimed.
// Default depth = finite accepted M05 integrated maximum 1024 neurons x8 ticks;
// 8192 x 192-bit FF/BRAM is a candidate requiring post-synthesis measurement.
// Recovered execution requires system reset + externally restored clean image.
module m06_g4_output_quarantine #(
    parameter integer MAX_TRACE = 8192
) (
    input  wire         aclk,
    input  wire         aresetn,
    input  wire         epoch_begin,
    input  wire [31:0]  expected_trace_count,
    input  wire         commit_valid,
    input  wire         poisoned,
    input  wire [191:0] s_trace_tdata,
    input  wire         s_trace_tvalid,
    output wire         s_trace_tready,
    input  wire [255:0] s_metrics_tdata,
    input  wire         s_metrics_tvalid,
    output wire         s_metrics_tready,
    output wire [191:0] m_trace_tdata,
    output wire         m_trace_tvalid,
    input  wire         m_trace_tready,
    output wire [255:0] m_metrics_tdata,
    output wire         m_metrics_tvalid,
    input  wire         m_metrics_tready,
    output reg          quarantined,
    output wire         published_done,
    output reg  [31:0]  buffered_trace_count,
    output reg  [31:0]  published_trace_count,
    output reg          protocol_fault
);
    localparam [2:0] IDLE=0,CAPTURE=1,DRAIN=2,METRICS=3,DONE=4,BLOCK=5;
    reg [2:0] state;
    reg [191:0] trace_mem [0:MAX_TRACE-1];
    reg [255:0] metrics_word;
    reg metrics_seen;
    reg [31:0] target;
    wire valid_target = (expected_trace_count<=MAX_TRACE);
    assign s_trace_tready = aresetn && (state==CAPTURE) &&
                            !poisoned && !commit_valid &&
                            (buffered_trace_count<MAX_TRACE);
    assign s_metrics_tready = aresetn && (state==CAPTURE) &&
                              !poisoned && !commit_valid && !metrics_seen;
    assign m_trace_tvalid = aresetn && state==DRAIN && !poisoned &&
                            published_trace_count<buffered_trace_count;
    assign m_trace_tdata = trace_mem[published_trace_count];
    assign m_metrics_tvalid = aresetn && state==METRICS && !poisoned;
    assign m_metrics_tdata = metrics_word;
    assign published_done = aresetn && state==DONE && !poisoned &&
                            !quarantined && !protocol_fault;

    always @(posedge aclk) begin
        if(!aresetn) begin
            state<=IDLE;
            quarantined<=0;
            protocol_fault<=0;
            target<=0;
            buffered_trace_count<=0;
            published_trace_count<=0;
            metrics_word<=0;
            metrics_seen<=0;
        end else if(poisoned) begin
            // Fault persists; no consumer may read uncommitted raw streams.
            state<=BLOCK;
            quarantined<=1;
        end else begin
            case(state)
                IDLE: begin
                    if(s_trace_tvalid || s_metrics_tvalid) begin
                        state<=BLOCK;
                        protocol_fault<=1;
                        quarantined<=1;
                    end else if(epoch_begin) begin
                        if(!valid_target || commit_valid) begin
                            state<=BLOCK;
                            protocol_fault<=1;
                            quarantined<=1;
                        end else begin
                            state<=CAPTURE;
                            target<=expected_trace_count;
                            buffered_trace_count<=0;
                            published_trace_count<=0;
                            metrics_seen<=0;
                        end
                    end
                end
                CAPTURE: begin
                    if(epoch_begin) begin
                        state<=BLOCK;
                        protocol_fault<=1;
                        quarantined<=1;
                    end else if(commit_valid) begin
                        // HLS ap_done / external gate must already have
                        // quiesced ALL stream input handshakes.
                        if(s_trace_tvalid || s_metrics_tvalid ||
                           buffered_trace_count!=target || !metrics_seen) begin
                            state<=BLOCK;
                            protocol_fault<=1;
                            quarantined<=1;
                        end else if(buffered_trace_count==0) begin
                            state<=METRICS;
                        end else begin
                            state<=DRAIN;
                        end
                    end else begin
                        if(s_trace_tvalid && s_trace_tready) begin
                            trace_mem[buffered_trace_count]<=s_trace_tdata;
                            buffered_trace_count<=buffered_trace_count+1;
                        end
                        if(s_metrics_tvalid && s_metrics_tready) begin
                            metrics_word<=s_metrics_tdata;
                            metrics_seen<=1;
                        end
                        // Any additional metrics beat after one is invalid.
                        if(s_metrics_tvalid && metrics_seen) begin
                            state<=BLOCK;
                            protocol_fault<=1;
                            quarantined<=1;
                        end
                    end
                end
                DRAIN: begin
                    if(epoch_begin || s_trace_tvalid || s_metrics_tvalid) begin
                        state<=BLOCK;
                        protocol_fault<=1;
                        quarantined<=1;
                    end else if(m_trace_tvalid && m_trace_tready) begin
                        published_trace_count<=published_trace_count+1;
                        if(published_trace_count+1>=buffered_trace_count)
                            state<=METRICS;
                    end
                end
                METRICS: begin
                    if(epoch_begin || s_trace_tvalid || s_metrics_tvalid) begin
                        state<=BLOCK;
                        protocol_fault<=1;
                        quarantined<=1;
                    end else if(m_metrics_tvalid && m_metrics_tready)
                        state<=DONE;
                end
                DONE: if(epoch_begin || s_trace_tvalid || s_metrics_tvalid) begin
                    // No silent reuse of a completed image; reset+external
                    // new canonical image required for next owner epoch.
                    state<=BLOCK;
                    protocol_fault<=1;
                    quarantined<=1;
                end
                BLOCK: begin
                    quarantined<=1;
                end
                default: begin
                    state<=BLOCK;
                    protocol_fault<=1;
                    quarantined<=1;
                end
            endcase
        end
    end
endmodule
