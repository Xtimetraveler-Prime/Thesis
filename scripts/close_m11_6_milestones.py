from pathlib import Path
import re

path = Path("MILESTONES.md")
text = path.read_text(encoding="utf-8")

# Summary row.
old = "| M11 | Implement first FPGA neuron/core datapath | In progress | 2026-08-20 | — |"
new = "| M11 | Implement first FPGA neuron/core datapath | Complete | 2026-08-20 | 2026-08-27 |"
if text.count(old) != 1:
    raise RuntimeError(f"expected one M11 summary row, found {text.count(old)}")
text = text.replace(old, new, 1)

# M11 parent milestone status and completion note.
old = """## M11 — Implement first FPGA neuron/core datapath

**Status:** In progress  
**Started:** 2026-08-20  
**Repository evidence:** `main` through M11.5.5; branch `agent/m11-6-bitstream-hardware-smoke` for M11.6

### Goal
"""
new = """## M11 — Implement first FPGA neuron/core datapath

**Status:** Complete  
**Started:** 2026-08-20  
**Completed:** 2026-08-27  
**Repository evidence:** `main` through M11.5.5; branch `agent/m11-6-bitstream-hardware-smoke` for M11.6 and final physical closure

### Goal
"""
if text.count(old) != 1:
    raise RuntimeError("M11 status block not found exactly once")
text = text.replace(old, new, 1)

anchor = """M11 and later FPGA-development work standardize on AMD Vitis 2025.2 and AMD Vivado 2025.2. The work is split into six ordered sub-milestones. Each stage adds a stronger hardware-specific verification boundary before the next layer is introduced.

---
"""
replacement = """M11 and later FPGA-development work standardize on AMD Vitis 2025.2 and AMD Vivado 2025.2. The work is split into six ordered sub-milestones. Each stage adds a stronger hardware-specific verification boundary before the next layer is introduced.

### Completion outcome

All six M11 sub-milestones are complete. The work progressed from a single frozen M10 neuron transition in HLS, through Python/HLS differential verification, HLS synthesis/cosimulation and IP packaging, into finite memories, packed-M08 synapse traversal, recurrent routing, trace-observable whole-core integration, routed K26 implementation, and finally a physical four-tick JTAG/VIO smoke on the KV260. The physical run completed with `done=1`, `pass=1`, `fail_code=00`, `tick=4`, and `core_fault=00`. M11 therefore hands a physically executed, timing-clean first FPGA computational core to M12 for broader Python-versus-RTL and Python-versus-FPGA trace validation.

---
"""
if text.count(anchor) != 1:
    raise RuntimeError("M11 implementation-strategy anchor not found exactly once")
text = text.replace(anchor, replacement, 1)

section = r"### M11\.6 — Generate first integrated bitstream and perform hardware smoke checks\n.*?\n---\n\n## M12 — Validate FPGA against Python golden model"
new_section = r"""### M11.6 — Generate first integrated bitstream and perform hardware smoke checks

**Status:** Complete  
**Started:** 2026-08-25  
**Completed:** 2026-08-27  
**Repository evidence:** branch `agent/m11-6-bitstream-hardware-smoke`; physical closure on 2026-08-27

### Goal

Produce the first routed, timing-clean, loadable FPGA image containing the complete M11 core and prove through JTAG/VIO that its control, reset, computational, recurrent-routing, and debug boundaries execute correctly on the physical K26.

### Final implementation approach

- Keep the complete M11.5 computational RTL and packaged `neuron_step_v1` HLS IP behaviorally unchanged throughout physical-shell debugging.
- Use the Zynq UltraScale+ PS only as the source of `pl_clk0`; do not depend on software-managed `pl_resetn0` for the smoke domain.
- Drive a local active-low reset command from VIO into `proc_sys_reset`. Use synchronized `peripheral_aresetn` for the smoke controller and synchronized active-high `peripheral_reset` for packaged HLS `ap_rst`.
- Keep a reset-independent heartbeat on `pl_clk0` so stopped-clock failures can be separated from reset/control failures.
- Expose `reset_released` and sticky `start_seen` diagnostics through VIO so the physical reset and start boundaries can be proven directly rather than inferred from all-zero core state.
- Reuse the Python-golden M11.5.4 four-tick recurrent chain as the autonomous on-FPGA smoke workload.
- Have the sequencer preload packed M08 weight/config/route memories, issue architectural reset, execute four ticks, and compare committed state, spikes, recurrent counts/bank selection, and recurrent event data against generated expectations.
- Generate `.bit`, `.ltx`, routed `.dcp`, and `.xsa` artifacts from the source-controlled Vivado 2025.2 flow, and accept implementation only with nonnegative routed setup/hold slack, zero implementation DRC errors, and every tracked K26 resource class within capacity.

### Completion gates

- [x] Define carrier-independent PS-clock + VIO physical shell.
- [x] Add autonomous packed-M08 + real-HLS + recurrent smoke sequencer.
- [x] Add source-controlled implementation/bitstream/reporting flow.
- [x] Add source-controlled VIO programming/smoke flow.
- [x] Add focused M11.6 source-regression guards.
- [x] Independently rerun the focused M11.6 source guards after shell revisions.
- [x] Independently rerun the complete Python regression suite after the final M11.6 shell changes; the run reached 100% with zero failures.
- [x] Regenerate the final shell through Vivado synthesis, placement, routing, DRC, and bitstream generation.
- [x] Confirm nonnegative routed WNS and WHS for the final shell.
- [x] Confirm final implemented resource capacity for the final shell.
- [x] Generate the final `.bit`, `.ltx`, routed `.dcp`, and `.xsa` through the accepted routed-bitstream flow.
- [x] Program the physical K26 image through JTAG after unloading the active stock Kria PL application.
- [x] Confirm the physical `pl_clk0` heartbeat advances through VIO.
- [x] Confirm synchronized local-reset release with `reset_released=1`.
- [x] Confirm physical start delivery with `start_seen=1`.
- [x] Confirm autonomous four-tick physical completion with `done=1`, `pass=1`, `fail_code=00`, `tick=4`, and `core_fault=00`.
- [x] Record final evidence and mark M11.6 and M11 complete.

### Bring-up and debugging record

M11.6 required several physical-shell iterations. The failures were useful because each revision added enough observability to turn an ambiguous all-zero board result into a specific root cause. The computational M11.5 core was intentionally kept unchanged while the board/reset/debug shell was isolated.

#### 1. First routed image implemented successfully but the physical smoke stayed all zero

The first complete routed image programmed successfully through JTAG. Vivado selected `xck26_0`, reached startup status `HIGH`, discovered the matching VIO core, and committed `smoke_start`. Despite that, every clocked smoke output remained at reset values until timeout:

```text
busy=0 done=0 pass=0 fail_code=00 phase=00 tick=00000000
state0=0 state1=0 state2=0 spikes=0
recurrent_bank=0 recurrent_count=0
```

At this point programming and JTAG/VIO enumeration were proven, but the result could still have been caused by a stopped PL clock, a stuck reset, a lost start pulse, or a computational-core problem.

The stock `k26-starter-kits` PL application was also active during the earliest direct-JTAG attempts. Replacing that live PL image made the Linux/UART session unresponsive. The accepted procedure therefore unloads the stock application with `sudo xmutil unloadapp` before direct PL programming. This removes one avoidable software/PL ownership conflict, but it did not by itself fix the all-zero smoke.

#### 2. PS fabric-reset hypothesis was tested and rejected

A PS-side check showed `PL0_REF_CTRL=0x01010A00`, consistent with the PL0 clock generator being enabled at approximately 100 MHz. Because the original shell depended on the PS fabric reset, a one-time GPIO output-enable experiment was tried to determine whether `pl_resetn0` was simply not being driven by stock Linux. The smoke still remained all zero.

That experiment ruled out the simple "one missing PS GPIO output-enable bit" explanation. Manual `devmem`/PS-reset pokes were removed from the accepted bring-up path. The physical shell was redesigned so M11.6 reset ownership is local to the PL/VIO test rather than dependent on stock-Linux reset policy.

#### 3. Local-reset/heartbeat shell revision exposed a Vivado reset-polarity error before implementation

The first local-reset revision kept `pl_clk0`, added a reset-independent heartbeat, and attempted to drive the packaged HLS reset directly from the smoke wrapper. Vivado 2025.2 rejected the design during block-design validation: the HLS `ap_rst` pin is active-high and associated with `pl_clk0`, while the wrapper reset source was inferred as active-low/asynchronous. Vivado reported both an asynchronous-reset warning and a fatal `POLARITY` mismatch.

This was fixed structurally rather than suppressed. `proc_sys_reset` was restored as a local PL reset conditioner driven by the VIO reset command. Its synchronized active-low `peripheral_aresetn` drives the smoke controller, while synchronized active-high `peripheral_reset` drives HLS `ap_rst`. The PS fabric-reset output remains disabled, so the design still does not depend on `pl_resetn0`.

#### 4. Read-only reset-polarity warning was verified rather than guessed away

The revised `proc_sys_reset` flow initially attempted to set `CONFIG.C_EXT_RESET_HIGH {0}` explicitly. Vivado issued a critical warning because that parameter is read-only/tool-managed. Instead of assuming the polarity, the generated handoff and IP netlist were inspected. They showed the instantiated core bound to active-low external reset:

```text
C_EXT_RESET_HIGH=0
C_EXT_RESET_HIGH => '0'
```

The candidate bitstream was therefore accepted for diagnosis, and the unnecessary write to the read-only property was later removed so the final flow no longer emits that warning.

#### 5. Heartbeat and VIO output readback proved the clock and host control were working

The next physical run still timed out with all smoke state at zero, but the new heartbeat advanced. That was the first direct physical proof that `pl_clk0`, the debug hub, VIO clocking, and reset-independent PL logic were executing:

```text
M11.6 PL clock heartbeat advanced: 03e5c812 -> 04be4628
```

The hardware script was then strengthened to read VIO output registers back from the device. A subsequent run proved the commanded reset and start values were actually present in the VIO hardware:

```text
smoke_resetn readback = 1
smoke_start readback  = 1 while asserted
smoke_start readback  = 0 after deassertion
```

The core still stayed at phase/tick zero. This eliminated stopped `pl_clk0`, failed JTAG programming, and host-side VIO `set/commit` failures. The remaining uncertainty was now specifically downstream of the VIO outputs.

#### 6. Live-Linux instability was characterized as a separate platform-integration issue

During direct-JTAG full-PL replacement, PuTTY and SSH became unusable. Kernel output showed repeated `mmc1: sdhci: Timeout waiting for hardware interrupt` diagnostics and `systemd-journald` blocked for more than 122 seconds. The kernel remained alive enough to print diagnostics, but the stock Linux storage/runtime environment was no longer healthy after its expected PL image had been replaced.

This is recorded as a real platform-integration limitation, not hidden as a successful Linux coexistence result. M11.6 does not require the stock Kria Linux image to remain operational after an out-of-band JTAG replacement of its PL design; it requires the physical FPGA core itself to program and pass its JTAG/VIO smoke. Future software-managed deployment should use an FPGA-manager/device-tree/platform flow appropriate for Linux coexistence rather than treating direct JTAG replacement as a production loading mechanism.

#### 7. U-Boot isolation experiment did not provide a usable debug environment

To remove Linux from the equation, autoboot was interrupted at `ZynqMP>`. The bitstream still programmed, but Vivado could not detect the debug hub/VIO. A read of `PL0_REF_CTRL` still returned `0x01010A00`, showing that the clock-control register alone was not sufficient evidence that the complete PS-to-PL/debug environment was active at that boot stage.

A later attempt to read a PMU power-state register from U-Boot triggered a synchronous abort and CPU reset. No further PMU/PS register poking was used. The project returned to the normally booted PS solely as the known-good `pl_clk0` source and relied on explicit PL instrumentation instead of opaque PS-state inference.

#### 8. `reset_released` and `start_seen` instrumentation isolated the stuck-reset boundary

Two physical witnesses were added:

- `reset_released`: direct observation of `proc_sys_reset/peripheral_aresetn`;
- `start_seen`: a reset-independent sticky bit proving that `smoke_start` reached the smoke-module boundary.

The first instrumented run showed:

```text
reset_released=0 start_seen=0   # while reset intentionally asserted
heartbeat advanced              # PL clock proven alive
VIO smoke_resetn readback=1     # reset-release command reached VIO
reset_released=0                # synchronized smoke domain never released
```

The script stopped immediately at this boundary instead of waiting for a misleading core timeout. That result proved the failure was inside `proc_sys_reset` configuration/wiring and not in the smoke FSM or M11.5 computational datapath.

#### 9. Root cause: unused active-low `aux_reset_in` was tied permanently active

Inspection of the generated `proc_sys_reset` instance showed:

```text
C_AUX_RESET_HIGH=0
```

Therefore `aux_reset_in` is active-low. The block design had tied this unused input to constant `0`, which asserted auxiliary reset continuously. This held `peripheral_aresetn` low forever regardless of the VIO external-reset command. It exactly explains every prior combination of "heartbeat works, VIO commands read back correctly, core remains all zero."

The final fix is intentionally small and local to the physical shell:

```text
dcm_locked       = 1
aux_reset_in     = 1   # inactive for active-low auxiliary reset
mb_debug_sys_rst = 0
```

No M11.5 computational state machine, packed-M08 datapath, HLS arithmetic, or recurrent-routing behavior changed.

#### 10. Final physical run crossed every diagnostic boundary and passed the autonomous workload

With `aux_reset_in` held inactive, the final board run proved each physical layer in order:

```text
M11.6 reset diagnostic before release: reset_released=0 start_seen=0
M11.6 PL clock heartbeat advanced: 03c61c0d -> 04831207
M11.6 local smoke reset released through VIO; output readback=1 reset_released=1
M11.6 smoke_start asserted through VIO; output readback=1 start_seen=1
M11.6 smoke_start pulse committed through VIO; final output readback=0
M11.6 VIO status: busy=0 done=1 pass=1 fail_code=00 phase=00 tick=00000004 core_fault=00
M11.6 physical VIO smoke passed: tick=00000004, fail_code=00
```

The final `phase=00` is not a reset failure: after a successful self-test the sequencer returns/settles to its idle reporting state while sticky `done/pass` remain asserted and architectural tick remains `4`. The decisive completion outputs are `done=1`, `pass=1`, `fail_code=00`, `tick=4`, and `core_fault=00` together with the preceding `reset_released=1` and `start_seen=1` witnesses.

The outer Bash wrapper initially printed one false-negative error after this successful Vivado run because it searched for the old exact reset-message punctuation and did not account for the newly appended diagnostic suffix. The wrapper was changed to match stable message prefixes. No bitstream rerun was required because the underlying Vivado/JTAG execution had already passed.

### Final implementation evidence

The final aux-reset-fix shell was rebuilt through the source-controlled Vivado 2025.2 implementation flow. Routed setup and hold timing both pass:

```text
M11.6 routed timing check passed: WNS=1.480 ns, WHS=0.012 ns
```

Final implemented resource capacity passes comfortably on `xck26-sfvc784-2LV-c`:

```text
M11.6 implementation resource check passed: CLB_LUT=2766/117120, CLB_REG=3302/234240, BRAM_TILE<=13/144 (RAMB36=9, RAMB18=7), DSP=2/1248, URAM=0/64
```

The routed artifact flow completed successfully:

```text
M11.6 routed bitstream flow completed successfully.
```

The complete Python regression suite was rerun from the final branch state and reached 100% with zero failures. No exact final test count is recorded because the captured quiet-mode output reported progress to 100% without a numeric summary line.

### Why M11.6 passes

M11.6 is accepted because the final evidence closes every completion boundary defined for this milestone:

1. **Reproducible implementation** — the complete M11 core is generated by source-controlled Vivado 2025.2 scripts for the exact K26 part.
2. **Routed timing closure** — final routed setup and hold slack are both positive (`WNS=1.480 ns`, `WHS=0.012 ns`).
3. **Resource closure** — LUT, register, BRAM, DSP, and URAM usage all remain well below device capacity.
4. **Physical clock proof** — the reset-independent heartbeat advances on the programmed board.
5. **Physical reset proof** — `reset_released` transitions from `0` while asserted to `1` after the VIO release command.
6. **Physical command proof** — VIO output readback proves the start pulse is commanded and sticky `start_seen=1` proves it reaches the smoke-module boundary.
7. **Real computational execution** — the autonomous packed-M08 + real-HLS + recurrent core advances the architectural tick to `4`.
8. **On-FPGA self-check success** — the workload finishes with `done=1`, `pass=1`, `fail_code=00`, and `core_fault=00`, meaning its generated Python-golden expectations were satisfied.
9. **Regression preservation** — the complete Python suite still passes after the final shell changes.
10. **Failure modes understood rather than masked** — the earlier all-zero behavior is explained by a specific active-low auxiliary-reset wiring bug, and the Linux hang is separately documented as a stock-platform coexistence issue rather than being conflated with FPGA computational correctness.

The remaining Linux coexistence problem does not block M11.6 because this milestone's loading/control boundary is explicitly direct JTAG/VIO hardware bring-up, not a production Linux FPGA-manager integration. That software/platform integration concern is a handoff item for later deployment/validation work.

### Detailed design record

See `Neuromorphic Digital Twin/docs/M11_6_BITSTREAM_HARDWARE_SMOKE.md` for the physical shell, smoke sequence, failure codes, implementation gate, programming flow, and M12 handoff.

---

## M12 — Validate FPGA against Python golden model"""

text, count = re.subn(section, new_section, text, flags=re.S)
if count != 1:
    raise RuntimeError(f"expected one M11.6 section replacement, found {count}")

path.write_text(text, encoding="utf-8")
print("M11/M11.6 milestone closure text updated.")
