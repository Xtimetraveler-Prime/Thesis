# M08 tests explained — entry/read-only and hardware-readiness contracts

**Status:** M08.1 complete within accepted host-evidence scope; M08.2 first through fourth genuine Vivado failures diagnosed, narrow Tcl corrections in source, **new vendor revalidation NOT YET COMPLETE; NOT M08 physical acceptance.** Do not reinterpret CI fixture data as a captured physical KV260 observation. Genuine board runs and original vendor place-and-route require local operator evidence.

## Scope and independent evidence

M08.1 is intended to answer **what is actually available on the development PC and the KV260?**, before risking unowned PS DDR or programming a PL design that lacks a proven Linux driver.

- `m08_entry.py`: immutable five-ZIP M06 acceptance SHA256 list from original M06 acceptance report, input-shape-only kernel DMA address guard, and a deliberately **never automatically ready** physical evidence checklist.
- `m08_capture_readonly.py`: host or KV260-on-device Linux inventory. Every subprocess is a named read-only argv, never `shell=True`. No `sudo`, `/dev/mem`, `vivado -mode batch`, flash, FPGA programming, DMA, or DDR memory writes. Output is a unique operator-owned mode-0700 folder with JSON and SHA receipt.
- `m08_receipt_audit.py` and `m08_audit_readonly.py`: independent SHA and schema/command-scope auditor. It detects file tampering and fake ready-to-DMA claims but **cannot cryptographically verify** that a board supplied an authentic boot log; owner observation/independent device and toolchain evidence remains necessary.
- `docs/M08_PHASED_HARDWARE_PLAN.md`: exact next gates (Vivado BD build, kernel-owned buffer, physical neural parity, matched hardware benchmarks, performance evidence and M09 handoff).

### Test-by-test meaning (host-only synthetic negative/positive fixtures)

| Test | Input and method | PASS means / what it does NOT mean |
| --- | --- | --- |
| `test_readiness_is_nonclaim_even_when_all_self_reported` | Missing, malformed and complete operator-text evidence IDs | An empty list fails readiness; even a complete *self-report* requires independent audit. No fabricated physical PASS. |
| `test_physical_dma_requires_kernel_owned_buffer_and_32bit_bound` | Valid 64B-aligned kernel API *claim*, then bare devmem, guessed allocator, invalid mask/bounds/alignment, booleans, negative/overflow cases | Only structural shape of declared DMA buffer is admitted. This is NOT a real allocation/driver proof, and `physical_allocation_verified=false` is mandatory. |
| `test_archive_inventory_is_sha_strict_no_faked_owner_vivado_pass` | Empty evidence directory, wrong/duplicate/symlink files, and SHA mismatch | Five accepted original M06 ZIP names must each appear once and have **their independently published exact SHA256**, without copies or mutations. Synthetic files cannot be accepted as Vivado evidence. |
| `test_host_capture_fake_safe_tools_does_not_claim_board` | Synthetic read-only command results from a PC environment | Records host source hashes/version observations and explicit no-board/DDR flags; a host OS cannot identify a live KV260. |
| `test_board_local_observation_is_not_fpga_attestation` | Synthetic Linux DT model text (a positive name and missing-model negative) | Evidence is labeled *local OS observation*, not a bitstream/AXI/DDR proof even if a string says KV260. |
| `test_exclusive_evidence_no_overwrite_or_invented_host_pass` | New output folder, SHA receipt, attempt to overwrite | Original evidence bytes are unchanged; no accepted pass is replaced by a later run. |
| `test_command_allowlist_and_board_device_file_allowlist` | Unapproved shell/Vivado/physical memory operations | Fail closed before executing any nonallowlisted command or reading device memory. |
| `test_real_cli_host_is_explicit_read_only_and_exclusive` | Genuine local read-only capture in CI's Ubuntu host, repeat same folder | Output is reproducible in structure with local timestamps/source SHA, no board PASS, and refusal to overwrite. CI runner is a workstation, NOT the KV260. |
| `test_host_receipt_audits_only_integrity_not_real_board` | Source-only fake host capture + independent SHA256 verifier | SHA, command allowlist and false physical readiness flags are enforced; it does not authenticate identity of a real KV260. |
| `test_board_local_receipt_never_authenticates_board_or_dma` | Synthetic DT payload + independent auditor | Even a board-local capture only proves receipt consistency. |
| `test_modified_receipt_is_rejected_even_with_valid_json` | Change one JSON field, preserve original receipt | SHA256 mismatch must fail. |
| `test_self_consistent_but_false_physical_or_extended_commands_rejected` | Regenerate valid SHA for fabricated DDR READY/board program, unauthorized command or fake archive state | Integrity alone cannot grant physical authority; auditor rejects fabricated status and unapproved captures. |
| `test_cli_preserves_accepted_receipt_and_exclusive_output` | Audit output in a new file, attempted repeat | Independent JSON result is only integrity-pass and is never overwritten. |

**CI:** `.github/workflows/neuromorphic_accelerator_m08_host_preflight.yml` runs `test_m08*.py`, inherited M07 and full v1 unittest discovery in a single process. It performs a real **host-only** inventory on Ubuntu GitHub Actions, validates the independent receipt and retains a marked `m08-1-host-only-physical-not-run` archive. No board, HLS synthesis, original AMD XSim, physical DMA or real DDR is exercised by CI.

### Test sources vs real hardware acceptance

The accepted M05 signed32 engine and accepted M06 signed16 pager differ in arithmetic width; they cannot automatically be compared as matched 4-way physical variants. M06's 64 KiB canonical memory is a simulated bytearray/RTL scratch, not Linux-owned DDR. The original AMD interconnect and historical M05 DMA memory graph do not supply a genuine kernel driver/bitstream. Before **any** physical latency/throughput figure, the exact original generated vendor sources, addresses, XSA/bitstream, DDR ownership, AXI transfer integrity and M02 independent neural reference must all be verified on target.

No owner board measurements are available yet; that absence should be shown as **OPEN**, not hidden or represented by model-only counters.

## Evidence acceptance strategy

The first genuinely useful owner deliverable is a **PC-host** preflight receipt with the original M06 ZIP digest matches and, if the board boots, a **separate board-local** receipt. Capture a serial boot log if the KV260 never reaches a usable Linux shell. These observations determine whether to pursue the current on-device Linux/driver path or a recovery/isolated boot plan.

Physical M08 acceptance requires future separately documented tests: signed neural trace parity, fail-closed fault behavior, actual DDR read/write and W-before-R ordering, real FIFO/backpressure, timing boundaries, routed utilization, and repeatable independent runs. A synthetic CI fixture must never be used for that acceptance.

## M08.2 standalone PL identity — preliminary original RTL (NOT yet a PS/PL bitstream)

**Modules:** `rtl/m08/m08_axil_readonly_identity.v`, `rtl/m08/tb_m08_axil_readonly_identity.sv`, `src/neuromorphic_accelerator_v1/m08_identity_client.py`. Tests: `tests/test_m08_identity_rtl.py` and `tests/test_m08_identity_client.py`.

Why this step: before deploying the original M05/M06 compute/DDR paths, a **side-effect-free** PL identity slave can distinguish “the PS can read my actual PL address decode” from “a Vivado bitstream was accepted” or “the neural engine ran.” It never constructs a user-space `/dev/mem` mapping or generates any DMA transaction. It is an independently developed local-first-party Verilog candidate; not a sourced original AMD/HLS model or a physical K26 project.

**Register map** (32-bit little-endian AXI4-Lite word offsets; must later be assigned an independently audited, non-overlapping PS address):
| Offset | Read result | Write behavior |
| --- | --- | --- |
| 0x00 | `0x4D303831` ASCII "M081" | SLVERR |
| 0x04 | `0x00010000` protocol version v1.0 | SLVERR |
| 0x08 | `0x00000000` this slave has **no DMA/master capability** | SLVERR |
| 0x0c | zero reserved | SLVERR |
| 0x10–0x1c | four 32-bit parameterized BUILD_ID words, default all zero | SLVERR |
| others / unaligned | `RDATA=0`, AXI4-Lite DECERR | SLVERR |

On any accepted AW/W pair, including AW before W or W before AW, exactly one SLVERR B reply is generated and held under BREADY backpressure. No register write side effect exists. Read response and data stay stable while RREADY is low. Reset drops pending half-writes/outputs. Unknown read offsets do **not** alias a control register. The four build ID words must be set from a real verified deployment build later; zero defaults prohibit a false “this bitstream is certified” conclusion.

**Host client:** `inspect_identity(adapter)` takes a caller-supplied `read32(offset)` interface, never allocates MMIO or chooses a physical address. It reads the entire map twice, rejects unknown magic/protocol/unknown capabilities, changed reads and a zero build tag by default. Even a consistent nonzero build tag returns `actual_bitstream_sha_verified=false`, `physically_attested=false`, `dma_buffer_owner_verified=false`. Only the independently SHA-verified routed bitstream and external board/driver evidence can change those downstream claims.

| New test | Scope | Expectation |
| --- | --- | --- |
| `test_identity_module_has_no_dma_or_writable_effects` | Local static structural check | Separate read-only RTL has no AXI master and returns errors for every write/unknown read address. |
| `test_real_iverilog_protocol_reset_and_backpressure` | **Real Icarus iverilog/vvp simulation** of new RTL and independent TB | Thirteen exact read cases (including fault addresses), three rejected AW/W ordering cases, stable R/B backpressure, reset drops stale AW, no DMA. A single `M08_AXIL_IDENTITY_STANDALONE_ICARUS_PASS` marker, zero compile warnings. Requires `iverilog` and `vvp` locally; M08 Actions CI installs them and demands actual PASS. |
| `test_requires_two_stable_passes_and_nonzero_build_tag` | Mock read32 transport, no OS MMIO | Two identical snapshots, exact map/protocol, unsigned32 bounds and nonzero build tag. All physical attestation flags remain false. |
| `test_reject_unknown_magic_version_caps_reserved_and_unprovisioned_tag` | Mock unknown and malformed register maps | Fail closed instead of guessing software/RTL compatibility; optional zero tag explicitly remains untrusted. |
| `test_reject_unstable_response_or_bad_integer_range` | Inconsistent/invalid read values | Refuse stale or corrupted MMIO data before any device command. |
| `test_read_failure_has_no_write_operation` | Adapter raises OSError | Throw tagged protocol error; never issue a write. |
| `test_readonly_client_has_no_devmem_backend` | Source API inspection | There is no direct /dev/mem mmap nor outbound MMIO writes in this module. |

**Acceptance boundary:** Icarus PASS shows this *standalone first-party slave* is self-consistent. It is NOT an actual KV260 PS-PL MMIO test, a real AXI interconnect/SmartConnect simulation, a PS Linux memory driver, routed timing closure, or on-chip/DDR neural inference. The next hardware-required step is to add this probe to an actual observed KV260 project, provide an independently verified real FPGA address map, program the verified built bitstream, and read it via a known kernel-approved MMIO interface. No fabricated base address is specified here.

## M08.1b — owner evidence, Loihi-v2 reuse, and read-only xmutil state

The owner first PC inventory (SHA256 `2c4276c13e3adb21721b8b49e027aa94cbe1e51cf592d402272684bc518606e0`) and independent audit agree; **all 5 M06 original ZIP hashes MATCH**. Host Vivado/Vitis commands were not found on that shell PATH, but are not asserted uninstalled. The host working tree is **dirty from untracked historical Loihi physical evidence and Vivado logs**. Preserve those files and work in exclusive M08 evidence folders. The user separately confirms normal KV260 Linux boot and the standard `sudo xmutil unloadapp` postboot routine; the original uploaded host inventory does not establish board-local Linux release/DT or prove an M08 bitstream.

The Loihi v2 acceptance notes document a routed host-paged K26 design and a genuine JTAG/VIO physical neural conformance case on the *separate Loihi v2 system*. Those results are useful for procedure reuse, **not** transferable accelerator SHA/FPGA performance or signed16 M06 computational parity. See `M08_1_OWNER_EVIDENCE_AND_LOIHI_REUSE_2026_11_10.md`.

`scripts/m08_capture_readonly.py --mode board-local` now allows only *read-only* `xmutil listapps`, `boardid`, `bootfw_status` and `platformstats`; it never calls `unloadapp` itself. Receipt auditor demands the same exact command set and rejects unsolicited `loadapp`, `unloadapp` and `bootfw_update` from an inventory script. The operator may still perform the existing authorized `sudo xmutil unloadapp` **outside this script**, logging app state before and after.

## M08.2 — real Vivado K26 PS→PL read-only identity integration trial (NOT yet operator executed)

**New candidate sources:** `scripts/m08_identity_ps_bd_candidate.tcl`, `scripts/run_m08_identity_bd.sh`, `scripts/m08_identity_bd_audit.py`, `tests/test_m08_identity_bd_candidate.py`. This is the first integration path between M08's verified standalone no-DMA AXI4-Lite slave and a Zynq UltraScale+ PS master. It follows the accepted **K26 PS HPM0 FPD 128-bit control interface, proc_sys_reset and explicit PS reset inversion** patterns documented by the M05.12d.3 original integration work, not a freely chosen physical DDR base address.

The genuine operator Vivado candidate requires a real 2025.2 `xck26-sfvc784-2LV-c` part and exact AMD PS, SmartConnect, reset conditioner, inverter and constant IP versions. It creates a **new** project inside a unique `~/Thesis_Evidence/M08/m08_2_identity_bd_*_XXXXXX` folder, adds **only** the first-party read-only identity RTL, creates one PS `M_AXI_HPM0_FPD` → one SmartConnect → one `identity/S_AXI` path, connects the original PS PL clock/reset, lets genuine Vivado assign an address, validates the BD and exports a readback report. It **does not synthesize, implement, generate a bitstream/XSA, program JTAG, use xmutil or access physical DDR**. Module-reference AXI-Lite port inference, PS settings, address segment and native validation remain unproven until a real local trial is run.

The wrapper generates SHA-256 of four current original source/script files **both before and after** the tool run, an original exit-status file, raw Vivado log and exported BD Tcl. The independent auditor demands exact source consistency, one success marker, no error/critical warning, a genuine bounded 32-bit assigned identity register aperture, correct PS/PL pin names and explicit `NOT_RUN/NOT_PROGRAMMED` physical fields. A failed run remains in the evidence directory and MUST NOT be relabeled a successful validation. The source-level unit test's positive synthetic fixture demonstrates **auditor behavior only, not a real vendor PASS**.

| New test | Contract checked |
| --- | --- |
| `test_tcl_is_ps_to_readonly_id_only_not_software_ddr` | Exact K26/PS→SmartConnect→identity references; no JTAG or bitstream commands. |
| `test_runner_has_valid_bash_syntax_without_running_vivado` | Bash syntax is valid, without executing vendor tools. |
| `test_tcl_grammar_balanced_without_loading_vendor_ip` | A standalone Tcl interpreter reaches the mandatory argument guard; this does **not** validate Vivado commands. |
| `test_fixture_checks_auditor_only_not_real_vivado` | Synthetic original-looking report exercises the independent auditor schema and explicit no-physical fields, not real Vivado. |
| `test_reject_bad_source_result_or_log` | Failed exit status, altered before/after source, missing success marker or fake report are rejected. |
| `test_reject_bad_address_and_false_physical_claims` | Invalid/overflowing/unwordaligned PS aperture and bitstream/DDR/programming claims fail. |
| `test_cli_rejects_failed_evidence_without_creating_pass` | Refuses a failed original vendor report and never leaves an accepted audit file. |

**Actual owner stage:** source your local 2025.2 `settings64.sh` and run `bash scripts/run_m08_identity_bd.sh`. The original report is mandatory for M08.2 validation and must be reviewed before an actual bitstream or Linux MMIO backend can be claimed. No physical inference acceptance is implied by a valid BD.

**CI:** includes this entire source-only negative suite and first-party Icarus identity TB; it **does not** run Vivado 2025.2 or any hardware tool requiring local licensed vendor binaries/board connection.

## New genuine original Vivado evidence — first FAILED offline BD invocation and diagnosed first error

**Original owner run 2026-11-10 22:56 America/Denver:** `bash scripts/run_m08_identity_bd.sh` invoked real `vivado v2025.2` (SW 6299465, IP 6300035) and returned `M08_VIVADO_BD_ORIGINAL_FAILED exit_status=1`. Original evidence folder: `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ`. The owner subsequently uploaded the original `01_vivado_identity_bd.log`, `result.txt` and before/after SHA manifests. The first fatal diagnostic is `ERROR: [Common 17-53] User Exception: No open project` on `get_ipdefs -all -quiet $vlnv` before `create_project`. The two four-file SHA manifests match byte-for-byte. Root cause: IP catalog queried without project context, not evidence of defective identity RTL/AMD unsupported IP. The minimal fix places `create_project` and part readback before the strict five-IP catalog checks; **no IP check is removed**. Missing `vitis_hls` command in this shell is not an established cause: the identity-BD wrapper does not invoke HLS. The script exits early on failed `vivado`, before the independent BD success auditor.

**Scope reporting:** source-only M08 negative-fixture/RTL Icarus tests remain previously successful; they have not proven genuine IP Integrator output. Mark the genuine vendor gate **FAILED/OPEN**; do not call it a BD PASS, rerun or silently waive errors. This failure is *not* a neural inference or memory transaction fault, and no actual board JTAG, Linux MMIO, DDR or bitstream activity occurred in this offline trial.

**Regression:** `test_ip_catalog_query_occurs_only_after_open_project` runs the candidate under plain `tclsh` with mocked `get_ipdefs` refusing lookup before project creation, and a sentinel stopping before `add_files`. This reproduces the exact missing-project ordering boundary but is not a genuine Vivado test. **Next proof:** run M08 targeted, inherited M07, full suite and standalone Icarus where available; confirm all eight same-SHA GitHub workflows; then require exactly one **fresh** owner Vivado run preserving original and new evidence. Vendor outcome remains OPEN until raw new `result.txt`, log, report, export, SHA manifests and independent audit are reviewed. See [M08.2 first failure handoff](M08_2_BD_FAILURE_NEXT_CHAT_HANDOFF_2026_11_10.md).

## Second genuine original Vivado failure — stray LPD master clock, NOT a valid BD

**Second original local Vivado trial (2026-11-10 23:22:58 America/Denver; original folder `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T062256Z_MakfLD`)**: genuine 2025.2 created the project, found all five IPs, inferred `identity/S_AXI` (AXI4-Lite, 32-bit), connected the intended `ps/M_AXI_HPM0_FPD` path, and assigned `/identity/S_AXI/reg0` in `/ps/Data` at `0xA0000000`/4 KiB. `validate_bd_design -force` nevertheless returned `WARNING: [BD 41-2670]` incomplete `/ps/M_AXI_HPM0_LPD` path and **first fatal** `ERROR: [BD 41-758]` unclocked `/ps/maxihpm0_lpd_aclk`, followed by `[Common 17-39]`. `result.txt=exit_status=1`; all four source SHA rows match before/after. This confirms the prior get_ipdefs/project-ordering fix progressed, but **the second vendor run failed**. The narrow new correction explicitly configures `CONFIG.PSU__USE__M_AXI_GP0 1` and `CONFIG.PSU__USE__M_AXI_GP2 0`, verifies both readbacks and requires the unused LPD AXI interface/clock to disappear. A Tcl mock regression checks a successful and a refused-disable path; actual IP behavior remains subject to a **third fresh owner run, after all eight updated same-SHA workflows are green**. The two failed original directories must remain preserved; no bitstream/DDR/FPGA activity is claimed.

| Added source-only regression | Exact contract |
| --- | --- |
| `test_unused_lpd_is_disabled_with_readback_before_bd_wiring` | Plain Tcl mock refuses GP2 disable in one negative case and allows it in a positive case. The code must enable FPD GP0, disable GP2 LPD, read back the value, and verify unused LPD interface/clock are absent before module BD construction. It does not model AMD IP Integrator, AXI timing, or a vendor success. |

**Next evidence gate:** run updated 28→29 targeted M08 tests, inherited M07 and full discovery; confirm M01–M08 GitHub Actions success on the final commit SHA; then request **one new** owner original Vivado 2025.2 invocation via the existing runner, which automatically chooses a fresh directory. Require genuine log, project validation, BD report/export, exact hashes and independent audit; preserve both failures even if this new one also fails.

## Third genuine local Vivado failure — PS clock metadata vs fixed 100 MHz AXI4-Lite

**Third original owner Vivado failure (2026-11-10 23:35 America/Denver):** preserved under `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T063515Z_xsLGAr`. Genuine Vivado 2025.2 created the K26 project, inferred `identity/S_AXI` AXI4-Lite (32-bit, 100 MHz), disabled the previously unused LPD master, connected `M_AXI_HPM0_FPD`, and assigned the identity aperture `0xA0000000` (4 KiB) in `/ps/Data`. On `validate_bd_design -force`, the **first serious message** was SmartConnect **CRITICAL WARNING** about incompatible clocks, followed by **[BD 41-237]** `identity/S_AXI(100000000)` versus `ctrl_sc/M00_AXI(96968727)` and **[BD 41-238]** `identity/aclk(100000000)` versus `ps/pl_clk0(96968727)`; [Common 17-39] is the cascading validation failure. `result.txt=exit_status=1`; all four SHA-before/after records are byte-identical. No accepted readback/export/audit and no physical activity. The immediately preceding two failed folders remain preserved.

**Loihi v2 precedent reviewed:** in `Loihi_Digital_Twin/v2/vivado/create_p03_impl_project.tcl`, `create_p04_impl_project.tcl`, `create_p05_impl_project.tcl`, and `create_p08_impl_project.tcl`, the accepted K26 designs explicitly set `CONFIG.PSU__FPGA_PL0_ENABLE {1}` and `CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}` before wiring `pl_clk0` into the fabric. These were real routed physical shells, but **not** AXI4-Lite validation of M08 and not interchangeable signed16 hardware. The Loihi scripts also applied a KV260 board preset; the **current narrow M08 correction deliberately does NOT import that broader preset or DDR integration**. Instead it requests 100 MHz on the M08 PS and fails closed if the actual `ps/pl_clk0` pin `CONFIG.FREQ_HZ` differs from the 100,000,000 Hz RTL metadata. A plain-Tcl mocked negative regression covers the observed `96968727` case; it does NOT prove genuine Vivado IP generation. Require eight updated same-SHA source-only CI workflows, then one **fresh fourth** owner Vivado offline validation in a new exclusive evidence directory. Keep PR #83 draft/unmerged.

**New regressions:** `test_unused_lpd_and_ps_clock_readbacks_before_bd_wiring` has three mocked Tcl scenarios: correctly disabled unused LPD plus 100,000,000 Hz PS pin (allowed to reach the identity-cell sentinel), an ignored LPD-disable request (must fail), and the **observed** 96,968,727 Hz PS clock (must fail with exact readback error). `test_explicit_ps_pl0_clock_request_preserves_fpd_only_topology` checks that the Tcl requests and checks the PS clock without importing Loihi's board preset or DDR settings. These test first-party source behavior **only**, not Vivado frequency synthesis, BD validation, implementation, or on-board PS/PL transactions. The existing strict independent auditor remains unchanged.

## Fourth original Vivado failure — PS requested MHz is not generated PL0 Hz

**Fourth original owner Vivado failure (2026-11-10 23:47:59 America/Denver):** genuine Vivado 2025.2 `result.txt=exit_status=1` in immutable `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T064757Z_DFdwwi`. Before/after four-file SHA records match, and the owner independently reported `sha256sum -c` PASS for each of the four sources. The Tcl successfully created the project and set `CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100`, but the exact fail-closed pin readback was **`M08 PS PL0 actual FREQ_HZ mismatch: expected 100000000 got '96968727'`** at Tcl line 92. This failed **before** AXI identity/SmartConnect creation or `validate_bd_design`; no clock DRC result, no readback/export/audit, no bitstream, JTAG, physical DDR or neural inference. The fourth run confirms requesting 100 MHz without applying a KV260 board preset is **insufficient**, not that a board preset definitely fixes it.

**Evidence-guided corrective hypothesis from accepted Loihi history:** the independently routed `Loihi_Digital_Twin/v2/vivado/create_p03_impl_project.tcl`, `create_p04_impl_project.tcl`, `create_p05_impl_project.tcl` and `create_p08_impl_project.tcl` explicitly find the installed `xilinx.com:kv260_som:part0:*` board definition, select `BOARD_PART`, apply `apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"}` and **then** request 100 MHz. M08 now reproduces that PS initialization sequence, with a fail-closed board-part availability/readback guard; after the preset it reasserts the **M08-only** FPD HPM0 AXI master, disables unused FPD HPM1/LPD HPM0 masters, requests 100 MHz, and verifies actual PL0 `CONFIG.FREQ_HZ`. This imports only PS initialization, not Loihi neural architecture or its PL/DDR datapath, and creates **no** physical DDR transaction. Mock Tcl tests cover missing board files, ordered preset, rejected GP2 disable, and original 96,968,727 Hz clock mismatch; these cannot prove real AMD output. **After eight same-new-SHA source workflows pass, require ONE fresh fifth local Vivado 2025.2 offline BD run with a NEW original evidence directory; preserve all four historical failed folders.** Keep PR #83 draft/unmerged.

**New no-board regression:** the previous `test_unused_lpd_and_ps_clock_readbacks_before_bd_wiring` Tcl harness also requires an installed KV260 board definition and successful `BOARD_PART` readback, and verifies the PS board automation occurs **before** explicit FPD/clock overrides. The negative cases still reject 96,968,727 Hz and GP2-disable refusal. The static `test_explicit_ps_pl0_clock_request_preserves_fpd_only_topology` verifies KV260 board-part selection, preset ordering, GP1/GP2 disables and that no bitstream or boot-programming command was introduced. These synthetic tests cannot validate a genuine board preset, actual clocks, BD or hardware.
