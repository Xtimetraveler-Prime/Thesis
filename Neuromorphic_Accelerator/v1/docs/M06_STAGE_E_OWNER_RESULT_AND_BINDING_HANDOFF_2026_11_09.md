# M06 owner Stage E genuine XSim result; remaining generated-HLS binding gates

2026-11-09 America/Denver. M06 remains OPEN. PR #80 DRAFT / UNMERGED.

## Actual owner report and interpretation

Original vendor evidence directory: ~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2

The operator provided an excerpt from actual original AMD SmartConnect Stage E:
- M06_ORIGINAL_VENDOR_4096_RANGE_PASS highest_page=255 last_neuron=4095 last_byte=65535 dirty_wb=1 M00_write=16 M00_read=48
- M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS block256_rejected=1 no_physical_DDR=1
- Genuine XSim $finish at 8970 ns, exit 0.
- Full A-E runner reported PASS and exit 0; output explicitly says original M05 HLS RTL NOT INSTANTIATED, NO DDR/BOARD.

**Conclusion:** Stage E functional PASS at original vendor RTL/simulated 64KiB scratch-memory scope, but run-wide SHA/commit provenance still requires the ORIGINAL evidence files. This is not generated HLS-to-AMD SmartConnect integration or real DDR.

## New independent evidence attester

scripts/m06_original_stage_e_evidence_audit.py rechecks the immutable existing owner folder read-only: result, Git commit format, before/after SHA manifest equality, **live original D3 source digest readback**, installed Vivado glbl.v, original compile/elaboration 2025.2 and five XSim PASS/clean exits; exact high-page byte/counts, quarantined illegal page and generated testbench dimensions. It writes a fresh new audit JSON; it never marks M06 complete or claims board/DDRx correctness.

Six synthetic-only tests in tests/test_m06_original_stage_e_evidence_audit.py cover correct reporting, missing/duplicated markers, wrong 2025.2, corrupted counts, failures after PASS, missing provenance, modified original sources, invalid bench. The tests are NOT vendor execution. If genuine output unexpectedly fails the audit, retain raw logs and troubleshoot the first actual discrepancy. Do not modify or overwrite older evidence.

Owner local commands after pulling latest M06 branch:

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    python3 -m unittest discover -s tests -p 'test_m06_original_stage_e_evidence_audit.py' -v
    export E="$HOME/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2"
    cat "$E/result.txt" "$E/commit.txt"
    cmp "$E/sha_before.txt" "$E/sha_after.txt" && echo ORIGINAL_VENDOR_SHA_MATCH
    python3 scripts/m06_original_stage_e_evidence_audit.py --evidence "$E" --output "$HOME/Thesis_Evidence/m06_stage_e_attested_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

## Files needed next: ONLY original text evidence, not proprietary IP

Original Stage E directory: result.txt, commit.txt, sha_before.txt, sha_after.txt, original_directory.txt, installed_vivado_glbl_sha256.txt, 03_xvlog.log, 12_4096_xelab.log, 13_4096_xsim.log, 05_xsim.log, 07_paged_xsim.log, 09_neural_paged_xsim.log, 11_lru8_xsim.log, and generated owner testbench tb_m06_original_vendor_4096.sv. Prefer new independent attestation JSON too.

Original HLS --cosim directory (m06_paged_rolling_hls_cosim_*): result.txt, commit.txt, source_before_sha256.txt, source_after_sha256.txt, 01_csim.log, 02_csynth.log, 03_cosim.log if created, and report_paths.txt. Preserve failed runs and original files.

Original HLS --synth directory (m06_paged_rolling_hls_synth_20261110T010713Z_s1mUED): report_paths.txt and generated *_csynth.rpt plus previously produced m06_paged_hls_ports_*.json, containing independently **measured** data widths and RTL top hash. Never assume bus width from HLS pointer word size.

## Remaining M06 acceptance work

G1: Original generated-HLS C/RTL cosim gate: operator already ran according to current user statement, results not supplied. Diagnose real tool result before changing source.

G2: Original AMD SmartConnect Stage E: functional PASS excerpt, run-wide source/version/commit evidence pending attestation.

G3: Integrate real generated HLS read master with original S00 READ_ONLY, and generated HLS write with original S03 WRITE_ONLY (both original S ports 256-bit, original M00 128-bit); use converters if ACTUAL generated widths require them. Both masters must map to one 64KiB offline scratch memory; prove AR/R, AW/W/B, 4KiB burst/byte lanes and correct read-after-dirty-write completion across masters with stalls, responses and errors. No claim of integration until original vendor simulator runs it.

G4: End-to-end M02/M03 independent trace plus canonical 16-byte memory image with forced 1/8-slot dirty eviction/restoration, negative timeout/error/quarantine and no speculative trace publish. The HLS pointer API doesn't expose failed BRESP/RRESP to C++; need tested RTL supervision or explicit system-level failure contract. Current six workflows and original SHA provenance, then owner decides closeout scope.

No physical JTAG/DDR/programming, no PR merge or M07 without authorization.
