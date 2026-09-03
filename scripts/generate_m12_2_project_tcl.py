from pathlib import Path

src = Path("Neuromorphic Digital Twin/rtl/core_v1/vivado/create_m12_1_3_project.tcl")
dst = Path("Neuromorphic Digital Twin/rtl/core_v1/vivado/create_m12_2_project.tcl")
text = src.read_text(encoding="utf-8")
text = text.replace("M12.1.3", "M12.2")
text = text.replace("m12_1_capture_controller_bd_v1", "m12_2_single_tick_capture_controller_bd_v1")
text = text.replace("m12_1_3", "m12_2")
text = text.replace("capture_m12_2_trace.tcl", "capture_m12_2_single_tick.tcl")
dst.write_text(text, encoding="utf-8")
