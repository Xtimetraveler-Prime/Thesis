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
