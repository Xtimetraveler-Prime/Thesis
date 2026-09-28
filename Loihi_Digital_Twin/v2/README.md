# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the new source-backed Loihi-1 architectural digital twin.

Development begins with `docs/LOIHI1_TARGET_SPEC.md`. The specification is the normative contract for the separate v2 Python golden model, mapping/compiler layer, and later FPGA implementation. FPGA-v1 remains frozen under `../v1/`.

No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts and cites them.
