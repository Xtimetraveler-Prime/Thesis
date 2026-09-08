from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "Neuromorphic Digital Twin" / "rtl" / "core_v1"


def common(text: str) -> str:
    replacements = (
        ("m12_3_multitick_capture_controller_bd_v1", "m12_4_broad_capture_controller_bd_v1"),
        ("m12_3_multitick_capture_controller_v1", "m12_4_broad_capture_controller_v1"),
        ("generated_m12_3_multitick_cases.svh", "generated_m12_4_broad_cases.svh"),
        ("generate_m12_3_multitick_corpus.py", "generate_m12_4_broad_corpus.py"),
        ("capture_m12_3_multitick.tcl", "capture_m12_4_broad.tcl"),
        ("create_m12_3_project.tcl", "create_m12_4_project.tcl"),
        ("M12.3", "M12.4"),
        ("M12_3", "M12_4"),
        ("m12_3", "m12_4"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


controller = common((RTL / "m12_3_multitick_capture_controller_v1.sv").read_text())
controller = controller.replace(
    "    logic [12:0] case_external_count;\n",
    "    logic [12:0] case_external_count;\n"
    "    logic [31:0] case_config_offset;\n"
    "    logic [31:0] case_state_offset;\n"
    "    logic [31:0] case_format_offset;\n"
    "    logic [31:0] case_synapse_offset;\n"
    "    logic [31:0] case_weight_row_offset;\n"
    "    logic [31:0] case_route_row_offset;\n"
    "    logic [31:0] case_route_target_offset;\n"
    "    logic [31:0] case_tick_base;\n"
    "    logic [31:0] case_tick_flat_index;\n"
    "    logic [31:0] case_external_offset;\n",
)
old_counts = """    always_comb begin
        case_neuron_count   = M12_4_NEURON_COUNTS[active_case_id];
        case_axon_count     = M12_4_AXON_COUNTS[active_case_id];
        case_synapse_count  = M12_4_SYNAPSE_COUNTS[active_case_id];
        case_format_count   = M12_4_FORMAT_COUNTS[active_case_id];
        case_route_count    = M12_4_ROUTE_COUNTS[active_case_id];
        case_tick_count     = M12_4_TICK_COUNTS[active_case_id];
        case_external_count = M12_4_EXTERNAL_COUNTS[
            (active_case_id * M12_4_MAX_TICKS) + tick_index
        ];
    end
"""
new_counts = """    always_comb begin
        case_neuron_count       = M12_4_NEURON_COUNTS[active_case_id];
        case_axon_count         = M12_4_AXON_COUNTS[active_case_id];
        case_synapse_count      = M12_4_SYNAPSE_COUNTS[active_case_id];
        case_format_count       = M12_4_FORMAT_COUNTS[active_case_id];
        case_route_count        = M12_4_ROUTE_COUNTS[active_case_id];
        case_tick_count         = M12_4_TICK_COUNTS[active_case_id];
        case_config_offset      = M12_4_CONFIG_OFFSETS[active_case_id];
        case_state_offset       = M12_4_STATE_OFFSETS[active_case_id];
        case_format_offset      = M12_4_FORMAT_OFFSETS[active_case_id];
        case_synapse_offset     = M12_4_SYNAPSE_OFFSETS[active_case_id];
        case_weight_row_offset  = M12_4_WEIGHT_ROW_OFFSETS[active_case_id];
        case_route_row_offset   = M12_4_ROUTE_ROW_OFFSETS[active_case_id];
        case_route_target_offset = M12_4_ROUTE_TARGET_OFFSETS[active_case_id];
        case_tick_base          = M12_4_CASE_TICK_BASES[active_case_id];
        case_tick_flat_index    = case_tick_base + tick_index;
        case_external_count     = M12_4_EXTERNAL_COUNTS[case_tick_flat_index];
        case_external_offset    = M12_4_EXTERNAL_TICK_OFFSETS[case_tick_flat_index];
    end
"""
if old_counts not in controller:
    raise SystemExit("controller count/index block anchor not found")
controller = controller.replace(old_counts, new_counts)

index_replacements = (
    ("(active_case_id * M12_4_MAX_NEURONS) + load_index", "case_config_offset + load_index"),
    ("(active_case_id * M12_4_MAX_FORMATS) + load_index", "case_format_offset + load_index"),
    ("(active_case_id * M12_4_MAX_SYNAPSES) + load_index", "case_synapse_offset + load_index"),
    ("(active_case_id * (M12_4_MAX_AXONS + 1)) + load_index", "case_weight_row_offset + load_index"),
    ("(active_case_id * (M12_4_MAX_NEURONS + 1)) + load_index", "case_route_row_offset + load_index"),
    ("(active_case_id * M12_4_MAX_ROUTES) + load_index", "case_route_target_offset + load_index"),
)
for old, new in index_replacements:
    if old not in controller:
        raise SystemExit(f"controller index anchor not found: {old}")
    controller = controller.replace(old, new)

# The state image uses the state offset, not the configuration offset.
state_old = "M12_4_INITIAL_STATE_WORDS[\n                    case_config_offset + load_index\n                ]"
state_new = "M12_4_INITIAL_STATE_WORDS[\n                    case_state_offset + load_index\n                ]"
if state_old not in controller:
    raise SystemExit("controller state offset anchor not found")
controller = controller.replace(state_old, state_new)

external_old = """M12_4_EXTERNAL_EVENTS[
                    (((active_case_id * M12_4_MAX_TICKS) + tick_index) *
                     M12_4_MAX_EXTERNAL_EVENTS) + load_index
                ]"""
external_new = """M12_4_EXTERNAL_EVENTS[
                    case_external_offset + load_index
                ]"""
if external_old not in controller:
    raise SystemExit("controller external packed-index anchor not found")
controller = controller.replace(external_old, external_new)

next_old = """M12_4_EXTERNAL_COUNTS[
                                (active_case_id * M12_4_MAX_TICKS) + tick_index + 8'd1
                            ]"""
next_new = """M12_4_EXTERNAL_COUNTS[
                                M12_4_CASE_TICK_BASES[active_case_id] + tick_index + 8'd1
                            ]"""
if next_old not in controller:
    raise SystemExit("controller next-tick external anchor not found")
controller = controller.replace(next_old, next_new)

phase_old = "assign capture_phase = {active_case_id[3:0], state};"
if phase_old not in controller:
    raise SystemExit("capture-phase anchor not found")
controller = controller.replace(
    phase_old,
    "assign capture_phase = active_case_id; // full 8-bit case witness for M12.4 cases 0..21",
)
controller = controller.replace(
    "// High nibble is a physical witness of the selected directed case.",
    "// M12.4 uses the full byte as a physical witness of the selected broad-regression case.",
)
(RTL / "m12_4_broad_capture_controller_v1.sv").write_text(controller)

bd = common((RTL / "m12_3_multitick_capture_controller_bd_v1.v").read_text())
(RTL / "m12_4_broad_capture_controller_bd_v1.v").write_text(bd)

vivado_dir = RTL / "vivado"
project = common((vivado_dir / "create_m12_3_project.tcl").read_text())
(vivado_dir / "create_m12_4_project.tcl").write_text(project)

capture = common((vivado_dir / "capture_m12_3_multitick.tcl").read_text())
old_header = 'case_id\\tcase_name\\tneuron_count\\ttick_count'
new_header = 'case_id\\tcase_name\\tsource_kind\\tseed\\tconfiguration_sha256\\tneuron_count\\taxon_count\\tsynapse_count\\troute_count\\ttick_count'
capture = capture.replace(old_header, new_header)
capture = capture.replace("if {[llength $fields] != 4}", "if {[llength $fields] != 10}")
capture = capture.replace(
    "    set neuron_count [lindex $fields 2]\n    set tick_count [lindex $fields 3]",
    "    set source_kind [lindex $fields 2]\n"
    "    set seed [lindex $fields 3]\n"
    "    set configuration_sha256 [lindex $fields 4]\n"
    "    set neuron_count [lindex $fields 5]\n"
    "    set tick_count [lindex $fields 9]",
)
capture = capture.replace(
    "set selected_case [expr {($phase >> 4) & 0xF}]",
    "set selected_case $phase",
)
capture = capture.replace(
    'puts "M12.4 case $case_id selected and reset: name=$case_name neurons=$neuron_count ticks=$tick_count"',
    'puts "M12.4 case $case_id selected and reset: name=$case_name kind=$source_kind seed=$seed config=$configuration_sha256 neurons=$neuron_count ticks=$tick_count"',
)
capture = capture.replace(
    "M12.4 physical directed multi-tick suite capture completed successfully:",
    "M12.4 physical broad deterministic suite capture completed successfully:",
)
(vivado_dir / "capture_m12_4_broad.tcl").write_text(capture)

bitstream = common((RTL / "run_m12_3_bitstream.sh").read_text())
bitstream = bitstream.replace(
    'printf \'M12.4 directed cases: 10\\n\'\nprintf \'M12.4 directed committed ticks: 40\\n\'',
    'printf \'M12.4 broad cases: 22\\n\'\nprintf \'M12.4 broad committed ticks: 166\\n\'',
)
bitstream = bitstream.replace(
    "M12_4_EXPECTED|RECURRENT_SCHEDULE|RECURRENT_EVENTS",
    "M12_4_EXPECTED|RECURRENT_SCHEDULE|GOLDEN_STATE|GOLDEN_SPIKE",
)
bitstream = bitstream.replace("directed cases", "broad cases")
bitstream = bitstream.replace("directed committed ticks", "broad committed ticks")
(RTL / "run_m12_4_bitstream.sh").write_text(bitstream)
