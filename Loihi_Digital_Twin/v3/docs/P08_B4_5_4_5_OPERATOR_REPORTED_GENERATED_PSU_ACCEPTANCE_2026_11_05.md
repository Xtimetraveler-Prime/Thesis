# P08-B4.5.4.5 — operator-reported original source audit acceptance

**Evidence level: operator-reported PC-only source audit PASS; physical
boot, DDR ownership and XMPU permission NO-GO.**

On 2026-11-05 UTC the operator posted the terminal report and pretty
JSON contents from the actual original P03 generated sources. Original
external file:
`/home/dna/Thesis_Evidence/p08_b4545_psu_source_20261105T065516Z.json`.
Operator's `sha256sum`:
`2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0`.

The following exact terminal assertions were posted:
```text
P08_B4545_ORIGINAL_XSA_C_H_TCL_BYTE_IDENTITY_PASS=1
P08_B4545_GENERATED_PROTECTION_SOURCE_GRAPH_RECORDED=1
P08_B4545_ACTIVE_BOOT_PROVEN=0
P08_B4545_XMPU_DDR_OWNERSHIP_OR_MASTER_IDS_PROVEN=0
P08_B4545_BOARD_JTAG_DDR_BOOT_WRITES_AUTHORIZED=0
```

The report gives:
- Frozen original P03 XSA `52aea12b...93af6f` and C
  `049ae8a0...22b8679`; newly inventoried C header
  `ff2edf0c2a7d54ca5d43b6d45de3a06eb97ed44575dcda860c3e5f795c162a11`
  and Tcl
  `4a6ce994e65170e54a123f963e52aae05f8671d2fba6ea51e657acfedccf2cbe`.
- 43 source C function definitions; full root
  `psu_protection` reaches six DDR-XMPU helper names, as well as
  FPD, LPD/OCM, `psu_apply_master_tz` and `PSU_Mask_Write`.
- All six generated C `psu_ddr_xmpu[0-5]_data` functions have
  21-byte source bodies and **zero named calls** as reported.
  `psu_protection_lock_data` has an 87-byte body and zero
  named calls in this particular heuristic report.
- Only one reachable C register call-site heuristic was found:
  `Xil_Out32(offset, RegVal)` inside `PSU_Mask_Write`.
  No *literal* DDR-XMPU address was directly discovered;
  this is **not proof** that no register can be written.
- The Tcl file contains XMPU symbols, but is separately
  generated for debugger use, not automatic cold-boot FSBL execution.
- No existing boot artifact candidate was supplied in the JSON.
  Active BOOT.BIN, compiled FSBL branch, all six DDR-XMPU
  effective permissions, master IDs, 13.5MiB immutable backup
  owner, extra 512KiB owner and trusted A53 guard are **unproven**.

**Evidence distinction:** This document records the operator's
posted original-command output and SHA. The full original binary
JSON and actual local generated PS sources are not attached to GitHub
and have not been independently re-hashed by the assistant. The
user's paste did not include a local pytest transcript, although
the B4.5.4.5 native GitHub Actions regression had passed
beforehand. This acceptance is strictly for the source-report
deliverable; no new physical inference, boot image, protection or
DDR master ownership is claimed or authorized.

**Next:** P08-B4.5 FSBL C-vs-XSDB Tcl source channel split and
host-existing BOOT.BIN/BIF/FSBL provenance inventory, under a
new separate draft PR stacked on B4.5.4.5. No deeply nested
B4.5.4.6 numbering. Source-only no-board checks first, followed
by independent operator source audit before any request for
separately approved read-only physical state inspection.
