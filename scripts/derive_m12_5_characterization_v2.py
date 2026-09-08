from pathlib import Path

root = Path(__file__).resolve().parents[1]
rtl = root / "Neuromorphic Digital Twin" / "rtl" / "core_v1"
vivado = rtl / "vivado"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label} anchor: {needle}")


# 1) Passive characterization capture controller. Keep all M12_4_* corpus names
# intentionally: M12.5 characterizes the already-validated frozen M12.4 corpus.
text = (rtl / "m12_4_broad_capture_controller_v1.sv").read_text(encoding="utf-8")
text = text.replace("M12.4 case-selectable", "M12.5 characterization")
text = text.replace(
    "module m12_4_broad_capture_controller_v1",
    "module m12_5_characterization_capture_controller_v1",
    1,
)
require(text, "    output logic [12:0]  observed_external_event_count,\n", "cycle output")
text = text.replace(
    "    output logic [12:0]  observed_external_event_count,\n",
    "    output logic [12:0]  observed_external_event_count,\n"
    "    output logic [31:0]  observed_last_tick_cycles,\n",
    1,
)
require(text, "    logic [23:0] watchdog;\n", "counter declaration")
text = text.replace(
    "    logic [23:0] watchdog;\n",
    "    logic [23:0] watchdog;\n"
    "    logic [31:0] tick_cycle_counter;\n"
    "    logic        tick_cycle_active;\n",
    1,
)
bridge_anchor = "    m12_trace_read_bridge_v1 trace_bridge_i (\n"
require(text, bridge_anchor, "trace bridge")
counter = '''    // Passive M12.5 measurement only. These registers never feed the
    // computational core, load path, routing path, or trace-read bridge.
    // Count the ap_clk periods from the architectural tick_start acceptance
    // edge through the edge on which this shell observes outer-core tick_done.
    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            tick_cycle_counter        <= 32'd0;
            tick_cycle_active         <= 1'b0;
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
text = text.replace(bridge_anchor, counter + bridge_anchor, 1)
text = text.replace(
    "// M12.4 uses the full byte as a physical witness of the selected broad-regression case.",
    "// M12.5 reuses the M12.4 full-byte case witness unchanged.",
    1,
)
(rtl / "m12_5_characterization_capture_controller_v1.sv").write_text(text, encoding="utf-8")

# 2) Module-reference wrapper with one new passive 32-bit output.
bd = (rtl / "m12_4_broad_capture_controller_bd_v1.v").read_text(encoding="utf-8")
bd = bd.replace("M12.4", "M12.5")
bd = bd.replace(
    "m12_4_broad_capture_controller_bd_v1",
    "m12_5_characterization_capture_controller_bd_v1",
)
bd = bd.replace(
    "m12_4_broad_capture_controller_v1",
    "m12_5_characterization_capture_controller_v1",
)
require(bd, "    output wire [12:0]  observed_external_event_count,\n", "BD cycle output")
bd = bd.replace(
    "    output wire [12:0]  observed_external_event_count,\n",
    "    output wire [12:0]  observed_external_event_count,\n"
    "    output wire [31:0]  observed_last_tick_cycles,\n",
    1,
)
require(bd, "        .observed_external_event_count(observed_external_event_count),\n", "BD cycle connection")
bd = bd.replace(
    "        .observed_external_event_count(observed_external_event_count),\n",
    "        .observed_external_event_count(observed_external_event_count),\n"
    "        .observed_last_tick_cycles(observed_last_tick_cycles),\n",
    1,
)
(rtl / "m12_5_characterization_capture_controller_bd_v1.v").write_text(bd, encoding="utf-8")

# 3) Vivado project. Reuse the M12.4 physical shell and add one VIO input.
proj = (vivado / "create_m12_4_project.tcl").read_text(encoding="utf-8")
proj = proj.replace("M12.4", "M12.5")
proj = proj.replace("m12_4", "m12_5")
proj = proj.replace(
    "m12_5_broad_capture_controller_bd_v1",
    "m12_5_characterization_capture_controller_bd_v1",
)
require(proj, "CONFIG.C_NUM_PROBE_IN {35}", "VIO input count")
proj = proj.replace("CONFIG.C_NUM_PROBE_IN {35}", "CONFIG.C_NUM_PROBE_IN {36}", 1)
probe_anchor = "    CONFIG.C_PROBE_IN34_WIDTH {16} \\\n"
require(proj, probe_anchor, "VIO probe 34")
proj = proj.replace(
    probe_anchor,
    probe_anchor + "    CONFIG.C_PROBE_IN35_WIDTH {32} \\\n",
    1,
)
connect_anchor = (
    "connect_named_pair observed_external_event_count      "
    "capture_0/observed_external_event_count vio_m12_5/probe_in19\n"
)
require(proj, connect_anchor, "VIO cycle connection")
proj = proj.replace(
    connect_anchor,
    connect_anchor
    + "connect_named_pair observed_last_tick_cycles        "
      "capture_0/observed_last_tick_cycles vio_m12_5/probe_in35\n",
    1,
)
(vivado / "create_m12_5_project.tcl").write_text(proj, encoding="utf-8")

# 4) Hardware capture: preserve full architectural trace and add per-tick cycle TSV.
cap = (vivado / "capture_m12_4_broad.tcl").read_text(encoding="utf-8")
cap = cap.replace("M12.4", "M12.5")
cap = cap.replace("capture_m12_4_broad.tcl", "capture_m12_5_characterization.tcl")
old_usage = (
    'if {$argc != 4} {\n'
    '    error "usage: capture_m12_5_characterization.tcl <bitstream> <ltx> '
    '<hardware_cases.tsv> <output_dir>"\n'
    '}\n'
)
require(cap, old_usage, "capture usage")
cap = cap.replace(
    old_usage,
    'if {$argc != 5} {\n'
    '    error "usage: capture_m12_5_characterization.tcl <bitstream> <ltx> '
    '<hardware_cases.tsv> <output_dir> <cycle_tsv>"\n'
    '}\n',
    1,
)
output_anchor = "set output_dir [file normalize [lindex $argv 3]]\nfile mkdir $output_dir\n"
require(cap, output_anchor, "capture output")
cap = cap.replace(
    output_anchor,
    "set output_dir [file normalize [lindex $argv 3]]\n"
    "set cycle_tsv [file normalize [lindex $argv 4]]\n"
    "file mkdir $output_dir\n"
    "file mkdir [file dirname $cycle_tsv]\n"
    "set cycle_fh [open $cycle_tsv w]\n"
    "puts $cycle_fh \"case_id\\tcase_name\\ttick\\tcycles\\texternal_events\\trecurrent_events\\trouted_events\"\n",
    1,
)
probe_lookup = "set p_external_count [find_one_probe $vio observed_external_event_count]\n"
require(cap, probe_lookup, "cycle probe lookup")
cap = cap.replace(
    probe_lookup,
    probe_lookup + "set p_tick_cycles [find_one_probe $vio observed_last_tick_cycles]\n",
    1,
)
count_anchor = "        set external_count [probe_uint $p_external_count]\n"
require(cap, count_anchor, "cycle sample")
cap = cap.replace(
    count_anchor,
    count_anchor
    + "        set tick_cycles [probe_uint $p_tick_cycles]\n"
      "        if {$tick_cycles <= 0} {\n"
      "            close $fh\n"
      "            close $cycle_fh\n"
      "            error \"M12.5 invalid tick-cycle measurement: case=$case_id tick=$expected_tick cycles=$tick_cycles\"\n"
      "        }\n",
    1,
)
row_anchor = "        incr captured_ticks\n"
require(cap, row_anchor, "cycle TSV row")
cap = cap.replace(
    row_anchor,
    "        puts $cycle_fh \"$case_id\\t$case_name\\t$expected_tick\\t$tick_cycles\\t$external_count\\t$consumed_count\\t$routed_count\"\n"
    + row_anchor,
    1,
)
final_anchor = (
    'puts "M12.5 physical broad deterministic suite capture completed successfully: '
    'cases=$captured_cases ticks=$captured_ticks output=$output_dir"\n'
    'close_hw_manager'
)
require(cap, final_anchor, "capture final marker")
cap = cap.replace(
    final_anchor,
    'puts "M12.5 physical characterization capture completed successfully: '
    'cases=$captured_cases ticks=$captured_ticks cycles=$cycle_tsv output=$output_dir"\n'
    'close $cycle_fh\n'
    'close_hw_manager',
    1,
)
(vivado / "capture_m12_5_characterization.tcl").write_text(cap, encoding="utf-8")

# 5) Routed build script. Change only characterization image identities; retain the
# frozen M12.4 corpus generator and generated include names intentionally.
run = (rtl / "run_m12_4_bitstream.sh").read_text(encoding="utf-8")
run = run.replace("M12.4", "M12.5")
run = run.replace("M12_4_JOBS", "M12_5_JOBS")
run = run.replace("LOCAL_BUILD_DIR=\"$SCRIPT_DIR/build/m12_4\"", "LOCAL_BUILD_DIR=\"$SCRIPT_DIR/build/m12_5\"")
run = run.replace("STAGE_ROOT=\"/tmp/neuromorphic_twin_rtl_${UID}/m12_4\"", "STAGE_ROOT=\"/tmp/neuromorphic_twin_rtl_${UID}/m12_5\"")
run = run.replace("m12_4_broad_capture_controller_v1.sv", "m12_5_characterization_capture_controller_v1.sv")
run = run.replace("m12_4_broad_capture_controller_bd_v1.v", "m12_5_characterization_capture_controller_bd_v1.v")
run = run.replace("create_m12_4_project.tcl", "create_m12_5_project.tcl")
run = run.replace("neuromorphic_twin_m12_4", "neuromorphic_twin_m12_5")
# Undo M12.5 substitutions that would imply a new corpus; workload authority remains M12.4.
run = run.replace("generate_m12_5_broad_corpus.py", "generate_m12_4_broad_corpus.py")
run = run.replace("generated_m12_5_broad_cases.svh", "generated_m12_4_broad_cases.svh")
run = run.replace("M12_5_EXPECTED", "M12_4_EXPECTED")
run = run.replace("M12.5 broad cases: 22", "M12.5 characterization cases: 22")
run = run.replace("M12.5 broad committed ticks: 166", "M12.5 characterization committed ticks: 166")
(rtl / "run_m12_5_bitstream.sh").write_text(run, encoding="utf-8")

print("Derived M12.5 passive characterization hardware sources.")
