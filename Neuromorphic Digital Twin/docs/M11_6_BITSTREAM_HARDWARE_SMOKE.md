# M11.6 — Integrated Bitstream and Physical-Board Smoke

**Status:** In progress  
**Started:** 2026-08-25  
**Repository evidence:** branch `agent/m11-6-bitstream-hardware-smoke`

## Goal

Take the behaviorally complete, trace-observable M11.5 core through placement and routing, generate the first loadable K26 bitstream, program the physical device, and prove that the integrated core can be controlled and observed on hardware without relaxing the frozen M10 behavior.

M11.6 is a hardware bring-up milestone. Exact broad Python-versus-physical-FPGA trace conformance remains M12; this milestone requires a deliberately small but decisive physical smoke that traverses the same real memories, HLS neuron datapath, recurrent queues, and commit boundary already validated in simulation.

## Physical shell

The M11.6 bitstream deliberately avoids carrier-card-specific PL pins.

```text
K26 Zynq UltraScale+ PS
        │
        └── pl_clk0 (~100 MHz PL clock)
                │
                ├── reset-independent heartbeat counter -> VIO
                │
                v
      M11.6 autonomous smoke sequencer
                ↑
        VIO smoke_resetn
                │
                ├── packed M08 memories
                ├── exact signed-64 Phase B
                ├── packaged neuron_step_v1 HLS IP
                ├── recurrent route CSR / double buffer
                └── post-commit debug reads
                │
                v
          VIO over JTAG
```

The Zynq UltraScale+ processing-system block supplies only `pl_clk0` to the JTAG smoke shell. DDR and fixed-IO remain dedicated PS/SOM resources, and M11.6 adds no carrier-card PL `PACKAGE_PIN` assignments. The physical smoke no longer depends on software-managed `pl_resetn0`: VIO supplies the active-low local reset command to `proc_sys_reset`, whose synchronized `peripheral_aresetn` drives the smoke controller and synchronized active-high `peripheral_reset` drives packaged HLS `ap_rst`.

A reset-independent 32-bit heartbeat counter runs directly from `pl_clk0` and is exposed through VIO. The hardware script samples it twice before reset release and refuses to start the workload unless the value changes. Two additional physical witnesses isolate the control boundary: `reset_released` observes synchronized `proc_sys_reset/peripheral_aresetn`, and reset-independent sticky `start_seen` records whether the physical `smoke_start` net reached the module boundary. This separates stopped PL clock, reset-release failure, start-delivery failure, and actual smoke-FSM/datapath failure. VIO output probes supply `smoke_start` and `smoke_resetn`; input probes expose heartbeat/reset/start diagnostics plus busy/done/pass, failure code, sequencer phase, committed tick, core fault code, all three smoke-neuron state words, spike vector, and recurrent bank/count.

## Autonomous physical smoke

The physical smoke reuses the previously frozen M11.5.4 Python-golden four-tick recurrent chain instead of inventing a new hardware-only expected result.

The smoke sequencer regenerates and synthesizes `generated_m11_5_4_integrated_vectors.svh` from:

```text
examples/generate_m11_5_4_integrated_vectors.py
```

The intended chain is therefore unchanged:

```text
external axon 0 -> neuron 0 -> recurrent axon 1 -> neuron 1
                                  |
                                  +-> neuron 1 -> recurrent axon 2 -> neuron 2
```

Expected spike vectors by algorithmic tick:

```text
(1,0,0)
(0,1,0)
(0,0,1)
(0,0,0)
```

Expected consumed recurrent events:

```text
()
(1,)
(2,)
()
```

The on-FPGA sequencer performs the following operations after one VIO start pulse:

1. Writes the three packed neuron configuration words and initial states.
2. Writes the M08 format table, synapse words, and axon CSR row pointers.
3. Writes the recurrent route CSR rows and route targets.
4. Issues architectural core reset and checks tick 0 with an empty recurrent bank.
5. Executes all four complete recurrent ticks.
6. After every Phase-F commit, verifies committed tick, consumed/routed recurrent counts, current-bank selector/count, every neuron state word, and every spike bit.
7. When the current recurrent bank is nonempty, reads event zero through the real recurrent debug port and checks the expected routed axon.
8. Requires both physical recurrent bank counts to be empty after the final tick.
9. Raises `smoke_pass` only if every comparison succeeds; otherwise it exposes a stable failure code and sequencer phase.

A watchdog converts reset/tick/debug hangs into explicit smoke failures rather than leaving a board test waiting indefinitely.

## M11.6 implementation gate

`rtl/core_v1/run_m11_6_bitstream.sh` recreates the complete project in Vivado 2025.2 for:

```text
xck26-sfvc784-2LV-c
```

The flow:

1. Requires the previously packaged M11.4 `neuromorphic-twin.org:hls:neuron_step_v1:1.0` IP.
2. Stages RTL under a no-space `/tmp` path.
3. Regenerates the M11.5.4 recurrent smoke vectors from Python.
4. Builds a block design containing the Zynq UltraScale+ PS PL0 clock source, the autonomous smoke module with reset-independent heartbeat, the real packaged HLS IP, and one VIO core.
5. Runs synthesis and implementation through `write_bitstream`.
6. Opens the routed design and records implementation utilization, RAM mapping, route status, DRC, clocks, setup/hold paths, methodology, and timing summary.
7. Requires both routed worst setup slack and routed worst hold slack to be nonnegative.
8. Rejects any implemented CLB-LUT, CLB-register, block-RAM-tile, DSP, or URAM capacity overflow.
9. Writes a routed DCP, `.bit`, `.ltx`, and hardware `.xsa` into the ignored M11.6 build directory.

The decisive bitstream markers are:

```text
M11.6 hardware-smoke block design validated successfully.
M11.6 implementation completed successfully.
M11.6 routed timing check passed: WNS=..., WHS=...
M11.6 bitstream generated successfully.
M11.6 implementation resource check passed: ...
M11.6 routed bitstream flow completed successfully.
```

M11.6 must not be marked complete from synthesis-only timing. The accepted bitstream must come from the routed design with nonnegative setup **and** hold slack.

## Physical programming and smoke gate

`rtl/core_v1/run_m11_6_hardware_smoke.sh` invokes Vivado Hardware Manager in batch mode. It:

1. Connects to the hardware server and opens the JTAG target.
2. Selects the single K26 device.
3. Programs `neuromorphic_twin_m11_6.bit` and associates `neuromorphic_twin_m11_6.ltx`.
4. Discovers the VIO and named smoke probes.
5. Holds `smoke_resetn=0`, samples the reset-independent heartbeat twice, and requires it to advance.
6. Releases `smoke_resetn=1` through VIO and allows the synchronized local reset to clear.
7. Pulses `smoke_start` using the VIO `OUTPUT_VALUE`/commit mechanism.
8. Polls the VIO until `smoke_done` or a bounded host timeout.
9. Prints the pass/failure code, sequencer phase, tick, core fault, final neuron states/spikes, and recurrent-bank status.
10. Requires `smoke_pass=1`.

Required physical markers are:

```text
M11.6 bitstream programmed successfully.
M11.6 PL clock heartbeat advanced: ... -> ...
M11.6 local smoke reset released through VIO.
M11.6 smoke_start pulse committed through VIO.
M11.6 physical VIO smoke passed: ...
M11.6 physical-board smoke completed successfully.
```

### Stock-Kria/Linux prerequisite and physical bring-up finding

The hardware smoke uses PS `pl_clk0`; therefore the K26 processing system must be alive and supplying that clock when the PL image is programmed. On the stock AMD Kria Linux image, the default `k26-starter-kits` PL application can already occupy slot 0. Before direct JTAG programming, unload that active application cleanly with `sudo xmutil unloadapp` and verify Linux remains responsive. Directly overwriting an active stock PL application during the first board attempts caused the UART/Linux session to become unresponsive.

The first programmed M11.6 image was accepted by JTAG and its VIO was discovered, but every clocked smoke signal remained zero. `PL0_REF_CTRL` read back as `0x01010A00`, showing the PL0 clock generator configured active, and a manual PS-GPIO output-enable experiment did not make the smoke advance. The final JTAG shell therefore removes the software-managed `pl_resetn0` dependency and adds the reset-independent heartbeat described above. Manual PS register pokes are not part of the accepted flow.

## Completion boundary

M11.6 is complete only when all of the following have independently passed on the final branch state:

- [ ] Focused M11.6 Python/source regression.
- [ ] Complete Python regression suite.
- [ ] Vivado 2025.2 block-design validation.
- [ ] Successful synthesis, placement, routing, and bitstream generation for `xck26-sfvc784-2LV-c`.
- [ ] Nonnegative routed setup slack.
- [ ] Nonnegative routed hold slack.
- [ ] No implementation DRC errors.
- [ ] All K26 physical resource classes remain within capacity.
- [ ] `.bit`, `.ltx`, routed `.dcp`, and `.xsa` artifacts are produced.
- [ ] Physical JTAG programming succeeds.
- [ ] Physical VIO start/control access succeeds.
- [ ] Autonomous four-tick packed-M08 + HLS + recurrent hardware smoke reports `smoke_pass=1`.
- [ ] Completion evidence is recorded in `MILESTONES.md` before M11 itself is marked complete.

## Scope handoff to M12

Passing M11.6 proves that the integrated core is implementable, routable, programmable, clocked, controllable, and observably executing a known recurrent workload on the physical K26. It does **not** replace M12. M12 will use the trace contract to run broader automated Python-versus-RTL and Python-versus-physical-FPGA comparisons and will report final behavioral, timing, resource, and throughput results for the thesis.
