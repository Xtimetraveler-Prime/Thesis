# P02.3b2 Synthesis Acceptance Record

**Phase:** P02 — DDR-backed logical-core virtualization  
**Sub-milestone:** P02.3b2 — HP0 Vivado integration  
**Synthesis accepted:** 2026-10-05

## Independent verification

The P02.3b2 synthesis gate was independently rerun with reduced Vivado
parallelism after the original four-job run exhausted host memory.

Observed completion:

```text
PASS: P02.3b2 HP0 integration synthesis gate completed successfully.
SCRIPT_EXIT=0
```

The same run also reproduced:

- P02.3a page-walker RTL PASS;
- P02.3b1 AXI burst-adapter RTL PASS;
- P02.3b2 DDR range-guard RTL PASS;
- complete P02.3b2 preflight PASS;
- successful HP0 DDR-low address assignment;
- successful block-design validation;
- successful generation of the HP0 SmartConnect and custom paging blocks.

## Accepted synthesis boundary

This evidence accepts the **synthesized integration topology**:

- one P03-compatible HLS physical engine;
- three full resident context slots;
- P02.3a page walker;
- Port-B page/debug arbiter;
- fixed 64 MiB DDR backing-window guard;
- accepted P02.3b1 128-bit AXI burst adapter;
- SmartConnect;
- PS `S_AXI_HP0_FPD` DDR ingress;
- 128-bit HP0 contract;
- 256-byte / 16-beat AXI transport contract.

The remaining `AWUSER_WIDTH` and `ARUSER_WIDTH` messages are Vivado warnings,
not validation or synthesis failures. They are not treated as an acceptance
blocker unless route/DRC later promotes them into a functional or timing issue.

## Host-memory observation

The original synthesis attempt with the script default of four concurrent
Vivado jobs exhausted host memory. A single-job run completed normally.

P02.3b2 synthesis and route scripts therefore default to:

```text
VIVADO_JOBS=1
```

The environment variable can still override that default on a higher-memory
machine.

This is a host-tool resource constraint. It is not evidence of K26 FPGA
resource exhaustion.

## What remains unproven

Synthesis acceptance does **not** yet prove:

- routed timing closure;
- post-route K26 resource counts;
- bitstream generation;
- physical DDR page-in/page-out correctness;
- board-local autonomous runtime behavior.

The next gate is the P02.3b2 routed implementation. P02.4 remains responsible
for physical DDR-backed paging acceptance on the KV260.
