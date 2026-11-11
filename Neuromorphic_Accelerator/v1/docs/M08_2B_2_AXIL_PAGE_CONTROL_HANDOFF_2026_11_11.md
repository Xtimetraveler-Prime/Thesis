# M08.2b.2 — PS-facing 32-bit AXI4-Lite signed16 page staging adapter

**Status (2026-11-11):** First-party source code and Icarus tests developed. **Do not mark native Vivado/physical gate complete:** no connected PS→page BD, route, WNS/WHS, bitstream, Linux MMIO, DDR, DMA or complete neural inference has been performed. Source-only acceptance requires a real Icarus HDL PASS and exact-HEAD M01–M08 tests.

## Why this implementation differs from the Loihi v2 digital twin

The Loihi v2 P08.4.3a/b accepted K26 host-owned retained full-context memory via VIO/JTAG, with logical backing, resident core banks and an HLS engine; that is an excellent **exclusive host/compute ownership** precedent. The M08 signed16 accelerator instead starts with an **M06 16-neuron × 16-byte = 256-byte state page**, not full Loihi signed24 context banks. We retain the Loihi ownership principles but use a **PS AXI4-Lite memory/control interface** instead of cloning its P08 VIO interface. [Loihi evidence crosswalk](M08_3_LOIHI_KV260_MEMORY_OWNERSHIP_REUSE_2026_11_11.md).

M08.2b.1 previously supplied `rtl/m08/m08_host_staged_page_bank.sv`: single resident 64×32-bit page, per-byte write coverage and per-word host readback coverage, exclusive host versus compute access, sticky fault and save-before-evict. Owner independently verified the fixed dangling-else read defect with original local Icarus. [M08.2b.1 history](M08_2B_1_SIGNED16_HOST_STAGING_RTL_2026_11_11.md).

## First-party RTL and wire-level architecture

**New** `rtl/m08/m08_axil_page_control.sv` is a **single-clock 32-bit AXI4-Lite SLAVE** instantiating the existing M08.2b.1 page bank. The slave has a 12-bit address port (4 KiB design-level aperture), two fully decoupled write-address/write-data capture registers, one pending AR read register, and a **single serialized backend operation**. It is intentionally an AXI-Lite peripheral and **not** a PL bus master. Input clock and reset have AMD/Xilinx IP-Integrator interface annotations with **no hardcoded 100 MHz FREQ_HZ**: the owner-validated KV260 PS preset generated **99,999,001 Hz** when requesting 100 MHz. The actual PS and SmartConnect clock must propagate and be verified again in the future genuine BD.

- AW and W are captured in **either order**; no B response until both have arrived. Simultaneous AW/W is also supported.
- Write responses and read data remain stable while BREADY/RREADY are low; at most one outstanding AXI-Lite transaction, with no overlapped read/write backend accesses.
- Misaligned/unknown addresses: **DECERR (11)**, no alias. Known read-only registers / invalid commands / unsafe page access: **SLVERR (10)**, no software-visible success.
- A 64-cycle read/write backend watchdog returns **SLVERR** when an ACK never arrives and places the adapter into **sticky bridge quarantine** until external reset. In quarantine all writes and page reads fail closed; identity/status reads remain accessible for diagnosis.
- Backend B/R responses wait for actual page-bank acknowledgments. The adapter does **not** infer readback verification or state commit from the presence of a host buffer.
- An externally supplied `compute_req`/`compute_done`/`compute_fault` interface is preserved. It is **NOT connected to an HLS engine in this stage**; the standalone testbench drives a bounded debug compute transaction. Never claim M06 signed16 neural inference from this adapter test.

### 4 KiB local register map (byte offsets, not actual Linux addresses)

| Offset | Read | Write | Description |
| --- | --- | --- | --- |
| `0x000` | `0x4D303850` ASCII M08P | SLVERR | Identifies only the adapter's RTL, not the programmed image |
| `0x004` | `0x00020002` | SLVERR | Register-map revision (v2.2 source candidate) |
| `0x008` | `0x00000001` | SLVERR | One host-staged 256-byte page; **no** DMA/master/neural-engine capability |
| `0x00C` | status | SLVERR | bits [2:0] page phase; bit3 bank poisoned; bit4 valid; bit5 dirty; bit6 compute busy; bit7 host busy; bit8 bridge timeout/quarantine |
| `0x010` | selected logical ID | full-strobe 32-bit | Host-selected logical page number; blocked when compute active or quarantined |
| `0x014` | zero | full-strobe onehot command | `1=BEGIN` (EMPTY/READY), `2=COMMIT` (LOADING), `4=DISPATCH` (READY), `8=SAVE` (DIRTY). All other patterns SLVERR. |
| `0x018` | physical slot's current logical tag | SLVERR | Tag in page bank (not kernel physical address) |
| `0x01C` | number of unique initialized page bytes, 0..256 | SLVERR | Full-byte coverage must reach 256 |
| `0x100..0x1FC` | one 32-bit word from resident page | partial-byte WSTRB permitted while LOADING | 64 page words, ascending little-endian byte lanes; reads possible only while LOADING, READY, DIRTY. The compute owner excludes host page reads during RUNNING. |
| Others | DECERR (or SLVERR while quarantined for writes) | DECERR | No aliasing or hidden write effects |

**Command-specific hardware enforcement:** `COMMIT` asserts the M08.2b.1 `host_readback_verified` signal. The bank checks that *all 256 bytes were loaded* and *all 64 words were subsequently read*; it cannot authenticate that a CPU actually compared each value. The operator/driver must compare the 64 returned words against the intended image before issuing COMMIT. After compute, `SAVE` asserts `host_save_done` only if the bank has observed **all 64 dirty words**; the operator/driver must save and independently verify canonical backing before issuing SAVE. Malicious/inaccurate host software can still lie about these actions, which is outside the peripheral's proof.

**Poisoning:** bank hardware faults and watchdog faults quarantine the page until reset and fresh 256-byte complete load. A rejected malformed control command or read during RUNNING returns SLVERR without granting host access or silently resetting the page.

## Actual first-party test coverage and scope

**New** `rtl/m08/tb_m08_axil_page_control.sv` is an independent synchronous AXI-Lite bus functional model: AW-before-W, W-before-AW and simultaneous AW/W, absent/early B checks, B and R backpressure, unknown addresses and misalignment, RO/control write errors, full and partial WSTRB, complete 64-word load and readback, ready/dispatch and debug compute write, dirty readback + save before replacement, false SAVE/COMMIT poisoning, CPU page access forbidden during RUNNING, and forced no-ACK watchdog with sticky bridge quarantine. This tests the actual first-party RTL, **not** real PS or AMD SmartConnect hardware.

**New** `tests/test_m08_axil_page_control.py` checks source structure and invokes `iverilog -g2012` plus `vvp`. Its Icarus runtime test **SKIPS** if Icarus is unavailable on the local machine, which does not count as a proof. The M08 GitHub CI runs Icarus when the package is available; earlier unrelated Actions Icarus installation DNS outages are documented and cannot be mislabeled as a successful HDL simulation.

### Development PC (no Vivado, FPGA or root required)

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
command -v iverilog
command -v vvp
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_axil_page_control -o "$TMP/m08_axil_page.vvp" \
  rtl/m08/m08_axil_page_control.sv \
  rtl/m08/m08_host_staged_page_bank.sv \
  rtl/m08/tb_m08_axil_page_control.sv
vvp "$TMP/m08_axil_page.vvp"
python3 -m unittest discover -s tests -p 'test_m08_axil_page_control.py' -v
python3 -m unittest discover -s tests -p 'test_m08_host_staged_page_rtl.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

No `/dev/mem`, PS Linux shell, JTAG, original owner evidence folder or real DDR is accessed by these commands.

## Next gate — M08.2b.3 genuine native Vivado and then physical staging

**The new adapter has NOT been connected to the already accepted M08.2a native BD.** The next new isolated candidate must import the *original exact* RTL `m08_axil_page_control.sv` plus `m08_host_staged_page_bank.sv`, optionally retain identity, and use the actual AMD KV260 K26 PS board preset, FPD HPM0 → SmartConnect, common PS clock and reset. A separate **safe compute test controller/tieoff** is needed before native `validate_bd_design`; do not leave compute inputs floating or claim a neural kernel was integrated.

The genuine Vivado tool must assign and report a **new distinct 4 KiB AXI aperture**. Do **not** assume the previously accepted identity-only `0xA0000000` address is Linux MMIO or reuse that same aperture without a new original address-map review. Preserve the generated BD Tcl, warning inventory, exact source SHA256-before/after, report and original offline vendor log in a new exclusive owner evidence directory before synthesis. Only afterwards consider full route/WNS/WHS, signed16 integration, new bitstream and safe owner-controlled KV260 physical programming. External Linux DMA API buffer ownership is a separate later DDR gate.

**Completion rule:** M08.2b.2 closes **only as a source-level first-party AXI4-Lite peripheral** once genuine Icarus passes and same-HEAD M01–M08 workflows pass (or any infrastructure-only CI blocker is explicitly recorded and independently reproduced). M08.2b.3/4 physical gates remain open regardless.
