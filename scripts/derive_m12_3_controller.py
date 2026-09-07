from pathlib import Path

root = Path('Neuromorphic Digital Twin/rtl/core_v1')
src = root / 'm12_2_single_tick_capture_controller_v1.sv'
dst = root / 'm12_3_multitick_capture_controller_v1.sv'
text = src.read_text(encoding='utf-8')

text = text.replace('M12.2 case-selectable single-tick physical capture controller.', 'M12.3 case-selectable multi-tick/recurrent physical capture controller.')
text = text.replace('generated_m12_2_single_tick_cases.svh', 'generated_m12_3_multitick_cases.svh')
text = text.replace('m12_2_single_tick_capture_controller_v1', 'm12_3_multitick_capture_controller_v1')
text = text.replace('M12.2 must test arbitrary', 'M12.3 must test arbitrary')
text = text.replace('M12.2 initial state', 'M12.3 initial state')
text = text.replace('M12.2_*', 'M12_3_*')
text = text.replace('M12_2_', 'M12_3_')

old = '''    logic [12:0] load_index;
    logic [23:0] watchdog;

    logic [8:0]  case_neuron_count;
'''
new = '''    logic [12:0] load_index;
    logic [7:0]  tick_index;
    logic [23:0] watchdog;

    logic [8:0]  case_neuron_count;
'''
assert old in text
text = text.replace(old, new, 1)

old = '''    logic [12:0] case_route_count;
    logic [12:0] case_external_count;

    always_comb begin
        case_neuron_count   = M12_3_NEURON_COUNTS[active_case_id];
        case_axon_count     = M12_3_AXON_COUNTS[active_case_id];
        case_synapse_count  = M12_3_SYNAPSE_COUNTS[active_case_id];
        case_format_count   = M12_3_FORMAT_COUNTS[active_case_id];
        case_route_count    = M12_3_ROUTE_COUNTS[active_case_id];
        case_external_count = M12_3_EXTERNAL_COUNTS[active_case_id];
    end
'''
new = '''    logic [12:0] case_route_count;
    logic [7:0]  case_tick_count;
    logic [12:0] case_external_count;

    always_comb begin
        case_neuron_count   = M12_3_NEURON_COUNTS[active_case_id];
        case_axon_count     = M12_3_AXON_COUNTS[active_case_id];
        case_synapse_count  = M12_3_SYNAPSE_COUNTS[active_case_id];
        case_format_count   = M12_3_FORMAT_COUNTS[active_case_id];
        case_route_count    = M12_3_ROUTE_COUNTS[active_case_id];
        case_tick_count     = M12_3_TICK_COUNTS[active_case_id];
        case_external_count = M12_3_EXTERNAL_COUNTS[
            (active_case_id * M12_3_MAX_TICKS) + tick_index
        ];
    end
'''
assert old in text
text = text.replace(old, new, 1)

old = '    assign step_ready = (state == S_READY_TICK);\n'
new = '    assign step_ready = (state == S_READY_TICK) || ((state == S_CAPTURE_HOLD) && !capture_done);\n'
assert old in text
text = text.replace(old, new, 1)

old = '''                external_wdata = M12_3_EXTERNAL_EVENTS[
                    (active_case_id * M12_3_MAX_EXTERNAL_EVENTS) + load_index
                ];
'''
new = '''                external_wdata = M12_3_EXTERNAL_EVENTS[
                    (((active_case_id * M12_3_MAX_TICKS) + tick_index) *
                     M12_3_MAX_EXTERNAL_EVENTS) + load_index
                ];
'''
assert old in text
text = text.replace(old, new, 1)

# Initial state load must not overwrite the trace-visible external memory before
# the host actually requests tick 0. The step pulse owns external load + launch.
old = '''                S_LOAD_STATE: begin
                    if (load_index + 13'd1 >= case_neuron_count) begin
                        load_index <= 13'd0;
                        if (case_external_count == 0)
                            state <= S_READY_TICK;
                        else
                            state <= S_LOAD_EXTERNAL;
                    end else load_index <= load_index + 13'd1;
                end
                S_LOAD_EXTERNAL: begin
                    if (load_index + 13'd1 >= case_external_count) begin
                        load_index <= 13'd0;
                        state <= S_READY_TICK;
                    end else load_index <= load_index + 13'd1;
                end

                S_READY_TICK: begin
                    if (capture_step_pulse) begin
                        capture_done <= 1'b0;
                        watchdog <= 24'd0;
                        state <= S_TICK_PULSE;
                    end
                end
'''
new = '''                S_LOAD_STATE: begin
                    if (load_index + 13'd1 >= case_neuron_count) begin
                        load_index <= 13'd0;
                        state <= S_READY_TICK;
                    end else load_index <= load_index + 13'd1;
                end
                S_LOAD_EXTERNAL: begin
                    if (load_index + 13'd1 >= case_external_count) begin
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        state <= S_TICK_PULSE;
                    end else load_index <= load_index + 13'd1;
                end

                S_READY_TICK: begin
                    if (capture_step_pulse) begin
                        capture_done <= 1'b0;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        if (case_external_count == 0)
                            state <= S_TICK_PULSE;
                        else
                            state <= S_LOAD_EXTERNAL;
                    end
                end
'''
assert old in text
text = text.replace(old, new, 1)

old = '''                        if (core_tick != 32'd1) begin
                            capture_fault <= 1'b1;
                            capture_fault_code <= CAPTURE_FAULT_TICK_COUNT;
                            state <= S_FAIL;
                        end else begin
                            capture_done <= 1'b1;
                            state <= S_CAPTURE_HOLD;
                        end
'''
new = '''                        if (core_tick != ({24'd0, tick_index} + 32'd1)) begin
                            capture_fault <= 1'b1;
                            capture_fault_code <= CAPTURE_FAULT_TICK_COUNT;
                            state <= S_FAIL;
                        end else begin
                            if ((tick_index + 8'd1) >= case_tick_count)
                                capture_done <= 1'b1;
                            state <= S_CAPTURE_HOLD;
                        end
'''
assert old in text
text = text.replace(old, new, 1)

old = '''                S_CAPTURE_HOLD: begin
                    // Hold the immutable post-commit trace until the host has
                    // finished all indexed reads. A new start may then select
                    // another case and will run a fresh architectural reset.
                    if (capture_start_pulse) begin
                        active_case_id <= trace_read_addr[7:0];
                        capture_done <= 1'b0;
                        capture_fault <= 1'b0;
                        capture_fault_code <= CAPTURE_FAULT_NONE;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
                            capture_fault <= 1'b1;
                            capture_fault_code <= CAPTURE_FAULT_CASE_SELECT;
                            state <= S_FAIL;
                        end else begin
                            state <= S_LOAD_CONFIG;
                        end
                    end
                end
'''
new = '''                S_CAPTURE_HOLD: begin
                    // Preserve this committed tick until the host finishes all
                    // indexed reads. The next step edge owns both next-tick
                    // external-event loading and tick launch, so no future input
                    // can overwrite the current tick's trace window early.
                    if (capture_step_pulse && !capture_done) begin
                        tick_index <= tick_index + 8'd1;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        if (M12_3_EXTERNAL_COUNTS[
                                (active_case_id * M12_3_MAX_TICKS) + tick_index + 8'd1
                            ] == 0)
                            state <= S_TICK_PULSE;
                        else
                            state <= S_LOAD_EXTERNAL;
                    end else if (capture_start_pulse) begin
                        active_case_id <= trace_read_addr[7:0];
                        tick_index <= 8'd0;
                        capture_done <= 1'b0;
                        capture_fault <= 1'b0;
                        capture_fault_code <= CAPTURE_FAULT_NONE;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
                            capture_fault <= 1'b1;
                            capture_fault_code <= CAPTURE_FAULT_CASE_SELECT;
                            state <= S_FAIL;
                        end else begin
                            state <= S_LOAD_CONFIG;
                        end
                    end
                end
'''
assert old in text
text = text.replace(old, new, 1)

# Initialize/reset tick index on every fresh case start and failure restart.
text = text.replace(
    '''            load_index <= 13'd0;
            watchdog <= 24'd0;
''',
    '''            load_index <= 13'd0;
            tick_index <= 8'd0;
            watchdog <= 24'd0;
''',
    1,
)
text = text.replace(
    '''                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
''',
    '''                        load_index <= 13'd0;
                        tick_index <= 8'd0;
                        watchdog <= 24'd0;
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
''',
    1,
)
# S_FAIL has the same restart pattern; patch the remaining occurrence.
needle = '''                        load_index <= 13'd0;
                        watchdog <= 24'd0;
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
'''
if needle in text:
    text = text.replace(
        needle,
        '''                        load_index <= 13'd0;
                        tick_index <= 8'd0;
                        watchdog <= 24'd0;
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
''',
        1,
    )

# Replace single-tick prose that is no longer accurate.
text = text.replace(
    'Python independently generates the complete per-case FPGA load image and\n// golden result.',
    'Python independently generates the complete per-case FPGA load image,\n// per-tick external schedule, and host-side golden timeline.',
)
text = text.replace(
    '// Hold the immutable post-commit trace until the host has\n',
    '// Hold the immutable post-commit trace until the host has\n',
)

dst.write_text(text, encoding='utf-8')
print(dst)
