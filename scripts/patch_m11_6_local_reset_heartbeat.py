from pathlib import Path

ROOT = Path('.')
RTL = ROOT / 'Neuromorphic Digital Twin' / 'rtl' / 'core_v1'
DOC = ROOT / 'Neuromorphic Digital Twin' / 'docs' / 'M11_6_BITSTREAM_HARDWARE_SMOKE.md'
MILESTONES = ROOT / 'MILESTONES.md'


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'expected text not found in {path}: {old[:120]!r}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


# 1) The existing smoke controller already has the correct two-flop reset
# synchronizer; rename its input to make the new local/VIO ownership explicit.
smoke = RTL / 'm11_6_smoke_controller_v1.sv'
replace_once(smoke, 'input  logic         pl_resetn0,', 'input  logic         smoke_resetn,')
replace_once(
    smoke,
    '''    // Active-low PS fabric reset is asynchronously asserted and synchronously\n    // released into the PL clock domain. The same synchronized reset is sent to\n    // the HLS IP so the complete smoke path shares one reset boundary.\n''',
    '''    // Active-low VIO-controlled local reset is asynchronously asserted and\n    // synchronously released into the PL clock domain. The same synchronized\n    // reset is sent to the HLS IP so the complete smoke path shares one reset\n    // boundary without depending on PS software-managed fabric reset state.\n''',
)
replace_once(smoke, 'always_ff @(posedge ap_clk or negedge pl_resetn0) begin', 'always_ff @(posedge ap_clk or negedge smoke_resetn) begin')
replace_once(smoke, 'if (!pl_resetn0)', 'if (!smoke_resetn)')

# 2) Thin Verilog Module-Reference wrapper: expose a reset-independent heartbeat
# and rename the reset pin. Declaration-time init is mapped to FPGA INIT state,
# so the counter starts deterministically after configuration without a reset.
wrapper = RTL / 'm11_6_smoke_controller_bd_v1.v'
text = wrapper.read_text(encoding='utf-8')
text = text.replace('ASSOCIATED_RESET pl_resetn0', 'ASSOCIATED_RESET smoke_resetn')
text = text.replace('XIL_INTERFACENAME pl_resetn0, POLARITY ACTIVE_LOW', 'XIL_INTERFACENAME smoke_resetn, POLARITY ACTIVE_LOW')
text = text.replace('input  wire         pl_resetn0,', 'input  wire         smoke_resetn,')
text = text.replace('    input  wire         smoke_start,\n\n    output wire         smoke_busy,', '    input  wire         smoke_start,\n\n    output wire [31:0]  clock_heartbeat,\n    output wire         smoke_busy,')
text = text.replace('        .pl_resetn0(pl_resetn0),', '        .smoke_resetn(smoke_resetn),')
needle = '    m11_6_smoke_controller_v1 smoke_i (\n'
if needle not in text:
    raise SystemExit('wrapper instantiation marker missing')
heartbeat = '''    // Free-running physical PL-clock witness. It is intentionally independent\n    // of the smoke/core reset so Hardware Manager can distinguish a stopped\n    // pl_clk0 from a reset or datapath problem before starting the workload.\n    reg [31:0] heartbeat_counter = 32'h00000000;\n    always @(posedge ap_clk) begin\n        heartbeat_counter <= heartbeat_counter + 32'd1;\n    end\n    assign clock_heartbeat = heartbeat_counter;\n\n'''
text = text.replace(needle, heartbeat + needle, 1)
wrapper.write_text(text, encoding='utf-8')

# 3) Vivado block design: PS supplies clock only; VIO owns local reset. Remove
# proc_sys_reset/xlconstant dependencies and expose heartbeat/reset probes.
project = RTL / 'vivado' / 'create_m11_6_project.tcl'
replace_once(
    project,
    'foreach required_ip {xilinx.com:ip:zynq_ultra_ps_e:3.5 xilinx.com:ip:vio:3.0 xilinx.com:ip:proc_sys_reset:5.0 xilinx.com:ip:xlconstant:1.1} {',
    'foreach required_ip {xilinx.com:ip:zynq_ultra_ps_e:3.5 xilinx.com:ip:vio:3.0} {',
)
replace_once(
    project,
    '''# Use the K26 processing system only as a carrier-independent 100 MHz PL clock\n# and fabric-reset source. The Zynq MPSoC cell must first receive its SOM board\n# preset through Block Automation; that step initializes the PS/DDR configuration\n# and creates the dedicated external DDR/FIXED_IO interfaces. Only after the\n# preset is applied do we disable unused AXI masters and freeze PL0 at 100 MHz.\n''',
    '''# Use the K26 processing system only as a carrier-independent 100 MHz PL clock\n# source. The Zynq MPSoC cell must first receive its SOM board preset through\n# Block Automation; that step initializes the PS/DDR configuration and dedicated\n# I/O. The M11.6 JTAG smoke deliberately does not depend on the software-managed\n# PS fabric-reset GPIO; reset ownership is local to VIO inside the PL shell.\n''',
)
replace_once(project, '    CONFIG.PSU__USE__FABRIC__RST {1} \\\n', '    CONFIG.PSU__USE__FABRIC__RST {0} \\\n')
replace_once(
    project,
    '''# dedicated PS/SOM resources configured by the board preset. For M11.6 the only\n# PS-to-PL boundary we require is the fabric clock/reset pair below.\nset pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]\nset pl_resetn0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_resetn0]\nif {[llength $pl_clk0_pin] != 1 || [llength $pl_resetn0_pin] != 1} {\n    error "M11.6 KV260 PS preset did not expose the required pl_clk0/pl_resetn0 fabric boundary."\n}\nputs "M11.6 PS Block Automation configured K26 SOM; PL boundary: clk=$pl_clk0_pin reset=$pl_resetn0_pin"\n''',
    '''# dedicated PS/SOM resources configured by the board preset. For M11.6 the only\n# PS-to-PL signal required by the JTAG shell is the fabric clock below.\nset pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]\nif {[llength $pl_clk0_pin] != 1} {\n    error "M11.6 KV260 PS preset did not expose the required pl_clk0 fabric clock."\n}\nputs "M11.6 PS Block Automation configured K26 SOM; PL clock boundary: clk=$pl_clk0_pin"\n''',
)
replace_once(project, '    CONFIG.C_NUM_PROBE_IN {13} \\\n    CONFIG.C_NUM_PROBE_OUT {1} \\\n', '    CONFIG.C_NUM_PROBE_IN {14} \\\n    CONFIG.C_NUM_PROBE_OUT {2} \\\n')
replace_once(
    project,
    '''    CONFIG.C_PROBE_IN12_WIDTH {13} \\\n    CONFIG.C_PROBE_OUT0_WIDTH {1} \\\n    CONFIG.C_PROBE_OUT0_INIT_VAL {0x0}] $vio\n''',
    '''    CONFIG.C_PROBE_IN12_WIDTH {13} \\\n    CONFIG.C_PROBE_IN13_WIDTH {32} \\\n    CONFIG.C_PROBE_OUT0_WIDTH {1} \\\n    CONFIG.C_PROBE_OUT0_INIT_VAL {0x0} \\\n    CONFIG.C_PROBE_OUT1_WIDTH {1} \\\n    CONFIG.C_PROBE_OUT1_INIT_VAL {0x0}] $vio\n''',
)
old_reset_block = '''# Clock/reset boundary. The K26 PS reports its realizable PL0 frequency as\n# approximately 100 MHz (99,999,001 Hz with this board preset). Module Reference\n# clock metadata is therefore allowed to inherit the propagated PS value instead\n# of forcing an exact 100,000,000-Hz property.\n#\n# Synchronize the active-low PS fabric reset with proc_sys_reset. Its active-low\n# peripheral_aresetn drives the smoke sequencer; its active-high peripheral_reset\n# drives the packaged HLS ap_rst. Both are synchronous to the same PL0 clock.\nset ps_reset [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_m11_6]\nset_property -dict [list CONFIG.C_EXT_RESET_HIGH {0}] $ps_reset\nset const_one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_m11_6]\nset_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $const_one\nset const_zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_m11_6]\nset_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $const_zero\n\nconnect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] \\\n    [get_bd_pins smoke_0/ap_clk] \\\n    [get_bd_pins neuron_step_v1_0/ap_clk] \\\n    [get_bd_pins vio_m11_6/clk] \\\n    [get_bd_pins proc_sys_reset_m11_6/slowest_sync_clk]\nconnect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_resetn0] \\\n    [get_bd_pins proc_sys_reset_m11_6/ext_reset_in]\nconnect_bd_net [get_bd_pins const_one_m11_6/dout] \\\n    [get_bd_pins proc_sys_reset_m11_6/dcm_locked]\nconnect_bd_net [get_bd_pins const_zero_m11_6/dout] \\\n    [get_bd_pins proc_sys_reset_m11_6/aux_reset_in] \\\n    [get_bd_pins proc_sys_reset_m11_6/mb_debug_sys_rst]\nconnect_bd_net [get_bd_pins proc_sys_reset_m11_6/peripheral_aresetn] \\\n    [get_bd_pins smoke_0/pl_resetn0]\nconnect_bd_net [get_bd_pins proc_sys_reset_m11_6/peripheral_reset] \\\n    [get_bd_pins neuron_step_v1_0/ap_rst]\nputs "M11.6 synchronized reset boundary: smoke=peripheral_aresetn HLS=peripheral_reset"\n'''
new_reset_block = '''# Clock/reset boundary. The K26 PS reports its realizable PL0 frequency as\n# approximately 100 MHz (99,999,001 Hz with this board preset). Module Reference\n# clock metadata inherits that propagated PS value. Reset is deliberately local:\n# VIO probe_out1 asynchronously asserts the smoke reset; the existing two-flop\n# synchronizer in the smoke controller releases it synchronously and produces the\n# matching active-high HLS ap_rst. A reset-independent heartbeat proves pl_clk0.\nconnect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] \\\n    [get_bd_pins smoke_0/ap_clk] \\\n    [get_bd_pins neuron_step_v1_0/ap_clk] \\\n    [get_bd_pins vio_m11_6/clk]\nconnect_verified_pair hls_ap_rst ap_rst\nconnect_named_pair smoke_resetn vio_m11_6/probe_out1 smoke_0/smoke_resetn\nconnect_named_pair clock_heartbeat smoke_0/clock_heartbeat vio_m11_6/probe_in13\nputs "M11.6 local reset/heartbeat boundary: reset=VIO smoke_resetn heartbeat=clock_heartbeat"\n'''
replace_once(project, old_reset_block, new_reset_block)

# 4) Hardware Manager Tcl: verify heartbeat first, then release local reset,
# then run the unchanged autonomous workload.
program = RTL / 'vivado' / 'program_m11_6_smoke.tcl'
text = program.read_text(encoding='utf-8')
text = text.replace('open_hw\n', 'open_hw_manager\n', 1)
text = text.replace('set p_start [find_one_probe $vio smoke_start]\n', 'set p_start     [find_one_probe $vio smoke_start]\nset p_resetn    [find_one_probe $vio smoke_resetn]\nset p_heartbeat [find_one_probe $vio clock_heartbeat]\n', 1)
old_sequence = '''# Synchronize Tcl-side values with the freshly programmed VIO before pulsing the\n# one-bit command. VIO uses the documented OUTPUT_VALUE + commit model.\nrefresh_hw_vio -update_output_values $vio\nset_property OUTPUT_VALUE 0 $p_start\ncommit_hw_vio $p_start\nafter 10\nset_property OUTPUT_VALUE 1 $p_start\ncommit_hw_vio $p_start\nafter 10\nset_property OUTPUT_VALUE 0 $p_start\ncommit_hw_vio $p_start\nputs "M11.6 smoke_start pulse committed through VIO."\n'''
new_sequence = '''# Synchronize Tcl-side values with the freshly programmed VIO. Both command\n# outputs initialize low: smoke_start=0 and smoke_resetn=0. Before releasing the\n# reset, prove that the reset-independent heartbeat advances on the physical PL0\n# clock. This distinguishes clock failure from reset/datapath failure.\nrefresh_hw_vio -update_output_values $vio\nset_property OUTPUT_VALUE 0 $p_start\ncommit_hw_vio $p_start\nset_property OUTPUT_VALUE 0 $p_resetn\ncommit_hw_vio $p_resetn\nrefresh_hw_vio $vio\nset heartbeat_before [get_property INPUT_VALUE $p_heartbeat]\nafter 100\nrefresh_hw_vio $vio\nset heartbeat_after [get_property INPUT_VALUE $p_heartbeat]\nif {$heartbeat_before eq $heartbeat_after} {\n    error "M11.6 PL clock heartbeat did not advance: value=$heartbeat_before. Verify pl_clk0 before debugging reset or datapath logic."\n}\nputs "M11.6 PL clock heartbeat advanced: $heartbeat_before -> $heartbeat_after"\n\n# Release the local reset through VIO. The smoke controller synchronizes the\n# deassertion into pl_clk0 and drives the packaged HLS active-high ap_rst from the\n# same synchronized reset state.\nset_property OUTPUT_VALUE 1 $p_resetn\ncommit_hw_vio $p_resetn\nafter 20\nputs "M11.6 local smoke reset released through VIO."\n\nset_property OUTPUT_VALUE 1 $p_start\ncommit_hw_vio $p_start\nafter 10\nset_property OUTPUT_VALUE 0 $p_start\ncommit_hw_vio $p_start\nputs "M11.6 smoke_start pulse committed through VIO."\n'''
if old_sequence not in text:
    raise SystemExit('program Tcl VIO sequence block missing')
text = text.replace(old_sequence, new_sequence, 1)
program.write_text(text, encoding='utf-8')

# 5) Shell runner: document the stock-Kria unload prerequisite and require the
# two new bring-up markers before accepting a physical result.
runner = RTL / 'run_m11_6_hardware_smoke.sh'
text = runner.read_text(encoding='utf-8')
text = text.replace(
    "echo 'The board must be powered, visible to the Vivado hardware server, and have its PS running so pl_clk0 is active.'\n",
    "echo 'The board must be powered, visible to the Vivado hardware server, and have its PS running so pl_clk0 is active.'\necho 'On stock Kria Linux, unload the active starter-kit PL application first with: sudo xmutil unloadapp'\n",
    1,
)
text = text.replace(
    '    "M11.6 bitstream programmed successfully." \\\n    "M11.6 smoke_start pulse committed through VIO." \\\n',
    '    "M11.6 bitstream programmed successfully." \\\n    "M11.6 PL clock heartbeat advanced:" \\\n    "M11.6 local smoke reset released through VIO." \\\n    "M11.6 smoke_start pulse committed through VIO." \\\n',
    1,
)
runner.write_text(text, encoding='utf-8')

# 6) Source guards now enforce the local-reset/heartbeat architecture.
tests = ROOT / 'Neuromorphic Digital Twin' / 'tests' / 'test_m11_6_bitstream_sources.py'
text = tests.read_text(encoding='utf-8')
text = text.replace('def test_m11_6_smoke_uses_ps_reset_and_exports_real_hls_boundary() -> None:', 'def test_m11_6_smoke_uses_local_reset_heartbeat_and_exports_real_hls_boundary() -> None:')
text = text.replace('    assert "input  logic         pl_resetn0" in smoke\n', '    assert "input  logic         smoke_resetn" in smoke\n')
text = text.replace('    assert "ASSOCIATED_RESET pl_resetn0" in wrapper\n', '    assert "ASSOCIATED_RESET smoke_resetn" in wrapper\n    assert "clock_heartbeat" in wrapper\n    assert "heartbeat_counter" in wrapper\n')
old_project_asserts = '''    assert "set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]" in text\n    assert "set pl_resetn0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_resetn0]" in text\n    assert "M11.6 PS Block Automation configured K26 SOM; PL boundary:" in text\n    assert "xilinx.com:ip:vio:3.0" in text\n    assert "xilinx.com:ip:proc_sys_reset:5.0" in text\n    assert "CONFIG.C_EXT_RESET_HIGH {0}" in text\n    assert "proc_sys_reset_m11_6/slowest_sync_clk" in text\n    assert "proc_sys_reset_m11_6/ext_reset_in" in text\n    assert "proc_sys_reset_m11_6/peripheral_aresetn" in text\n    assert "proc_sys_reset_m11_6/peripheral_reset" in text\n    assert "[get_bd_pins smoke_0/hls_ap_rst]" not in text\n    assert "M11.6 synchronized reset boundary:" in text\n    assert "connect_named_pair smoke_start" in text\n    assert "connect_named_pair smoke_pass" in text\n'''
new_project_asserts = '''    assert "set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]" in text\n    assert "pl_resetn0_pin" not in text\n    assert "CONFIG.PSU__USE__FABRIC__RST {0}" in text\n    assert "M11.6 PS Block Automation configured K26 SOM; PL clock boundary:" in text\n    assert "xilinx.com:ip:vio:3.0" in text\n    assert "xilinx.com:ip:proc_sys_reset:5.0" not in text\n    assert "xilinx.com:ip:xlconstant:1.1" not in text\n    assert "CONFIG.C_NUM_PROBE_IN {14}" in text\n    assert "CONFIG.C_NUM_PROBE_OUT {2}" in text\n    assert "connect_verified_pair hls_ap_rst ap_rst" in text\n    assert "connect_named_pair smoke_resetn" in text\n    assert "connect_named_pair clock_heartbeat" in text\n    assert "M11.6 local reset/heartbeat boundary:" in text\n    assert "connect_named_pair smoke_start" in text\n    assert "connect_named_pair smoke_pass" in text\n'''
if old_project_asserts not in text:
    raise SystemExit('test project assertion block missing')
text = text.replace(old_project_asserts, new_project_asserts, 1)
text = text.replace('        "open_hw",\n', '        "open_hw_manager",\n')
text = text.replace('        "smoke_start",\n', '        "smoke_start",\n        "smoke_resetn",\n        "clock_heartbeat",\n        "M11.6 PL clock heartbeat advanced:",\n        "M11.6 local smoke reset released through VIO.",\n')
text = text.replace('    assert "open_hw_manager" not in tcl\n', '    assert "open_hw\\n" not in tcl\n    assert "sudo xmutil unloadapp" in runner\n')
tests.write_text(text, encoding='utf-8')

# 7) Documentation: replace the physical-shell and programming descriptions and
# record the bring-up prerequisite discovered on the real stock KV260 image.
doc = DOC.read_text(encoding='utf-8')
old_shell = '''```text\nK26 Zynq UltraScale+ PS\n        │\n        ├── pl_clk0 (100 MHz PL clock)\n        └── pl_resetn0\n                │\n                v\n      M11.6 autonomous smoke sequencer\n                │\n                ├── packed M08 memories\n                ├── exact signed-64 Phase B\n                ├── packaged neuron_step_v1 HLS IP\n                ├── recurrent route CSR / double buffer\n                └── post-commit debug reads\n                │\n                v\n          VIO over JTAG\n```\n\nThe Zynq UltraScale+ processing-system block supplies `pl_clk0` and `pl_resetn0`. DDR and fixed-IO interfaces are externalized as dedicated PS interfaces, but M11.6 adds no carrier-card PL `PACKAGE_PIN` assignments. This lets the first smoke image remain tied to the exact `xck26-sfvc784-2LV-c` SOM device rather than to one carrier connector mapping.\n\nControl and status use a Vivado VIO core. One output probe supplies `smoke_start`; input probes expose busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count. The VIO core is driven by the same PL clock as the computational core.\n'''
new_shell = '''```text\nK26 Zynq UltraScale+ PS\n        │\n        └── pl_clk0 (~100 MHz PL clock)\n                │\n                ├── reset-independent heartbeat counter -> VIO\n                │\n                v\n      M11.6 autonomous smoke sequencer\n                ↑\n        VIO smoke_resetn\n                │\n                ├── packed M08 memories\n                ├── exact signed-64 Phase B\n                ├── packaged neuron_step_v1 HLS IP\n                ├── recurrent route CSR / double buffer\n                └── post-commit debug reads\n                │\n                v\n          VIO over JTAG\n```\n\nThe Zynq UltraScale+ processing-system block supplies only `pl_clk0` to the JTAG smoke shell. DDR and fixed-IO remain dedicated PS/SOM resources, and M11.6 adds no carrier-card PL `PACKAGE_PIN` assignments. The physical smoke no longer depends on software-managed `pl_resetn0`: VIO supplies an active-low `smoke_resetn`, the smoke controller asynchronously asserts and synchronously releases it in the PL clock domain, and that same synchronized state drives the packaged HLS `ap_rst`.\n\nA reset-independent 32-bit heartbeat counter runs directly from `pl_clk0` and is exposed through VIO. The hardware script samples it twice before reset release and refuses to start the workload unless the value changes. This separates three bring-up failure classes: stopped PL clock, reset/control failure, and actual computational smoke failure. VIO output probes supply `smoke_start` and `smoke_resetn`; input probes expose the heartbeat plus busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count.\n'''
if old_shell not in doc:
    raise SystemExit('doc physical-shell block missing')
doc = doc.replace(old_shell, new_shell, 1)
doc = doc.replace('4. Builds a block design containing the Zynq UltraScale+ PS clock/reset source, the autonomous smoke module, the real packaged HLS IP, and one VIO core.', '4. Builds a block design containing the Zynq UltraScale+ PS PL0 clock source, the autonomous smoke module with reset-independent heartbeat, the real packaged HLS IP, and one VIO core.')
old_prog = '''1. Connects to the hardware server and opens the JTAG target.\n2. Selects the single K26 device.\n3. Programs `neuromorphic_twin_m11_6.bit` and associates `neuromorphic_twin_m11_6.ltx`.\n4. Discovers the VIO and named smoke probes.\n5. Pulses `smoke_start` using the VIO `OUTPUT_VALUE`/commit mechanism.\n6. Polls the VIO until `smoke_done` or a bounded host timeout.\n7. Prints the pass/failure code, sequencer phase, tick, core fault, final neuron states/spikes, and recurrent-bank status.\n8. Requires `smoke_pass=1`.\n'''
new_prog = '''1. Connects to the hardware server and opens the JTAG target.\n2. Selects the single K26 device.\n3. Programs `neuromorphic_twin_m11_6.bit` and associates `neuromorphic_twin_m11_6.ltx`.\n4. Discovers the VIO and named smoke probes.\n5. Holds `smoke_resetn=0`, samples the reset-independent heartbeat twice, and requires it to advance.\n6. Releases `smoke_resetn=1` through VIO and allows the synchronized local reset to clear.\n7. Pulses `smoke_start` using the VIO `OUTPUT_VALUE`/commit mechanism.\n8. Polls the VIO until `smoke_done` or a bounded host timeout.\n9. Prints the pass/failure code, sequencer phase, tick, core fault, final neuron states/spikes, and recurrent-bank status.\n10. Requires `smoke_pass=1`.\n'''
if old_prog not in doc:
    raise SystemExit('doc programming steps missing')
doc = doc.replace(old_prog, new_prog, 1)
doc = doc.replace('M11.6 bitstream programmed successfully.\nM11.6 smoke_start pulse committed through VIO.', 'M11.6 bitstream programmed successfully.\nM11.6 PL clock heartbeat advanced: ... -> ...\nM11.6 local smoke reset released through VIO.\nM11.6 smoke_start pulse committed through VIO.')
old_prereq = '''### PS clock prerequisite\n\nThe hardware smoke uses PS `pl_clk0`; therefore the K26 processing system must be alive and supplying that clock when the PL image is programmed. The normal powered/booted SOM state is the intended bring-up condition. If the VIO is discoverable but all values remain static and the smoke times out, the first check is PS/PL-clock availability rather than changing computational RTL.\n'''
new_prereq = '''### Stock-Kria/Linux prerequisite and physical bring-up finding\n\nThe hardware smoke uses PS `pl_clk0`; therefore the K26 processing system must be alive and supplying that clock when the PL image is programmed. On the stock AMD Kria Linux image, the default `k26-starter-kits` PL application can already occupy slot 0. Before direct JTAG programming, unload that active application cleanly with `sudo xmutil unloadapp` and verify Linux remains responsive. Directly overwriting an active stock PL application during the first board attempts caused the UART/Linux session to become unresponsive.\n\nThe first programmed M11.6 image was accepted by JTAG and its VIO was discovered, but every clocked smoke signal remained zero. `PL0_REF_CTRL` read back as `0x01010A00`, showing the PL0 clock generator configured active, and a manual PS-GPIO output-enable experiment did not make the smoke advance. The final JTAG shell therefore removes the software-managed `pl_resetn0` dependency and adds the reset-independent heartbeat described above. Manual PS register pokes are not part of the accepted flow.\n'''
if old_prereq not in doc:
    raise SystemExit('doc prerequisite block missing')
doc = doc.replace(old_prereq, new_prereq, 1)
DOC.write_text(doc, encoding='utf-8')

# 8) Milestones: revise architecture, reopen implementation evidence invalidated by
# the shell change, and preserve the first routed image as historical evidence.
m = MILESTONES.read_text(encoding='utf-8')
m = m.replace('- Use the Zynq UltraScale+ PS `pl_clk0` and `pl_resetn0` so the first hardware shell does not require carrier-card PL pin assignments.', '- Use the Zynq UltraScale+ PS `pl_clk0` as the carrier-independent clock, but keep JTAG-smoke reset local to VIO so direct PL programming does not depend on PS software-managed `pl_resetn0`.')
old_gates = '''- [x] Define carrier-independent PS-clock + VIO physical shell.\n- [x] Add autonomous packed-M08 + real-HLS + recurrent smoke sequencer.\n- [x] Add source-controlled implementation/bitstream/reporting flow.\n- [x] Add source-controlled VIO programming/smoke flow.\n- [x] Add focused M11.6 source-regression guards.\n- [x] Independently run the focused M11.6 source guard.\n- [ ] Independently rerun the complete Python regression suite after the final M11.6 shell changes.\n- [x] Run Vivado synthesis, placement, routing, DRC, and bitstream generation.\n- [x] Confirm nonnegative routed WNS and WHS.\n- [x] Confirm final implemented resource-capacity marker.\n- [x] Confirm `.bit`, `.ltx`, routed `.dcp`, and `.xsa` artifacts.\n- [ ] Program the physical K26 through JTAG.\n- [ ] Confirm VIO control/readback and autonomous four-tick `smoke_pass=1`.\n- [ ] Record final hardware evidence and mark M11.6 and M11 complete.\n'''
new_gates = '''- [x] Define carrier-independent PS-clock + VIO physical shell.\n- [x] Add autonomous packed-M08 + real-HLS + recurrent smoke sequencer.\n- [x] Add source-controlled implementation/bitstream/reporting flow.\n- [x] Add source-controlled VIO programming/smoke flow.\n- [x] Add focused M11.6 source-regression guards.\n- [ ] Independently rerun the focused M11.6 source guard after the local-reset/heartbeat revision.\n- [ ] Independently rerun the complete Python regression suite after the final M11.6 shell changes.\n- [ ] Regenerate the revised shell through Vivado synthesis, placement, routing, DRC, and bitstream generation.\n- [ ] Confirm nonnegative routed WNS and WHS for the revised shell.\n- [ ] Confirm final implemented resource-capacity marker for the revised shell.\n- [ ] Confirm revised `.bit`, `.ltx`, routed `.dcp`, and `.xsa` artifacts.\n- [ ] Program the revised physical K26 image through JTAG after unloading any active stock Kria PL application.\n- [ ] Confirm the physical `pl_clk0` heartbeat advances through VIO.\n- [ ] Confirm VIO local-reset control/readback and autonomous four-tick `smoke_pass=1`.\n- [ ] Record final hardware evidence and mark M11.6 and M11 complete.\n'''
if old_gates not in m:
    raise SystemExit('milestone gate block missing')
m = m.replace(old_gates, new_gates, 1)
anchor = '''This is a checkpoint, not M11.6 completion. The remaining decisive evidence is physical K26 programming plus VIO/JTAG execution of the autonomous four-tick recurrent smoke workload with `smoke_pass=1`. M11.6 and M11 therefore remain **In progress**.\n\n'''
addition = '''This is a checkpoint, not M11.6 completion. The remaining decisive evidence is physical K26 programming plus VIO/JTAG execution of the autonomous four-tick recurrent smoke workload with `smoke_pass=1`. M11.6 and M11 therefore remain **In progress**.\n\n### First physical bring-up findings and shell revision — 2026-08-27\n\nThe first board attempt established that direct JTAG programming itself works: Vivado selected `xck26_0`, reached startup status `HIGH`, discovered the matching VIO core, and committed `smoke_start`. However, all clocked smoke outputs remained zero (`busy=0`, `done=0`, `pass=0`, phase/tick/state all zero) until the host timeout. The stock AMD Kria image also had the default `k26-starter-kits` PL application active; programming over that live PL image made the UART/Linux session unresponsive. The stock application is now explicitly unloaded with `sudo xmutil unloadapp` before future JTAG smoke attempts.\n\nPS-side diagnosis showed `PL0_REF_CTRL=0x01010A00`, consistent with the PL0 clock generator being configured active. A manual PS-GPIO output-enable experiment intended to release the fabric reset did not make the smoke advance and is not part of the accepted flow. The shell is therefore being revised instead of relying on further PS register pokes: `pl_clk0` remains the real physical clock, a reset-independent 32-bit heartbeat is exposed through VIO, and a second VIO output supplies a local active-low reset that the existing smoke-controller synchronizer converts into the shared smoke/HLS reset boundary.\n\nBecause this changes the physical shell, the 2026-08-25 routed image remains valuable historical implementation evidence but is no longer the candidate final M11.6 image. Synthesis/place/route, routed WNS/WHS, DRC, resource capacity, and `.bit/.ltx/.dcp/.xsa` generation must be rerun for the revised local-reset/heartbeat shell before physical closure. The M11.5 computational core and Python-golden workload are unchanged.\n\n'''
if anchor not in m:
    raise SystemExit('milestone checkpoint anchor missing')
m = m.replace(anchor, addition, 1)
MILESTONES.write_text(m, encoding='utf-8')

print('Patched M11.6 local reset + heartbeat shell, hardware flow, tests, docs, and milestones.')
