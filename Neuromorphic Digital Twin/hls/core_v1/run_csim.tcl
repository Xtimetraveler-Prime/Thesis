# M11.1 pre-synthesis C simulation.
# Compatible with the Vitis HLS 2023.2 project/Tcl flow used by this project.

set script_dir [file dirname [file normalize [info script]]]
set project_dir [file join $script_dir build m11_1_csim]

open_project -reset $project_dir
set_top neuron_step_v1

add_files [file join $script_dir src neuron_step_v1.cpp] \
    -cflags "-I[file join $script_dir include]"
add_files -tb [file join $script_dir tb test_neuron_step_v1.cpp] \
    -cflags "-I[file join $script_dir include]"

open_solution -reset solution1 -flow_target vivado

# C simulation is intentionally run before selecting a physical FPGA part.
# M11.3 will add the target part and clock when synthesis begins.
csim_design -clean

close_project
exit
