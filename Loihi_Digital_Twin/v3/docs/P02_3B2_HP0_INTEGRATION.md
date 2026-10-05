# P02.3b2 — K26 HP0 DDR Integration

**Status:** Verification candidate  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Date drafted:** 2026-10-05

## 1. Purpose

P02.3b2 connects the accepted P02.3a page semantics and P02.3b1 AXI transport
to a real Zynq UltraScale+ PS high-performance DDR ingress path.

The shell is derived from the accepted P08 one-engine / three-resident-context
implementation. The existing HLS compute engine, three full resident contexts,
dispatch controller, reset strategy, 100 MHz PL clock, and debug interface are
retained.

The new physical path is:

    resident Port B
        <->
    P02.3a page walker
        <->
    fixed DDR range guard
        <->
    P02.3b1 128-bit AXI burst adapter
        <->
    AXI SmartConnect
        <->
    PS S_AXI_HP0_FPD
        <->
    K26 DDR

## 2. Source-backed PS interface mapping

AMD PG201 identifies `S_AXI_HP0_FPD` as a PL-master ingress into the PS full
power domain and names the corresponding PS AXI signal group `SAXIGP2`.

The Zynq UltraScale+ PS configuration parameters used by this project are:

    PSU__USE__S_AXI_GP2       = 1
    PSU__SAXIGP2__DATA_WIDTH  = 128

The shell also drives:

    zynq_ultra_ps_e_0/saxihp0_fpd_aclk

from the same 100 MHz PL clock used by the page path.

SmartConnect is used between the custom AXI master and the PS slave port so AXI
interface adaptation remains explicit and tool-managed.

## 3. Physical backing reservation

P02.3b2 freezes the first physical backing-window candidate as:

    base   = 0x4000_0000
    bytes  = 0x0400_0000
    end    = 0x4400_0000 exclusive
    stride = 0x0008_0000 = 512 KiB
    slots  = 128 logical-core record addresses

This is a **project implementation choice**, not a native-Loihi address and not
an AMD-required address.

The complete region is inside the HP0 DDR-low mapping used by the Vivado design.

Before the future A53 runtime is linked, this 64 MiB window must be reserved so
that application code, heap, stack, DMA buffers, or other software allocations
cannot overlap it.

P03 must record that reservation in the standalone linker/memory map.

## 4. Transport containment

`p02_ddr_backing_range_guard.v` is inserted between the page walker and the AXI
adapter.

It rejects any scalar request whose byte range is not wholly contained in:

    [0x4000_0000, 0x4400_0000)

This is deliberately separate from:

- P02.3a record-base alignment checking;
- P02.3b1 AXI size/alignment/protocol checking.

The three checks answer different questions:

1. is this a legal logical-context record command?
2. is this access inside the reserved physical DDR region?
3. is this access legal for the AXI transport?

## 5. Port-B ownership

The accepted P02 page/debug arbiter remains the only path to resident-memory
Port B.

For P02.3b2 it is strengthened so `debug_busy` is asserted immediately when a
new debug request is present. This prevents the dispatch controller from
starting compute in the request-to-fabric acceptance cycle.

The page walker's `busy` signal explicitly drives the arbiter's
`page_active` ownership input.

Therefore:

- compute is blocked while paging owns Port B;
- debug is blocked while paging owns Port B;
- paging receives a memory-fabric error if a page command is improperly started
  while compute already owns the fabric;
- P03 will later prevent that illegal ordering in software before issuing the
  command.

## 6. Vivado shell

The new project generator is:

    vivado/create_p02_ddr_impl_project.tcl

It supports two stages:

    synth
    route

The shell adds:

- `p02_context_page_bank_walker`;
- `p02_page_host_arbiter`;
- `p02_ddr_backing_range_guard`;
- `p02_axi128_burst_adapter`;
- one-input / one-output AXI SmartConnect;
- enabled PS `S_AXI_HP0_FPD`;
- a dedicated paging VIO.

The original P08 dispatch/debug VIO remains separate.

## 7. Paging VIO bring-up contract

P02.3b2 intentionally keeps page-command issuance on VIO for hardware bring-up.

Outputs:

    0  page start
    1  page-out direction
    2  mutable-only page-out
    3  resident slot
    4  64-bit DDR record base

The default record base is:

    0x0000_0000_4000_0000

Inputs expose:

- page busy;
- page done;
- start blocked;
- semantic bytes transferred;
- completed transfers;
- last page cycles;
- page command/host/DDR errors;
- completed AXI read/write bursts;
- AXI bytes moved;
- AXI protocol error;
- backing-range error;
- pending coalesced write bytes.

This VIO is a temporary P02 bring-up mechanism. It is not the final autonomous
runtime interface.

## 8. Address mapping

The custom AXI master's address space is explicitly mapped to:

    zynq_ultra_ps_e_0/SAXIGP2/HP0_DDR_LOW

with:

    offset = 0x0000_0000
    range  = 0x8000_0000

The local range guard then restricts the page engine itself to the 64 MiB
project backing reservation.

## 9. Verification stages

### 9.1 Preflight

`scripts/run_p02_3b2_preflight.sh` reruns:

- 14 focused P02 Python tests;
- complete P02.3a page-walker XSIM;
- complete P02.3b1 AXI coalescer XSIM;
- DDR range-guard XSIM.

### 9.2 Integration synthesis

`vivado/run_p02_ddr_integration_synth.sh`:

1. runs the P02.3b2 preflight;
2. packages the accepted HLS compute IP;
3. creates the K26 block design;
4. enables/configures HP0;
5. connects the AXI page path;
6. validates the block design;
7. synthesizes the complete design;
8. records resource and topology metrics.

The synthesis gate requires:

- three resident contexts;
- one physical engine;
- unchanged logical-capacity contract;
- 128-bit HP0;
- 256-byte AXI transport units;
- fixed 64 MiB range guard;
- no more than 64 K26 URAMs.

### 9.3 Route

`vivado/run_p02_ddr_impl.sh` performs the routed implementation and requires
non-negative setup and hold slack before producing:

    p02_ddr_paged.bit
    p02_ddr_paged.ltx
    p02_ddr_post_route.dcp

The route stage is intentionally not the first independent gate. Synthesis
should be verified first so block-design/interface errors fail quickly.

## 10. P02.3b2 acceptance boundary

P02.3b2 can close only after independent evidence shows:

1. focused P02 software tests pass;
2. walker/coalescer/range-guard RTL simulations pass;
3. the HP0 block design validates in Vivado 2025.2;
4. the full shell synthesizes for `xck26-sfvc784-2LV-c`;
5. the shell still contains three resident contexts and one HLS engine;
6. URAM usage remains within the K26's 64 URAM288 blocks;
7. the subsequent routed design has non-negative WNS and WHS;
8. bitstream/probes identities are recorded.

Even after those pass, P02.3b2 only proves that the DDR page path is physically
integrated and routable.

P02.4 must still prove actual DDR-backed save/load behavior with known context
data on the KV260.
