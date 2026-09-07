from pathlib import Path

root = Path('Neuromorphic Digital Twin/rtl/core_v1')

# Module-reference wrapper: same VIO/HLS port surface as M12.2, new controller only.
wrapper = (root / 'm12_2_single_tick_capture_controller_bd_v1.v').read_text(encoding='utf-8')
wrapper = wrapper.replace('M12.2', 'M12.3')
wrapper = wrapper.replace('m12_2_single_tick_capture_controller_bd_v1', 'm12_3_multitick_capture_controller_bd_v1')
wrapper = wrapper.replace('m12_2_single_tick_capture_controller_v1', 'm12_3_multitick_capture_controller_v1')
(root / 'm12_3_multitick_capture_controller_bd_v1.v').write_text(wrapper, encoding='utf-8')

# Vivado project: preserve the proven K26 PS-clock/reset/VIO topology exactly.
project = (root / 'vivado' / 'create_m12_2_project.tcl').read_text(encoding='utf-8')
project = project.replace('M12.2', 'M12.3')
project = project.replace('m12_2', 'm12_3')
project = project.replace('m12_3_single_tick_capture_controller_bd_v1', 'm12_3_multitick_capture_controller_bd_v1')
project = project.replace('capture_m12_3_single_tick.tcl', 'capture_m12_3_multitick.tcl')
(root / 'vivado' / 'create_m12_3_project.tcl').write_text(project, encoding='utf-8')

# Bitstream runner: same toolchain and resource gates, new corpus/controller/artifacts.
runner = (root / 'run_m12_2_bitstream.sh').read_text(encoding='utf-8')
runner = runner.replace('M12.2', 'M12.3')
runner = runner.replace('M12_2', 'M12_3')
runner = runner.replace('m12_2', 'm12_3')
runner = runner.replace('m12_3_single_tick_capture_controller_v1.sv', 'm12_3_multitick_capture_controller_v1.sv')
runner = runner.replace('m12_3_single_tick_capture_controller_bd_v1.v', 'm12_3_multitick_capture_controller_bd_v1.v')
runner = runner.replace('generated_m12_3_single_tick_cases.svh', 'generated_m12_3_multitick_cases.svh')
runner = runner.replace('generate_m12_3_single_tick_corpus.py', 'generate_m12_3_multitick_corpus.py')
runner = runner.replace("printf 'M12.3 directed cases: 16\\n'", "printf 'M12.3 directed cases: 10\\n'\nprintf 'M12.3 directed committed ticks: 40\\n'")
runner = runner.replace(
    "if grep -Fq 'M12_3_EXPECTED' \"$CAPTURE_VECTORS\"; then\n    echo \"ERROR: generated M12.3 FPGA include contains forbidden golden-output arrays.\" >&2\n    exit 3\nfi",
    "if grep -Eq 'M12_3_EXPECTED|RECURRENT_SCHEDULE|RECURRENT_EVENTS' \"$CAPTURE_VECTORS\"; then\n    echo \"ERROR: generated M12.3 FPGA include contains forbidden golden/recurrent schedule arrays.\" >&2\n    exit 3\nfi",
)
(root / 'run_m12_3_bitstream.sh').write_text(runner, encoding='utf-8')

print('derived M12.3 wrapper/project/bitstream runner')
