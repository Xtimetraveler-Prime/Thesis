from pathlib import Path

p = Path('Neuromorphic Digital Twin/rtl/core_v1/m12_3_multitick_capture_controller_v1.sv')
text = p.read_text(encoding='utf-8')
duplicate = """                        active_case_id <= trace_read_addr[7:0];
                        tick_index <= 8'd0;
                        capture_done <= 1'b0;
                        capture_fault <= 1'b0;
                        capture_fault_code <= CAPTURE_FAULT_NONE;
                        load_index <= 13'd0;
                        tick_index <= 8'd0;
                        watchdog <= 24'd0;
"""
clean = """                        active_case_id <= trace_read_addr[7:0];
                        tick_index <= 8'd0;
                        capture_done <= 1'b0;
                        capture_fault <= 1'b0;
                        capture_fault_code <= CAPTURE_FAULT_NONE;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
"""
if duplicate not in text:
    raise SystemExit('duplicate restart anchor missing')
text = text.replace(duplicate, clean, 1)

fail_old = """                S_FAIL: begin
                    if (capture_start_pulse) begin
                        active_case_id <= trace_read_addr[7:0];
                        capture_done <= 1'b0;
                        capture_fault <= 1'b0;
                        capture_fault_code <= CAPTURE_FAULT_NONE;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
"""
fail_new = """                S_FAIL: begin
                    if (capture_start_pulse) begin
                        active_case_id <= trace_read_addr[7:0];
                        tick_index <= 8'd0;
                        capture_done <= 1'b0;
                        capture_fault <= 1'b0;
                        capture_fault_code <= CAPTURE_FAULT_NONE;
                        load_index <= 13'd0;
                        watchdog <= 24'd0;
"""
if fail_old not in text:
    raise SystemExit('S_FAIL restart anchor missing')
text = text.replace(fail_old, fail_new, 1)
p.write_text(text, encoding='utf-8')
