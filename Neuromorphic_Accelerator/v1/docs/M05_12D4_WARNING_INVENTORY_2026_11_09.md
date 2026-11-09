# M05.12d.4 — D4.1 genuine SmartConnect warning provenance and remaining gates

**2026-11-09 UTC — new CODE and SYNTHETIC TESTS, no genuine owner D4 trial yet.** Branch agent/neuromorphic-accelerator-v1-m05-sparse-onchip, PR #79 draft/unmerged. Do not confuse the parser's synthetic tests with an actual vendor-IP protocol result.

## Immutable genuine input

Accepted original Vivado 2025.2 D3 output-products directory:

    ~/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ

Original source commit fc17906e95c727d9091a443e2082fe00c95d4e0c; original exit_status=0. The six real control banks, four DMA DDR_LOW mappings, four OCM exclusions, ten 256/128-bit interface endpoints, forced BD validation, vendor-generated output products (382 file hashes, 118 memory-SmartConnect), and independent original D3 audit passed. They do NOT prove that a 256-to-128-bit burst, ID, sideband, or response is correct.

The new scripts/m05_12d4_warning_inventory.py is independent and read-only on the original folder. It rechecks original source commit/result, saved XPR/BD, output width report, original generated product SHA256 manifest against all current .gen file bytes, and original vendor log. Every BD 41-* WARNING or CRITICAL WARNING occurrence is recorded with line number, exact message, severity, ID, endpoint paths, widths if parseable, AXI channel hints and unproven parent. Missing or changed originals and unknown warning IDs fail closed.

Specifically, BD 41-2384 explicit source/destination paths and width fields are parsed without inferring that the lost high bits are padding; 172→168 implies 4 possibly dropped source bits, 55→53 implies 2 and 9→7 implies 2. BD 41-237 AWUSER_WIDTH/ARUSER_WIDTH mismatch is not waived. BD 41-3281 auto-configuration and BD 41-1629 OCM-exclusion messages remain unresolved until correlated with original actual generated hierarchy and configured interface properties. AXI AW/AR/W/R/B channel hints are NOT packed-field bit offsets.

Bare internal /m00_nodes through /m05_nodes DO NOT uniquely determine whether a warning came from the six-MI control SmartConnect or the memory SmartConnect. Only an explicit /ctrl_sc/ or /mem_sc/ endpoint permits direct attribution from the warning string; all other parent identities are UNATTRIBUTED or AMBIGUOUS. The owner original-generated .gen cell hierarchy or safe read-only Vivado query may be necessary before we can distinguish meaningfully discarded data from structural packing. **No warning is classified as demonstrated benign in this revision.**

The inventory JSON records source file SHA256, warning counts by ID, every occurrence, and explicit D4.2/D4.3 NOT_RUN and AXI PROTOCOL BLOCKED. A complete inventory intentionally exits with status 3, not status 0; 2 indicates invalid evidence/input. Its runner creates a NEW timestamped immutable D4 folder, retains original logs without mutation, and records both source and original proof checksums. It invokes no Vivado, physical DDR, JTAG, FPGA, synthesis or simulation tools.

## Host-only tests (SYNTHETIC)

tests/test_m05_12d4_warning_inventory.py covers:
- test_extract_exact_two_pin_widths_narrowing_and_line_numbers: source/destination 55→53, 172→168, and widening 7→9, raw paths and AW/R/B hints.
- test_m00_m05_does_not_prove_parent_smartconnect and test_explicit_prefix_and_ambiguous_multi_parent_fail_closed: no heuristic attribution, explicit name only and mixed-parent warning blocker.
- test_unknown_code_and_critical_warning_not_suppressed and test_duplicate_warnings_remain_distinct_occurrences: no discarded warnings or duplicates.
- test_no_unreviewed_benign_whitelist_for_auto_config_and_ocm: OCM exclusions and automatic configuration require actual evidence.
- test_new_report_path_and_immutability_guards, test_cli_missing_original_must_not_emit_fake_report: no reused reports or fake original proof.
- test_runner_is_offline_readonly_and_syntax_valid: shell syntax and offline-only safety.

All warning messages in these unit tests are marked SYNTHETIC. A passing Python test cannot establish any real generated-IP hierarchy or semantics.

## Owner Ubuntu / VS Code terminal instructions

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1

    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m05_12d4*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05_12d*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05*.py' -q
    python3 -m unittest discover -s tests -p 'test_m04*.py' -q
    python3 -m unittest discover -s tests -p 'test_m03*.py' -q
    python3 -m unittest discover -s tests -p 'test_m02*.py' -q
    python3 -m unittest discover -s tests -p 'test_m01*.py' -q
    bash -n scripts/run_m05_12d4_warning_inventory.sh

    export IP_D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    cat "$IP_D3/commit.txt" "$IP_D3/result.txt"
    bash scripts/run_m05_12d4_warning_inventory.sh "$IP_D3"
    echo "D4 exit=$?; 3 means inventory created but protocol BLOCKED"
    export D4="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d4_warning_inventory_* | head -n 1)"
    echo "$D4"
    cat "$D4/commit.txt" "$D4/result.txt" "$D4/03_independent_inventory.log"
    python3 -m json.tool "$D4/02_warning_inventory.json" | head -n 120

Please return the NEW 02_warning_inventory.json, 03_independent_inventory.log, result.txt and source_sha256.txt, or the exact original warning lines plus those SHA values. Keep every original owner PASS and FAIL evidence folder intact. This native read-only run does not require a fresh Vivado execution.

## Ordered gate decisions and scientific limits

**D4.1:** parser, tests, runner and runbook SOURCE STAGED; actual original 2025.2 warning attribution report PENDING OWNER. At least the hierarchy and packed channel fields remain UNRESOLVED_BLOCKER until the real report and vendor sources are inspected. This stage is not vendor-verified complete.

**D4.2:** no configuration edits justified yet. Do not force unsupported USER widths or modify generated/vendor HLS RTL merely to quiet warnings. If genuine evidence shows meaningful field loss, derive a minimally changed evidence-local Tcl, verify original/derivative SHA, and rerun fresh real six-bank/four-DMA/OCM/10-width/full-BD/generated-IP audits. If genuinely benign, document proof per warning and negative cases, not a global waiver.

**D4.3:** actual vendor-generated 256→128 AXI-MM multi-beat read/write, WSTRB, LAST/LEN/SIZE, ID, response, simultaneous masters, backpressure, timeout/reset and invalid-operation simulation NOT RUN. Offline Vivado simulator feasibility and library support have not been established. Full integrated BD synthesis/elaboration NOT RUN. No fake memory test may substitute for real generated vendor interconnect.

**D4.4:** M05 accepted M02 oracle contracts, genuine signed32 HLS and M05.11c real generated-RTL neural/stream evidence, and D3 BD/product connectivity prove distinct limited gates. M05 roadmap acceptance still requires independently checked on-chip event-driven behavior and known counters without a DDR virtual-paging dependency. Integrated scheduler and PS control transaction, timeout/fault/quiescence evidence must be separately reviewed. D3's 2GiB mapped bus aperture is not physical DDR ownership. M05 remains OPEN; M06 NOT STARTED; PR #79 DRAFT/UNMERGED. No board, JTAG, DDR transfer or merge authorization.
