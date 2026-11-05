# P08-B4.5 — FSBL C vs XSDB Tcl source-channel and boot readiness

**Scope: PC-ONLY source audit and optional existing-file inventory.**
This step moves toward *planning* a safe immutable DDR backup mechanism,
not physical permission or a working FSBL/backup guard. No actual boot,
Vitis build, bitstream, FSBL rebuild, XSDB/JTAG, PL/DDRx register read
or write, network/board action, or official MNIST TEST.

## 1. Accepted operator-reported source input

The user reported the completed P08-B4.5.4.5 original-source check,
with accepted P03 generated XSA/C/H/Tcl byte identity and call-graph
recorded. The **user-reported** report:
`/home/dna/Thesis_Evidence/p08_b4545_psu_source_20261105T065516Z.json`
SHA-256:
`2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0`.

Its JSON states:
`GENERATED_PSU_SOURCE_GRAPH_ONLY_ACTIVE_BOOT_AND_XMPU_NO_GO`,
all six `psu_ddr_xmpu{0:5}_data` functions found (21 source-body
bytes each), `psu_protection_lock_data` found (87 source-body bytes),
zero *direct literal* DDR-XMPU register sites, and the only obvious
reachable C `Xil_Out32` call was in `PSU_Mask_Write` via a
non-literal `offset` argument. The generated Tcl has XMPU symbols
but its `psu_protection_data` symbol count was zero. These
observations **do not** prove XMPU is not configured: the previous
scanner was deliberately source-limited, not a C preprocessor,
real compiler/linker, Tcl interpreter or live register readback.

The report was supplied as text and SHA output; the original JSON and
local generated source bytes were not uploaded. Operator-local pytest
output was not included; the inherited GitHub host-only CI previously
passed. The next operator run must independently rehash the actual
unchanged local files and produce a fresh result.

The original P03 XSA SHA is
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
Generated C SHA is
`049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.
Header SHA:
`ff2edf0c2a7d54ca5d43b6d45de3a06eb97ed44575dcda860c3e5f795c162a11`.
Tcl SHA:
`4a6ce994e65170e54a123f963e52aae05f8671d2fba6ea51e657acfedccf2cbe`.

## 2. Technical source distinction, not board evidence

AMD PG201 describes `psu_init.c` as generated PS initialization
source used by the **FSBL**, and `psu_init.tcl` as initialization
procedures used by the **XSDB/debugger** flow. The presence of a
protection write in Tcl does **not** imply it was executed during
ordinary cold boot. The tagged 2025.2 FSBL header also defines
`XFSBL_PROT_BYPASS` by default unless
`FSBL_PROT_BYPASS_EXCLUDE` was supplied at compile time.
The active KV260 FSBL/compile flags remain unknown.

AMD UG1085 documents DDR-XMPU ports 0–5 register bases
`0xFD000000`, `0xFD010000`, `0xFD020000`, `0xFD030000`,
`0xFD040000`, `0xFD050000`.
The new checker rereads the **original actual C and Tcl bytes**,
reconstructs the accepted C call graph, enumerates C helper calls and
obvious writes, and records only whether Tcl references each symbol.
It does **not** execute Tcl or claim full register/region/ID/mask
decoding. Any `XMPU0` Tcl block or source-level C return status
is not a hardware protection readback.

Vendor attribution:
- [AMD PG201 PS output files](https://docs.amd.com/r/en-US/pg201-zynq-ultrascale-plus-processing-system/Output-Generation).
- [AMD UG1085 protection unit locations](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances).
- [AMD UG1085 XMPU register layout](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Register-Set-Overview).
- [AMD/Xilinx FSBL 2025.2 default protection bypass](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h).

## 3. Complete VS Code/Linux PC verification commands

Use a **new terminal**, original frozen files and a new no-overwrite
report path in `$HOME/Thesis_Evidence`. Do not modify the original
P03 XSA/generated source or existing accepted operator JSON.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-physical-readiness-source-gate
git pull --ff-only origin agent/v3-p08-b45-physical-readiness-source-gate
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

export P08_B45_PRIOR="$HOME/Thesis_Evidence/p08_b4545_psu_source_20261105T065516Z.json"
export P08_B45_BUILD="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z"
export P08_B45_DIR="$P08_B45_BUILD/project/loihi_twin_v3_p03_mmio_impl.gen/sources_1/bd/loihi_twin_v3_p03_mmio_impl/ip/loihi_twin_v3_p03_mmio_impl_zynq_ultra_ps_e_0_0"
export P08_B45_XSA="$P08_B45_BUILD/reports/p03_2_ps_mmio.xsa"
export P08_B45_C="$P08_B45_DIR/psu_init.c"
export P08_B45_H="$P08_B45_DIR/psu_init.h"
export P08_B45_TCL="$P08_B45_DIR/psu_init.tcl"
export P08_B45_OUT="$HOME/Thesis_Evidence/p08_b45_fsbl_c_tcl_$(date -u +%Y%m%dT%H%M%SZ).json"
```

If any original generated file moved, use these **read-only**
finds, confirm it is the original P03 revision, and explicitly
re-export the actual matching absolute path. Do not choose a
different project's generated PSU file.

```bash
find "$P08_B45_BUILD" -type f \( -name psu_init.c -o -name psu_init.h \
  -o -name psu_init.tcl -o -name p03_2_ps_mmio.xsa \) -print
find "$HOME/Thesis_Evidence" -type f \
  -name 'p08_b4545_psu_source_*.json' -print

test -s "$P08_B45_PRIOR" &&
test -s "$P08_B45_XSA" &&
test -s "$P08_B45_C" &&
test -s "$P08_B45_H" &&
test -s "$P08_B45_TCL" &&
test ! -e "$P08_B45_OUT" &&
echo P08_B45_REQUIRED_FILES_PRESENT=1

sha256sum "$P08_B45_PRIOR" "$P08_B45_XSA" \
  "$P08_B45_C" "$P08_B45_H" "$P08_B45_TCL"
```

Expected SHA in order:
```text
2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0
52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679
ff2edf0c2a7d54ca5d43b6d45de3a06eb97ed44575dcda860c3e5f795c162a11
4a6ce994e65170e54a123f963e52aae05f8671d2fba6ea51e657acfedccf2cbe
```

Run new negative tests then inherited tests:

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b45_fsbl_source_channel_gate.py

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b4545_generated_psu_graph.py \
  tests/test_p08_b4544_fsbl_protection_path.py \
  tests/test_p08_b4543_fsbl_boot_source_inventory.py \
  tests/test_p08_b4542_xmpu_boot_policy.py \
  tests/test_p08_b454_ddr_owner_preflight.py

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m compileall -q \
  scripts/p08_b45_fsbl_source_channel_gate.py \
  tests/test_p08_b45_fsbl_source_channel_gate.py
```

Analyze the original files without running any PS initialization:

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b45_fsbl_source_channel_gate.py \
  --original-report "$P08_B45_PRIOR" \
  --original-xsa "$P08_B45_XSA" \
  --psu-c "$P08_B45_C" \
  --psu-h "$P08_B45_H" \
  --psu-tcl "$P08_B45_TCL" \
  --out "$P08_B45_OUT"

sha256sum "$P08_B45_OUT"
python3 -m json.tool "$P08_B45_OUT"
```

Expected markers if the original-byte check succeeds:
```text
P08_B45_ORIGINAL_C_H_TCL_AND_PREVIOUS_REPORT_MATCH=1
P08_B45_FSBL_C_VS_XSDB_TCL_CHANNELS_INVENTORIED=1
P08_B45_GENERATED_C_DDR_PORTS_RECONCILED=6
P08_B45_ACTIVE_BOOT_FSBL_PROTECTION_PROVEN=0
P08_B45_BOARD_OR_BOOT_MEDIA_WRITES_AUTHORIZED=0
```

## 4. Optional existing-file BOOT.BIN/BIF/FSBL compile candidate audit

The prior report listed **zero optional boot artifacts**. Finding
pre-existing files on the **host PC only** helps identify what needs
a later authenticated boot provenance study; it does NOT establish
which FSBL is currently running. Do not touch live boot media, copy
boot partitions, reboot or use XSDB/JTAG under this milestone.

```bash
find "$HOME/Git/Thesis" "$HOME/Vivado/2025.2" -type f \
 \( -iname 'BOOT.BIN' -o -name '*.bif' -o -iname '*fsbl*.elf' \
    -o -name 'compile_commands.json' -o -name '*.rsp' -o -name '*.map' \) \
 -print 2>/dev/null

# OPTIONAL ONLY: set the actual absolute existing local path first.
# export P08_B45_BOOT_BIF="/absolute/existing/host/path/boot.bif"
# export P08_B45_OUT="$HOME/Thesis_Evidence/p08_b45_boot_candidate_$(date -u +%Y%m%dT%H%M%SZ).json"
# test -s "$P08_B45_BOOT_BIF" && test ! -e "$P08_B45_OUT"
# PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
#   scripts/p08_b45_fsbl_source_channel_gate.py \
#   --original-report "$P08_B45_PRIOR" --original-xsa "$P08_B45_XSA" \
#   --psu-c "$P08_B45_C" --psu-h "$P08_B45_H" \
#   --psu-tcl "$P08_B45_TCL" --artifact "$P08_B45_BOOT_BIF" \
#   --out "$P08_B45_OUT"
```

`--artifact` can repeat for at most 12 individual, original,
host-existing regular non-symlink files. Textual BIF/map/JSON/flag
files can contain a `bootloader` keyword or
`FSBL_PROT_BYPASS_EXCLUDE` marker; presence of that text is **not
proof** it compiled or booted. Never pass an active device,
`/dev/mem`, or remote filesystem write path.

## 5. Physical pilot acceptance path — still NO-GO

The present source check cannot authorize physical inference. Before
a 16-image pilot, independently establish **all**:

1. Which physical boot medium/BOOT.BIN/FSBL ELF is running and the
   actual compiler branch; preserve recoverable known-good media.
2. Original 27 P02 backup records' trusted 13.5MiB placement, each
   authenticated **before** securing/locking, and ownership of
   the extra 512KiB in the 14MiB protection envelope.
3. Actual port master IDs, effective read/write rules and
   configured region slots/priorities on all six DDR XMPUs,
   including A53/CCI and PL/RPU/other write masters.
4. A trusted continuing read-only protection/owner attestation
   exposed to a **new** independently built/admitted A53 guard.
   Do not edit the current guard to return success.
5. Independent recovery plan, passive preflight, and **new
   explicit operator approval** of the exact physical actions.

After approval, run 16 original TRAIN-derived images per candidate
and demand all frozen 26-tick neural/FNV results match the scalar
oracle before measuring reset and whole-service timing; the 1024
runs require separate approval. Original TEST stays sealed.

After completing the inherited deeply nested B4.5.4.5 stage,
future work is tracked as **P08-B4.5 work packages**, using
plain deliverable names/PRs rather than another .4.5.4.x number.
Keep P08-B4.6 reserved for the later repeated Track A/B comparison.
