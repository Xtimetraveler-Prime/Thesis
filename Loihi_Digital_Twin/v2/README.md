# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the new source-backed Loihi-1 architectural digital twin.

The active development plan is `LOIHI_TWIN_ROADMAP.md`. Future work on FPGA-v2 should update that roadmap as objectives, research gates, and implementation stages are completed or revised.

The normative architecture contract is `docs/LOIHI1_TARGET_SPEC.md`. Development begins from that specification and proceeds into a separate v2 Python golden model, mapping/compiler layer, and later FPGA implementation. FPGA-v1 remains frozen under `../v1/`.

No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts and cites them.
