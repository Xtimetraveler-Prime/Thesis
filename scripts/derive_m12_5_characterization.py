from pathlib import Path

root = Path(__file__).resolve().parents[1]
rtl = root / "Neuromorphic Digital Twin" / "rtl" / "core_v1"
vivado = rtl / "vivado"

# Capture controller: preserve the frozen M12.4 corpus arrays and computational core,
# add only a passive cycle counter and one observation port.
text = (rtl / "m12_4_broad_capture_controller_v1.sv").read_text(encoding="utf-8")
text = text.replace("M12.4 case-selectable", "M12.5 characterization")
text = text.replace("module m12_4_broad_capture_controller_v1", "module m12_5_characterization_capture_controller_v1")
text = text.replace(
    "    output logic [12:0]  observed_external_event_count,\n",
    "    output logic [12:0]  observed_external_event_count,\n"
    "    output logic [31:0]  observed_last_tick_cycles,\n",
    1,
)
text = text.replace(
    "    logic [23:0] watchdog;\n",
    "    logic [23:0] watchdog;\n"
    "    logic [31:0] tick_cycle_counter;\n"
    "    logic        tick_cycle_active;\n",
    1,
)
anchor = "    m12_trace_read_bridge_v1 trace_bridge_i (\n"
counter = '''    // Passive M12.5 measurement only. This counter does not feed core control,
    // configuration, state, events, routing, or trace data. The measurement is
    // the number of ap_clk periods from the accepted architectural tick_start
    // edge through the edge on which the outer core's tick_done is observed.
    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            tick_cycle_counter       <= 32'd0;
            tick_cycle_active        <= 1'b0;
            observed_last_tick_cycles <= 32'd0;
        end else if (tick_start) begin
            tick_cycle_counter <= 32'd0;
            tick_cycle_active  <= 1'b1;
        end else if (tick_cycle_active) begin
            if (tick_done) begin
                observed_last_tick_cycles <= tick_cycle_counter + 32'd1;
                tick_cycle_active         <= 1'b0;
            end else begin
                tick_cycle_counter <= tick_cycle_counter + 32'd1;
            end
        end
    end

'''
if anchor not in text:
    raise SystemExit("M12.5 controller counter anchor not found")
text = text.replace(anchor, counter + anchor, 1)
text = text.replace("M12.4 uses the full byte", "M12.5 reuses the M12.4 full-byte")
(rtl / "m12_5_characterization_capture_controller_v1.sv").write_text(text, encoding="utf-8")

# Verilog module-reference wrapper.
bd = (rtl / "m12_4_broad_capture_controller_bd_v1.v").read_text(encoding="utf-8")
bd = bd.replace("M12.4", "M12.5")
bd = bd.replace("m12_4_broad_capture_controller_bd_v1", "m12_5_characterization_capture_controller_bd_v1")
bd = bd.replace("m12_4_broad_capture_controller_v1", "m12_5_characterization_capture_controller_v1")
bd = bd.replace(
    "    output wire [12:0]  observed_external_event_count,\n",
    "    output wire [12:0]  observed_external_event_count,\n"
    "    output wire [31:0]  observed_last_tick_cycles,\n",
    1,
)
bd = bd.replace(
    "        .observed_external_event_count(observed_external_event_count),\n",
    "        .observed_external_event_count(observed_external_event_count),\n"
    "        .observed_last_tick_cycles(observed_last_tick_cycles),\n",
    1,
)
(rtl / "m12_5_characterization_capture_controller_bd_v1.v").write_text(bd, encoding="utf-8")

# Vivado project: same physical design plus one passive VIO input.
proj = (vivado / "create_m12_4_project.tcl").read_text(encoding="utf-8")
proj = proj.replace("M12.4", "M12.5")
proj = proj.replace("m12_4", "m12_5")
proj = proj.replace("m12_4_broad_capture_controller_bd_v1", "m12_5_characterization_capture_controller_bd_v1")
proj = proj.replace("CONFIG.C_NUM_PROBE_IN {35}", "CONFIG.C_NUM_PROBE_IN {36}", 1)
probe_anchor = "    CONFIG.C_PROBE_IN34_WIDTH {16} \\\n"
if probe_anchor not in proj:
    raise SystemExit("M12.5 probe-width anchor not found")
proj = proj.replace(probe_anchor, probe_anchor + "    CONFIG.C_PROBE_IN35_WIDTH {32} \\\n", 1)
connect_anchor = "connect_named_pair observed_external_event_count      capture_0/observed_external_event_count vio_m12_5/probe_in19\n"
if connect_anchor not in proj:
    raise SystemExit("M12.5 VIO connection anchor not found")
proj = proj.replace(
    connect_anchor,
    connect_anchor + "connect_named_pair observed_last_tick_cycles        capture_0/observed_last_tick_cycles vio_m12_5/probe_in35\n",
    1,
)
(vivado / "create_m12_5_project.tcl").write_text(proj, encoding="utf-8")

# Hardware capture: retain full trace capture and additionally emit cycle TSV.
cap = (vivado / "capture_m12_4_broad.tcl").read_text(encoding="utf-8")
cap = cap.replace("M12.4", "M12.5")
cap = cap.replace(
    "if {$argc != 4} {\n    error \"usage: capture_m12_5_broad.tcl <bitstream> <ltx> <hardware_cases.tsv> <output_dir>\"\n}",
    "if {$argc != 5} {\n    error \"usage: capture_m12_5_characterization.tcl <bitstream> <ltx> <hardware_cases.tsv> <output_dir> <cycle_tsv>\"\n}",
    1,
)
cap = cap.replace(
    "set output_dir [file normalize [lindex $argv 3]]\nfile mkdir $output_dir\n",
    "set output_dir [file normalize [lindex $argv 3]]\n"
    "set cycle_tsv [file normalize [lindex $argv 4]]\n"
    "file mkdir $output_dir\n"
    "set cycle_fh [open $cycle_tsv w]\n"
    "puts $cycle_fh \"case_id\\tcase_name\\ttick\\tcycles\\texternal_events\\trecurrent_events\\trouted_events\"\n",
    1,
)
cap = cap.replace(
    "set p_external_count [find_one_probe $vio observed_external_event_count]\n",
    "set p_external_count [find_one_probe $vio observed_external_event_count]\n"
    "set p_tick_cycles [find_one_probe $vio observed_last_tick_cycles]\n",
    1,
)
count_anchor = "        set external_count [probe_uint $p_external_count]\n"
if count_anchor not in cap:
    raise SystemExit("M12.5 capture count anchor not found")
cap = cap.replace(
    count_anchor,
    count_anchor + "        set tick_cycles [probe_uint $p_tick_cycles]\n"
    "        if {$tick_cycles <= 0} {\n"
    "            close $fh\n"
    "            close $cycle_fh\n"
    "            error \"M12.5 invalid tick-cycle measurement: case=$case_id tick=$expected_tick cycles=$tick_cycles\"\n"
    "        }\n",
    1,
)
row_anchor = "        incr captured_ticks\n"
if row_anchor not in cap:
    raise SystemExit("M12.5 capture TSV anchor not found")
cap = cap.replace(
    row_anchor,
    "        puts $cycle_fh \"$case_id\\t$case_name\\t$expected_tick\\t$tick_cycles\\t$external_count\\t$consumed_count\\t$routed_count\"\n"
    + row_anchor,
    1,
)
cap = cap.replace(
    "puts \"M12.5 physical broad deterministic suite capture completed successfully: cases=$captured_cases ticks=$captured_ticks output=$output_dir\"\nclose_hw_manager",
    "puts \"M12.5 physical characterization capture completed successfully: cases=$captured_cases ticks=$captured_ticks cycles=$cycle_tsv output=$output_dir\"\n"
    "close $cycle_fh\n"
    "close_hw_manager",
    1,
)
(vivado / "capture_m12_5_characterization.tcl").write_text(cap, encoding="utf-8")

# Bitstream runner: M12.5 identity, same frozen M12.4 corpus generator/arrays.
run = (rtl / "run_m12_4_bitstream.sh").read_text(encoding="utf-8")
run = run.replace("M12.4", "M12.5")
run = run.replace("M12_4_JOBS", "M12_5_JOBS")
run = run.replace("build/m12_4", "build/m12_5")
run = run.replace("/m12_4\"", "/m12_5\"")
run = run.replace("m12_4_broad_capture_controller_v1.sv", "m12_5_characterization_capture_controller_v1.sv")
run = run.replace("m12_4_broad_capture_controller_bd_v1.v", "m12_5_characterization_capture_controller_bd_v1.v")
run = run.replace("create_m12_4_project.tcl", "create_m12_5_project.tcl")
run = run.replace("neuromorphic_twin_m12_4", "neuromorphic_twin_m12_5")
# The corpus itself remains the already validated M12.4 corpus.
run = run.replace("generate_m12_5_broad_corpus.py", "generate_m12_4_broad_corpus.py")
run = run.replace("generated_m12_5_broad_cases.svh", "generated_m12_4_broad_cases.svh")
run = run.replace("M12_5_EXPECTED", "M12_4_EXPECTED")
run = run.replace("M12.5 broad cases: 22", "M12.5 characterization cases: 22")
run = run.replace("M12.5 broad committed ticks: 166", "M12.5 characterization committed ticks: 166")
(rtl / "run_m12_5_bitstream.sh").write_text(run, encoding="utf-8")
