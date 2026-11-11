# M08.2b — Owner-original K26 post-route implementation review

**Decision, 2026-11-11: Native KV260 synthesis, routing, timing and design-resource evidence ACCEPTED within its offline, PS-only, no-bitstream scope, with ONE documented post-route DRC warning (RTSTAT-10).** The warning is not erased or a clean DRC signoff. A later checkpoint-based bitstream release will recheck the warning and fail on any change. This is one consolidated **M08.2b implementation/deployment** effort, not a new micro-milestone for each verification step.

## Genuine original route and evidence

Owner-original evidence directory, preserved outside Git:
`/home/dna/Thesis_Evidence/M08/m08_2b_4_route_20261111T174620Z_9FLCz7`.

Owner provided original `01_vivado_impl.log`, `04_implementation_metrics.txt`, `05_timing_summary_post_route.rpt`, `06_utilization_post_route.rpt`, `07_drc_post_route.rpt`, `08_methodology_post_route.rpt`, `09_clock_utilization_post_route.rpt`, `11_m08_route_independent_audit.json`, `12_evidence_sha256.txt`. These nine uploaded original files were independently SHA256-checked against the owner's original receipt, and **all nine matched**. Owner's original JSON independently audited another three originals not separately uploaded: `02_vivado_page_bd_readback.txt`, `03_page_bd_export.tcl` and the native `10_m08_page_post_route.dcp`. Original `result.txt` and before/after source manifests were not attached in this turn; the owner-hosted independent audit reports their consistency. **Do not claim an off-machine hash check of unuploaded DCP or original source manifests.** Existing original owner evidence must never be edited/deleted or committed into Git.

Original native source evidence says:
- Vivado v2025.2 on **xck26-sfvc784-2LV-c**, KV260 SOM board preset, original PS FPD HPM0→two AXI-Lite slaves, actual 99,999,001 Hz PL0 clock. Both standalone PS address spaces 4 KiB: read-only identity **0xA0000000**, safe page **0xA0001000**.
- The original log reported **`synth_design Complete!` and `route_design Complete!`**, each 100% progress; full routed DCP persisted. The source-controlled PS-only page has **`ENABLE_COMPUTE=0`**. No neural engine, HLS, DMA, Linux MMIO, PS DDR or board programming was used.
- **WNS +5.469 ns; TNS 0.000 ns; WHS +0.015 ns; THS 0.000 ns**; **0 failing endpoints of 4515** each setup/hold. Minimum pulse-width slack **+3.500 ns** with 0 failing endpoints (1748 total); the report states all user timing constraints met.
- Original `check_timing`: **no_clock=0; unconstrained_internal_endpoints=0; no_input_delay=0; no_output_delay=0; multiple_clock=0; generated_clocks=0; timing loops=0**. The unconstrained path table is empty. The actual native report has a nonempty constrained PS clock domain; the audit clock count is **2**.
- **1,957 CLB LUTs (1.67%), 1,665 registers (0.71%), 82 LUTs used as memory, 0 BRAM, 0 URAM, 0 DSP**, 1 PS global clock buffer. No black boxes were reported in utilization. These are **PS-connected interface costs**, not full M06 neural-engine inference resources.
- The genuine native *methodology* report: **0 findings**.
- The genuine native *DRC*: exactly **1 warning, RTSTAT-10: No routable loads**, counting **15** internal SmartConnect `ctrl_sc/inst/*/mi_handler_m_sc_areset_pipe` reset-pipeline nets. The human-readable detail lists **14** names despite its stated count of 15; do not invent the omitted name. This is an internal interconnect diagnostic, not a listed bad physical I/O pin, page-storage path or failed timing endpoint. It is **not a DRC-clean claim**. The release gate only permits this precise rule/severity/origin and requires owner acknowledgement, while also re-running Vivado `report_drc` from the routed DCP. Any new DRC issue blocks release.
- The source-generated SmartConnect warning `[BD 41-2384]` about different internal payload widths appears in the original implementation vendor log (two sets); it is an AMD SmartConnect generated-IP/internal interconnect warning, not an accepted external 32-bit S_AXI mismatch. It was nonfatal in this native implementation. Exact warning inventory is not deleted.
- Original `11_m08_route_independent_audit.json` status: `ORIGINAL_OWNER_M08_KV260_ROUTE_EVIDENCE_CONSISTENT_DRC_REVIEW_REQUIRED`; SHA of original native route DCP **`516ded0b2b19352952810b8f2a82f15b9eca02b4757cf53c187d179d051c8673`**, per owner receipt (local file bytes not uploaded). This status is *not* a bitstream or real-board acceptance.

### Independently verified uploaded artifact SHA256

| Uploaded source file | SHA256 from original owner receipt, independently checked |
| --- | --- |
| `01_vivado_impl.log` | `95a9eeecfd97aafbf4f8292e99aa7c5839fa7083caa48fb97f7841a5d4b362ef` |
| `04_implementation_metrics.txt` | `572740a5dc589cb5330f708347b8c9a303d947ce3645bdc5ae443bc8e362f9d8` |
| `05_timing_summary_post_route.rpt` | `b985fd46fba2f3eb2134f49a32b3c20522edc8fc0082792dfbc7590c92cd920d` |
| `06_utilization_post_route.rpt` | `6092f2cd0c72e88281af0a2b843dba6d6518dca4d956b0c29a3d4d519174c831` |
| `07_drc_post_route.rpt` | `8339b38d770061dd2aabc3fc484313e040a08ec29e6d0125858520fcdf849427` |
| `08_methodology_post_route.rpt` | `bf7e21397b40bfb35bee9717c9c2ffd7d8209e058004d3b0f8ed9b7d3c37ba26` |
| `09_clock_utilization_post_route.rpt` | `810299fa7f7cd6aeac12ad6cbd1fcc14c1bd00a102171d8535ceff9d7b3b03b4f9` |
| `11_m08_route_independent_audit.json` | `fba76abe0abe7da3a8c8a9288f3301df96133b9f7bc43a25e15b8303bd0fb7a0` |
| `12_evidence_sha256.txt` | Original receipt provided and independently parsed (not itself a row in that receipt) |

**Scope boundary:** Routing + timing are accepted as owner-original report evidence with one explicitly inventoried DRC warning. This does not certify application-level memory parity, Linux driver/FPGA address reachability, DDR ownership, autonomous neurons, or signed16 inference. A bitstream generated in a later owner run will be for a *safe PS-controlled state page*, not a complete deployed neural accelerator.

## Consolidated next action

Do **not** create additional standalone numbered micro-milestones. Continue **M08.2b: implemented PS state-page deployment** in one coherent sequence: source-level checkpoint/DRC/timing/receipt checks → new offline PL bitstream built from the **original immutable route DCP** → controlled, operator-approved K26 physical programming only after confirming the board's live boot/platform ownership and safe access path → PS-to-PL identity and 256-byte page readback parity. Full signed16 M06 neural execution and DDR DMA remain later architectural integration, never inferred from this PS-only gate. [Consolidated source-to-board runbook](M08_2B_BITSTREAM_AND_BOARD_HANDOFF_2026_11_11.md).
