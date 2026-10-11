# P03.2c PS HPM width at boot: diagnosis and corrective integration

**Status: strong, hardware-specific hypothesis; awaiting live PS width register dump.**
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
