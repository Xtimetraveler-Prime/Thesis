# M08.2b D0/D1 forensic source review and first D2 offline fault tests — 2026-11-12

**Status: INVESTIGATION OPEN; original M08 PL image QUARANTINED; NO physical MMIO.**
This document supplements, but **does not replace**, the authoritative
[M08.2b.3 first-identity RCU-stall incident and D0–D5 plan](M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md).
PR #83 remains DRAFT/UNMERGED. This source-only review did **not** access a
KV260, original owner DCP, Vivado 2025.2, /dev/uio, /dev/mem, or JTAG.

## D0: original incident evidence scope

The incident records three original uploaded files, separately SHA identified:
`01_identity_original.log` 73 bytes, SHA256
`41a692f58008b42b3381bb02039a67b03f779d3d521351bad45a51271bd46e3a`;
`02_identity_exit.txt` 16 bytes, SHA256
`e24b46ec0eb8fb4f2b497e7efd508bc7e70bab830aaeb1b6d967c9cee3f3a31c`;
and PuTTY `image.png`, SHA256
`6cf3c88bd5a582c740cc04748892ec280b108b53bb226301c949785bb0078697`.
The **original bytes are not in this source checkout** and were NOT rehashed in
this follow-up. Do not conflate cited older evidence receipts with independently
re-inspected original crash files. A complete immutable incident SHA-ledger
archive is still outstanding.

The observed `exit_status=255` is an SSH failure; `rcu_preempt` stalls,
starved RCU grace-period thread, and possible timer issue are genuine symptoms,
**not an MMIO address/AXI error response, PS exception frame or root-cause
proof**. There was no pre-read breadcrumb. The possible phase is preflight,
UIO open/mmap, first identity read, later identity read or page header read.
The stock post-reboot firmware state is not evidence of the pre-crash PL0
clock/reset, PS isolation or firmware manager rollback.

**Safe, optional D0 diagnostics** on the *recovered STOCK image only*:
read-only `uname -a`, `cat /proc/cmdline`, `cat
/proc/sys/kernel/random/boot_id`, `journalctl --list-boots`,
`journalctl -k -b -1` (expected unavailable), `systemctl is-active
dfx-mgr fancontrol`, `cat /sys/class/fpga_manager/fpga0/state`,
`sudo xmutil listapps`, current temperature paths and `ls -al
/sys/fs/pstore /var/lib/systemd/pstore`. Inspect `/sys/kernel/debug/clk/clk_summary`
**only if already mounted and readable**; do NOT mount debugfs, write
clock/reset controls or infer original M08 runtime state from stock.
Preserve outputs in an exclusive new owner evidence directory with SHA256
receipt; do not replace previous originals.

## D1: exact first-party source path

Source: `scripts/m08_page_ps_bd_candidate.tcl` (unchanged quarantined baseline)
and fan-preserving wrapper `scripts/m08_path_a_fan_bd_candidate.tcl`:

```text
PS zynq_ultra_ps_e
  CONFIG.PSU__USE__M_AXI_GP0 = 1   (FPD HPM0, 128-bit)
  CONFIG.PSU__USE__M_AXI_GP1/2 = 0
  CONFIG.PSU__FPGA_PL0_ENABLE = 1
  PS pl_clk0 (nominal requested 100MHz; native BD observed 99,999,001 Hz)
           |-> maxihpm0_fpd_aclk
           |-> ctrl_sc/aclk
           |-> identity/aclk ; page/aclk ; pl_reset/slowest_sync_clk
  PS pl_resetn0 -> reset_inv (NOT) -> pl_reset/ext_reset_in
  logic_one -----------------------> pl_reset/dcm_locked [TIED 1]
  logic_zero ----------------------> pl_reset/aux_reset_in, mb_debug_sys_rst
  pl_reset/interconnect_aresetn -> ctrl_sc/aresetn
  pl_reset/peripheral_aresetn   -> identity/aresetn ; page/aresetn

PS M_AXI_HPM0_FPD -> ctrl_sc/S00_AXI (SmartConnect 1 SI / 2 MI)
  ctrl_sc/M00_AXI -> identity/S_AXI (read-only, 8-bit local offset)
  ctrl_sc/M01_AXI -> page/S_AXI (shell, 12-bit local offset)
Native owner BV/route address record:
  identity: PS 0xA0000000 / 4 KiB
  page:     PS 0xA0001000 / 4 KiB
Overlay source and live UIO metadata agree with these addresses.
```

Vivado `validate_bd_design -force` and the routed timing report verify a
**nominally configured and constrained design**, not that Linux-managed
runtime enables PL0, has released all relevant resets, leaves HPM0 and its
power/isolation bridge usable, or returns AXI responses. The `dcm_locked`
tie-high is a design choice that **does not measure clock lock or clock
presence**; `proc_sys_reset` requires a clock to operate correctly.
The `RTSTAT-10` warning was *15 counted* internal SmartConnect
`mi_handler_m_sc_areset_pipe` reset-pipeline nets (14 names printed),
not an identified timing/DRC failure and NOT proof of being harmless.
Original owner route report: WNS +5.469ns, WHS +0.015ns, no
unconstrained internal endpoints; neither demonstrates successful MMIO.
The first-party original generated BD export, routed DCP, bitstream bytes,
and Linux/PS clock/isolation register state are **not attached for
independent re-inspection here**. Those exact owner originals must be
cross-checked before attempting to explain RTL-vs-physical behavior.

The identity RTL registers `RVALID` on the same `aclk` edge that accepts
`ARVALID && ARREADY`, holds RDATA/RRESP while `RREADY=0`, and rejects
writes with SLVERR. `ARREADY` is gated by `aresetn` and an outstanding
read, but in a **halted clock** can be combinationally high without any
AR handshake *edge*. Thus a healthy standalone identity RTL can still
never respond if the clock does not run. The page adapter has a bounded
`host_wait_count==63` watchdog inside `ST_HOST_WAIT`; it only covers its
internal bank response when the **page RTL clock is running**. It does
not protect the PS→SmartConnect→identity path, missing AR handshakes, or
a stopped PL clock.

The old physical operator calls `inspect_identity`, `check_idle_pair`,
and eventually multiple identity+page reads **without an externally
visible pre-each-register breadcrumb**; although now quarantined, this
explains the forensic ambiguity. The alternative legacy MMIO entry point
is quarantined independently. **Never run old copies staged on the KV260.**

### Hypotheses and discriminating evidence

| Hypothesis | Strength | Distinguishing *future* evidence |
| --- | --- | --- |
| PL0 clock stopped / reset held / HPM0 not enabled after dfx-mgr load | Leading, unproven | Actual failed-image clock/reset runtime state, PS isolation/clock controls from safe trusted instrumentation **before** MMIO; independent observable PL-clock alive signal; Vivado clock/reset domain reports |
| SmartConnect decode/handshake or reset-pipeline issue | Serious, unproven | Original routed DCP/netlist vs source BD + native IP simulation; AXI checker/ILA at SI and MIs, exact AR/R traces, review RTSTAT-10 fanout and reset connectivity |
| Physical mapping / security / Linux manager issue | Possible | Original deployed XSA/address export, UIO live DT and PS memory map, kernel exception/ESR if available, sequencing and manager logs |
| Linux RCU/timer failure unrelated to AXI | Possible | Original timestamped serial and full CPU backtraces/timer interrupts, journal/pstore when available, independent reproduction only by safe Linux observation **without old PL MMIO** |

In particular, pre-read serial breadcrumbs must establish a test reached
a PS register transaction *before* interpreting lack of RVALID as causal.

## D2: offline tests added; what they do NOT prove

- `rtl/m08/tb_m08_axil_identity_stall_forensics.sv` instantiates the **real
  first-party identity RTL**, exercising AR refused under reset, a fresh
  accepted AR/R, 25 cycles of RREADY backpressure and blocked second AR,
  reset in the middle of an unconsumed response, and stopped-`aclk`
  where no response is produced. It also contains a **separate deliberate
  no-ready/no-response mock** held for 64 running-clock cycles. That
  negative fixture explicitly reports *NO PROTECTION*: it does not claim
  a real protected PS path.
- `tests/test_m08_ps_pl_stall_forensics.py` checks static original
  PS/SmartConnect/clock/reset topology, fan route, narrow page watchdog,
  DRC warning and UIO address agreement, incident scope and safety
  quarantine. If Icarus is installed it compiles/runs the fault TB and
  demands five unique markers and zero warnings/failures. If absent,
  simulation is **SKIPPED, not PASS**. All source-only, not Vivado IP sim.
- Existing M08 standalone identity and page BFM tests remain required.
  Neither the new nor old tests simulate genuine PS IP, SmartConnect,
  physical reset, kernel MMIO or a locked-up ZynqMP, so they cannot
  confirm the physical failure cause or a fixed system.

### Protection engineering decision (not implemented yet)

A Python process/SSH timeout is **not** a hardware AXI timeout. Candidate
protections for an independently versioned D3 design:

1. **ZynqMP PS ATB, on the actual FPD HPM0 path**: UG1085 describes
   configurable SLVERR and timeout, but the FPD instance selection,
   actual kernel/firmware boot ownership, clock behavior, response enable
   and correct ordering must be proven. **Do not write these registers on
   the recovered stock system.** AMD explicitly warns that the limited
   ATB transaction tracking can hang again after repeated timeout
   responses and recommends a restart after the **first timeout**.
   Ref: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming
2. **AMD AXI Protocol Firewall IP (PG293)**: evaluate MI-side blocking
   on no ARREADY/RVALID and compliant completion of outstanding
   requests; verify actual Vivado 2025.2 licensing/availability and
   timeout configuration. A PL-clocked firewall **cannot be assumed to
   protect against a completely absent PL clock**. Any own RTL
   timeout/SLVERR producer must likewise prove it does not leave
   unresolved downstream transactions in SmartConnect.
   Ref: https://docs.amd.com/r/en-US/pg293-axi-firewall/Features
3. **Isolation/readiness gating and instrumented capture**:
   arrange robust clock/reset sequencing and independently verified
   quiescence before any PS access. Consider an ILA plus AXI Protocol
   Checker at HPM0/S00 and both M00/M01, preserving clocks, READY/VALID,
   RDATA/RRESP and address in a new diagnostic image. ILA clocked by
   `pl_clk0` cannot capture **if that very clock is absent**; a
   separately clocked liveness indication or trustworthy PS-side
   status must cover that case.

D3 is **NOT AUTHORIZED** yet: no safe replacement bitstream, original
vendor rerun, full timeout/isolation demonstration, real clock enable
proof, or original SHA-backed D3 artifacts exist. Do not program a new
or old image or resume physical identity/page tests. A future first
hardware probe will require a **separately reviewed versioned image**,
durable before/after breadcrumbs for just **one 32-bit identity
register**, actual protection validation, owner approval and recorded
UART/recovery evidence. D5 64-word page/COMMIT remains blocked.

## PC-only verification (NO BOARD)

```bash
cd /home/dna/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_ps_pl_stall_forensics.py' -v
python3 -m unittest discover -s tests -p 'test_m08_post_incident_mmio_quarantine.py' -v
# Require real Icarus outputs; a Python SKIP is NOT an RTL PASS.
command -v iverilog
command -v vvp
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_axil_identity_stall_forensics -o "$TMP/m08_d2.vvp" \
    rtl/m08/m08_axil_readonly_identity.v \
    rtl/m08/tb_m08_axil_identity_stall_forensics.sv
vvp "$TMP/m08_d2.vvp"
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

All proof labels are **OFFLINE SOURCE/RTL ONLY**; the original physical
bit.bin SHA `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`
remains QUARANTINED.
