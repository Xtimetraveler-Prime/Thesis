# P03.2c HPM0 System ILA Diagnosis

> **2026-10-11 resolution:** The *read-only MMIO* failure is now resolved
> on the KV260. Live PS HPM0 is **128 bits**; both earlier failed PL
> candidates expected **32 bits**. An independently routed FPD128 design
> with SmartConnect 128->32-bit width/protocol conversion physically passed
> all four standalone A53 read-only register checks. All sections below
> record the chronological debugging process—including superseded early
> hypotheses—not the current fault status. **P03.2c full page/debug/dispatch
> command acceptance remains open.** See
> [P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md](P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md)
> for the authoritative evidence and fix.


**Phase:** P03 — autonomous PS-resident runtime  
**Sub-milestone:** P03.2c — physical Cortex-A53 MMIO smoke  
**Status:** diagnostic instrumentation candidate  
**Reason:** physical nonzero MMIO offsets still return zero through both
SmartConnect and a dedicated AXI Protocol Converter.

## Evidence motivating signal-level diagnosis

Physical PSU-target reads have repeatedly produced:

```text
0xA4000000 -> 0x4C543302
0xA4000004 -> 0x00000000
0xA4000008 -> 0x00000000
0xA400000C -> 0x00000000
```

A temporary otherwise-unmapped RTL response was also added:

```text
0xA4000018 -> expected 0xD1A60018 if the access reaches the custom slave
```

but physical hardware returned:

```text
0xA4000018 -> 0x00000000
```

Changing the HPM0 path from SmartConnect to a dedicated AXI Protocol Converter
did not change the physical failure signature.

This means further topology changes without visibility would be speculative.

## Diagnostic shell

A temporary two-slot System ILA monitors the same 100 MHz HPM0 clock domain.

```text
SLOT_0_AXI:
PS M_AXI_HPM0_FPD
    -> AXI Protocol Converter S_AXI

SLOT_1_AXI:
AXI Protocol Converter M_AXI
    -> p03_ps_control_regs S_AXI
```

Both slots have AXI data/trigger monitoring and protocol checking enabled.

The accepted HP0/DDR paging path is unchanged.

## Controlled transaction

The capture workflow:

1. boots/provisions the board normally before the diagnostic;
2. programs the ILA-instrumented P03 candidate;
3. halts all visible Cortex-A53 cores;
4. arms the HPM0 System ILA;
5. performs exactly one PSU/APU physical 32-bit read:
   `0xA4000004`;
6. captures both sides of the AXI Protocol Converter in the same ILA window;
7. exports native `.ila`, CSV, and VCD evidence;
8. reboots rather than resuming the halted Linux instance.

The System ILA trigger is SLOT_0 read-address VALID. With the A53s already
halted, the single physical diagnostic read is intended to be the transaction
that triggers the capture.

## Signals of interest

For the read-address channel:

- ARADDR
- ARVALID
- ARREADY
- ARSIZE
- ARLEN / ARBURST where present

For the read-response channel:

- RDATA
- RRESP
- RVALID
- RREADY

The relevant comparison is between SLOT_0 and SLOT_1 for the same request.

## Frozen interpretation

### Case A — address is wrong before the converter

If SLOT_0 does not show `ARADDR=0xA4000004`, the defect is upstream of the
protocol converter, in PS/HPM0/debug-access behavior or its configuration.

### Case B — SLOT_0 is correct, SLOT_1 is absent or altered

If SLOT_0 shows a valid `0xA4000004` transaction but SLOT_1 does not carry
the equivalent read, the protocol-converter/integration boundary is the fault
domain.

### Case C — both slots carry the correct address, but response is zero

If both slots show `ARADDR=0xA4000004` and the custom slave handshakes it,
then the fault moves back inside the physical custom-slave implementation or
its generated wrapper/netlist despite the standalone RTL simulation.

`RRESP` distinguishes a legal OKAY zero-data response from SLVERR/DECERR.

### Case D — both slots and response are correct

If SLOT_1 returns `RDATA=0x00010000` with an OKAY response but the external
debug read reports zero, the defect is downstream of the PL AXI response,
inside the PS/debug access path.

## Acceptance boundary

This ILA build is diagnostic only. The temporary System ILA, protocol-checking
instrumentation, and unmapped-read signature are not part of the final P03.2
ABI.

After the root cause is identified and corrected:

1. remove temporary diagnostic logic/instrumentation;
2. route a clean final P03.2 shell;
3. verify ID/VERSION/CAPABILITIES physically;
4. rebuild standalone A53 software against the final XSA;
5. rerun the full P03.2c page/resident/dispatch smoke;
6. close P03.2 only after independent physical verification;
7. continue to the PS-resident autonomous runtime phases.


## ILA integration attempt 1 — invalid monitor-interface connection

The first ILA-instrumented route attempt stopped during block-design
construction with:

```text
ERROR: [Common 17-161] Invalid option value
'/p03_hpm0_system_ila_0/SLOT_0_AXI' specified for 'auto'.
```

No synthesis, implementation, or timing result was produced.

Cause: the System ILA monitor interface was incorrectly treated as a normal
third endpoint in `connect_bd_intf_net`.

For System ILA interface debugging, the AXI functional connection remains a
normal two-endpoint interface net. That interface net is marked for debug and
Vivado's debug/Designer Assistance automation connects it to System ILA.

The corrected diagnostic flow now:

1. creates explicitly named functional interface nets:
   - `p03_hpm0_ps_to_converter_axi`;
   - `p03_hpm0_converter_to_mmio_axi`;
2. sets `HDL_ATTRIBUTE.DEBUG=true` on both;
3. invokes `xilinx.com:bd_rule:debug` once for both interfaces;
4. requests read-address/read-data capture and protocol checking;
5. requires Vivado to produce exactly one System ILA with two monitor slots.

The functional HPM0 control topology did not change as part of this fix.


## ILA integration attempt 2 — mixed AXI4/AXI4-Lite monitor protocols

The corrected Debug Automation flow created one two-slot System ILA and attached
both functional HPM0 interface nets. Independent local preflight passed, but
`validate_bd_design` failed before synthesis or routing:

```text
Debug Automation : Instantiating new System ILA block '/system_ila_0'
P03.2c System ILA automation: cell=/system_ila_0 slots=2
ERROR: [BD 41-237] Bus Interface property PROTOCOL does not match between
/system_ila_0/SLOT_1_AXI(AXI4) and
/p03_hpm0_protocol_converter_0/M_AXI(AXI4LITE)
```

The blocker is in the **debug monitor interface**, not yet evidence of a
functional PS-to-PL AXI transaction failure. The converter's upstream AXI4
and downstream AXI4-Lite protocols are intentional.

The System ILA's documented per-slot `C_SLOT_<p>_AXI_PROTOCOL` parameter
supports `AXI4LITE` (AMD PG261, System ILA Product Guide). Debug Automation
left slot 1 at its AXI4 default, so the diagnostic Tcl now sets and checks:

```tcl
CONFIG.C_SLOT_0_AXI_PROTOCOL {AXI4}
CONFIG.C_SLOT_1_AXI_PROTOCOL {AXI4LITE}
```

To avoid repeating a complete route merely to discover a block-design
configuration error, `P03_MMIO_STAGE=bd` now stops after
`validate_bd_design` and `save_bd_design`, with a required PASS marker.
The normal `route` path and accepted P02/P03.2b functional architecture are
unchanged. Each diagnostic build uses a new output directory; existing
routed/acceptance artifacts are preserved.

**Status:** Correction committed; awaiting independent Vivado 2025.2 BD-only
validation, then a new routed ILA shell, then one physical HPM0 read capture.
Neither the System ILA change nor this documentation accepts P03.2c.

Reference: AMD System ILA PG261,
https://docs.amd.com/v/u/en-US/pg261-system-ila


## ILA integration attempt 3 — slot parameter versus real interface pin

The next independent Vivado 2025.2 BD-only run confirmed:

```text
P03_2C_ILA_SLOT_0_PROTOCOL=AXI4
P03_2C_ILA_SLOT_1_PROTOCOL=AXI4LITE
ERROR: [BD 41-237] Bus Interface property PROTOCOL does not match between
/system_ila_0/SLOT_1_AXI(AXI4) and
/p03_hpm0_protocol_converter_0/M_AXI(AXI4LITE)
```

**Diagnosis:** The `CONFIG.C_SLOT_1_AXI_PROTOCOL` *IP setting* reads back
`AXI4LITE`, but the connected `SLOT_1_AXI` block-design *interface pin*
remains `AXI4`. The prior check established only the IP parameter value,
not the actual interface pin protocol, and therefore falsely indicated that
the mismatch had been resolved. The preserved `AWUSER_WIDTH`/`ARUSER_WIDTH`
notices are warnings, not the fatal issue in this log. AMD UG912 documents
`CONFIG.PROTOCOL` on `bd_intf_pin` as read-only; do not try to force the
monitor interface property or waive `validate_bd_design`.

### Diagnostic replacement (awaiting Vivado verification)

The new implementation deliberately does not connect a System ILA AXI
interface to the converter's AXI4-Lite output. It instruments both functional
boundaries without modifying the AXI protocol converter or the register
decode:

- **Upstream:** 1-slot System ILA on the genuine PS-HPM0 to converter AXI4
  net; its *actual BD interface pin* `CONFIG.PROTOCOL` must read `AXI4`.
- **Downstream:** a separate native ILA with seven **passive RTL mirror
  outputs** from `p03_ps_control_regs`: `ARVALID`, `ARADDR[39:0]`,
  `ARREADY`, `RVALID`, `RREADY`, `RDATA[31:0]`, `RRESP[1:0]`.
  It uses ordinary scalar probe pins and has no AXI interface protocol
  property. The mirrors are not new control inputs or alternative datapaths.
- **Physical capture:** arm both ILAs for the same physical MMIO read. Export
  the upstream `p03_2c_hpm0_capture.{ila,csv,vcd}` and downstream
  `p03_2c_mmio_slave_capture.{ila,csv,vcd}`. Preserve upstream evidence
  even if the downstream analyzer never triggers.

Both diagnostic ILAs and the passive RTL probe outputs must be removed
before producing the final, non-instrumented P03.2 acceptance bitstream.

**Current status:** code and preflight updated on the active P03 branch.
Independent BD-only `validate_bd_design`, route, and physical capture are
**not yet completed**. P03.2c remains blocked until those gates pass.

References: AMD PG261 (System ILA) and UG912 (BD_INTF_PIN properties).


## First dual-ILA physical capture attempt — HW_ILA trigger mode write refused

Independent hardware programming of the routed split-ILA diagnostic design
succeeded. Vivado Hardware Manager discovered both the upstream System ILA
and downstream native ILA; the downstream probe inventory included the
seven named passive MMIO read-channel taps. It also included many
`<const0>`/`<const1>` synthetic probe aliases.

**Capture did not arm.** The Tcl script failed in `p03_arm_ila` while
configuring the first ILA:

```text
ERROR: [Labtoolstcl 44-156] hw_ila property 'CONTROL.TRIGGER_MODE' is read-only.
```

The failure occurred before the arming marker and before the wrapper issued
its controlled `0xA4000004` read. No captured AXI transaction is available
from this attempt; the physical MMIO root cause is still unknown.

AMD UG835 documents that `reset_hw_ila` restores the basic-mode defaults:
`CONTROL.TRIGGER_MODE=BASIC_ONLY`,
`CONTROL.TRIGGER_CONDITION=AND`,
`CONTROL.CAPTURE_MODE=ALWAYS`, `CONTROL.WINDOW_COUNT=1`.
The capture Tcl now resets each analyzer, **reads and verifies** those
properties, avoids *all* explicit `CONTROL.*` writes, and sets only the
`TRIGGER_COMPARE_VALUE` on the selected `ARVALID` hardware probe.
The default trigger position is zero, providing a post-trigger capture
window. The script also summarizes synthetic constant probes to prevent
diagnostic errors being hidden in long log tails.

Added an offline regression
`tests/test_p03_2c_ila_capture_contract.py` covering the default-property
contract, both-analyzer arming, preserved trace outputs, and log filtering.

**Next independent hardware gate:** Reboot the KV260 (the previous wrapper
halted the Cortex-A53 cores), reprogram the *existing* successful diagnostic
bitstream/probe pair if needed, and rerun the updated capture Tcl with a new
output directory. A new route or XSA rebuild is **not required** for these
Hardware Manager script changes.

AMD references:
- https://docs.amd.com/r/2021.1-English/ug835-vivado-tcl-commands/reset_hw_ila
- https://docs.amd.com/r/2023.2-English/ug912-vivado-properties/HW_ILA


## 2026-10-11 — first successful physical dual-ILA capture: MMIO read returns correct PL data

**Status: independently captured; root cause isolated past PS-facing PL AXI boundary, not yet resolved.** The user supplied the complete paired captures and XSDB result from a
diagnostic K26 bitstream routed on 2026-10-10:

- `p03_2c_hpm0_capture.csv`: 1,024 samples, SHA-256
  `9bfb11bd9844aa5de7c665fb66db738858f035ce85807a90755eeddb01360896`.
- `p03_2c_mmio_slave_capture.csv`: 1,024 samples, SHA-256
  `63bc33a3da34b4f992fba48672bda9e91c0abf259efd8e86fc3875016ce1765d`.
- `xsdb_single_read.log`: SHA-256
  `17a2b5109c7c81684830cf4bcf6c9d39ed48b629d8ca5d4b653f1d577c69bffe`.
- `vivado_ila_capture.log`: SHA-256
  `abdb179ad3ebf65d6ea9df6a28089a9063dfb82486207657bf9c8857d3df9077`.

Both ILAs triggered on the intended `0xA4000004` transaction. Sample numbers
are independent windows; **do not subtract them to calculate bridge latency**.

| Captured channel | Accepted request | Completed response | Other evidence |
|---|---|---|---|
| Downstream native ILA at `p03_ps_control_regs` | sample 0, `ARVALID=ARREADY=1`, `ARADDR=0xA4000004` | sample 1, `RVALID=RREADY=1`, `RDATA=0x00010000` | Captured `RRESP[0]=0` (only the low bit is present in this trace) |
| Upstream System ILA at PS-facing converter input | sample 0, `ARVALID=ARREADY=1`, `ARADDR=0x00A4000004`, `ARSIZE=4 bytes` | sample 5, `RVALID=RREADY=RLAST=1`, `RDATA=0x00010000` | `RRESP=OKAY` |
| XSDB PSU physical read | `mrd -force -size w 0xA4000004 1` | reports `0x00000000` | **Disagrees with observed PS-facing PL response** |

Each capture has exactly **one** qualifying AR handshake and one R handshake.
The slave-side `ARADDR` happens to change to `0xA4000008` after sample 0,
but `ARVALID=0` at that time: it is an **inactive bus value**, not evidence
of another read or an address translation defect.

### Conclusions and corrected interpretation

1. For the captured transaction, the custom MMIO RTL **does decode +0x004**
   and returns its specified VERSION `0x00010000`.
2. The AXI Protocol Converter delivers the correct, valid, OKAY read response
   to the PS-facing AXI bus. The clocked AXI4 read handshakes complete.
3. XSDB `PSU` nevertheless prints zero. The disagreement lies **after the
   monitored PL-to-PS boundary, or in the XSDB debug access/reporting path**.
   The capture alone does not determine which.
4. **Supersedes earlier diagnostic-signature interpretations** in
   `P03_2C_PHYSICAL_ATTEMPT1.md`: returning zero via XSDB is NOT evidence
   that nonzero-offset accesses never reached the custom slave. The new
   signal-level capture proves that +0x004 reaches the slave and returns
   correct data.
5. The earlier A53 standalone mailbox `FAIL_MMIO_VERSION` was observed with
   an **older physical candidate**. It has **not** been repeated against this
   newly routed, protocol-converter/split-ILA bitstream; do not combine the
   two results as proof of a persistent A53 read defect.
6. Do not modify the custom RTL decode or replace the HPM0 topology based on
   the now-disproven "lost nonzero address" explanation.

### Next discriminating experiment (no bitstream rebuild)

Boot the KV260 into Linux, program the same proven diagnostic bitstream, and
use a **real A53 Linux process**, not a `PSU`/DAP XSDB memory read, to
perform *read-only* 32-bit device-memory accesses:

```sh
sudo busybox devmem 0xA4000000 32
sudo busybox devmem 0xA4000004 32
sudo busybox devmem 0xA4000008 32
sudo busybox devmem 0xA4000018 32
```

Expected (diagnostic candidate):

```text
0x4C543302
0x00010000
0x0001031F
0xD1A60018
```

If Linux observes the expected values, the current A53-visible MMIO read
path works, and the XSDB `PSU` zero needs separate debugger-path
investigation. Continue the accepted-behavior page/debug/dispatch smoke with
an ELF built for the **same candidate XSA**, keeping its identity separate
from accepted P03.2b artifacts.

If Linux also reads zero, the failure remains in the PS software/translation
or PS-side data-return path; investigate memory attributes and master-port
width/byte-lane mapping before any speculative RTL topology changes.
A53 and debug/DAP access paths are not equivalent.

**P03.2c acceptance remains open:** this captures a working PL MMIO read,
not a passing physical Cortex-A53 standalone page/resident/dispatch smoke.


## 2026-10-11 — KV260 Linux/PuTTY terminal becomes unresponsive after programming

**Observed by the user:** the diagnostic PL bitstream programmed successfully,
but no new commands could be entered in the PuTTY serial terminal afterward.
This prevents the planned Linux BusyBox `devmem` check. The cause is **not
yet established**; a stopped/crashed A53 Linux instance, a serial-console
connection problem, or JTAG/hardware-server interference are distinct
possibilities. Successful programming does not prove Linux remains alive.

### Next path: Cortex-A53 standalone read-only probe, no serial terminal

The repo now contains a diagnostic-only `p03_2c_readonly.c` application
that reuses the established Vitis 2025.2 standalone build/XSDB download path.

- Reads ONLY `ID`, `VERSION`, `CAPABILITIES`, and temporary unmapped
  signature at `0xA4000018` using `Xil_In32` from A53 #0.
- Preserves **all four observed values**, even if they mismatch. Reports a
  separate pass mask, completion marker, and expected constants.
- Uses the existing reserved 64-byte DDR mailbox at `0x43FF0000`, read
  through the established PSU/APU **DDR** debug path. A PSU debug read of
  DDR is not equivalent to the problematic PSU **PL-MMIO** read.
- **Does not write P03 MMIO registers** and does not issue page, debug,
  resident-memory or dispatch commands.
- Requires explicit per-candidate XSA SHA-256 identity and a fresh isolated
  Vitis workspace. The previously accepted P03.2b SHA remains frozen.
- Reuses `p03_2c_xsdb_prepare.tcl`, `p03_2c_program_bitstream.tcl`,
  `p03_2c_xsdb_run.tcl` through `run_p03_2c_readonly.sh` and decodes
  the returned mailbox with `p03_2c_verify_readonly.py`.

**Reproduction after a board reboot and normal DDR initialization:**

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
export P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_native_route_20261010T202128Z/reports"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_APP_NAME=p03_2c_readonly
export P03_2C_SOURCE_FILE=p03_2c_readonly.c
export P03_2C_BUILD_DIR="$PWD/vivado/build/p03_2c_readonly_$(date -u +%Y%m%dT%H%M%SZ)"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
bash scripts/build_p03_2c_smoke.sh
bash scripts/run_p03_2c_readonly.sh
```

The run script provisions the accepted P02 core-0 512 KiB fixture and
zeroes the 64-byte mailbox; programs the routed candidate bitstream and
pulses PL reset; halts A53 cores, starts the new standalone application,
and dumps/decodes the mailbox. It therefore **interrupts and replaces the
normal Linux execution context on A53 #0**. Reboot after the run. It can
skip programming if the same exact bitstream is already resident via
`P03_2C_SKIP_PROGRAM=1`, but the user assumes responsibility for identity.

**Interpretation:**

- All four A53 values match: current processor-originated MMIO read path
  works; the XSDB PSU/DAP readout remains independently anomalous. Proceed
  to the existing full page/resident/dispatch smoke with an appropriately
  rebuilt candidate ELF.
- A53 reads also return zero: real processor-side data-path/software
  problem; investigate A53 translation/memory attributes and PS read
  handling, not an already-proven good RTL VERSION decoder.
- No mailbox completion: A53 standalone program did not finish or DDR
  evidence is not visible; inspect `a53_run.log` and rerun preparation
  before attributing the result to AXI MMIO.

This does not close P03.2c: no autonomous runtime or page/dispatch proof
is claimed from the read-only diagnostic.


## 2026-10-11 — actual A53 read-only mailbox confirms the fault persists

The first `p03_2c_readonly.c` diagnostic ran successfully under XSDB on
Cortex-A53 #0 and wrote a complete DDR mailbox. The host verified:

```text
P03_2C_A53_MAGIC=0x50335244
P03_2C_A53_RESULT=0xDEAD0001
P03_2C_A53_COMPLETE=0xC0DEF00D
0xA4000000 -> 0x4C543302 (PASS)
0xA4000004 -> 0x00000000 (expected 0x00010000)
0xA4000008 -> 0x00000000 (expected 0x0001031F)
0xA4000018 -> 0x00000000 (expected 0xD1A60018)
```

`result=0xDEAD0001` encodes a failing four-register check with **only
bit 0 / ID passing**. The completion marker is present, so this is not a
mere XSDB failure to start the application or a missing JTAG server:
`hw_server` already provides the USB/JTAG connection for Vivado and XSDB.
The A53 **itself** reproduces the nonzero-offset failure on the present
candidate. This **supersedes** the earlier open possibility that the
problem is restricted to PSU-target XSDB reads.

The prior dual-ILA capture of an XSDB-initiated +0x004 read independently
established that the custom MMIO slave returned `0x00010000` and the
PS-facing AXI4 interface delivered `RDATA=0x00010000` with
`RRESP=OKAY`. The capture and this A53-only mailbox are from different
transactions; **do not claim that the A53 read itself has been
ILA-captured**. The combination strongly motivates investigating the PS
master data-width/byte-lane or PS-side read-return path rather than
speculatively rewriting the already verified slave VERSION decoder.

### Tested external precedent and opt-in LPD diagnostic candidate

A separate ZCU102 AXI-Lite project documented the same
`+0x0` works / `+0x4` returns zero pattern on
`M_AXI_HPM0_FPD`, and reported recovery after moving a control
register aperture to the 32-bit `M_AXI_HPM0_LPD` master:
https://github.com/Binoculars-X/zynq-axi-lite/blob/main/research-history.md

This report is an **external precedent**, not proof of the KV260 root
cause (their decisive bad beat was a *write*; ours is a *read*).
AMD PG201 documents `PSU__MAXIGP2__DATA_WIDTH` as a configurable PS master
setting. AMD UG1085 gives LPD-to-PL a 512 MiB aperture
`0x80000000..0x9FFFFFFF`; the FPD HPM0 low aperture starts at
`0xA4000000`.

An isolated candidate can now be built using `P03_PS_MMIO_MASTER=LPD`.
It changes **only** the diagnostic PS-to-PL control master and low
address mapping:

```text
FPD default (unchanged):  M_AXI_HPM0_FPD -> converter -> MMIO @ 0xA4000000
LPD candidate (opt-in):  M_AXI_HPM0_LPD -> converter -> MMIO @ 0x80000000
Existing HP0/DDR path:   unchanged (S_AXI_HP0_FPD, 128 bits)
```

It retains the two diagnostic analyzers. The LPD bitstream gets a separate
explicit build directory and must pass the BD-only gate before routing.
The unchanged frozen `p03_mmio.h` ABI still declares `0xA4000000`.
Only the copied `p03_2c_readonly.c` inside the isolated candidate build
is prefixed with `P03_READONLY_MMIO_BASE=0x80000000` so the A53
diagnostic reads the correct **LPD** address; acceptance smoke and baseline
FPD builds retain the old base.

**Status:** LPD diagnostic candidate code prepared, **not yet BD-validated,
routed, or physically tested**. No P03.2c acceptance evidence has been
produced, and the working FPD ILA evidence must be preserved.


## 2026-10-11 — LPD routed/programmed and failed the same A53 read-only probe

**Independent physical result:** The alternate `P03_PS_MMIO_MASTER=LPD` candidate
completed BD validation, routing, bitstream programming, and standalone Cortex-A53
mailbox collection. The mailbox reported:

```text
P03_2C_A53_MAGIC=0x50335244
P03_2C_A53_RESULT=0xDEAD0001
P03_2C_A53_COMPLETE=0xC0DEF00D
PASS: Cortex-A53 MMIO 0x80000000 returned 0x4C543302
FAIL: Cortex-A53 MMIO 0x80000004 returned 0x00000000 (expected 0x00010000)
FAIL: Cortex-A53 MMIO 0x80000008 returned 0x00000000 (expected 0x0001031F)
FAIL: Cortex-A53 MMIO 0x80000018 returned 0x00000000 (expected 0xD1A60018)
```

This directly **falsifies the proposed LPD relocation workaround** for the
KV260 as configured: switching the PS-to-PL MMIO control interface and base
address alone does **not** solve the nonzero-offset read failure. An isolated
problem specific to the FPD master is no longer a sufficient explanation.
The shared symptom may still arise from shared PS translation, data-width,
lane handling, or another common factor. Do not reinterpret a completed
mailbox as proof that data was correct; the result and match mask failed.
Do not change the frozen baseline ABI or accept P03.2c.

The LPD design has been independently routed and physically tested, superseding
the previous section's "not yet physically tested" status. Preserve its build
outputs and the FPD split-ILA captures as separate diagnostic evidence.

### Next discriminating measurement: A53-originated ILA capture

The previous dual-ILA capture showing correct `VERSION=0x00010000`
was initiated by an XSDB **PSU** target read. Neither the previous capture
nor the LPD mailbox captures the **A53-originated** transaction in the ILA.
The next test must launch the existing A53 read-only ELF *after arming both*
ILAs and capture the same execution's AXI read requests and responses, then
dump the A53 DDR mailbox. This separates:

- A53 sends a different address/size/protection and the PL returns zero:
  investigate master transaction generation and byte-lane behavior.
- A53 sends the intended request, PL returns the correct value, yet A53
  mailbox reports zero: investigate PS read-return path, A53 mapping or
  standalone software/runtime.
- A53 reads are absent from one ILA: inspect master, routing and trigger
  configuration before declaring success or failure.

No new bitstream or hardware topology change is warranted solely by the
latest LPD outcome. Continue on `agent/v3-p03-autonomous-runtime`.

### Implemented same-run Cortex-A53 + dual-ILA capture (pending board verification)

Added:

- `scripts/run_p03_2c_a53_ila_capture.sh`: a non-destructive capture driver
  that validates the pre-existing LPD/FPD XSA and compiled C-source MMIO base,
  provisions the reserved DDR fixture, programs the same diagnostic FPGA,
  arms both existing System/native ILAs, **then** launches the already-built
  Cortex-A53 read-only ELF, dumps the resulting DDR mailbox, exports the
  upstream/downstream CSV/VCD/ILA traces, and preserves all logs/hashes in a
  *new* evidence directory. The return status of the read-only mailbox
  verifier is reported separately, so a genuine bad MMIO value does not
  discard the hardware captures.
- `scripts/p03_2c_summarize_a53_ila.py`: prints each sampled AXI
  `ARVALID && ARREADY` request and `RVALID && RREADY` response (address,
  data, response code, and AXI transfer size when available), alongside the
  **same execution's** four Cortex-A53 result words.
- `tests/test_p03_2c_a53_ila_capture_contract.py` and
  `tests/test_p03_2c_a53_ila_trace_summary.py` for offline regression.

Reuse the LPD candidate's successfully routed `reports/` directory and its
matching existing A53 ELF build directory. From the development PC (not
PuTTY), after a fresh board boot/DDR initialization:

```bash
export P03_DIAG_REPORTS="<absolute path to routed LPD reports>"
export P03_2C_BUILD_DIR="<absolute path to matching LPD readonly ELF build>"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_2C_READONLY_MMIO_BASE=0x80000000
export P03_A53_ILA_CAPTURE_DIR="/tmp/v3_p03_2c_a53_ila_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_2c_a53_ila_capture.sh "$P03_A53_ILA_CAPTURE_DIR"
python scripts/p03_2c_summarize_a53_ila.py \
    --capture-dir "$P03_A53_ILA_CAPTURE_DIR" --base 0x80000000
```

The ILA trigger is `ARVALID` and may fire first on the ID register read
at `+0x0`; later reads will only appear if they occur inside the 1024-sample
post-trigger capture window. **Absence of VERSION from that window is not
proof it never occurred.** If needed, a subsequent run can trigger explicitly
on VERSION or reorder only the diagnostic A53 ELF reads.

This script does not require rebuilding or rerouting the FPGA or rebuilding
the existing A53 ELF. Physical signal capture on the user's board remains
pending; the persistent MMIO root cause has **not** yet been corrected.


## 2026-10-11 — same-execution A53 LPD ILA resolves all four AXI transactions

User-uploaded evidence: `p03_2c_hpm0_capture.csv`,
`p03_2c_mmio_slave_capture.csv`, `p03_2c_a53_readonly_mailbox.bin`,
`vivado_ila_capture.log`. Both traces contain 1024 samples and were
triggered by the same real A53 diagnostic process. Analysis counts exactly
four upstream and four downstream accepted address/data handshakes.

| Address | Upstream AR sample / R sample | Downstream AR sample / R sample | PL/slave RDATA | Upstream RDATA / RRESP | A53 DDR mailbox |
| --- | --- | --- | --- | --- | --- |
| `0x80000000` | 0 / 5 | 0 / 1 | `4C543302` | `4C543302` / OKAY | `4C543302` |
| `0x80000004` | 37 / 42 | 37 / 38 | `00010000` | `00010000` / OKAY | `00000000` |
| `0x80000008` | 63 / 68 | 63 / 64 | `0001031F` | `0001031F` / OKAY | `00000000` |
| `0x80000018` | 90 / 95 | 90 / 91 | `D1A60018` | `D1A60018` / OKAY | `00000000` |

All upstream requests have `ARSIZE=4 bytes`; read responses
have `RVALID=RREADY=RLAST=1` and `RRESP=OKAY`. Every slave
response has `RVALID=RREADY=1`, `RRESP[0]=0`. The A53
mailbox has valid `magic=0x50335244`, `complete=0xC0DEF00D` and
`result=0xDEAD0001`, with only the ID match bit set.

**High-confidence localization:** The slave and protocol converter
return the correct data on all A53-originated transactions. The discrepancy
appears on the **PS side of the observed 32-bit AXI master bus**, between
that boundary and the A53-visible result, or in the A53 application's
storage path. The earlier theory that the converter was dropping offsets
is disproved for all four reads. Swapping to the LPD master did not help.

### New leading hypothesis: mismatch between boot-time PS AXI width and bitstream

The design's `CONFIG.PSU__MAXIGP{0,2}__DATA_WIDTH {32}` and the realized
32-bit BD interface specify PL-side HPM width; they do **not prove** the
PS-side runtime width registers were configured accordingly. The KV260
boots its original firmware and the project subsequently programs only
the PL bitstream through JTAG. The FSBL normally initializes the
processing-system configuration, including AXI width settings.

AMD UG1087 identifies these **static** PS registers:

- `FPD_SLCR.afi_fs` at `0xFD615000`: `dw_ss0_sel[9:8]` controls
  `M_AXI_HPM0_FPD`; `00=32`, `01=64`, `10=128` bits.
- `LPD_SLCR.afi_fs` at `0xFF419000`: `dw_ss2_sel[9:8]` controls
  `M_AXI_HPM0_LPD`; same encoding.
- Their documented reset values `0x00000A00` and `0x00000200`
  respectively select 128 bits on those masters, unless boot firmware
  configures otherwise.

**Critical safety:** The AMD register descriptions warn that these width
selectors are **static** and should not be modified during normal
operation. Do NOT write these registers from a halted Linux debugger
session. First gather their actual values using the new *read-only*
`vivado/p03_2c_xsdb_ps_axi_width_diag.tcl`, which selects a PSU/APU
physical target and prints the raw values and decoded widths. It does
not write any PS or PL register.

References:
- AMD UG1087 FPD `afi_fs`:
  https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/afi_fs-FPD_SLCR-Register
- AMD UG1087 LPD `afi_fs`:
  https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/afi_fs-LPD_SLCR-Register
- AMD PG201 `psu_init.tcl`/`psu_init.c` generated initialization
  including PS clock/AXI/peripheral configuration:
  https://docs.amd.com/r/3.4-English/pg201-zynq-ultrascale-plus-processing-system/Output-Generation

If runtime width selectors are 128/64 but the routed design specifies
32, this is a specific, testable **PS hardware/runtime configuration
mismatch**, not an RTL bug. The corrective solution would be to configure
the PS width **during boot/reset initialization** using the PS init from
the *matching candidate XSA* and then program/run that design; the project
must not depend on the boot firmware's unrelated default PS topology.
Follow that with the four-register A53 read-only gate and subsequently
the full page/resident/dispatch smoke gate. If widths already match
32 bits, investigate A53 software/MMU/response handling rather than
declaring the mismatch as root cause.

**Current status:** Width mismatch is a strong hypothesis awaiting the
two live PS register values; no firmware correction nor P03.2c acceptance
has been physically verified.


## 2026-10-11 — live PSU width registers confirm 128-bit PS versus 32-bit PL mismatch

The user executed the new read-only `p03_2c_xsdb_ps_axi_width_diag.tcl` on
the physical KV260 after normal PS boot:

```text
P03_2C_PS_WIDTH_TARGET=PSU
P03_2C_PS_WIDTH_MRD=FD615000:   00000A00
P03_2C_PS_WIDTH_MRD=FF419000:   00000200
P03_2C_PS_FPD_AXIFS_RAW=0x00000A00
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_AXIFS_RAW=0x00000200
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
P03_2C_PL_EXPECTED_HPM0_WIDTH_BITS=32
P03_2C_PS_WIDTH_MISMATCH_FPD=1
P03_2C_PS_WIDTH_MISMATCH_LPD=1
PASS: P03.2c read-only PS AXI width diagnostic complete; no PS registers written.
```

**Hardware mismatch confirmed:** both physical HPM PS width selectors are
128-bit, whereas the PS-facing AXI master BD ports in the failed bitstreams
were configured for 32 bits. This is consistent with the ID-only A53 failure
and four correct upstream ILA `RDATA` words. The fact of the mismatch is
now observed rather than inferred from reset defaults.

**Causality remains conditional:** until a compatible 128-bit routed design
returns the four A53 register values correctly, do not claim this is a
physically *fixed* MMIO path or close P03.2c.

### Opt-in corrected hardware variant (awaiting independent BD/route/board run)

Rather than writing to static PS SLCR width selectors in a running system,
the branch can now compile `P03_PS_MMIO_MASTER=FPD` with
`P03_PS_HPM0_DATA_WIDTH=128`. The PS-to-PL HPM0 bus becomes 128-bit
AXI4 to match the actual booted hardware. An isolated 1x1 SmartConnect
provides protocol conversion and data-width downsizing to the unchanged
32-bit AXI4-Lite register endpoint. The alternative 32-bit FPD Protocol
Converter implementation remains the default for reproducibility.

`vivado/create_p03_mmio_impl_project.tcl` now checks the realized 128-bit
AXI4 ingress and 32-bit AXI4-Lite egress; the route acceptance script
checks a distinct 128-bit width/SmartConnect metrics signature. All
new builds use unique directories. HP0/DDR paging remains unchanged.

See `docs/P03_2C_PS_HPM_WIDTH_BOOT_REMEDIATION.md` for the full
safe A53 build and read-only hardware test procedure. AMD PG247 documents
SmartConnect's automatic 128-to-32 Lite width/protocol conversion:
https://docs.amd.com/r/en-US/pg247-smartconnect/Downsizing-to-an-AXI4-Lite-Slave

This candidate has **not** yet passed independent Vivado 2025.2
implementation or KV260 validation; no P03.2c hardware acceptance is
claimed. If the four A53 reads pass, the next gate remains the full
page/debug/dispatch smoke, not merely a successful route.
