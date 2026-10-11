# P03.2c HPM0 System ILA Diagnosis

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
