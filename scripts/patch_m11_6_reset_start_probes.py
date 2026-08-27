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
        raise RuntimeError(f'{path}: expected exactly one occurrence of {old!r}, found {text.count(old)}')
    path.write_text(text.replace(old, new, 1))

# Reset-independent sticky witness that the physical smoke_start net reached the
# module boundary. It deliberately does not depend on smoke_resetn.
replace_once(
    WRAP,
    '    output wire [31:0]  clock_heartbeat,\n',
    '    output wire [31:0]  clock_heartbeat,\n    output wire         start_seen,\n',
)
replace_once(
    WRAP,
    '    assign clock_heartbeat = heartbeat_counter;\n\n',
    '    assign clock_heartbeat = heartbeat_counter;\n\n'
    '    // Sticky, reset-independent witness for the VIO smoke_start net. The\n'
    '    // bitstream initializes this to zero; any observed start level sets it.\n'
    '    reg start_seen_reg = 1\'b0;\n'
    '    always @(posedge ap_clk) begin\n'
    '        if (smoke_start)\n'
    '            start_seen_reg <= 1\'b1;\n'
    '    end\n'
    '    assign start_seen = start_seen_reg;\n\n',
)

replace_once(
    PROJECT,
    '    CONFIG.C_NUM_PROBE_IN {14} \\\n',
    '    CONFIG.C_NUM_PROBE_IN {16} \\\n',
)
replace_once(
    PROJECT,
    '    CONFIG.C_PROBE_IN13_WIDTH {32} \\\n',
    '    CONFIG.C_PROBE_IN13_WIDTH {32} \\\n    CONFIG.C_PROBE_IN14_WIDTH {1} \\\n    CONFIG.C_PROBE_IN15_WIDTH {1} \\\n',
)
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

replace_once(
    PROGRAM,
    'set p_heartbeat [find_one_probe $vio clock_heartbeat]\n',
    'set p_heartbeat [find_one_probe $vio clock_heartbeat]\n'
    'set p_reset_released [find_one_probe $vio reset_released]\n'
    'set p_start_seen [find_one_probe $vio start_seen]\n',
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
    '    error "M11.6 start_seen was unexpectedly set immediately after programming: value=$start_seen_before"\n'
    '}\n'
    'puts "M11.6 reset diagnostic before release: reset_released=$reset_asserted_readback start_seen=$start_seen_before"\n'
    'set heartbeat_before [get_property INPUT_VALUE $p_heartbeat]\n',
)
replace_once(
    PROGRAM,
    'puts "M11.6 local smoke reset released through VIO; output readback=$reset_readback"\n\n',
    'refresh_hw_vio $vio\n'
    'set reset_released_readback [get_property INPUT_VALUE $p_reset_released]\n'
    'if {$reset_released_readback ne "1"} {\n'
    '    error "M11.6 proc_sys_reset did not release the smoke domain: reset_released=$reset_released_readback"\n'
    '}\n'
    'puts "M11.6 local smoke reset released through VIO; output readback=$reset_readback reset_released=$reset_released_readback"\n\n',
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
    '    error "M11.6 hardware smoke timed out after clock and VIO-output diagnostics. If status remains at reset values, instrument proc_sys_reset peripheral_aresetn and smoke-start observation before changing computational RTL."\n',
    '    error "M11.6 hardware smoke timed out after clock/reset/start diagnostics. If reset_released=1 and start_seen=1 while phase remains 00, debug the smoke FSM boundary before changing computational RTL."\n',
)

text = TESTS.read_text()
text = text.replace('assert "CONFIG.C_NUM_PROBE_IN {14}" in text', 'assert "CONFIG.C_NUM_PROBE_IN {16}" in text')
text = text.replace('assert "connect_named_pair clock_heartbeat" in text', 'assert "connect_named_pair clock_heartbeat" in text\n    assert "reset_released" in text\n    assert "connect_named_pair start_seen" in text')
text = text.replace('assert "heartbeat_counter" in wrapper', 'assert "heartbeat_counter" in wrapper\n    assert "start_seen_reg" in wrapper')
# Hardware runner token coverage.
needle = '        "smoke_start",\n        "smoke_done",\n'
if needle not in text:
    raise RuntimeError('tests: hardware-runner token insertion point not found')
text = text.replace(needle, '        "smoke_start",\n        "reset_released",\n        "start_seen",\n        "smoke_done",\n', 1)
TESTS.write_text(text)

# Documentation: describe the new decisive probes without rewriting prior evidence.
replace_once(
    DOC,
    'A reset-independent 32-bit heartbeat counter runs directly from `pl_clk0` and is exposed through VIO. The hardware script samples it twice before reset release and refuses to start the workload unless the value changes. This separates three bring-up failure classes: stopped PL clock, reset/control failure, and actual computational smoke failure. VIO output probes supply `smoke_start` and `smoke_resetn`; input probes expose the heartbeat plus busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count.\n',
    'A reset-independent 32-bit heartbeat counter runs directly from `pl_clk0` and is exposed through VIO. The hardware script samples it twice before reset release and refuses to start the workload unless the value changes. Two additional bring-up witnesses make the control boundary explicit: `reset_released` samples the synchronized `proc_sys_reset/peripheral_aresetn` net at the smoke-domain input, while reset-independent sticky `start_seen` records whether the physical `smoke_start` net ever reached the module boundary. This separates stopped PL clock, reset-release failure, start-delivery failure, and actual smoke-FSM/datapath failure. VIO output probes supply `smoke_start` and `smoke_resetn`; input probes expose heartbeat/reset/start diagnostics plus busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count.\n',
)

print('Patched M11.6 with reset_released and reset-independent start_seen probes.')
