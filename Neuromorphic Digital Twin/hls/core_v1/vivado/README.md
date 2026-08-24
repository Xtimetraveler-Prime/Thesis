# M11.4 Vivado Integration

M11.4 takes the M11.3-verified `neuron_step_v1` HLS top and turns it into a reusable Vivado IP plus a reproducible Vivado 2025.2 project/block design.

## Frozen M11.4 boundary

The packaged IP uses:

```text
VLNV:        neuromorphic-twin.org:hls:neuron_step_v1:1.0
FPGA part:   xck26-sfvc784-2LV-c
HLS clock:   10 ns (100 MHz baseline)
Toolchain:   Vitis/Vivado 2025.2
```

The HLS control/data interface is unchanged from the completed M11.3 design:

- `ap_ctrl_hs` transaction control;
- scalar `ap_none` inputs;
- `ap_vld` result outputs;
- signed 24-bit current/voltage state;
- unsigned 16-bit refractory state;
- signed 64-bit already-accumulated synaptic input boundary.

M11.4 does **not** add neuron memories, synapse memories, the multi-neuron tick controller, recurrent routing, or host registers. Those remain M11.5 work.

## Reproducible flow

From `hls/core_v1` after sourcing Vitis/Vivado 2025.2:

```bash
export HLS_PART='xck26-sfvc784-2LV-c'
bash run_m11_4.sh | tee m11_4_2025_2.log
```

The wrapper:

1. stages the HLS component under `/tmp` to avoid the repository path space;
2. synthesizes the verified top with the frozen 100 MHz HLS baseline;
3. runs `vitis-run --mode hls --package` with `package.output.format=ip_catalog`;
4. copies the unzipped packaged IP and ZIP into ignored `build/m11_4/` evidence;
5. launches Vivado 2025.2 in batch mode;
6. registers the packaged IP repository and rebuilds the IP catalog;
7. creates project `neuromorphic_twin_m11_4` for `xck26-sfvc784-2LV-c`;
8. creates block design `neuromorphic_twin_core`;
9. instantiates `neuromorphic-twin.org:hls:neuron_step_v1:1.0` as `neuron_step_v1_0`;
10. externalizes every unconnected HLS clock/reset/control/data pin;
11. validates the block design, generates output products, creates the HDL wrapper, and saves project/BD recreation Tcl.

The generated project is expected under:

```text
hls/core_v1/build/m11_4/vivado_project/
```

and is intentionally ignored by Git. The source-controlled reconstruction path is `vivado/create_m11_4_project.tcl` plus `run_m11_4.sh`.

## Why all HLS pins are external in M11.4

At this stage the purpose is to prove that the verified HLS RTL can be packaged, discovered by Vivado, instantiated in IP Integrator, and preserved in a deterministic system project without yet inventing the final core controller.

Externalizing the current HLS pins keeps the interface visible and prevents M11.4 from prematurely choosing the M11.5 memory/control architecture. M11.5 will replace these temporary top-level connections with neuron state/configuration memories, the M08 synapse-storage path, deterministic tick scheduling, recurrent routing, and observability/control logic.

No board pin constraints or bitstream generation are part of M11.4. Physical clock/reset sources, implementation timing closure, and board programming remain later M11 work.
