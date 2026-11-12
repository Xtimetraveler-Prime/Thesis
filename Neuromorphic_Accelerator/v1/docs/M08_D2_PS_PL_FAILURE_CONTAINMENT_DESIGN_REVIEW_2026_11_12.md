# M08 D2 — offline PS↔PL failure-containment design review and fault simulation

**Date:** 2026-11-12. **Gate:** D2 source-only review; original M08 image quarantined; NO physical PS register access, FPGA manager programming, JTAG, fan or boot changes; D3 new corrected image NOT created/authorized. PR #83 draft/unmerged.

## 1. Proven baseline vs unproven runtime

**Owner original physical evidence:** after the first M08 identity-mode access attempt, an SSH session was lost and Linux serial showed RCU/timer stall warnings; no dependable returned register data, ESR, AXI trace, or proof the code reached a specific identity address. The board was recovered to stock by a hard power cycle. The original M08 `.bit.bin` SHA `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` remains quarantined. See the authoritative incident document.

**Source-level M08 topology:**

```text
ARM/Linux normal loads/stores (HPM0 upstream PS/FPD)
   │   PS FPD main interconnect  [ATB INSTANCE 4 — configuration UNKNOWN]
   ▼
PS M_AXI_HPM0_FPD (128-bit design setting)
   │  PS pl_clk0 -> maxihpm0_fpd_aclk / SmartConnect / slaves
   ▼
PL SmartConnect S00_AXI 1SI / 2MI
   ├── M00_AXI -> identity (0xA0000000, 4KiB; read-only)
   └── M01_AXI -> page shell (0xA0001000, 4KiB; DISPATCH disabled)
ps/pl_resetn0 -> inverter -> proc_sys_reset -> fabric resets
proc_sys_reset/dcm_locked = logic_one, NOT a measured clock lock
```

The routed fan-preserving Vivado design passed nominal clock/timing constraints but this does not prove active Linux PL0, deasserted reset or valid HPM0 width/AFI configuration. The *decompiled original owner DTBO* SHA recorded `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` confirms only `fpga_full` firmware + four reset references and **two separately placed `&amba` generic-UIO nodes**. It has no `assigned-clocks`, `assigned-clock-rates`, `clocks`, `clock-names`, `xlnx,fclk`, `xlnx,afi-fpga`, or `config-afi`. Stock original DTBO and failed-boot firmware/PS registers remain UNAVAILABLE: **the absence in M08 does not prove an actual clock/AFI failure**.

## 2. Full lifecycle boundary, proposed safe invariant

| Stage | Required independently reviewed invariant | Currently proven? |
| --- | --- | --- |
| BEFORE reconfiguration | Prevent *new* PS HPM0 transactions, quiesce/drain outstanding transactions, stop old mappings/driver users; establish active bridge isolation or error responders before stopping/resetting PL clock | **NO** |
| Clock/reset programming | Identify owner for PS `PL0_REF_CTRL.CLKACT`, Linux clocks, `pl_resetn0`, `proc_sys_reset`; prove clock active at runtime and downstream reset synchronized after clock stable | **NO** |
| PS AXI width/AFI | Independently compare M_AXI_HPM0_FPD 128-bit PS design to Linux/boot AFI data; do not copy generator values without proving old owner/target | **NO** |
| Downstream enumeration | Verify FPGA-region versus independent AMBA UIO population order and driver clock dependencies; expose UIO resource only after bridge/clock/reset readiness | **NO** |
| Fault boundary | PS/FPD-clocked timeout before PL and verified error response for missing AR acceptance or missing R; no reliance on `pl_clk0` or a Python/signal timeout | **NOT IMPLEMENTED/VERIFIED** |
| First timeout | At most one outstanding owner diagnostic transaction; stop ALL subsequent reads; record error; quiesce/isolate; escalate to controlled restart instead of retry | **OFFLINE MODEL ONLY** |
| Recovery/fan | Stock Linux/XRT/FPGA manager rollback and independent fan cooling through PL replacement; original stock and M08 source hashes preserved | **NOT VERIFIED** |

The requested D2 simulation explores only the PS timeout and poison portions as an *abstract behavioral contract*. Other rows stay blocking for hardware.

## 3. Vendor mechanisms and why they are not yet an implementable fix

**ATB4:** AMD UG1085 explicitly identifies **instance 4** in the FPD main interconnect ahead of `M_AXI_HPM0_FPD`. Configurable `ATB_RESP_EN`, `ATB_RESP_TYPE`, FPD `ATB_PRESCALE` and optional interrupt enable are described, but failed-boot values are UNKNOWN. AMD recommends **boot-time configuration**; runtime changes require quiescing all relevant masters/outstanding transactions. Tracking is **fewer than 16** transactions; **restart after first timeout** is recommended. We **do not** include a runtime register recipe or attempt to enable ATB on the recovered stock system. Exact firmware/kernel ownership and FPD clock independence must be verified before D3. **A simulated `SLVERR` is NOT proof of the physical ATB response.**

**AIB / isolation:** AMD documents isolation blocks that stop new transactions and can respond with SLVERR *or* cause timeout, dependent on configuration, while waiting for posted transactions to complete. This is **not** a license to isolate or reset hardware with uncompleted transactions. Confirm the relevant PS/PL bridge path and its actual stop/ack behavior; an ordinary PL-based AXI firewall/timeout may also stop with `pl_clk0` and cannot replace upstream PS-side protection.

**Linux FPGA region/driver:** Linux region programming can disable declared bridges, program the fabric and reenable them, then make child devices available. M08's UIO nodes were authored as **independent `&amba` siblings**, not under the FPGA region, with no per-device clock dependencies. Actual installed `dfx-mgr`, FPGA region, generic UIO and firmware lifecycle must be checked offline against the *specific boot components*, not inferred from a generic binding. Do not assume adding a speculative `fpga-bridges` property alone fixes this.

**Clock/AFI ownership:** AMD's ZynqMP FPGA Manager example and 2025.2 device-tree generator illustrate PS-to-PL `assigned-clocks`, PL clock consumers, and AFI width configuration. The missing properties in original M08 are a **configuration-ownership gap**; stock FSBL/PMU/boot/Linux could have supplied them. The complete *as-applied* failed-boot DT and registers were not captured; the owner-stock DTBO was not found on the PC. New DT changes must be derived from the specific XSA/PS configuration and valid kernel clock ids, *not* guessed.

References:
- UG1085 ATB instances: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances
- UG1085 ATB programming/safety: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming
- UG1085 AIB isolation semantics: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/AIB-Isolation-Functionality
- Linux FPGA region sequencing: https://kernel.org/doc/html/next/driver-api/fpga/fpga-programming.html
- AMD ZynqMP Linux FPGA Manager overlay examples: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847
- AMD 2025.2 generator: https://github.com/Xilinx/system-device-tree-xlnx/blob/xlnx_rel_v2025.2/device_tree/data/device_tree.tcl

## 4. Offline simulation implementation and cases

**New source:** `rtl/m08/tb_m08_d2_ps_domain_timeout_contract.sv` defines `m08_d2_abstract_ps_read_guard` and a dedicated testbench. **ONLY TESTBENCH / NOT SYNTHESIZABLE PS ATB.** It has its own 10ns simulation PS clock, a separately stoppable 14ns PL clock, and abstract downstream AXI-Lite **read** ready/valid observations (not a physical asynchronous AXI CDC implementation). It models a single outstanding PS read and two waiting phases: `WAIT_AR` (no downstream address handshake) and `WAIT_R` (downstream address accepted, no response). After six PS cycles without a handshake, it holds synthetic `SLVERR` while upstream RREADY is low, then remains sticky poisoned and refuses any subsequent AR. A normal read returns correct data and holds RVALID with RREADY backpressure.

**Actual simulated conditions:**

| Scenario | Asserted offline behavior | What is NOT established |
| --- | --- | --- |
| Normal read + RREADY backpressure | Correct data/OKAY, response held until handshake, no poison | AMD SmartConnect actual behavior |
| Downstream ARREADY absent | Timeout in bounded *PS* cycles, synthetic SLVERR, sticky poison | PS ATB4 actually enabled or RRESP supported |
| AR accepted but RVALID missing | Timeout in bounded *PS* cycles, poison, late response ignored at abstract boundary | Downstream transaction drained or discarded; protocol-compliant bridge |
| PL clock stopped before AR acceptance | Abstract PS clock still advances timeout; no PL edges observed | Real PS↔PL clock ownership and CDC |
| PL clock stopped after AR acceptance | Abstract PS clock still advances timeout; no PL edges observed | Actual PS/SmartConnect pending AR/R resolution |
| PS clock stopped | **NEGATIVE:** timeout does NOT advance at all; only resumes after PS clock resumes | Independent PS clock always active on real board |

All error/poison assertions use the abstract model. It **does not instantiate** the physical ZynqMP PS, AXI HPM0, SmartConnect, FPGA region/bridge, real ATB, operating system or actual fan. The original first-party slave stall RTL tests remain separate and prove only their own narrow scope. The abstract model holds `m_rready=0` after timeout; **an accepted downstream AR may remain outstanding**. This is *explicitly a FAILURE of the D3 hardware-containment gate* until upstream hardware handling, quiescence, late-response disposition and safe restart are proved. No generated `.bit`, DTBO or corrected image is produced.

`tests/test_m08_d2_ps_domain_fault_containment.py` checks static integration boundaries/quarantine and compiles/runs the HDL with actual `iverilog`/`vvp`. If Icarus is unavailable, only the simulation test is **SKIPPED** and no RTL PASS can be claimed; the GitHub Actions M08 job installs Icarus and exercises it natively.

Expected seven real Icarus stdout markers:

```text
M08_D2_GUARD_NORMAL_READ_AND_BACKPRESSURE_PASS
M08_D2_GUARD_MISSING_ARREADY_TIMEOUT_AND_POISON_PASS
M08_D2_GUARD_MISSING_RVALID_LATE_RESPONSE_QUARANTINE_PASS
M08_D2_GUARD_PL_CLOCK_ABSENT_UPSTREAM_BOUNDED_PASS
M08_D2_GUARD_PL_STOPPED_AFTER_AR_TIMEOUT_PASS
M08_D2_GUARD_PS_CLOCK_ABSENT_IS_UNPROTECTED_NEGATIVE
M08_D2_GUARD_ABSTRACT_PS_DOMAIN_CONTRACT_ALL_PASS_NO_HARDWARE_PROOF
```

## 5. Next D3 candidate entry gates (NOT authorized yet)

1. **Boot-time PS-side protection plan** must identify who configures ATB4 and what reliable, bounded response the actual hardware produces under PL0 absent and reset asserted. It must prove outstanding transactions are drained/isolated before and after first timeout and prevent all retries. Test with AMD native PS/FPGA simulation or hardware-independent approved model; the current abstract contract is not sufficient.
2. **PS/PL configuration plan** must derive actual PL0 clock, `M_AXI_HPM0_FPD` width/AFI and reset ownership from a reviewable XSA and stock kernel/device-tree/FSBL/PMU/software integration. Missing stock original DTBO is a known limitation, not permission to invent. Avoid live register reads/writes on board.
3. **Linux sequencing plan** must prove no UIO mapping access before PL clock stable, reset released and bridge enabled; quiescent transition back to stock, with independent fan cooling. Consider whether nodes should be region children instead of unrelated `&amba` fragments, validated against real kernel manager behavior.
4. **New candidate architecture** may add ILA/AXI Protocol Checker, reset/clock liveness instrumentation, and versioned DT/firmware only AFTER upstream protection choice. An ILA using absent PL0 cannot observe that absence; use a genuinely independent observation domain.
5. Preserve old quarantined firmware exactly; new hardware candidate must use unique names, new native 2025.2 build, implementation/DRC/timing/CDC/resets, source hashes and independent operator evidence. D3 image generation can be considered later, but there is **no permission to install, boot or access an image** until owner approves after protection and cooling validation.

## 6. PC verification

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d2_ps_domain_fault_containment.py' -v
python3 -m unittest discover -s tests -p 'test_m08_ps_pl_stall_forensics.py' -v
python3 -m unittest discover -s tests -p 'test_m08_post_incident_mmio_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Native direct offline Icarus, no board:
command -v iverilog
command -v vvp
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_d2_ps_domain_timeout_contract \
  -o "$TMP/m08_d2_ps_guard.vvp" rtl/m08/tb_m08_d2_ps_domain_timeout_contract.sv
vvp "$TMP/m08_d2_ps_guard.vvp"
```

**Decision:** D2 behavioral boundary simulation can pass; **D3 protected physical image gate remains BLOCKED** until a real upstream PS timeout/isolation configuration and complete clock/AFI/bridge lifecycle plan exist. No change to stock K26 or original deployed M08.
