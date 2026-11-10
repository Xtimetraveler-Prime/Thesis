> **M06 G1 owner-genuine cosim PASS + G3 synthetic/owner-input tests, 2026-11-09:** New corrected Vitis 2025.2 `--cosim` archive has `exit_status=0`, genuine generated Verilog XSim 4/4 transactions + post-check `COSIM 212-1000 PASS`, source SHA unchanged; accepted M06 G1 only for the tested scenarios. New `tests/test_m06_g3_original_link_inputs.py`: 6 positive/negative SYNTHETIC_ONLY mocked external-attestation methods for real cosim required, source SHA, original A-E status, 32:256 roles; `tests/test_m06_axi32_to256_byte_oracle.py`: 7 positive/negative host-only lane/WSTRB/4KiB/last legal 65535/B→AR+error quarantine methods; `tests/test_m06_g3_exact_original_pin_matrix.py`: 5 positive/negative tests for real original 96-pin/real HLS pin-role audit and 64→32 address+ID sidebands. These are **NOT real Vivado or original AMD DUT integration**. `m06_paged_hls_axi_link_plan.py` now records original S00/S03 ADDRESS WIDTH=32 against generated HLS 64 and requires explicit upper-bit guard. Genuine G3 input verification commands/new owner JSON via [G3 runbook](M06_G3_REAL_OWNER_INPUTS_AND_EXACT_PORT_MATRIX_2026_11_09.md). Next real G3 must compile AMD width adapter + generated HLS + ORIGINAL SmartConnect in independent scratch XSim and independently M02/M03 trace, failure quarantine G4. No PR merge/board/DDR.

> **NEW 2026-11-09 M06 G1 HLS two-master alias test ledger (NO VENDOR EXECUTION):** `scripts/m06_paged_hls_alias_contract.py` has a strict source-only check that canonical read/write M_AXI are separate gmem_read/gmem_write bundles, offset=slave, equal depth=16384, identical pointer base `#pragma HLS ALIAS ports=canonical_read_words,canonical_write_words distance=0`, and no phantom RTL/board claims. `tests/test_m06_paged_hls_alias_contract.py` adds five positive/negative unittest methods: actual source contract positive, missing/duplicate/reordered/wrong-distance alias negative, wrongly merged bundle/depth/offset negative, wrong HLS top/third master negative, and CLI source preflight. These tests are SYNTHETIC source checks only; they CANNOT prove actual Vitis accepts ALIAS or real RTL coherency. CSim testbench changes only introduce precise `M06_HLS_CSIM_DIAG` on failed checks; thresholds and M02/M03/M05 parity are unchanged. The uploaded owner `--cosim` FAILURE `COSIM 212-359` occurred on PRIOR source during C testbench instrumentation, BEFORE RTL simulator vectors. [Original real evidence and new owner gates](M06_OWNER_COSIM_FAIL_AND_ALIAS_NEXT_GATE_2026_11_09.md). Prior Stage E pass remains valid at original AMD scratch scope; untested fresh Vitis cosim and HLS-to-vendor link remain open. Run `python3 -m unittest discover -s tests -p 'test_m06*.py' -v` and inspect latest six CI outcomes at changed HEAD.

> **2026-11-09 G2 original AMD Stage E real-owner result + new source-only attestation regression:** The operator's authentic original-vendor XSim excerpt shows BOTH Stage E PASS markers (highest page255, neuron4095, last byte65535, one dirty writeback, 16 M00 writes/48 reads; illegal block256 quarantine), actual XSim exit0 and A–E runner exit0. **Run-wide source SHA and owner commit still need original-folder readback.** New scripts/m06_original_stage_e_evidence_audit.py is a read-only source/commit/2025.2 simulator/XSim A–E log verifier and refuses missing original D3, modified source SHA, fabricated/duplicated markers, corrupted Stage E counts and nonzero exits. tests/test_m06_original_stage_e_evidence_audit.py adds six SYNTHETIC_ONLY positive/negative unittest methods; local isolated Python suite PASS at authoring, fresh GitHub Actions still to verify. This source audit is not a new real vendor simulator run and never asserts generated HLS IP integration or physical DDR. [Actual Stage E owner report and exact commands](M06_STAGE_E_OWNER_RESULT_AND_BINDING_HANDOFF_2026_11_09.md). G1 genuine paged HLS cosim owner results not yet supplied; G3 HLS→original AMD original SmartConnect and G4 numerical negative acceptance still OPEN.

# M06 test explanations: AXI link planning after genuine paged-HLS synthesis

**Stage:** M06 OPEN, PR #80 DRAFT. Refer to [genuine owner-synthesis review](M06_OWNER_VITIS_SYNTHESIS_READBACK_AND_OPEN_GATES_2026_11_09.md) and the [authoritative M06 handoff](M06_NEXT_CHAT_HANDOFF_2026_11_09.md). This document describes a narrow new synthetic source-only test increment; previous M06 host, Icarus, and owner original AMD A–D evidence remains separate and unchanged.

## What the new tests prove

`tests/test_m06_paged_hls_axi_link_plan.py` imports `plan` from `scripts/m06_paged_hls_axi_link_plan.py` and tests six methods:

1. **Positive mismatched widths:** a synthetic generated 32-bit read / 64-bit write pair correctly requests separate width adaptation to original 256-bit S00 READ_ONLY and S03 WRITE_ONLY; also checks 64KiB/255 legal page and required B-response fence.
2. **Positive already matching widths:** synthetic 256-bit HLS ports do not need a width adapter, but remain `WIDTH_ONLY_COMPATIBLE_NOT_CONNECTED`. Matching width never counts as an actual link.
3. **Negative false vendor/board claims:** mutate synthetic claims to connected IP, allocated memory, programmed board, completed milestone or incorrect generated status. Each must reject.
4. **Negative source provenance:** corrupted generated-top SHA256 and missing accepted M05 source identifier must reject.
5. **Negative port metadata:** corrupt read/write role, address/data width or a computed adapter flag. Each must reject instead of selecting an unsafe direct adapter.
6. **Negative CLI absent evidence:** no owner HLS evidence or JSON: exit2 and no fabricated output artifact.

**Synthetic fixture limitations:** The test metadata is invented exclusively to exercise the parser and planning logic. It is not HLS-generated Verilog, Vivado-generated IP, a converted bus transaction, or an AXI functional simulation. It never accesses a board, DDR, JTAG or a real vendor simulator.

## Genuine owner readback contract

The CLI requires both an existing genuine paged-HLS evidence directory and an independent port-audit JSON. It re-runs `m06_paged_hls_port_audit.audit()` on the original generated Verilog, checks exact JSON equality, and creates only a new unique plan JSON. Never infer actual widths from the synthetic unit test's invented 32/64/256-bit values. The real data widths are measured in the owner's independently generated audit JSON, which has not yet been supplied in this chat.

Source-only native verification:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_paged_hls_axi_link_plan.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
bash -n scripts/run_m06_paged_rolling_hls.sh
bash -n scripts/run_m06_original_mem_sc_vendor_xsim.sh
```

After pulling new source, check all six M01–M06 GitHub Actions workflows at latest HEAD, not at old `f59b12b`. Existing accepted M05 neural source was NOT changed, so the historical successful owner `--synth` experiment is preserved, not invalidated. Generated HLS C/RTL cosim and original Stage E still need *fresh* owner gates. The source-only plan must **never** mark M06 closed.
