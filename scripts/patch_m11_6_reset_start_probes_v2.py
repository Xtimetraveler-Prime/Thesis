from pathlib import Path

ROOT = Path('.')
RTL = ROOT / 'Neuromorphic Digital Twin' / 'rtl' / 'core_v1'
WRAP = RTL / 'm11_6_smoke_controller_bd_v1.v'
PROJECT = RTL / 'vivado' / 'create_m11_6_project.tcl'
PROGRAM = RTL / 'vivado' / 'program_m11_6_smoke.tcl'
TESTS = ROOT / 'Neuromorphic Digital Twin' / 'tests' / 'test_m11_6_bitstream_sources.py'
DOC = ROOT / 'Neuromorphic Digital Twin' / 'docs' / 'M11_6_BITSTREAM_HARDWARE_SMOKE.md'


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f'{path}: expected one occurrence of {old!r}, found {text.count(old)}')
    path.write_text(text.replace(old, new, 1))

# Wrapper: add a reset-independent sticky witness for smoke_start delivery.
replace_once(
    WRAP,
    '    output wire [31:0]  clock_heartbeat,\n',
    '    output wire [31:0]  clock_heartbeat,\n    output wire         start_seen,\n',
)
replace_once(
    WRAP,
    '    assign clock_heartbeat = heartbeat_counter;\n\n',
    '    assign clock_heartbeat = heartbeat_counter;\n\n'
    '    // Sticky reset-independent witness that VIO smoke_start reached this\n'
    '    // module boundary. Configuration initializes it to zero.\n'
    "    reg start_seen_reg = 1'b0;\n"
    '    always @(posedge ap_clk) begin\n'
    '        if (smoke_start)\n'
    "            start_seen_reg <= 1'b1;\n"
    '    end\n'
    '    assign start_seen = start_seen_reg;\n\n',
)

# Project: expose proc_sys_reset release and sticky start witness through VIO.
replace_once(PROJECT, '    CONFIG.C_NUM_PROBE_IN {14} \\\n', '    CONFIG.C_NUM_PROBE_IN {16} \\\n')
replace_once(
    PROJECT,
    '    CONFIG.C_PROBE_IN13_WIDTH {32} \\\n',
    '    CONFIG.C_PROBE_IN13_WIDTH {32} \\\n    CONFIG.C_PROBE_IN14_WIDTH {1} \\\n    CONFIG.C_PROBE_IN15_WIDTH {1} \\\n',
)
# Vivado 2025.2 reports this parameter as read-only; the generated IP default is 0.
replace_once(PROJECT, 'set_property -dict [list CONFIG.C_EXT_RESET_HIGH {0}] $local_reset\n', '')
replace_once(
    PROJECT,
    'connect_bd_net [get_bd_pins proc_sys_reset_m11_6/peripheral_aresetn] \\\n    [get_bd_pins smoke_0/smoke_resetn]\n',
    'set reset_released_net [create_bd_net reset_released]\n'
    'connect_bd_net -net $reset_released_net \\\n'
    '    [get_bd_pins proc_sys_reset_m11_6/peripheral_aresetn] \\\n'
    '    [get_bd_pins smoke_0/smoke_resetn] \\\n'
    '    [get_bd_pins vio_m11_6/probe_in14]\n',
)
replace_once(
    PROJECT,
    'connect_named_pair clock_heartbeat smoke_0/clock_heartbeat vio_m11_6/probe_in13\n',
    'connect_named_pair clock_heartbeat smoke_0/clock_heartbeat vio_m11_6/probe_in13\n'
    'connect_named_pair start_seen smoke_0/start_seen vio_m11_6/probe_in15\n',
)
replace_once(
    PROJECT,
    'puts "M11.6 local reset/heartbeat boundary: VIO reset -> proc_sys_reset; smoke=peripheral_aresetn HLS=peripheral_reset"\n',
    'puts "M11.6 local reset/heartbeat boundary: VIO reset -> proc_sys_reset; smoke=peripheral_aresetn HLS=peripheral_reset; probes=reset_released,start_seen"\n',
)

# Hardware Tcl: enforce reset/start observations before entering the workload.
replace_once(
    PROGRAM,
    'set p_heartbeat [find_one_probe $vio clock_heartbeat]\n',
    'set p_heartbeat      [find_one_probe $vio clock_heartbeat]\n'
    'set p_reset_released [find_one_probe $vio reset_released]\n'
    'set p_start_seen     [find_one_probe $vio start_seen]\n',
)
replace_once(
    PROGRAM,
    'set heartbeat_before [get_property INPUT_VALUE $p_heartbeat]\n',
    'set reset_asserted_readback [get_property INPUT_VALUE $p_reset_released]\n'
    'set start_seen_before [get_property INPUT_VALUE $p_start_seen]\n'
    'if {$reset_asserted_readback ne "0"} {\n'
    '    error "M11.6 synchronized reset was not asserted before heartbeat test: reset_released=$reset_asserted_readback"\n'
    '}\n'
    'if {$start_seen_before ne "0"} {\n'
    '    error "M11.6 start_seen unexpectedly set immediately after programming: value=$start_seen_before"\n'
    '}\n'
    'puts "M11.6 reset diagnostic before release: reset_released=$reset_asserted_readback start_seen=$start_seen_before"\n'
    'set heartbeat_before [get_property INPUT_VALUE $p_heartbeat]\n',
)
replace_once(
    PROGRAM,
    'puts "M11.6 local smoke reset released through VIO; output readback=$reset_readback"\n',
    'refresh_hw_vio $vio\n'
    'set reset_released_readback [get_property INPUT_VALUE $p_reset_released]\n'
    'if {$reset_released_readback ne "1"} {\n'
    '    error "M11.6 proc_sys_reset did not release the smoke domain: reset_released=$reset_released_readback"\n'
    '}\n'
    'puts "M11.6 local smoke reset released through VIO; output readback=$reset_readback reset_released=$reset_released_readback"\n',
)
replace_once(
    PROGRAM,
    'puts "M11.6 smoke_start asserted through VIO; output readback=$start_high_readback"\n',
    'refresh_hw_vio $vio\n'
    'set start_seen_high [get_property INPUT_VALUE $p_start_seen]\n'
    'if {$start_seen_high ne "1"} {\n'
    '    error "M11.6 smoke_start did not reach the module boundary: start_seen=$start_seen_high"\n'
    '}\n'
    'puts "M11.6 smoke_start asserted through VIO; output readback=$start_high_readback start_seen=$start_seen_high"\n',
)
replace_once(
    PROGRAM,
    'if {!$completed} {\n    error "M11.6 hardware smoke timed out after clock and VIO-output diagnostics. If status remains at reset values, instrument proc_sys_reset peripheral_aresetn and smoke-start observation before changing computational RTL."\n}\n',
    'if {!$completed} {\n'
    '    set reset_final [get_property INPUT_VALUE $p_reset_released]\n'
    '    set start_seen_final [get_property INPUT_VALUE $p_start_seen]\n'
    '    error "M11.6 hardware smoke timed out after clock/reset/start diagnostics: reset_released=$reset_final start_seen=$start_seen_final phase=$phase tick=$tick. If both diagnostics are 1 while phase remains 00, debug the smoke FSM boundary before changing computational RTL."\n'
    '}\n',
)

# Source guards.
text = TESTS.read_text()
text = text.replace('    assert "heartbeat_counter" in wrapper\n', '    assert "heartbeat_counter" in wrapper\n    assert "start_seen_reg" in wrapper\n', 1)
text = text.replace('    assert "CONFIG.C_NUM_PROBE_IN {14}" in text\n', '    assert "CONFIG.C_NUM_PROBE_IN {16}" in text\n', 1)
text = text.replace('    assert "connect_named_pair clock_heartbeat" in text\n', '    assert "connect_named_pair clock_heartbeat" in text\n    assert "reset_released" in text\n    assert "connect_named_pair start_seen" in text\n', 1)
text = text.replace('        "clock_heartbeat",\n', '        "clock_heartbeat",\n        "reset_released",\n        "start_seen",\n', 1)
if 'CONFIG.C_NUM_PROBE_IN {16}' not in text or 'start_seen_reg' not in text:
    raise RuntimeError('test updates did not apply')
TESTS.write_text(text)

replace_once(
    DOC,
    'A reset-independent 32-bit heartbeat counter runs directly from `pl_clk0` and is exposed through VIO. The hardware script samples it twice before reset release and refuses to start the workload unless the value changes. This separates three bring-up failure classes: stopped PL clock, reset/control failure, and actual computational smoke failure. VIO output probes supply `smoke_start` and `smoke_resetn`; input probes expose the heartbeat plus busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count.\n',
    'A reset-independent 32-bit heartbeat counter runs directly from `pl_clk0` and is exposed through VIO. The hardware script samples it twice before reset release and refuses to start the workload unless the value changes. Two additional physical witnesses isolate the control boundary: `reset_released` observes synchronized `proc_sys_reset/peripheral_aresetn`, and reset-independent sticky `start_seen` records whether the physical `smoke_start` net reached the module boundary. This separates stopped PL clock, reset-release failure, start-delivery failure, and actual smoke-FSM/datapath failure. VIO output probes supply `smoke_start` and `smoke_resetn`; input probes expose heartbeat/reset/start diagnostics plus busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count.\n',
)

print('Patched M11.6 reset_released/start_seen diagnostics successfully.')
