from pathlib import Path

branch_root = Path('.')
tcl_path = branch_root / 'Neuromorphic Digital Twin/rtl/core_v1/vivado/create_m11_6_project.tcl'
test_path = branch_root / 'Neuromorphic Digital Twin/tests/test_m11_6_bitstream_sources.py'

text = tcl_path.read_text(encoding='utf-8')
old_project = '''create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]
'''
new_project = '''create_project $project_name $project_dir -part $target_part -force
set_property TARGET_LANGUAGE Verilog [current_project]
set_property SIMULATOR_LANGUAGE Mixed [current_project]

# The K26 part alone does not initialize the Zynq UltraScale+ PS package/DDR
# configuration. Select the installed KV260 SOM board file dynamically; this is
# a SOM-level preset for the K26 PS/DDR/dedicated I/O and does not constrain any
# carrier-card PL pins.
set kv260_board_parts [get_board_parts -quiet xilinx.com:kv260_som:part0:*]
if {[llength $kv260_board_parts] == 0} {
    error "M11.6 requires the Vivado KV260 SOM board files (xilinx.com:kv260_som:part0:*)."
}
set kv260_board_part [lindex [lsort -dictionary $kv260_board_parts] end]
set_property BOARD_PART $kv260_board_part [current_project]
puts "M11.6 K26 SOM board preset: $kv260_board_part"
'''
if old_project not in text:
    raise SystemExit('create_project block not found')
text = text.replace(old_project, new_project, 1)

old_ps = '''# Use the K26 processing system only as a carrier-independent 100 MHz PL clock
# and fabric-reset source. No AXI host path is introduced in M11.6; control and
# observation are provided by VIO over the existing JTAG connection.
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0]
set_property -dict [list \\
    CONFIG.PSU__USE__M_AXI_GP0 {0} \\
    CONFIG.PSU__USE__M_AXI_GP1 {0} \\
    CONFIG.PSU__USE__M_AXI_GP2 {0} \\
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \\
    CONFIG.PSU__USE__FABRIC__RST {1}] $ps

set ddr_pin [get_bd_intf_pins -quiet zynq_ultra_ps_e_0/DDR]
set fixed_pin [get_bd_intf_pins -quiet zynq_ultra_ps_e_0/FIXED_IO]
if {[llength $ddr_pin] != 1 || [llength $fixed_pin] != 1} {
    error "M11.6 expected Zynq PS DDR and FIXED_IO interfaces."
}
make_bd_intf_pins_external $ddr_pin
make_bd_intf_pins_external $fixed_pin
'''
new_ps = '''# Use the K26 processing system only as a carrier-independent 100 MHz PL clock
# and fabric-reset source. The Zynq MPSoC cell must first receive its SOM board
# preset through Block Automation; that step initializes the PS/DDR configuration
# and creates the dedicated external DDR/FIXED_IO interfaces. Only after the
# preset is applied do we disable unused AXI masters and freeze PL0 at 100 MHz.
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \\
    -config {apply_board_preset "1"} $ps
set_property -dict [list \\
    CONFIG.PSU__USE__M_AXI_GP0 {0} \\
    CONFIG.PSU__USE__M_AXI_GP1 {0} \\
    CONFIG.PSU__USE__M_AXI_GP2 {0} \\
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \\
    CONFIG.PSU__USE__FABRIC__RST {1} \\
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

# Block Automation, rather than manual make_bd_intf_pins_external calls, owns
# creation of the PS dedicated-I/O boundary. Accept the normal DDR/FIXED_IO name
# suffixes Vivado may choose, but require exactly one of each.
set ddr_ports [get_bd_intf_ports -quiet -filter {NAME =~ "DDR*"}]
set fixed_ports [get_bd_intf_ports -quiet -filter {NAME =~ "FIXED_IO*"}]
if {[llength $ddr_ports] != 1 || [llength $fixed_ports] != 1} {
    puts "M11.6 external PS interfaces after Block Automation: [get_bd_intf_ports -quiet]"
    error "M11.6 PS Block Automation did not create exactly one DDR and one FIXED_IO external interface."
}
puts "M11.6 PS Block Automation created external interfaces: DDR=$ddr_ports FIXED_IO=$fixed_ports"
'''
if old_ps not in text:
    raise SystemExit('old PS block not found')
text = text.replace(old_ps, new_ps, 1)
tcl_path.write_text(text, encoding='utf-8')

# Harden the static source gate around the exact failure seen in the first
# independent Vivado M11.6 run.
test = test_path.read_text(encoding='utf-8')
old_test = '''    assert 'set project_name "neuromorphic_twin_m11_6"' in text
    assert "xilinx.com:ip:zynq_ultra_ps_e:3.5" in text
    assert "CONFIG.PSU__FPGA_PL0_ENABLE {1}" in text
    assert "get_bd_pins zynq_ultra_ps_e_0/pl_clk0" in text
    assert "get_bd_pins zynq_ultra_ps_e_0/pl_resetn0" in text
    assert "make_bd_intf_pins_external $ddr_pin" in text
    assert "make_bd_intf_pins_external $fixed_pin" in text
    assert "xilinx.com:ip:vio:3.0" in text
'''
new_test = '''    assert 'set project_name "neuromorphic_twin_m11_6"' in text
    assert "xilinx.com:ip:zynq_ultra_ps_e:3.5" in text
    assert "get_board_parts -quiet xilinx.com:kv260_som:part0:*" in text
    assert "set_property BOARD_PART $kv260_board_part" in text
    assert "apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e" in text
    assert 'apply_board_preset "1"' in text
    assert "CONFIG.PSU__FPGA_PL0_ENABLE {1}" in text
    assert "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}" in text
    assert "get_bd_intf_ports -quiet -filter {NAME =~ \"DDR*\"}" in text
    assert "get_bd_intf_ports -quiet -filter {NAME =~ \"FIXED_IO*\"}" in text
    assert "make_bd_intf_pins_external $ddr_pin" not in text
    assert "make_bd_intf_pins_external $fixed_pin" not in text
    assert "get_bd_pins zynq_ultra_ps_e_0/pl_clk0" in text
    assert "get_bd_pins zynq_ultra_ps_e_0/pl_resetn0" in text
    assert "xilinx.com:ip:vio:3.0" in text
'''
if old_test not in test:
    raise SystemExit('old source-test block not found')
test = test.replace(old_test, new_test, 1)
test_path.write_text(test, encoding='utf-8')
