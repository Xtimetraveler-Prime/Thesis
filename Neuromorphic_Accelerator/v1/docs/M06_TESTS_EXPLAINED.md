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
