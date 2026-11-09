> **D2c REAL VIVADO INITIAL AUDITOR SORT ERROR, NOW REGRESSION COVERED:** **2026-11-08 18:51 local / 2026-11-09 01:51 UTC — M05.12d.2c ORIGINAL OWNER VIVADO PROPERTY DISCOVERY SUCCEEDED; INDEPENDENT AUDIT FAILED (NOT YET ACCEPTED):** Original immutable evidence `~/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_20261109T015151Z_BNn7SH`, checkout `b2ad947c952b515acec3c061df2e04d6ddc3aba8`, **`result.txt exit_status=1`**. Genuine Vivado 2025.2 `zynq_ultra_ps_e:3.5` on K26 correctly produced `01_ps_properties.txt` with **57 named properties**, all **14 tracked candidate keys present**, and original Tcl emitted its exact discovery PASS marker. Python auditor erroneously demanded `sorted(values, key=str.lower)` while Tcl actually emitted `lsort` (case-sensitive ASCII). In original report `PSU__USE__STM` precedes `PSU__USE__S_AXI_ACE` — valid under Tcl order, invalid under Python lowercase order. Original independent audit printed `property records not sorted as the original Tcl contract`; **NO other failure identified**. Focused fix uses `sorted(values)` to match Tcl, preserving strict ordering/duplicate/malformed-value checks, and adds actual-owner-key regression with reversed-order negative case. Original evidence remains exit1 and unmodified; **fresh real Vivado runner exit0 plus independent PASS still required**. Actual discovered default values include `PSU__USE__M_AXI_GP2=1`, `M_AXI_GP0=0`, `M_AXI_GP1=0`, `S_AXI_GP0..6=0`, `IRQ0=0`, `FABRIC__RST=1`, `PL0_REF_CTRL__FREQMHZ=100`, `FPGA_PL0_ENABLE=1`; these are an UNCONFIGURED IP catalog only, not PS/DDR enablement or actual PL clock measurement. M05 OPEN; PR #79 DRAFT/unmerged; no hardware.

 New test `test_owner_d2c_ascii_sort_regression_stm_precedes_s_axi`; total M05 native methods increases **290→291** (M01–M04 stay91). Genuine fresh D2c run remains pending and original evidence `exit_status=1`. [Incident details](M05_12D2C_FIRST_AUDIT_SORT_FAILURE_2026_11_08.md).

> **M05.12d.2c NATIVE TEST COUNT CONFIRMED:** **LATEST D2c NATIVE CI VERIFIED (source+docs `9718afc5929437a3601bb08c72762d095426dd81`):** Five GitHub Actions workflows SUCCESS, [M05 run 42546806598](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42546806598). **290 M05 named methods** (289 PASS +1 preinstall Icarus skip; mandatory postinstall Icarus elaboration + 9/9 original D1 tests PASS) plus **91 M01–M04** (22+28+21+20) = **381 distinct native methods PASS at least once**. New D2c synthetic PSU property-catalog regression **8/8 PASS** (also checked in mandatory separate CI stage). Actual original D2a owner Vivado PS default catalog already accepted; D2c **genuine owner Vivado CONFIG.PSU__ discovery NOT YET RUN**. This CI does not run Vivado/PS/DDR and does not attest to enabled FPD/HP/HPC ports. Eight new native D2c test methods explained below. D2c actual Vivado PS property values are pending.

## 2026-11-08 / 2026-11-09 UTC — genuine M05.12d.2a accepted, new M05.12d.2c strict PSV property inventory

**OWNER ORIGINAL genuine Vivado D2a ACCEPTED:** `neuromorphic_v1_m05_12d2a_ps_inventory_20261109T013033Z_oCd1O9`, source `c7dfffb351db3e5779384161a7b45d5968ef95c6`, `exit_status=0`, v3.5 Zynq UltraScale+ PS default (no preset/DDR). Master HPM0_LPD default enabled1; **none of 9 potential HP/HPC/LPD/ACE DDR slave default pins active**; `pl_clk0` and `pl_resetn0` output pins present, other selected clocks/IRQ absent by default. Independently audited `ps_to_pl_master_defaults=1`, `pl_to_ps_slave_defaults=0`, `pin_defaults=2`. Nine old guessed `PCW_*` property keys unavailable (do not infer silicon absence).

**NEW D2c `tests/test_m05_12d2c_ps_properties.py`: 8 native methods, entirely synthetic (NOT genuine IP).** Test coverage:
- `test_genuine_output_schema_can_report_available_psu_keys`: valid synthetic PSU defaults and proper target count.
- `test_empty_config_value_is_an_explicit_default_not_absence`: empty readback represented safely, not mislabeled missing.
- `test_wrong_target_presence_missing_duplicate_and_extra_rejected`: contradictions, missing, duplicate or unknown targets fail closed.
- `test_wrong_part_ip_mode_scope_property_count_rejected`: reject corrupted part, VLNV, source mode, claimed board preset or count.
- `test_property_format_duplicate_unsorted_noncanonical_and_unknown_rejected`: reject malformed/noncanonical encoding, duplicate/unknown properties.
- `test_sorted_property_list_and_raw_escaping_are_strict`: list order and control-character values must be valid.
- `test_cli_requires_original_report_and_never_modifies_it`: strict independent parser, read-only, fails missing original file.
- `test_no_board_no_ps_changes_and_true_config_property_discovery`: only in-memory Vivado default IP + readback; no PS/DDR writes, board or bitstream; shell runner syntax/arg safety.

D2c PS keys are NOT physically verified in native CI and must be run in operator Vivado. [Current D2c runbook](M05_12D2C_PS_PROPERTY_DISCOVERY_2026_11_08.md).

---

> **M05.12d.2 VERIFIED HOST TEST RESULTS:** **NATIVE VERIFICATION VERIFIED at implementation+doc commit `338b1406da363a2ae33f14868143a750aa68debf`:** all five GitHub Actions workflows **SUCCESS**, including [M05 workflow 42545536913](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42545536913). **282 named M05 methods** were discovered (281 PASS + one early pre-install Icarus SKIP, later mandatory `iverilog` and 9/9 original D1 module-ref tests PASS); **91 M01–M04 methods PASS** (22+28+21+20). Thus all **373 distinct native methods PASS at least once**, including 14/14 brand-new D2a/D2b tests and exact source fingerprints. Native CI uses synthetic PS catalogs; **NO genuine M05.12d.2a Vivado PS IP run has been provided**, so the PS inventory gate remains PENDING. D2b pure-host admission is native verified only. Original genuine D1 partial four-AXIS net PASS remains accepted. The 14 new precise D2 host tests and accepted owner D1 genuine Vivado status are documented below; do not relabel synthetic PS inventory as actual K26 IP evidence.

## 2026-11-08 local / 2026-11-09 UTC — M05.12d.1 owner Vivado PASS and M05.12d.2a/b new synthetic tests

**Accepted original D1 owner run:** `neuromorphic_v1_m05_12d1_axis_graph_20261109T011233Z_Qjt8oT`, source `c702d1712e153aa283c55f1e35c079738ea1c50e`, **exit0**, real Vivado source_mgmt_mode All, four correctly directed/point-to-point connected DMA↔shell 256b AXIS nets and independent Python graph audit PASS. Still no physical PS/HLS/DDR/clock wiring. Original unresolved `IP_Flow 19-11770` missing `clk FREQ_HZ` warning and inferred ASSOCIATED_BUSIF only neuron stream must be reviewed in full connected design.

**New M05.12d.2a `tests/test_m05_12d2a_ps_inventory.py`: seven synthetic PS IP-catalog tests (not Vivado).** Exact methods:
- `test_fully_disabled_default_catalog_is_discovery_not_integration` — accepts complete default-disabled PS port inventory without mislabeling it as usable connected ports.
- `test_enabled_directional_ports_count_not_assumed_from_defaults` — positive synthetic HPM master/HP slave/PS output clock readback.
- `test_wrong_direction_or_enabled_field_is_rejected` — rejects direction inversion and non-binary active bits.
- `test_missing_duplicate_extra_wrong_vlnv_or_preset_is_rejected` — rejects missing/duplicated/extra IP fields, wrong VLNV, hypothetical physical/preset scope and truncated text.
- `test_properties_can_be_observed_but_absence_not_assumed_enabled` — available property observations do not imply actual PS interface enablement.
- `test_cli_is_read_only_and_missing_report_fails_closed` — strict stand-alone audit fail-closed and read-only behavior.
- `test_safe_offline_runner_and_no_configuration_side_effects` — bash syntax/help/arg and read-only Tcl no-board safety.

**New M05.12d.2b `tests/test_m05_12d2_control_map.py`: seven synthetic host-only address-map tests.** Exact methods:
- `test_six_independent_apertures_and_directional_dma_offsets` — six distinct control banks, MM2S vs S2MM length and shell version offsets.
- `test_no_missing_extra_duplicate_or_wrong_bank_admission` — reject missing/duplicate/unknown banks.
- `test_overlap_and_touching_regions` — reject overlap but allow exact 4KiB-aligned adjacent windows.
- `test_alignment_length_rejection_and_40_bit_bound` — check 4KiB alignment, 4KiB–1MiB supported control aperture, PS 40bit arithmetic overflow.
- `test_bools_and_non_ints_cannot_be_accepted_as_addresses` — reject bool/coerced non-integer bases and lengths.
- `test_read_only_immutable_and_unknown_register_refusal` — immutable plan, unknown HLS generated offset and wrong-direction DMA registers cannot be guessed.
- `test_no_default_addresses_or_hardware_mmio_backend` — no physical memory, driver or default address assignment.

**Total new 14 D2 named native methods**; all new D2 source, actual synthetic test outcomes and source hashes are versioned in the existing M05 GitHub workflow. Genuine local Vivado `zynq_ultra_ps_e` default inventory is STILL PENDING operator. [Full D2 implementation and local commands](M05_12D2_PS_INVENTORY_AND_CONTROL_APERTURES_2026_11_08.md). The previously verified D1 stable CI had **268 M05 +91 earlier=359** unique methods (one Icarus preinstall skip later explicitly passed). Expected new total **282 M05 +91=373** only after corresponding full native CI passes; no PS/DDR was exercised.

---

> **M05.12d.1 REPAIR TEST COUNT VERIFIED:** **POST-REPAIR CI PASSED (2026-11-08 local / 2026-11-09 UTC):** source and incident-doc commit `7f982c39a38197fda576a6acf5dd38d8734f12fe` has all **five GitHub Actions workflows SUCCESS**; actual [M05 run 42543219964](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42543219964) job log includes `test_auto_source_management_before_module_reference_regression ... ok`, source-mode bad/missing-report negative tests, and **268 M05 named methods** (267 PASS + one pre-install Icarus skip, then mandatory Icarus installation/recompile and **9/9 D1 methods PASS**, including the formerly skipped elaboration). M01–M04 22+28+21+20 =91 PASS; **359 distinct native methods passed at least once**. This verifies Python/RTL host logic only; **genuine post-fix M05.12d.1 Vivado graph still PENDING**. Original `neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa` stays `exit_status=1` and immutable. One new source-mode regression increases M05 named-method inventory from 267 to 268; M01–M04 remain91. Source mode is also strictly required in independent synthetic report negative tests; these are NOT genuine Vivado module-reference resolution tests.

## 2026-11-08 / 2026-11-09 UTC — first genuine M05.12d.1 Vivado module-ref failure and strict source-mode regression

Original operator M05.12d.1 evidence `~/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa`, checkout `eea1a56f6486365e22211f525c1d5eaecfc5fea0`, **exit_status=1**. Vivado reports `filemgmt 56-176` + `56-587`: manual compile-order mode makes `m05_12d_axis_shell_ref` unavailable for `create_bd_cell -type module -reference`, followed by BD 41-1690 and BD 5-7. No four AXIS connections nor independent audit executed. Existing M05.12c passed configuration is a separate previously accepted gate.

**New native method:** `test_auto_source_management_before_module_reference_regression` proves the Tcl sets AMD-required `source_mgmt_mode All` immediately after scratch project creation, before `add_files` and `update_compile_order`; asserts two readback guards, no manual override, and actual source mode printed into report. Existing `test_config_provenance_duplicate_unknown_and_partial_rejected` now additionally rejects `DisplayOnly` or missing `source_mgmt_mode` in strict synthetic report; positive tests include `META|source_mgmt_mode|All`. **This is a native static/synthetic gate, not a true post-fix Vivado PASS.** [Full incident](M05_12D1_FIRST_MODULE_REF_FAILURE_2026_11_08.md).

All original evidence preserved, new user local Vivado rerun pending. Full M05.12d.1 partial PL graph remains OPEN.

---

> **M05.12d.1 NATIVE CI VERIFIED:** **CI VERIFIED at source+documentation commit `e49c8ed18f5206d887175588c6e05d5523459a4b`:** all five GitHub Actions workflows **SUCCESS**. [M05 workflow 42541636739](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42541636739) exercised **267 named M05 methods**: first Python discovery executed 266 PASS and **one Icarus-dependent SKIP** before Icarus was installed; then a mandatory post-install step compiled the exact RTL shell wrapper with Icarus and reran all eight M05.12d.1 tests, including the previously skipped elaboration (**8/8 PASS**). Prior accepted M01–M04 methods **22+28+21+20=91 PASS**. Therefore all **358 distinct named native methods have passed at least once**; none of these CI tests is genuine Vivado IP Integrator connected-net verification, which is still pending local operator evidence. The exact eight new M05.12d.1 tests and the extra M05.12c read-only property regression are explained below. Do not conflate CI with original Vivado stream-net proof.

## 2026-11-08 local / 2026-11-09 UTC: M05.12c four DMA real Vivado PASS; M05.12d.1 new host tests

**M05.12c original operator Vivado configuration accepted:** `~/Thesis_Evidence/neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce` on source `0ea2178c71023250150609a2983a67bbd6c84ef2`, `exit_status=0`, four AXI DMA 7.1 K26 IPs all 256b stream/AXI-MM, length24, SG0, directional MM2S×3 and S2MM×1 and strict independent audit PASS. The original Vivado log contains four `BD 41-737` critical warnings for writing **read-only async property**. Source now only READS/REQUIRES the value0, and adds **one native regression method**: `test_read_only_clock_property_is_checked_not_written`. Do not erase original warnings or call this a full connected BD.

**M05.12d.1 new `tests/test_m05_12d1_axis_graph.py`: 8 native methods, synthetic graph reports / actual source inspection; NOT Vivado.** One Icarus elaboration method skips in the *pre-install* Python suite when Icarus absent; the modified M05 CI then installs Icarus and explicitly compiles the new shell-wrapper after the standalone RTL tests. New native coverage:

| Exact test method | Purpose |
| --- | --- |
| `test_four_connected_point_to_point_links_synthetic` | Accept exact 3→shell and shell→1 reported AXIS links in a synthetic transcript. |
| `test_wrong_link_or_missing_trace_link_fail_closed` | Reject missing, duplicate, cross-wired trace and shared net aliases. |
| `test_config_provenance_duplicate_unknown_and_partial_rejected` | Reject wrong SG, part/version/scope, missing/duplicate IP/shell and incomplete report. |
| `test_wrapper_exactly_maps_existing_shell_ports` | Require exact 54 original shell ports mapped 1:1 by the new RTL wrapper. |
| `test_wrapper_has_all_axi_stream_byte_qualifiers` | All 4 AXIS groups must carry 256-bit TDATA, 32-bit TKEEP, TLAST, TVALID, TREADY and interface annotations. |
| `test_wrapper_native_icarus_elaboration_without_hls` | Icarus structural compile of new wrapper with actual, unchanged M05.11 RTL when installed; CI installs Icarus in a later mandatory stage. |
| `test_audit_cli_is_read_only_and_fails_if_missing` | Original synthetic transcript unchanged by audit, missing file fails closed. |
| `test_no_board_runner_and_actual_bd_net_proof_requirements` | Require in-memory Vivado RTL Module Reference, four real `connect_bd_intf_net`/net adjacency checks, unique evidence, forbid board, full BD, bitstream and DDR actions. |

**Provenance:** The previously documented **258 M05+91 other=349 named native tests** at M05.12c source `c5fa13f433c9b0746892a71b029dc3ef9889eccb`. Following one clock-warning regression plus eight d1 methods, expect **267 M05 named tests** and **91 previous** = **358 named methods** once CI verifies. Note any skipped Icarus method in the preinstall Python run separately, and require the new mandatory post-install wrapper compile stage. No real Vivado four-DMA connected-graph result has been provided; its operator command is in [M05.12d.1 runbook](M05_12D1_OFFLINE_PL_AXIS_GRAPH_2026_11_08.md).

---

> **LATEST M05.12c TEST RESULT:** **Native CI independently VERIFIED at M05.12c implementation commit `c5fa13f433c9b0746892a71b029dc3ef9889eccb`:** [M05 workflow 42540072916](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42540072916) original job log explicitly records all seven new M05.12c tests `ok`, **258 M05 methods PASS**. The four previous workflows M01–M04 all PASS (20+21+28+22=91), giving **349/349 named native methods PASS**. These are host-side regression/synthetic report tests and prior standalone RTL smoke, **not Vivado evidence for the new four-IP customization**. Real M05.12c Vivado readback remains PENDING user. Complete explanation of seven exact new native tests is provided below; their mocked IP reports are not physical RTL data. Original operator M05.12b catalog-only Vivado PASS recorded separately.

## 2026-11-08 local — M05.12b owner Vivado catalog PASS and new M05.12c synthetic native tests

**M05.12b genuine operator-owned Vivado discovery ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`, checkout `1dc439c9e06e8580008857db52ccba63d25965ca`, original result `exit_status=0`, actual K26 IP `xilinx.com:ip:axi_dma:7.1`. Defaults are SG1, both directions, 32bit stream/memory, length14 and addr32. No actual PS/DDR or configured 256b IP was verified by this earlier catalog run.

**M05.12c new `tests/test_m05_12_dma_candidate.py`: seven independent SYNTHETIC NATIVE tests.** They do not invoke Vivado, accept raw connector evidence, configure an actual DMA core, access a board, or demonstrate PS/PL operation.

| Actual method | Exact positive/negative test |
| --- | --- |
| `test_complete_four_direction_256b_24bit_direct_candidate` | Synthetic report admits exactly MM2S ×3 and S2MM ×1 with requested strict settings and direction pins. |
| `test_wrong_width_length_mode_or_address_rejected` | Reject wrong AXIS/memory width, length14, SG enabled, disabled MM2S direction, alternate address width, micro/DRE/CDC changes. |
| `test_direction_pins_missing_wrong_or_duplicate_rejected` | Reject missing/duplicate/direction-mismatched AXI4-Stream/AXI-MM pins. |
| `test_provenance_missing_extra_duplicate_or_reordered_rejected` | Reject missing/duplicate cell, wrong IP/part, unexpected physical scope marker, missing source fields, extra/partial report. |
| `test_cli_read_only_valid_and_missing_report_failure` | Separate Python CLI reads fixtures without modifying original content and fails on missing report. |
| `test_runner_syntax_help_bad_arg_and_evidence_contract` | Bash `-n`, `--help`, invalid option, original evidence path/manifest/proof layout. |
| `test_offline_tcl_has_strict_readback_and_no_hardware_actions` | Require in-memory K26/Vivado IP configuration+readback and forbid connected BD, hardware, implementation or core changes. |

**Current status:** M05.12c source and tests committed, native CI to be assessed at its source commit. Genuine four-IP configuration readback **PENDING operator**; [M05.12c specification and runbook](M05_12C_FOUR_DMA_IP_CONFIGURATION_2026_11_08.md). The previous 251 M05+91 M01–M04=342 PASS were before these seven tests; expected 258 M05 +91=349 only once CI confirms. Do NOT conflate synthetic text transcript tests with actual Vivado 2025.2 proof.

---

> **LATEST CI VERIFICATION (2026-11-08 local):** **Current source+documentation commit `c3632f81cdf6f35fec6bdccc419044644ddefbd3` has all FIVE CI workflows PASS:** [M05 run 42539252472](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42539252472) original job log reports **251 M05 native tests PASS**, including both new M05.12b source-only IP probe safety tests; M01–M04 report **20+21+28+22=91 PASS**, for **342 named native PASS**. The M05.12b *real Vivado catalogue run is not yet done*; no actual AXI DMA IP/PS/DDR integration or board verification is claimed. All 17 M05.12 native test method names and their exact positive/negative meanings are explained below; these are **host/synthetic or static** only. Genuine M05.11c XSim acceptance and the earlier failed evidence are recorded separately below.

## 2026-11-08 owner M05.11c integrated XSim ACCEPTED; M05.12 new native test inventory

**Original operator evidence:** `~/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`, checkout `bf20f33aa07df2b187bfb837ee5ba2a946cb7098`, `result.txt exit_status=0`, genuine Vivado 2025.2 `04_xsim.log` RTL PASS, independent `05_dma_frame_replay.log` PASS; success run 24/24 committed, late status4 failure run 8 provisional/0 committed, correct footer/TLAST and 148 output/HLS stalled cycles. The original failed postcheck evidence remains exit_status=1 and is NOT overwritten. This gate is verified **OFFLINE ORIGINAL HLS RTL plus transport shell only**; no real DMA/PS/DDR/physical route.

### M05.12a — 15 NEW SYNTHETIC HOST-ONLY methods

Source: `tests/test_m05_12_dma_contract.py`; design: `src/neuromorphic_accelerator_v1/m05_12_dma_contract.py`. Native GitHub Actions **PASS 15 methods** and all 249 M05 tests at `9577fc9b8f98b1d7a2c5f5334de8ba914fe4fdd7`; earlier 91 methods PASS; 340 total. Does **not** instantiate AXI DMA IP or run PS DDR/cache.

| Exact native method | What is tested / invalid path |
| --- | --- |
| `test_exact_packed_buffers_s2mm_worst_case_and_source_counts` | 32B padded 2-neuron/one-synapse/event sources, 25-beat capacity, full session ID. |
| `test_zero_count_mm2s_skipped_not_zero_length_submitted` | Empty synapse/event inputs have no DMA submission. |
| `test_receive_capacity_includes_terminal_footer` | 1024×64 trace requires 2,097,184 bytes; insufficient 21-bit length rejected. |
| `test_length_width_does_not_silently_split_stream_into_early_tlast` | 14-bit cap rejected for 1024 neurons; no unverified fragmented MM2S. |
| `test_unsupported_ip_mode_width_or_identity_fail_closed` | Invalid bit-width, 128b streams, SG/micro, bad session IDs denied. |
| `test_receive_must_be_armed_before_start_and_sticky_fault` | START before S2MM arm is FAULT, cannot silently reuse. |
| `test_receive_buffer_ownership_before_arm` | Refuse to arm RX without declared device ownership. |
| `test_positive_success_uses_actual_packet_and_full_input_completion` | Full MM2S completion + status0 + 25-beat packet produces 24 committed rows, one-use ledger. |
| `test_duplicate_mm2s_and_false_dma_or_cache_proof_are_sticky` | Reject duplicate, short, missing input TLAST, stale cache proof or zero-length port. |
| `test_hls_completion_must_be_latched_before_footer` | HLS status must be valid and latched before FINISH. |
| `test_success_rejects_missing_mm2s_completion` | Do not accept nominal status0 with outstanding input DMA. |
| `test_fail_closed_on_missing_tlast_cache_invalidity_or_write_fence` | RX TLAST, cache invalidate, byte length, write drain, quiescence and completion are all required. |
| `test_status4_partial_frame_never_commits_and_requires_reset` | Late error drains 8 provisional rows, commits0, leaves sticky FAULT. |
| `test_wrong_session_or_truncated_success_never_published` | Reject wrong footer session, missing terminal data or oversized trailing data. |
| `test_explicit_abort_is_sticky_and_no_auto_recovery` | Timeout requires explicit full-system verified recovery; no silent restart. |

### M05.12b — 2 NEW SOURCE-ONLY IP-probe safety methods (not real Vivado)

Source: `tests/test_m05_12_ip_catalog.py`.

| Exact native method | What is tested / invalid path |
| --- | --- |
| `test_bash_syntax_help_and_invalid_argument_do_not_need_vivado` | Runner syntax, --help and bad-flag rejection without Vivado or any device. |
| `test_probe_is_catalog_only_with_no_hw_or_persistent_bd_actions` | Tcl is in-memory catalog only; rejects references to launch/synthesis, bitstreams, HW manager, opening a project, and other prohibited actions. |

**Evidence boundary:** even if all 17 new tests pass, there is no actual Vivado 2025.2 AXI DMA catalog run (operator still required), actual four-direction system block diagram, two PS MMIO bases, DDR cache coherency, physical DMA completion or routed timing. [Full M05.12 development/verification spec](M05_12_DMA_ADMISSION_AND_IP_CATALOG_2026_11_08.md).

---

## 2026-11-08 M05.11c original operator XSim postcheck failure, strict parser repair

The original genuine Vivado 2025.2 *integrated* generated-HLS+shell testbench did **PASS**, with 24 status0 rows committed, then 8 status4 rows rejected, 148 output stalls, and correct TLAST footers. However the original overall `result.txt` recorded **exit_status=1**: `m05_11c_replay.py` rejected the SV bench's **legitimate** `M05_11C_ROW` diagnostic lines as unknown. Preserve operator folder `neuromorphic_v1_m05_11c_real_hls_20261108T235448Z_NzKhyY` (checkout `60c48fe32eed4adb28ba10e7c822fbed63abc3d0`). Full acceptance remains **PENDING owner rerun**. [Detailed failure and original proof boundary](M05_11C_FIRST_XSIM_POSTCHECK_FAILURE_2026_11_08.md).

**Three new M05.11c native synthetic regression methods (not real XSim):**

| Actual test method | Required behavior |
| --- | --- |
| `test_observed_xsim_row_diagnostics_match_raw_dma_words` | Parse 24+8 interleaved `DMA`/`ROW` marker pairs and verify each diagnostic against trace fields decoded from its preceding accepted 256-bit word; commits remain 24+0. |
| `test_corrupt_missing_duplicate_and_misordered_row_diagnostic_rejected` | Reject a corrupted spike, missing/duplicate row diagnostic or incorrect run ID. |
| `test_row_diagnostic_after_footer_and_unknown_marker_rejected` | Reject misplaced row diagnostics and unknown tagged records; do not weaken failure-on-unrecognized-marker contract. |

Existing 14 methods retained; **17 M05.11c methods VERIFIED in native CI**, **234 M05+91 earlier=325 named native methods PASS** at repair source commit `6b5fa76f589d37e103752cf173cc74d0a7355aca`. [M05 workflow 42537892857](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42537892857) reports `Ran 234 tests ... OK`, including all three new tests; M01–M04 workflows also PASS. Genuine post-fix integrated XSim remains pending. The kernel, RTL shims, SV bench, 1/7 `TREADY` test, source hashes and original failed evidence are unchanged. No new Vivado PASS is claimed by this fix.

---

## CURRENT M05.11c test explanation — 14 synthetic host methods; real generated-HLS XSim not yet run (2026-11-08)

**Primary handoff:** [M05.11c current next-chat seed](M05_11C_NEXT_CHAT_HANDOFF_SEED_2026_11_08.md); detailed [generated HLS + AXI-Lite shell contract](M05_11C_REAL_HLS_STREAM_SHELL_INTEGRATION_2026_11_08.md).

The actual committed tests are in ../tests/test_m05_11c_hls_shell.py. They construct a **synthetic text transcript** with two runs using build_fake_dma_packet_for_test and pass it to scripts/m05_11c_replay.py. They **do not invoke real Vivado XSim**, no matter that the log strings resemble the future simulator. The helper constructs success: 12 ticks ×2 neurons = 24 rows, status0, 24 committed; late error: 4 ticks ×2 =8 provisional rows, status4, **zero committed**. Footer/session/TLAST bytes are checked through the existing accept_dma_frame and RollingTraceCommitGate. The HLS-neuron source is not executed by these Python tests.

| Actual test method | Check / invalid case |
| --- | --- |
| test_full_synthetic_raw_dma_transcript | Entire two-run positive transcript decodes to exactly (24 committed, 0 committed). |
| test_missing_tlast_is_rejected | Remove footer TLAST independently from run0/run1; refuse both. |
| test_wrong_session_footer_is_rejected | Change failure-run session to success ID; refuse stale/wrong provenance. |
| test_failed_run_must_not_commit_partial_rows | Fake committing 8 invalid provisional rows; reject atomicity violation. |
| test_missing_duplicate_or_early_final_rejected | Delete, duplicate or reorder simulator final marker; reject. |
| test_wrong_tkeep_and_trace_padding_rejected | Corrupt TKEEP and forbidden transport high-bit padding; reject. |
| test_deleted_or_extra_256bit_handshake_is_rejected | Drop or repeat one accepted 256-bit transfer; reject. |
| test_recurrent_spike_and_raw_hls_word_are_checked | Flip neural trace bit for tick8 neuron1; reject altered recurrent output. |
| test_wrong_status_in_raw_terminal_beat_is_rejected | Change the successful run's terminal status; reject. |
| test_missing_sim_pass_or_fatal_is_rejected | Missing or duplicate PASS, or injected Fatal; reject. |
| test_cli_reads_only_and_never_mutates_logs | CLI processes a temporary simulated log and leaves the exact original bytes unchanged. |
| test_cli_missing_real_log_fails_closed | Missing input log causes nonzero CLI failure and explicit error. |
| test_operator_script_uses_real_hls_source_and_ram_assets | Static script inspection requires correct HLS RTL/part/ROM and RAM-init staging/decoder instructions and absence of Vitis synthesis or board programming. |
| test_sv_connects_two_real_axi_banks_without_modifying_hls | Static SV source inspection checks genuine HLS instance, shell instance, two sessions, status4 and backpressure/TLAST hookups. |

**Other native regressions:** M05's full pattern includes **231** named methods and M01–M04 includes **91** (total **322**) at original source commit 7834632180d44a5179e2609e6c1cefde15c851eb; all five workflow checks PASS at that commit. Check CI again at latest branch HEAD after documentation updates. Do not recast this count as 322 independent FPGA tests.

**Remaining genuine test (still PENDING):** In a shell with **Vivado 2025.2** loaded, run scripts/run_m05_11c_hls_shell_xsim.sh with the original genuine K26 rolling --impl evidence directory. This compiles **actual prior-generated HLS Verilog**, existing shell components, authentic RAM init and the two-session SV bench. The wrapper requires the real XSim PASS marker, exact status/session/TLAST/row counts and source fingerprints; scripts/m05_11c_replay.py then checks the **actual XSim-logged** accepted 256-bit words. Independently inspect its result.txt, 04_xsim.log and 05_dma_frame_replay.log before claiming M05.11c RTL PASS. A genuine XSim result is still not a physical DMA/DDR/PS or routed timing result.

---

> **M05.11c LATEST (2026-11-08):** Owner **genuine Vivado 2025.2 M05.11b AXI4-Lite controller XSim PASS** `exit_status=0` on checkout `90c31f05a40603914fed507b7f9507220df4d932`; original `~/Thesis_Evidence/neuromorphic_v1_m05_11_axil_20261108T230817Z_HFWBlw`, actual AW/W stagger, R/B backpressure, START/FINISH/ACK, FAULT + verified reset. **M05.11c developed (NOT YET operator XSim verified):** real original Vitis-generated signed32 `m05_rolling_replay` Verilog plus current `m05_11_stream_shell` in one full RTL testbench with **two separate AXI-Lite banks**, 3 padded 256-bit input shims, one 256-bit S2MM-facing TLAST footer. Test two consecutive runs: valid 2-neuron/12-tick recurrent inference must stream **24 rows+1 footer**, hardware status0, COMMIT 24; deliberately unsorted external ticks 0,4,3 must stream **8 provisional+1 footer**, actual HLS status4, REJECT all, custom FAULT (no ACK). Output TREADY 1/7 cycles, exact row semantics and footer counts/session IDs. New `scripts/run_m05_11c_hls_shell_xsim.sh` reuses immutable K26 --impl HLS RTL source + RAM init and regenerates actual HLS regmap, no resynthesis/board. `scripts/m05_11c_replay.py` replays **actual simulator-captured 256-bit handshake words** (16 undefined C padding bits explicitly normalized) through native `accept_dma_frame` and `RollingTraceCommitGate`; independent **14 synthetic native tests**. 231 named M05+91 M01–M04 =322 native tests; **no physical DMA/PS/DDR or new routed clock result**. [Full M05.11c engineering/verification runbook](M05_11C_REAL_HLS_STREAM_SHELL_INTEGRATION_2026_11_08.md); [M05.11b verified register protocol](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md); [canonical evaluation-engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md). M05 OPEN; PR #79 DRAFT UNMERGED; no physical board actions.
>

> **LATEST 2026-11-08 — M05.11a owner Vivado XSim VERIFIED; M05.11b AXI-Lite MMIO developed:** Owner's existing bridge XSim evidence `~/Thesis_Evidence/neuromorphic_v1_m05_11_bridge_20261108T224957Z_AQzMlG`, checkout `b3385619b81bc43ee69a082a2f5c8af258e03696`, `exit_status=0`: *both* genuine Vivado 2025.2 standalone bridge RTL snapshots passed (trace 3 TLAST terminal cases +12 egress stalls +sticky overflow, ingress 128/192 unpad +7 ingress stalls +bad TLAST quarantine). **M05.11b NEW:** `rtl/m05_11/m05_11_axil_session_controller.v` 32b AXI4-Lite slave, independently buffered AW/W channels, persistent B/R under backpressure, programmable session/count registers, start/finalize/ACK lifecycle, nonzero-status quarantine; `m05_11_stream_shell.v` structurally wires MMIO control to three input bridges and trace packetizer, all under single clock; typed host-only register client `m05_11_mmio.py` + 14 fake-MMIO tests; new independent RTL testbench + safe Vivado XSim runner. Original HLS kernel and real Vivado OOC timing unchanged. **Icarus RTL AXI bus test PASS + structural shell elaboration PASS**, but **M05.11b genuine Vivado XSim/PS-DMA/HLS integration pending**. Detailed [custom register-map and control lifecycle](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md), [3-question transport design ADR](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md), [evaluation engine evidence history](M05_EVALUATION_ENGINE_EVOLUTION.md). Operator next: `bash scripts/run_m05_11_axil_xsim.sh` in sourced Vivado 2025.2; no board. M05 OPEN, PR #79 DRAFT/UNMERGED.
>
> **LATEST M05.11a PS/PL TRANSPORT PROTOTYPE (2026-11-08):** The three required architecture questions are answered in the new [M05.11 detailed ADR](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md): **(1)** proposed 3 separate 256-bit MM2S inputs + 1 256-bit S2MM trace, with 256→128/192 low-bit ingress adapters; **(2)** a 192→256-bit trace adapter appends a 32-byte terminal status+count+session footer asserting **TLAST even on zero-row errors**; **(3)** PS arms receive FIRST, feeds/drains concurrently, reads HLS ap_done/ap_return, commands finalize through a future MMIO bridge, verifies actual S2MM bytes/footer/status/quiescence and discards/reset-flushes on any error. All new hardware bridge modules and 2 SV benches are **independent of and leave unchanged** the verified signed32 HLS evaluation kernel. GitHub Actions **Icarus compiled/simulated both standalone RTL benches PASS** (12 output stalls, 7 input stalls, 3 terminal scenarios, malformed input and overproduction quarantines), **203 M05 native Python tests +91 prior=294 named native regression methods**. **Actual Vivado 2025.2 XSim bridge test still PENDING**; physical DMA, MMIO command block, full HLS+bridge RTL and full PS/PL implementation have NOT been built/tested. Local next: `bash scripts/run_m05_11_bridge_xsim.sh` in Vivado-sourced shell; it stores exclusive evidence under ~/Thesis_Evidence. [Canonical optimized engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md) and [controller development ledger](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md) updated. M05 OPEN, PR #79 DRAFT/UNMERGED, no board/JTAG action.
>
> **M05.10 verification boundary (2026-11-08):** Added `test_m05_execution_controller.py` (**18** native test methods) plus `test_m05_execution_abi.py` (**10** native byte-lane/trace tests) = **28 new**, **185 M05 named native tests +91 M01–M04 =276 total**. Covers multiple simultaneous ingress channels, bounded fake FIFOs, delayed output even after completion, late error/discard, short/extra/corrupt trace, timeouts, exceptions, quiescence fence, explicit error recovery and exact 128/192-bit field/padding offsets. **No new real XSim or PS/DMA driver**; test transport explicitly simulated. Historical actual direct XSim M05.9 PASSED 8 provisional status4 +20 valid status0 on same DUT, 213 output stalls, no stale tick8. [Full controller design](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md). M05 OPEN/PR draft.
>
> **LATEST M05.9 — 2026-11-08:** Operator's **real Vivado 2025.2 direct generated-RTL M05.8 late-error test PASSED** (original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T211756Z_234592`, exit0): 11 genuine generated RAM images staged, 8 ordered provisional rows from ticks0..3 including t0/n0 spike, real `BAD_EXTERNAL=4` at tick4, **56 output stalled cycles**, offline host `RollingTraceCommitGate` replay **drained 8 / committed 0**. Prior genuine directed 312 neuron-input and 7573 trace-output stalled cycles and routed 6.503ns OOC evidence unchanged. **New M05.9**: distinct SystemVerilog [two-run recovery test](M05_MULTI_RUN_RECOVERY_GATE_2026_11_08.md) runs the **same RTL instance without pulsing reset**: first run emits 8 provisional rows then status4, second run reloads an entirely new synapse-free network (2 neurons/10 ticks), emits exactly **20 valid rows** including a fresh t1/n1 spike and **zero stale t8 recurrence**, returns status0. New strict read-only XSim transcript replay feeds two independent host commit gates (0+20 committed). **15 new native synthetic/source tests = 157 M05 +91 accepted earlier =248 named native tests**. **Genuine M05.9 direct XSim NOT YET RUN**; do not claim physical PS/PL or DMA integration. [Canonical evaluation-engine optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md). Owner next: run `bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --multi-run` using existing immutable --impl proof. M05 OPEN; PR #79 draft/unmerged, no board/JTAG.
>
> **M05.8 added tests and actual evidence boundaries (2026-11-08):** Operator M05.7 **direct RTL input and output backpressure XSim PASS**, 64 neurons × 12 ticks, 768 ordered records, 312 neuron-input stalled cycles, 7573 trace-output stalled cycles, final status0; this is REAL RTL/XSim, not native tests. New `tests/test_m05_rtl_transaction_replay.py` provides **12 SYNTHETIC XSim transcript replay/negative tests** verifying `RollingTraceCommitGate` discards all provisional rows on hardware-like status4, plus source-only assertions for `--late-error` bench and runner. **142 M05 named native methods +91 M01–M04 =233 total**, five independently native compiled HLS benches (not genuine Vitis). New `--late-error` **has not run on operator's genuine Vivado yet**, so leave it PENDING. [New test design](M05_LATE_ERROR_TRANSACTION_GATE_2026_11_08.md) and [canonical optimization history](M05_EVALUATION_ENGINE_EVOLUTION.md).
>
> **LATEST M05.7, 2026-11-08 — input-stall test coverage corrected, NOT DUT math:** Operator ran genuine direct XSim with *11 real Vitis RAM .dat assets staged successfully* (`neuromorphic_v1_m05_rolling_axis_rtl_20261108T205357Z_221064`), `xvlog` and `xelab` PASS, but XSim stopped at `RTL_STRESS_FAIL no meaningful incoming AXIS backpressure` (coverage gate) after the existing trace/status checks. Two neuron records + one edge/event weren't enough to make ingress TREADY deassert. Prior **separate XSim output-backpressure PASS** remains valid (24 rows, 188 output stalls, final status 0). **M05.7 development:** restored that proven two-neuron SV testbench byte-for-byte; created separate **64-neuron/12-tick/768-row ingress saturation test** with 300 prestart cycles, full trace/status scoreboard and real input VALID/TDATA hold + **>=10 measured input stalls**; runner now selects it using `--ingress`, retains identical original HLS IP, RAM asset checks and new/fatal-aware evidence. **New direct ingress XSim gate is PENDING.** [Canonical engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md) and [M05.7 runbook](M05_INGRESS_BACKPRESSURE_GATE_2026_11_08.md). M05 OPEN; PR #79 draft/unmerged, no board operations.
>
> **LATEST 2026-11-08 — M05.6 direct RTL PASS and next strict backpressure gate:** Operator direct Vivado 2025.2 XSim generated-Verilog test at source checkout after syntax fix **PASSED** (`exit_status=0`), evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T203635Z_212333`: 24/24 two-neuron/12-tick trace records validated, 188 real output `TVALID && !TREADY` stall cycles, 1162 input VALID-gap cycles, correct final status 0. **Input stalls were N/S/E=0/0/0**, and XSim printed missing generated `*.dat` RAM-initialization warnings. Thus output backpressure is verified on this directed RTL workload; inbound stall and initialized-memory gates are **PENDING**. New development: offline runner stages only original Vitis-produced RAM images (fails closed if none exist), strengthened testbench primes input `TVALID` before start and asserts incoming hold-under-stall with >=10 measured input stall cycles. Kernel and earlier **6.503ns routed OOC timing, 35 BRAM/6257 LUT/6887 FF/2 DSP** unchanged. New native tests (9 RAM staging +1 input gate) make **128 M05 +91 older=219 native tests**. Follow-on genuine XSim rerun still required. [Canonical optimization history](M05_EVALUATION_ENGINE_EVOLUTION.md), [M05.6 operator runbook](M05_AXIS_RTL_STALL_TEST_2026_11_08.md). No board actions; M05 OPEN; draft PR #79 unmerged.
>
> **LATEST M05.6 (2026-11-08):** Existing **103 M05 native tests** plus **14 new source-only AXI-Lite register-map and direct RTL stressbench preparation tests** = **117 M05 methods**; +91 accepted M01–M04 = **208 native methods**. New testbench `hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv` and launcher `scripts/run_m05_rolling_rtl_stress.sh` are intended for genuine direct XSim with `TREADY` stalls after pulling branch; **NO genuine direct XSim stress PASS exists** yet. The accepted signed32 HLS core did pass genuine Vivado OOC routing 6.503ns vs 10ns, 35 BRAM, 6257 LUT/6887 FF/2 DSP at original `--impl` run. New [M05.6 harness documentation](M05_AXIS_RTL_STALL_TEST_2026_11_08.md) and [optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md). All evidence remains outside Git.
>
> **LATEST native verification and RTL gate (2026-11-08):** **103 M05 named native methods** (existing 92 plus **11 synthetic source-only audit-parser tests**) + **91 accepted M01–M04** = **194 named native tests**. Five HLS benches additionally compiled/run natively; hardware-optimized signed32 rolling has passed operator-run real Vitis CSim + synth + XSim cosim (10/10 transactions), **not** routed or on-board. New [canonical optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md) and [evidence audit parser](../scripts/m05_hls_evidence_audit.py) ensure next area/timing measurements are recorded with exact source+testbench identities, and no false performance comparisons. Next offline `--rolling --impl`.
>
> **LATEST M05.5 STATUS (2026-11-08):** Operator's optimized **signed32** rolling HLS top genuine Vitis 2025.2 K26 **CSim + synthesis PASS**, commit `827f719778472da39ffa294b431ee848fe360529`, original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_synth_20261108T193909Z_169727`. HLS estimated period **8.256ns** vs requested 10ns; **39 BRAM18K** (down 14 from prior i64 rolling 53), including `current_U` **16 BRAM18K** vs old 30; 9,956 LUT, 8,346 FF, 2 DSP. The single-port bias II lower-bound-2 warning remains; full-run latency unknown. **i32 rolling XSim C/RTL cosim NOT YET RUN** (the old i64 rolling version was verified). `m05_rolling.cpp` source **unchanged** since this synthesis, sha `e5443aa87dcc8819ee8aa680b6ca105facc1aced`. After it, developed a strictly HOST-ONLY [transactional output accept/abort gate](M05_TRACE_COMMIT_GATE_2026_11_08.md): validates row-major framing and per-tick counts, drains provisional records, commits only on final status 0 plus expected row count, discards the whole run on late status, malformed framing or timeout. Added 16 native receiver/model/CLI tests including a toy 1-beat FIFO stall model; **92 M05 +91 accepted prior=183 named native tests PASS**. This is NOT an AXIS RTL/TREADY test, DMA/PS driver, real hardware recovery or physical timing. **NEXT OPERATOR GATE:** after pulling current branch run `--rolling --cosim` (cumulative real CSim, synth then XSim), preserve original reports. M05 remains OPEN, PR #79 DRAFT/UNMERGED; no board operations. [Full boundary and commands](M05_TRACE_COMMIT_GATE_2026_11_08.md).
>
> **LATEST 2026-11-08 VERIFIED RTL AND NEW SOURCE OPTIMIZATION:** The operator's **unchanged i64 rolling engine** at commit `03c3fbc5f8866c44510ff67d2cce8151988fa4d7` has now passed **actual Vitis HLS 2025.2 CSim, synthesis AND XSim C/RTL cosim**. Report: Verilog PASS, all **8/8 transactions**, latency **265 / 3616 / 16492 cycles** min/avg/max, intervals **285 / 3919 / 16512 cycles**, **29077 cycles total**, simulated 10ns clock. Old synthesis **53 BRAM18K (30 for 64-bit current_U), 10,083 LUT, 8459 FF, 2 DSP**, estimated 8.244ns vs 10ns requested. **NEW development since that PASS:** changed only fifth rolling top's internal current wheel `[8][1024]` from signed i64 to **signed i32**, mathematically exact under max 4096 individual signed W16 deliveries per tick (bounds **-134217728 .. +134213632**, signed28 sufficient), and preserve i64 M04 API via explicit sign extension. Added HLS CSim/RTL vectors for both extremal 4096-arrival polarities and 4096 negative delayed recurrent synapses at t+8, plus two M02/M03 full reference tests. **76 M05 + 91 older = 167 named native tests PASS**; current code's genuine Vitis CSim/synthesis/cosim **NOT YET RUN**. NEXT: pull branch and run cumulative `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --synth` (new genuine CSim first; then synth), compare previous current_U 30/total 53 BRAM18K before any new cosim. No physical action, M05 OPEN/PR #79 UNMERGED. [Signed32 proof + gates](M05_ROLLING_I32_ACCUMULATOR_2026_11_08.md).
>
> **LATEST verification count (2026-11-08):** **74 M05 native methods PASS** (14 rolling including new max-horizon 64-tick M02/M03 complete-trace parity and 1024 logical-neuron-boundary test) + **91 accepted M01–M04 = 165 native methods**; 5 HLS testbenches additionally compiled natively. The real rolling HLS synthesis passed on source commit `984f5baf45ce771e94e1e8b2947e1ef27ccc6d58`, new stronger rolling bench is not yet tested under actual Vitis; next gate `--rolling --cosim` cumulative. See [rolling design](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md). Older counts below are historical.

> **LATEST 2026-11-08:** **72 M05 +91 M01–M04 = 163 named native regression tests**, five native-compiled HLS-Csim vector benches. New [12 rolling-wheel native tests](../tests/test_m05_rolling.py) exercise 24–40 tick full-trace M02 dense/event and M03 sparse parity, 8-slot wrap, signed coalescing and count, 4097 late-event invalidation, sorted external ingress and 8-tick delay bounds. Four earlier tops (including integrated) now have **operator-run genuine Vitis CSim + synthesis + XSim cosim PASS**. New *fifth* rolling top has **native-only** PASS; real Vitis is next. Older count/verification paragraphs below are preserved as historical snapshots. [Rolling design and exact commands](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md).

# M05 — Tests explained (native stream candidate + PC event scheduling)

**CURRENT 2026-11-08 STATUS:** Three standalone IPs have real operator-run Vitis CSim, HLS synthesis and XSim cosim PASS. The fourth integrated finite-horizon candidate has **12 new native network tests** and a **native CSim bench PASS**, but has **NOT** been evaluated with genuine Vitis or RTL. **60 new M05 methods + 91 accepted earlier methods = 151 native test methods PASS**; M05 remains OPEN. The original failures/old host-only verification counts in historical sections below are provenance notes, not current gate results.

**Status:** M05 IN PROGRESS, not user-accepted. M05 has **60 named PC-native unittest methods** across [17 streaming/scheduler](../tests/test_m05_stream.py), [12 persistent state memory](../tests/test_m05_stateful.py), [11 signed tick accumulator](../tests/test_m05_accumulator.py) [5 HLS setup/runner safety](../tests/test_m05_hls_setup.py) [3 Vitis-workdir path regressions](../tests/test_m05_hls_path_regression.py) and [12 integrated finite-horizon network tests](../tests/test_m05_integrated.py); additional seeded cross-tick subcases are counted within methods. Accepted regressions: M04 **22**, M03 **28**, M02 **21**, M01 **20**, for **151 named methods total**. Four separate checked-in HLS Csim vector benches are also compiled and executed NATIVELY by CI, not in Vitis.

## Test setup and methodology

`setUpClass` compiles the **real new C++ source** [m05_stream.cpp](../hls/m05_stream_eval/m05_stream.cpp) + [m04_eval.cpp](../hls/m04_lif_eval/m04_eval.cpp) + native-only CLI with g++/c++17 (`-O2 -Wall -Wextra -Werror -pedantic -Wno-unknown-pragmas`); missing compiler or compilation failure fails the suite (no silent skip). Host-stream fallback is a `std::queue`, **not real RTL ready/valid**. Each native batch accepts count 0..1024 and one text line per full 11-field M04 request; returns status, count and ID/tick/status/new state/spike per request. Malformed batch exits nonzero.

[Host sparse runtime](../src/neuromorphic_accelerator_v1/m05_host_runtime.py) runs the actual compiled kernel once per nonempty tick, performs its **own** event-bucket traversal, signed aggregation, exact-zero-safe worklist, positive-delay synaptic fanout, status checks and state snapshots. It does **not** call M02 to produce its result. Tests independently compare **all tick voltage/spike rows** with both M02 dense and M02 event evaluators, and compare worklists/delivery counts with M03 sparse evaluator.

| Exact test method | Mechanism and asserted outcome |
| --- | --- |
| `test_stream_batch_exact_negative_division_and_threshold_equality` | -3×1/2 → -1, inclusive threshold 5 fires/resets -2; W16 maximum old state at threshold also fires. |
| `test_stream_batch_preserves_order_and_per_request_status` | Non-sorted IDs 2,1,0 and tick41; invalid width3 returns status2/zero; legal minimum current -32768 preserved. |
| `test_stream_zero_requests_returns_empty` | Valid empty batch returns success and no fabricated output. |
| `test_stream_input_protocol_rejects_malformed_and_overlarge_batches` | 1025 or negative count, invalid/missing/extra tokens, extra rows and out-of-u32 rational → exit 2, no false output. |
| `test_bias_only_neurons_always_evaluated` | Bias+3 threshold5, zero event; voltages 3,0,3,0; spikes at t1,t3; neuron evaluated all 4 ticks. |
| `test_only_exact_zero_state_idle_is_skipped` | 4-neuron N, only neuron1 has +4 t0; decay1/2 yields 4,2,1,0,0; last tick safely omitted. |
| `test_duplicate_signed_cancellation_before_one_saturation` | Simultaneous +32767,-32768,+6 sums to +5, equality fires/reset -3; no intermediate clamp. |
| `test_parallel_recurrent_self_edges_with_strictly_positive_delays` | Two neurons with self-feedback, signed parallel synapses, delays 1/2/3 and bias; M02/M03 full trace parity. |
| `test_seeded_recurrent_networks_all_tick_state_and_spike_parity` | **12 deterministic seeds**, 6 neurons, 16 signed recurrent/parallel edges, 36 events over 10 ticks; exact M02 dense/event/M03 voltage, spike and worklist parity; bounded evaluation count. |
| `test_4096_admitted_events_exact_without_intermediate_clipping` | 2048 copies (+32767,-32768) → -2048; counts 4096 individual deliveries, one update. |
| `test_4097_external_events_fail_closed` | 4097 zero-current external events cause explicit M04AdmissionError, not silent drop. |
| `test_4097_scheduled_recurrent_events_fail_closed` | One neuron fires and creates 4097 delayed parallel self deliveries; future-tick limit rejected before any successful trace is returned. |
| `test_provisional_resident_capacity_bound` | 1024 empty neurons admitted, all safely skipped; 1025 and zero budget rejected. This **models** a capacity, not SRAM. |
| `test_m02_legal_other_width_or_ratio_rejected_by_first_profile` | W4/W8/W32 or denominator=2^32 valid in Python M02 but outside first W16/u32 hardware admission profile. |
| `test_invalid_zero_delay_is_rejected_before_any_engine_call` | Zero-delay recurrent edge fails M02 validation; no same-tick recursion. |
| `test_missing_host_binary_rejected_without_fake_pass` | Missing native binary fails rather than silently executing Python-only arithmetic. |
| `test_tick_exceeding_u64_rejected_before_any_large_replay` | Horizon outside 64-bit tick metadata rejected before costly/unbounded work. |

**Observed CI:** initial M05 compile **failed** on `-Werror=unused-label` in the HLS top; removed label without changing behavior. Tightened an invalid u32-denominator fixture. [Run 42454758437](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42454758437) at `cd483fe5` logged **17 M05 PASS, 22 M04 PASS, 28 M03 PASS, 21 M02 PASS, 20 M01 PASS**. HLS source/documentation additions require final HEAD CI recheck.

**What these tests do NOT establish:** HLS synthesis, C/RTL co-sim, actual AXIS backpressure, real bounded event FIFO or future queue, on-chip state memory ownership/RAW hazards, DDR/AXI traffic, microarchitectural II/latency, routed clock, physical FPGA performance, energy or Loihi/YANA equivalence. [HLS Csim vectors](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) are **unexecuted** Vitis inputs; include no fake HLS PASS. M05 operator native testing and user approval remain pending. See [M05 verification](M05_PC_ONLY_VERIFICATION.md) and [v3 comparison](M05_ENGINE_V3_COMPARISON.md).


## Additional independent native Csim-testbench smoke gate (not a unittest method)

The M05 workflow now also compiles [`m05_hls_csim_tb.cpp`](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) against the *same* C++ M05 kernel/M04 step via native `g++`, runs it, and requires the testbench's fixed scalar fixtures to return PASS. This confirms the staged Vitis testbench **itself** is internally consistent under the host-only stream shim. It does **not** add an 18th unittest method, call Vitis, prove AXIS ready/valid, achieve II=1, or demonstrate C/RTL parity. **Genuine Vitis HLS Csim/synthesis/C-RTL remain NOT RUN.**


## M05.3 — 12 additional named tests for the persistent 1,024-row state memory candidate

**Source:** [`test_m05_stateful.py`](../tests/test_m05_stateful.py), actual [C++ stateful HLS top](../hls/m05_stateful/m05_stateful.cpp), [text CLI](../hls/m05_stateful/m05_stateful_host_cli.cpp), and [separate HLS Csim vectors](../hls/m05_stateful/m05_stateful_csim_tb.cpp). C++ `static` voltage/bias/threshold/reset arrays and last-tick tags persist across successive function invocations in one process. Memory `BIND_STORAGE` requests BRAM; **native g++ does not establish physical BRAM inference**. The top rejects invalid/duplicate/backward ticks without changing stored state; it does not enforce global tick barrier or external event queue safety.

| Exact new method | Mechanism and required output |
| --- | --- |
| `test_init_read_and_clear_invalidate_without_leaking_old_data` | CLEAR → READ rejects uninitialized; INIT voltage=-11, READ exact; CLEAR then READ rejected, never stale state. |
| `test_negative_decay_inclusive_spike_and_reset` | INIT -3, update with 1/2 gives -1, next input +6 crosses inclusive threshold and resets -2. |
| `test_duplicate_tick_rejected_no_state_write` | First tick4 update accepted; second tick4 returns duplicate status6/zero; READ confirms prior committed voltage. |
| `test_stale_tick_rejected_and_gap_is_allowed_if_scheduler_proves_skip` | Tick9 accepted, tick3 rejects as stale status7, tick11 later accepted; skip legality is still external scheduler responsibility. |
| `test_invalid_init_and_invalid_step_no_state_update` | Out-of-W16 init, invalid threshold/reset and invalid denominators return error4; later READ verifies no write. |
| `test_duplicate_initialization_rejected_unless_cleared` | INIT twice gives status5; CLEAR permits a fresh INIT epoch. |
| `test_invalid_opcode_and_id_fail_closed` | Unknown command, zero/oversized network, or out-of-range neuron ID rejected with zero state/spike. |
| `test_two_neurons_can_advance_in_different_dispatch_order` | Two independent neuron rows processed in non-ID order; spike/reset and negative voltage preserved, demonstrating no old core scan. |
| `test_1024_neuron_physical_capacity_and_independent_state` | INIT all 1,024 row IDs with distinct voltages, READ nonadjacent IDs for independence; this is C++ storage, not BRAM proof. |
| `test_saturation_must_follow_exact_64bit_aggregate` | i64 max/min input triggers one W16 clamp and inclusive spike/reset; no early event-wise clipping. |
| `test_m02_dense_and_event_traces_match_stateful_ram_across_ticks` | **8 deterministic networks**, five neurons each, 13 signed/delayed recurrent edges and 25 currents; all 8×5 update outputs and spikes match BOTH accepted M02 oracles. |
| `test_malformed_or_unrepresentable_cli_inputs_rejected` | Missing, extra, negative-count, non-integer or unrepresentable fields exit 2 without misleading partial output. |

## M05.2 — 11 additional named tests for the tick-sealed signed-aggregate PL candidate

**Source:** [`test_m05_accumulator.py`](../tests/test_m05_accumulator.py), actual [C++ accumulator](../hls/m05_accumulator/m05_accumulator.cpp), [text CLI](../hls/m05_accumulator/m05_accum_host_cli.cpp), and [HLS Csim vectors](../hls/m05_accumulator/m05_accum_csim_tb.cpp). The one-tick store has 1,024 logical ID slots, signed i64 exact sums, a **SEAL barrier**, 4,096 individual W16 contributions/tick, and **sticky-invalid no-readout on error**. There is **no physical future-delay FIFO or router** yet.

| Exact new method | Mechanism and required output |
| --- | --- |
| `test_signed_cancellation_sealed_aggregate_matches_exact_sum` | +32767,-32768,+6 → exact +5, delivered flag1 for ID1; no current for ID0; read only after SEAL. |
| `test_4096_signed_contributions_success_including_zero` | 4,096 W16 signed values, including cancellations, accepted; exact -2048 and count 4096 on final read. |
| `test_4097th_signed_contribution_fails_closed_without_readout` | 4,097th W16 event rejects status5 and latches invalid; SEAL/READ reject status10 until explicit CLEAR. |
| `test_invalid_w16_current_sticky_failure_and_rearm` | Current +32768 outside W16 rejects and locks readout; CLEAR plus new tick allows -32768 exactly. |
| `test_duplicate_begin_or_unknown_opcode_invalidates_current_tick` | Second BEGIN or illegal opcode sets sticky failure; all later work rejected until CLEAR. |
| `test_read_before_seal_is_failure_not_partial_current` | Reading accumulated current while tick is open produces status7, then sticky status10; never exposes partial sum. |
| `test_sealed_tick_rejects_late_add_and_refuses_earlier_sum` | Valid READ succeeds after SEAL; subsequent ADD causes phase error9, then READ refuses previously valid data. |
| `test_wrong_tick_or_neuron_id_or_network_size_fail_closed` | Old tick, ID>=count, or mismatched count rejects, prevents corrupted cross-neuron/current routing. |
| `test_multiple_ticks_reset_touch_without_modifying_old_sum` | New tick clears touched flags; zero-attendance neuron reports zero even if previous tick held a nonzero signed aggregate. |
| `test_m02_recurrent_delivery_aggregate_across_seeded_networks` | **6 seeded recurrent networks**, six ticks each; external and delayed synapses enumerated using accepted M02 spike rows, then every sealed (tick,ID) sum/touched/count checked against independent enumeration. This validates aggregation, **not** future event routing in PL. |
| `test_malformed_transport_rejected_without_partial_results` | Host CLI missing/extra/invalid values cause parse error without partial output. |

## Five HLS config/offline runner tests (source and shell static checks ONLY)

**Source:** [`test_m05_hls_setup.py`](../tests/test_m05_hls_setup.py). Methods:
- `test_three_isolated_k26_configs_have_documented_2025_2_keys`: compare **all three** configs to documented `part=xck26-sfvc784-2LV-c`, `clock=10ns`, 12% uncertainty, `flow_target=vivado` and **`syn.output.format=rtl`**; reject old invalid `package.output.format`.
- `test_configs_reference_real_sources_and_independent_benches`: ensure every `syn.file`/`tb.file` in all 3 configs exists in current checkout and `csim.clean=true`.
- `test_offline_runner_bash_syntax_help_and_bad_flags`: `bash -n`, offline script `--help`, and invalid/duplicate option rejection before running Vitis.
- `test_offline_runner_never_invokes_board_or_old_v3_scripts`: static blocklist of JTAG/HW manager commands and no destructive `rm -rf`; original evidence folder/new run and failure trap required.
- `test_three_tops_are_distinct_and_syn_top_always_matches`: verify top signatures, persistent-state BRAM hints, accumulator overflow control, and script top selection.

**Observed source-only CI:** [M05 run 42456476435](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42456476435), source commit `7cb863b6`: **45 M05 tests PASS**, previous **91 tests PASS**, and **three separate HLS vector testbenches compiled/run with native g++ PASS**. Initial new accumulator test failed because a Python expected-row index was off by one; fixed and reverified, with no accumulator arithmetic change.

**Not validated:** actual 2025.2 HLS Csim/synthesis, RTL equivalence, inferred BRAM/URAM, achieved II/latency/Fmax, AXIS framing/backpressure, on-chip temporal FIFO/synaptic fanout, integrated global tick barrier, PS/AXI/DDR interface, physical K26 or overall speedup. Do not accept M05 as complete based only on native results. **Exact operator HLS stages and required original logs:** [M05_HLS_OPERATOR_RUNBOOK.md](M05_HLS_OPERATOR_RUNBOOK.md). M05 remains OPEN and unmerged pending user verification.


## 2026-11-08 genuine Vitis HLS CSim failure and three new workdir-path regressions

**Real operator evidence (not a CSim PASS):** all three Vitis 2025.2 CSim runs from initial commit `6f5ca78a` **FAILED** before source compilation, with warnings `HLS 200-2001` about missing `syn.file`/`tb.file`, followed by `HLS 200-627` no testbench; Vitis had changed into the evidence folder where old `relative_roots=cwd` no longer referred to the project. It additionally warned `syn.output.format` was deprecated, superseded by `package.output.format`. [Line-level error and remediation](M05_HLS_CSIM_FAILURE_2026_11_08.md).

**Correction:** [`prepare_hls_config.py`](../hls/m05_stream_eval/prepare_hls_config.py) creates a new evidence-local, validated `hls_effective_config.cfg` with absolute design/testbench/include paths and canonical package output format; the [runner](../hls/m05_stream_eval/run_m05_offline_hls.sh) passes it to **each** Vitis command and preserves config/report hashes. The original failed operator evidence is untouched.

**New methods (three named tests):**
- `test_all_three_effective_configs_resolve_from_unrelated_directory`: generate per-run configs for **each** top, prove all referenced C++ files exist via absolute paths even after changing outside the project, verify checked-in templates remained unchanged.
- `test_absolute_config_is_exclusive_and_fails_on_missing_input`: fail explicitly if a C testbench is absent (instead of leaving the error for Vitis) or if an output INI is being overwritten.
- `test_offline_runner_three_kernels_survive_vitis_chdir_with_stub`: run the **actual no-board runner** three times against an **explicitly fake Vitis executable** that changes CWD into each external evidence directory, validates the effective config, and checks that original logs/config hashes/result files are produced. **Stubbed tool output is NOT genuine Vitis CSim.**

The existing five HLS setup tests now assert the corrected `package.output.format=rtl` and `relative_roots=file/../..` (template), plus runner use of the generated effective config, instead of enforcing the deprecated key. Prior 45 M05 tests unchanged; new count **48 M05**, accepted regressions **91**, total **139** named host tests. Real successful Vitis Csim/synthesis/C-RTL evidence is still **NOT RECEIVED**; rerun the three actual CSim steps per [updated operator instructions](M05_HLS_OPERATOR_RUNBOOK.md) and review the original outputs before proceeding.


## NEW M05 integrated finite-horizon scheduler — 11 native whole-network methods

[Design details and safety boundary](M05_INTEGRATED_FINITE_HORIZON_DESIGN.md). Actual C++ [integrated top](../hls/m05_integrated/m05_integrated.cpp) owns 1,024 neuron states, a resident 4,096-edge adjacency graph, eight future-tick signed i64 aggregate+touch+delivery-count buckets and all neural steps in a **single** call. No Python logical-tick service. The CSim vectors in [m05_integrated_csim_tb.cpp](../hls/m05_integrated/m05_integrated_csim_tb.cpp) exercise self recurrence, over-capacity no-output, and a subsequent clean run; compiled natively by CI. **Neither these new tests nor the prior genuine real Vitis results for the three different tops establish integrated HLS or RTL PASS.**

| Exact new method | What is independently checked |
| --- | --- |
| `test_native_csim_vectors` | Compile and execute the separate integrated HLS CSim vector source natively |
| `test_exact_zero_bias_wakeup_with_no_external_events` | Bias wakeups and exact zero/biasless idle skips across all ticks |
| `test_unsorted_zero_and_canceling_deliveries_remain_touched` | Input order independence; zero and signed canceling terms count as touched |
| `test_recurrent_self_parallel_edges_and_future_delays` | Self, parallel, negative edge weights, positive delays, delayed graph fanout |
| `test_negative_decay_rounding_and_threshold_equality` | Truncate-toward-zero leak and inclusive threshold/reset |
| `test_all_4096_signed_deliveries_are_exact_and_admitted` | Full signed W16 admission count with exact i64 pre-clamp aggregate |
| `test_4097_external_deliveries_fail_before_any_trace` | External over-capacity status with no output |
| `test_4097_recurrent_deliveries_fail_before_any_trace` | Future-bucket recurrent overflow causes entire trace to be suppressed |
| `test_horizon_and_shape_validation_no_publication` | Reject 0/9 ticks, zero neurons, invalid unsigned decay ratio |
| `test_invalid_neuron_synapse_and_external_fail_closed` | Invalid threshold/delay/tick/W16 reject without output |
| `test_native_wrapper_rejects_extra_unframed_fields` | Reject trailing malformed data in the test-only native command adapter without publishing a misleading result | 
| `test_seeded_networks_full_trace_and_sparse_schedule` | 16 seeded recurrent networks, 8 ticks each; every voltage, spike, touched worklist and arrival count compared against independent M02 dense, event, and M03 sparse |

**Count now:** 60 M05 named PC-only methods + 91 M01–M04 = **151 native methods**, plus four native-compiled CSim vector benches. **NEXT REAL TOOL GATE:** new fourth `--integrated --csim`, then `--synth`, then `--cosim`, preserving full original Vitis evidence outside Git.
