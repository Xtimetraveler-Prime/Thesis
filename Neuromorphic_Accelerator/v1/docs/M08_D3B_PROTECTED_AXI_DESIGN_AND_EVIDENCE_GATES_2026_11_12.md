# M08 D3.2A — versioned protected-AXI architecture and evidence-locked integration design

**2026-11-12 • Research branch:** `agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design`, based on the D3.1 source/native candidate branch, NOT on deployed firmware. **Status: D3.2 architecture and offline contract model started; D3.2 physical corrected image NOT BUILT/NOT AUTHORIZED.** Original M08 `.bit.bin` SHA `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` is still quarantined; stock KV260 remains unmodified.

## 2026-11-12 owner verification and next-stage decision (local PC evidence)

Owner independently reran the D3.2 source evidence checker against the immutable D3.1 native PC run directory and received `D3A_NATIVE_OWNER_FILES_SHA256_AND_SEMANTICS_ACCEPTED`, matching all four archived texts and the original SHA ledger `955677040227dd5eaef81e49421b6b4c56f2436ca829036d3836d217371043a1`. The checker returned `D3B_CONTRACT_CREATED_PROTECTED_AXI_HARDWARE_BLOCKED` and explicit FALSE values for ATB4, AIB13, clock/AFI and hardware MMIO readiness. Manifest SHA reported by the owner is `0bcd98e00c5f5aab64075d08fc97b71b0d4e05c032a1cfa563cd877873384824`; this hash applies to the unchanged architecture JSON, not the updated design review.

The owner compiled and ran both D3.2 Icarus testbenches **twice** in the Linux terminal. The PS/Linux admission-policy model printed all five scenario markers plus `M08_D3B_OFFLINE_PS_LINUX_POLICY_ALL_PASS_NOT_HARDWARE_ATB_OR_MMIO_PROOF`; the genuine but unintegrated PL0 monitor printed all four scenario markers plus `M08_D3B_LIVENESS_GENUINE_RTL_ALL_PASS_NOT_PS_ATB_OR_PHYSICAL_CLOCK_PROOF`. All invocations ended with the expected `$finish`, without fatal. **This is owner-PC simulation acceptance for D3.2A only.** It cannot be upgraded to runtime PS ATB4/AIB13 protection, clock/fan continuity, actual PS boot configuration or a safe corrected image.

**Next submilestone:** start [D3.2B authoritative next-chat handoff, evidence-first implementation gates and full development workflow](M08_D3B_NEXT_CHAT_HANDOFF_2026_11_12.md). Specifically start B.1 (read-only, bounded owner PC inventory and provenance report for original XSA/PS init/base DT/boot component versions), then conditional B.2 PS ATB4/AIB13+PL0/AFI ownership, B.3 full AXI fail/late-response test coverage, B.4 Linux region/fan/rollback design, and B.5 a **new native Vivado-only candidate** ONLY if upstream safety is independently proven. Open a fresh branch from the latest D3.2A handoff commit and keep draft PRs #83/#84/#85 unmerged. No physical hardware step authorized.

## 1. Accept D3.1 owner-native evidence, carefully scoped

Original owner PC Vivado 2025.2 texts were supplied as exactly five separately uploaded files. The full *original binary Vivado project* was **not** uploaded; the exported Tcl/report/log provide native PS configuration provenance, not routed hardware evidence.

| Owner text file | SHA256 independently verified from uploaded file | Interpretation |
| --- | --- | --- |
| `01_native_vivado.log` | `5debf086f5ead1acbea506570440a2a21d71eff9b53f0394ab9d2a5dc04b46c4` | Native Vivado 2025.2 exited normally after successful marker |
| `10_d3a_passive_bd_readback.txt` | `c0a4443fcf42ae9c95f8b8eb970511f7e07630722620cd83e115bb20fb9b9c76` | K26 part, 2025.2, KV260 SOM board part0:1.4, all three PS HPM masters disabled, PL0 native FREQ_HZ 99999001, fan path reported, no bitstream |
| `11_d3a_passive_bd_export.tcl` | `a2a1f94d5fcf93ca87e2dea54d00227f4ec62bfa9ef947d456dd190af8525b19` | Actual exported PS properties include GP0/GP1/GP2 all **0**, EMIO TTC0 waveout enabled; fan xlslice output connected; **no** `connect_bd_intf_net` |
| `12_d3a_fan_a12.xdc` | `7b5f25d14ed1b45ba4c858277d661ba61c0490957370c195218b65de30d899ff` | A12 LVCMOS33, slow slew, drive 4 |
| `99_evidence_sha256.txt` | `955677040227dd5eaef81e49421b6b4c56f2436ca829036d3836d217371043a1` | Original native PC ledger matches all four original text files |

D3.1 **native BD** is ACCEPTED. D3.1 has **NOT** passed synthesis, timing/routing, physical fan, PL0 runtime, ATB, or protected MMIO gates. The Vivado log contains a **nonfatal compatibility advisory `INFO: [BD 5-1043]`**: `xlslice:1.0` is legacy; vendor recommends `inline_hdl:ilslice:1.0` for 2025.2. Preserve original fan source for traceability; migrate in **new candidate** only after verified native IP configuration and compare A12 continuity before routing.

## 2. Target D3.2 protected integration boundaries

The D3.1 PS HPM0-disabled architecture does not expose a PL AXI slave; that is intentional. To reintroduce the identity/page control path in D3.2, protection must be configured **upstream, in independent PS FPD**, not as another counter behind `pl_clk0`.

```text
APU / Linux diagnostic (one isolated read only, not an arbitrary /dev/uio mmap)
   │             Linux never exposes a PL resource until hardware-ready gating
   ▼
FPD main interconnect
   ├── ATB instance 4: BOOT-OWNED response enable + timeout clock + error policy
   └── AIB instance 13: FPD→M_AXI_HPM0_FPD transaction isolation + ACK contract
   ▼
M_AXI_HPM0_FPD (candidate width = 128 bits; need boot-time AFI agreement)
   ▼
PL SmartConnect (must have PL0 clock and reset stable; native sim required)
   ├── identity AXI4-Lite (original first-party read-only RTL)
   └── page AXI4-Lite (signed16 shell with DISPATCH *disabled*)
            Fan: unchanged PS TTC0 EMIO WAVEOUT2 → A12
```

**No D3.2 physical PS AXI path has been created, and ATB4/AIB13 are NOT configured by our testbench or by the D3.1 PS Tcl.** The planned D3.2 native Vivado build source, new overlay, boot integration and release artifact remain **blocked** pending an independently checked PS-boot configuration and lifecycle evidence. We will not label a PL-clocked firewall as an independent stopped-clock solution.

Vendor identifiers: UG1085 (2026-10-28 rev2.6) ATB instance 4 = FPD main interconnect→`M_AXI_HPM0_FPD`; AIB instance 13 = FPD interconnect→`M_AXI_HPM0_FPD`. ATB `ATB_RESP_EN`, `ATB_RESP_TYPE` (SLVERR), `ATB_PRESCALE` and optional `ERR_ATB_IER` require firmware/boot ownership and a configured independent timebase. The docs warn that only a **limited number of transactions (<16)** can be tracked; **restart after the first timeout** is recommended. ATB response from the PS does not prove the downstream SmartConnect/PL has no still-outstanding AR/R/W or that AIB isolation is safe. AIB13 quiescence and ACK, ordered disable/program/reenable, and no new accesses are separate controls.

**Vendor doc version note:** The online UG1085 currently identifies the timeout expression as `65536 * APB clock period * (PRESCALE+1)` while an older TRM extraction reports `131071 * APB period * (PRESCALE+1)`. This is a documentation/version mismatch, not permission to guess prescale values. **Do not generate any ATB register programming** until the exact version, FPD clock, reset defaults and current board firmware ownership are established.

## 3. What the new offline artifacts actually do

`docs/M08_D3B_PROTECTED_AXI_ARCHITECTURE_CONTRACT.json` is the versioned D3.2 architecture manifest. It pins the native D3.1 text SHA receipts and explicitly lists unresolved protection dependencies, absence of a D3.2 .bit/.bit.bin/DTBO/native HPM0 build, original quarantine and no physical approval. It is NOT a deployable DT fragment or vendor PS register map.

`scripts/m08_d3b_protected_axi_evidence_gate.py` is a **read-only** PC-only contract validator. Source-only mode ensures the manifest cannot silently authorize hardware or turn **UNKNOWN** boot/ATB4/AIB13/clock/AFI/fan prerequisites into a claimed PASS. Optional `--owner-d3a-run <original-run-directory>` rereads original owner-PC D3.1 log, native exported Tcl, report, fan XDC, and SHA receipt. Requires exactly the four original pinned SHA hashes and no symlinks. It checks native PS GP0/GP1/GP2 all disabled, logged completion, known legacy slice advisory and source fan A12. It *never* configures hardware, invokes Vivado, writes files, or claims runtime state. A positive D3.1 evidence attestation still returns **D3.2 blocked**.

`rtl/m08/tb_m08_d3b_ps_linux_release_policy.sv` is an **ABSTRACT TESTBENCH-ONLY PS-clocked admission/restart model**, not synthesizable PS ATB, Linux, ARM, AIB, memory mapped I/O, or a physically qualified PL clock sensor. It models seven boolean prerequisites: PS ATB4 configured, AIB13 quiescent, HPM0 128-bit AFI agreement, independently observed PL0 clock stable, reset released, Linux region/driver gate ready, and cooling continuity. All seven must be TRUE to arm an **abstract** single diagnostic request. First PS timeout latches a fault and blocks any further requests; a successful first response consumes the one-shot budget; loss of readiness locks the path; no unlock until full simulated PS restart. **Negative:** When the PS clock stops, the abstract controller cannot update/timeout and must not be counted as protection. Model input booleans are *assumed*, not measurements, nor evidence of actual PS-side hardware safety. No actual AXI responses, error draining or CDC logic is implemented.

`tests/test_m08_d3b_protected_axi_design.py` invokes real `iverilog`/`vvp` when installed, checks unique simulation pass markers, and runs synthetic native-receipt and manifest failure tests. Real Icarus simulation passing means **only model behavior** is verified.

### Unintegrated two-clock PL0 liveness diagnostic

We additionally designed real first-party, synthesizable **unintegrated** RTL
`rtl/m08/m08_d3b_clock_liveness_probe.v`. A PL0-clocked heartbeat bit
crosses a two-flop `ASYNC_REG` synchronizer and is checked by a **different
monitor clock**. The output initially fails closed (`clock_observed_alive=0`);
once transitions are observed it indicates activity, and if PL0 stops for
`QUIET_LIMIT` monitor cycles it clears alive and latches
`clock_failure_sticky`. The output **cannot be used as a hardware MMIO
authorization**, because no proven independent PS-side monitor clock or
qualified status-export path exists in the native K26 integration. Even if
clock activity is observed, HPM0 AFI/reset, ATB4 and AIB13 would still be
unproven. Native route/CDC verification, clock domain source and reset
sequencing are **NOT RUN**.

`rtl/m08/tb_m08_d3b_clock_liveness_probe.sv` runs genuine RTL in Icarus
when available: PL running → observed transitions; PL stopped but monitor
running → bounded loss of liveness and sticky fault; restored PL without
full-monitor reset → still latched; **negative monitor-clock stoppage** →
stale alive may remain high, proving this cannot replace a PS hardware
ATB. `tests/test_m08_d3b_clock_liveness.py` independently compiles and
checks these cases. No Vivado BD integration or `.bit` has been made.
This monitor is a **diagnostic aid for D3.2**, not a solution to the owner's
RCU stall or an alternative to independent PS protection.

## 4. D3.2 exit criteria before any new HPM0-enable Vivado design

These are mandatory **new independently reviewable artifacts**, not values inferable from the D3.1 passive BD:

1. **PS FPD timeout + isolation owner**: identify boot firmware or kernel version, where ATB4 RESP_EN/RESP_TYPE/timebase and timeout IRQ are established, who handles first fault, and AIB13 type/request/ack when outstanding transactions may be present. Do NOT write live ATB/AIB registers on recovered stock K26; offline source or saved immutable logs only. Prove semantic treatment of **late downstream responses after upstream timeout**; arbitrary synthetic SLVERR does not discharge an AXI AR.
2. **Clock/AFI**: source of actual PS PL0 clock enable/consumer/reset and 128-bit FPD HPM0 AFI data from genuine PS XSA and its corresponding firmware/DT. A 100MHz Vivado request alone is insufficient, and the stock DTBO remains missing.
3. **FPGA manager and Linux**: review actual KV260 Linux `dfx-mgr`/FPGA region/bridge/clock sequence and UIO or alternative driver exposure. Original `&amba` UIO nodes lack clock consumers and may not inherit region child-enumeration guarantees. No memory mapping before independent readiness.
4. **Fan**: demonstrate independent cooling across configuration changes, stock recovery, and TTC0 PWM generation independent of the failed interface; D3A A12 source is not thermal proof.
5. **Versioned native candidate**: only after 1–4, create D3.2 standalone PS HPM0 + read-only identity/page BD (new names, no original .bit reuse), source-derived clock/AFI DT and PS boot configuration, proper isolation, protocol tests with full AXI AR/R/AW/W/B, native 2025.2 DRC/CDC/reset timing and routed checkpoint. No physical MMIO until separate owner-approved hardware evidence.
6. **Physical gate separately**: first minimal identity 32-bit operation only with independent UART breadcrumbs and verified protection; stop on first error, no retries, no page/COMMIT, D3.2 board programming explicitly NOT AUTHORIZED.

## 5. Owner-PC offline verification (NO BOARD)

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 scripts/m08_d3b_protected_axi_evidence_gate.py
python3 -m unittest discover -s tests -p 'test_m08_d3b_protected_axi_design.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Recheck the ORIGINAL, owner-PC native D3.1 five-text evidence bundle:
RUN="$HOME/Thesis_Evidence/M08/m08_d3a_PASSIVE_NATIVE_PC_jA5mtaMf"
python3 scripts/m08_d3b_protected_axi_evidence_gate.py --owner-d3a-run "$RUN"

# Direct real RTL simulation (no Vivado, no board):
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_d3b_ps_linux_release_policy \
  -o "$TMP/m08_d3b_policy.vvp" rtl/m08/tb_m08_d3b_ps_linux_release_policy.sv
vvp "$TMP/m08_d3b_policy.vvp"
```

Expected evidence source output: `D3A_NATIVE_OWNER_FILES_SHA256_AND_SEMANTICS_ACCEPTED` with `D3B_CONTRACT_CREATED_PROTECTED_AXI_HARDWARE_BLOCKED`. Expected RTL final stdout marker: `M08_D3B_OFFLINE_PS_LINUX_POLICY_ALL_PASS_NOT_HARDWARE_ATB_OR_MMIO_PROOF`.

**Next owner evidence, if already present on PC**: archived original failed-image XSA and PS init output (`psu_init.c`/`psu_init.tcl`), versioned bootloader source/boot DT (not a newly guessed stock DTBO), dfx-manager/kernel source or saved logs describing PS PL0/AFI/ATB/AIB ownership, independent fan/rollback process. Finding those offline does not grant authority to connect to the recovered board. DO NOT edit/probe/reload stock or original M08.

## References

- AMD UG1085 ATB instance 4: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances?contentId=ZVwvfrhYNsa6uwvpZGJFOw
- AMD UG1085 AIB instance 13: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances?contentId=0AQgBby0rplaLkOjKRLYMA
- AMD UG1085 ATB programming / first-timeout restart: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming?contentId=LmhBOgbMAWEMJfstlk7gwg
- AMD UG1085 AIB isolation: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming?contentId=PPjyE9v19UubF6sdrqbt4Q
- AMD UG1087 FPD ATB_RESP_TYPE documented bit for afifs0: https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/ATB_RESP_TYPE-FPD_SLCR-Register

**Disposition: D3.1 native source accepted; D3.2 architecture + PS/Linux admission simulation in progress; protected image, boot-time ATB/AIB configuration, stock hardware changes and PS MMIO all STOP.**
