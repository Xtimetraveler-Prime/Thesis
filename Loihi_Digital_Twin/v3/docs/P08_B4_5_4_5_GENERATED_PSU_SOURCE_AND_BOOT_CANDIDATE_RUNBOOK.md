# P08-B4.5.4.5 — generated PS protection call graph and boot-source inventory

**Status: SOURCE IMPLEMENTED; OPERATOR FILE VERIFICATION PENDING.**
This procedure is **PC-only**. Never use XSDB, JTAG, PL MMIO, XMPU
writes, BOOT.BIN rewriting, FSBL compiler flag changes, or actual
MNIST TEST. Existing original B4.5 A53 guard intentionally fails
closed and remains unmodified. All originals are read-only.

## What is established, and what is not

The accepted operator B4.5.4.4 source report is:
`/home/dna/Thesis_Evidence/p08_b4544_fsbl_protection_branch_20261105T062334Z.json`
SHA-256:
`e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9`.

Original P03 routed XSA SHA-256:
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
Original matching generated `psu_init.c` SHA-256:
`049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.

The analyzer verifies original XSA root `psu_init.c`, `psu_init.h`,
and `psu_init.tcl` **byte-for-byte** against operator-supplied copies,
with SHA, size, archive, and no-overwrite guards. It enumerates HWH
descriptor symbols, root `psu_protection()` and
`psu_protection_lock()` C dependencies, unresolved macros/external
functions, candidate register call sites and obvious **literal**
DDR-XMPU port addresses. It does **not** execute the C preprocessor,
resolve generated Tcl tables to verified hardware values, or prove
region-slot priority, mask, master IDs, permissions or boot ownership.
A report containing zero literal register sites does **not** show no
XMPU configuration: such writes may be generated indirectly.

AMD/Xilinx 2025.2 FSBL default is bypass unless
`FSBL_PROT_BYPASS_EXCLUDE` is compiled; no compiled effective
configuration or active BOOT.BIN has been independently proven.
The original protected backing needs 13.5 MiB
`[0x43000000,0x43D80000)`, with conservative 14 MiB XMPU cover
`[0x43000000,0x43E00000)` that includes 512 KiB unknown ownership.
No new protection can safely be enabled by this analysis.

Vendor sources: [AMD 2025.2 FSBL header](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h),
[AMD 2025.2 FSBL handoff](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c),
[AMD UG1085 DDR XMPU region and master-ID details](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Regions).
Security features are AMD mechanisms; this thesis adds bounded audit
and Loihi digital-twin memory-state verification, not a new XMPU IP.

## 1. Fresh VS Code Linux terminal: exact source exports

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b4545-generated-psu-audit
git pull --ff-only origin agent/v3-p08-b4545-generated-psu-audit
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

export P08_B4545_PRIOR="$HOME/Thesis_Evidence/p08_b4544_fsbl_protection_branch_20261105T062334Z.json"
export P08_B4545_BUILD="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z"
export P08_B4545_PSU_DIR="$P08_B4545_BUILD/project/loihi_twin_v3_p03_mmio_impl.gen/sources_1/bd/loihi_twin_v3_p03_mmio_impl/ip/loihi_twin_v3_p03_mmio_impl_zynq_ultra_ps_e_0_0"
export P08_B4545_XSA="$P08_B4545_BUILD/reports/p03_2_ps_mmio.xsa"
export P08_B4545_C="$P08_B4545_PSU_DIR/psu_init.c"
export P08_B4545_H="$P08_B4545_PSU_DIR/psu_init.h"
export P08_B4545_TCL="$P08_B4545_PSU_DIR/psu_init.tcl"
export P08_B4545_OUT="$HOME/Thesis_Evidence/p08_b4545_psu_source_$(date -u +%Y%m%dT%H%M%SZ).json"
```

If the exact original generated header or Tcl file is elsewhere, **find
the actual file and explicitly reset its export**; do not substitute
the newer project's generated output. Compare against exact XSA root
members before assuming files are equivalent.

```bash
find "$P08_B4545_BUILD" -type f \( -name psu_init.c -o -name psu_init.h -o -name psu_init.tcl -o -name '*.hwh' \) -print
find "$P08_B4545_BUILD" -type f -name p03_2_ps_mmio.xsa -print
find "$HOME/Thesis_Evidence" -type f -name 'p08_b4544_fsbl_protection_branch_*.json' -print
test -s "$P08_B4545_PRIOR" &&
test -s "$P08_B4545_XSA" &&
test -s "$P08_B4545_C" &&
test -s "$P08_B4545_H" &&
test -s "$P08_B4545_TCL" &&
test ! -e "$P08_B4545_OUT" &&
echo P08_B4545_ORIGINAL_HOST_INPUTS_PRESENT=1

sha256sum "$P08_B4545_PRIOR" "$P08_B4545_XSA" "$P08_B4545_C" "$P08_B4545_H" "$P08_B4545_TCL"
```

First three expected hashes in order: accepted B4.5.4.4 report
`e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9`,
original XSA
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`,
original C
`049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.
The header and Tcl exact digests are established from the original XSA
by this stage, **not guessed in advance**.

## 2. Run purely host-native tests and original source scanner

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b4545_generated_psu_graph.py
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b4544_fsbl_protection_path.py \
  tests/test_p08_b4543_fsbl_boot_source_inventory.py \
  tests/test_p08_b4542_xmpu_boot_policy.py \
  tests/test_p08_b454_ddr_owner_preflight.py
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m compileall -q \
  scripts/p08_b4545_generated_psu_graph.py \
  tests/test_p08_b4545_generated_psu_graph.py

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b4545_generated_psu_graph.py \
  --prior-report "$P08_B4545_PRIOR" \
  --xsa "$P08_B4545_XSA" \
  --psu-init "$P08_B4545_C" \
  --psu-header "$P08_B4545_H" \
  --psu-tcl "$P08_B4545_TCL" \
  --out "$P08_B4545_OUT"

sha256sum "$P08_B4545_OUT"
python3 -m json.tool "$P08_B4545_OUT"
```

Expected terminal markers on actual source acceptance:
`P08_B4545_ORIGINAL_XSA_C_H_TCL_BYTE_IDENTITY_PASS=1`,
`P08_B4545_GENERATED_PROTECTION_SOURCE_GRAPH_RECORDED=1`,
`P08_B4545_ACTIVE_BOOT_PROVEN=0`,
`P08_B4545_XMPU_DDR_OWNERSHIP_OR_MASTER_IDS_PROVEN=0`,
`P08_B4545_BOARD_JTAG_DDR_BOOT_WRITES_AUTHORIZED=0`.

## 3. Optional read-only existing boot artifact **candidate** inventory

This is *not necessary* for source analysis and **must not** use the
live board or its boot media. Identify local previously existing
candidate paths with read-only `find` first; do not assume the result
is active or verified. Choose at most 12 individual original files,
and pass them individually with repeated `--artifact` options. They
are only SHA256/size inventoried, not executed or rebuilt.

```bash
find "$HOME/Git/Thesis" "$HOME/Vivado/2025.2" -type f \
  \( -iname 'BOOT.BIN' -o -name '*.bif' -o -iname '*fsbl*.elf' \
     -o -name 'compile_commands.json' -o -name '*.map' \) \
  -print 2>/dev/null
# Example ONLY after identifying an authentic existing PC file:
# export P08_B4545_LOCAL_BIF="/absolute/original/path/boot.bif"
# export P08_B4545_OUT="$HOME/Thesis_Evidence/p08_b4545_psu_optional_$(date -u +%Y%m%dT%H%M%SZ).json"
# test -f "$P08_B4545_LOCAL_BIF" && test ! -e "$P08_B4545_OUT"
# PYTHONPATH="$PWD/scripts:$PWD/src" python3 scripts/p08_b4545_generated_psu_graph.py \
#   --prior-report "$P08_B4545_PRIOR" --xsa "$P08_B4545_XSA" \
#   --psu-init "$P08_B4545_C" --psu-header "$P08_B4545_H" \
#   --psu-tcl "$P08_B4545_TCL" --artifact "$P08_B4545_LOCAL_BIF" \
#   --out "$P08_B4545_OUT"
```

A found ELF, BIF, map, BOOT.BIN or compiler flag file **never**
demonstrates which image is running on KV260. No write-oriented
commands or board readbacks are included.

## 4. Acceptance boundary and later organization

Ask for operator-local test output, terminal markers, original
JSON report path and its SHA256 before declaring B4.5.4.5 accepted.
Even with source PASS, the effective per-port region/ID/priority/mask
policy, 512KiB extra-region owner, active BOOT.BIN provenance,
staged authenticated P02 records, secure FSBL compile branch,
A53 continuing guard and recovery procedure remain **NO-GO**.

After closing this existing nested B4.5 family, use **one
milestone at 4.x per major deliverable** instead of creating ever
deeper 4.5.4.6/4.5.4.7 tasks. Keep individual acceptance checks in
the milestone description or the PR, not as numbering levels.
Do not merge this draft PR or any ancestor without explicit approval.
