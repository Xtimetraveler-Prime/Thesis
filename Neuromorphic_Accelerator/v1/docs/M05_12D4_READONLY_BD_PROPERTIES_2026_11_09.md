> **OWNER D4.1b ORIGINAL VIVADO GENUINELY RUN AND LIMITED GATE PASSED, 2026-11-09 UTC:** Owner supplied actual original folder ~/Thesis_Evidence/neuromorphic_v1_m05_12d4_readonly_bd_20261109T154700Z_yG0IsT, source SHA 541cc1742c3d20493af381999366d94cf0cfa4a3, result exit3, 23 original interfaces and 11 pair-nets independently checked, 382 original generated files/118 mem_sc confirmed; documented intentional original OCM exclusion 1, remaining 63 BD warnings UNRESOLVED. This earlier runbook's old D4.1b PENDING language is now historical. The **NEW single follow-up owner D4.2–D4.4 verification and complete commands** are [here](M05_12D4_PROTOCOL_GATE_2026_11_09.md). No source-only or model-file listing can prove genuine vendor downsize functionality. M05 OPEN, M06 NOT STARTED.

# M05.12d.4 D4.1b — original Vivado 2025.2 read-only SmartConnect endpoint proof

**2026-11-09 UTC — source/staging complete, genuine owner D4.1b run PENDING.** Current research branch, draft PR #79, M05 OPEN, M06 NOT STARTED. Preserve all original evidence, failed and passed.

## Accepted NEW owner evidence and its limits

The owner's D4.1 original file inspection at:

    ~/Thesis_Evidence/neuromorphic_v1_m05_12d4_warning_inventory_20261109T152119Z_jBQsxu

returned exit_status=3, correctly confirming that every original generated IP file hash still matches D3; generated=382, mem_sc=118, and exactly **64 original Vivado BD warnings** requiring further analysis. This is a PASSED original D3 provenance+inventory check, NOT a passed AXI 256-to-128 transfer gate. The original D3 remains:

    ~/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ

at original code commit fc17906e95c727d9091a443e2082fe00c95d4e0c, result exit_status=0. Owner shared original hashes 03_vivado.log=31cadb319f2f9fcd17ff217bfb87c5250e4cafe8acd4345fccd9ec72ef and 16_ip_output_sha256_manifest.txt=2a6abae03ce19910388c691b2a40812ceb4405d6b3fbc909292feab704c8de38. Actual first 64-warning examples include genuine BD 41-1629 OCM exclusion at line774 and BD 41-3281 PS/four DMA SmartConnect auto-configuration warnings at lines775-779. No full original generated-IP pin/field evidence was uploaded here; field meaning cannot be guessed.

## New development: why this gate exists

Warning path fragments /m00_nodes, /m05_nodes, s_sc_payld and similar are vendor-generated internal names with no reliable top-level parent qualification in the text. Control SmartConnect has six output interfaces (NUM_MI=6) and memory SmartConnect has four input interfaces (NUM_SI=4); that is an interesting distinction, not proof of an individual warning's origin. The original 172→168, 55→53 and 9→7 possible high-bit losses cannot be declared harmless from pin naming. Auto-configuration 41-3281 explicitly says manual configuration may be needed; no USER-width change is justified before native readbacks.

The implementation now includes:

1. scripts/m05_12d4_generated_hierarchy_index.py: re-runs the original D3 SHA/382-file audit and checks the accepted D4.1 JSON exact equality with the recomputed original warning inventory, inspects each hashed generated HDL/IP file read-only and records distinct warning-token hits with exact file paths/hashes. Matches inside ctrl_sc or mem_sc directories are only TEXTUAL HINTS, never automatic generated parent attribution or bit-layout proof. Cross-checks genuine D3 DMA/OCM evidence.
2. scripts/m05_12d4_readonly_bd_properties.tcl: opens the exact original file-backed XPR using Vivado 2025.2 open_project -read_only, opens the exact saved original .bd, queries original ctrl_sc NUM_SI=1/NUM_MI=6 and mem_sc NUM_SI=4/NUM_MI=1, queries the actual 23 AXI interface objects and their 25 original properties (PROTOCOL, DATA_WIDTH, ADDR_WIDTH, ID_WIDTH, AWUSER/ARUSER/WUSER/RUSER/BUSER widths, MAX_BURST_LENGTH, HAS_BURST/WSTRB/BRESP/RRESP, clock and outstanding properties), and writes actual interface-net identity. Missing properties are ABSENT rather than guessed. Original ten 256/128 widths are checked. This is READ-ONLY, no vendor generate_target, synthesis, bitstream or hardware access.
3. scripts/m05_12d4_readonly_bd_audit.py: checks exact report schema, 23 interfaces, four SmartConnect cell properties, all 11 original connection pairs, ten original width endpoints, exact original D4.1/ D3 SHA evidence and new original Vivado log success marker. Any USER/ID property disagreement remains UNRESOLVED_NEEDS_AXI_FIELD_PROOF. ONLY the exact original BD 41-1629 warning is classified DOCUMENTED_INTENTIONAL_OCM_EXCLUSION_ONLY, and only after verifying the original D3 11_dma_hp0_memory_readback.txt, 12_independent_dma_hp0_memory_audit.log and full BD VALIDATION PASS (four actual OCM exclusions). The other 63 warning occurrences remain open pending real information. This OCM exception proves no AXI payload semantics.
4. scripts/run_m05_12d4_readonly_bd_probe.sh: creates a NEW immutable timestamped D4.1b folder, hashes original XPR/BD/manifest/OCM records before and after Vivado, uses -read_only on the original project from a fresh working directory, and runs both independent audits. Original bytes changing is an error. Does not require a new HLS preflight output or expand old D3 preflight allowlist because no RTL is generated or substituted.

**Exit statuses:** 3 means genuine original endpoint report/provenance captured but AXI functional gate BLOCKED, 2 means invalid evidence / original query failed. A clean tool invocation or host-native unittest never becomes automatic SmartConnect data/response acceptance.

## SYNTHETIC independent native tests

New tests/test_m05_12d4_readonly_bd_probe.py exercises the 23-interface positive report shape, wrong/missing/duplicate properties and 256→128 endpoint drift, wrong/aliased original net pairs, mismatched AWUSER without waiver, sole intentional OCM warning with four exclusions and deliberate negative corruption, refusal of missing original input, duplicate token appearances in both control and memory generated-file hints, static vendor Tcl property-readback and no mutation contract, no-hardware Bash syntax, and refusal to accept fake Vivado proof. All host fixtures are SYNTHETIC, clearly separate from genuine original owner Vivado 2025.2 evidence.

## Owner Ubuntu/VS Code commands — one safe ORIGINAL 2025.2 offline read-only trial

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
    git rev-parse HEAD
    git status --short
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m05_12d4*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05_12d*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05*.py' -q
    python3 -m unittest discover -s tests -p 'test_m04*.py' -q
    python3 -m unittest discover -s tests -p 'test_m03*.py' -q
    python3 -m unittest discover -s tests -p 'test_m02*.py' -q
    python3 -m unittest discover -s tests -p 'test_m01*.py' -q
    bash -n scripts/run_m05_12d4_readonly_bd_probe.sh
    vivado -version

    export IP_D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export D4_OLD="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d4_warning_inventory_20261109T152119Z_jBQsxu"
    cat "$IP_D3/result.txt" "$D4_OLD/result.txt"
    bash scripts/run_m05_12d4_readonly_bd_probe.sh "$IP_D3" "$D4_OLD"
    echo "D4.1b exit=$?; 3 is accepted read-only collection but unresolved AXI semantics"

    export D4_BD="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d4_readonly_bd_* | head -n 1)"
    echo "$D4_BD"
    cat "$D4_BD/commit.txt" "$D4_BD/result.txt"
    cat "$D4_BD/01_original_hierarchy_index.log" "$D4_BD/06_independent_bd_audit.log"
    cmp "$D4_BD/source_sha256.txt" "$D4_BD/07_source_sha256_after.txt"
    head -n 80 "$D4_BD/03_bd_interface_properties.txt"
    tail -n 80 "$D4_BD/04_vivado_readonly.log"
    python3 -m json.tool "$D4_BD/06_independent_bd_audit.json" | head -n 150

Return the new original D4_BD/result.txt, 03_bd_interface_properties.txt, 04_vivado_readonly.log, 05_generated_hierarchy_hints.json, 06_independent_bd_audit.json, 06_independent_bd_audit.log, source_sha256.txt and 07_source_sha256_after.txt (or excerpts and exact original checksums). Do not replace or delete earlier trial folders, even on failure. Do not invoke board manager, JTAG, physical PS/DDR, synthesis, bitstream, or deployment.

## Remaining acceptance boundaries

**D4.1b OWNER VERIFICATION PENDING.** The generated-file token index may be insufficient to attribute internal packed payloads; if so preserve "UNATTRIBUTED" and investigate genuine vendor module hierarchy and simulator support without pretending it is proven. **D4.2 NOT RUN; NO CONFIGURATION CORRECTION AUTHORIZED BY EVIDENCE YET.** A change must be separately staged and preserve the accepted signed32 original HLS/BD, then rerun all genuine 6 control/4 DDR/OCM/10 width/BD/IP audits in new evidence. **D4.3 NOT RUN:** no vendor-generated 256→128 byte/strobe/ID/USER/burst/response/backpressure functional simulation or whole-system synthesis. **D4.4 M05 OPEN:** independent event-driven neural/M02 on-chip acceptance, known counters, PS control and timeout/quiescence gating require explicit review; mapped PS HP0 DDR_LOW is not physical DDR ownership. No M06, no PR merge.

Information references (not execution evidence): AMD UG835 2025.2 open_project -read_only / open_bd_design / get_bd_intf_nets; UG912 BD_INTF_PIN user/ID/burst property descriptions; AMD SmartConnect PG247 for possible but unproven width conversion.
