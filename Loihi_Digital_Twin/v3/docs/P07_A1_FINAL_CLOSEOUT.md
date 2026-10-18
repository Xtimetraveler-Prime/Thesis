# P07-A1 — 784-axon input/transfer contract: native acceptance

**Status:** COMPLETE / USER-ACCEPTED, 2026-10-17.
**Branch:** `agent/v3-p07-a-784-axon-streaming`.
**Scope:** versioned P07 image/axon transport, independent Python/C11
validation, 26-tick deterministic input encoding, trained model/DDR
provenance binding, host tests. **No FPGA inference, no Vitis/XSDB
execution, and no official MNIST TEST accuracy is claimed.**

## User-supplied native evidence

The user explicitly states: **"P07-A1 passed verification on my machine."**
The user ran the 512 KiB existing artifact's `sha256sum`, then
`scripts/p07_a1_ingress.py --synthetic ramp` and a strict C11 build and
native probe against the emitted record, reporting these exact markers:

- `P07_A1_DDR_SHA256=9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`
- `P07_A1_COMPILED_FINGERPRINT=e612a971cda11fae3f1be215c0ca3ed7de7b2af7339446e926ce559658db2f7f`
- `P07_A1_INGRESS_SHA256=53c7fb5c99046aa6417fb56400c06c00b68525486a412e1f2e9ceadf539`
- `P07_A1_INPUT_EVENTS=9230`
- `P07_A1_26_TICKS=25_INPUT_PLUS_1_DRAIN`
- `P07_A1_HOST_RECORD_PASS=1`
- `P07_A1_KV260_STATUS=NOT_RUN`
- `P07_A1_C_NATIVE_PASS=1`

User-supplied C output contains 26 ordered tick rows (0–25). The
drain tick (25) has count 0 and FNV64 `cbf29ce484222325`, the empty
stream checksum. The first tick had 370 external events and FNV64
`5d708bd93035b75b`; exactly 9,230 events across input ticks 0–24.

The user explicitly accepted P07-A1; the full local pytest stdout was
not pasted in the handoff, so the native test *count* is not fabricated.
GitHub Actions verified the Python encoder, portable C11 probe,
negative parsing cases and frozen P05 ABI regressions; this is CI
host validation rather than independent physical proof.

## Frozen physical deployment provenance

The P06-A4.2 **existing** `artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin`
file was hashed in place (not regenerated), producing the full-file
SHA-256 above. The frozen effective integer tensor SHA-256 is
`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`.
These are separate identities and MUST NOT be interchanged.
The P07 deployment uses explicit compiler ingress (pixel IDs are not
automatically destination axon IDs).

## Next gate: P07-A2

Develop autonomous Cortex-A53 runtime, full per-image reset, immutable
initial DDR re-seed, 26-tick PS/PL dispatch with correct NEXT routing,
and exact class-specific trace/spike readout. Preserve accepted P03/P05
goldens. New host-native C tests and Vitis build/board execution require
their own evidence. Sealed official TEST remains untouched. Do not
merge this branch without explicit user permission.
