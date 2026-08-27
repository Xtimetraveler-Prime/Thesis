from pathlib import Path

ROOT = Path('.')
PROJECT = ROOT / 'Neuromorphic Digital Twin' / 'rtl' / 'core_v1' / 'vivado' / 'create_m11_6_project.tcl'
TESTS = ROOT / 'Neuromorphic Digital Twin' / 'tests' / 'test_m11_6_bitstream_sources.py'
DOC = ROOT / 'Neuromorphic Digital Twin' / 'docs' / 'M11_6_BITSTREAM_HARDWARE_SMOKE.md'


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{path}: expected exactly one occurrence, found {count}: {old!r}')
    path.write_text(text.replace(old, new, 1))

old_wiring = '''connect_bd_net [get_bd_pins const_one_m11_6/dout] \\
    [get_bd_pins proc_sys_reset_m11_6/dcm_locked]
connect_bd_net [get_bd_pins const_zero_m11_6/dout] \\
    [get_bd_pins proc_sys_reset_m11_6/aux_reset_in] \\
    [get_bd_pins proc_sys_reset_m11_6/mb_debug_sys_rst]
'''
new_wiring = '''# proc_sys_reset v5.0 on this K26/Vivado build instantiates both external and
# auxiliary reset inputs active-low. Keep the unused auxiliary reset explicitly
# inactive (1); tying it low would hold every generated reset asserted forever.
connect_bd_net [get_bd_pins const_one_m11_6/dout] \\
    [get_bd_pins proc_sys_reset_m11_6/dcm_locked] \\
    [get_bd_pins proc_sys_reset_m11_6/aux_reset_in]
connect_bd_net [get_bd_pins const_zero_m11_6/dout] \\
    [get_bd_pins proc_sys_reset_m11_6/mb_debug_sys_rst]
'''
replace_once(PROJECT, old_wiring, new_wiring)

text = TESTS.read_text()
needle = '    assert "proc_sys_reset_m11_6/peripheral_reset" in text\n'
insert = (
    '    assert "proc_sys_reset_m11_6/peripheral_reset" in text\n'
    '    assert "[get_bd_pins proc_sys_reset_m11_6/dcm_locked] \\\\\\n    [get_bd_pins proc_sys_reset_m11_6/aux_reset_in]" in text\n'
    '    assert "[get_bd_pins const_zero_m11_6/dout] \\\\\\n    [get_bd_pins proc_sys_reset_m11_6/mb_debug_sys_rst]" in text\n'
)
if needle not in text:
    raise RuntimeError('test insertion point not found')
text = text.replace(needle, insert, 1)
TESTS.write_text(text)

old_doc = 'The Zynq UltraScale+ processing-system block supplies only `pl_clk0` to the JTAG smoke shell. DDR and fixed-IO remain dedicated PS/SOM resources, and M11.6 adds no carrier-card PL `PACKAGE_PIN` assignments. The physical smoke no longer depends on software-managed `pl_resetn0`: VIO supplies the active-low local reset command to `proc_sys_reset`, whose synchronized `peripheral_aresetn` drives the smoke controller and synchronized active-high `peripheral_reset` drives packaged HLS `ap_rst`.\n'
new_doc = 'The Zynq UltraScale+ processing-system block supplies only `pl_clk0` to the JTAG smoke shell. DDR and fixed-IO remain dedicated PS/SOM resources, and M11.6 adds no carrier-card PL `PACKAGE_PIN` assignments. The physical smoke no longer depends on software-managed `pl_resetn0`: VIO supplies the active-low local reset command to `proc_sys_reset`, whose synchronized `peripheral_aresetn` drives the smoke controller and synchronized active-high `peripheral_reset` drives packaged HLS `ap_rst`. The unused active-low `aux_reset_in` is tied high (inactive); `mb_debug_sys_rst` is tied low.\n'
replace_once(DOC, old_doc, new_doc)

print('Patched M11.6 proc_sys_reset auxiliary reset to its inactive high level.')
