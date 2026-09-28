# M11.4 Vivado Integration

**Status:** Complete  
**Completed:** 2026-08-24

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

M11.4 does **not** add neuron memories, synapse memories, the multi-neuron tick controller, recurrent routing, or host registers. Those are M11.5 work.

## What M11.4 added

### Vitis HLS IP packaging

`hls_package.cfg` adds a packaging-specific configuration on top of the already verified M11.3 source. It uses:

```ini
package.output.format=ip_catalog
package.output.syn=false
```

and freezes the project-specific IP identity:

```text
neuromorphic-twin.org:hls:neuron_step_v1:1.0
```

`run_m11_4.sh` performs a reproducible packaging flow that:

1. checks the Vitis/Vivado 2025.2 toolchain and exact K26 part;
2. stages the HLS source under a no-space `/tmp` path;
3. regenerates the deterministic M11.2 test-vector include;
4. runs a fresh HLS synthesis of the verified top;
5. runs `vitis-run --mode hls --package`;
6. preserves the packaged ZIP when produced;
7. copies the unpacked `impl/ip` result into an ignored local IP repository under `build/m11_4/ip_repo`;
8. invokes Vivado 2025.2 in batch mode to build the project/block design.

### Reproducible Vivado project generation

`vivado/create_m11_4_project.tcl` creates the real Vivado integration shell entirely from source-controlled Tcl. It:

- creates project `neuromorphic_twin_m11_4` for `xck26-sfvc784-2LV-c`;
- points `IP_REPO_PATHS` at the generated custom IP repository and rebuilds the IP catalog;
- checks that `neuromorphic-twin.org:hls:neuron_step_v1:1.0` is discoverable;
- creates block design `neuromorphic_twin_core`;
- instantiates the packaged HLS IP as `neuron_step_v1_0`;
- externalizes the complete HLS `ap_ctrl_hs` interface so `ap_start`, `ap_done`, `ap_idle`, and `ap_ready` stay grouped as one transaction-control boundary;
- externalizes the remaining unconnected clock/reset/data/result ports;
- validates and saves the block design;
- reports the external interface/scalar ports while the BD is open;
- generates block-design output products;
- creates and adds the HDL wrapper;
- updates compile order and closes the project cleanly.

The generated project is expected under:

```text
hls/core_v1/build/m11_4/vivado_project/
```

and is intentionally ignored by Git. The source-controlled reconstruction path is `vivado/create_m11_4_project.tcl` plus `run_m11_4.sh`.

## Tooling issues resolved during M11.4

Several Vivado-specific issues were discovered and fixed while making the flow reproducible:

1. A zero-argument `save_project` command caused the first project-generation run to fail after the BD had otherwise been created. The command was removed because `create_project` already creates and updates the requested project in place.
2. Manually overriding only `ap_start` produced an IP-Integrator warning because it is a member of the HLS `ap_ctrl` interface. The final flow externalizes the complete `ap_ctrl_hs` interface instead of breaking out a single member.
3. Port-reporting code originally called `get_bd_ports` after project-export helpers had changed the active IP-Integrator context. The final flow reports ports immediately after BD validation while the design is known to be open.
4. Generated `write_bd_tcl`/`write_project_tcl` snapshots were removed from the normative flow because they embedded build-local custom-IP paths and produced avoidable repository warnings. The checked-in Tcl file is the authoritative reconstruction source.

None of these fixes changes the verified M10/M11.3 neuron arithmetic or HLS datapath behavior; they are Vivado project/integration fixes only.

## Reproducible flow

From `hls/core_v1` after sourcing Vitis/Vivado 2025.2:

```bash
export HLS_PART='xck26-sfvc784-2LV-c'
bash run_m11_4.sh | tee m11_4_2025_2.log
```

For iterative Vivado-only retries after packaging has already succeeded, the project script can be invoked directly against the preserved IP repository:

```bash
IP_REPO_DIR="$PWD/build/m11_4/ip_repo"
VIVADO_PROJECT_DIR="$PWD/build/m11_4/vivado_project"

vivado -mode batch \
  -source "$PWD/vivado/create_m11_4_project.tcl" \
  -tclargs \
  "$IP_REPO_DIR" \
  "$VIVADO_PROJECT_DIR" \
  "xck26-sfvc784-2LV-c" \
  "neuromorphic-twin.org:hls:neuron_step_v1:1.0"
```

## Completion evidence

The independent M11.4 vendor run on 2026-08-24 successfully reached and completed both packaging and project integration. Vivado:

- loaded the custom IP repository;
- found the expected VLNV;
- instantiated `neuron_step_v1_0`;
- validated `neuromorphic_twin_core`;
- generated Verilog/VHDL block-design products;
- generated the HDL wrapper and hardware handoff files;
- created the target project file.

After the final Tcl fixes, the following verification commands were independently run and passed:

```bash
test -f build/m11_4/vivado_project/neuromorphic_twin_m11_4.xpr \
  && echo "XPR: PASS"

find build/m11_4/vivado_project \
  -type f -name 'neuromorphic_twin_core.bd' -print
```

This is sufficient to close M11.4: the M11.3-verified HLS RTL is now packaged as a custom Vivado IP, discoverable through the Vivado IP catalog, instantiated in a validated K26-targeted block design, wrapped as HDL, and reconstructible from source-controlled scripts.

## Why the HLS ports remain external in M11.4

At this stage the purpose is to prove that the verified HLS RTL can be packaged, discovered by Vivado, instantiated in IP Integrator, and preserved in a deterministic system project without yet inventing the final core controller.

The `ap_ctrl_hs` members (`ap_start`, `ap_done`, `ap_idle`, and `ap_ready`) remain grouped as one block-design interface. Externalizing that interface plus the remaining scalar HLS ports keeps the implementation boundary visible and prevents M11.4 from prematurely choosing the M11.5 memory/control architecture.

M11.5 replaces these temporary top-level connections with neuron state/configuration storage, the M08 synapse-storage path, deterministic tick scheduling, recurrent routing, and observability/control logic.

No board pin constraints or bitstream generation are part of M11.4. Physical clock/reset sources, implementation timing closure, and board programming remain later M11 work.
