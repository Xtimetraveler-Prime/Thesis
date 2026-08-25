from pathlib import Path

path = Path('Neuromorphic Digital Twin/rtl/core_v1/run_m11_6_bitstream.sh')
text = path.read_text(encoding='utf-8')

old_source = '''    "$SCRIPT_DIR/vivado/create_m11_6_project.tcl"\n    "$PROJECT_DIR/examples/generate_m11_5_4_integrated_vectors.py"\n)'''
new_source = '''    "$SCRIPT_DIR/vivado/create_m11_6_project.tcl"\n    "$SCRIPT_DIR/check_m11_6_resources.py"\n    "$PROJECT_DIR/examples/generate_m11_5_4_integrated_vectors.py"\n)'''
if old_source not in text:
    raise SystemExit('SOURCE_FILES insertion point not found')
text = text.replace(old_source, new_source, 1)

start = text.index('# Preserve the M11.5.5 physical-capacity gate after adding the PS/VIO smoke')
end_marker = '''print("M11.6 implementation resource check passed: " + ", ".join(summary))\nPY\n'''
end = text.index(end_marker, start) + len(end_marker)
replacement = '''# Preserve the M11.5.5 physical-capacity gate after adding the PS/VIO smoke\n# shell. The dedicated checker tolerates Vivado 2025.2 implemented-report\n# formatting where a literal `Block RAM Tile` row may be absent.\npython3 "$SCRIPT_DIR/check_m11_6_resources.py" \\\n    "$REPORT_DIR/utilization_impl.rpt" \\\n    "$REPORT_DIR/ram_utilization_impl.rpt"\n'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding='utf-8')

# Extend the static source guard so this regression cannot silently return.
test_path = Path('Neuromorphic Digital Twin/tests/test_m11_6_bitstream_sources.py')
test = test_path.read_text(encoding='utf-8')
old = '''    assert '("CLB LUTs", "CLB_LUT")' in text\n    assert '("Block RAM Tile", "BRAM_TILE")' in text\n    assert "M11.6 implementation resource check passed:" in text\n'''
new = '''    assert 'check_m11_6_resources.py' in text\n    assert '"$REPORT_DIR/utilization_impl.rpt"' in text\n    assert '"$REPORT_DIR/ram_utilization_impl.rpt"' in text\n'''
if old not in test:
    raise SystemExit('old M11.6 resource source guard not found')
test = test.replace(old, new, 1)
test_path.write_text(test, encoding='utf-8')
