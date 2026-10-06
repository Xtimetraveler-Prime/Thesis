# P03.2b Routed HPM0/MMIO Integration Acceptance

**Phase:** P03 — Autonomous PS-resident runtime  
**Sub-milestone:** P03.2b — Routed HPM0 integration  
**Accepted:** 2026-10-06  
**Branch:** `agent/v3-p03-autonomous-runtime`

## Result

P03.2b is accepted.

The PS-visible MMIO shell routed successfully on K26 with the accepted P02 HP0
DDR page data path retained and the new PS HPM0 control path added.

The already-routed project was advanced from:

```text
route_design Complete!
```

to:

```text
write_bitstream Complete!
```

and then exported a fixed XSA including the run-owned bitstream.

## Accepted routed evidence

```text
wns_ns=+0.539
whs_ns=+0.010
resident_context_slots=3
physical_engines=1
uram=47
hp0_data_width_bits=128
hpm0_data_width_bits=32
mmio_base=0xA4000000
mmio_range_bytes=0x00001000
```

The accepted address window is:

```text
0xA4000000 .. 0xA4000FFF
```

Vivado reserved this as a 4 KiB HPM0 SmartConnect window.

## Accepted artifacts

```text
bitstream_sha256=8b4d1d3996147e73bbe71ec2a5036f0a4d23efc5cc3fe3d25237f855acf72119
probes_sha256=a745b96c24f4e01480d1d89d706e90c52c822b4a7fda7ea43d2ad794a0b86def
xsa_sha256=703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40
```

Files:

```text
vivado/build/p03_2_mmio_impl/reports/p03_2_ps_mmio.bit
vivado/build/p03_2_mmio_impl/reports/p03_2_ps_mmio.ltx
vivado/build/p03_2_mmio_impl/reports/p03_2_ps_mmio.xsa
```

## What this proves

P03.2b proves that:

- `M_AXI_HPM0_FPD` is enabled as the PS-to-PL control direction;
- the PS master reaches the custom 32-bit AXI4-Lite register block;
- the register block is mapped at the fixed 4 KiB HPM0 window;
- the accepted P02 HP0 DDR path remains enabled in the opposite PL-to-DDR
  direction;
- page, dispatch, and resident-memory command ownership is wired to the MMIO
  block rather than VIO;
- VIO remains observation/reset-only;
- timing closes at the 100 MHz PL clock;
- resource usage remains within K26 capacity;
- a fixed XSA suitable for Vitis standalone software is available.

## Route-attempt note

The first P03.2 route attempt physically routed successfully but stopped at
fixed-XSA export because `impl_1` had been launched only through
`route_design`.

The corrected flow now runs:

```tcl
launch_runs impl_1 -to_step write_bitstream
```

before `write_hw_platform -include_bit`.

The accepted artifact set above was recovered from the already-routed project
without repeating placement/routing.

## Acceptance boundary

P03.2b does not yet prove that Cortex-A53 software can physically access and
operate the MMIO block.

That is P03.2c.

Primary records:

- `docs/P03_2_PS_MMIO_CONTROL.md`
- `docs/P03_2_ROUTE_ATTEMPT1.md`
- this acceptance record
