# M08.2b.3 — FIRST PHYSICAL IDENTITY ACCESS INCIDENT: RCU stall, evidence, quarantine, diagnostic/recovery plan

**2026-11-12 America/Denver (board journal timestamps UTC).** Scope: `Neuromorphic_Accelerator/v1`, ONE M08.2b, PR #83 **DRAFT/UNMERGED**. **CURRENT AUTHORITY FOR THIS HARDWARE INCIDENT.** Replaces the earlier permission in [post-power-cycle physical UIO test runbook](M08_2B_3_4_POST_POWER_CYCLE_FIRST_PHYSICAL_UIO_VERIFICATION_2026_11_12.md) to perform identity/page MMIO on the original M08 image. Those previously published hardware-read commands are **WITHDRAWN**, even with old owner approval flags.

## A. Original physical evidence (NEVER invent successful register data)

The owner completed the first M08 `PL_FLAT` Linux manager load, exact UIO sysfs names/4KiB resources and Linux `uio_pdrv_genirq` bindings in earlier, independently SHA-authenticated operator archives. These remain accepted *only in their original scope*. After a subsequent KV260 power cycle, the owner observed the normal default stock `k26-starter-kits` loaded. The owner re-established M08 and attempted the first real physical identity read using `scripts/m08_kv260_physical_uio_operator.py --mode identity` on a live K26 with the known candidate package:

- M08 bit.bin SHA256 `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`
- M08 DTBO SHA256 `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed`
- M08 shell.json SHA256 `0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3`
- UIO metadata references (last confirmed prior to incident): `m08-identity` 0xA0000000/4096 and `m08-page` 0xA0001000/4096. **Not** proof of AXI completion.

Uploaded original files individually in this turn, *not a complete original SHA-ledger incident archive*:
1. `01_identity_original.log` size **73 bytes**, SHA256 **`41a692f58008b42b3381bb02039a67b03f779d3d521351bad45a51271bd46e3a`**: only `[sudo] password for ubuntu:` and `client_loop: send disconnect: Broken pipe`. **No Python progress marker, no result data, no identity.json**; there is no observed proof that the program reached a particular slave read.
2. `02_identity_exit.txt` size **16 bytes**, SHA256 **`e24b46ec0eb8fb4f2b497e7efd508bc7e70bab830aaeb1b6d967c9cee3f3a31c`**: `exit_status=255`. This is SSH failure, NOT an AXI error code and NOT a returned identity word.
3. Owner's PuTTY screenshot `image.png` SHA256 **`6cf3c88bd5a582c740cc04748892ec280b108b53bb226301c949785bb0078697`**. Serial output near kernel monotonic **278.4s** includes `OF: overlay: WARNING: memory leak will occur if overlay removed, property: /fpga-region/firmware-name` (also `/fpga-region/resets`). Near **542s–552s** shows `rcu_preempt detected stalls on CPUs/tasks`, `rcu_preempt kthread starved for 58359 jiffies`, `Possible timer handling issue`, and `RCU grace-period kthread stack dump`. These are genuine kernel-wide scheduling/timing symptoms; the overlay removal warning precedes the stalls and **cannot be assigned as their cause** without evidence. No captured CPU backtrace identifies the failing MMIO address.
4. After operator-controlled hard power cycle: original new boot showed `sudo journalctl --list-boots` prior boot `-1` ID `61240ec1b7294d9b8c4cde347765128c`, recorded 2026-11-12 07:01:57–15:40:07 UTC, and current boot `0` ID `1b307d06b5854d34a0555965b72a3096`. `sudo journalctl -k -b -1` output `-- No entries --`; kernel-search pipe empty; both `/sys/fs/pstore/` and `/var/lib/systemd/pstore/` empty. The previous boot appears in journal *index* but its kernel messages **did not survive / are not available**. After reboot: stock `k26-starter-kits XRT_FLAT` **slot 0->0**, M08 `PL_FLAT` **-1**, FPGA manager `operating`, `dfx-mgr` and `fancontrol` `active`. This is **post-reboot recoverability**, not proof that stock rollback worked before the crash or that M08 AXI is safe.

**Incident verdict**: first real PS→PL M08 identity register experiment **FAILED/INDETERMINATE** (system-wide stall and lost SSH); **M08.2b.3 physical register acceptance BLOCKED**, **M08.2b.4 physical page write/read/COMMIT BLOCKED**. NO `identity.json`, `page.json`, 64-word page or neural inference result accepted. Initial Linux firmware load and kernel UIO binding acceptance are not rescinded.

## B. Root-cause ranking; distinguish observed facts from engineering hypotheses

**Leading hypothesis (moderate confidence, not demonstrated):** one PS→PL AXI transaction attempted during the first identity-mode process encountered a nonresponding interconnect/PL slave; the processor or kernel may have stopped progressing while waiting. Temporal adjacency to first MMIO and system-wide RCU/timer warnings supports this investigation priority. **However, the script prints no progress until after all reads**, and the captured original SSH output cannot distinguish:
- BEFORE any device open: `sudo`/preflight `systemctl`, `xmutil`, or SHA verification.
- `/dev/uio` open/mmap before first read.
- First identity `0xA0000000 + 0x00` register read, later identity registers, or page `0xA0001000` read.

Candidate mechanisms in priority order:
1. **PS/PL ACLK or reset is incorrect at runtime**, even though Vivado 2025.2 validated nominal 99,999,001 Hz and routed timing. The BD drives PS `pl_clk0` to HPM0, SmartConnect, identity/page RTL clocks, and reset from `ps/pl_resetn0` via `util_vector_logic` inversion and `proc_sys_reset`; `dcm_locked` is deliberately tied to constant 1, not measured lock. Investigate whether Linux-managed deployment truly enables clock, deasserts reset and PS/HPM0 interface/isolation after bitstream load.
2. **AXI address decoder/SmartConnect/bridge or handshake deadlock**: actual PS FPD HPM0 to `ctrl_sc` MI0/MI1 to RTL, 4KiB windows 0xA0000000 and 0xA0001000. Linux `generic-uio` DT claims **do not** verify physical target response, and a successful FPGA manager load is not an AXI handshake test. The prior offline SmartConnect **RTSTAT-10 reset-pipeline methodology warning** requires renewed investigation rather than being labeled harmless.
3. **Linux mmap/firmware/PS isolation/security/address translation** despite correct UIO sysfs resource names and driver symlinks. Determine whether the physical map and access permission match the actual powered PS/PL transaction route. A deadlocked transaction and a synchronous abort require different fixes; no ESR/fault backtrace was captured.
4. Less supported: unrelated Linux timer/IRQ/RCU issue occurring during first test, possibly amplified by serial logging; the screenshot does not exclude it.

The Linux RCU CPU-stall detector documents several non-AXI root causes (CPUs with preemption/interrupts disabled, timer scheduling issues, kernel bugs), so do **not** identify AXI as proven root cause solely from the `rcu_preempt` warning: https://www.kernel.org/doc/html/latest/RCU/stallwarn.html . AMD ZynqMP documentation warns that outstanding AXI transactions in interconnect can hang the system and that AXI Timeout Block responses are not an excuse to repeatedly access an unresponsive slave: https://adaptivesupport.amd.com/s/article/73457?language=en_US and https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/ATB-Timeout-Description . PS PL reset guidance: https://docs.amd.com/r/2025.1-English/ug1137-zynq-ultrascale-mpsoc-swdev/GPIO-Reset-to-PL .

## C. Immediate hardware/software quarantine (committed)

**Hard STOP:** no `/dev/uio*` `mmap`/read/write on the ORIGINAL deployed M08 bit.bin SHA above, no `devmem`, no `/dev/mem`, no M08 256B state page operations, no DISPATCH or neural inference, no blind `xmutil` M08 reload and retry, no changing stock default boot, no JTAG hot reconfiguration on Linux-managed PL. Keep recovered stock K26 app running while diagnosing. Preserve original home-staged physical script, PuTTY screenshots, logs and ledger *without re-executing* them. The earlier post-power-cycle runbook's Part C/Part D commands are superseded and **WITHDRAWN**.

**Repository mitigation**: `scripts/m08_kv260_physical_uio_operator.py` now calls a non-bypassable mode check `reject_quarantined_mmio_mode` before any live platform check, so the only available mode is `preflight` (metadata-only). The alternative `scripts/m08_path_a_uio_identity_guard.py --mode identity` is separately rejected as `M08_MMIO_QUARANTINED_AFTER_PHYSICAL_RCU_STALL`. The rollback authorization flags used before the incident **cannot** enable new physical reads. New `tests/test_m08_post_incident_mmio_quarantine.py` source-only tests both entry points. NOTE: older original code copies previously transferred to `/home/ubuntu/m08_2b_tests_*` on the KV260 are NOT retroactively patched and remain dangerous; **NEVER execute these old board-side files**. Do not delete immutable originals before auditing.

## D. Ordered forensic and fix plan — new chat next steps

**D0 — evidence lock, no hardware changes.** Preserve these three original uploaded artifacts and per-file SHA; check full owner `MMIO_EVIDENCE` original directory for context, raw SSH log, missing identity.json, exit status and receipts; request original PuTTY full session log if it exists, but a screenshot alone already proves RCU symptoms. Gather only **post-reboot/current-stock no-MMIO observations** as original SHA-receipted files: manager `xmutil listapps`, FPGA state, dfx-mgr/fancontrol, kernel version, boot ID/journal availability, `/proc/cmdline`, read-only clocks if the debugfs clock summary is **already mounted** (no mount/writes), current power/thermal. Do not infer the failed boot's PL clocks from the currently running stock design.

**D1 — static source/Vivado forensic mapping.** Trace exact trusted source `scripts/m08_page_ps_bd_candidate.tcl`, `scripts/m08_path_a_fan_bd_candidate.tcl`, `rtl/m08/m08_axil_readonly_identity.v`, `rtl/m08/m08_ps_page_safe_shell.v`, and `scripts/m08_kv260_physical_uio_operator.py` against ORIGINAL routed DCP/BD export/implementation/XSA, address reports and deployed firmware SHA. Check PS `M_AXI_HPM0_FPD` enabled, Linux runtime PS HPM0 gating/isolation, PL0 clock output, `pl_resetn0` deassertion, all `aresetn` and SmartConnect reset clock domains, `dcm_locked` tied high, and original RTSTAT-10 warning. Verify address decode 0xA0000000/0xA0001000 matches final IMPLEMENTED (not just pre-route) address map and DTBO; 4KiB UIO name/driver is not sufficient.

**D2 — reproduce/resolve offline, never by repeating old MMIO.** Extend *source-only* simulation BFM, including backpressure/independent AR/R, identity/page returns and reset timing; if possible validate generated SmartConnect behavior in native Vivado simulation. Add a deliberate no-response slave negative simulation to prove protection: upstream PS-facing path must return a bounded error or isolate the failed downstream path **without leaving a pending transaction in the AXI interconnect**. Compare candidate AMD isolation/timeout options and ATB limitations, don't assume a Python timeout prevents a kernel hard hang. Add non-invasive hardware-visible signals / AXI Protocol Checker / ILA in a **new versioned bitstream**: PL clock live, reset released, M_AXI_HPM0 ARVALID/ARREADY/RVALID/RREADY (and later AW/W/B) at SmartConnect input/output and each slave; capture with JTAG/Vivado **read-only** diagnostic procedures after separately reviewed safe image programming. Preserve K26 fan TTC A12 route and independent cooling.

**D3 — prepare a corrected safe candidate, separately gate release.** Generate fresh Vivado 2025.2 project and version-named artifact, not modifying deployed original firmwares; run native DRC, synthesis/implementation WNS/WHS, reset/clock methodology, AXI protocol simulation, instrumentation/timeout verification, exact .bit -> .bit.bin and DTBO with original SHA ledger. Retain known-good k26-starter-kits and stock default; prove independently powered fan continuity and manager-controlled return-to-stock in its own operator evidence before physical AXI retesting. A source-only passing result is NOT safe-to-read proof. Require explicit owner approval at each hardware phase.

**D4 — one new versioned owner-operated hardware diagnostic, NOT CURRENTLY AUTHORIZED.** Install new reviewed PL_FLAT app via proven two-stage manager registration; record UART from before image load, dfx-mgr, temperatures, last seen pre-MMIO breadcrumb. Verify physical clock/reset and instrumentation BEFORE attempting PS AXI. If timing path still dubious, return to stock without reads. Only after independently reviewed timeout/isolation and owner authorization, attempt ONE minimal, isolated 32-bit **identity-only** read with durable pre-/post-stage markers and independent recovery path. Never read the page window in same initial probe; never batch 8 identity reads before first proof. On first failure STOP. Review originals.

**D5 — re-open milestones incrementally.** Only after genuine identity read+physical trace, mark M08.2b.3 PASS for actual PS/PL register access (not RRESP unless instrumented). Then separately authorize M08.2b.4 staged page exactly 64 x 32-bit write/read/compare-before-COMMIT, no DISPATCH. Full Loihi-style event engine, DDR/DMA, neural inference and M09 physical comparisons remain OPEN. Keep PR #83 DRAFT/UNMERGED until owner hardware acceptance.

## E. Immediate user PC source verification (NO BOARD)

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_post_incident_mmio_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

**This incident is OPEN; root cause not proven. The next chat should begin D0/D1 and progress source-only/D2 before ANY additional physical M08 test.**
