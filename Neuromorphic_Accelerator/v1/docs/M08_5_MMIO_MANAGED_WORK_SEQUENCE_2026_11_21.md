# M08.5 — AXI-Lite MMIO work-command sequencer with actual 75-command LIF regression (2026-11-21)

**Source-only increment** on the **same** branch `agent/neuromorphic-accelerator-v1-m08-matched-experiments`, draft/unmerged PR #95. The owner has reported full local verification of the *previous* AXI4-Lite control/neural increment; newly added work-command source requires its **own exact-HEAD** Icarus CI and independent owner local replay. The original accepted M08.4 KV260 bitstream/source hash and physical evidence directories remain immutable. **No hardware contact, programming, Linux driver, DMA allocation, DDR access, Vivado or physical reset/drain was performed.**

## Design delta and why it matters

Until now, the source `m08_m085_axil_neural_candidate.v` could grant the address window via a five-channel AXI4-Lite register interface but required separate **testbench-supplied** pins for page requests and compute dispatch. A Linux platform driver cannot use that as a complete host interface. This increment adds a **versioned (ABI v1.1), polled work-command ABI** to the *same* 32-bit AXI-Lite register aperture, opt-in only, while retaining all preexisting unmodified signed16 recurrent neural components and regression tests.

- `rtl/m08/m08_m085_work_command_sequencer.v`: synthesizable source-level finite-state machine with one-shot LOAD, DISPATCH and dirty SAVE requests, bank-state safety checks, timeout/sticky fault and monotonic completion counter. It does not expose a DDR address to the caller; the master address remains `frozen DMA base + 256*slot` from the seven-slot lease. A failed, untrusted, busy or malformed work write immediately embargoes new work; a fault cannot be cleared by a second command. Future controlled full reset is **not** a physical AXI drain.
- `rtl/m08/m08_m085_axil_control_candidate.v` now has `ENABLE_WORK_COMMANDS=0` by default (old standalone decoder tests and old `m08_m085_axil_neural_candidate.v` retain their original behavior), with opt-in work offsets decoded from exact 12-bit byte addresses, no alias of `0x100+...` to low offsets. Actual AW/W independent capture, WSTRB, B/R backpressure, and the core CAP/descriptor/GRANT/STOP ABI are unchanged. The bridge blocks new work on a partial AW or W write, a still-pending BRESP, and any sticky work fault.
- **New** `rtl/m08/m08_m085_axil_managed_neural_candidate.v` is an independently named synthesizable top with no external neural-page request/dispatch input pins. All LOAD/COMPUTE/SAVE commands originate from MMIO work registers and pass the same real lease fence to the unchanged original one-bank/signed16 LIF AXI neural shell. The DDR AXI4 ports are **unconnected to PS** in this source candidate.
- `rtl/m08/tb_m08_m085_axil_managed_neural_candidate.sv` + `tests/test_m08_m085_axil_managed_neural.py`: genuine Icarus 75 MMIO work-command sequence, with exactly one original five-edge M6EG load→dispatch→save and 24 original signed16 M6NF LOAD→DISPATCH→SAVE operations over four tick barriers. It performs all **512 independent M02/M03 numerical oracle checks**: 128 host-coalesced input-current checks and 384 actually computed PL neural state checks over **synthetic** seven-page DDR. The untouched comparison oracle is never sent to neural state. It verifies completed command count=75, 25 AXI writes/50 reads, full verified save readbacks and one-way source-simulated STOP/drain seal.
- `rtl/m08/tb_m08_m085_work_command_sequencer.sv` + `tests/test_m08_m085_work_command_sequencer.py`: real Icarus source test against 19 additional adverse scenarios, such as pregrant attempt, invalid slot/tick, M6EG nonzero tick, invalid commands, RO/partial/untrusted writes, compute before load, save before dirty, active-session mutation, owner/route stop, neural poison, completion/dispatch timeout, wrong bank logical ID and completed-save mismatch. This stand-alone work FSM TB supplies **synthetic neural status**; it is not the integrated neural parity test.

## Register ABI (byte offsets within a new, UNASSIGNED SoC aperture)

All registers below are 32-bit little-endian, aligned, with full write strobes only. External `csr_trusted`, `driver_bound_verified`, `control_route_verified` and `interconnect_drain_ack` remain synthetic inputs. They are **not** kernel authentication or a physical drain attestation.

| Byte offset | Operation | Meaning |
| --- | --- | --- |
| `0x00`, `0x04` | RO | Existing CAP `M085`; **ABI v1.1 `0x00010001` only when `ENABLE_WORK_COMMANDS=1`**. Legacy control-only endpoint remains **ABI v1.0 `0x00010000`**. Driver must read/reject incompatible versions before sending work commands. |
| `0x08`, `0x0c` | RO | Existing lease STATUS and synthetic external drain observations |
| `0x10..0x1c` | RW only before GRANT | Existing DMA base low/high, allocation length and generation. Only a future bound kernel driver's `dma_addr_t` may populate these. |
| `0x20` | WO | Existing `1=GRANT`, `2=STOP_AND_DRAIN` |
| `0x24` | RW while granted, idle | `WORK_SLOT` = neuron slot `0..5` or edge/config slot `6` |
| `0x28` | RW while granted, idle | `WORK_TICK` = `0..3`; edge slot 6 only allows tick 0 |
| `0x2c` | WO while granted, idle | `WORK_COMMAND` = `1=LOAD`, `2=DISPATCH`, `3=SAVE` |
| `0x30` | RO | `WORK_STATUS`: bit0 busy, bit1 sticky done since last command, bit2 sticky fault, bits `7:6` last operation code; remaining bits reserved |
| `0x34` | RO | `WORK_COMPLETIONS`: 32-bit incrementing number of completed work commands, **not** independently verified physical page bytes |

The Linux driver must serialize writes, read back the STATUS and completion counter, never issue a second command while BUSY, and quarantine on any SLVERR or sticky fault. A success BRESP for WORK_COMMAND only means **command accepted**, NOT that DDR read/write or neural compute completed. A success BRESP for GRANT only means **descriptor command accepted**, NOT that lease admission succeeded; driver must check status separately. WORK_STATUS completion is not an interrupt, not a DMA barrier, and not a bus quiescence proof. All work requires exact valid seven-page slot/tick, appropriate verified resident-bank phase/logical ID and active granted lease.

### Sequence for the original 32-neuron × 4-tick experiment (SOURCE SIMULATION)

1. Future **kernel driver** would verify correct bound platform/device/firmware/hardware identity and obtain `dma_addr_t` from its own `dma_alloc_coherent` allocation; these steps DO NOT EXIST yet. In the new RTL testbench only, set synthetic trusted/driver/control/drain pins and grant synthetic 4096B allocation at 0x1000, with usable interval exactly 1792B.
2. Stage `WORK_SLOT=6, WORK_TICK=0`, command `LOAD(1)`, poll bit1 DONE, verify command counter; command `DISPATCH(2)` to configure 5 recurrent edges; command `SAVE(3)` to preserve M6EG backing slot.
3. For each tick 0..3 and each neuron slot 0..5: set slot/tick in the AXI4-Lite work ABI, `LOAD(1)`, `DISPATCH(2)`, `SAVE(3)`, checking work status/counter after each; the original source fixture advances synthetic tick header and the original independent comparison-only M02/M03 oracle checks results **after** actual bank dirty SAVE and independent 256B readback.
4. Expect `(1+24)*3=75` work commands, 24 compute-bearing neuron dispatches, 25 256B loads +25 256B saves +25 independent 256B verification reads = **19,200 source-synthetic AXI bytes**, and 512 comparison-only original checks. STOP, observe **testbench-supplied** fresh low→high ACK, then one-way SEALED. Neither this ACK nor passed source test permits `dma_free_coherent` in physical hardware.

## Physical hardware still explicitly BLOCKED

The existing owner-verified KV260 SSH inventory showed `ZynqMP KV260 revB`, Linux `6.8.0-1036-xilinx`, `cma=800M`, stock-named active overlay and existing PS DMA drivers, but **no exact M08.5 bound PL driver** and no verified M08.5 DMA address translation. User independently ran `sha256sum -c` on the untouched original SSH evidence directory and reported **5/5 OK**; the assistant received and SHA-checked two of those original output files, not the full five files.

**Do not infer from this source integration** that we have protected kernel-only PS HPM0 MMIO (128→32 width), valid Linux device-tree/XSA/AFI, PL AXI128→PS HP0 physical DDR, real coherent DMA allocation, independent interconnect drain/isolation and late R/B proof, routed K26 Vivado 2025.2 utilization/WNS/WHS/DRC, a tested kernel module, safe bus reset or true measured speedups. The source `interconnect_drain_ack` is *still synthetic*. Unprivileged userspace MMIO is not an alternative.

**Next concrete increment:** Independent offline K26 PS/PL Vivado integration (HPM0 width converter → protected 32-bit AXI-Lite, PL AXI4 master → HP0 and appropriate clock/reset, no board programming), a precisely matched DT/bound platform-driver skeleton allocating coherent memory and a physically credible late-response drain/isolation protocol. Hardware programming/DDR access requires separate explicit owner authorization and new preserved evidence.

## Owner PC verification

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v python3 && command -v iverilog && command -v vvp
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_m085_work_command_sequencer.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_managed_neural.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_control_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_neural_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_lease.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

This does **not** use SSH or board access. Confirm the specific latest Git commit and actual Icarus execution without skips. Keep PR #95 draft/unmerged and leave historical accepted physical evidence untouched.
