from pathlib import Path

root = Path('.')
tcl_path = root / 'Neuromorphic Digital Twin/rtl/core_v1/vivado/create_m11_6_project.tcl'
test_path = root / 'Neuromorphic Digital Twin/tests/test_m11_6_bitstream_sources.py'

text = tcl_path.read_text(encoding='utf-8')
old_ips = 'foreach required_ip {xilinx.com:ip:zynq_ultra_ps_e:3.5 xilinx.com:ip:vio:3.0} {'
new_ips = 'foreach required_ip {xilinx.com:ip:zynq_ultra_ps_e:3.5 xilinx.com:ip:vio:3.0 xilinx.com:ip:proc_sys_reset:5.0 xilinx.com:ip:xlconstant:1.1} {'
if old_ips not in text:
    raise SystemExit('required_ip block not found')
text = text.replace(old_ips, new_ips, 1)

old_block = '''# Clock/reset: PS pl_clk0 defaults to the 100 MHz PL0 clock for this IP profile.
# pl_resetn0 is synchronized and polarity-converted inside smoke_0; the resulting
# active-high hls_ap_rst is shared with the packaged HLS block.
connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] \\
    [get_bd_pins smoke_0/ap_clk] \\
    [get_bd_pins neuron_step_v1_0/ap_clk] \\
    [get_bd_pins vio_m11_6/clk]
connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_resetn0] \\
    [get_bd_pins smoke_0/pl_resetn0]
connect_bd_net [get_bd_pins smoke_0/hls_ap_rst] \\
    [get_bd_pins neuron_step_v1_0/ap_rst]
'''
new_block = '''# Clock/reset boundary. The K26 PS reports its realizable PL0 frequency as
# approximately 100 MHz (99,999,001 Hz with this board preset). Module Reference
# clock metadata is therefore allowed to inherit the propagated PS value instead
# of forcing an exact 100,000,000-Hz property.
#
# Synchronize the active-low PS fabric reset with proc_sys_reset. Its active-low
# peripheral_aresetn drives the smoke sequencer; its active-high peripheral_reset
# drives the packaged HLS ap_rst. Both are synchronous to the same PL0 clock.
set ps_reset [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_m11_6]
set_property -dict [list CONFIG.C_EXT_RESET_HIGH {0}] $ps_reset
set const_one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_m11_6]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] $const_one
set const_zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_m11_6]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] $const_zero

connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] \\
    [get_bd_pins smoke_0/ap_clk] \\
    [get_bd_pins neuron_step_v1_0/ap_clk] \\
    [get_bd_pins vio_m11_6/clk] \\
    [get_bd_pins proc_sys_reset_m11_6/slowest_sync_clk]
connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_resetn0] \\
    [get_bd_pins proc_sys_reset_m11_6/ext_reset_in]
connect_bd_net [get_bd_pins const_one_m11_6/dout] \\
    [get_bd_pins proc_sys_reset_m11_6/dcm_locked]
connect_bd_net [get_bd_pins const_zero_m11_6/dout] \\
    [get_bd_pins proc_sys_reset_m11_6/aux_reset_in] \\
    [get_bd_pins proc_sys_reset_m11_6/mb_debug_sys_rst]
connect_bd_net [get_bd_pins proc_sys_reset_m11_6/peripheral_aresetn] \\
    [get_bd_pins smoke_0/pl_resetn0]
connect_bd_net [get_bd_pins proc_sys_reset_m11_6/peripheral_reset] \\
    [get_bd_pins neuron_step_v1_0/ap_rst]
puts "M11.6 synchronized reset boundary: smoke=peripheral_aresetn HLS=peripheral_reset"
'''
if old_block not in text:
    raise SystemExit('old clock/reset block not found')
text = text.replace(old_block, new_block, 1)
tcl_path.write_text(text, encoding='utf-8')

test = test_path.read_text(encoding='utf-8')
needle = '''    assert "module m11_6_smoke_controller_bd_v1" in wrapper
    assert "m11_6_smoke_controller_v1 smoke_i" in wrapper
'''
replacement = '''    assert "module m11_6_smoke_controller_bd_v1" in wrapper
    assert "m11_6_smoke_controller_v1 smoke_i" in wrapper
    assert "FREQ_HZ 100000000" not in wrapper
    assert "ASSOCIATED_RESET pl_resetn0" in wrapper
    assert "POLARITY ACTIVE_LOW" in wrapper
'''
if needle not in test:
    raise SystemExit('wrapper source-guard anchor not found')
test = test.replace(needle, replacement, 1)

needle2 = '''    assert "xilinx.com:ip:vio:3.0" in text
    assert "connect_named_pair smoke_start" in text
'''
replacement2 = '''    assert "xilinx.com:ip:vio:3.0" in text
    assert "xilinx.com:ip:proc_sys_reset:5.0" in text
    assert "CONFIG.C_EXT_RESET_HIGH {0}" in text
    assert "proc_sys_reset_m11_6/slowest_sync_clk" in text
    assert "proc_sys_reset_m11_6/ext_reset_in" in text
    assert "proc_sys_reset_m11_6/peripheral_aresetn" in text
    assert "proc_sys_reset_m11_6/peripheral_reset" in text
    assert "[get_bd_pins smoke_0/hls_ap_rst]" not in text
    assert "M11.6 synchronized reset boundary:" in text
    assert "connect_named_pair smoke_start" in text
'''
if needle2 not in test:
    raise SystemExit('project source-guard anchor not found')
test = test.replace(needle2, replacement2, 1)
test_path.write_text(test, encoding='utf-8')
