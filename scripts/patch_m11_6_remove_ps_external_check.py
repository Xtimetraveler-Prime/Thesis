from pathlib import Path

root = Path('.')
tcl_path = root / 'Neuromorphic Digital Twin/rtl/core_v1/vivado/create_m11_6_project.tcl'
test_path = root / 'Neuromorphic Digital Twin/tests/test_m11_6_bitstream_sources.py'

text = tcl_path.read_text(encoding='utf-8')
old = '''# Block Automation, rather than manual make_bd_intf_pins_external calls, owns
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
new = '''# Unlike Zynq-7000 PS7 flows, the KV260/K26 Zynq UltraScale+ MPSoC preset does
# not require top-level DDR/FIXED_IO block-design interface ports. Those are
# dedicated PS/SOM resources configured by the board preset. For M11.6 the only
# PS-to-PL boundary we require is the fabric clock/reset pair below.
set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]
set pl_resetn0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_resetn0]
if {[llength $pl_clk0_pin] != 1 || [llength $pl_resetn0_pin] != 1} {
    error "M11.6 KV260 PS preset did not expose the required pl_clk0/pl_resetn0 fabric boundary."
}
puts "M11.6 PS Block Automation configured K26 SOM; PL boundary: clk=$pl_clk0_pin reset=$pl_resetn0_pin"
'''
if old not in text:
    raise SystemExit('old PS external-interface verification block not found')
text = text.replace(old, new, 1)
tcl_path.write_text(text, encoding='utf-8')

test = test_path.read_text(encoding='utf-8')
old_test = '''    assert 'get_bd_intf_ports -quiet -filter {NAME =~ "DDR*"}' in text
    assert 'get_bd_intf_ports -quiet -filter {NAME =~ "FIXED_IO*"}' in text
    assert "make_bd_intf_pins_external $ddr_pin" not in text
    assert "make_bd_intf_pins_external $fixed_pin" not in text
    assert "get_bd_pins zynq_ultra_ps_e_0/pl_clk0" in text
    assert "get_bd_pins zynq_ultra_ps_e_0/pl_resetn0" in text
'''
new_test = '''    assert "KV260/K26 Zynq UltraScale+ MPSoC preset does" in text
    assert "get_bd_intf_ports -quiet -filter" not in text
    assert "make_bd_intf_pins_external $ddr_pin" not in text
    assert "make_bd_intf_pins_external $fixed_pin" not in text
    assert "set pl_clk0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_clk0]" in text
    assert "set pl_resetn0_pin [get_bd_pins -quiet zynq_ultra_ps_e_0/pl_resetn0]" in text
    assert "M11.6 PS Block Automation configured K26 SOM; PL boundary:" in text
'''
if old_test not in test:
    raise SystemExit('old PS source-guard block not found')
test = test.replace(old_test, new_test, 1)
test_path.write_text(test, encoding='utf-8')
