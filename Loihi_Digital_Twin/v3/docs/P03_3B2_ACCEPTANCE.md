# P03.3b2 — Physical Cortex-A53 runtime-to-hardware adapter acceptance

**Status:** ACCEPTED (user independently ran physical KV260 test).  
**Local date:** 2026-10-11 (UTC evidence directory dated 2026-10-12).  
**Branch:** `agent/v3-p03-autonomous-runtime`, unmerged.  
**Candidate FPGA:** Accepted `M_AXI_HPM0_FPD` PS 128-bit AXI4,
SmartConnect to original 32-bit AXI4-Lite P03 register bank
`0xA4000000` and separate P02 128-bit HP0 DDR data path.

## Independent physical evidence

The user provided the tail of `run_p03_3b2_probe.sh` and then separately
displayed the new evidence directory's `verify.log`:

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
PASS: P03.2c standalone ELF downloaded to Cortex-A53 #0
P03.2c physical mailbox target: PSU
PASS: P03.2c A53 smoke executed and 64-byte mailbox dumped
PASS: P03.3b2 physical A53 adapter probe ps_width=128 id=0x4C543302 config0=0x14001000 page_bytes=438272 page_ins=1 dispatches=2 barriers=2
P03_3B2_VERIFY_EXIT=0
P03_3B2_EVIDENCE_DIR=/tmp/v3_p03_3b2_20261012T025233Z
PASS: P03.3b2 physical Cortex-A53 two-timestep runtime-adapter probe
```

Independent verification log:

```text
PASS: P03.3b2 physical A53 adapter probe ps_width=128 id=0x4C543302 config0=0x14001000 page_bytes=438272 page_ins=1 dispatches=2 barriers=2
```

These were **real** outputs from the standalone Cortex-A53 running
`p03_rt_execute()` with physical `p03_hw_adapter.c`,
`p03_hw_runtime_bridge.c` and the Xilinx BSP MMIO implementation,
not merely the earlier hand-coded P03.2c smoke or host C simulator.

The independent 64-byte mailbox verifier required:

- live PS HPM0 width selector = **128-bit**;
- matching ID/VERSION/CAPABILITIES;
- accepted P02 backing DDR page-in of exactly **438272 bytes**;
- successful resident `config[0]=0x14001000` MMIO debug read;
- **one** initial page-in and **two** completed HLS dispatches;
- **two** completed timestep barriers; zero sticky runtime faults;
- completed runtime execution and correct record identity.

## Scope boundary

**Accepted:** initial real A53 scheduler-to-MMIO/runtime adapter
integration for **one logical core, one resident slot, two timesteps,
zero packets**, with correct count/status handling.

**Not accepted by this result:** real emitted packet decoding/routing,
nonresident DDR NEXT event insertion, dirty 104 KiB page-out and
reload, resident destination routing, multi-core scheduling and golden
trace equivalence. These require dedicated P03.3b3/P03.4 tests.

The exact ELF/XSA/bitstream SHA256 hashes and full raw physical evidence
are retained in the user's local evidence folder; they were not
provided in the chat and must not be invented.

**Decision: P03.3b2 ACCEPTED; proceed to P03.3b3.**
