# P08-B4.5.3 — Two distinct A53 applications, offline Vitis build instructions

**Status (2026-11-03): SOURCE / NATIVE CI.** The two mode-specific
standalone A53 applications and their offline source/Vitis/ELF tests are
implemented. A **genuine local Vitis 2025.2 AArch64 ELF/map build has not
yet been run or admitted** in this milestone. No new physical JTAG,
DDR writes, PL program or KV260 inference have been authorized.

## Why two applications, not one mutable production ELF?

The previously accepted uninstrumented B2.3 firmware and fully authenticated
B4.4.2 profiler remain frozen. The B4.5 experiments each get a separate
entrypoint, Vitis project/platform, fresh evidence directory and original
source/network provenance:

| Experiment | C entrypoint | Vitis ELF | Session bind | Per-image reset |
|---|---|---|---|---|
| B4.5.1 authenticate once | `p08_b45_auth_once_full1024_a53.c` | `p08_b45_auth_once_1024.elf` | 27 source SHA-256 + header checks | 27 source and destination P02 header checks, no SHA |
| B4.5.2 unchecked content | `p08_b45_unchecked_full1024_a53.c` | `p08_b45_unchecked_1024.elf` | no context-data hashes or P02 headers | no SHA, no headers, no context-content scans |

Both reuse the accepted P07 full inference engine, P03 device adapter,
27 logical 512KiB contexts, 3 PL slots, 26 ticks, 702 dispatches,
frozen raw input/ingress/route semantics, original CRC result journals and
the same complete A53 six-phase image-service timer.
**Unchecked content applies to the context-reset path, not to independent
host/source admission or the per-image result journal.** Both variants
still perform the accepted raw-pool source SHA admission and per-image
journal raw/wire SHA so independent provenance can be assessed. No neural
weights, event scheduling or source checkpoint was changed.

The extra reset-only 256B sidecar at `[0x42400000,0x42440000)` is a new
B4.5 schema with distinct mode magics and counters (not the B4.4 sidecar
schema). The recorded fields include source/destination check counts,
14,155,776 copied bytes, one-time bind ticks, per-image reset ticks, actual
A53 CNTFRQ and a guard-provisioned flag. The ordinary 1023 frames exclude
the selected ordinal 1023 trace. Original result and six-phase timing
journals are preserved independently of this sidecar.

## Hardware ownership STOP gate — both bundled ELFs deliberately fail closed

`software/p08/p08_b45_a53_backup_guard.c` is an **unprovisioned**
platform protection adapter. Both callbacks return failure (not a no-op
success). The build-stage inventory checks this guard's exact source,
and its provisioned flag remains `0`. **Any resulting ELF is for offline
linking/static admission only and will refuse to begin inference** at
reset-session bind (first-fault mailbox code 105). There is no authorization
to load either ELF on the KV260.

A working future guard requires a separately audited, demonstrably
persistent exclusive/read-only immutable DDR ownership configuration.
The Zynq UltraScale+ XMPU can enforce memory master/region access policy,
but AMD's UG1085/UG1137 note that secure-master configuration and lock
state are boot-time concerns. Some XMPU locks reset only on power-on reset.
Do not write XMPU registers from the A53 to make these tests work.

Current physical region uncertainty includes the immutable backup
`[0x43000000,0x43D80000)`, the reset sidecar
`[0x42400000,0x42440000)`, all original P08 journals/timers/mailbox,
boot firmware, TF-A, U-Boot, Linux, RPU and PL DMA masters. A safe future
implementation requires a separate full-owner audit, an independently
reviewed boot/protection configuration, read-only preflight and new
operator consent/recovery plan. A source-only platform stub is not proof
of hardware protection.

AMD references:
- Zynq UltraScale+ UG1085, System Protection / XMPU Configuration:
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Configuration
- Zynq UltraScale+ UG1085, XMPU Protection of Slaves:
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Protection-of-Slaves

## Step 1 — pull branch and run PC-only regressions

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-reset-integrity
git pull --ff-only origin agent/v3-p08-b45-reset-integrity
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b45_reset_variants.py \
  tests/test_p08_b45_a53_build.py \
  tests/test_p08_b45_elf_admission.py \
  tests/test_p08_b45_sidecar.py

# Also preserve inherited acceptance paths:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b44_profile_physical.py \
  tests/test_p08_b4_2_full1024_physical.py \
  tests/test_p08_b44_reset_profile_sidecar.py \
  tests/test_p08_b44_profile_elf_admission.py \
  tests/test_p08_b44_build_offline.py
```

Source-only syntax tests inject synthetic Xilinx header declarations to
compile with GCC. This is **not** a real AArch64 Vitis BSP build. The ELF
admission negative tests create unmistakably synthetic ELF64 fixtures;
they are not hardware artifacts.

## Step 2 — discover and export ALL signed prerequisites

**Do not assume dated paths from a previous workstation session.** B4.5
requires exactly three exported source variables and the Vitis 2025.2
toolchain (plus mode/build-dir variables in Steps 3 and 4):

| Environment variable | Required contents |
|---|---|
| `P08_B45_ORIGINAL_ELF` | Accepted original B2.3 full1024 `.elf` |
| `P08_B2_RESET_PINS` | Directory holding the accepted B2.2 27-core SHA header **and manifest** |
| `P07_B4L_REPORTS` | Directory holding the accepted `p03_2_ps_mmio.xsa` **and** `p03_2_post_route_metrics.txt` |
| `P08_B45_MODE` | `once` or `unchecked` — set freshly for each build |
| `P08_B45_BUILD_DIR` | A **new**, absolute evidence directory outside Thesis, separately created for each build |

Use these discovery commands when paths have moved or the shell was
restarted. They are read-only:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate

# Find every candidate on this PC (do not blindly select the first match):
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_3_image_only_1024.elf" -print
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_2_original_context_sha256.h" -print
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_2_original_context_reset_pins.json" -print
find "$HOME/Thesis_Evidence" -type f -name "p03_2_ps_mmio.xsa" -print
find "$HOME/Thesis_Evidence" -type f -name "p03_2_post_route_metrics.txt" -print

# If Vitis commands are not already in PATH:
command -v vitis || true
find /tools /opt "$HOME" -type f -path "*/Vitis/2025.2/settings64.sh" -print 2>/dev/null
# Source the exact Vitis 2025.2 settings64.sh path discovered above.
```

The next block is a **complete export example for the original accepted
artifacts** as recorded in this project's B4.4 runbook. The original ELF
and pin paths have been used in the operator's current B4.5 session.
**Important operator correction (2026-11-04):** The previous `find`
searched only `$HOME/Thesis_Evidence`. The original accepted P07-B4L
runbook (`docs/P07_B4L_CONSOLIDATED_MODEL_DEPLOYMENT.md`) explicitly
places the routed P03.2c reports inside the **project's Vivado build tree**:
`$V3/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports`.
Vitis-imported copies in `Thesis_Evidence` often contain the XSA but NOT
the original companion `p03_2_post_route_metrics.txt`, so discovery
limited to `Thesis_Evidence` can never set `P07_B4L_REPORTS`. Set this
canonical path first and verify its XSA SHA; if missing, search the Vivado
build tree and evidence dirs for both files rather than guessing.

```bash
export P08_B45_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"

# Exact accepted P07-B4L original Vivado routed reports location,
# taken from docs/P07_B4L_CONSOLIDATED_MODEL_DEPLOYMENT.md:
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"

# If the exact original build directory was relocated, inspect BOTH
# sources and select only a directory with BOTH required originals:
if [[ ! -s "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa" ||
      ! -f "$P07_B4L_REPORTS/p03_2_post_route_metrics.txt" ]]; then
  echo 'Original P03 route reports directory moved; candidates:'
  find "$PWD/vivado/build" "$HOME/Thesis_Evidence" -type f -name "p03_2_post_route_metrics.txt" -print 2>/dev/null
  find "$PWD/vivado/build" "$HOME/Thesis_Evidence" -type f -name "p03_2_ps_mmio.xsa" -print 2>/dev/null
  echo 'STOP: review candidate XSA SHA and original sibling metrics before export'
fi

# Print all active exports before launching an expensive build:
printf 'ORIGINAL_ELF=%s\nPINS=%s\nROUTED_REPORTS=%s\n' \
  "${P08_B45_ORIGINAL_ELF:-UNSET}" \
  "${P08_B2_RESET_PINS:-UNSET}" \
  "${P07_B4L_REPORTS:-UNSET}"

# Fail closed if a path is absent or is not an accepted original artifact:
test -s "$P08_B45_ORIGINAL_ELF" || echo 'STOP: original ELF missing'
test -s "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" || echo 'STOP: pin header missing'
test -f "$P08_B2_RESET_PINS/p08_b2_2_original_context_reset_pins.json" || echo 'STOP: pin manifest missing'
test -s "${P07_B4L_REPORTS:?Must export accepted routed P03 reports}/p03_2_ps_mmio.xsa" || echo 'STOP: P03 XSA missing'
test -f "$P07_B4L_REPORTS/p03_2_post_route_metrics.txt" || echo 'STOP: routed metrics missing'

sha256sum \
  "$P08_B45_ORIGINAL_ELF" \
  "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" \
  "$P08_B2_RESET_PINS/p08_b2_2_original_context_reset_pins.json" \
  "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa"
```

**Accepted SHA-256 values (compare the printed values exactly):**

| File | Expected digest |
|---|---|
| B2.3 production ELF | `0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1` |
| B2.2 context SHA header | `5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171` |
| B2.2 SHA manifest | `1d915c36eaf42740bac9e62afae58ffe80c94ae51cbf6c6c809d3fd6e626ce34` |
| Accepted routed P03 XSA | `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f` |

After sourcing your genuine installed Vitis 2025.2 environment, verify:

```bash
command -v vitis
command -v aarch64-none-elf-readelf
command -v aarch64-none-elf-nm
```

If the original paths above have changed, use the `find` output to
replace the corresponding exports. Do **not** bypass a hash mismatch,
modify the frozen source or edit the hash to match an unverified file.
The B4.5 wrapper originally contained a **mistyped expected header SHA**;
that bug was corrected without changing any accepted artifact.

## Step 3 — separately build B4.5.1 authenticated-once ELF/map (NO BOARD)

```bash
export P08_B45_MODE=once
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_once_build_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B45_BUILD_DIR"
bash scripts/build_p08_b45_variant.sh

sha256sum \
  "$P08_B45_BUILD_DIR/vitis_workspace/p08_b45_auth_once_1024.elf" \
  "$P08_B45_BUILD_DIR/vitis_workspace/p08_b45_auth_once_1024.map" \
  "$P08_B45_BUILD_DIR/p08_b45_once_elf_admission.json"
```

Expect source-stage exact PASS, a genuine AArch64 ELF/map and separate
offline admission PASS, and these explicit NO-BOARD markers:

```text
P08_B45_VARIANT_GENUINE_A53_ELF_STATIC_ADMISSION_PASS=1
P08_B45_once_A53_ELF_AND_MAP_BUILT=1
P08_B45_BACKUP_GUARD_PROVISIONED=0
P08_B45_NEW_KV260_PHYSICAL_RUN=NOT_RUN
P08_B45_EXPERIMENTAL_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED
```

The one-time SHA checks are included in the bind interval, not charged to
the per-image reset-service measurement.

## Step 4 — separately build B4.5.2 unchecked-content ELF/map (NO BOARD)

Keep the original environment prerequisites. Use a **different fresh**
evidence directory and mode:

```bash
export P08_B45_MODE=unchecked
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_unchecked_build_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B45_BUILD_DIR"
bash scripts/build_p08_b45_variant.sh

sha256sum \
  "$P08_B45_BUILD_DIR/vitis_workspace/p08_b45_unchecked_1024.elf" \
  "$P08_B45_BUILD_DIR/vitis_workspace/p08_b45_unchecked_1024.map" \
  "$P08_B45_BUILD_DIR/p08_b45_unchecked_elf_admission.json"
```

Expect a **different** original 27-core B4.5 unchecked ELF identity,
different ELF/map digests, and the same no-board/no-guard markers.
If a build fails, preserve its external staged sources, logs and
readelf output. Do not overwrite directories or substitute the accepted
B2.3/B4.4 ELF to satisfy new identity checks.

## Step 5 — what can and cannot be tested after Vitis build

**Can test now:** exact source inventory, strict native C11 syntax, real
Vitis 2025.2 compilation/linking, distinct ELF identities, actual
low-DDR ELF64/AArch64 PT_LOAD envelope, linker map reset/guard/full-neural
symbols, pinned original P03 XSA/ELF and SHA header, independent
offline admission.

**Not authorized yet:** XSDB, PL programming, source DDR staging,
A53 takeover, board-local 16/1024 inference, physical latency or neural
parity claims. The current unprovisioned guard makes genuine physical
inference impossible by design.

A future accepted 16-image pilot per variant and then a new full1024
session need a distinct guard-enabled, independently verified build plus
a new dedicated physical runner/verifier. PC-only
`scripts/p08_b45_sidecar.py` already defines strict sidecar checks,
but raw sidecar structure alone is NEVER physical neural parity proof.

The accepted B4.4.2 run and every original artifact remain untouched.
