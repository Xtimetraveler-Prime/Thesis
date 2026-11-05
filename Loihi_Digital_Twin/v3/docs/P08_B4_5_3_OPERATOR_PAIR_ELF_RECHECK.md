# P08-B4.5.3 — independent PC-only verification of BOTH genuine A53 builds

**Correction after operator's independent SHA diagnostic:** An earlier
copy of the pinned Experiment A admission JSON digest omitted its terminal
hex character `e` (63 characters rather than 64). The corrected value
`602238d0fddc9d13c9c4a67176f023748f77e62ee49f28564b4e2d20793c526e`
exactly matches the originally posted operator SHA and the rechecked
on-disk report. No ELF, map or JSON was modified or rebuilt.

**Evidence status (November 4, 2026 local / November 5 UTC):**
The operator reported successful genuine offline Vitis 2025.2 builds
for authenticated-once (A) and unchecked-content (B), and supplied exact
SHA-256 hashes for each separate ELF, linker map, and admission JSON.
The project pins these six hashes in
`P08_B4_5_3_OPERATOR_REPORTED_A53_ARTIFACT_PINS_2026_11_05.json`.
**Those hashes originate from the user's PC output, not from files
independently accessible to GitHub CI.**

## Exact operator-reported artifacts

| Mode | Root | ELF SHA-256 | Map SHA-256 | Admission JSON SHA-256 |
| --- | --- | --- | --- | --- |
| A / `once` | `/home/dna/Thesis_Evidence/p08_b45_once_build_20261105T041935Z` | `70501217482d156d59037a8694b9b837938026cba0d62ccd1f8939bfdd112e04` | `946ed7105d01bb9bf0548208c46707d6dc2d6df7edfd31f937bd58f70fbfe691` | `602238d0fddc9d13c9c4a67176f023748f77e62ee49f28564b4e2d20793c526e` |
| B / `unchecked` | `/home/dna/Thesis_Evidence/p08_b45_unchecked_build_20261105T042140Z` | `f6e09a8cde5ecd05900b30f0cc91d8d9549f2ae1e446157eb2c06024e0fd1655` | `f23298ccd3842e3ef89ed2157238123f38e1995a42ccca0f830fad12028e7545` | `be2284d366dd53d1474719eabefaa7133fa59a809fa047251dff20884b45998b` |

## Pull current sources and set EVERY input path

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-reset-integrity
git pull --ff-only origin agent/v3-p08-b45-reset-integrity
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Three accepted ORIGINAL immutable input paths:
export P08_B45_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"

# Two genuine new mode-distinct local build roots reported by the operator:
export P08_B45_ONCE_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_once_build_20261105T041935Z"
export P08_B45_UNCHECKED_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_unchecked_build_20261105T042140Z"

# Fresh, out-of-repository, NO-OVERWRITE independently recomputed report:
export P08_B45_PAIR_CHECK_REPORT="$HOME/Thesis_Evidence/p08_b45_pair_offline_independent_$(date -u +%Y%m%dT%H%M%SZ).json"
```

If an original source directory is relocated, find it BEFORE changing
an export. Never use a Vitis-imported XSA that lacks original routed
P03 metrics as if it were the primary P03 reports directory.

```bash
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_3_image_only_1024.elf" -print
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_2_original_context_sha256.h" -print
find "$PWD/vivado/build" "$HOME/Thesis_Evidence" -type f -name "p03_2_post_route_metrics.txt" -print 2>/dev/null
find "$PWD/vivado/build" "$HOME/Thesis_Evidence" -type f -name "p03_2_ps_mmio.xsa" -print 2>/dev/null
```

Ensure all expected artifacts actually exist before running the verifier:

```bash
test -s "$P08_B45_ORIGINAL_ELF" &&
test -s "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" &&
test -s "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa" &&
test -f "$P07_B4L_REPORTS/p03_2_post_route_metrics.txt" &&
test -s "$P08_B45_ONCE_BUILD_DIR/vitis_workspace/p08_b45_auth_once_1024.elf" &&
test -s "$P08_B45_ONCE_BUILD_DIR/vitis_workspace/p08_b45_auth_once_1024.map" &&
test -s "$P08_B45_ONCE_BUILD_DIR/p08_b45_once_elf_admission.json" &&
test -s "$P08_B45_UNCHECKED_BUILD_DIR/vitis_workspace/p08_b45_unchecked_1024.elf" &&
test -s "$P08_B45_UNCHECKED_BUILD_DIR/vitis_workspace/p08_b45_unchecked_1024.map" &&
test -s "$P08_B45_UNCHECKED_BUILD_DIR/p08_b45_unchecked_elf_admission.json" &&
test ! -e "$P08_B45_PAIR_CHECK_REPORT" &&
echo "P08_B45_BOTH_LOCAL_SOURCE_SETS_PRESENT=1"
```

**If the above does not print `=1`, stop and inspect paths.**

## Reverify both builds independently (no Vitis or board required)

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 scripts/p08_b45_pair_elf_evidence.py \
  --original-elf "$P08_B45_ORIGINAL_ELF" \
  --xsa "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa" \
  --pins-header "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" \
  --out "$P08_B45_PAIR_CHECK_REPORT"

test -s "$P08_B45_PAIR_CHECK_REPORT" &&
sha256sum "$P08_B45_PAIR_CHECK_REPORT"

python3 -m json.tool "$P08_B45_PAIR_CHECK_REPORT"
```

Expected success marker:

```text
P08_B45_TWO_GENUINE_A53_ELFS_INDEPENDENT_OFFLINE_PASS=1
P08_B45_BOTH_PROVENANCE_AND_SOURCE_GUARD_MATCH=1
P08_B45_KV260_PHYSICAL_INFERENCE_VERIFIED=0
P08_B45_DDR_OWNER_INDEPENDENTLY_PROVEN=0
P08_B45_DESTRUCTIVE_JTAG_AUTHORIZED=0
```

The verifier compares all six bytestring digests against the operator's
checked-in pins; re-runs `p08_b45_elf_admission.audit` on the actual
local files; insists the original JSON equals that recomputed outcome;
verifies the frozen original B2.3 ELF/P03 XSA/B2.2 header digests; checks
that staged reset/guard/mode-specific entrypoint sources match the
reviewed branch; and confirms that the guard intentionally returns
failure rather than granting DDR ownership.

This is a **static, PC-only artifact/provenance gate**. It does not run
either ELF, prove secure memory-master ownership, validate neural
outputs, authorize destructive JTAG, or unseal official MNIST TEST.

After the operator supplies a passing terminal transcript and fresh
independent JSON SHA, the B4.5.3 **build/static-admission** work can be
recorded complete, separately from the B4.5.4 physical validation gate.
