# P03.2c PS HPM width at boot: diagnosis and corrective integration

> **Latest authoritative outcome (2026-10-11):** The 128-bit FPD PS master
> combined with SmartConnect downsizing to the unchanged 32-bit AXI-Lite
> slave physically passed the four-register standalone A53 diagnostic.
> Earlier sections are preserved as chronological hypotheses and plans.
> See [the full root-cause case study](P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md)
> for the before/after evidence, the mechanism, and remaining acceptance gates.


**Status (2026-10-11): measured 128-bit PS/32-bit PL mismatch and physically verified corrected FPD128 read-only MMIO; full P03.2c command smoke still pending.**
**Branch:** `agent/v3-p03-autonomous-runtime`.
**Do not merge or close P03.2c from this note alone.**

## Signal-level symptom and fault boundary

2026-10-11 **same-run** LPD dual-ILA capture and A53 DDR mailbox:

| A53 physical address | PL AXI request/response | Processor-reported 32-bit value |
|---|---|---|
| 0x80000000 | `RDATA=0x4C543302`, OKAY | `0x4C543302` |
| 0x80000004 | `RDATA=0x00010000`, OKAY | `0` |
| 0x80000008 | `RDATA=0x0001031F`, OKAY | `0` |
| 0x80000018 | `RDATA=0xD1A60018`, OKAY | `0` |

All requests are 32-bit AXI transfers and all responses handshake. The
different values are observed **after the PS-facing PL AXI boundary**.
The FPD and LPD control paths exhibit the same CPU-visible failure.

## Critical boot-time width selectors (AMD UG1087)

| PS PL master | PS register | Selector bits | 32-bit | 64-bit | 128-bit |
|---|---|---|---|---|---|
| M_AXI_HPM0_FPD | FPD_SLCR.afi_fs `0xFD615000` | 9:8 | 0 | 1 | 2 |
| M_AXI_HPM0_LPD | LPD_SLCR.afi_fs `0xFF419000` | 9:8 | 0 | 1 | 2 |

Vivado candidate BD outputs **32-bit** AXI on both tested masters.
FSBL from an independent KV260 boot image initializes PS registers *before*
the agent JTAG-programs the **PL bitstream only**. Its HPM width may therefore
be 128 rather than the design's expected 32 bits. The documented hardware
reset values are 128-bit selection on both paths.

The exact read-only field inspection is:

```text
FPD = (raw(0xFD615000) >> 8) & 3
LPD = (raw(0xFF419000) >> 8) & 3
0=32-bit, 1=64-bit, 2=128-bit, 3=invalid/reserved
```

On the development PC, with `hw_server` running and a normally booted KV260:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl \
  tcp:127.0.0.1:3121 | tee /tmp/v3_p03_2c_ps_axi_width.log
```

This script selects PSU/APU physical access, halts A53 processors, reads
only those two PS system configuration registers, and prints decoded widths.
No `mwr`, PS reset, Linux commands, or PL bitstream rebuild. **Reboot
afterward** rather than resuming Linux.

If a register reports `128` or `64` while the matching PL port is 32,
that is a **concrete PS/PL hardware integration mismatch**. If both show 32,
the root cause is still open and one must not label the mismatch as proven.

## Corrective direction if mismatch is confirmed

**Do not use ad hoc `mwr` on `0xFD615000` or `0xFF419000` after Linux
boots.** AMD describes these AXI port selectors as static and instructs
not to modify them during normal operation.

The proper integration fix is to configure the PS early, from **the same
candidate hardware design used to build/program the PL**, before either the
A53 workload or ordinary PL HPM accesses:

1. Generate the PS initialization files (notably `psu_init.tcl` and/or
   `psu_init.c`) from the candidate's *fixed XSA*. These are used by
   the Vitis standalone/JTAG initialization and the board's FSBL.
2. Confirm the generated PS initialization contains the intended
   32-bit HPM master configuration (FPD HPM0 if using the preserved
   `0xA4000000` ABI, LPD HPM0 only for the opt-in `0x80000000` candidate).
3. **At a clean system-reset / pre-boot boundary**, use the documented
   XSDB `psu_init`, `psu_ps_pl_isolation_removal`,
   `psu_ps_pl_reset_config` path, or replace the board boot FSBL with one
   built from that same hardware XSA. This may reinitialize DDR, clocks,
   firewalls, and other PS hardware: use the vendor-supported reset/boot
   procedure, not the existing Linux-halt-and-provision sequence.
4. Re-read both width selector registers after initialization and before
   launching A53 code. Require 32 bits for the selected control master.
5. Provision project DDR fixture **after** PS/DDR reinitialization; program
   the matching bitstream and run the existing A53 read-only mailbox test.
6. Require all four nonzero-offset/ID values to match before attempting
   the original P03.2c page/resident-memory/dispatch smoke.
7. Once A53 MMIO is physically proved, incorporate this PS-boot initialization
   dependency into the production runtime and fixed boot artifacts, and
   return to the frozen FPD `0xA4000000` ABI unless explicitly changing
   the hardware/software contract is approved.

The prior user workflow depended on a Linux boot to initialize DDR and
then used standalone XSDB application download without running a matching
`psu_init` sequence. This can be incompatible with the newly routed
PS-PL interface widths.

**No PS width writes or resets have been committed to automation yet.**
First verify the current raw selector values, then implement and physically
verify one controlled boot-time integration path. This preserves the
accepted P02 DDR and P03.2b work.

## Vendor references

- [AMD UG1087 FPD_SLCR afi_fs](https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/afi_fs-FPD_SLCR-Register)
- [AMD UG1087 LPD_SLCR afi_fs](https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/afi_fs-LPD_SLCR-Register)
- [AMD PG201 PS initialization generation](https://docs.amd.com/r/3.4-English/pg201-zynq-ultrascale-plus-processing-system/Output-Generation)
- [AMD UG1400 JTAG PS init sequence](https://docs.amd.com/r/2024.1-English/ug1400-vitis-embedded/Debugging-Applications-on-Zynq-UltraScale-MPSoC)


## 2026-10-11 physical confirmation: boot width mismatch is real

Independent read-only XSDB measurements on the user's KV260:

```text
P03_2C_PS_WIDTH_TARGET=PSU
P03_2C_PS_WIDTH_MRD=FD615000:   00000A00
P03_2C_PS_WIDTH_MRD=FF419000:   00000200
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
P03_2C_PL_EXPECTED_HPM0_WIDTH_BITS=32
P03_2C_PS_WIDTH_MISMATCH_FPD=1
P03_2C_PS_WIDTH_MISMATCH_LPD=1
PASS: P03.2c read-only PS AXI width diagnostic complete; no PS registers written.
```

**Confirmed:** the PS hardware's FPD and LPD HPM0 widths are **128 bits**
during the current board's initialized state, whereas both routed
candidate PL-side interfaces were **32 bits**. This is a physically proven
integration mismatch. It is consistent with the four same-run A53/ILA
reads showing correct 32-bit data in PL and zero at three offsets in A53.

**Not yet confirmed:** eliminating this mismatch fixes MMIO. A corrected
bitstream and successful A53 mailbox test are required for causality and
P03.2c acceptance.

### Preferred non-invasive corrective experiment: match the booted PS width

An opt-in 128-bit FPD diagnostic is now supported by setting
`P03_PS_HPM0_DATA_WIDTH=128` with the normal
`P03_PS_MMIO_MASTER=FPD`.

```text
KV260 existing boot firmware:
  FPD_SLCR.afi_fs / dw_ss0_sel[9:8] = 2 (128 bits)
                 |
                 v
  zynq_ultra_ps_e/M_AXI_HPM0_FPD (128-bit AXI4)
                 |
                 v
  p03_hpm0_width_smartconnect_0 (128-bit AXI4 -> 32-bit AXI4-Lite)
                 |
                 v
  p03_ps_control_regs/S_AXI (32-bit AXI4-Lite, offsets unchanged)
                 |
                 v
  resident context/page/dispatch control signals
```

This avoids unsafe runtime writes to static PS width registers and
avoids replacing the KV260's existing boot image while testing.
The HP0/DDR data path remains at 128 bits, the MMIO control aperture
remains `0xA4000000..0xA4000FFF`, and the frozen P03 C header and
register offsets stay unchanged.

AMD PG247 specifies that SmartConnect internally adds lightweight
protocol and data-width downsizing logic when a >32-bit AXI4/AXI3
master is connected to 32-bit AXI4-Lite slave endpoints:
https://docs.amd.com/r/en-US/pg247-smartconnect/Low-Area-Mode
https://docs.amd.com/r/en-US/pg247-smartconnect/Downsizing-to-an-AXI4-Lite-Slave

The candidate code resides in `vivado/create_p03_mmio_impl_project.tcl`.
Vivado BD validation must prove the PS and SmartConnect input are 128-bit
AXI4 and the SmartConnect output and actual MMIO slave are 32-bit
AXI4-Lite. `vivado/run_p03_mmio_impl.sh` checks matching post-route
metrics and timing and rejects accidental reuse of old build directories.
Default values **still select the original 32-bit FPD Protocol Converter**
for historical reproducibility.

**Board-level verification required:** reboot KV260, retain normal DDR init,
run the candidate bitstream plus **an isolated read-only A53 ELF built from
the candidate XSA**, and require all four register values
(ID/VERSION/CAPABILITIES/unmapped signature). Because the previous FPD
and LPD candidate tests both returned zeros at +4/+8/+18, this is a
discriminating proof rather than a cosmetic configuration update.
Subsequently exercise the original P03.2c page/resident/dispatch smoke
before marking the milestone accepted.

If the 128-bit route or A53 readout still fails, retain all evidence
and investigate PS fabric transaction-width and address-byte-lane
alignment. Do not presume the hypothesis solved the fault before physical
verification.

### Exact host workflow for boot-matched FPD candidate

Set up your environment as before (Vivado/Vitis 2025.2,
`hw_server`, `.venv-p08`), then:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
export P03_PS_MMIO_MASTER=FPD
export P03_PS_HPM0_DATA_WIDTH=128
export P03_MMIO_STAGE=bd
export P03_MMIO_BUILD_DIR="$PWD/vivado/build/p03_2c_fpd128_bd_$(date -u +%Y%m%dT%H%M%SZ)"
bash vivado/run_p03_mmio_impl.sh

# After the BD gate passes:
export P03_MMIO_STAGE=route
export P03_MMIO_BUILD_DIR="$PWD/vivado/build/p03_2c_fpd128_route_$(date -u +%Y%m%dT%H%M%SZ)"
bash vivado/run_p03_mmio_impl.sh

# After route passes:
export P03_DIAG_REPORTS="$P03_MMIO_BUILD_DIR/reports"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_APP_NAME=p03_2c_readonly
export P03_2C_SOURCE_FILE=p03_2c_readonly.c
export P03_2C_READONLY_MMIO_BASE=0xA4000000
export P03_2C_BUILD_DIR="$PWD/vivado/build/p03_2c_readonly_fpd128_$(date -u +%Y%m%dT%H%M%SZ)"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
bash scripts/build_p03_2c_smoke.sh

# Reboot/DDR-init the KV260 first, then from development PC:
bash scripts/run_p03_2c_readonly.sh
cat "$P03_2C_BUILD_DIR/read_only_physical_evidence/verify.log"
```

Physical programming is JTAG-driven. The read-only ELF replaces the A53
Linux context; reboot KV260 afterward. No PuTTY access or unsafe SLCR
width writes are required.

Expected distinct pass marker from the 128-bit routed build:
`PASS: P03.2c boot-matched 128-bit PS master / 32-bit MMIO diagnostic routed (NOT P03.2c acceptance).`
An additional `PASS: P03.2c read-only Cortex-A53 MMIO diagnostic`
is required for the corrected *read* path; no such board result has yet
been reported.
