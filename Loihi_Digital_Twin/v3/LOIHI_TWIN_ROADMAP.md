# Loihi Digital Twin v3 Development Roadmap

## P08-B4.5.4.5 IN DEVELOPMENT — generated PSU source dependency and offline boot candidate inventory (PC-ONLY)

New descendant branch `agent/v3-p08-b4545-generated-psu-audit`,
stacked on accepted B4.5.4.4 draft PR #59. **Operator-local verification
and real-source JSON SHA are pending; this is NOT accepted physical
evidence.** The original accepted 4.4 report SHA is pinned:
`e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9`.
The new read-only script `scripts/p08_b4545_generated_psu_graph.py`
verifies original routed P03 XSA and independent generated
`psu_init.c`, `psu_init.h`, `psu_init.tcl` exact-byte identity.
It walks named C dependencies from `psu_protection()` /
`psu_protection_lock()`, records unresolved function/macro references,
literal register call sites, port-level hints and HWH/Tcl symbols,
and SHA-inventories only optional operator-specified pre-existing
BOOT.BIN/BIF/FSBL build artifacts. Because this is not a preprocessor,
symbolic source hints cannot prove region-slot, secure/NS, 10-bit
master IDs, priority, permissions or locked effective XMPU state.
Possible absence of literal XMPU sites is NOT proof that generated
tables do nothing. All original ELF, HLS/bitstream, 27 frozen P02
records and official TEST stay unchanged; **no board contact or writes**.

Native negative tests and the no-board CI workflow are newly added.
Operator runbook (all required exports and bounded read-only
`find` commands):
[docs/P08_B4_5_4_5_GENERATED_PSU_SOURCE_AND_BOOT_CANDIDATE_RUNBOOK.md](docs/P08_B4_5_4_5_GENERATED_PSU_SOURCE_AND_BOOT_CANDIDATE_RUNBOOK.md).
Do not mark accepted without operator report and SHA. The currently
active KV260 FSBL/compiler flags/boot medium, all DDR master owners,
13.5 MiB backup protection and adjacent 512 KiB remain unproven.
A53 guard remains fail-closed. **NO-GO** for XMPU enabling, firmware
changes, DDR/JTAG/PL access or physical inference.

**Numbering simplification (after the current 4.5 family closes):**
use one `B4.x` entry per substantive next deliverable and record its
individual checks in the entry/PR; do not continue a `4.5.4.6`
subsubsubtask chain. Preserve existing numbered accepted evidence and
stacked draft PRs intact until explicitly approved to merge.

---

## P08-B4.5 ACTIVE — context-reset integrity optimization experiments (2026-11-03)

**Status:** P08-B4.5.1/.2 reset kernels and two separate source-level
A53 applications are implemented. Operator posted a clean local PASS of
the original **70 B4.4 regression tests** and **2 B4.5 native tests**.
Original P08-B4.5.3 no-board regression passed the inherited 72 +
81 source/ELF/sidecar/pinned-SHA + 15 paired-ELF tests (168 total).
B4.5.4.1 added independent DDR-owner gap tests; the B4.5.4.2
policy branch adds six-port/10-bit-ID/region-priority/boot-order
native tests. The **current stacked no-board CI passes all inherited
and new tests** (B4.5.4.2 run `41974939755`, PASS). Draft PR stack:
#54 (B4.4) -> #55 (B4.5.3) -> #56 (B4.5.4.1) ->
#57 (B4.5.4.2); all open/draft/unmerged.

**Both genuine Vitis 2025.2 A53 ELFs/maps are now OPERATOR-REPORTED
BUILT (2026-11-05 UTC).** The operator supplied six distinct SHA-256
digests for the `once` and `unchecked` ELF, map and admission JSON.
These are pinned in the
`docs/P08_B4_5_3_OPERATOR_REPORTED_A53_ARTIFACT_PINS_2026_11_05.json`
source-reported evidence manifest. **On the first local paired-ELF
verification, the operator found that the new evidence manifest had
accidentally omitted the final `e` in the authenticated-once admission
JSON SHA: recorded `602238...c526` (63 characters), actual/original
`602238...c526e` (64 characters).** The operator's read-only
diagnostic showed all four real ELF/map hashes and the unchecked-report
SHA matched exactly; the authenticated-once report also matched the
*originally supplied* correct SHA. The source-evidence manifest and
runbook have been corrected to the original 64-digit SHA. A new
regression requires six proper 64-character lowercase hexadecimal
digests and explicitly pins the correct once admission-report SHA.
**INDEPENDENT OFFLINE PAIR VERIFIED / P08-B4.5.3 ACCEPTED (2026-11-05 UTC).**
The operator reran the independently recomputed genuine paired-A53
offline checker and posted
`P08_B45_TWO_GENUINE_A53_ELFS_INDEPENDENT_OFFLINE_PASS=1` and
`P08_B45_BOTH_PROVENANCE_AND_SOURCE_GUARD_MATCH=1`.
Independent JSON path:
`/home/dna/Thesis_Evidence/p08_b45_pair_independent_20261105T045733Z.json`;
SHA-256
`03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1`.
Full source-derived acceptance:
`docs/P08_B4_5_3_INDEPENDENT_DUAL_A53_OFFLINE_ACCEPTANCE_2026_11_05.md`.
No physical inference, DDR ownership proof or JTAG launch occurred;
the genuine **offline** build provenance was independently accepted.
No JTAG, DDR writes, physical KV260 inference or neural/latency
verification are authorized or reported.

The accepted P08-B4.4.2 full-SHA reset profile is the immutable reference:
1,023 ordinary frames; reset-service median **5,826.767549 ms**; source
SHA-256 median **2,908.5978 ms**; destination SHA-256 median
**2,908.5991 ms**; mutable 27-context memcpy median **7.0247 ms**.
The two SHA scans account for approximately **99.84% of summed reset ticks**.
The separate original B4.4 full image-service median was **13,034.111501 ms**.
These are distinct sessions and must not be subtracted as if paired.

### P08-B4.5.1 — authenticate once, lightweight per-image checks

Authenticate all 27 immutable backup records once at session bind. Require a
real platform mechanism that establishes persistent exclusive/read-only
ownership of the entire backup range. On each image, confirm that protection
remains active, validate all 27 source P02 headers before the first copy,
perform the original 27-context memcpy/cache/barrier sequence, and validate
all 27 destination headers. No per-image SHA-256 is permitted. This mode is
only integrity-defensible if the platform actually prevents backup mutation;
a software flag or no-op lock callback is not proof.

### P08-B4.5.2 — unchecked-content performance bound

Remove SHA-256, P02-header, CRC and payload-content checks from the reset
variant. Retain operational safety controls: pointer/range/size admission,
persistent backup ownership/protection, positive quiescence, cache
maintenance, barriers, callback error handling, generation accounting and
fail-stop poisoning after a partial restore. This is an experimental
performance lower bound, not a production recommendation. Native tests must
demonstrate that content corruption is intentionally not detected.

### P08-B4.5.3 — separate A53 source and Vitis offline builds

**ACCEPTED (2026-11-05 UTC): two genuine Vitis A53 builds and independent paired PC-only static admission.**

Two distinct A53 mains now exist:
`software/p08/p08_b45_auth_once_full1024_a53.c` and
`software/p08/p08_b45_unchecked_full1024_a53.c`. Both reuse the
original frozen P07/P03 26-tick/702-dispatch neural path, original
complete A53 image-service meter and neural result journals. Only reset
integrity policy differs; the unchecked variant still retains unrelated
raw-input provenance SHA and original result-journal raw/wire hashes.

`software/p08/build_p08_b45_variant.py`,
`scripts/build_p08_b45_variant.sh` and
`scripts/p08_b45_elf_admission.py` now support two separate, source-pinned
offline Vitis applications and ELF/map identity/low-DDR PT_LOAD admission.
The B4.5 sidecar uses a new 256B record schema with its own
`scripts/p08_b45_sidecar.py` PC-only structural verifier and native
negative tests. These are **not** actual physical measurements.

**CRITICAL deliberate STOP:** the included
`software/p08/p08_b45_a53_backup_guard.c` refuses backup-region locking
and lock verification. The resulting offline-buildable ELFs are
**intentionally incapable of executing inference on the board** until a
separately audited and accepted real PS/PL DDR backup owner/protection
provider is implemented. Do not replace it with a no-op. Hardware XMPU
configuration may be boot-time/secure-master controlled; never perform
speculative runtime XMPU writes. Source, stage and ELF admission explicitly
pin this fail-closed adapter and continue to report DDR ownership unproven.

**Operator build-preflight fix (2026-11-03):** the first attempt to build
B4.5.1 stopped before Vitis at `original context SHA header drift`.
Investigation found the **new B4.5 shell script contained a mistyped
expected SHA**, not evidence of a changed original model. Corrected its
literal to the accepted B2.2 header SHA
`5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171`.
A CI regression now compares B4.5 shell pins against accepted B2.3
admission constants and B4.4 shell pins. Runbook includes complete
exports and read-only `find`/SHA validation commands. Both offline
Vitis builds subsequently completed according to operator-supplied
six-file SHA-256 output.

**Following B4.5.3:** B4.5.4.1 PC-only geometry and DDR owner-gap
audit was performed and accepted separately (report SHA and reference
below). B4.5.4.2 now explores a vendor-sourced *trusted-boot*
hardware DDR-XMPU policy with native symbolic testing. No physical
DDR, JTAG, PL, ELF download or inference is allowed without genuine
backup read-only/owner proof, new guard-enabled signed builds,
recovery readiness and explicit operator authorization.

Runbooks and commands:
[docs/P08_B4_5_3_TWO_A53_VITIS_OFFLINE_BUILD_RUNBOOK.md](docs/P08_B4_5_3_TWO_A53_VITIS_OFFLINE_BUILD_RUNBOOK.md)
and
[docs/P08_B4_5_3_OPERATOR_PAIR_ELF_RECHECK.md](docs/P08_B4_5_3_OPERATOR_PAIR_ELF_RECHECK.md).
All verification is PC-only.

Keep original B2.3 production firmware, accepted P08-B4.4.2
profiler, P03 shell/XSA/bitstream, B2.4 frozen assets and scalar oracle
unchanged. No variant may silently replace the accepted baseline.

### P08-B4.5.4.1 — PC-only DDR owner/backup-protection gap inventory

**ACCEPTED (2026-11-05 UTC): operator's original PC-only DDR geometry
and physical-owner evidence-gap report; draft PR #56 stacked on PR #55,
both UNMERGED.** This step
follows the independent accepted B4.5.3 paired A53 report
`/home/dna/Thesis_Evidence/p08_b45_pair_independent_20261105T045733Z.json`
SHA-256
`03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1`.
It is deliberately NOT a board execution milestone.

`scripts/p08_b454_ddr_owner_preflight.py` authenticates that
independently accepted paired report by SHA and its typed fields,
rereads all six genuine A53 ELF/map/admission artifact pins and
the staged fail-closed guard, parses the actual A53 ELF64 PT_LOAD
geometry, and checks original P03 + P07 routing + frozen 27-context
and B4.5 original source-declared DDR allocations for static overlap.
The code does not call Vitis, XSDB/JTAG, MMIO, PL or board hardware.
Its owner-gap matrix explicitly marks FSBL, TF-A, U-Boot, Linux,
APU, RPU, PMU/CSU, PL/DMA, all six DDR-XMPU ports and debug/low-DDR
owners as unproven; optional operator-provided boot snapshots remain
unauthenticated observations rather than permission.

**New physical requirement discovered:** the original 13.5MiB immutable
backup `[0x43000000,0x43D80000)` would need conservative 1MiB DDR-XMPU
cover `[0x43000000,0x43E00000)`, including another **512KiB** of
neighboring DDR. The report flags this overprotection as a geometry
consideration only, NOT a configured or locked hardware protection.
AMD UG1085 restricts XMPU configuration to secure masters and
recommends boot-time, locked provisioning. Software-only read-only
page permissions do not prove other DMA/PS/PL master exclusion.
The previously accepted A53 applications still ship the intentional
backup-lock callbacks that return `-1`; they cannot start physical
inference, and no current change enables them.

**Operator-accepted actual risk report:** 
`/home/dna/Thesis_Evidence/p08_b454_ddr_owner_gap_20261105T051850Z.json`,
SHA-256
`7a1d87cf3278245a4a5ed612773ac228097e506f464861c3e1b69856f6ba56f2`,
schema `p08-b454-ddr-owner-gap-pc-only-preflight-v1`,
`decision=PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO`.
Both original new A53 ELFs' observed on-disk PT_LOAD are
`[0x0,0x00109BC0)` (1,088,448B each). None of
the 14 classes of actual PS/PL/boot/DDR owners is proven; no XMPU
was programmed or read. Acceptance document:
[docs/P08_B4_5_4_1_OPERATOR_STATIC_DDR_GAP_ACCEPTANCE_2026_11_05.md](docs/P08_B4_5_4_1_OPERATOR_STATIC_DDR_GAP_ACCEPTANCE_2026_11_05.md).
Full static-PC runbook remains
[docs/P08_B4_5_4_1_DDR_OWNERSHIP_AND_PROTECTION_AUDIT_RUNBOOK.md](docs/P08_B4_5_4_1_DDR_OWNERSHIP_AND_PROTECTION_AUDIT_RUNBOOK.md).

**Next:** B4.5.4.2 trusted-boot DDR-XMPU immutable-backup
protection *design and host-only policy admission*, not real firmware
writes or physical access. Hardware and 16/1024-frame pilots remain
NO-GO until independent proof, a separately rebuilt and statically
admitted guarded A53/boot image, recovery readiness and explicit
operator approval.

### P08-B4.5.4.2 — trusted-boot DDR XMPU immutable-backup policy (PC-ONLY)

**B4.5.4.2 ACCEPTED 2026-11-05 UTC — operator-local PC-only symbolic 6-port XMPU-model validation; hardware protection NOT YET PROVEN.**
Development branch `agent/v3-p08-b4542-xmpu-boot-policy`, draft PR #57,
is stacked on B4.5.4.1 draft PR #56. Preserve both original B4.5.3 Vitis ELF/map
triples and immutable original scalar oracle; DO NOT merge or execute.

**Design decision (adapted from AMD, NOT an original invented IP core):**
A dedicated trusted FSBL/bootloader should load the exact 27 original
signed P02 records and authenticate their SHA-256 hashes before
any boot-time DDR-XMPU protection is locked. All six DDR XMPU
ports would then need the correct 1 MiB-aligned policy covering
`[0x43000000,0x43E00000)`, including the extra 512KiB whose
physical owner is NOT yet known. A53 inference handoff must happen
only after independent secure protection readback and lock evidence.
No new physical BOOT.BIN, boot partition, FSBL or XMPU register
writes are generated by this work.

**Security correction:** a blanket read-only rule for all 10-bit AXI
master IDs prevents writes but may broaden access by allowing
unauthorized masters to READ the sensitive backup. The candidate
therefore uses a mathematical **priority-14 ID/MASK=0 wildcard
deny-read/deny-write** region on each of six DDR XMPUs, plus a
**priority-15 future narrowly allow-listed read-only exception**.
The reader exception is **disabled**, because actual DDR AXI
master IDs, region-slot availability and secure/nonsecure attributes
have not been independently demonstrated. Consequently the current
candidate deliberately cannot provide working A53/PL backup reads.
Its PC sweep exercises all 1024 possible MIDs, both security classes,
multiple addresses and all six ports as **symbolic inference only**.
The existing firmware guard remains unprovisioned/fail-closed.

**Accepted operator evidence (original):**
`/home/dna/Thesis_Evidence/p08_b4542_xmpu_policy_pc_20261105T054738Z.json`,
SHA-256
`ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2`.
Source policy SHA-256 at audit:
`7f78e7582e7fee12a06d83f14e45f1de1faf877ce1429af441dd83db3e851d2a`.
The 147,456 symbolic transactions passed, while
`REAL_READER_ALLOWLIST_READY=0`,
`FSBL_BOOT_PROTECTION_PROVEN=0`,
`XMPU_REGISTERS_PROGRAMMED=0`,
`BOARD_JTAG_DDR_ACTION_AUTHORIZED=0`. 
Source acceptance:
[docs/P08_B4_5_4_2_OPERATOR_SYMBOLIC_XMPU_POLICY_ACCEPTANCE_2026_11_05.md](docs/P08_B4_5_4_2_OPERATOR_SYMBOLIC_XMPU_POLICY_ACCEPTANCE_2026_11_05.md).

**Additional upstream FSBL finding with attribution:** AMD/Xilinx
public `xfsbl_handoff.c` calls `XFsbl_ProtectionConfig()`
**before** `XFsbl_HookBeforeHandoff(EarlyHandoff)`.
The initial assumption that the handoff hook could necessarily
reprogram a locked XMPU is therefore **not valid** without
inspecting the exact local Vitis FSBL and prior boot config.
This new source is
https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c ;
AMD UG1137 handoff describes protection configuration:
https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Handoff.
The next B4.5.4.3 must inventory actual PS initialization and
FSBL/boot sources BEFORE selecting a real secure integration point;
`XFsbl_HookBeforeHandoff` is now **unverified, potentially too late**.
Neither the public upstream `master` source nor this source-coded
observation establishes the user's current installed FSBL version
or board runtime.

**Upstream AMD reference attribution and scope:**

- **AMD UG1085, Memory Protection Unit / Instances:** six DDR XMPU
  units, 1 MiB region alignment and independent read/write access
  checks; https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/AMD-Memory-Protection-Unit
  and https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances
- **AMD UG1085, XMPU Regions / Master ID Validation:** 16 regions
  per unit; higher numbered matching region wins; 10-bit
  `(ID & MASK) == (AXI_MasterID & MASK)` equation.
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Regions
  and https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Master-ID-Validation
- **AMD UG1085, Configuration:** XMPU configurations are
  secure-master privileged, normally established once at boot and
  locked. No speculative runtime XMPU writes permitted.
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Configuration
- **AMD UG1137, Partition Loading and FSBL Hooks:** boot partition
  load into DDR and proposed customization point
  `XFsbl_HookBeforeHandoff(u32 EarlyHandoff)` (**previous proposal;
  may be TOO LATE to adjust XMPU** because AMD public FSBL handoff
  calls `XFsbl_ProtectionConfig` earlier; real Vitis 2025.2
  source, early handoff and existing XMPU locks still **UNVERIFIED**).
  https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Partition-Loading
  and https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Hooks-in-FSBL
- **AMD UG1283, Bootgen `load` attribute:** possible partition
  target address, no real data partition currently generated;
  https://docs.amd.com/r/en-US/ug1283-bootgen-user-guide/load
- **AMD/Xilinx public FSBL hook skeleton** used to locate the
  customization point, not copied into new firmware:
  https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hooks.c

**Authorship:** AMD's XMPU/FSBL facility and boot partition capability
are established vendor mechanisms. The symbolic deny/reader exception
policy, frozen Loihi digital-twin memory envelope and test harness
are our own thesis-specific application of those vendor concepts,
NOT an invented hardware primitive. Cite original AMD sources in the
thesis method section when interpreting any later physical result.

**Files:** `config/p08_b4542_xmpu_boot_candidate.json`,
`scripts/p08_b4542_xmpu_boot_policy.py`,
`tests/test_p08_b4542_xmpu_boot_policy.py` and
[docs/P08_B4_5_4_2_BOOT_LOCKED_DDR_XMPU_DESIGN_AND_PC_RUNBOOK.md](docs/P08_B4_5_4_2_BOOT_LOCKED_DDR_XMPU_DESIGN_AND_PC_RUNBOOK.md).
The current output must stay
`SYMBOLIC_WRITE_DENY_CONTRACT_PASS_READERS_AND_REAL_BOOT_NOT_READY_NO_GO`
and `P08_B4542_BOARD_JTAG_DDR_ACTION_AUTHORIZED=0`.
Next work requires actual boot/FPD/DDR port master inventory,
specific verified reader IDs, trusted boot image sequencing and
secure XMPU readback, plus a new independently admitted guard-enabled
A53 candidate before a separately approved pilot.

### P08-B4.5.4.3 — real Vitis/FSBL/XSA source inventory (PC-ONLY)

**B4.5.4.3 ACCEPTED (2026-11-05 UTC): operator-local SHA-pinned original
FSBL + accepted XSA source inventory; active boot protection NO-GO.** On branch
`agent/v3-p08-b4543-fsbl-boot-inventory`,
**draft PR #58 stacked on draft PR #57** (both UNMERGED).
Unlike prior symbolic 147456-master-access simulation, this submilestone
begins inspecting **real vendor/project source bytes**. No boot image
or physical permission has been established.

The new
`scripts/p08_b4543_fsbl_boot_source_inventory.py`
SHA-pins the accepted operator B4.5.4.2 JSON report
`ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2`
and the accepted routed P03 XSA
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
It reads XSA ZIP metadata without modifying/extracting files,
hashes relevant bounded embedded PS initialization/hardware descriptors,
and optionally hashes actual operator-selected installed
`xfsbl_handoff.c`, `xfsbl_hooks.c`, `psu_init.c`,
`psu_protection.c`, boot `.bif` and FSBL ELF.
When a local handoff C source is provided, it reports the
source-observed order of protection configuration relative to
the before-handoff hook. **It does not prove** that any local source
was compiled into the KV260's current QSPI/SD BOOT.BIN or that source
order implies the true active XMPU lock/reader/DDR owner state.

**New AMD-derived design correction:** upstream
`xfsbl_handoff.c` calls `XFsbl_ProtectionConfig()` **before**
`XFsbl_HookBeforeHandoff(EarlyHandoff)`, so copying an XMPU
register-writing step into the nominal before-handoff hook is
NOT accepted as a safe integration plan. Reference:
https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c
and AMD UG1137 Handoff
https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Handoff .
AMD UG1085's example explicitly programs two CCI-connected
DDR XMPUs (ports 1,2) and defaults other four (0,3,4,5)
to deny; that example cannot be substituted for the K26's
real port topology/region settings:
https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs .
This is **adaptation of public AMD/Xilinx firmware architecture**,
not a novel independently discovered memory-protection primitive.
Our original contribution remains the frozen Loihi digital-twin
context-copy/integrity/performance design and independent
verification of boot/DDR isolation.

**Files:** `scripts/p08_b4543_fsbl_boot_source_inventory.py`,
`tests/test_p08_b4543_fsbl_boot_source_inventory.py`,
`.github/workflows/p08_b4543_fsbl_xsa_pc_only.yml`, and
[docs/P08_B4_5_4_3_FSBL_XSA_READONLY_BOOT_SOURCE_RUNBOOK.md](docs/P08_B4_5_4_3_FSBL_XSA_READONLY_BOOT_SOURCE_RUNBOOK.md).
Operator-supplied original report
`/home/dna/Thesis_Evidence/p08_b4543_fsbl_xsa_inventory_20261105T060831Z.json`,
SHA-256
`9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5`.
Installed Vitis 2025.2 FSBL handoff, hooks and original Vivado PS
sources were actually supplied. Handoff source shows
`PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK`; accepted P03
XSA internal `psu_init.c` SHA matches selected generated
`psu_init.c` exactly. However active boot/compiled FSBL, XMPU lock
readback, actual reader IDs and low DDR ownership remain unproven.
Acceptance:
[docs/P08_B4_5_4_3_OPERATOR_FSBL_XSA_SOURCE_ACCEPTANCE_2026_11_05.md](docs/P08_B4_5_4_3_OPERATOR_FSBL_XSA_SOURCE_ACCEPTANCE_2026_11_05.md).

**Next B4.5.4.4:** inspect exact source-function protection branches
and generated PS DDR XMPU initialization. AMD/Xilinx 2025.2
`XFsbl_ProtectionConfig` has an `XFSBL_PROT_BYPASS` conditional
with different protection behavior. The user's active boot build
macro is UNKNOWN, so proving source availability is not proof of
a physical lock. Vendor source:
https://raw.githubusercontent.com/Xilinx/embeddedsw/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c
and AMD TRM:
https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs .

The operator must supply actual installed source and prior report
paths or let the scanner report missing source honestly.
The current checker may print source inventory PASS but ALWAYS
states `ACTIVE_KV260_BOOT_FSBL_PROVEN=0`,
`PROTECTION_CONFIG_AND_MASTER_IDS_PROVEN=0`,
`FSBL_HOOK_APPROVED_FOR_XMPU_CHANGES=0` and
`BOARD_JTAG_DDR_EXECUTION_AUTHORIZED=0`.
No FSBL build, BOOT.BIN, A53 guard provisioning, JTAG, DDR writes,
PL/MMIO, hardware XMPU read/write or official TEST.

**Next physical prerequisites:** establish exact board boot source
and a reproducible signed boot chain; compare the actually
booted FSBL ELF/partitions with installed C/Vivado-generated
`psu_protection` source; select a trusted integration point
BEFORE any one-time XMPU locking, with verified PS/PL master
IDs and unallocated region slots. Independently prove backup and
extra-512KiB ownership, A53 low DDR exclusivity, staging and
persistent RO readback and obtain NEW operator approval before pilot.
Nothing in this source-only stage closes those gates.

### P08-B4.5.4.4 — original Vitis FSBL compile-time bypass / generated protection source (PC-ONLY)

**ACCEPTED 2026-11-05 UTC — native 16/16 and operator-local
source/FSBL branch provenance PASS; real XMPU/boot NO-GO.** New descendant branch
`agent/v3-p08-b4544-fsbl-protection-review`,
draft PR **#59 stacked on draft PR #58**, all UNMERGED,
stacked on the
operator-accepted original B4.5.4.3 report SHA
`9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5`
(see source acceptance document).

**High-impact AMD/Xilinx 2025.2 source finding and attribution:**
the **versioned release `xlnx_rel_v2025.2`** FSBL `xfsbl_hw.h`
contains `#if !defined(FSBL_PROT_BYPASS_EXCLUDE)` /
`#define XFSBL_PROT_BYPASS`. Thus, under unmodified/default
compile options, `XFSBL_PROT_BYPASS` is defined. The
**2025.2** `XFsbl_ProtectionConfig` in
`xfsbl_handoff.c` has two distinct code paths:

- When BYPASS is defined, invoke `psu_apply_master_tz()`
  and `psu_ocm_protection()`, **not** the generated
  `psu_protection()` and `psu_protection_lock()`.
- With `FSBL_PROT_BYPASS_EXCLUDE` defined by a
  verified separate FSBL build, call
  `psu_protection()` then `psu_protection_lock()`
  **before** ordinary before-handoff hook.
  This could activate generated security settings for
  all relevant XMPU/XPPU units, and is **not automatically
  safe** without full default/region/MID review.

**Original source links (AMD vendor technology, NOT novel thesis IP):**
https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h
and
https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c .
AMD UG1085 XMPU permissions:
https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs .

**Crucial caveat:** the operator's currently active KV260
BOOT.BIN/FSBL ELF/compiler flags are still UNKNOWN. These
2025.2 source defaults do NOT show which branch was actually
compiled into the running board image. We MUST NOT claim
the source default equals the observed physical lock state.
Also, simply enabling `FSBL_PROT_BYPASS_EXCLUDE` without
first auditing the original 2025.2 generated PS security
configuration could break existing boot/PL/DDR permissions.
No new build, boot image, XMPU writes or JTAG is permitted.

New `scripts/p08_b4544_fsbl_protection_path.py` checks
the exact accepted operator B4.5.4.3 SHA, the
independently pinned local `xfsbl_handoff.c`/generated
`psu_init.c` and original routed P03 XSA, and a
new read-only `xfsbl_hw.h` source input. It parses
the actual C function's guarded bypass/full-protection
cases, checks full protection->lock ordering and counts
generated PSU protection functions/literal DDR XMPU
register references. Native tests reject tampered
original reports/PSU/FSBL/XSA, inverted protections,
missing compile option and invented physical proof.
All output and hard NO-GO flags are **PC-only**.
Runbook with every export/find command:
[docs/P08_B4_5_4_4_FSBL_PROTECTION_BRANCH_AND_PHYSICAL_READINESS_RUNBOOK.md](docs/P08_B4_5_4_4_FSBL_PROTECTION_BRANCH_AND_PHYSICAL_READINESS_RUNBOOK.md).

**Original B4.5.4.4 accepted operator report:**
`/home/dna/Thesis_Evidence/p08_b4544_fsbl_protection_branch_20261105T062334Z.json`,
SHA-256
`e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9`.
The operator ran 16 new native tests (all PASS), confirmed original
source hashes and posted
`ACTUAL_LOCAL_FSBL_TWO_BRANCHES_PARSED=1`,
`VITIS_HEADER_DEFAULT_PROTECTION_BYPASS=1`,
`XSA_TO_GENERATED_PSU_INIT_EXACT_SHA_MATCH=1`, but also
`REAL_FSBL_BUILD_COMPILE_FLAGS_PROVEN=0`,
`REAL_DDR_XMPU_PERMISSIONS_PROVEN=0`,
`BOARD_JTAG_BOOT_DDR_WRITES_AUTHORIZED=0`.
Exact final decision:
`FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO`.
Source acceptance:
[docs/P08_B4_5_4_4_OPERATOR_FSBL_PROTECTION_SOURCE_ACCEPTANCE_2026_11_05.md](docs/P08_B4_5_4_4_OPERATOR_FSBL_PROTECTION_SOURCE_ACCEPTANCE_2026_11_05.md).
The next-chat **self-contained handoff seed**, based on the original
historical seed but updated to accepted B4.5.4.4 and proposed next
B4.5.4.5 source-only work, is
[docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md](docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md).
It preserves the original branch/PR workflow, Vitis+Vivado source
locations, evidence SHA list, all initial exports/finds, source
attribution and explicit physical NO-GO gates.

**Critical scope limit of current C parser:** `psu_protection()`
was only 130 bytes of *source body* and `psu_protection_lock()`
43 bytes. Six-port direct-literal XMPU register hits were all zero
in the scanner's restricted literal-address search. This C
source check does **NOT** prove that generated protection does
nothing. It may dispatch into generated helper/config tables or
header/Tcl definitions. It also does not prove active boot
compiler macros, security ID assignments or XMPU state. Do
NOT mistake zero matches for an empty XMPU policy.

**NEXT PROPOSED B4.5.4.5 — PC-only exact generated protection
call-graph and active boot artifact search** (new descendant
feature branch from B4.5.4.4 PR #59, unmerged, draft PR,
native tests, real local operator review before continuing):

1. Read and SHA-pin original P03 XSA `psu_init.c`, `psu_init.h`,
   `psu_init.tcl`, and HWH. Trace full
   `psu_protection()`/`psu_protection_lock()` call graph,
   `psu_protection_data()` and related generated tables,
   literal/macro register addresses, masks, writes and lock
   sequencing. Produce per-port and region-level *source*
   inventory, independent of direct-body literal counting.
   Use original generated PS protection configuration and
   source-specified AXI interface/PL port identities, but
   mark any unproven runtime master ID as UNKNOWN.
2. Search locally for actual BOOT.BIN/BIF/FSBL ELF/FSBL
   build flags/compile_commands/map only by **read-only**
   `find`, `sha256sum` and bounded static analysis. Presence
   does not prove which boot medium the board used. Require
   independent boot-media provenance and read-only board
   approval for any future device observation.
3. Create a **boot-source dependency/region/priority/mask
   conflicts report** with strict SHA/size bounds and
   negative tests. Never enable `FSBL_PROT_BYPASS_EXCLUDE`
   blindly; globally enabling generated security may
   interrupt existing board access.
4. Determine whether a trusted prelock staging/authentication
   mechanism exists or requires a new recoverable boot design.
   Preserve the 27 original frozen P02 records, full 13.5MiB
   `[0x43000000,0x43D80000)` and 512KiB overcoverage
   `[0x43D80000,0x43E00000)`.

**Subsequent, separately gated phases (not approved yet):**
(i) actual boot/DDR-master/exclusive-owner provenance and
safe, read-only physical inspection **only with new user consent**;
(ii) separately built trusted FSBL/boot image on recoverable
development media, staging all SHA-verified backups before
per-port XMPU RO/lock, with a verified read-only A53/PL
master allow-list and no unauthorized writes; (iii) a NEW
independently admitted A53 backup guard capable of **trusted
continuing protection attestation**, not an untrusted flag;
(iv) explicit operator-authorized 16-image KV260 pilot
with full oracle/FNV/neural parity; (v) separately approved
1024-image authenticated-once vs unchecked-content profiles
and whole-service matched comparison. Freeze all previous
Vitis A53 ELFs, bitstreams, XSA and physical evidence.
No project permission for current XMPU/DDR/PL/JTAG writes,
boot-media changes or official MNIST TEST access.

### P08-B4.5.4 — bounded physical validation and full1024 measurements

Only after independent proof of DDR ownership and persistent backup
protection, fresh read-only preflight, recovery readiness and new explicit
operator approval: run a bounded 16-image physical pilot for each variant.
Require exact independent scalar-oracle neural/spike/FNV parity before
accepting timing. After each pilot passes, run a separately approved
1,024-image session. Preserve all 1,024 neural rows, isolate selected trace
ordinal 1023, and use the 1,023 ordinary frames for latency distributions.
Measure both reset subspan and complete A53 image service with matched
boundaries and actual per-session `CNTFRQ_EL0`.

The original immutable backup range
`[0x43000000,0x43D80000)` and B4.4 profiling sidecar range
`[0x42400000,0x42440000)` still require a complete runtime ownership audit
covering boot firmware, TF-A, U-Boot, Linux, RPU, PL DMA and other masters.
Static non-overlap is insufficient. If ownership/protection cannot be
established, stop and redesign. No official MNIST TEST access.

### P08-B4.5.5 — differential analysis and closeout

Compare baseline, authenticated-once and unchecked-content variants using
separately pinned builds and accepted evidence. Report neural parity,
reset latency, complete image-service latency, instrumentation perturbation,
integrity guarantees and failure modes. Do not call the unchecked result a
safe optimization or infer PL-only speedup.

### P08-B4.6 — repeated paired Track A/Track B system comparison

The previously proposed six independent physical sessions in AB/BA/AB
order move here, after B4.5. Use the same frozen 1,024-image population,
1,023 ordinary frames per run, selected trace ordinal 1023 isolated,
complete matched image-service boundaries, actual per-run A53 frequency,
cold-boot/recovery accounting and run-level uncertainty. Track A (42
neurons/26 dispatches) and Track B (1,010 neurons/702 dispatches) are
different workloads; this is a system/workload comparison, not matched
complexity or pure FPGA speedup.

---

## P08-B4.4.2 ACCEPTED — genuine full1024 original 27-context reset microprofiling (2026-11-03)

The operator supplied the output of the separate genuine KV260 profiling
retry and the subsequent PC-only independent verifier. Successful physical
evidence root:
`/home/dna/Thesis_Evidence/p08_b44_profile1024_retry_20261103T061707Z`.
Independent report:
`/home/dna/Thesis_Evidence/p08_b44_profile1024_independent_20261103T100712Z.json`,
operator-supplied SHA256
`47f25cada89dd9220636fbb9539aba5bf0d7705ea3788fdc3ebd1d85f1145cfa`.

All three genuine independent acceptance checks were reported PASS:
same-session JTAG provenance; all 1,024 original neural outputs/FNV spike
fingerprints equal the frozen scalar oracle; and all 1,024 physical reset
profile rows pass SHA/copy/cache/subspan/counter validation. The selected
trace ordinal 1023 is excluded from the ordinary distribution, leaving
1,023 ordinary rows. The paired AB/BA/AB Track A/B benchmark remains
explicitly NOT accepted.

Actual A53 `CNTFRQ_EL0`: **99,999,001 Hz**. Reset-service distribution:
median **5,826.767549 ms**, nearest-rank P95 **5,826.881051 ms**,
minimum **5,826.591948 ms**, maximum **5,827.041922 ms**. Five reset
subphase medians: mutable 27-core memcpy **7.0247 ms** (0.12% of summed
reset ticks); mutable cache clean/invalidate **1.6885 ms** (0.03%);
mutable SHA-256 readback **2,908.5991 ms** (49.92%); original immutable
cache invalidate **0.8392 ms** (0.01%); original immutable SHA-256
**2,908.5978 ms** (49.92%). Unattributed counter/control residual median
**0.0157 ms** (0.00% after rounding). The two SHA scans therefore account
for approximately **99.84% of measured reset-service ticks**. This is a
strong measured bottleneck finding: the authenticated reset interval is
dominated by full-context integrity scans, not by the 27-core memcpy.

Interpretation limits are mandatory: this is an instrumented A53 reset
profile from one physical session, not PL-only compute time, a speedup,
energy, or a repeated A/B comparison. Phase percentages are based on
summed ticks; phase medians must not be added to claim the overall median.
The extra profile DDR region `[0x42400000,0x42440000)` (262,144 bytes)
still lacks independent proof of exclusive boot-firmware/PS/RPU/DMA
ownership. Do not repeat destructive JTAG until a separate memory-owner
audit, fresh read-only preflight and explicit operator approvals are
complete. Track B official MNIST TEST remains SEALED.

Full evidence, hashes, limitations and next gate:
[docs/P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md](docs/P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md).
Earlier roadmap entries below that describe B4.4 physical capture as pending
or not yet done are historical snapshots and are superseded by this
2026-11-03 acceptance entry; their failed-attempt records remain preserved.
Next work is **P08-B4.5 reset-integrity optimization**: compare
one-time authenticated restoration with lightweight per-image header checks
against an unchecked-content performance-bound variant. Preserve the accepted
full-SHA implementation as the reference. The previously proposed six-session
paired Track A/Track B protocol is renumbered **P08-B4.6** and follows B4.5.
No new physical run is authorized until the full DDR ownership/protection
audit and fresh operator approvals are complete. Track A and B remain
materially different workloads, not a matched-complexity comparison.

---

## P08-B4.4 second read-only target-property scan + historical B4i recovery precedent (2026-11-03)

Operator reports normal PuTTY boot and `sudo xmutil unloadapp`
performed while the PC `hw_server` remained running. New
read-only XSDB scan still lists ONLY PS TAP / PMU / PL and
target properties only those 3 nodes. JTAG chain recognizes
xck26 idcode 04724093 and arm_dap idcode 5ba00477; ARM DAP
XSDB properties `is_open=1`, `is_active=1`. This confirms
an active XSDB JTAG DAP node, NOT unlocked Cortex-A53 external
debug and NOT processor target discovery. No board writes
were performed. Exact operator log:
`/home/dna/Thesis_Evidence/p08_b44_a53_properties_readonly_20261103T060320Z.log`
SHA256 `54739cab92716c665939ffb5038e68a3b68a6907ea76b7c53a36588c6ce2080c`.

**Strong same-project historical precedent:** original
P07-B4i real KV260 stop/width pass on 2026-10-22 occurred
after **KV260 reboot, then `sudo xmutil unloadapp`, then
a new XSDB JTAG session**. Original user-reported signed
ledger `docs/P07_B4I_2026_10_22_PHYSICAL_TAKEOVER_WIDTH_PASS_LEDGER.json`
records A53 #0/#1 STOP PASS, #2/#3 exact powered-down
observations, PSU selection, FPD raw 0x00000A00 / 128-bit,
LPD raw 0x00000200 / 128-bit, exact
`P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1`.
It explicitly did NOT program PL, download ELF, touch DDR,
or run inference. Historical source commit
`ca3babc3eb27debe1dc9510595ddea58e8a7529d`.
AMD UG1089 says `xmutil unloadapp` removes the loaded
accelerated application; it is a PL/application lifecycle
operation, not a documented CPU debug unlock. The prior
ledger doesn't say whether hw_server was restarted, so
no claim that restart is required. Latest operator didn't
provide `xmutil listapps` output, so active app removal
status isn't independently confirmed.

**Bounded next recommendation:** one full B4.4 physical retry
is reasonable after confirming no active app via PuTTY
`sudo xmutil listapps` (if active, unload then verify) and
ensuring no competing XSDB/Vivado client. Do NOT kill
hw_server merely because it is listening; the prior ledger
does not say it was restarted. The full B4.4 runner's FIRST
physical action is the original fail-closed P07-B4i gate,
which uses filtered `targets -set -filter` selection
(different from the unfiltered read-only target list).
If target selection or any A53 stop/accounting fails,
the runner aborts BEFORE P03 programming, six DDR source
transfers, new ELF download, experimental DDR overwrite
or inference. If it passes, the runner proceeds only with
the nine explicit operator approvals and acknowledged
unproven DDR-owner risk. Use a NEW evidence directory and
rerun mandatory read-only B4.4 preflight. If the gate
fails for missing target, external-debug denial or any
unexpected response, preserve logs, reboot and STOP;
no repeated attempts or gate weakening. Any attempt
requires reboot afterward, successful or not.

See exact details and operator next command in
`docs/P08_B44_A53_EXTERNAL_DEBUG_READONLY_DIAG.md`.
Original accepted B4.2 physical 1024 numerical parity/
ordinary timing and new genuine B4.4 ELF/map remain
immutable; no B4.4 new reset-profile physical evidence
yet. Official TEST sealed.

## P08-B4.4 post-power-cycle: normal PuTTY boot, physical ARM DAP visible, actual PSU/APU/A53 target hierarchy NOT enumerated (2026-11-02)

Operator confirms KV260 normal serial boot after power cycle,
then successfully ran only separate read-only XSDB target
inventory: 1 PS TAP / 2 PMU / 3 PL. JTAG hardware
chain physically identified xck26 idcode 04724093 and
arm_dap idcode 5ba00477. NO PSU, RPU, APU,
Cortex-A53 #0..3 appeared in XSDB target list;
in AMD UG1725 Zynq UltraScale+ debug-session examples
the CPU targets normally appear in same targets listing.
Original accepted B4 physical sessions previously
succeeded at PSU selection. Existing failed B4.4
destructive run reported A53 #1 external debug
disabled; both observations suggest **current
processor debug target-access/discovery issue**
but do NOT prove security gate versus power/boot
firmware/debugger cause. No accidental user command
is evident; original B2.3/B4.2 and new genuine profile
ELF artifacts remain valid.

Accepted immutable read-only target inventory at:
 /home/dna/Thesis_Evidence/p08_b44_a53_target_readonly_20261102T224514Z.log
 SHA256 f3d7af4824b43a7b1aa66f4bd8ce92669cedc76a8cee73efb3371d97cc22a769

Improved separate read-only diagnostic XSDB
vivado/p08_b44_a53_status_readonly.tcl to
also query processor targets -target-properties
and arm_dap jtag targets -target-properties,
without stop, rst, mrd, mwr, target -set,
security register changes, core reset, PL
programming or DDR/firmware mutation. Native
tests/test_p08_b44_readonly_a53_diagnostic.py
with no-board workflow passed; original P07-B4i
fail-closed CPU halt safety gate untouched.
Operator instructions and actual original target
inventory SHA in docs/P08_B44_A53_EXTERNAL_DEBUG_READONLY_DIAG.md.
Next: OPTIONAL normal-boot PuTTY Linux CPU online
and one read-only XSDB property snapshot. Do not
retry nine-YES destructive B4.4 profiler nor
attempt debug security gate writes until new
observations interpreted and dedicated approval
is considered. Original 1024 neural/FNV and
1023 ordinary timing accepted; NEW reset
hardware microprofiles and true paired A/B
runs/closeout still PENDING. Official TEST
remains sealed.

## P08-B4.4 A53#1 debug failure after full power cycle — only one hw_server process tree observed; READ-ONLY target inventory pending

Operator physically power cycled the KV260 after a failed first
B4.4 profiling JTAG attempt and confirmed original exact
failed evidence root
/home/dna/Thesis_Evidence/p08_b44_profile1024_physical_20261102T201705Z
has exactly stage.txt, preflight.json and 486B
a53_takeover_and_ps128.log; early P07-B4i A53 #0
stop positive, A53 #1 "External debug access is disabled"
no-go. This confirms NO later P03 PL programming,
six original DDR source transfers or new profile
full1024 ELF execution/capture in that attempt.
Operator process list after power cycle shows one
running hw_server process tree (shell/loader/main)
and NO current local xsdb or Vivado process. Other
remote JTAG server clients are not independently excluded.
Normal post-powercycle UART firmware/Linux boot has not
yet been reported. A53#1 EDAD-disabled debug is not
equivalent to a confirmed A53#1 no-power state; original
P07-B4i exact secondary halt/powerdown gate remains
STRICTLY UNCHANGED and must not be bypassed.

New isolated READ-ONLY diagnostic Tcl
vivado/p08_b44_a53_status_readonly.tcl permits
ONLY one localhost hw_server connect, queries
targets and jtag targets, disconnects and prints
STATUS-ONLY / NOT HARDWARE ACCEPTED markers;
NO new STOP, rst, mwr, dow, CPU selection,
DDRx write, PL programming or Linux interruption.
Distinct from completely PC-only mailbox monitor:
this does make hardware JTAG READ observations.
tests/test_p08_b44_readonly_a53_diagnostic.py
runs native no-board syntax/localhost restrictions,
forbidden mutating action source audit, and ensures
original P07 strict stop gate unchanged. Native
.github/workflows/p08_b44_profile_physical_no_board.yml
verifies read-only diagnostic with other B44
new full1024 profile negative tests. Operator read-only
serial/target next actions in
docs/P08_B44_A53_EXTERNAL_DEBUG_READONLY_DIAG.md.
Do NOT reexecute 9-YES profile runner until
actual target and expected boot-state diagnosis;
preserve first failed physical evidence. Original
signed B4.2 first accepted full1024 physical neural
parity/timing and new genuine B44 Vitis ELF
build remain valid/immutable. Real B4.4 profile
timing still pending, true A-versus-B repeated
benchmark still pending, official TEST sealed.

## P08-B4.4 first REAL profiling hardware attempt — NO-GO at existing A53 secondary debug halt, NOT firmware execution (2026-11-02)

Operator completed offline read-only B4.4 admission PASS for
NEW genuine reset profiler ELF SHA
bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3
and linker map SHA
d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9,
then explicitly invoked separate destructive JTAG with nine YES
approvals. Actual new physical attempt evidence directory:

    /home/dna/Thesis_Evidence/p08_b44_profile1024_physical_20261102T201705Z

Actual hardware transcript (do not modify or overwrite):

    a53_takeover_and_ps128.log
    P07_B4I_A53_0_TRANSIENT_POWER_DOWN_RETRY=1
    P07_B4I_A53_0_TRANSIENT_POWER_DOWN_RETRY=2
    P07_B4I_A53_0_STOP_COMMAND_PASS=1
    P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1
    P07-B.4i stop failed for Cortex-A53 #1:
    Context Cortex-A53 #1 state: External debug access is disabled

Existing original production P07-B4i takeover explicitly rejects
all unexpected secondary A53 stop responses: only a genuine confirmed
halt or TWO exact messages "The core is powered down" and
"Cannot halt processor core: power down" are admitted.
"External debug access is disabled" is NOT one of those and
does NOT prove core #1 is safely halted/powered down. ARM A53
architecture separately classifies external debug access permissions
and core-off states, so it is inappropriate to reclassify this
as a benign exact power-down without other independent evidence.
Code correctly FAILED CLOSED at early processor takeover.
NO successful 128bit FPD+LPD width gate, no new original P03
PL programming, no original six DDR source staging, no new
profiled ELF download, no 1024 run, no physical profile capture
or numerical verification is supported by this transcript.

This is **not evidence of erroneous user shell commands**:
preflight accepted, genuine Vitis artifacts and exact SHA matched.
Root cause of current external-debug-disabled A53 #1 remains
undetermined: may depend on core power/debug authorization/boot state
and requires a separate hardware/serial/secure-boot state assessment.
Do not assert board damage, firmware bug or successful profile run.
NO speculative changes to historical accepted P07 B4i takeover;
do not suppress/auto-accept unexpected debug-disabled errors.

**Operator required:** FULL KV260 power-cycle/reboot after ANY
destructive JTAG attempt (Linux may no longer be intact).
Preserve all failed evidence and stopped-CPU transcript;
perform read-only PC log inspection and ordinary serial/boot
verification after power-cycle. Prior to any new physical attempt,
ensure no competing JTAG owner, review exact processor target
states and any boot/security/low-power changes and require new
independent operator risk approval, fresh evidence directory
and same original source+profile ELF preflight; do not reuse
the failed directory. A follow-up exact external debug
diagnostic may be conducted separately, without relaxing
core-stop or PS width admission. Repeated true A-vs-B
and P08-B closure STILL PENDING. Original accepted B4.2 physical
neural and 1023 ordinary timing SHA reports unchanged.

## P08-B4.4.2 EXPERIMENTAL 1024 RESET PROFILE: genuine Vitis ELF accepted, full independent same-session hardware pipeline SOURCE CI PASS (2026-11-02)

Operator genuinely completed NEW experimental Vitis 2025.2
full1024 profile A53 ELF/map separately from immutable original
B2.3, with original P03/27core SHA and AArch64 PT_LOAD
static offline source admission PASS:
- NEW Vitis profile ELF:
  /home/dna/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z/vitis_workspace/p08_b44_reset_profile_1024.elf
  SHA256 **bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3**
- NEW linker map:
  /home/dna/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z/vitis_workspace/p08_b44_reset_profile_1024.map
  SHA256 **d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9**
- NEW independent offline ELF source admission JSON:
  /home/dna/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z/p08_b44_profile_elf_ptload_preflight.json
  SHA256 **7a5818dc5469ea288fefcefb87ebc4fd3ab1e5c7bdce0bbfda717a6f2787b129**.
Actual NEW profile physical JTAG: **NOT RUN**. Original accepted
B4.2 first real 1024 full neural/FNV+timing report SHA
297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032
and original 1023 ordinary descriptive A53 timing report SHA
4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81
remain immutable and enforced as source continuity in NEW
preflight.

Implemented on stacked draft profiling branch and PR #54,
NO BOARD/NO JTAG CI PASS:
- scripts/p08_b44_profile_physical_run.py — **read-only default**.
  Reauthenticates all accepted ORIGINAL B3/B4 numerical/1024
  scalar 64 shards, original P03 XSA/bit/LTX/P07 DDR staging
  and NEW exact signed profiling ELF/map/ELF admission (including
  recomputation). Nine explicit distinct destructive YES
  approvals required, including the NEW 256KiB profile
  region [0x42400000,0x42440000). No new DDR boot/RPU/
  firmware/DMA exclusivity is proven by source check.
- vivado/p08_b44_profile_full1024_run_and_capture.tcl —
  NEW ONLY SHA-pinned profile ELF/download and unique identity;
  same-session independent A53 stop/FPD128+P03 programming,
  original six DDR source byte-exact physical readbacks,
  physical zero/readback of ALL four output regions:
  256B mailbox and three 1024x256B original journal,
  timer and NEW profile regions. Correct 1024/1024 terminal
  state, bounded 3600-poll no-image-progress watchdog and
  global timeout, 1024 original neural+timing and NEW reset
  profile journals physically captured. Reboot mandatory
  after any destructive JTAG attempt; original accepted
  B4.2 Tcl and A53 ELF untouched.
- scripts/p08_b44_profile_independent_physical_verify.py —
  second PC-only verifier independently repeats original
  signed source/ELF SHA/oracle, true JTAG transcript/A53/PSU/P03
  and six DDR source readbacks, FOUR original signed zeroed DDR
  capture regions, original complete1024 26tick×1010
  neural FNV + 10-spike vector and classification parity,
  all 1024 A53 6-phase timers, NEW original 27core
  5-phase SHA/cache/memcpy/after SHA CRC/clock/reset-in-A53
  timestamp nesting. Only separately admits one
  NEW physical 1024 profile numerical and microtiming
  record if every gate PASS, not a performance benchmark.
- tests/test_p08_b44_profile_physical.py,
  .github/workflows/p08_b44_profile_physical_no_board.yml —
  real Tcl mailbox classifier replay (intermediate 1024
  progress does NOT end run), independent synthetically
  complete1024 original source numerical + new 27core
  five-component positive, original scalar-neural/FNV,
  journal CRC, A53 timer CRC, 1024 exact mailbox,
  reset profile source SHA/CRC/size/timing negatives,
  no genuine JTAG in CI. Fixed premature preliminary
  success report: BOTH source+new reset profile must
  PASS before any combined JSON report created.
- Original saved **PC-only nonintrusive** long-run monitor
  scripts/p08_b4_2_monitor_mailbox_pc_only.py now supports
  explicit --capture-subdir profile1024_capture, default
  remains original B4.2 full1024_capture. No additional
  XSDB/hardware/CPU halt/host evidence writes.
- New docs/P08_B44_PROFILE1024_PHYSICAL_RUNBOOK.md with
  exact read-only setup/pinned SHA preflight, nine-YES
  dedicated coldboot physical command, safe PC-only
  mailbox monitoring, mandatory after-any-JTAG reboot,
  separate PC independent real1024 source/reset profile
  acceptance. Operator should **NOT** run new JTAG if
  read-only source preflight NO-GO or hardware ownership/
  physical recovery risks are unacceptable.

P08-B closeout STILL PENDING after this source work:
first independently accepted genuine full1024 NEW reset profile
hardware session and SHA report; nested 26tick scheduler/
AXI-paging/MMIO/trace/routing profiling; TRUE repeated
6 paired A-vs-B AB/BA/AB coldboots, same 1023
ordinary TRAIN validation IDs and full A53 service
boundaries, observed CNTFRQ and run-level uncertainty;
signed P08-B final scientific limitations and user
authorization before merge. Historical 3 pairs of
A2.1-vs-A2.2 are within Track A, NOT A-vs-B. Networks
have 42 versus 1010 neurons and different computational
load; energy, isolated PL-only speedup and original
PS/DDR/DMA exclusive ownership NOT proved, official
MNIST TEST SEALED. Preserve all original B2.4 frozen
artifacts/P03/P07/A/B3/B4/LitReview immutable.

## P08-B4.4.2 genuine Vitis operator retry gate — FIRST ATTEMPT HOST STAGING ISSUE FIXED, NO PHYSICAL RUN

On 2026-11-02 operator locally executed the real separate
B4.4.2 Vitis 2025.2 offline builder, with original accepted
P03 XSA, 27-core SHA pins and accepted original B2.3 ELF.
Vitis began but the *Python exact stage admission*
rightly failed BEFORE new ELF compilation/linking:

    missing={p08_b44_profile_full1024_a53.c,
             p08_b4_4_profile_reset.c,
             p08_b4_4_profile_reset.h}
    extra={p08_b2_3_image_only_a53.c}

Cause is unambiguously in the NEW staging Bash script:
it retained the original B2.3 A53 main and omitted the
three new B4.4 main/C/H profiling files. It was NOT
a compiler, P03 hardware, original model or board problem.
Original accepted physical B4/B3 data, Vitis B2.3
ELF and original frozen sources are all unchanged.

Fixed scripts/build_p08_b44_profile_full1024.sh:
it now COPIES new main/profile_reset.c and .h and does
NOT copy original production main. It invokes
Python exact actual-stage inventory
--check-stage-only with PASS marker
P08_B44_ACTUAL_SHELL_STAGED_PROFILE_SOURCE_EXACT_PASS=1
BEFORE first Vitis call. A new native regression
independently parses the literal Bash cp loops against
the Python Vitis SOURCES+HEADERS and reproduces
operator missing/new + unexpected/old case as a
negative test. Native GitHub Actions PASS
on new source commit e3ae840744d8a01d101dfff29302f13013b20510.
The failure directory in external Thesis_Evidence must
not be overwritten or reused. A NEW genuine Vitis
2025.2 ELF/map retry on operator machine remains
PENDING; no profile physical JTAG authorized or run.
Copyable safe native test/new evidence build commands
preserved in
docs/P08_B4_4_1_RESET_PROFILING_DEV_RUNBOOK.md.

P08-B final remaining independent gates unchanged:
new profile ELF/map SHA and physical DDR memory
admission, dedicated new source-readback+profile
capture, independently verified original1024
26tick x1010 scalar/FNV/spike parity, profiling
of the mixed 26tick MMIO/paging/trace phase,
six real coldboot matched-source A-vs-B pairs,
independent closeout report/user review. Earlier
A2.1-vs-A2.2 three Track-A pairs are NOT paired
A-vs-B evidence. Official MNIST TEST sealed;
power, pure PL speedup and DDR DMA exclusivity
remain unproven.

## P08-B4.4 new 27-core profiled C + independent Vitis build source READY — native CI PASS, real Vitis JTAG NOT RUN

New B4.4.1 full 27x512KiB immutable/mutable SHA, cache+memcpy
reset differential source and B4.4.2 distinct original 1024-image
A53 profile sidecar source are **native CI PASS** on new
stacked DRAFT PR #54, branch agent/v3-p08-b44-profiling
based on B4 draft PR #53.

Genuine native GCC test links original UNMODIFIED production
reset with the NEW portable five-subphase profiler and
original P07 real SHA256. It compares all 13.5MiB of mutable
context bytes across two generations and matches the original
source-SHA-corrupt-before-first-copy poison fault.
Standalone NEW A53 full1024 profile firmware source passes
native C11 syntax using declaration-only Xilinx headers
(no hardware). Profile output 1024x256B has new distinct
CRC/observed CNTFRQ/27SHA/5-phase+residual per-frame rows
at the separately proposed [0x42400000,0x42440000)
DDR region. 1024-row sidecar parser validates exact
ordered CRC/source-SHA/count/clock/additive fields
and rejects 11 malformed synthetic cases. No real
profiled Vitis ELF, JTAG physical copy, additional
full1024 numerical parity or new profile timing observed.

NEW actual Vitis 2025.2 PC-only source build:
scripts/build_p08_b44_profile_full1024.sh, with
software/p08/build_p08_b44_profile_full1024.py.
They stage the original accepted full P07 B4m/27core C
under a new outside-repo work directory with new
A53 profiling entrypoint only; immutable originals
source/ELF unaffected. The build requires original
routed P03 XSA SHA
52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f,
original 27SHA header SHA
5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171,
original full1024 B2.3 ELF SHA
0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1.
New scripts/p08_b44_profile_elf_admission.py checks
distinct experimental genuine AArch64 PT_LOAD ELF, map,
new identity and terminal, original original ELF/XSA/
27SHA pins; explicitly DENIES destructive JTAG
permission, no PS FSBL DMA boot ownership proof.
Build scripts, native C main syntax and synthetic ELF
11 adverse cases pass native CI.

OPERATOR NEXT PC-only action: after pulling PR #54,
source Vitis 2025.2 environment and run
scripts/build_p08_b44_profile_full1024.sh under
fresh P08_B44_BUILD_DIR; instructions in
docs/P08_B4_4_1_RESET_PROFILING_DEV_RUNBOOK.md.
Do NOT attempt JTAG with newly generated ELF.
Independent 1024-source same-session physical profiler
capture verifier for the EXTRA region and original
neural/FNV/timer journals plus new DDR ownership/reboot
consents must be developed and independently verified
before any new destructive profile experiment.

Still pending for P08-B closure: nested 26-tick page/
MMIO/PL-poll/trace/router microprofiles; six true
Track A vs B coldboot AB/BA/AB paired sessions at
matching original 1023 ordinary TRAIN sample identities
and A53 service scope; signed final P08-B limitations/
uncertainty report and explicit user acceptance before
merging drafts #52/#53/#54. Historical Track A
three A2.1-vs-A2.2 pairs are NOT true paired A-vs-B.
Different 42-neuron A and 1010-neuron B workloads
limit performance equivalence; no isolated PL
speedup/energy, exclusive DDR owner or official TEST
claims are made. All accepted original B3/B4 physical
SHA evidence/model/bitstream and LitReview unchanged.

## P08-B4.4.1/B4.4.2 profile source development — original immutable baseline, no new physical JTAG (2026-11-02)

**Scope decision:** user accepted real original B4.2 full1024 physical
neural/FNV parity and genuine 1023 ordinary-frame A53 six-phase
timing breakdown, and requested to proceed with finer-grained
reset + 26tick bottleneck profiling toward P08-B closure.
Previous real B4.4 signed report:
`/home/dna/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json`,
SHA256 **4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81**.
Original physically observed A53 CNTFRQ 99,999,001Hz,
1023 ordinary median 13.0341115s; restore original 27
frozen mutable cores 5.826693s/44.695321% of sum,
mixed 26tick paging/MMIO/FPGA/trace 6.93507s/53.215729%.

**NEW stacked DRAFT profiling branch** agent/v3-p08-b44-profiling,
based on accepted source B4 DRAFT PR #53 (itself stacked on
B3 DRAFT PR #52), in separate DRAFT PR #54.
Original 33-file B2.4 frozen network, original P03 XSA/bit,
P07-B, Track A, B3/B4 real physical evidence, original
SHA-pinned B2.3 A53 ELF/map and root LitReview.md UNCHANGED.

B4.4.1 source assets:
- software/p08/p08_b4_4_profile_reset.[ch] adds NEW distinct
  portable C11 reset routine p08_b44_profile_reset_image,
  preserving original 27x512KiB immutable-before-copy source SHA,
  destination DDR memcpy/cache/barrier/SHA and original
  generation/receipt/error poisoning. Five new disjoint
  microtiming categories: source invalidate, source SHA256,
  destination memcpy, destination clean/invalidate, destination
  SHA256; explicit unattributed counter/control remainder.
  Original p08_b2_context_reset.c/h production source NOT edited.
- Native real 27x512KiB full record-sized differential
  tests/native/p08_b44_reset_profile_diff.c +
  tests/test_p08_b4_4_1_profile_reset_native.py,
  compare production original and profile reset byte-for-byte
  over two generations, exact original receipt and first-fault
  SHA corrupt-before-copy behavior. Portable native tests,
  no FPGA/TEST.

B4.4.2 SOURCE ONLY:
- software/p08/p08_b44_profile_full1024_a53.c is separate,
  distinct identity P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1;
  accepted B2.3 ELF/source untouched. Uses original B4.2
  1024 matched source, 26 ticks, frozen neural/route functions,
  identical original neural and six-phase timing output
  destinations. Adds a separate 1024x256B experimental
  state-reset profile sidecar in [0x42400000,0x42440000)
  after old image service timestamp, exposing five phases,
  observed CNTFRQ, 27core immutable/mutable SHA counts,
  CRC and ordinal. Disjointness asserted relative to
  original B23 timing/backup/bind/frame map, but boot/
  firmware/PS/PL DMA OWNER EXCLUSIVITY NOT proven.
- scripts/p08_b44_reset_profile_sidecar.py +
  tests/test_p08_b44_reset_profile_sidecar.py
  strictly check 1024 256B order, SHA counts, CRC,
  observed clock, additive five spans+residual, selected
  trace ordinal 1023 exclusion, 11 corruption negatives.
  It NEVER attests real physical source or neural parity
  based on a profile sidecar alone.
- .github/workflows/p08_b44_1_reset_profiling_offline.yml:
  native no-JTAG original-vs-new profile differential and
  strict 1024 profile record tests, plus existing source
  B4.4 genuine first-run descriptive analysis regressions.
- docs/P08_B4_4_1_RESET_PROFILING_DEV_RUNBOOK.md:
  operator read-only pull/native tests, mandatory Vitis A53
  distinct experimental ELF, independent JTAG admission,
  independent full1024 FNV+spike re-verification and
  experimental sidecar capture before accepting ANY
  extra reset phase number.

**No profiling Vitis ELF, no new physical 1024 JTAG and no
experimental reset bottleneck microbenchmarks have actually
been produced.** All new C/Python tooling is source-only
until genuine user-local toolchain, new signed ELF/map,
independent same-session JTAG session, new strict sidecar
capture and independent physical provenance/numerical verifier
exist. Do not use accepted B2.3 original ELF hash as
new experimental ELF. User must explicitly reapprove any
destructive B4.4 session and recovery; prior board risk
acceptance does not authorize silent new run.

**Remaining P08-B closeout gates:**
(1) genuine Vitis profiling ELF + memory/DDR admission,
(2) original 1024 neural/FNV parity and signed 27core
source/readback plus profile sidecar first physical experiment,
(3) nested 26tick per-operation page/PL dispatch wait/
trace/route profiling and measurement-intrusion assessment,
(4) true A vs B (NOT historical A2.1/A2.2 within A)
six coldboot independent AB/BA/AB sessions on same 1023
ordinary TRAIN frames, same A53 image-service endpoint
and actual per-run CNTFRQ, with run-level uncertainty and
different network complexity explicitly qualified,
(5) independent P08-B signed closeout report with optional
profiling data, original sealed MNIST official TEST
status and separate user acceptance before any merges.
Power, PL-only speedup and exclusive DDR boot/DMA ownership
remain UNPROVEN/DEFERRED.

---

## P08-B4.4 ACCEPTED first full1024 KV260 real 1023 ordinary-image A53 6-phase descriptive timing and optimization targets (2026-11-02)

Operator directly ran the previously CI-passing PC-only
scripts/p08_b4_4_single_run_timing_audit.py on the genuine signed,
independently verified 1024-image physical B4.2 evidence, excluding
selected trace frame ordinal 1023 from the **1023 ordinary-frame
latency distribution** and preserving original exact CNTFRQ.

- Actual ORIGINAL B4 physical evidence folder (NOW confirmed by operator):
  /home/dna/Thesis_Evidence/p08_b4_2_original1024_physical_20261102T145943Z
- Original B4.2 independent genuine 1024 neural/FNV + A53 timing
  provenance report SHA256:
  297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032
- NEW real one-session six-phase B4.4 descriptive report (PC only,
  no JTAG):
  /home/dna/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json
- **Operator SHA256: 4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81**
- Actual A53 CNTFRQ_EL0 frequency: **99,999,001 Hz**;
  **1023 ordinary images**, whole image-service
  **median 13,034.111500774ms = 13.0341115s**,
  **nearest-rank p95 13,167.109029419ms = 13.167109s**.
- Original six disjoint measured stage medians and their
  population *SUM service time shares*:
  - 27 frozen context restore **5826.693269ms / 44.695321%**;
  - original B1.3 input encode **18.673677ms / 0.143253%**;
  - pager/scheduler reset **228.098739ms / 1.749822%**;
  - all 26 ticks, 702 dispatches, page-in/out, MMIO/poll,
    routing/nested trace **6935.069581ms / 53.215729%**;
  - neural receipt validate **0.000430ms / 0.000003512%**;
  - journal commit **25.534815ms / 0.195872%**.
  **Restoration + neural tick mixed software/PL phase account
  for 97.91105% of the observed A53 whole-service population
  time**. Do NOT add medians to claim exact total median.
  Preserve selected frame 1023 separately to prevent
  trace instrumentation scope bias.

**Source-level implication confirmed:** original
software/p08/p08_b2_context_reset.c
p08_b2_reset_image verifies EACH original 27x512KiB immutable
backup record SHA256 before the first destructive mutable copy;
then memcpy's each 512KiB into mutable DDR and clean/barrier/
invalidate/readback SHA256 verifies the destination per core.
This is a 13.5MiB copy EACH image (13.5GiB copies across
1024 images), plus a minimum of 27MiB SHA source/dest
full-context scan traffic per image. Thus 44.7% reset
includes SOFTWARE integrity SHA, cache maintenance, DDR
copy and verification, not just copying memory or PL neural
arithmetic. These checks enforce original independent
physical model fidelity; removing them changes the
scientific control and is not a valid unacknowledged
optimization. The 53.2% all-tick phase includes nested P07
context paging, AXI/MMIO dispatch and polling, spike routing,
barriers and 27 logical-core PL runs/tick, not pure PL
computation. Per-operation contributions INSIDE it remain
unmeasured. No new physical B4 run required merely to
interpret this first accepted phase result.

**Next gated B4.4 research:** plan separate 27-context
reset SHA/cache/copy instrumentation and full26tick per-core
page-in/out, AXI, neural dispatch+wait, trace/routing counters
under a separately built/new SHA-pinned profiling ELF, not
silently change accepted original B2.3 full1024 firmware.
Before any new hardware JTAG, require matching 1024 original
frozen scalar FNV spike parity and explicit destructive
admission. Then plan new independent coldboot six-session
**TRUE A-vs-B** AB/BA/AB 1023 ordinary matched-source A53
service comparison (original earlier A2.1-vs-A2.2 three
pairs are NOT true A-vs-B pairs). Different A/B network
complexities (42 neurons/26 dispatches vs 1010 neurons/
702 dispatches + paging) limit direct interpretation.
Track A previous 35.67–35.72ms ordinary service medians
are source/boundary context, not an accepted measured
comparable-complexity speedup ratio. Record run-level
variance and actual CNTFRQ; do NOT infer PL-only seconds,
energy, speedup, DDR ownership exclusivity, or official
MNIST TEST from this single B4.2 physical session.
Original B4 draft PR #53 stacked on B3 PR #52 remains
DRAFT/UNMERGED; original model, P03, P07, A and B3
physical evidence and root LitReview.md unchanged.

## P08-B4.4 single-session first physical 1024 original B2.4 timing descriptive analysis — PENDING actual A53 clock/1023 ordinary phase audit

After accepted genuine full1024 KV260 A53/B2.4 neural and six-phase
timing provenance PASS, operator read the signed independent
B4.2 JSON's original 1,024-image FULL service distribution:
**min 1,283,832,503 A53 ticks; median 1,303,433,920 ticks;
nearest-rank p95 1,316,697,749 ticks; max 1,327,299,037 ticks;
n=1024**. Median is in raw A53 CNTVCT ticks; B4 physical
CNTFRQ was NOT pasted, so no definitive seconds accepted yet.
Within this one physical session P95 is about **1.018% above median**
and max-min spread is about **3.386% of min**. These statistics
alone cannot establish run-to-run clock/thermal variation,
energy, hardware speedup or a paired Track A/B comparison.

If B4 recorded CNTFRQ is 100,000,000Hz *conditionally*,
median 13.0343392s/image, min 12.83832503s,
p95 13.16697749s, max 13.27299037s.
The original Track A physical paired A2.1/A2.2 sessions
observed 99,999,001Hz but that is NOT proof of actual
B4 counter frequency. Accepted Track A ordinary 1,023
medians ~35.67–35.72ms, but the architectures differ
fundamentally: 42 neurons/one logical core/26 dispatches
for A vs 1010 neurons/27 virtual cores/702 dispatches
and 27-context per-image reset/page IO for B.
Matched first1024 TRAIN-derived source and 26 ticks
does NOT imply matched computational workload or pure PL speed.
No naive speedup/slowdown ratio is accepted. Original A
first three pairs are A2.1-vs-A2.2 instrumentation,
not true physical paired A-vs-B sessions.

To extract **ACTUAL frequency and correctly scoped 1,023
ordinary-frame A53 service** (trace frame 1023 isolated)
and the six disjoint A53 phase distributions, new read-only
PC-only tools added:
- scripts/p08_b4_4_single_run_timing_audit.py:
  independent already verified physical report SHA
  297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032;
  original scalar SHA
  7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8;
  physical raw 1024×256B sidecar SHA and terminal mailbox SHA
  exactly matched from independent report; actual per-row
  CNTFRQ consistency, original CRC/timestamps and disjoint
  six service intervals. **No board contact/XSDB**.
  Outputs fresh outside-repo 1023 ordinary service and
  six per-phase min/median/p95/max in raw counter ticks
  and actual frequency-normalized milliseconds. Includes
  per-phase additive full-population SUM shares but does
  not naively sum medians. Isolates selected trace frame
  1023 in distinct report.
- tests/test_p08_b4_4_single_run_timing_audit.py
  with complete synthetic 1024-row real wire-ABI sidecar,
  selected-scope checks and corruption negative cases;
  .github/workflows/p08_b4_4_single_run_timing_offline.yml
  native **NO BOARD** source CI.
- docs/P08_B4_4_SINGLE_SESSION_TIMING_ANALYSIS.md with
  operator's genuine exact observed raw values and
  read-only local test/report generation procedure.

**Operator-local genuine descriptive output has NOT yet been
run/verified**, and no subsequent destructive JTAG session has
been proposed/authorized by this offline audit.
Next after actual 1023 ordinary first-session descriptive report:
plan matched, independently coldbooted six paired AB/BA/AB
original Track A/B session procedure and run-level uncertainty
with frozen source identities and scope. Never treat current
A-only three A2.1/A2.2 pairs as A-versus-B repeats.
B4 PR #53 DRAFT/UNMERGED, prior B3 PR #52 DRAFT/UNMERGED;
no changes to frozen 33-asset B2.4, accepted physical source,
root LitReview.md, P07/B3/A outputs, or sealed official TEST.

## P08-B4.2 ACCEPTED: first genuine original 1024-image KV260 physical numerical/FNV parity and 1024 timing rows (2026-11-02)

Operator completed read-only full1024 original scalar + original genuine
B2.3 ELF/map/accepted B3 physical evidence preflight; then personally
ran destructive dedicated original P03/JTAG full1024 original B2.4 A53
KV260 physical session. ALL 54 original 512KiB P02 **mutable and
separately backed up** core DDR readbacks PASS; four frozen original
binding/route/raw1024 source transfers byte exact PASS; result
mailbox/1024x256B neural and 1024x256B A53 timing regions physically
zero initialized/read back. Genuine original SHA-pinned original
full1024 Vitis A53 ELF downloaded. Physical XSDB observed genuine
A53 exact **1,024/1,024 completed** terminal, not merely DONE/progress,
captured all 1,024 original neural journal receipts and all 1,024 A53
timer sidecars; **original independent scalar first-pass numerical
precheck PASS**.

After reboot protocol, operator executed wholly separate PC-only
independent same-session provenance verification against exact accepted
original 64-shard 1024 TRAIN validation scalar/ELF/P03 physical
sources/earlier B3 accepted evidence. Reported:

~~~text
P08_B4_2_ALL_1024_ORIGINAL_NEURAL_AND_SPIKE_VECTORS_PHYSICAL_PARITY_PASS=1
P08_B4_2_ALL_1024_A53_SERVICE_TIMERS_PHYSICAL_CAPTURE_VALID=1
P08_B4_2_INDEPENDENT_SAME_SESSION_PHYSICAL_PROVENANCE_PASS=1
P08_B4_2_SIX_SESSION_TRACKB_LATENCY_BENCHMARK_ACCEPTED=0
~~~

External independent full physical numerical/timing report:
**/home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json**.
**Operator SHA-256: 297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032**.
Operator separately accepted frozen scalar oracle:
**/home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json**,
SHA256 **7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8**.
The B4 physical evidence root was referenced as the original
P08_B4_PHYSICAL shell variable but its literal path was NOT pasted.
Do not guess or fabricate a physical session path. Evidence files
and all externally SHA-signed originals must remain immutable.
Root LitReview.md, frozen original 33 model assets, original Track A
six accepted physical sessions, P07, earlier accepted B3 physical
report and official MNIST TEST remain unchanged.

**B4.2 acceptance:** first independently verified single-session
physical **all 1024** numerical classifier/10-output spike vectors,
26 ticks x 1,010-neuron FNV fingerprint parity, and internal
A53 whole-service/six-phase CNTVCT timer consistency.
This is a meaningful new 64x-sample-scale neural functional
result relative to the earlier 16-image B3 pilot. It does NOT prove
single-session latency speedup, overall energy, PL-only speed,
direct physical byte equality for full raw all-neuron traces,
uncontested PS/boot firmware/PL-DMA DDR ownership, or the required
repeated original Track A/B matched cold-boot latency experiment.
The original selected tracing frame ordinal 1023 must be isolated
from ordinary latency statistics if its instrumentation differs.

**Useful operator process discovery:** during the long physical
all1024 run, no terminal progress was printed after A53 ELF download,
because the single owning XSDB Tcl polls and replaces an existing
PC-side 256B mailbox file. Reading
<exact_active_evidence>/full1024_capture/mailbox_poll.tmp in a
SECOND PC terminal (or mailbox_terminal_physical.bin after completion)
is NON-INTRUSIVE; status word[2], completed word[5] and fault word[4]
show image progress. Python reads of these PC files require no
second JTAG session, board interrupts, A53 halt or restart.
**Saved the exact two-snapshot Python heredoc commands** in
docs/P08_B4_2_FULL1024_PHYSICAL_RUNBOOK.md, plus reusable
scripts/p08_b4_2_monitor_mailbox_pc_only.py with synthetic
tests/test_p08_b4_2_monitor_mailbox_pc_only.py and no-board CI
coverage. This technique should be reused on future multi-hour
physical sessions; absent/partial temporary files are normal,
and DONE sentinel alone cannot establish completion.

**NEXT (do not prematurely merge):** plan P08-B4.4 controlled
**six repeated counterbalanced AB/BA/AB** cold-boot matched-source
Track A vs virtualized 27-core Track B sessions. Before any
new destructive operation, inspect independently verified B4.2
report's count/time distributions and accepted Track A 1024
physical latency-scope timing contract; design original
matched service-window CNTFRQ/CNTVCT normalization, selected
trace ordinal 1023 exclusion/instrumentation control and
trial/session variance estimates. Accept final comparative
latency only with 6 genuine physically verified paired sessions,
correct original source/mode and explicit uncertainty. No
energy or speedup claim yet; all new hardware sessions remain
separately gated. PR #53 on B4 branch DRAFT/UNMERGED,
stacked on B3 PR #52 DRAFT/UNMERGED.

## P08-B4.1 genuine original 1024 independent numerical oracle — OPERATOR ACCEPTED (2026-11-02)

Operator ran original independent P06-B2.4 scalar simulation for **64/64 distinct 16-image shards**, including final shard 63 ordinals **1008:1024**, preserving previously individually verified shard0 0:16. Then completed full no-overwrite 64-file merge using original signed B2.1 matched TRAIN-only ingress, frozen original network and SHA-coded routes and exact accepted B3 first16 reference. Genuine operator terminal:

```
P08_B4_1_ALL_1024_ORIGINAL_SCALAR_ROWS_ADMITTED=1
P08_B4_1_ALL_64_SHARDS_SHA_VERIFIED=1
P08_B4_1_ACCEPTED_FIRST16_SCALAR_REPRODUCED=1
P08_B4_1_PHYSICAL_1024_KV260_EXECUTED=0
```

Original external 64 shards:
`/home/dna/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z`.
Full original scalar oracle:
`/home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json`;
**operator SHA-256 `7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8`**.
The FULL genuine independent 1024 TRAIN-source scalar baseline is now ACCEPTED; no physical B4 inference yet. SHA pinned as mandatory frozen B4.2 offline admission (while keeping all 64 shards authenticated independently).

Operator additionally located genuine original full1024 B2.3 Vitis A53 ELF
`/home/dna/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf`
and matching linker map
`/home/dna/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.map`
with previously authenticated exact SHA pins `0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1` and `f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc`. Neither original ELF/map rebuilt nor modified. B4.2 demands **separate external canonical copies**, independent original ELF AArch64 PT_LOAD/accepted P03 XSA source recheck, all 64 original scalar shards, operator accepted B3 independent report and matched original P03 BIT/LTX before any JTAG.

**Next genuine hardware gate:** User locally stage canonical `p08_b4_original_full1024.elf`/`.map`, verify exact SHA, and run default read-only B4.2 `--mode preflight` with the real full1024 oracle. Only after ORIGINAL signed source/ELF/P03/B3 PASS, attempt new coldboot dedicated destructive 1024 KV260 JTAG session in fresh evidence dir with 8 separate explicit YES; independent after-run PSU 6-source+1024 neuronal FNV/timing verifier still required. Original boot/firmware/DMA DDR exclusive ownership remains UNPROVEN despite operator permission. No 1024 numerical physical result, energy, speedup or six-session A/B latency claimed. Root `LitReview.md`, accepted P07/B3/A, original 33 B2.4 and official MNIST TEST unchanged.

## P08-B4.2 complete full1024 physical runner SOURCE DEVELOPMENT — authentic local preflight and original 64-shard compute REQUIRED

Operator reports genuine **B4.1 shard 0/64** re-simulation from
original B2.4 frozen 33-asset model PASS:
`P08_B4_1_ORIGINAL_SCALAR_SHARD_INDEPENDENT_PASS=1`,
`P08_B4_1_VERIFIED_ORDINAL_RANGE=0:16` from
`/home/dna/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z/p08_b4_1_scalar_shard_00.json`.
No user evidence of remaining 63 genuine scalar shards, merged
1024 oracle SHA, newly signed full1024 Vitis physical-launch
ELF/map or B4 physical JTAG yet. This is a **source-development
checkpoint; NO full1024 physical execution claim**.

B4.2 now has SEPARATE fail-closed original 1024 source/CNTVCT/
physical-evidence tools on `agent/v3-p08-b4-fullscale` (stacked
DRAFT PR #53, B3 draft PR #52 unchanged):
- `scripts/p08_b4_2_physical_run.py`: read-only DEFAULT
  `--mode preflight`, requires original accepted B3 independent
  physical report SHA
  `b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11`,
  exact 64 original scalar shard SHA receipts, strict regeneration
  of full1024 signed oracle, all six SHA-authenticated original P02/
  routing/1024 raw sources, original B2.2 SHA header, accepted
  original P03 XSA/LTX/BIT and genuine **separate** full1024
  AArch64 ELF SHA `0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1`
  and map SHA `f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc`.
  Invokes original genuine ELF PT_LOAD admission. Exact 8 YES
  destructive consent flags mandatory; every real physical operation
  occurs in dedicated halted-A53 JTAG coldboot session and requires
  operator reboot afterward. Reuses ORIGINAL B3 full signed-six
  JTAG DDR stage and independent host 54 original model-core readbacks
  plus four source blobs before any new ELF download. Never
  copies B3 pilot16 A53 ELF to full1024 runner.
- `vivado/p08_b4_2_full1024_run_and_capture.tcl`: actual original
  B2.3 1024-image firmware ELF identity and 1024 terminal embedded
  string SHA checked; no new/simulated firmware. Initializes and
  physically zero-readbacks 256-byte mailbox, **1024×256B**
  original journal and independent 1024×256B A53 timing sidecar,
  polls genuine 256B mailbox until EXACT 1024/1024 terminal
  (DONE sentinel alone is NOT success; intermediate frame 1023
  progress still not terminal), captures all 524,288B neural/timing
  receipts + mailbox before final independent verification.
  A timeout, malformed/tampered terminal or reported A53
  error **fails closed**, retaining the source evidence and
  requiring reboot.
- `scripts/p08_b4_2_verify_full1024.py`: independent
  original first16 continuity, full1024 source, CRC/26tick
  1,010-neuron FNV, trained 10-vector spike output and
  classification, timestamp/6 disjoint service-phase validation.
  Reports only **UNVERIFIED physical provenance** by design.
- `scripts/p08_b4_2_independent_physical_verify.py`:
  separately repeats source/oracle/ELF SHA admission, authentic
  same-session P03/A53/PSU evidence and all six original DDR
  readbacks and zero-memory/captured journal checks before
  accepting first full1024 numerical & timing scope.
  Reports **single-session** original full1024 numerical parity
  only, **NOT** six-session Track A/B latency acceptance.
- `tests/test_p08_b4_2_full1024_physical.py`,
  `.github/workflows/p08_b4_2_full1024_physical_offline.yml`:
  actual Tcl mailbox-state replay, synthetic full 1024-row
  262144B journal+timing positive tests, multiple corrupted
  numerical/CRC/backtrack/terminal negative tests, source
  no-board admission and independent provenance fixture refusal.
  GitHub Actions native source CI **PASS** (no physical board).
- **Complete exact local operator instructions**:
  `docs/P08_B4_2_FULL1024_PHYSICAL_RUNBOOK.md`.

**Crucial physical B4 go/no-go:** shard0 PASS alone is NOT B4.1
complete. Generate and admit 63 remaining genuine original
B2.4 scalar shards and full1024 oracle first; locate previous
original B2.3 genuine Vitis ELF/map by their exact SHA and stage
copies under independent B4 canonical names; then check mandatory
B4.2 read-only operator preflight before running hardware. NO
fresh JTAG B4.2 attempted by agent, and no quantitative
full1024 KV260 latency, PL speedup, energy, 1023 selected full
raw neural trace or official TEST result yet. Independent boot/
DMA DDR exclusivity remains unproven, notwithstanding
operator consent. After one B4.2 physical pass, repeated six
coldboot AB/BA/AB Track A/B sessions and matched service-scope
analysis are still separate gated B4.4 work.

## P08-B4.1 full-scale original 1024-image physical Track B PREPARATION — source/CI pass, genuine local scalar computation PENDING

**Operator-accepted B3.1/B3.2 physical gate:** third actual
KV260 JTAG first16 session
`/home/dna/Thesis_Evidence/p08_b3_pilot16_physical_retry_20261102T053637Z`
reached 16/16 original B2.4 A53 terminal with separately authenticated
physical source P02 mutable/backup and frozen B4l/B4m/raw pixels,
physical neural/timing sidecars and original scalar precheck.
The *separate* independent physical verifier subsequently reported
`P08_B3_PILOT16_SIGNED_ORIGINAL_27CORE_MUTABLE_BACKUP_PHYSICAL_PASS=1`,
`P08_B3_PILOT16_REAL_16_FRAMES_ORIGINAL_SCALAR_NUMERICAL_FNV_PASS=1`,
`P08_B3_PILOT16_FULL_SERVICE_TIMER_INTERNAL_CONSISTENCY_PASS=1`.
Operator external independently verified report
`/home/dna/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json`
SHA-256 **`b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11`**.
**B3 first16 physical neural, spike-vector and 26-tick FNV parity
accepted on operator-supplied separate verifier evidence, with 16
internally consistent A53 timer rows.** This does NOT prove direct
full raw 26×1,010 trace bytes, 1,024-image Track B numerical
equality, a multi-session latency benchmark, exclusive boot/DMA DDR
ownership, speedup, energy or anything about official TEST.

**New independent B4 development branch:**
`agent/v3-p08-b4-fullscale`, stacked on the B3 draft branch, PR #53
**DRAFT/UNMERGED** (B3 PR #52 also unmerged). Do not alter
original 33 frozen B2.4 assets, original trained checkpoint,
P03 BIT/XSA/LTX, P07-B V3/B5, 6 accepted P08-A physical sessions,
operator B3 physical source/evidence, or `LitReview.md`.

**B4.1 target** independent numerical reference for EVERY one
of the same 1024 original TRAIN-only matched Track A validation
pixels, including 26 ticks, all 1,010 neurons' deterministic FNV
fingerprint, 10-vector spike readout and original 27-core 702
physical-dispatch comparison geometry. This is **not** the official
MNIST TEST dataset; keep TEST sealed. An original full1024 A53
B2.3 candidate exists *as a distinct 1024-image firmware binary
source* but has not been freshly physical-run or approved for full
B4 latency sessions. Never replace the accepted B3 first16 ELF.

New **PC-only** scripts:
- `scripts/p08_b4_1_scalar_shard.py` computes one 16-frame original
  B2.4 independent scalar segment at a time using the **same**
  original P06-B2.4 monolithic neural simulator and accepted P08-B2.4
  `pure_reference()` FNV/counter routines as the proven B3
  16-frame reference. Each invocation reauthenticates original 33
  frozen assets, original B4m routes, A3.2 first1024 canonical
  held-out TRAIN identities, all 1,024 raw pixel/ingress metadata
  and signed wire hash ledger; re-encodes all 16 selected originals.
  Shard 0 MUST reproduce the accepted signed first16 scalar frame
  rows byte-exact; 64 nonoverwriting external shards are required.
- `scripts/p08_b4_1_merge_scalar_1024.py` demands exactly 64
  consecutive SHA-derived original 16-frame reports, no duplicate,
  altered, extra or missing shard, all 1,024 immutable original
  ingress source identities/hashes, independent 16-model-trace FNV
  fields, original fully signed first16 reference. Produces
  separate no-overwrite full1024 JSON and full list of independent
  shard SHA receipts. **Zero physical board contact**.
- `tests/test_p08_b4_1_scalar_1024.py` and
  `.github/workflows/p08_b4_1_fullscale_scalar_offline.yml`
  run synthetic full 1,024 row positive and nine malformed-source
  negative admission checks. Native CI **PASS**. Synthetic
  test artifacts MUST NOT be mistaken for real independent oracle.

**B4.1 acceptance boundary:** genuine *operator-local* shard0 must
match signed first16, then operator must generate all 64 shards
from original frozen sources and merge a completely authenticated
1024-ordinal scalar JSON, report SHA256. The code/CI source PASS
alone does **not** mean original full1024 scalar computed or 1024
images run on KV260. B4.1 on local execution PENDING.

**Planned remaining B4 phases (gated; NOT yet implemented/accepted):**
B4.2 distinct **real Vitis** 1024-image A53 ELF/map full
range/heap/stack/load admission, output allocation, non-overlap
and launch-poll verification, 1024x256B CRC journals and timing
sidecars and exact terminal count; strict JTAG physically authenticated
capture and new destructive authorization. B4.3 physical full1024
independent scalar FNV + classifier parity and per-image full
service CNTVCT/CNTFRQ checks before admitting ANY latency result.
B4.4 repeated controlled **cold-boot, AB/BA/AB** physical comparison
protocol, original Track A baseline scope and instrumentation parity,
scope-selected trace image 1023 handled separately to avoid
instrumentation-induced bias, analysis of medians/tails and
per-phase timing. No unproven pure-PL speedup or energy claims.
All actual B4 physical board calls remain **NOT RUN**.

## P08-B3.1 third physical KV260 run: FIRST actual 16/16 terminal & scalar precheck PASS — independent evidence audit NEXT

Operator reports third **dedicated fresh-session KV260 JTAG** run
successfully completed physical P03.2c PS-MMIO bitstream programming
and VIO reset release, identified physical PSU DDR target, staged and
physically read back **all 27 original mutable P02 core records and all
27 independently staged immutable backup records (54×512KiB)**,
original B4l 16KiB descriptor, original B4m 896KiB input routes and
80KiB output routes and the matched original 1,024-image raw-pixel
pool. Tcl reported six physical source transfers byte-exact PASS.
This third run progressed *beyond both earlier aborted sessions*.

Genuine operator console further reports physical zero/readback of
all three dedicated result regions, exact **SHA-pinned first16 A53
ELF downloaded to real hardware**, A53 terminal 16/16 physically
observed, real 256-byte mailbox + 16×256B neural journal +
16×256B A53 timing journal physically captured, and the *separate
preliminary untrusted-file scalar verifier* PASS
(`P08_B3_FIRST16_BOARD_RESULT_NUMERICAL_PRECHECK_PASS=1`).
This is **new actual physical 16-image inference evidence**, not
merely PC mock data or original P07 one-frame experiment.

**Acceptance boundary remains explicit:** independent verification of
same-session physical provenance and all 16 neural/trace-fingerprint
records is **PENDING**, because the printed terminal ends with
`P08_B3_PILOT16_INDEPENDENT_PHYSICAL_PROVENANCE_VERIFICATION_PENDING=1`.
The genuine *third-session* external evidence path was not specified
by operator (do NOT infer it from previous second-session readback path
`.../p08_b3_pilot16_physical_retry_20261102T052232Z`).
User should identify newest `p08_b3_pilot16_physical_retry_*`
evidence directory whose `stage.txt` equals
`P08_B3_FIRST16_JTAG_RESULTS_MATCH_SCALAR_PRECHECK_INDEPENDENT_PHYSICAL_ATTESTATION_PENDING_REBOOT_REQUIRED`,
then execute **PC-only**
`scripts/p08_b3_pilot16_independent_physical_verify.py` against
original frozen PC stage, scalar oracle, exact genuine ELF/map,
accepted P03 hardware reports, and B2.2 reset pins. Require
`P08_B3_PILOT16_REAL_16_FRAMES_ORIGINAL_SCALAR_NUMERICAL_FNV_PASS=1`
and the separate independent report before calling accepted physical
numerical fingerprint parity. Store the report SHA. Reboot/power-cycle
KV260 after the JTAG attempt; do not resume discarded Linux.

No current physical 1,024-image Track B latency benchmark or
energy/speedup claims; no direct full raw 26×1,010 neuron-trace
byte equality obtained. DDR boot/firmware/RPU/DMA ownership remains
independently **unproven**, although user has accepted the experimental
risk. No changes to frozen original B2.4 33-asset model, original
P03 bit/XSA, accepted Track A six sessions, P07-B accepted V3/B5,
root `LitReview.md` or sealed official MNIST TEST. Next after
independent 16-frame pass: freeze this first verified physical
pilot as B3 acceptance evidence, inspect timestamp distributions
without calling them a 1,024-image latency result, then plan the
scalable controlled Track B physical matched-source latency
experiment and A-vs-B comparison.

## P08-B3.1 second physical JTAG session — all 6 original DDR readbacks PASS, host Python key error before A53 launch

Operator second dedicated KV260 run **completed physical original frozen staging**:
accepted P03 PL bitstream/VIO release pass, physically selected PSU,
all 27 original **mutable** B2.4 P02 core 512KiB physical readbacks
PASS, all 27 independent **immutable backup** P02 core readbacks PASS,
and signed 16KiB B4l bindings, original 896KiB B4m input routes,
80KiB B4m output routes and original matched 802,816B 1,024 raw
TRAIN-derived images all reported physical byte-for-byte PASS.
Tcl emitted `P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1`
and `P08_B3_PILOT_ORIGINAL_FROZEN_SIX_TRANSFERS_STAGED_REBOOT_REQUIRED=1`.
These are authentic *operator-provided* physical staging logs; the
separately independent host verification was NOT yet completed.

Despite full Tcl staging success, host Python runner halted with
`P08_B3_PILOT16_PHYSICAL_NO_GO=PosixPath('.../original_27core_backup_source_14155776.bin')`,
a `KeyError` because `scripts/p08_b3_pilot16_physical_run.py`'s
`readback_original(stage,readback)` indexed
`source.EXPECTED_SHA[original]` where `original` was a full
`Path`, while SHA keys are filenames (`str`).
Both occurrences fixed by retaining `original_name=source.FILES[0][0]`,
`original_path=stage/original_name`, and
`source.EXPECTED_SHA[original_name]`.
**No new pilot16 ELF was downloaded, no inference executed,
no neural parity or latency verified.** JTAG touched DDR, so **reboot
required and no old-Linux resume**.

New synthetic host-only regression independently exercises exact
`readback_original` on **54 full 512KiB P02 physical-copy fixture files**
plus all 4 source staged payload fixtures. It asserts all 6 source
SHA results and injects backup-core and route corruption to confirm
fail-closed behavior. Historical full fake-PSU Tcl six-stage regression
remains intact. **All seven P08 native CI workflows GREEN**.
No accepted original frozen B2.4 assets, P07-B, P08-A physical
sessions, original P03 BIT/XSA or root `LitReview.md` touched.
Exact operator new PILOT16 ELF SHA
`29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3`
and original scalar first16 oracle SHA
`13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271`
remain intact; original TEST sealed.

NEXT: use fixed Python `readback_original` on **the second
session's preserved external `source_physical_readback/`** files
as an offline, read-only staging-forensics check before another
destructive run. A PASS retrospectively validates saved source
readbacks but **cannot revive the old JTAG session**. After reboot,
run only a NEW dedicated session with new external evidence root,
full fresh six-source staging/readback and subsequent separately
SHA-pinned A53 ELF launch/16 original held-out TRAIN validation
inferences. Independent 16 journal, timer, terminal and scalar
FNV verification still pending. Risk of unproven independent
PS/boot/RPU/PL-DMA/firmware DDR owner remains acknowledged, NOT solved.

## P08-B3.1 first hardware attempt (2026-11-02 UTC): Tcl receipt interpolation abort, no A53 launch

Operator initiated **first physical KV260 P08-B3 pilot16** dedicated JTAG
execution with genuine user-built first16 ELF SHA
`29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3`.
External session evidence
`/home/dna/Thesis_Evidence/p08_b3_pilot16_physical_20261102T050721Z`.
User-provided genuine physical console establishes accepted P03 PL
shell programmed and VIO reset released, PSU physical target selected,
all **27 original mutable 512KiB P02 context copies** read back
byte-exact, all **27 original independent 512KiB reset-backup P02
copies** read back byte-exact. This is useful hardware staging evidence,
**NOT a complete six-payload readback, NOT an A53 ELF launch, and
NOT a 16-image inference/latency result**.

**Observed failure after these two full P02 readback sets:**
`P08_B3_PILOT_STAGING_FAILED_REBOOT_REQUIRED=1`,
Tcl `can't read "name_BYTE_EXACT_PASS": no such variable` at
`vivado/p08_b3_pilot16_six_ddr_stage.tcl` dynamic route/binding/raw
source status emission. Root cause was Tcl interpreting
`$name_BYTE_EXACT_PASS` as a single nonexistent variable, rather than
a base filename variable followed by a literal suffix.
Corrected to `\${name}_BYTE_EXACT_PASS` using Tcl braced variable
expansion (only new P08 B3 staging Tcl source modified).
NO ELF downloaded and NO inference in failed session.
Even if partial later source write occurred, its session is NOT reusable.
**Power-cycle/reboot KV260; never resume halted old Linux**.

Added host-only end-to-end `tclsh` fake-PSU DDR simulation regression
`test_six_original_ddr_stage_full_mock_xsdb_byte_roundtrip`: exercises
ALL 54 original mutable/backup 512KiB P02 core stages/readbacks and
4 other original source transfers and exact status markers against
synthetic host-only stage data. It then deliberately restores the
incorrect Tcl variable and proves the old failure would be caught.
CI B3.1 and all other P08 native workflows **PASS**. NO new Vitis
A53 source/ELF/map, original frozen 33 B2.4 assets, prior accepted
P07-B/A evidence, root `LitReview.md` or official TEST changed.

**Next:** after local pull and passing B3.1 full fake staging regression,
take a brand-new dedicated rebooted JTAG session with a NEW external
evidence directory. Re-run all six original source transfers and
independent same-session readbacks from scratch. Same exact original
pilot16 ELF and source stage should be reused; do not manually continue
from the failed B3.1 partial stage or claim pilot success based on
P02-only PASS. Independent first16 classifier/spike/FNV results remain
unmeasured, firmware/boot DDR owner risk remains unproven, and explicit
per-run consent flags/reboot recovery still apply.

## P08-B3.1 real JTAG original 16-image physical pilot pipeline — 2026-11-01

Operator reports **genuine separate original B2.4 first16 Vitis 2025.2
A53 ELF build and oracle admission PASS**, with ELF SHA
`29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3`,
map SHA `9d2106d82347385e936bb27176aa8f50a332beb3f13c3ca8e182890a689c674b`,
selected original first16 scalar oracle SHA
`13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271`.
These are operator **offline** observations. There has been NO
P08-B3 physical board attempt or measured inference yet.

New [B3.1 original first16 dedicated cold-boot JTAG runbook]
(docs/P08_B3_1_FIRST16_DESTRUCTIVE_JTAG_RUNBOOK.md) and source:
`scripts/p08_b3_pilot16_physical_run.py` defaults to **READ-ONLY HOST
PREFLIGHT**, authenticates original 27×512KiB and separate backup
destination, all five frozen source SHA payloads/six proposed transfers,
separate exact user-built pilot ELF/map SHA and already accepted
original P03 BIT/XSA/LTX, new 16 scalar oracle. Destructive
`--mode execute` requires **eight individually explicit operator
YES flags**, including A53/Linux discard, unproven PS/boot/firmware/DMA
ownership RISK acceptance, all six DDR transfers, PS/PL programming,
low DDR ELF and sidecar overwrite and mandatory reboot.
New `vivado/p08_b3_pilot16_six_ddr_stage.tcl` physically reads
back and validates **both full 27×512KiB original neuron contexts**
(mutable and independent immutable backup) and original
B4l metadata/B4m route tables/full 1,024-source raw pool
before any ELF download; Python independently authenticates every
PSU readback byte SHA within same dedicated session.
New `vivado/p08_b3_pilot16_run_and_capture.tcl` zeroes and reads
back new 256B terminal mailbox, 4KiB original first16 neural and
4KiB timer journals; downloads exact pilot16 SHA-pinned A53
ELF only after physical source readbacks and catches bounded
first16 PASS versus timeouts/faults; captures exact physical 16 journals
and mailbox after halting A53. Independent
`scripts/p08_b3_pilot16_independent_physical_verify.py`
checks authentic XSDB/Vivado logs, original 6 source readbacks,
all 16 original scalar spike-count/trace FNV and timing receipt.
Neither fingerprint comparison nor successful PC-only gate proves
full RAW physical neuron trace, standalone firmware memory ownership,
calibrated 1,024 latency, speedup or energy.

**New native negative/default-deny CI PASS; operator PC-only dry-run
preflight PENDING and destructive physical execution NOT AUTHORIZED by
preflight.** In particular verified ELF low-DDR PT_LOAD nonoverlap does
not prove independent PS Linux, FSBL/TF-A, U-Boot, PMUFW, RPU, CMA or
PL DMA ownership. User must review/acknowledge this risk and agree to
discard Linux / reboot after every attempted JTAG. The user request
to progress toward physical test did not itself resolve unproven DDR
owners. No P08-B3 physical JTAG action executed by agent; original
P07-B V3/B5 evidence and untouched original 33 B2.4 assets, six
accepted Track A latency sessions, protected root `LitReview.md`
and original B official MNIST TEST remain unchanged.
**P09 and all energy/speedup claims deferred.**

## P08-B3.0 bounded original B2.4 first16 A53 pilot source and safe offline stage — 2026-11-01

Operator genuine original P08-B2.4 independent scalar **first16 PASS**,
including reproduction of the first 3 frozen B2.3 scalar witnesses:
external `p08_b2_4_original_first16_scalar_20261102T042201Z.json`
SHA `13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271`.
Physical numerical parity remains **UNTESTED**.

New [bounded original 27core pilot ELF and offline staging contract]
(docs/P08_B3_PILOT16_OFFLINE_ELF_AND_STAGE.md): **separate**
`p08_b3_pilot16_a53.c` with original B2.4 27-core/3-slot/26-tick engine
and 27x512KiB source-SHA reset, but bounded **exactly 16 images**;
distinct application identity and terminal receipt.
It still SHA-authenticates **all original 1,024** raw pixels to avoid
changing matched Track A/B population. A separate Vitis 2025.2
standalone A53 builder and **PC-only** ELF PT_LOAD / map / accepted
first16 scalar-report SHA admission are provided.
PC-only original B2.4 source packaging independently verifies original
33 frozen model assets, 27 original P02 context SHA, original
16KiB axon bindings, signed 80/896KiB routes and 802,816-byte raw
pool, then writes a no-overwrite **five immutable-copy file** transfer
proposal with two proposed copies of identical original 27core bundle
in disjoint mutable/backup DDR slots. No JTAG command is issued.

**Genuine new pilot16 ELF+map not built by operator yet.**
No physical proof of PS Linux/FSBL/TF-A/RPU/PL DMA/stack and reserved DDR
ownership, no independent same-session physical DDR/model/route/backup
readbacks, no operator authorization for destructive JTAG takeover and no
pilot hardware neural/latency measurement. Original **1024-image**
B2.3 ELF must never substitute for this separately bounded pilot.
Original accepted P07-B V3/B5, B2.4 33 frozen files, Track A six
sessions, root `LitReview.md` and original official TEST are
untouched. **P09 and numerical/speedup/energy claims deferred.**

## P08-B2.4 original B2.4 matched first16 scalar oracle and untrusted record gate — 2026-11-01

Operator reports **fixed original 1,024-frame C encoder PASS** plus
genuine Vitis P08-B2.3 new A53 image-only ELF built, real linker map
and `PT_LOAD` low-DDR static non-overlap audit PASS.
ELF SHA `0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1`,
map SHA `f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc`.
**No DDR ownership proof or physical FPGA deployment.**

[P08-B2.4 original scalar first16 and record contract]
(docs/P08_B2_4_FIRST16_SCALAR_AND_RECORD_GATES.md) adds independent
original frozen B2.4 first 16 of the *exact same* 1,024 held-out
TRAIN-derived source and a new external no-overwrite numerical oracle
generator. It reauthenticates original B2.4 33 assets, original route
tables, accepted P08-A source and original P08-B2.1 raw/wire SHA,
reproduces first three independently signed B2.3 scalar numerical
witnesses, simulates original frozen scalar 25+1 ticks and derives
per-image classification, all 10 spike counts, external CURRENT/source
spikes/captured+NEXT packets, and full 26×1,010 trace FNV.
**Genuine first16 scalar oracle run on operator workstation PENDING.**

Separate `p08_b2_4_verify_untrusted_first16.py` rejects a mismatched
original numeric receipt, incorrect timestamp accounting, altered
per-frame SHA256, wrong journal CRC, malformed terminal mailbox, frame
order/length and truncated/incomplete 16 evidence. Its result *cannot*
establish actual physical provenance, because same-session JTAG
readback/DDR/ELF evidence is NOT YET BUILT. CI synthetic native
26 negative/positive tests PASSED. This is a **source-only** offline
checkpoint. Original P08-B2.3 ELF is **1024-image**, not safe to use for a
16-image physical pilot. A separate 16-image A53 pilot firmware ELF/map,
verified hardware DDR source ownership including untouched first original
27 backing contexts and independent backup and signed XSDB readback
procedure remain to build before explicit operator destructive approval.
Accepted P07-B/A and frozen original 33-asset B2.4, original 1024
Track A runs, root `LitReview.md` and official Track B TEST SEALED.
**No P09 or physical speedup/energy claim.**

## P08-B2.1 original-route C hash corrected; new B2.3 image-only A53 offline build candidate — 2026-11-01

Operator **P08-B2.2 SHA-pins gate PASSED**: 27 original
SHA-pinned initial P02 cores, original 14,155,776B aggregate SHA
`3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`;
external original context header SHA
`5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171`.
The operator's B2.1 C all-1024 verification discovered
`P08_B2_NATIVE_ORIGINAL_896K_ROUTE_SHA_NO_GO`; **P08 new C route
SHA constant was hand-transcribed incorrectly** (final 16 bytes).
C source now matches accepted immutable 896KiB original B4M route
SHA `380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8`.
The original immutable route table and accepted Python stage passed;
real C 1024-frame revalidation is **PENDING** after correction.
CI now checks literal C/Python SHA equivalence and positive
1,024-frame native C P06B13I1 wire parity using a strictly
test-only synthetic 896KiB route with separate temporary SHA.

New [P08-B2.3 independent image-only A53 application and offline Vitis
build contract](docs/P08_B2_3_IMAGE_ONLY_A53_OFFLINE_VITIS.md): separate
`p08_b2_3_image_only_a53.c` uses genuine P07 B4m 26-tick original
engine (702 dispatches, 3 slots), per-image original 27-context
SHA restoration/reinit, original 1,024 raw-pixel pool and bound 27-core
ingress, CNTVCT/CNTFRQ full-A53 service timestamps, raw+encoded SHA
and neural-result journal, timing sidecar outside measured interval.
New separate Vitis 2025.2 offline-only app builder/source stage and
read-only genuine ELF/low-DDR PT_LOAD admission; **not yet built
by local Vitis, no new A53 ELF/map accepted**. Native C syntax and
synthetic ELF gate only, no board contact. Genuine B1.3 C all-1,024
local parity and **Vitis real ELF/map PT_LOAD acceptance pending**.
No destructive JTAG, original-backed DDR physical ownership,
oracle parity on actual hardware, detailed tick ELF, selected full
raw trace, or P08-B 1,024 physical inference/latency accepted.
Official Track B TEST SEALED; original Track A six sessions,
P07-B original V3/B5 ELF, original frozen B2.4 and root
`LitReview.md` remain unchanged. **P09 deferred.**

## P08-B2.2 source-only reset/timer development — 2026-11-01

The operator reported **P08-B2.1 host 1,024 original-B ingress staging
PASS** (802,816B raw pool; 123,216B frames; 1,024 SHA rows) in new
external folder `p08_b2_1_original1024_20261102T003256Z`; full
independent native-C 1,024 wire parity has not yet been shown. File
hashes are recorded in
[reset source contract](docs/P08_B2_2_CONTEXT_RESET_AND_METER.md).

P08-B2.2 adds **new** isolated C11 original 27×512KiB SHA-bound
context-restoration primitive with all 27 backup hashes checked before
the first write, cache-coherent destination SHA check, permanent poison
on any failed reset; a bounded CNTVCT/CNTFRQ seven-boundary six-phase
full-A53-service meter; a no-overwrite original frozen 33-asset
SHA-pin header generator and 27×512KiB native fake-DDR two-image
regression. **New source in CI; operator local source validation pending.**
No real A53 app/ELF, physical DDR owner, backup readback, original 1024
scalar oracle, signed timing sidecar, JTAG launch, or B physical latency
is yet accepted. The 26-tick meter INCLUDES nested P03 trace hooks
during the dispatch; no artificial isolated dispatch/pretrace claim.
Separate full P08-B app and genuine Vitis ELF work remain to implement
before any operator-approved destructive B3 pilot. Original A six
latency sessions, B2.4 frozen model, B5 acceptance and sealed official
MNIST TEST unchanged. **P09 deferred.**

## P08-B2.1 source-only candidate: authenticated original 1024 B ingress — 2026-11-01

The operator reported a genuine local P08-B1 `MATCHED_DATASET_OFFLINE_PASS=1`
on the original Track A first1024 stage and accepted B2.4 freeze, with
zero B training index overlap. **B1 source/dataset gate is accepted for
continued development**, although the assistant has not re-opened the
operator-local JSON. New separate [P08-B2.1 original scaled ingress and
DDR design](docs/P08_B2_1_ORIGINAL_MATCHED_INGRESS_AND_DDR_CANDIDATE.md)
adds a strict, no-overwrite PC-only 1024 raw-pixel 802,816B pool, original
P06B13I1 27-core frame hash manifest, strict C11 original 896KiB SHA-bound
route/ingress builder and native 1,024-frame cross-encoder verifier.

**B2.1 operator local validation pending.** The newly proposed
27×512KiB backup, raw-pixel/journal/timing DDR spans are statically
non-overlapping only. **B2.2/B2.3 NOT built**: no new A53 firmware,
per-image neural state reset, neural oracle/sidecar/ELF/map or independently
proved DDR owner. No authorized destructive B3 physical session or
P08-B latency has occurred; original TRAIN-derived stage and B2.4 freeze,
P07-B hardware/ELFs, Track A accepted measurements, root literature,
and sealed Track B official TEST remain untouched. **P09 deferred.**

## P08-B1 launched: matched 27-core latency source contract — 2026-11-01

**P08-B STARTED (B1 PC-ONLY SOURCE CANDIDATE; LOCAL OPERATOR VALIDATION PENDING).**
Development branch `agent/v3-p08-b-scaled-latency` from accepted main
`2c9767ba6f6e001b52b14ff4285ae60c2d7ab47b` contains
[the new B1 matched-dataset/latency contract](docs/P08_B1_MATCHED_TRACK_A_LATENCY_CONTRACT.md),
a strict offline original Track A 1,024-image source/ledger audit with
read-only 33-asset B2.4 freeze validation, and negative native tests.
Both Track A P07-A4 and Track B P06-B2.2 training sources pin the SAME
canonical 50k/10k TRAIN-derived partition; seeded first1024 membership
has zero overlap with Track B training. Stage pixel and original freeze
file hashes must still be independently checked on the local workstation.

**B1 gate:** user must run native tests and original source/stage audit,
report the actual no-overwrite output, and accept the dataset provenance.
**B2 NOT started:** implement a distinct instrumented scaled A53
image-service/tick runtime, arbitrary-image frozen scalar oracle, safe
per-image 27-record restoration, nonoverlapping DDR buffers, external
Vitis ELF/map and strict read-only preflight. **B3 NOT approved:**
operator-authorized destructive cold-boot 16-frame KV260 pilot only
after B2 passes. **B4 future:** matched six independently cold-booted
A2.1/A2.2-style paired 1,024-frame runs AB/BA/AB, ordinary frames
0–1022, frame 1023 selected trace, full independent numerical parity
before latency. **B5 future:** immutable physical results and P09 handoff;
branch merge only by separate operator permission.

**No new physical measurements, new FPGA bitstream, official MNIST
TEST access, energy sampling, standalone scaled latency or P09
comparison are claimed.** Original P07-B and Track A freeze and root
`LitReview.md` remain untouched. The preserved historical
"P08-B not started" statement below records P07-B closeout time,
not the present development branch status.

## P07-B final acceptance and GitHub integration — 2026-11-01

**P07-B COMPLETED, FORMALLY OPERATOR ACCEPTED AND MERGED INTO MAIN.**
P07-B.4's original trained 27-core/3-slot KV260 board-local inference,
P07-B.5's independently accepted 5 genuine physical sessions and
840,320-byte original TRAIN0 full raw-neuron physical/scalar exact parity,
and P07-B.6's accepted immutable source/five-session archive freeze,
independent portable archive audit, and B6.3 final operator handoff
are **closed**. The original explicit acceptance report
`/home/dna/Thesis_Evidence/p07_b6_3_final_operator_accepted_20261101T233410Z.json`
reported `P07_B_complete=true`, `P08_B_started=false` and
`official_MNIST_TEST=SEALED_NOT_ACCESSED`.
[Bounded real P07-B operator closeout ledger](docs/P07_B6_3_2026_11_01_FORMAL_OPERATOR_ACCEPTED_P07_B_CLOSEOUT.json).

**Final main integration occurred afterward, with three normal Git
merge commits, in correct dependency order:**
PR #49 `48b5db1f6430e594b2fce03aefa9136935249546` →
PR #50 `1328e2cd04ae43f7dde1aa3e898f81be2c1ac6ea` →
PR #51 `a59fa21eb5ffff8586c33c65b291a6ea2bfca6e4`.
The independent original main-only `LitReview.md` **was not
overwritten**: its exact Git blob SHA remained
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e` after **each**
merge. [Verified post-merge integration provenance](docs/P07_B_2026_11_01_POST_MERGE_INTEGRATION_ACCEPTED.json).

**Acceptance bounds remain unchanged:** official MNIST TEST still
SEALED, external board power cycles only operator-attested,
firmware/Linux/DDR exclusive ownership unproven, every individual
routed packet word not numerically traced, and no claim of fully
asynchronous hardware equivalence. The physical raw complete equality
was proven for the original selected TRAIN0 26×1010 neurons;
original four physical V3 runs (TRAIN 0/1/2/0) proved full 26-tick
fingerprints and counters. **P08-B is NOT started**; a separate
benchmark/test protocol must be explicitly accepted before any
new measurements or official TEST use. Earlier roadmap entries below
are a preserved chronological history and may describe work that
was pending at their time.

## Purpose

FPGA-v3 is the next research/development line for the Loihi-1 architectural digital twin.

v3 begins from the final accepted FPGA-v2 state at:

```text
a9329caa064fee3876d69fbbe6c626ac035e67b5
Close P08 and complete FPGA-v2 roadmap
```

The v2 tree remains the frozen accepted record. v3 may reuse and modify v2 implementation code, but new v3 results must not retroactively change or weaken the accepted v2 evidence.

The central v3 goal is to move from a host-assisted FPGA execution model to a substantially board-local KV260/K26 execution model while increasing physical test coverage and improving benchmark comparability.

The inherited Loihi-1 architecture contract is initially:

```text
docs/LOIHI1_TARGET_SPEC.md
```

P01 will decide whether v3 needs a separate amendment/addendum for board-local execution and any new modeled Loihi features. Architectural fidelity claims remain distinct from FPGA implementation choices.

## v3 research goals

### 1. Board-local execution

Move algorithmic execution ownership onto the KV260/K26 as far as practical.

The target execution hierarchy is:

```text
PC / development host
  -> provisioning, launch, optional debug, result collection only

KV260 Processing System (PS)
  -> deployment/runtime control
  -> logical-core scheduling
  -> routing/barrier ownership where appropriate
  -> DDR-backed logical-context management

KV260 Programmable Logic (PL)
  -> Loihi-like core execution
  -> resident-context datapath
  -> packet/event datapath
  -> high-throughput DDR movement where justified

K26 DDR4
  -> non-resident logical-core backing contexts
  -> deployment/runtime buffers
  -> test/input/output data as required
```

The external PC must not be required in the algorithmic timestep loop for the final v3 runtime.

### 2. More physical validation

v2 proved the architecture with strong Python/compiled-software validation plus representative physical K26 dispatches. v3 should move substantially more of the regression and application validation onto the board itself.

The target is not to eliminate the Python golden model. The target is to use it to generate/freeze expectations while the KV260 executes most accepted regression/application runs end-to-end.

### 3. Better published benchmark

Select a published MNIST SNN whose architecture is reproducible enough to avoid the ambiguity encountered with the NxTF reconstruction.

The selected benchmark should preferably publish or provide:

- exact input preprocessing/encoding;
- exact layer dimensions;
- exact neuron counts;
- exact connection/synapse structure;
- neuron equations and parameters;
- inference timestep/phase schedule;
- readout rule;
- training procedure;
- source code and preferably reproducible weights/checkpoints;
- accuracy;
- neuromorphic-hardware mapping details where available;
- latency/power/energy methodology where available.

A benchmark is not accepted merely because its headline neuron or parameter count is known.

Initial candidate for source audit, **not yet selected**:

- Alpha Renner et al., "The backpropagation algorithm implemented on spiking neuromorphic hardware," Nature Communications (2024), DOI 10.1038/s41467-024-53827-9.
- The paper describes a cropped-MNIST feed-forward inference module with 400 input neurons, 400 hidden neurons, and 10 output neurons, explicit Loihi CUBA parameters, a four-timestep reduced inference path, published Loihi inference measurements, and public implementation code.
- P06 must independently audit the paper/code before this project treats it as the v3 benchmark.

### 4. Latency, throughput, power, and energy characterization

v3 should measure real board-local inference rather than extrapolating a single core dispatch into sample latency.

Measurements must keep distinct:

- algorithmic timesteps/phases;
- PL clock cycles;
- logical-core dispatch time;
- context page-in/page-out time;
- PS scheduling/routing time;
- complete timestep time;
- complete sample latency;
- steady-state throughput;
- idle/static board power;
- active board power;
- dynamic power when explicitly defined;
- energy per inference.

The KV260 SOM power telemetry may be used for reproducible board-level measurements, with an external meter retained as an optional validation path.

### 5. Multiple physical HLS execution engines — deferred

Multi-engine execution remains a valid v3 optimization direction, but it is
**deferred from the current critical path** until the single-engine DDR-backed
board-local architecture is implemented and characterized.

The reason is not primarily HLS arithmetic cost. Accepted routed evidence
suggests the compute engine itself is modest relative to K26 logic/DSP capacity.
The limiting issue is the resident-context memory architecture:

- the accepted three-context fabric uses true-dual-port URAM banks;
- one port currently services the HLS compute path and the other services
  host/integration/maintenance access;
- a two-engine design could potentially repurpose both ports for compute during
  a parallel wave, but page movement and packet/event maintenance would then
  need explicit arbitration or serialization;
- three or more simultaneous engines would require a deeper memory redesign,
  such as per-slot banking, selective replication, or moving some storage
  classes out of URAM.

Because v3's primary research goal is first to eliminate PC-owned paging and
control, introducing that memory redesign now would mix two independent
questions: **board autonomy** and **compute parallelism**.

The deferred optimization should be reconsidered after P02/P03/P08 measure the
single-engine system and show whether HLS compute serialization is actually a
dominant end-to-end latency term.


---

## Development/acceptance rules

Status meanings:

- **Complete** — deliverables are implemented, reproduced independently, and accepted.
- **In progress** — active work exists but acceptance is pending.
- **Planned** — agreed work not yet started.
- **Blocked** — waiting on a dependency/decision.
- **Deferred** — intentionally outside the current critical path.

For every major sub-milestone:

1. implement on a dedicated branch;
2. run the relevant automated/software/hardware gates;
3. provide exact reproduction commands;
4. stop for independent verification before merge;
5. record acceptance evidence only after independent verification succeeds;
6. merge only after explicit approval.

A passing developer-side test does not by itself close a hardware/software milestone.

---

## Phase summary

| ID | Phase | Status |
|---|---|---|
| P00 | Establish v3 baseline, directory, and roadmap | Complete |
| P01 | Define board-local architecture, ownership, and v3 contract | Complete |
| P02 | Move non-resident logical contexts into K26 DDR | Complete |
| P03 | Build autonomous PS-resident scheduling/routing/barrier runtime | Complete |
| P04 | Add multi-engine parallel logical-core execution | Deferred |
| P05 | Build board-local regression, observability, and data-path hardening | In progress (P05.2; P05.1 accepted) |
| P06 | Audit and freeze an exact published MNIST benchmark | In progress (Track A accepted; Track B gated by P08-A) |
| P07 | Execute the frozen benchmark end-to-end primarily on KV260 | In progress (A1/A2 accepted; A3 validation pending) |
| P08 | Characterize latency, throughput, power, and energy | Planned |
| P09 | Final source-backed comparison and v3 closure | Planned |

---

# P00 — Establish v3 baseline, directory, and roadmap

**Status:** Complete  
**Accepted:** 2026-10-05

## Goal

Create an isolated v3 development tree from the final accepted v2 implementation without changing the v2 record.

## Deliverables

- copy the accepted `Loihi_Digital_Twin/v2/` tree into `Loihi_Digital_Twin/v3/`;
- preserve the existing v2 source/HLS/RTL/Vivado/test functionality as the initial v3 baseline;
- add this v3 roadmap;
- replace the copied v2 README with a v3 baseline README;
- update the parent `Loihi_Digital_Twin/README.md` to identify v2 as the accepted baseline and v3 as active follow-on development;
- record that inherited package/module names may still contain `v2` until a later deliberate compatibility migration.

## Acceptance

P00 was accepted after independent verification confirmed:

- the copied implementation matches the accepted v2 baseline except for intentional v3 documentation changes;
- all inherited `docs`, `examples`, `hardware`, `hls`, `rtl`, `scripts`, `src`, `tests`, and `vivado` Git subtrees are identical to v2;
- `pyproject.toml` and `.gitignore` are identical to v2;
- no accepted v2 files were modified;
- the inherited v3 regression suite completed at 100% with 67 passing test indicators and no reported failures/errors.

Primary acceptance record: `docs/P00_ACCEPTANCE.md`.

---

# P01 — Board-local architecture, ownership, and v3 contract

**Status:** Complete  
**Accepted:** 2026-10-05

## Research question

What is the cleanest PS/PL/DDR partition that removes the PC from the algorithmic execution loop while preserving v2 architectural semantics?

## Proposed default ownership

Unless measurements justify a different split:

- **PS/A53:** control plane, deployment loading, logical-core scheduling, global barrier, cross-page routing bookkeeping, run control, result collection;
- **PL:** Loihi-like core arithmetic, resident-context memories, packet/event datapath, performance counters, and bulk memory movement support;
- **DDR4:** backing images for non-resident logical cores and runtime buffers;
- **PC:** build/deploy, initial provisioning, optional debugging, and post-run collection only.

This is a project implementation partition, not a claim about Loihi's physical microarchitecture.

## Resolution

P01 closed on the ownership/interface architecture in
`docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

The detailed implementation contracts originally sketched as P01.2/P01.3 are
intentionally re-homed to the phases that implement them:

- **P02.1 — DDR backing-image ABI and coherency contract** will freeze DDR
  layout, context sections/stride/alignment, page-transfer commands, address
  validation, cache-maintenance/ownership rules, and serialization.
- **P03.1 — Autonomous runtime contract** will freeze exact run/barrier/error
  transitions, board-local timing/observability boundaries, and the v3
  implementation addendum to the inherited Loihi target specification.

This avoids treating implementation details as completed merely because the
high-level partition is accepted.

## Accepted deliverables

- v3 board-local architecture/ownership document;
- explicit external-host / PS / PL / DDR responsibility table;
- PS-to-PL control-plane direction;
- PL-to-DDR bulk-data-plane direction;
- first non-coherent ownership strategy;
- preservation of logical-core / resident-slot / physical-engine separation;
- preservation of CURRENT/NEXT event causality and global barrier semantics;
- decision that no existing logical Loihi-1 semantic rule needs to change;
- explicit decision to defer multi-engine execution until the memory system and
  single-engine board-local runtime are measured.

## Acceptance

P01 is accepted based on independent design review and explicit approval of the
PS/PL/DDR partition.

This acceptance freezes the architectural direction only. It does **not** claim
that DDR paging or the PS-resident runtime is implemented yet. Those are P02
and P03 respectively.

Primary record: `docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

---

# P02 — DDR-backed logical-core virtualization

**Status:** Complete  
**Accepted:** 2026-10-06

## Goal

Replace PC-RAM backing for non-resident cores with K26 DDR backing.

## Sub-milestones

- **P02.1 — DDR backing-image ABI and coherency contract.** **Complete; accepted 2026-10-05.** Freeze layout,
  fixed/variable section sizes, alignment, versioning, address validation,
  page-transfer commands, ownership/cache-maintenance rules, and deterministic
  serialization. Primary records: `docs/P02_1_DDR_ABI.md` and
  `docs/P02_1_VERIFICATION.md`.
- **P02.2 — Software reference and transfer-model validation.** **Complete; accepted 2026-10-05.** Model authoritative DDR records, resident-slot
  materialization, eviction/writeback, runtime metadata refresh, transfer byte
  accounting, and full-versus-mutable-only writeback equivalence. Primary
  records: `docs/P02_2_DDR_TRANSFER_MODEL.md` and
  `docs/P02_2_ACCEPTANCE.md`.
- **P02.3a — Resident-bank page walker and ownership path.** **Complete; accepted 2026-10-05.**
  Implement the deterministic PL bank walker over the accepted P05 host-side
  memory access boundary, with full/mutable-only transfer sequencing and
  directed RTL verification.
- **P02.3b — AXI DDR master/burst integration.** **Complete; accepted 2026-10-05.** Connect the
  verified bank walker to the selected PS DDR high-performance path, add burst
  buffering/range checks, and integrate into the Vivado shell.
  - **P02.3b1 — 128-bit AXI burst coalescer.** **Complete; accepted 2026-10-05.** Coalesce the
    scalar-correct walker transactions into 256-byte / 16-beat AXI4 bursts
    without changing the accepted DDR address stream.
  - **P02.3b2 — HP0 Vivado integration.** **Complete; accepted 2026-10-05.** Bind the
    verified AXI master to the K26 PS `S_AXI_HP0_FPD` path through
    SmartConnect, confine paging to the fixed 64 MiB DDR backing window, and
    synthesize/route the resulting shell. Primary record:
    `docs/P02_3B2_HP0_INTEGRATION.md`; routed acceptance: `docs/P02_3B2_ROUTE_ACCEPTANCE.md`.
- **P02.4 — Physical DDR-backed paging acceptance.** **Complete; accepted 2026-10-06.** Demonstrate that
  non-resident logical contexts live in K26 DDR and are paged into the three
  resident slots without PC RAM participating in the page loop. Primary plan:
  `docs/P02_4_PHYSICAL_PAGING.md`.
  - **P02.4a — deterministic physical DDR round-trip.** **Complete; accepted 2026-10-05.** Reused the
    accepted P02.3b2 bitstream to prove byte-exact full page-in/full page-out and
    mutable-only writeback through real K26 DDR, with exact burst/byte/cycle
    evidence and per-bank fingerprints. Primary acceptance record:
    `docs/P02_4A_ACCEPTANCE.md`.
  - **P02.4b — five-over-three DDR-backed workload.** **Complete; accepted 2026-10-06.** Execute
    a directed seven-timestep / 35-dispatch five-logical-core workload through
    three resident slots and one physical engine with K26 DDR as the
    authoritative non-resident backing store. Require exact per-dispatch
    state/spike/packet agreement and byte-exact final DDR images for all five
    logical contexts. Primary record: `docs/P02_4B_FIVE_OVER_THREE.md`.

## Deliverables

- deterministic `logical_core_id -> DDR backing region` mapping;
- storage for all complete logical context images required by a deployment;
- page-in/page-out between DDR and the three proven resident context slots;
- preserved CURRENT/NEXT event-bank semantics;
- preserved logical destination IDs independent of physical residency;
- explicit dirty/writeback rules;
- context fingerprints/checksums;
- measured page transfer size, latency, and bandwidth;
- PS-copy and/or AXI/DMA implementation chosen from measured evidence rather than assumption.

## Acceptance

Accepted on 2026-10-06.

The directed five-logical-core / three-resident-context physical workload
completed with K26 DDR as the authoritative backing store:

```text
dispatches=35
barriers=7
routed_packets=30
page_ins=60
page_outs=60
evictions=57
page_hits=8
axi_read_bursts=102720
axi_write_bursts=24960
axi_bytes=32686080
result=PASS
```

All five complete final 512 KiB DDR records matched their golden images
byte-for-byte. Primary phase record: `docs/P02_ACCEPTANCE.md`; physical
five-over-three acceptance: `docs/P02_4B_ACCEPTANCE.md`.

---

# P03 — Autonomous PS-resident runtime

**Status:** Complete — independently accepted 2026-10-12
**Development branch:** `agent/v3-p03-autonomous-runtime` (merged into `main` at closeout).
**Authoritative acceptance:** `docs/P03_FINAL_ACCEPTANCE.md`.
**Detailed PS application architecture, DDR/packet/mailbox ABI,
debugging chronology and reproduction:** `docs/P03_PS_AUTONOMOUS_APPLICATION.md`.

## Goal

Move host-owned algorithmic orchestration onto the KV260 PS.

## Sub-milestones

- **P03.1 — Autonomous runtime contract.** **Complete; accepted 2026-10-06.** Freeze
  exact run/barrier/error transitions, board-local timer/counter boundaries,
  recovery behavior, external-host exclusion, cache/ownership rules, and the v3
  implementation addendum to the inherited Loihi target specification. Primary
  record: `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`.
- **P03.2 — PS-visible MMIO control/status shell.** **Complete; accepted 2026-10-11 for the physical experimental control shell.** Replace
  VIO-owned page/dispatch/resident-memory control with a PS-accessible AXI-Lite
  register block on the accepted `M_AXI_HPM0_FPD` direction while preserving
  the accepted P02 data plane and response semantics.
  - **P03.2a — AXI-Lite register contract.** **Complete; accepted 2026-10-06.**
    Freeze the 32-bit register map, sticky completion semantics, slow resident
    request handshake, Python/C software constants, and directed RTL regression.
  - **P03.2b — Routed HPM0 integration.** **Complete; accepted 2026-10-06.** Connect
    the register block through HPM0 at `0xA4000000..0xA4000FFF`, preserve the
    accepted HP0 DDR data path, retain VIO as observation/reset-only, close
    timing, and export bitstream/probes/fixed XSA.
  - **P03.2c — Physical PS-MMIO smoke.** **Complete; independently
    accepted 2026-10-11.** The KV260's physical PS HPM0 width selectors
    were measured at 128 bits while the original FPD/LPD PL designs
    expected 32 bits. The corrected FPD 128-bit AXI4 master plus
    1x1 SmartConnect 128-to-32-bit AXI4-Lite bridge preserves the
    `0xA4000000` MMIO ABI and existing HP0/DDR paging path.
    The independent A53 read-only diagnostic passed all four registers.
    Subsequently the independent **full A53 page/resident/dispatch
    smoke passed**: strict 64-byte mailbox verifier reported
    `id=0x4C543302`, `capabilities=0x0001031F`,
    `page_bytes=438272`, `config0=0x14001000`,
    `dispatches=1`, with full verifier exit `0`. The full
    verifier additionally checked VERSION, page burst counts, sticky
    done/errors, resident read-valid, dispatch/global errors and
    completion. Physical evidence directory:
    `/tmp/v3_p03_2c_fullsmoke_20261012T020320Z` (user PC).
    **Accepted experimental-shell decision:** retain diagnostic ILAs
    and temporary otherwise-unmapped signature during P03.3; track
    their removal and a final release route as a separate cleanup
    gate, not as a blocking functional requirement. See
    `docs/P03_2C_ACCEPTANCE.md` and
    `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`.
- **P03.3 — Standalone Cortex-A53 runtime.** **Complete; independently accepted through P03.4/P03.5 on 2026-10-12.** Implement
  P03.1's board-local state machine, deterministic scheduling/replacement,
  packet routing, cache-maintenance ownership, timer/counter collection,
  fail-closed result records, and the fixed P02 64 MiB DDR reservation.
  - **P03.3a — Portable C runtime policy engine.** **Complete;
    independently accepted 2026-10-11.**
    Introduce `software/p03/include/p03_runtime.h`,
    `software/p03/p03_runtime.c` and a host-native hardware-mock test
    harness. Test compiled logical-core service order, initial resident
    selection, dirty-victim writeback before page-in, round-robin
    eviction, exact packet-drain accounting, no-premature-barrier
    event-bank swaps, sticky first-error, and 35 dispatches / seven
    barriers for a five-over-three plan. This does **not** prove
    packet encoding, actual MMIO control or inference equivalence.
  - **P03.3b — Physical MMIO/DDR/packet adapter.**
    **Directed P03.3b1–b3 acceptance complete 2026-10-11; resident
    destination physical coverage explicitly tracked.** Native C
    MMIO/DDR packet adapter passed, the one-core/two-step real A53
    scheduler/adapter probe passed, and the two-core/one-slot
    physical real-HLS packet/dirty-page roundtrip independently passed:
    `ps_width=128`, `first_packet=0x2000000020000581`,
    `second_packet=0x2000000040000A00`,
    `core1_ddr_event1=11`, `core0_ddr_event0=20`,
    `page_ins=3`, `page_outs=3`, `dispatches=4`,
    `barriers=2`, `routed_packets=2`,
    `P03_3B3_VERIFY_EXIT=0`.
    Accepted local evidence folder:
    `/tmp/v3_p03_3b3_fixed_20261012T034337Z`.
    This verified actual PL packets, PS-owned nonresident DDR routing
    and mutable context persistence. The one-slot probe did not
    exercise direct MMIO delivery to an already-resident destination;
    that path remains native-tested and is counted explicitly by
    the new unified P03 runner. Primary acceptance record:
    `docs/P03_3B3_ACCEPTANCE.md`.
  - **P03.3c + P03.4 + P03.5 — Consolidated implementation and
    two independent physical acceptance runs.** **Complete; combined C11/Vitis implementation and physical P03.4/P03.5 gates accepted on 2026-10-12.** To minimize extra subphases, these use one immutable
    software/ABI/hardware path. New
    `software/p03/p03_finish_run.c` links the accepted C
    scheduler, real P03.3b adapter/bridge, and A53 Xilinx BSP. A
    versioned 256-byte CRC32-checked DDR launch manifest selects
    **7 or 100 timesteps** for the **exact accepted P02.4b
    five-logical-core/three-resident-slot ring**. The A53 owns
    the formerly host-driven per-core ingress injection immediately
    before dispatch, RR page replacement, cross-core routing, global
    barrier and bank swaps, CNTVCT timing/counters, failure
    persistence, and final dirty resident flush. XSDB passively
    waits for terminal mailbox and only then retrieves five full
    final 512 KiB records. The Python verifier compares those
    records byte-exactly to the frozen P02 golden and the 256-byte
    mailbox to the scheduler/timing/status oracle. The 7-step
    profile must demonstrate **35 dispatches, 7 barriers, 30
    packets** and the accepted trace fingerprint
    `9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac`.
    The 100-step profile requires **500 dispatches, 100 barriers**,
    and the 100-step Python reference's own packet count and five
    full normalized final records; it may not borrow the 7-step
    oracle. The PS runtime uses a different packet-delivery/paging
    policy than PC-controlled P02, so its *paging counts* may differ
    without changing logical results.
    **P03.4 physical attempt 1 FAILED on 2026-10-11 at the
    `WRITE_RESULT` callback (fault=12, phase=17, result=0xDEAD000B).**
    The mailbox confirmed 35 dispatches, seven barriers and all 30
    expected packets, but reported an impossible final flush count
    `0x800023` instead of 3. The five complete DDR records were
    dumped successfully but the original verifier aborted before
    comparing them against the Python oracle. A V2 corrective
    candidate explicitly initializes application-owned counters,
    preserves every acceptance predicate while encoding the exact
    failed check in a tagged error-only mailbox overlay, and runs
    byte-exact final-DDR comparison even on a failed mailbox. The
    build/physical runner require a V2 ELF marker, not the older V1
    binary. The exact root of the counter anomaly remains
    **unconfirmed** until fresh physical evidence. See
    `docs/P03_4_PHYSICAL_ATTEMPT1.md`.
    **P03.4 ACCEPTED from independent physical KV260 seven-step V2
    verification on 2026-10-11 local / 2026-10-12 UTC.**
    The five-core/three-slot A53 autonomous run completed 35 dispatches,
    30 routed HLS packets, seven barriers, 35 page-ins and 35 page-outs,
    and all five final 512 KiB DDR records matched the frozen P02/v2
    Python oracle byte-exactly; trace fingerprint
    `9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac`.
    Measured `resident_deliveries=0`: this ring provides physical
    nonresident routing evidence, not direct-to-resident packet delivery.
    Acceptance: `docs/P03_4_ACCEPTANCE.md`.
    **P03.5 ACCEPTED on 2026-10-12 (same V2 A53 ELF and FPD128
    experimental bitstream).** The independent 100-timestep
    five-core/three-slot physical test reported terminal
    `result=0x600D600D`, **500 real HLS dispatches, 495 routed
    packets, 100 barriers, 500 page-ins, 500 page-outs**, and all
    five final 512 KiB DDR records byte-exact to the independent
    100-step P02/v2 Python oracle. Reference trace fingerprint:
    `b10387cb7930e6e4452548ff4d025c8dffe52e9eeebde2d5b43ed9c5475cfcac`.
    Launch manifest SHA-256:
    `30076c118d312e57674f716e50fe3d080e7a057ed55ba1f2ae58a9a7dba51c4b`.
    User evidence:
    `/tmp/v3_p03_finish_100_20261012T145336Z`;
    `P03_FINISH_VERIFY_EXIT=0`.
    **P03 functionally COMPLETE.** P03.4 and P03.5 both reported
    `resident_deliveries=0`; this acceptance does **not** claim
    a real FPGA direct-to-resident destination packet test.
    Preserve it as a P05 hardening/coverage item, along with
    optional release cleanup for the accepted ILA/VIO diagnostic
    shell. See `docs/P03_5_ACCEPTANCE.md`,
    `docs/P03_FINAL_ACCEPTANCE.md` and
    `docs/P03_PS_AUTONOMOUS_APPLICATION.md`.

## Deliverables

A board-resident runtime that can:

- load a compiled deployment into DDR;
- initialize resident contexts;
- ingest an input sample;
- schedule logical cores;
- page contexts;
- route local and cross-page packets;
- determine timestep quiescence;
- enforce the global barrier;
- swap CURRENT/NEXT event banks only at the barrier;
- advance the requested number of timesteps/phases;
- return final evidence/results and execution metadata.

## Acceptance

After a start command, the PC must not participate in logical-core scheduling, packet routing, page replacement, or timestep/barrier control.

The representative five-over-three 100-timestep workload must complete board-locally and match the normalized v2/Python architectural result.

---

# P04 — Multi-engine parallel logical-core execution

**Status:** Deferred

## Motivation

Replicating the P03-compatible HLS evaluation engine remains attractive because
independent logical cores in the same algorithmic timestep can, in principle,
consume frozen CURRENT state concurrently and produce NEXT-timestep traffic.
That could reduce the serialized compute portion of inference latency.

Accepted routed evidence also indicates that the compute logic itself is not the
obvious K26 bottleneck:

```text
P05 one-engine / three-full-context shell:
  LUTs       5,062
  registers  7,686
  DSPs       2
  URAM       47

P04 resource-scaled two-engine shell:
  LUTs       7,059
  registers  9,980
  DSPs       4
```

The two shells are not otherwise identical, so these numbers are **not** an
exact per-engine cost model. They do support the narrower conclusion that v2's
full-capacity scaling problem was dominated by retained memory rather than by
the HLS arithmetic datapath.

## Why it is deferred

The current three-full-context memory fabric is built from true-dual-port URAM
banks. In the accepted one-engine design:

- one memory side services the HLS compute path;
- the second side services host/integration functions such as packet access,
  next-event writes, and context maintenance.

A plausible two-engine design would consume both memory ports for compute during
a parallel wave:

```text
resident context A <-> port A <-> engine 0
resident context B <-> port B <-> engine 1
resident context C remains retained
```

That creates a new arbitration problem: page movement, packet draining, and
event maintenance can no longer freely use the second port while both engines
are active. The first implementation would therefore have to serialize those
operations around compute or redesign the resident-memory access fabric.

The problem becomes more fundamental at three or more engines. Three resident
slots do **not** imply three independent memory read/write ports. Supporting
3+ simultaneous engines would likely require one or more of:

- per-slot memory banking;
- selective replication of read-mostly configuration/axon/synapse/route banks;
- relocation of trace/packet/event storage to other memory classes;
- additional AXI/interconnect arbitration;
- a different resident-context organization altogether.

Those choices can increase URAM/BRAM usage and routing pressure enough to change
the physical architecture that P02/P03 are trying to stabilize.

## Why deferral is preferable

The central v3 research question is first whether the KV260 can execute the
virtualized architecture independently of PC RAM and PC-owned timestep control.

Adding multi-engine execution before that is proven would couple two separate
research problems:

1. **memory/control localization** — DDR-backed paging plus PS/PL ownership;
2. **compute parallelization** — multiple engines and a multiported/banked
   resident-memory system.

Keeping P04 deferred lets P02/P03 establish a clean single-engine baseline. P08
can then quantify how much complete-inference time is actually spent in HLS
compute versus DDR paging, packet routing, PS control, and barriers.

If compute serialization is a dominant measured term, P04 should be reactivated
with an evidence-based engine-count target.

## Preserved design rules for later reactivation

Any future multi-engine implementation must preserve:

- logical-core ID independent of engine ID;
- one engine may own at most one resident logical context at a time;
- two engines may never write the same resident context concurrently;
- CURRENT inputs remain frozen for the entire algorithmic timestep;
- generated traffic is committed only to NEXT-timestep state;
- all engines and all packet/page work must quiesce before the global barrier;
- physical engine/wave assignment is excluded from normalized logical traces;
- one-engine and multi-engine normalized results must be identical.

A future two-engine experiment should measure actual complete-inference speedup;
an assumed 2x speedup is not a valid result.

## Reactivation trigger

Reconsider P04 after the single-engine board-local implementation has accepted
measurements for:

- HLS dispatch time;
- DDR page-in/page-out time;
- packet drain/routing time;
- PS scheduling/barrier overhead;
- complete timestep latency;
- complete inference latency;
- routed resource/timing margin.

---

# P05 — Board-local regression, observability, and data-path hardening

**Status:** **COMPLETE / PHYSICALLY ACCEPTED, 2026-10-13** —
**P05.1 complete; all P05.2a–P05.2i gates physically accepted
within the documented scope.**  
**Historical development branch:** `agent/v3-p05-board-regression`;
user explicitly authorized P05 closeout and merge to `main`.
Phase acceptance: `docs/P05_FINAL_ACCEPTANCE.md`.  
**Baseline:** P03 accepted A53 scheduler, FPGA MMIO/DDR adapter, FPD128
bitstream/XSA and frozen P02/P03 reference goldens remain unchanged.

## Goal

Make KV260 the primary execution target for independent Python-oracle
regression evidence. Demonstrate correctness across different network
sizes, packet residency paths and selected intermediate checkpoints;
then harden error diagnostics, fanout, input saturation/backpressure,
paging, arithmetic, service-order variation and counter provenance.

## P05.1 — Configurable PS regression runner and test infrastructure

**Status: COMPLETE — functional acceptance from two independent user-run
KV260 gates on 2026-10-12.**

- New standalone `p05_regression_run.elf` successfully built using
  accepted routed XSA, versioned/CRC-bounded P05G descriptors,
  strictly validated complete initial DDR records, and original
  unmodified P03 scheduler and PS hardware adapter. Host
  Python↔C11 ABI/negative regressions were independently reported PASS.
- **First physical gate:** Five logical cores, three resident slots,
  seven timesteps, 35 dispatches, 30 real packet events,
  seven barriers, **35/35 independent actual-device state0
  checkpoints**, and **all five complete 512 KiB final DDR records
  byte-exact to frozen P02**. `resident_deliveries=0`;
  `P05_1_VERIFY_EXIT=0`. User evidence:
  `/tmp/v3_p05_1_probe_20261012T173751Z`.
  Acceptance: `docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md`.
- **Second physical gate:** Genuinely different three-core / three-slot
  spiking triangle, threshold=4, five timesteps,
  **15 real dispatches, 12 real packets,
  12 confirmed direct-to-resident deliveries**, five barriers,
  **15/15 model-derived actual-device checkpoints**, zero
  page replacements, and **three complete 512 KiB DDR final
  records byte-exact to its separate LogicalChip model**.
  `P05_1_TRIANGLE_VERIFY_EXIT=0`, real terminal
  `0x600D600D`. User evidence:
  `/tmp/v3_p05_1_triangle_20261012T175547Z`.
  Reference trace fingerprint:
  `c2fde59f694508003fb6b0d17f5ed2945db5f03c427a2690b13acc7bc71b717e`.
  Acceptance: `docs/P05_1_TRIANGLE_ACCEPTANCE.md`.
- Both tests used the **same P05 ELF and accepted FPGA shell**,
  with only initial deployment records/table changed. Python
  compared **actual** physically retrieved complete DDR images;
  reference trace digests are model fingerprints, not full
  physical intermediate trace captures.
- **Qualified acceptance:** Functional deployment, model-relative
  checkpoints and both residency routing paths accepted.
  Independent **physical fault-injection/first-error and
  fast-mode/no-checkpoint equivalence remain untested**. User
  explicitly accepted P05.1 functional closeout with these
  limitations carried into the P05.2 hardening scope.
  Do not imply these two additional hardware gates already passed.

### Deliverables

- New P05 test-oriented standalone Cortex-A53 executable, separate
  from the accepted fixed P03.4/P03.5 ELF, **reusing** the same
  `p03_runtime.c` scheduler and `p03_hw_adapter.c` physical callbacks;
  no per-test recompilation of the algorithmic runtime.
- Versioned bounded deployment descriptor and test-vector format
  supporting selectable logical-core count, time horizon, valid
  logical-core/slot configuration, input events per timestep/core,
  service order where legal, and deterministic observation checkpoints.
  Include checksum/integrity, range, capacity and memory-reservation
  validation on **both host and device**; failures halt before MMIO.
- Python deployment builder, test-vector/golden generation and
  independent verifier with reproducible test IDs and fingerprints;
  initial workload must reproduce an accepted P03 five-core ring
  without modifying or substituting the frozen P03 oracle.
- Device-side per-run and selected per-timestep/per-core observations:
  first-mismatch metadata (logical core, timestep, state class),
  packet/barrier/page counters, and reproducible checksums at safe
  synchronization points. Separate diagnostic and low-overhead modes.
- Retain a replayable fail-closed result format and a fresh ELF marker;
  PS runtime may not delegate paging/routing/step decisions to the PC.

### P05.1 acceptance / hold points

1. **Contract checkpoint:** deterministic host-generated deployment,
   strict portable C11 reader/validator, field-layout and corruption/
   bounds tests, P03 baseline integrity tests. Request independent
   host validation before adding the PS execution path.
2. **Runtime checkpoint:** new separately identifiable standalone A53
   program can autonomously execute at least two distinct valid
   deployment profiles using the accepted PS–PL and DDR interface,
   with byte-exact Python oracle outputs and interpretable
   telemetry. Verify staged ELF/XSA/bitstream identity.
3. **Checkpoint/diagnostic checkpoint:** selected state/event/packet
   checkpoints and first-error reporting agree with model fixtures
   without changes to neural arithmetic; production/passive
   measurements do not silently change the test workload.

**Not P05.1 acceptance yet:** A host-only schema or mocked runner,
an unbuilt ELF, or a new host-controlled per-dispatch loop. A directed
physical already-resident destination packet test may be included in
the P05.1 trial profile; broader coverage is P05.2.

## P05.2 — Directed physical regression and observability validation

**Status:** COMPLETE / PHYSICALLY ACCEPTED (2026-10-13) —
P05.2a first-fault localization,
P05.2b checkpoint-disabled equivalence,
P05.2c reordered service, P05.2d two-destination fanout
and **P05.2e composite physical evidence recheck accepted**
on real KV260 (independent user-reported results, 2026-10-12).
The first P05.2e full-DDR comparison correctly failed at
core3 packet RAM offset 0x64000 because the normalized
destination-sorted model order [0,4] differs from physical
registered output-route order [4,0].
The independent **non-destructive recheck PASS**
`P05_2E_RECHECK_EXIT=0` verifies 40/40 checkpoints, 48
packets (24 resident and 24 nonresident), 37 dirty evictions,
and all five complete real DDR images against the separate
derived physical packet-layout oracle **without modifying the
original A53/FPGA evidence or neural model**. Its acceptance
record is `docs/P05_2E_RECHECK_ACCEPTANCE.md`; the user has
not supplied a fresh native pytest summary alongside this
physical recheck. P05.2f signed arithmetic/refractory/paging and P05.2g
exact 4096 CURRENT-event-bank saturation plus CRC-valid
4097-event early device-admission rejection are independently
physically ACCEPTED. P05.2h 16-barrier mixed-residency dual-bank/packet
stress gate is independently PHYSICALLY ACCEPTED, with 318
checkpoints, 156 packets split 78 resident/78 nonresident,
77 evictions and five byte-exact DDR records (user-confirmed).
P05.2i **PHYSICALLY ACCEPTED** as the final
counter-provenance closeout gate: the same-run,
no-reboot XSDB `mrd -force` read-only capture
measured **136,960 completed read bursts,
33,280 completed write bursts and 43,581,440
successful FPGA page-engine AXI bytes** in hardware.
The independent A53 `P05R` burst counts, separate
model-derived page totals, full 318-checkpoint neural
oracle and all five 512 KiB physical DDR records
agreed; `P05_2I_VERIFY_EXIT=0`. User expressly
approved final P05 closure and merge. See
`docs/P05_2I_ACCEPTANCE.md`. Live routed NEXT-bank
overflow recovery remains explicitly unverified.

**P05.2a — Deterministic negative-checkpoint hardware diagnostic
(ACCEPTED on real KV260, 2026-10-12).** Reuse the physically accepted
three-core fully resident triangle, unchanged 3×512KiB initial
neural records, same 15 stimulus events, same 15 dispatch
metadata entries, same PS/PL binary identities. Flip **one bit
of the EXPECTED state0 CRC at checkpoint 7** (timestep 2,
logical core 1); the real A53 must intentionally
stop at barrier 2 and report `result=0xDEAD000A`, runtime fault 11,
fault phase 13, first mismatch (step=2, core=1, class=state0)
with observed CRC **equal to the independent clean model**.
Do not call some unrelated hardware ERROR a test PASS.
No final DDR equality is expected after early fault because
final dirty-slot flush never executes.

Scripts: `scripts/p05_2_fault_fixture.py`,
`scripts/p05_2_fault_verify.py`,
`scripts/run_p05_2_fault.sh`.
Host native/injected-malformed-mailbox tests:
`tests/test_p05_2_fault.py`.
Reproduction, measurement caveats and directed coverage backlog:
`docs/P05_2_DIAGNOSTIC_GATE.md`.
**Observed P05.2a PHYSICAL PASS**: user captured real A53
`0xDEAD000A` after one passive poll, with first-fault 11,
phase 13, failing step 2/core 1/state0, injected expected
CRC `0x6522DF68`, physically observed/reference-model CRC
`0x6522DF69`, 9 prior dispatches, 6 packets,
6 direct resident deliveries, 2 complete barriers and 7 passing
prior checkpoints. Strict `P05_2_FAULT_VERIFY_EXIT=0`;
physical evidence:
`/tmp/v3_p05_2_fault_20261012T181015Z`.
See `docs/P05_2A_FIRST_MISMATCH_ACCEPTANCE.md`. This
intentionally stopped before final dirty DDR flush; **no
completed golden DDR equality was claimed**.

**P05.2b — Low-overhead/fast mode versus accepted diagnostic
mode (PHYSICAL ACCEPTED on KV260, 2026-10-12).** Run the **same** accepted
three-core/three-resident, threshold-4 spiking triangle and
15 input events on the **unchanged** P05 A53 ELF and FPGA PL.
Byte-exactly preserve all three initial core images and core/
input table; only mode flag changes 1→0 and 15 checkpoints
are removed. Require 15 dispatches, 12 packets, 12 direct
resident deliveries, 5 completed barriers, no checkpoints
and **three complete final DDR records equal to both**
independent Python golden and separately accepted diagnostic
KV260 SHA-256 results. Host builder/verifier/shell:
`scripts/p05_2_fast_fixture.py`,
`scripts/p05_2_fast_verify.py`,
`scripts/run_p05_2_fast.sh`;
native tests: `tests/test_p05_2_fast.py`;
procedure: `docs/P05_2_FAST_EQUIVALENCE_GATE.md`.
**Observed P05.2b PHYSICAL PASS:** User supplied
`verify.log` with `timesteps=5`, 15 FPGA dispatches,
12 packets, 12 resident deliveries, five barriers,
`checkpoints=0`, and all three **actual full DDR
record SHA256s byte-exact to both independent Python
oracle and previously accepted diagnostic KV260 records**.
Real P05G header CRC32 `0x76E6409B`, payload CRC32
`0x1AF530B0`; physical record SHA256s remain
`5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381`
(core0),
`2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2`
(core1),
`d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f`
(core2).
`pl_dispatch_cycles=357` and `ps_inference_ticks=25994`
are raw observations, **not a calibrated performance or
power/energy benchmark**. Acceptance:
`docs/P05_2B_FAST_ACCEPTANCE.md`.

**P05.2c — Legal logical-core service-order invariance
(PHYSICAL ACCEPTED on KV260, 2026-10-12).**
Same physically accepted diagnostic three-core triangle
on the unchanged P05 ELF and accepted FPGA.
Change actual A53 service order **`[0,1,2]` →
`[2,0,1]`**, while keeping all three cores resident,
all original neuroparameters and 15 input events,
five timesteps, 12 packets and 12 resident deliveries.
Recompute an independent Python LogicalChip oracle with
the new service order and require every per-core neural
state and all three *complete* model final DDR images
equal the baseline. Then verify 15 real board checkpoints
and byte-exact physical DDR equality to **both independent
models and the pinned accepted baseline physical SHA256s**.
Scripts: `scripts/p05_2_order_fixture.py`,
`scripts/p05_2_order_verify.py`,
`scripts/run_p05_2_order.sh`, native tests
`tests/test_p05_2_order.py`,
`docs/P05_2_ORDER_INVARIANCE_GATE.md`.
**Observed P05.2c PHYSICAL PASS:** User supplied independent
`verify.log` showing real A53 service order **[2,0,1]**,
15 dispatches, 12 packets, **12 resident deliveries**,
5 barriers and 15/15 actual golden neural checkpoints.
All **three complete 512KiB final DDR records** matched
both independently simulated Python service-order variants
and the previously accepted original-order KV260 SHA256s.
P05G header CRC32 `0x22ECC007`, payload CRC32
`0xC0AFC18C`. Acceptance record:
`docs/P05_2C_ORDER_ACCEPTANCE.md`.
This establishes physical invariance for **one legal
three-resident permutation only**, not all possible
virtualization/paging schedules.

**P05.2d — Two-route physical packet fanout / convergent
NEXT-bank event aggregation (PHYSICAL ACCEPTED 2026-10-12).**
Generate a **new** independent `LogicalChip` three-core
all-to-all-except-self topology where each firing
source emits **two distinct packets**, each destination
receives two routed next-timestep spikes plus one
external spike, without violating global barriers.
With five timesteps, weight 3 and threshold 4, the
independent model is expected to produce
**15 dispatches, 24 emitted packets and 24 direct
resident deliveries**, 15 actual-device state0
checkpoints, three initial page-ins/three final
page-outs and no replacement paging.
Require all three **complete** physical DDR records
byte-exact to a fresh fanout Python oracle.
Fixture `scripts/p05_2_fanout_fixture.py`,
strict verifier `scripts/p05_2_fanout_verify.py`,
physical provisioning `vivado/p05_2_fanout_prepare.tcl`,
two-mode runner `scripts/run_p05_2_fanout.sh`,
host negative tests `tests/test_p05_2_fanout.py`,
instructions `docs/P05_2_FANOUT_GATE.md`.
**Observed P05.2d PHYSICAL PASS:** User-supplied independent
KV260 `verify.log` confirms 15 dispatches,
**24 routed packets and 24 actual resident deliveries**,
5 barriers, 15/15 model-derived hardware state0 checks,
and three complete physical 512KiB final records byte-exact
to the new fanout LogicalChip golden. P05G header CRC32
`0xD6B1D9AC`, payload CRC32 `0x20423406`.
Reference Python trace SHA256:
`931ce506074695b567f97076b0b58bc65d796dd4c468e4d320a9e02b9182a759`.
Actual final physical SHA256s:
core0 `f545f5d7fa3d896ad2792ada1515f2db9676d80b7095ec8c8c817ca1d5e95da6`,
core1 `051d61da564a0d160265c620f384c7ede18c88f2551b146a6bdb556edb428a27`,
core2 `b806caf750a820b050a73f280d3ebdf08893b4d8b66a6a2d87ccdc77630807c4`.
Acceptance: `docs/P05_2D_FANOUT_ACCEPTANCE.md`.
**Fanout with 3 incoming events/core is not 4096-entry
event-bank saturation/backpressure coverage.**

**P05.2e — Composite multifeature physical regression
(PHYSICAL RECHECK PASS, user reported 2026-10-12; native-suite
reconfirmation outstanding).**
New fully model-derived **five logical cores over three
resident slots**, eight timesteps and actual service order
**[4,1,3,0,2]**. Every source has **two outgoing fanout
destinations** (core+1/core+2 mod 5), each with normal-range
heterogeneous thresholds **4,5,6,7,8** and weight 3.
Require 40 logical A53 dispatches, 40 ingress events,
40 real-device state0 barrier checks, five complete
byte-exact physical DDR records, and **both resident and
nonresident packet deliveries**, while stressing repeated
round-robin victim replacement and dirty page flush/reload
over eight barriers.
Golden neural states, packet vectors and entire five final
DDR images come from independently generated Python
`LogicalChip`. A second standalone Python replay of the
exact accepted C victim-pointer/dirty marking policy
computes page hits, evictions, full page-ins,
mutable-outs, packet residency at actual emission and
final page-command counts; the generator fails if it does
not cover 20+ real replacements/out and both routing paths.
The gate also audits expected **programmed payload bytes**
per physical page command (full-in `0x6B000`, mutable-out
`0x1A000`), **not calibrated AXI traffic or throughput**.
No software C, existing bitstream or accepted v2 oracle
source changed.
`scripts/p05_2_composite_fixture.py`,
`scripts/p05_2_composite_verify.py`,
`scripts/run_p05_2_composite.sh`,
`vivado/p05_2_composite_prepare.tcl`,
`tests/test_p05_2_composite.py`,
`docs/P05_2_COMPOSITE_GATE.md`.
**P05.2e originally failed** on full physical packet-RAM
comparison at core3 0x64000, although the standalone A53
terminal reported `0x600D600D`. The source-informed
physical packet-layout oracle was added in
`scripts/p05_2_packet_layout.py`, without changing the
normalized Loihi model, native FPGA routing or accepted A53.
**The user independently reran the non-destructive existing-
evidence check and reported `P05_2E_RECHECK_EXIT=0`.**
All five complete physical final 512KiB DDR records
matched the separately derived route-ordered reference;
the check also confirmed the original P05G, model, mailbox
and FPGA DDR dump evidence was unchanged.
Original failed evidence is retained; the new check's PASS
does not rewrite that history. Full reproduced output and
scope: `docs/P05_2E_RECHECK_ACCEPTANCE.md`. Native pytest
regression output remains to be confirmed independently.

**P05.2f — Combined signed-24 saturation, fractional/end-point
decay, negative weights, refractory and paging regression
(PHYSICAL ACCEPTED from user's independent KV260 results 2026-10-12).**
A single six-step five-logical-core / three-slot profile combines
+/- 24-bit saturation, +/- signed weights, decay 0/1024/2048/4096,
threshold/reset/refractory, packet routing, dirty victim paging
and 30 actual-device state0 barrier checkpoints. The unchanged
P05 A53 ELF and routed FPD128 shell were reused; **no new bitstream**.
The strict verifier checked all five complete 512 KiB raw DDR
contexts, encoded signed parameters, P05R counters and frozen model
SHA/CRC. The user independently reported:

```text
PASS: P05.2f physical five-over-three signed/decay/saturation/refractory steps=6 dispatches=30 packets=8 resident_deliveries=8 nonresident_deliveries=0 barriers=6 checkpoints=30 evictions=27
PASS: P05.2f five complete 512KiB physical DDR images byte-exact to independent signed 24-bit LogicalChip reference
P05_2F_VERIFY_EXIT=0
```

**Limit:** The eight real HLS packets all reached resident destinations;
P05.2f does NOT independently exercise nonresident routing. P05.2e
already covered 24 resident + 24 nonresident deliveries.
A native pytest summary and full local binary/evidence hashes were
not included in the user's P05.2f reply; these are not invented.
Original sources: `scripts/p05_2f_arithmetic_fixture.py`,
`scripts/p05_2f_arithmetic_verify.py`,
`scripts/run_p05_2f_arithmetic.sh`,
`vivado/p05_2f_arithmetic_prepare.tcl`,
`tests/test_p05_2f_arithmetic.py`.
Procedure: `docs/P05_2F_ARITHMETIC_GATE.md`.
Physical sign-off: `docs/P05_2F_ACCEPTANCE.md`.

**P05.2g — Exactly full 4096-event CURRENT-bank and
CRC-valid 4097-event device-rejection gates
(PHYSICAL ACCEPTED; independently user-verified on real KV260
2026-10-12/13).**
Two intentionally distinct, separate booted physical runs, on one
unchanged P05 A53 ELF and accepted P03 FPGA shell:

- **Physical FULL:** One logical core, one resident slot, one
  timestep, 4,096 registered external events, one HLS dispatch,
  one barrier, three barrier checkpoints (state0/event0/event1),
  one initial page-in, one final page-out, and a complete 512 KiB
  physical DDR record compared byte-exactly to a fresh model.
  The independent model predicts current=4096/voltage=4096 with
  no outgoing spikes or packets. This demonstrates the **maximum
  accepted CURRENT-event bank depth**, not routed congestion.
- **Physical OVERFLOW:** One additional valid axon event makes
  4,097, and the payload/header remain independently CRC-valid.
  The accepted P05 A53 must fail **before any dispatch/MMIO**
  with terminal 0xDEAD0002 / error=2, zero runtime activity,
  and an unchanged initial 512 KiB physical DDR context.
  A header/checksum error or unrelated terminal cannot PASS.
  The host builder independently rejects 4,097 before creating
  such a descriptor; the deliberately invalid CRC-valid
  descriptor is produced only for the physical admission test.
- **Portable C adapter:** Compile original `p03_hw_adapter.c`
  and directed `tests/p05_2g_route_guard.c` to demonstrate that
  a NEXT bank at 4,095 allows exactly one packet append and at
  4,096 rejects any further packet before DDR store/cache clean.
  This last gate is HOST-MOCKED, not physical packet pressure.

Sources:
`scripts/p05_2g_capacity_fixture.py`,
`scripts/p05_2g_capacity_verify.py`,
`scripts/run_p05_2g_capacity.sh`,
`vivado/p05_2g_capacity_prepare.tcl`,
`tests/test_p05_2g_capacity.py`,
`tests/p05_2g_route_guard.c`.
Full acceptance/reproduction plan:
`docs/P05_2G_CAPACITY_GATE.md`.
Independent original reported physical evidence:
`docs/P05_2G_ACCEPTANCE.md`.
**Observed P05.2g PHYSICAL PASS:** User supplied TWO separate
original KV260 `verify.log` results from
`/tmp/v3_p05_2g_capacity_20261013T004149Z`.
Full profile: 4,096 CURRENT-bank input spikes, 1 real HLS
dispatch, 1 barrier, 3 actual-device post-barrier checkpoints,
and complete original physical 512 KiB DDR byte-exact to
the independent model (`P05_2G_FULL_VERIFY_EXIT=0`).
CRC-valid 4,097-event profile: real A53 rejection
`0xDEAD0002` before any MMIO/dispatch/page/barrier with
unchanged complete original 512 KiB DDR context
(`P05_2G_OVERFLOW_VERIFY_EXIT=0`).
Host native suite passed independently per user, but a
full pytest count/log was not provided.

**P05.2h — Adversarial multi-bank/boundary and routing-barrier
stress (PHYSICAL ACCEPTED; independent user-verified real KV260
2026-10-13).** The new integration test deliberately
extends service time to **16 global timesteps** on five logical
cores / three physical context slots, retains real service
order [4,1,3,0,2], uses two outgoing fanout destinations per
spike and core-specific thresholds [2,3,4,5,6].
The independent `LogicalChip` produces all complete immutable
neural core DDR records and per-step model vectors; a separate
conservative P03 victim replay computes real paging and
resident/nonresident routing counters.

An **independently replayed double-event-bank oracle** computes
every post-barrier `event0` and `event1` first-word CRC,
alongside `state0` for **all five cores at all 16 barriers**,
plus actual `packet0` whenever emitted. This means **at least
240 live physical diagnostic checkpoints**, alongside
80 physical dispatches, 80 external stimuli, repeated dirty
evictions, both routing residency modes, and entire five
512 KiB physical DDR records byte-exact to a derived
output-route-ordered packet RAM reference. Crucially, the
original destination-sorted logical Python oracle remains
unchanged. The accepted P05 ELF and P03.2c bitstream are reused;
no hardware RTL, C or FPGA shell is modified.

Implemented:
`scripts/p05_2h_barrier_fixture.py`,
`scripts/p05_2h_barrier_verify.py`,
`scripts/run_p05_2h_barrier.sh`,
`vivado/p05_2h_barrier_prepare.tcl`,
`tests/test_p05_2h_barrier.py`.
Full native-first reproduction:
`docs/P05_2H_BARRIER_GATE.md`.
User-observed original physical proof:
`docs/P05_2H_ACCEPTANCE.md`:
```text
PASS: P05.2h physical adversarial 5-over-3 bank/barrier order steps=16 dispatches=80 packets=156 resident_deliveries=78 nonresident_deliveries=78 barriers=16 checkpoints=318 evictions=77
PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier
PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden
P05_2H_VERIFY_EXIT=0
```
This satisfies P05.2h's independently checked real
double-bank/barrier, routing and full physical DDR gate;
a numeric native pytest summary was not supplied alongside
this final physical result.

**P05.2i — FINAL Phase-5 read-only AXI transfer-counter
provenance and comprehensive physical closeout
(PHYSICAL ACCEPTED; user-verified real KV260
2026-10-13; `P05_2I_VERIFY_EXIT=0`).** Reuse exactly the accepted
five-logical-core / three-slot, 16-barrier P05.2h neural
profile in **one more standalone real KV260 execution**.
After the A53 finishes, capture twice (read-only) the live
FPGA page-AXI counter MMIO words at
`0xA4000044, 0xA4000048, 0xA400004C, 0xA4000050`.
Cross-verify the physical 128-bit AXI successful read/
write burst counters and successful-byte register against
(a) the original A53 `P05R` hardware-read counters,
(b) the independent P03 victim/page replay, (c) the
256-byte/16-beat physical AXI transport geometry,
and (d) the full repeated strict P05.2h neural, 318 CRC
checkpoint, 5 complete 512 KiB DDR goldens.

Frozen P05.2h page replay: 3 initial full-ins, 77
replacement full-ins, 77 dirty runtime mutable-outs,
and 3 final mutable-outs, so 80 × 0x6B000 full-in
bytes = 35,061,760 and 80 × 0x1A000 mutable-out
bytes = 8,519,680. Required **independently measured
PL HP0 AXI page counters**:
**136,960 completed 256-byte read bursts**, **33,280
completed write bursts**, **43,581,440 successful AXI
page bytes**. These are **PL page-engine** bytes only,
not total system traffic; no synthetic counter or
host-computed page payload alone is physical acceptance.
Require nonzero PL page cycle/PS generic-timer measurements
and zero pending/error status. No changes to accepted
ELF/C runtime/HLS/bitstream.

Implemented:
`scripts/p05_2i_axi_closeout.py`,
`scripts/run_p05_2i_axi_closeout.sh`,
`vivado/p05_2i_read_axi_counters.tcl`,
`tests/test_p05_2i_axi_closeout.py`.
Native-first reproduction and failure policy:
`docs/P05_2I_AXI_CLOSEOUT_GATE.md`.

**Final independently confirmed P05.2i physical PASS (2026-10-13).**
The first P05.2i trial completed all P05.2h neural
checkpoint and 5-DDR comparisons but hit the XSDB
debugger **software** memory-map restriction on
`0xA4000044` during unforced `mrd`. That first attempt
did not satisfy P05.2i. With the KV260 **not rebooted**,
the user ran the read-only `mrd -force` recovery on
the same physical A53/DDR evidence. The new read-only
actual FPGA AXI register witness matched the independent
A53 `P05R` and software page replay exactly.
The user supplied the following actual physical verifier
outcome (the underlying raw binaries remain on the
user's machine; don't pretend they are repository files):

```text
PASS: P05.2h physical adversarial 5-over-3 bank/barrier order steps=16 dispatches=80 packets=156 resident_deliveries=78 nonresident_deliveries=78 barriers=16 checkpoints=318 evictions=77
PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier
PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden
PASS: P05.2i KV260 PL HP0 AXI successful 256-byte burst counters read=136960 write=33280 and direct read-only hardware bytes=43581440 exactly equal 80 complete full page-ins + 80 mutable-only page-outs
PASS: P05.2i independent A53 P05R page counters match halted-PL MMIO burst registers and directly measured page AXI byte register
PASS: P05.2i original 16-barrier/318-checkpoint neural and all five 512KiB physical DDR oracle preserved
P05_2I_VERIFY_EXIT=0
```

Reconstructed page transfers: 3 initial full page-ins,
77 replacement full-ins, 77 dirty runtime mutable-outs,
3 final mutable-outs. Successful 256-byte read bursts:
136,960; successful write bursts: 33,280;
directly read actual PL HP0 successful-transfer bytes:
43,581,440. These are **FPGA page-engine physical
AXI transfers**, not overall PS+PL memory traffic.
User-reported P05R SHA-256
`3de43163e98d3368ee1bf52afcdbdc4737840962f449850b842f4e1ab68f4cfb`,
counter-witness SHA-256
`51ea572f1cb83902d6d853da2fc1b657bcfc28371763201fad32de41cc7d01f9`.
Whole-DDR SHA-256s, timing and preserved investigative
history: `docs/P05_2I_ACCEPTANCE.md`.

**P05 closeout disposition: COMPLETE / ACCEPTED.**
Independent physical P05.1 deployment/route tests and
P05.2a–i directed architectural tests all satisfy their
documented acceptance gates. User expressly requested
closure and merge to `main`.
Consolidated record: `docs/P05_FINAL_ACCEPTANCE.md`.

**Scope limitations carried forward (not silently closed):**

- Native C routing guard covers 4095→4096 NEXT packet append
  and reject-on-full; **the physical HLS-originating 4097th
  routed NEXT-bank packet, stall/backpressure timing, and
  successful runtime overflow recovery were NOT exercised**.
  CRC-valid 4097-**deployment** rejection is different.
- The directly observed AXI byte count covers only
  successful PL page-engine HP0 transfers, **not**
  host provisioning/PS DDR stores/cache traffic, total
  platform DDR traffic or application throughput/energy.
- P05 raw board regression timer data are **not**
  P07 MNIST inference latency nor P08 calibrated
  energy/power results. One physical HLS engine,
  not P04 deferred multi-engine parallelism, was tested.
- Several historical physical PASS excerpts did not
  include full fresh native pytest totals or original
  uploaded binary identities. Do not invent them.

The completed P05 correctness/observability scope is
accepted with these documented exclusions. P04 remains
deferred; **P06 is next**. Preserve accepted P02/P03
binary/RTL/software reference evidence unchanged.

### Deliverables

- Execute the major architectural regression corpus **physically on
  KV260**: neuron arithmetic, spike packet encoding/routing,
  **direct-to-resident delivery (unexercised in P03: measured
  `resident_deliveries=0`)**, nonresident DDR delivery, fanout,
  event saturation and backpressure, page transfers/dirty eviction,
  repeated page replacement, barriers, and legal service-order
  invariance. For every test, define independently reproducible
  Python golden outputs and target coverage before running hardware.
- Capture/checkpoint complete or selected trace/state fingerprints
  at well-defined safe observation points, with the first incorrect
  core/timestep/state class reported on mismatch.
- Audit existing PS/PL counters for dispatches, page-ins/out,
  actual transferred DDR bytes, routed packets, barrier waiting,
  hardware PL cycles and PS generic-timer intervals. Implement
  additional PL instrumentation **only where existing MMIO and
  PS software cannot supply a reliable measure**, maintaining a
  known-good accepted P03 bitstream as fallback.
- Maintain evidence provenance (ELF, XSA, bitstream, source SHA,
  manifest, output/trace digest), reproducible scripts and
  explicit failure/reboot instructions. Compare results with
  Python as oracle, not as runtime orchestration.

### P05.2 acceptance

The major frozen v3 architectural regression corpus executes on the
KV260 with zero unresolved deviations from its independently
generated software oracle. Every supported physical feature has
documented directed coverage; unexercised features remain clearly
labelled. The full evidence package identifies the first failing
core/timestep/state class when hardware diverges. A fresh hardware
route, if required, is independently revalidated before adoption.

## Relationship to later phases

P05 measures correctness and coverage; P06 freezes the exact MNIST
benchmark, P07 runs it primarily on board, and P08 measures
latency/throughput/power/energy with distinct rigor. P05 does **not**
retroactively change P03's accepted source or golden evidence.

---

# P06 — Two-track LIF MNIST model, mapping and benchmark freeze

**Direction: APPROVED — sequential compact then scaled tracks.**
**Branch:** `agent/v3-p06-lif-feasibility` (forked from the
unmerged Rao `agent/v3-p06-benchmark-audit`; accepted P05
`main` and its evidence unchanged). **No official
MNIST test-set accuracy evaluated; no trained model yet.**

**Published foundation, not an original checkpoint claim:**
Eshraghian et al. (2023), *Training Spiking Neural Networks Using Lessons
From Deep Learning* (DOI `10.1109/JPROC.2023.3308088`),
and its snnTorch MNIST examples. The tutorial's actual
784→1000→10 model uses **floating-point**, 25-step
analog image input, subtract-reset `Leaky` and same-step
forward-layer processing. Our **project models** deliberately
use deterministic spike events, P03 integer hard-reset
LIF and P05 NEXT-bank routing. Both resulting
checkpoints, accuracy results and timing measurements
will be **project-specific**; no tutorial or original
Loihi number may be attributed to them.

**Mandatory execution sequence:**

`P06-A compact reference/training/freeze → P07-A
physical 1-core MNIST → P08-A accepted baseline →
P06-B scaled mapping/training/freeze → P07-B physical
virtualized network → P08-B scaling measurements →
P09 final comparison`.

Track B's *design* is recorded here now, but **Track A physical
accuracy and a measured performance/power baseline take
priority**. Track A may proceed to P07-A when its
own P06 freeze gate passes even while P06-B remains
scheduled for later. Track B cannot retroactively
change Track A's approved checkpoint, protocol or
physical acceptance.

### Track A — Small single-core 784→32→10

- **P06-A1 — Existing compiler/hardware-image structural
  feasibility [ACCEPTED — independent user native PASS,
  2026-10-12].** Actual
  `compile_network`→`export_one_core_image`
  with **synthetic**, non-trained integer weights:
  **42 compartments, 25,408 real packed synapses,
  816 axon bindings, 32 static routes, 108,160 bytes
  v3 logical synapse cost**. Native regressions
  `test_p06_lif_compiler_probe.py` and
  `test_p06_lif_input_probe.py` PASSED after
  the source-faithful 31-spike/310-next-step-fanin
  test correction. The input-event feasibility
  and NEXT-barrier golden test passed.
  **Not trained; not a KV260 physical inference pass.**
- **P06-A2 — Integer-equivalent forward and
  input/readout protocol [CLOSED / USER-ACCEPTED 2026-10-13].**
  Independent signed-24-bit P03 LIF oracle
  covering exact decay rounding, threshold,
  saturation, signed weights, reset, refractory,
  25 event steps + 1 NEXT-bank drain, per-image
  zeroing, and 10-spike-count readout. Pin
  deterministic uint8 pixel→event encoder
  and parity against existing `LogicalChip`
  and packed P03 bank, including overflow/
  threshold/no-spike negative tests. Prove
  training-forward *inference* equivalence
  to the integer oracle, not just approximate
  float `snn.Leaky` behavior.
  A2.1 user attested native pytest PASS and supplied both 32-hidden
  and original-size compiler-probe PASS exits on 2026-10-13;
  see `docs/P06_A2_1_INTEGER_ORACLE_GATE.md`.
  The new independent event contract, complete 26-step dense SNN
  oracle and self-decoded packed-image replay are committed in
  A2.2–A2.4. Their 49-test mirrored local sanity gate passed;
  the user subsequently confirmed the A2.2–A2.4 native gate looked
  good (detailed pytest log not supplied). See
  `docs/P06_A2_2_TO_4_NATIVE_GATE.md`.
  A2.5 now provides integer-exact forward/STE surrogate gradients,
  signed24 fail-closed weight export and compiler-mapping adapter,
  with 7 PyTorch forward unit tests and 2 *native-only* export tests.
  The user explicitly confirmed verification of the A2.5 tests and
  authorized closing P06-A2 on 2026-10-13. The detailed native
  pytest counts/log were not pasted, so this is recorded as
  user-attested acceptance (not assistant-executed native testing).
  See `docs/P06_A2_5_TRAINING_FORWARD_GATE.md`. P06-A2 is
  CLOSED at the host-software numerical/training-forward boundary;
  it establishes no P07 hardware or MNIST-trained accuracy.
  No P05/HLS changes or physical MNIST.
- **P06-A3 — Train and validation-select
  a compact checkpoint [CLOSED / USER-ACCEPTED SOURCE-GO 2026-10-17;
  94.39% HELD-OUT VALIDATION / OFFICIAL TEST SEALED].**
  Canonical MNIST dataset/split/hashes,
  reproducible train/validation-only
  optimization, training seed/versions,
  source weights, legal integer weight/
  bias/decay/threshold quantization and
  a predeclared validation-only GO/NO-GO
  criterion. No sealed official MNIST
  test peeking and no borrowing paper
  accuracy/weights.
  A3.1 canonical TRAIN-only archive checksums/50k-10k seeded split,
  A3.2 exact integer-forward surrogate training and validation-only
  best-epoch selection, and A3.3 candidate checkpoint manifest and
  integrity checks are committed. The **60% validation GO/NO-GO
  floor was declared before real dataset results**. The user has now
  supplied a first 8-epoch full 50k/10k training manifest with best
  validation accuracy 0.9439, best epoch 8, GO=True, 2/10,000 silent,
  and intact split provenance. The later native A4.1 PASS necessarily
  executed the A3 load_candidate() file SHA256 check, state_dict reload,
  exported-integer-weight digest and frozen-source guard; thus the
  accepted A4.1 software run also established host checkpoint reload
  integrity (separate --validate-candidate marker not pasted).
  User on 2026-10-13 confirmed native pytest PASS and supplied
  `P06_A3_SYNTHETIC_SMOKE_PASS=1`, TRAIN-only archive MD5 and SHA256,
  `P06_A3_DATA_PREFLIGHT_PASS=1`, split seed/size and ordered-index
  hashes. Source identity and train/validation split verification:
  ACCEPTED. Synthetic smoke validation was 12/12 ALL SILENT,
  0.33333 accuracy and ln(10) cross entropy; this is computational
  success only, NOT learning evidence. A3.4 now implements a bounded
  256 TRAIN/128 validation, 2-epoch, no-checkpoint activity pilot with
  gradient, actual quantized-weight-change and output-spike diagnostics.
  The user reported native pytest PASS and supplied A3.4's canonical
  pilot output on 2026-10-15: PASS, no diagnostic reasons, 14,816 and
  320 nonzero layer gradient elements, 4,864 and 105 changed integer
  weights. Pilot baseline 128-image validation 10.16%, final 21.09%,
  but 77/128 (60.16%) final all-silent and class-0 tie bias.
  This is MECHANICAL ACTIVITY acceptance, not an accuracy guarantee.
  The user completed that predeclared eight-epoch full-data experiment:
  epoch 8 was best, train accuracy 0.9534, held-out validation 0.9439
  on 10k images, and 0.0002 silent fraction. The 60% validation
  floor is EXCEEDED by 34.39 percentage points; official test sealed.
  Saved weight-file SHA256 0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88
  and exported integer weights SHA256 1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b.
  A3 conclusion: user-attested validation GO plus native A4.1
  checkpoint-integrity prerequisite passed; A3 is CLOSED.
  Official test still SEALED; no physical accuracy claim.
  See `docs/P06_A4_FINAL_CLOSEOUT.md`.
- **P06-A4 — Freeze trained packed
  benchmark and reproducibility [CLOSED / USER-ACCEPTED 2026-10-17:
  TRAINED P03 SOFTWARE FREEZE + P02 512KiB STATIC DDR NATIVE PASS].**
  Exact real-weight compiler/exporter
  bank/resource gates, independent
  first-divergence software traces,
  model/weight SHA256 and parameter
  contract, decoder/readout/state-reset,
  26-step inference, model/data
  provenance and official-test/physical
  measurement boundaries recorded
  *before* P07-A. Explicit P06-A4
  native acceptance. This is the
  **Track A P06 exit**; P07-A may
  start without waiting for Track B.
  A4.1 now pins the accepted candidate byte hash, signed24-weight
  hash and canonical training split; compiles actual weights through
  original P06 one-core compiler and P03 word exporter; compares
  26-step PyTorch/dense/packed/LogicalChip traces on synthetic and
  fixed validation frames. Emits explicitly little-endian P03
  logical word streams plus SHA256 manifests only after parity passes.
  The user reported native P06_A4_SOFTWARE_SNAPSHOT_PASS=1 and exact
  five-frame, 26-tick, four-engine parity on the trained weights;
  that A4.1 software freeze is now ACCEPTED. All six resulting P03
  word-stream lengths and SHA256 were supplied and are pinned in
  `docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`.
  A4.2 audits those bytes against the user's snapshot and constructs
  the EXISTING P02.1 complete 524288-byte `LTV3CTX1` static DDR
  initial core record, checking all dense/sparse banks and header
  digest. User explicitly reported native A4.2 DDR validation PASS
  on 2026-10-17. The produced full-file SHA256 was not pasted,
  so its source-frozen metadata remains null; capture it from the
  pre-existing local artifact before P07 load, never fabricate it.
  See `docs/P06_A4_FINAL_CLOSEOUT.md` and
  `docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`.
  The P02 static record is NOT the old P05 diagnostic payload or
  a P07 A53 784-input event streamer. No board inference.

### Track B — Larger DDR-virtualized 784→1000→10

**B1 user-verified synthetic feasibility; B2 trained checkpoint not yet frozen:**
**794,000** possible dense synapses;
approximately **26 destination-partitioned
hidden logical cores plus 1 readout core** is
**now demonstrated structurally by the B1.2 user-verified
host-only synthetic dense mapper (27 cores)**,
not a guaranteed globally optimal partition or physical board run. At 27 full 512 KiB DDR
records, backing usage is **13.5 MiB**;
up to 126 logical core IDs are addressable
by the accepted P05 A53 diagnostic deployment
map, with **3 resident FPGA contexts
and 1 physical HLS compute engine**.
Important limitations are per-core 128 KiB
**logical** template/axon/synapse accounting,
32,768 physical synapse words, the input fanout
of up to 784 ports to roughly 26 destinations,
the old P05 ABI's **one valid external axon
per core**, the **896 KiB** diagnostic payload
bound, routing/buffering/barriers and DDR
page traffic. A new model/packet streaming
deployment ABI and **synapse-aware
destination partitioner** will be required.
Simply increasing `max_logical_cores`
in the present `compile_network` will
**NOT** partition by synapse pressure.

- **P06-B1 — Prove scalable packing and
  route semantics [COMPLETE — B1.1–B1.5 USER-ATTESTED NATIVE PASS; B1.6 HOST-SOFTWARE ACCEPTANCE SIGNED OFF 2026-10-19; NO SCALED PHYSICAL RUN].**
  Deterministic synapse-aware partitioner;
  fail-closed axon/synapse/route/event
  budgets per logical core and exact
  512 KiB per-core images. Compare
  a partitioned integer oracle vs an
  independent monolithic reference,
  source input event replication, packet
  arrival at the correct NEXT epoch,
  scheduling invariance, page-traffic
  and estimated throughput. Model
  a worst-case all-255 timestep
  without overflowing per-core banks.
  - **B1.1 — Packed capacity audit [USER-ATTESTED NATIVE PASS]:**
    Accepted on user report before beginning B1.2. See
    `docs/P06_B1_1_PACKED_CAPACITY_CONTRACT.md`; this did
    not imply scaled partition or physical KV260 deployment.
  - **B1.2 — Deterministic synapse-aware destination mapper
    [USER-ATTESTED NATIVE PASS, INCLUDING FULL 784→1000→10
    SYNTHETIC 27-CORE STRUCTURAL PROBE]:** New opt-in
    `src/loihi_twin_v2/p06_b12_partition.py` and
    `tests/test_p06_b12_partition.py` plus reproducible synthetic
    `scripts/p06_b12_synthetic_probe.py` reuse accepted P06
    source/deployment contracts, P03 packing, P02 512 KiB images,
    and B1.1 limit/CRC audit. They do NOT modify the accepted
    P06-A `compile_network` or change Track A checkpoints.
    Require user native acceptance of default synthetic numerical,
    source-edge decoding, deterministic placement, fail-closed capacity
    tests and the opt-in 784→1000→10 structural probe. The user
    reported PASS for the regressions, opt-in full test and both
    synthetic resource probes: 27 logical cores, 26 hidden partitions,
    794,000 connections, 14,155,776 source-derived backing bytes,
    maximum 128,576 logical synapse bytes and 1,000 CURRENT event
    pressure/core. This is *synthetic feasibility*, NOT an accepted
    trained checkpoint, scaled physical hardware paging or firmware.
    See `docs/P06_B1_2_SYNAPSE_AWARE_PARTITION.md`.
  - **B1.3 — Versioned 784-channel multi-core ingress / NEXT packet ABI
    [USER-ATTESTED NATIVE REGRESSION PASS, INCLUDING FOLLOW-UP ORDERING FIX]:**
    Distinct `P06B13I1` binary image + per-destination `<HHH`
    map and `P06B13R1` routed packet frames. Each uses 128-byte
    SHA256-bound deployment/DDR-audit header and independent CRC32.
    Enforces real mapped core/axon pairs, 25+1 tick input schedule,
    per-core CURRENT/NEXT event ≤4096 and emitted packet ≤4096,
    complete source fanout, transactional rejection, source-spike
    provenance (when available) and zero outgoing packets at the
    final drain tick. Independent all-255 26-tick, corruption,
    overflow and opt-in full 27-core fanout structural tests added.
    Source: `src/loihi_twin_v2/p06_b13_streaming.py`;
    documentation: `docs/P06_B1_3_MULTICORE_STREAMING_ABI.md`.
    Old P05 single-axon diagnostic firmware is NOT compatible.
    This does **not** implement the new A53/PL packet streaming
    firmware or claim a physical multi-core run. Native B1.3 tests
    initially exposed two error-reporting assertions; the packet
    decoder was corrected to check NEXT/route/fanout before canonical
    ordering, an independent reordered-frame test was added and the
    user subsequently verified all B1.3 tests/regressions PASS.
  - **B1.4 — Independent 26-tick monolithic integer oracle
    [USER-ATTESTED NATIVE PASS, INCLUDING LARGER OPTIONAL NUMERICAL PROBES]:**
    `src/loihi_twin_v2/p06_b14_monolithic.py` builds a flat
    original `NetworkSpec` event/connection graph and uses the
    independently accepted P06-A scalar signed-24-bit LIF oracle,
    NEVER `LogicalChip`/`step_compartment`/packed templates, to
    compute 26 full compartment-state/synaptic-input/spike epochs,
    readout counts/class and SHA-bound traces.
    `p06_b14_differential.py` checks every named original neuron
    across production B1.2 core placements, independent original
    graph external/NEXT routing groups and earliest divergence,
    under different valid core scheduling/drain orders. New tests
    cover independently encoded image events, manual signed LIF,
    fractional decay/refractory, fixed-seed randomized signed
    weights, saturation, silence/tie, malformed schedules, dropped
    final-drain packets, and deliberately corrupted state/synapse/
    packet witnesses. Host-only synthetic probes cover dense
    784→6→10, optional dense 784→40→10, and optional **SPARSE**
    784→1000→10 / 27-core 26-tick numerical networks. The
    last is NOT a dense 794,000-synapse numerical or physical result.
    See `docs/P06_B1_4_INDEPENDENT_NUMERICAL_ORACLE.md`.
  - **B1.5 — Three-resident-slot / one-engine host paging model
    [USER-ATTESTED NATIVE PASS, INCLUDING DENSE27 STRUCTURAL + SPARSE27 NUMERICAL]:**
    `src/loihi_twin_v2/p06_b15_paging.py` reuses original
    P08 `PagedHardwareImage.resident_page` and B1.1's
    exact P03/P02 512 KiB initial SHA ledger to verify
    logical-core/physical-slot identity at every dispatch.
    It models deterministic LRU hits/dirty evictions, 26
    barriers, all CURRENT inputs plus prior routed NEXT packets,
    per-core 4096 event/packet budget, resident/nonresident-at-emission
    packet classification and mandatory final dirty-slot flush.
    Its numerical path checks every simulated page-ordered core trace
    against the independent B1.4 full 26-tick oracle; an independent
    `project_schedule_only` estimates 27-core **DENSE**
    traffic without falsely claiming dense 794k-edge numerical
    execution. P05.2i's **physically measured** page sizes
    (438,272 full-in / 106,496 mutable-out; 256-byte AXI bursts)
    are applied to **unmeasured scaled scheduling hypotheses**:
    27-core 26-tick ascending policy = 702 dispatches,
    702 page-ins/outs and **382,427,136 ESTIMATED** page-engine
    bytes; alternating service order predicts 627 page-ins/outs
    and **341,569,536 ESTIMATED** bytes. The user separately
    verified both structural orders and the sparse 27-core
    numerical parity; the dense 794k-edge network still has
    **no full 26-tick numerical acceptance**.
    No actual scaled cache/DDR images, A53 firmware, PL timing,
    physical total bytes, speedup or energy asserted.
    New `tests/test_p06_b15_paging.py` includes an
    independent re-computation of actual P05.2i five-core
    measured 43,581,440-byte accounting, LRU edge cases,
    numerical scheduling-order parity, and opt-in dense-27
    structural plus sparse-27 numerical stress.
    Full details: `docs/P06_B1_5_THREE_SLOT_PAGING_ESTIMATE.md`.
  - **B1.6 — B1 host-software acceptance [CLOSED 2026-10-19]:**
    User-attested B1.1–B1.5 source, independent numeric,
    dense 27-core exact packing and sparse 27-core real-numeric
    evidence pinned in
    `docs/P06_B1_6_USER_ACCEPTANCE_LEDGER.json` and
    `docs/P06_B1_6_FINAL_HOST_SOFTWARE_ACCEPTANCE.md`.
    The posted dense alternating report recorded 702
    dispatches, 75 page hits, 627 full ins, 627 dirty outs,
    **341,569,536 estimated** bytes and zero physical scaled
    measurements. Sparse27 separately reported
    `algorithmic_neural_parity=true` for 26 ticks and
    25,000 routed packets; old P05 original physical page
    transfer *sizes* remain the only real page traffic
    measurements. **GO B2 training/validation candidate; NO-GO
    scaled physical KV260 / official TEST** until separate P07-B.
    Historical B1.6 status when originally authored: PR #46 was unmerged.
    **Integration update 2026-10-19:** PR #46 merged into `main` as
    `35ea181360ebf15627c2943090fbdc3c6bf3949e`.
- **P06-B2 — Train, quantize and freeze
  independent larger checkpoint [B2.1–B2.5 USER-ATTESTED HOST SOFTWARE PASS;
  MERGED MAIN 2026-10-19; P07-B PHYSICAL PHASE NOT STARTED].** Keep the same
  deterministic 25+1-step event/input,
  neuron/readout and dataset split;
  train a new project large-model
  checkpoint on train/validation ONLY.
  Freeze its own tensor SHAs, mapping,
  independent parity traces, per-core
  occupancy and a predeclared official
  test protocol. If the full 1000-hidden
  topology is infeasible, declare
  and evaluate a transparent intermediate
  model *before* accessing test results;
  do not silently relabel the model.
  - **B2.1 — Scaled training contract [USER-ATTESTED NATIVE PASS,
    INCLUDING FULL 1000-HIDDEN DENSE PACKED SHAPE]:** New isolated
    `src/loihi_twin_v2/p06_b21_training_foundation.py`
    introduces 784→H→10 H≤1000 integer-valued forward
    using the **unchanged frozen Track A** P06-A2.5 strict
    surrogate-gradient/saturating signed24 kernel; explicitly
    shape-dependent source graph export to the B1.2 mapper,
    dimension-bound signed integer tensor SHA256, canonical
    TRAIN-only split admission and untrained-only manifest.
    New host synthetic 26-tick independent scalar-LIF
    forward/parity/STE-gradient/source packing tests and optional
    dense 1000-neuron graph stress. This is NOT actual training,
    a trained checkpoint, official TEST, or a physical run.
    See `docs/P06_B2_1_TRAINING_FOUNDATION.md`.
  - **B2.2 — Canonical TRAIN-only fitting
    [USER-ATTESTED REAL TRAIN/VALIDATION CANDIDATE INTEGRITY PASS]:**
    `src/loihi_twin_v2/p06_b22_training.py` and
    `scripts/p06_b22_train.py` implement the **separate B2**
    exact signed24 25+1-tick integer-forward optimizer/trainer
    with original canonical 60k TRAIN-only gzip IDX/MD5 reader
    and independently pinned Track A 50k TRAIN/10k train-derived
    validation index SHA256. CLI defaults to shape-only
    memory preflight, WITHOUT loading data or training;
    actual full-data fitting requires explicit `--train`.
    A full trial uses deterministic per-epoch shuffling, Adam,
    full-population accuracy/class/spike/silent validation,
    earliest-best epoch, nonfinite/gradient guards, candidate
    GO floor, no output overwrite, checkpoint file SHA256 and
    separate B2 integer-weight SHA256. Synthetic-only source,
    optimizer, serialization/tamper tests introduced in
    `tests/test_p06_b22_training.py`, documented in
    `docs/P06_B2_2_CANONICAL_TRAIN_ONLY_CANDIDATE.md`.
    The prior development note was written before the actual
    B2.2 train run; the subsequent user-verified real checkpoint
    reached 0.9708 10k TRAIN-derived validation accuracy and
    B2.3/B2.4/B2.5 later passed HOST gates. This is not
    scaled KV260 execution or B2 official TEST acceptance.
  - **B2.3 — Trained weight/packing/numerical audit
    [USER-ATTESTED NATIVE PASS FOR DENSE 27-CORE PACKING + THREE COMPLETE NUMERICAL FRAMES]:**
    User-attested B2.2 candidate best epoch 6, **97.08% TRAIN-derived
    validation** (n=10,000), zero silent, candidate file SHA256
    `93e43915b38cf3c815a125bbab2788e45209f0ccd024d098b25b82a0a8cd0957`
    and effective signed integer SHA256
    `4a20357fc5e77465380c1600e7e82cda515bbafc233fb9e3a1205bca9d00d8b0`.
    `p06_b23_trained_audit.py` requires these exact trained
    checkpoint identities and exports all 794,000 *trained* integer
    connections to B1.2. It checks 27 packed logical cores,
    full P02 backing and event/synapse budgets. Optional
    `--validation-ordinals` executes full 26-tick trained-dense
    monolithic vs actual partitioned B1.4 numerical traces and
    PyTorch signed-integer output equality for selected
    canonical TRAIN-derived validation images ONLY. Default
    is structural-only; neither path claims sealed official
    TEST or scaled KV260 physical execution. Read-only output
    and negative provenance/ordinal tests in
    `tests/test_p06_b23_trained_audit.py`. See
    `docs/P06_B2_3_TRAINED_PACKED_NUMERICAL_AUDIT.md`.
    User-reported B2.3 frozen TRAIN-derived validation ordinals
    0,1,2 (original canonical TRAIN IDs 37384,27347,20178),
    all 26-tick full state/spike/NEXT neural parity `true`,
    27 actual trained packed contexts / 14,155,776 initial
    P02 backing bytes, maximum current events 1000 and
    source/deployment/B1.1 audit SHA256 respectively
    `0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a`,
    `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`,
    `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`.
    The user's repeated B2.3 CLI marker PASS and previous
    B2.1/B2.2/B1 regression suite PASS establish the
    host numerical gate; seven separate optional stress
    tests skipped in that particular regression invocation
    but earlier relevant B1/B2.1 optional cases were verified
    in separate user runs. No FPGA scaled parity was shown.
  - **B2.4 — New checkpoint+validation+official protocol freeze
    [USER-ATTESTED REGULAR AND DEEP NATIVE CHECKPOINT/27-DDR FREEZE PASS]:**
    `p06_b24_freeze.py` requires exactly the user-accepted
    trained B2.2 checkpoint/integer SHAs, B2.3 source/compiler/
    capacity hashes and unchanged original three TRAIN-derived
    full 26-tick trace witnesses before materializing anything.
    It exports original checkpoint bytes/metadata, signed24
    794k-edge source NetworkSpec, B1.2 mapping and all 27
    initial P02 512 KiB DDR context records in one new,
    non-overwritten staged local content-hashed snapshot.
    Built-in separate sealed official MNIST 10k TEST
    prespecified protocol, file digest registry, 27 full
    initial DDR/P02 header/payload checks and optional
    source+compiler+27-DDR deep byte regeneration verifier.
    `tests/test_p06_b24_freeze.py` checks source/trace
    tamper rejection, no overwrite, path-symlink protection,
    manifest tamper and sealed TEST protocol. The user
    supplied native `P06_B24_FROZEN_INTEGRITY_PASS=1` with
    33 frozen assets / 27 actual P02 512 KiB static contexts,
    `deep_regeneration=true` rebuilding original source,
    mapping and all 27 DDR images with matching hashes.
    Native canonical unsigned-manifest SHA256
    `d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90`;
    separate actual `frozen_manifest.json` on-disk file SHA256
    `d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63`.
    Both are separately pinned WITHOUT modifying the original
    still-historical `user_native_B2_4_accepted=false`
    field inside the frozen snapshot. No official TEST unseal,
    actual 27-core FPGA physical run, dynamic DDR dump or
    measured scaled performance asserted. See
    `docs/P06_B2_4_FROZEN_TRAINED_CHECKPOINT_AND_DDR.md`
    and `docs/P06_B2_5_USER_EVIDENCE_LEDGER.json`.
  - **B2.5 — B2 host-software exit / P07-B handoff
    [USER-ATTESTED NATIVE PASS; P07-B DESIGN GO / SCALED PHYSICAL NO-GO]:**
    `p06_b25_acceptance.py` performs read-only checks of
    the original 33 SHA-indexed frozen assets, 27 per-core
    P02 identity/axon/synapse/event/packet pressure bounds,
    both distinct frozen B2.4 manifest digests, B2.2
    trained checkpoint SHA/quantized weight SHA, B2.3
    source/mapping/capacity digests and three exact full
    26-tick TRAIN-derived validation trace witnesses.
    It preserves the original sealed official MNIST TEST
    predeclared protocol and lists the separate real P07-B
    A53/PL firmware, paging/DDR owner, physical timing,
    all-tick board parity and measured latency/energy gates.
    User explicitly reported B2.5 native acceptance PASS;
    no exact B2.5 stdout/test count was supplied, so none
    is invented. P07-B **DESIGN/PLANNING GO ONLY**;
    scaled FPGA programming, measured scaled performance
    and official MNIST TEST unseal remain **NO-GO**.
    Script `scripts/p06_b25_acceptance.py`, unit tests
    `tests/test_p06_b25_acceptance.py`, full closeout in
    `docs/P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md`.
    **Integration confirmed 2026-10-19:** B1 PR #46 merged to
    `main` as `35ea181360ebf15627c2943090fbdc3c6bf3949e`,
    then B2 PR #47 was retargeted to `main` and merged as
    `42f84de3bbbe62302599818c39e7e54747ce8aa2`.
    The prior stacked development branches remain historical;
    all new P07-B work must branch from merged `main`.

**Track B P06 host-software exit (B2.1–B2.4 USER-ATTESTED;
B2.5 FINAL READ-ONLY ACCEPTANCE USER-ATTESTED PASS):** Independent
actual 784→1000→10 TRAIN-only checkpoint trained to
0.9708 TRAIN-derived validation accuracy, 27 precise
P02 static DDR contexts and three full 26-tick trained
dense host numerical frames, with 33-asset native B2.4
normal/deep SHA freeze verified. NOT an actual physical
scaled FPGA implementation, official MNIST TEST score
or measured paging/latency/energy. B2.5 explicitly recorded
P07-B physical execution NO-GO and official TEST UNSEAL NO-GO;
this is not blocked from **starting P07-B development**.
**P06-B1/B2 host-software acceptance is complete and both PRs have merged. Track A P07-A official 94.56% FPGA MNIST TEST and P08-A physical baseline remain frozen and separately accepted. Next: start isolated P07-B development from `main`; do not unseal B2 official TEST until after physical board parity and protocol/run-ID gates.**

### Archived alternate source audit

The earlier Rao et al. Loihi AHP-LSNN
investigation remains intact in
`docs/P06_1_PAPER_CANDIDATE_AUDIT.md`,
`docs/P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md`
and its exact Intel manifest. It was
**not selected**, because original paper
accuracy-to-released-checkpoint linkage
was unresolved and AHP hardware would
require a different neuron contract.
The corrected Rao original-binary
nine-file native audit remains **not
independently accepted** and is no
longer a blocker for these two LIF
tracks. NxTF remains excluded.

### P06 acceptance policy

- Distinguish **published LIF methodology**,
  **project-trained model**,
  **source-level integer oracle**,
  **compiler/HLS image structural acceptance**,
  **actual KV260 inference** and
  **measured FPGA performance**; none
  implies the next.
- Preserve P05/HLS acceptance goldens; P06
  changes require independent regressions.
- Freeze each track's model and official-test
  protocol before evaluating the sealed test
  set; model A and B have **different
  project-trained checkpoints**, so
  differences in accuracy are not pure
  hardware efficiency comparisons.
- Proceed in the A→B order stated above.
  **P06 Track A (A1–A4) is CLOSED / USER-ACCEPTED 2026-10-17.**
  A4.2 completed the static P02.1 512KiB DDR record native audit.
  Exact P06-A4 DDR full-file SHA256 still needs provenance
  capture in that historical phase manifest; this does not reopen
  the accepted numerical/byte-layout gate. **Track A P07-A
  official TEST 94.56% FPGA inference and P08-A physical baseline
  subsequently passed**. B2 official TEST remains SEALED;
  27-core P07-B and P08-B remain untested physically.

**Detailed execution/resource contract:**
`docs/P06_TWO_TRACK_LIF_PLAN.md`.
See also `docs/P06_LIF_FEASIBILITY.md`,
`docs/P06_LIF_NATIVE_GATE.md`, and
`docs/P06_LIF_CANDIDATE_PROFILE.json`.

---

# P07 — Board-local classifier evaluation: compact first, scaled second

**Status (2026-10-19): P07-A and P08-A separately physically ACCEPTED;
P06-B1/B2 host software MERGED and accepted; P07-B is the NEXT
ACTIVE DEVELOPMENT PHASE, with scaled KV260 physical execution still
NOT TESTED. Branch new P07-B implementation from merged `main`.**
P07-A establishes the frozen compact Track A
784→32→10, 816 registered input axons, 42 compartments,
25 input + 1 drain timesteps, A53-orchestrated physical
FPGA inference and exact independent packed P03 numerical
verification. **Official canonical MNIST TEST accuracy:
9456/10000 = 94.56%; 544 incorrect; 2 all-silent
included in the denominator.** These are original-order
canonical TEST results from the **actual KV260 FPGA**,
not TRAIN validation, simulation-only parity, a competing
Intel Loihi chip or a power/throughput measurement.
Complete immutable user-submitted terminal marker
transcripts, paths, hardware identifiers and scope:
`docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.

## P07-A engineering and physical acceptance milestones

**A1 — COMPLETE:** accepted pixel-to-axon ingress
wire contract, original 784 distinct pixel axons,
26-tick event-input reconstruction and independently
checked Python/C neural transaction representation.
No change to the frozen P06 Track A checkpoint.

**A2 — COMPLETE:** accepted C11 standalone A53
FPGA inference runtime, verified against independent
packed P03 reference and physically accepted
FPD128 routed KV260 fabric. The historical
16-image JTAG-batch implementation required 625
separate launches for the originally precommitted
canonical full 10,000 TEST population.

**A3.1/A3.2/A3.3 — COMPLETE:** TRAIN-derived
validation and physical equivalence, accepted
original eight 16-image PRIMARY A53 runs and two
independent old-format repeats; **116/128 correct
(90.625%) diagnostic TRAIN-derived validation**,
zero silent. The 16-image A3.2 overlap is part of
the same 128, not additional unique validation
images. Frozen original A3.3 hardware records
were retained for the later A4 physical-to-
physical equivalence check.

**A4.1 — COMPLETE / PRECOMMITTED BEFORE UNSEAL:**
exact **10,000 canonical official TEST images**
in original IDX order, frozen compressed official
archive MD5/IDX identity, all-image 10000
denominator, trained checkpoint/encoder, numerical
policy, tie/silence rule, source validation and
whole-population scoring. No retuning, post hoc
selection or reduced denominator permitted.
See `docs/P07_A4_OFFICIAL_TEST_PROTOCOL_FREEZE.md`.

**A4.2a/b — COMPLETE:** user-accepted persistent
DDR transport (`P07A4P01` descriptor,
up to 10000 ×784B raw images,
`P07A4R01` 1MiB CRC journal, one selected
64KiB trace), Python+C native parity,
standalone Cortex-A53 Vitis build, exact
accepted ELF SHA256
`dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`,
XSA SHA256
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`,
and frozen immutable master DDR SHA256
`9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
The original accepted A53 A2 application, P03 neural
arithmetic and trained checkpoint were not rebuilt
or modified for this persistent execution.

**A4.2c — COMPLETE / PHYSICAL KV260:** accepted one
synthetic 16-image ramp pilot with exact physical
26×10 output and selected full trace; accepted
persistent TRAIN-derived 128-image PRIMARY
with byte-exact comparison to eight original A3.3
physical primary mailboxes; accepted independent
cold reboot 128-image repeat with byte-identical
full 1MiB journal and 64KiB selected frame0
26×42 trace; accepted one-launch **1024 distinct
TRAIN-derived validation images** with a full
last-image (frame1023) compartment trace,
then independent reboot repeat: **2/2 launches,
2048 physical frame executions across 1024 unique
validation images**, full journal 1MiB and
selected trace 64KiB byte-identical.
See `docs/P07_A4_2C_VAL128_RESTART_ACCEPTANCE.md`,
`docs/P07_A4_2C_VAL1024_RESTART_ACCEPTANCE.md`.

**A4.2c FINAL FAIL-CLOSED PHYSICAL GATE — ACCEPTED
2026-10-17:** original six DDR staging readbacks
exact on **synthetic ramp16 only**, then deliberately
change exactly one reserved descriptor 32-bit word at
`0x43FE0090` after provision and BEFORE A53
dispatch. The unchanged accepted ELF returned
`0xDEAD0001`, **zero completed image frames**,
**zero result body bytes and zero selected trace**;
independent original mutation/provision, journal CRC
and terminal failure evidence verifier passed.
`P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1`,
`P07_A4_2C_NEGATIVE_TEST_PASS=1`.
Original physical evidence:
`/tmp/v3_p07_a4_fail_closed_20261017T204554`
on user's PC. This is expected intentional rejection,
**not an inference success**.
See `docs/P07_A4_2C_FAIL_CLOSED_PROTOCOL.md`.

**A4.3 — COMPLETE / CANONICAL OFFICIAL TEST UNSEALED
AFTER A4.2c FAULT ACCEPTANCE:** the independently
accepted physical fault record and explicit
`--i-accept-unseal` +
`--i-accept-one-trace-policy` gates preceded
official t10k source staging. Canonical MNIST
TEST original full index range **0..9999**
was checked against MD5/IDX archive provenance
and host-only label ledger; data were not filtered,
sorted, sampled or retrained after test unseal.
No official TEST results were viewed during
pre-unseal native synthetic development.

**A4.4 — COMPLETE / FINAL OFFICIAL CANONICAL
KV260 FPGA FULL 10K PHYSICAL RUN ACCEPTED 2026-10-17:**
one autonomous persistent A53 ELF launch processed all
**10000/10000** raw test images in original IDX order.
The accepted independent closeout gate verified all
10000 CRC-protected physical result records, every
image's full **26×10 output spike-bit history**
(**2,600,000 output bits**), class counts,
silence, next-routing/discarded and external
input events against frozen packed P03 software
oracle, all original six DDR staging readbacks
and exactly one full last-image (IDX 9999)
**26×42 compartment** trace; all exact.
Success marker:
`P07_A4_4_FULL10000_KV260_INDEPENDENT_CLOSEOUT_PASS=1`
and physical terminal `0x600D600D`.
**9456 correct / 10000 = 94.56% accuracy;
544 incorrect; 2 silent / 10000.**
Original physical journal, selected trace
and complete host-only per-image score/provenance
JSON on user's PC:
`/tmp/v3_p07_a4_official_full10000_20261017T204944`;
report:
`p07_a4_4_official_full10000_report.json`.
Only the printed console PASS markers, not actual
raw binary/report per-class contents, were provided
to the assistant. See the separately frozen
`docs/P07_A4_3_4_FINAL_CANONICAL_TEST_PLAN.md`
and final physical acceptance
`docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.

**P07-A PUBLISHED-CLAIM BOUNDARY:** there is only
**one** selected full 26×42 compartment trace
for original official image 9999, unlike the
historical 625 A2 batch-selected traces;
all 10000 complete 26×10 *output* spike histories
and route/count summaries were preserved and
checked. Actual KV260 end-to-end timing,
PS overhead, throughput, rail/board power and
energy remain **P08-A**, and scaled multi-logical
core FPGA physical inference remains **P07-B**
after the P08-A gate. This is a single-core
Loihi-1-*inspired* digital twin, not physical
asynchronous circuitry or Intel Loihi silicon.
No claim of official 10000-image cold reboot
repeatability is made; only TRAIN-derived
128/1024 independent reboot repeatability
is established. Preserve all source/physical
evidence and stable artifact identifiers.

**Next:** P08-A compact physical baseline (required
before Track B scaling), followed by P07-B if
accepted. P07-A feature branch is to be merged
into `main` only with explicit user authorization,
which has been provided after the final hardware
experiments. Merging does not retroactively
validate P08/P07-B results.

## P07-A — One-core proof of useful physical MNIST inference

**STATUS: CLOSED / USER PHYSICALLY ACCEPTED
2026-10-17.** All A1/A2/A3/A4.1–A4.4 entry and
hardware numerical acceptance gates passed; final
full original-order canonical TEST classification
result **9456/10000 (94.56%)**, 2 all-silent.
See `docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.

Using frozen Track A 784→32→10 weights and event input,
extend (not replace) the accepted A53 P05 diagnostic path
to support **many different external axon IDs per timestep**
instead of its current one registered valid axon/core,
image streams and autonomous per-image state/packet/
readout reset. Execute the exact 25+1-step protocol and
produce independent FPGA predictions from real 10-output
spike counts. Verify full-model compiler/runtime
fingerprints, image provenance, first-mismatch
timestep/current/voltage/packet traces and independent
golden predictions. Run the sealed official test
population only after the model/accuracy protocol
is frozen; if the full 10,000-image test isn't feasible,
predeclare the reduced test scope **before**
reviewing test predictions.

**Gate:** useful trained model actually
running inference on the **physical PL** under
autonomous A53 scheduling, not a simulated
test that only checks packed memory.

## P07-B — Scaled multi-logical-core physical inference

**ACTIVE / PARTIAL REAL KV260 HARDWARE PASS (2026-10-23 UTC); NOT CLOSED.**
P07-B.4l's first frozen 27-core **physical scheduler epoch** is now
user-attested PASS: original 27 context full DDR readbacks, genuine
16KiB binding descriptor, accepted P03 PL, standalone A53,
**27 physical dispatches, 27 page-ins, 24 dirty page-outs** and
strict independently verified 256B physical mailbox. The **first
global barrier remained pending/unacknowledged**, **0 P03 spike words**
were captured (empty CURRENT input), and no 26-tick inference or
board/reference numerical parity was attempted. See
[physical B4l first-epoch evidence ledger](docs/P07_B4L_2026_10_23_FIRST_REAL_B3_EPOCH_ACCEPTANCE.json)
and [consolidated B4l deployment/next gate](docs/P07_B4L_CONSOLIDATED_MODEL_DEPLOYMENT.md).
**P07-B.4m consolidated full-inference SOFTWARE CANDIDATE now implemented,
but NOT physically accepted.** The new C11 path uses real P03 adapter
B4a CURRENT from frozen B1.3 ingress, **dispatch-time independent HLS
trace bank 7 / state bank 1 per-compartment spike verification**, B3c1
canonical B2b packet validation, B3c3 physical NEXT insertion and
B3c2 global barrier ACK. The separate 26-tick runner includes **702
dispatches, 26 barriers, final 3 dirty slot flushes, and readout
spike-tally classification**, all regression-tested against the
**original native fake P03 MMIO/DDR harness**, not the KV260.

Separate frozen B2.4 host-only route/input/three TRAIN validation
witness packer, strict C SHA/route table parser, standalone NEW
`p07_b4m_full_26tick` A53 source, offline Vitis build script and
independent 256-byte full-run mailbox verifier are added. The original
physically accepted B4l first epoch/ELF remains unchanged; the new
firmware is **not built or physically run yet**. Must first verify
original frozen stage/route counts on user PC, obtain and inspect
genuine new ELF PT_LOAD/low-DDR ownership, implement independently
verified physical input/route staging with new approvals and evidence,
run complete physical TRAIN validation, and independently cross-check
all signed24 per-neuron/packet/readout traces with source oracle.
**P07-B.4m physical inference/parity, P07-B.5 validation, P07-B.6
closeout/P08-B handoff remain OPEN.**

**2026-11-01 ENTIRE P07-B — FORMALLY COMPLETE / FINAL USER ACCEPTED ORIGINAL TRAINED 27-CORE BOARD-LOCAL PHYSICAL INFERENCE + REPRODUCIBILITY HANDOFF:**
B6.1 real operator-sealed SHA manifest (33 original frozen B2.4
assets, 27 original P02 contexts and all five accepted real KV260
sessions) PASS. B6.2 genuine copied 5-session portable source/firmware/
XSA/evidence package PASS: the original full physical evidence
`/home/dna/Thesis_Evidence/p07_b6_full_reproducibility_20261101T233311Z`
was created and independently rehashed every file + length, including
original accepted V3 and distinct B5 A53 ELF/map, P03 shell and
original signed TRAIN routes; archive manifest SHA256
`73491c0e4f1708ba726cb15e2fd64312d55b002c7d507f6ef0a0d868424fe431`;
independent archive audit SHA256
`10399bc72bef7ce14db04e85685f2099ae2ab6f5461f6d0712fd7b4918111907`.
B6.3 separate **REAL** operator `--mode review` and then
`--mode accept` source-backed final gate PASS. Accepted original
operator report:
`/home/dna/Thesis_Evidence/p07_b6_3_final_operator_accepted_20261101T233410Z.json`.
`P07_B5_final_operator_acceptance_revalidated=true`,
`P07_B6_1_original_source_and_five_physical_evidence_seal_revalidated=true`,
`P07_B6_2_full_portable_archive_independent_bytewise_verifier_pass=true`,
`P07_B6_final_hardware_freeze_accepted=true`,
`operator_final_P07_B_acceptance=true`,
**`P07_B_complete=true`** and **`P08_B_started=false`**.
Original 26-tick/1,010-neuron entire TRAIN0 real physical 840320B
SHA256 `7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`
remains identical to original independent scalar. Original trained
model, 27 original 512KiB contexts, P03 XSA and both historical
A53 firmware SHA identities frozen; four original V3 sessions 0/1/2/0
plus one genuine separate original TRAIN0 B5 RAW0 physical session.
**Preserved bounded original claims:** packet counts not full every-
packet-word parity, DDR/Linux/boot exclusive ownership unproven,
board power cycles operator-attested (not hardware instrumented),
Loihi fully asynchronous equivalent not claimed, original official
MNIST TEST **SEALED_NOT_ACCESSED** and P08-B benchmarks not started.
[Final user-accepted exact B6.3 P07-B completion ledger](docs/P07_B6_3_2026_11_01_FORMAL_OPERATOR_ACCEPTED_P07_B_CLOSEOUT.json).
[Accepted B6.3 reproducibility / P08 sealed handoff](docs/P07_B6_3_FINAL_HANDOFF_P08_BOUNDARY.md).
The user's final `github_main_merged=false` marker documents the
state **at B6.3 acceptance**, not whether a subsequent GitHub merge
has occurred. **Final P07-B approval includes explicit operator
request for ordered normal PR merges #49→#50→#51 into `main`**, with
independent main-only `LitReview.md` Git blob
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e` remaining exactly
unchanged before and after each merge. Never reset, force push or
replace `main` with a stale development branch. Do not unseal TEST.
Historical earlier P07-B-in-progress entries below are retained in
chronological development history and superseded by this final result.

**2026-11-01 P07-B.6.1 REAL 33-ORIGINAL-FROZEN-ASSET / FIVE-PHYSICAL-SESSION INDEPENDENT SEAL PASS; B6.2 COMPLETE PORTABLE ARCHIVE VERIFIER AND B6.3 FULL P07-B FINAL ACCEPTANCE GATE IMPLEMENTED (DRAFT PR #51):**
The operator ran genuine B6.1 `scripts/p07_b6_freeze_manifest.py --mode seal`
with original signed B2.4 frozen 33-asset tree, original signed
routing, accepted P03 XSA and distinct B5 ELF/map, all five real
source-backed 27-core physical sessions, and actual separately
operator-accepted B5.4 final report and cold-reboot attestation.
Genuine source report:
`/home/dna/Thesis_Evidence/p07_b6_original_freeze_seal_20261101T230852Z.json`.
Markers included
`P07_B6_ORIGINAL_27CORE_SIGNED_SOURCE_ARTIFACT_FREEZE_INVENTORY_PASS=1`,
`P07_B6_B5_FORMAL_ACCEPTANCE_INDEPENDENTLY_RECHECKED=1`,
`P07_B6_KV260_BOARD_CONTACT=0`, original TEST SEALED,
`P07_B6_FINAL_ACCEPTANCE=0` (intentionally).
[Reported exact B6.1 acceptance ledger](docs/P07_B6_1_2026_11_01_REAL_33_ASSET_FREEZE_SEAL_PASS.json).

The operator also located physically accepted original V3 A53
`p07_b4m_diag_v3_26tick.elf` (SHA
`66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`)
and original V3 linker map (SHA
`148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede`)
in `/home/dna/p07_b4m_diag_v3_build_20261101T034702Z/vitis_workspace/`.
Distinct original B5 RAW A53 original SHA and P03 XSA remain pinned.

**B6.2 tools implemented but NO real operator package COPY or
independent full archive PASS evidence has yet been supplied:**
`scripts/p07_b6_reproducibility_bundle.py` must create a separate
SHA-recorded copy of all 33 original frozen assets + frozen manifest,
frozen TRAIN routes + ingress, P03 XSA, original V3/new B5 firmware,
original B5.4 signed acceptance/attestation, the actual B6.1 seal,
and all 5 real physical evidence directories. A separate
`scripts/p07_b6_verify_reproducibility.py` must independently
rehash ALL archive files, reject extra/missing/symlink entries,
rerun the original frozen native 33-asset gate and authenticate
actual 840,320B neuron physical SHA and original firmware.

**B6.3 final bounded original P07-B handoff code IMPLEMENTED:**
`scripts/p07_b6_final_handoff.py` in `review` mode replays independent
full B6.2 archive checks, binds original source B6.1 seal +
accepted B5.4 attestation SHA, and checks exact independent
`origin/main:LitReview.md` Git blob.
`accept` mode additionally requires a distinct explicit final
operator P07-B original 27core physical handoff token.
No final `P07_B_complete=true` report yet; wait for genuine
B6.2 original physical source package + review and final operator
approval, **not** native synthetic/mock tests.
[Full B6.3 acceptance and P08-B protocol boundary](docs/P07_B6_3_FINAL_HANDOFF_P08_BOUNDARY.md).
Original 27core FPGA source/XSA/ELF/TEST SEALED; no board run,
no unsealing, no automatic P08-B benchmarking, and **no main merge**.
PR #51's B6 development branch now incorporates the accepted
B5 branch history in a normal two-parent commit; it remains
draft and unmerged from main. The independently committed
`main:LitReview.md` original Git blob
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`
must be byte-preserved by any later user-authorized
dependency-order PR #49→#50→#51 merge.

**2026-11-01 P07-B.5 FINAL ACCEPTANCE PASSED; B6.1 OPERATOR INVENTORY PASS; B6.2 COMPLETE REPRODUCIBILITY PACKAGE CODE IMPLEMENTED / REAL COPY PENDING (PR #51):**
Operator ran actual `scripts/p07_b5_final_acceptance.py --mode accept` after
supplying personal five-run cold-powercycle/JTAG/recovery/residual DDR risk
attestation. Report
`/home/dna/Thesis_Evidence/p07_b5_4_accepted_20261101T224134Z.json`
returned `P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=1` and
`P07_B5_final_acceptance=true`, including all 5 signed physical
sessions, four original V3 0/1/2/0 and fifth new B5 physical RAW0.
26×1010×32=840320 original TRAIN0 physical neuron trace/scalar SHA256
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`;
original TEST SEALED; frozen original B2.4 27core and P03 PL/V3 unchanged.
Attestation SHA256
`4dd6cf0d02c477a2992b55b8bc2454ee9800c94ccce78f6cee25a32f2dc7fa31`.
**P07-B.5 formally CLOSED** within its numerical/physical acceptance
scope; unproven DDR exclusive ownership, operator-attested (NOT
independent hardware-instrumented) cold power cycles, and incomplete
per-packet-word physical trace comparison remain explicit limitations.
[Final B5 acceptance ledger](docs/P07_B5_4_2026_11_01_FINAL_OPERATOR_ATTESTED_ACCEPTANCE.json).

Operator ran B6.1 `--mode inventory` and achieved
`P07_B6_ORIGINAL_27CORE_SIGNED_SOURCE_ARTIFACT_FREEZE_INVENTORY_PASS=1`
with `P07_B6_FINAL_ACCEPTANCE=0`. This initial report predates
B6.1 full 33-file signed freeze inventory tightening. Latest
`scripts/p07_b6_freeze_manifest.py` now rehashes all 33 signed frozen
original B2.4 assets + original manifest, signed TRAIN routes/frames,
P03 XSA, new B5 ELF/map; `--mode seal` REQUIRES real original B5.4
accepted report and attestation and freshly independently reopens
all five actual physical sessions before issuing a SHA-pinned, bounded
external B6.1 seal. **Operator B6.1 sealed file not yet received.**

**B6.2 IMPLEMENTED / PHYSICAL FILE COPY PENDING:**
`scripts/p07_b6_reproducibility_bundle.py` strictly requires B6.1
actual operator seal, genuine B5 acceptance, original historical V3
ELF/map byte SHA identities (distinct from new B5), verified original
full 33-file signed freeze, exact 3 TRAIN ingress/route pack, P03 XSA,
all five original physical evidence source trees, and real
`origin/main:LitReview.md` original independent Git blob.
Copies EVERY unchanged selected source/evidence file to a NEW
external output folder, stores exact SHA256/byte lengths for each, then
independently SHA-rechecks copied bytes. Does not run FPGA, modify
signed original model, unlock official TEST or merge anything.
[Detailed B6.1 seal and B6.2 exact copy/runbook](docs/P07_B6_FINAL_HARDWARE_FREEZE_AND_HANDOFF.md).

**P07-B.6.3 final independent handoff and overall P07-B COMPLETE are
still OPEN.** Draft PR #49→#50→#51 remain unmerged; main-only
`LitReview.md` Git blob
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`
must persist unchanged after any eventual authorized normal PR merges.
No merge to main before complete P07-B operator acceptance.

**2026-11-01 P07-B.5.4 OPERATOR ATTESTATION FILLED ON PC; FORMAL GATE PENDING. P07-B.6.1 IMMUTABLE SOURCE/HARDWARE EVIDENCE FREEZE CANDIDATE DEVELOPMENT STARTED (DRAFT PR #51):**
User reported they created a local external copy of the five-real-session B5.4
attestation template and changed every `null` to `true`, and approved
moving on to P07-B.6; they explicitly reaffirmed no merge until the
entire P07 track is finished. This is a genuine operator statement,
**not** the verified bytes of the actual external attestation file or a
`p07_b5_final_acceptance.py --mode accept` terminal PASS. B5.4 source
gate MUST independently re-open all five real physical sessions, inspect
the exact operator attestation's five paths and booleans, acknowledge
unproven DDR/boot exclusive ownership, and write its own signed
write-once `P07_B5_final_acceptance=true` report before formal
B5 closure. No false hardware cold-boot instrumentation claim is allowed.
See [B5.4 operator final acceptance command and evidence requirement](docs/P07_B5_4_FINAL_INDEPENDENT_REVIEW.md).

**P07-B.6.1 preparation** now proceeds separately in draft
`agent/v3-p07-b6-final-freeze-handoff` / PR #51, based on draft
PR #50 (itself based on #49). New
`scripts/p07_b6_freeze_manifest.py`:
`--mode inventory` (safe immediately) rechecks the entire original
**33-file signed B2.4 freeze**, 27 logical P02 cores, 20,384
input/1,000 output routes and all three original TRAIN images,
real routed P03 XSA, accepted distinct B5 ELF/map, genuine original
five-session numerical review source, and computes a whitelisted
SHA256 manifest for reproducibility. It explicitly labels B5 final
acceptance, B6 production freeze, full P07 completion and merge as
**NOT YET VERIFIED**. Later `--mode seal` requires both the actual
operator-approved B5.4 final report and actual five-run operator
attestation and **re-executes the real B5.4 five-source physical evidence
re-verification**, then compares the operator-signed report exactly.
Neither path touches KV260, changes official TEST or merges Git.

B6.2 reproducible hardware/ELF/XSA/DDR/trained protocol packaging and
B6.3 final independent operator freeze/P08-B handoff are **OPEN**.
See [P07-B.6 hardware freeze and handoff engineering plan](docs/P07_B6_FINAL_HARDWARE_FREEZE_AND_HANDOFF.md).
All PRs #49, #50 and #51 remain draft and unmerged; `main` retains
its independent `LitReview.md` Git blob SHA
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`. Merge must preserve
that exact blob, via normal ordered PR merges, **only after complete
P07-B acceptance and explicit operator merge authorization**.
Official MNIST TEST remains SEALED.

**2026-11-01 P07-B.5.4 OPERATOR INDEPENDENT FIVE-PHYSICAL-SESSION NUMERICAL REVIEW PASS, BUT FORMAL FINAL ACCEPTANCE NOT YET RECORDED — MAIN MERGE DEFERRED:**
Operator ran the REAL PC-only `scripts/p07_b5_final_acceptance.py --mode review`
and supplied complete report
`/home/dna/Thesis_Evidence/p07_b5_4_final_numerical_review_20261101T220745Z.json`.
Five real source-signed board sessions reverified: original V3 TRAIN
ordinals `0/1/2/0` with exact 26-tick FNV64, counts and original
TRAIN0 deterministic repeat; fifth independent B5 RAW0 26×1010×32B
**840,320-byte exact physical neuron/scalar parity**, SHA256
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`;
7/7 independent counters/trace/readout checks PASS, same-session original
signed 27-core DDR / route / TRAIN0 physical readback verified. Report
independently pins the original four-run summary SHA256
`f1dc383f4f4e316fca4cb5c6175e129347dfeb3fa4f9982de2c4ada412cc1ada`
and physical RAW0 verifier report SHA256
`0c37aee136c218216eb01926b8a50ad67fb81833d4aa2c6feb096be6aa68106c`.
`P07_B5_4_FIVE_PHYSICAL_SESSIONS_ORIGINAL_SIGNED_NUMERICAL_GATE_PASS=1`,
`P07_B5_4_840320B_REAL_RAW_NEURON_PARITY_PASS=1` and original TEST
still SEALED. [User-supplied five-run B5.4 numerical-only ledger](docs/P07_B5_4_2026_11_01_FIVE_SESSION_NUMERICAL_REVIEW_PASS_NOT_FINAL_ACCEPTANCE.json).
**Do NOT mark B5.4 or P07-B.5 accepted yet.** Actual report retained
`operator_attested_cold_boot_and_recovery_all_five_sessions=false`,
`operator_explicit_final_B5_acceptance=false`,
`independent_board_powercycle_instrumentation_proof=false`,
`boot_firmware_and_other_DDR_owner_independently_proven=false`,
and `P07_B5_final_acceptance=false`.
Actual operator-reported session-by-session cold-powercycle/recovery and
residual DDR owner risk disclosures plus explicit final B5 approval are
required by the source-controlled B5.4 gate; conditional conversational
merge request must not silently fabricate them. P07-B.6 final scaled
hardware freeze/handoff is separately OPEN, so the overall P07-B branch
is NOT complete. [B5.4 formal approval process](docs/P07_B5_4_FINAL_INDEPENDENT_REVIEW.md).
**Main branch literature protection:** `main` is diverged by one
main-only commit containing 403-line `LitReview.md` with blob SHA
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`.
No merge or rewrite of `main` was performed; PR #49 has base `main`,
PR #50 has base PR #49 branch. After final P07-B.5 and P07-B.6 approval,
merge in order **#49 then #50** via normal GitHub merge and prove the
literal `LitReview.md` blob SHA remains unchanged. No force/reset,
branch replacement or source overwrite, and no unsealing official TEST.

**2026-11-01 P07-B.5.3 AUTHENTICATED REAL PHYSICAL 840320B ORIGINAL TRAIN0 NEURON-BYTEWISE PARITY PASS; B5.4 FINAL ACCEPTANCE REVIEW IMPLEMENTED, REBOOT OPERATOR SIGNOFF OPEN:**
Operator ran distinct new B5 RAW A53 27core original TRAIN ordinal0
(index **37384**) and independently verified real same-session signed
27×512KiB physical context + 16KiB binding + original output/input
routes and ingress TRAIN0 readbacks. Genuine new ELF/map SHA
`0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf`/
`1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8`;
original B5 terminal 256B physical mailbox SHA256
`435b1c903f3323b3bfd156eb271202d82c8738ebe2a7a8c489e6aab7fcdd4d6b`.
**Actual physical 26×1010×32B = 840320B = 26260 neuron words**
byte-for-byte matched independently regenerated signed original scalar
trace; physical/scalar SHA256 both
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`.
Original FNV64 `0xB59CA8594D6E64AD`, **all 26 tick fingerprints**,
**all seven independently checked metrics** exact; 702 real physical
HLS dispatches, 26 barriers, 702 page-ins, 699 dirty + 3 final outs,
source spikes 1514, external CURRENT events 31512, packet/NEXT **counts**
1489 each, votes 25 for class1. **B5.3 selected FULL RAW NEURON
numerical parity ACCEPTED**, not just prior noncryptographic FNV64.
No claim of *every individual routed packet word* trace parity.
[Operator original physical B5.3 signed source/terminal/raw acceptance ledger](docs/P07_B5_3_2026_11_01_REAL_ORIGINAL_TRAIN0_840320B_PHYSICAL_RAW_NEURON_PASS.json).
Original V3 ELF, accepted P03 FPGA PL, frozen B2.4 model and
OFFICIAL MNIST TEST unchanged/SEALED.
**B5.4 NEXT:** source-controlled
`scripts/p07_b5_final_acceptance.py` PC-only reviewer freshly
reopens all FOUR previous original V3 0/1/2/0 genuine signed physical
sessions AND the FIFTH authenticated physical B5 RAW0 session, requires
exact original report consistency, and refuses milestone closeout
without explicit operator attestation of fresh cold power cycles before
and after all five sessions, dedicated JTAG, no resumed halted Linux,
independent numerical signoff and explicit residual DDR/boot ownership
risk acknowledgment. The source-controlled operator attestation template
has no pre-approved `true` facts. No physical DDR exclusivity or independent
hardware clock proof fabricated. [B5.4 final review/runbook](docs/P07_B5_4_FINAL_INDEPENDENT_REVIEW.md).
**Do NOT mark P07-B.5 or full P07-B closed yet; B5.4 formal user
acceptance and P07-B.6 freeze/handoff remain open. No main merge; draft
PRs #49/#50 preserved.** Prior earlier PC-only preflight and engineering
records below are historical, superseded in status by the actual real
B5.3 physical neural trace parity PASS above.

**2026-11-01 P07-B.5.3 ORIGINAL TRAIN0 B5 RAW A53 PC PREFLIGHT PASS; PHYSICAL DDR OWNERSHIP REVIEW REQUIRED BEFORE BOARD EXECUTION:**
Operator ran the separate B5.3 RAW runner with `--mode preflight`
and reported `P07_B5_NEW_RAW_GENUINE_A53_ELF_MAP_AND_ORIGINAL_TRAIN_HOST_PASS=1`,
`P07_B4M_DIAG_V3_ALL_27_ORIGINAL_P02_METADATA_COUNTS_HOST_VERIFIED=1`,
`P07_B5_NEW_RAW_PC_ONLY_PREFLIGHT_PASS=1` and
`P07_B5_BOARD_CONTACT=0`. The same report intentionally retained
`P07_B5_NEW_RAW_840320B_DDR_OWNER_INDEPENDENTLY_PROVEN=0`,
`P07_B5_NEW_LOW_DDR_0_TO_0x107BC0_EXCLUSIVITY_PROVEN=0`,
and `P07_B5_NEW_RAW_LAUNCH_AUTHORIZED_BY_PREFLIGHT=0`.
**Risk review finding:** Original `p03_hw_adapter.h` defines a broad
64MiB P03 DDR backing aperture `[0x40000000,0x44000000)`, within
which the new B5 840320B raw capture candidate
`[0x42000000,0x420CD280)` AND B5 256B mailbox
`[0x43FF0100,0x43FF0200)` lie. They are disjoint from the
27×512KiB original P02 context records, but that narrow geometry
is NOT physical exclusive ownership relative to Linux, boot firmware,
other APU/RPU or DMA users. Corrected B5 ELF changes original V3
low-DDR footprint `[0,0x00106B00)` to `[0,0x00107BC0)`, plus
4,288 bytes, also with independently UNPROVEN boot-firmware exclusivity.
New host-only SHA-pinned `scripts/p07_b5_raw_ddr_risk_review.py`,
`tests/test_p07_b5_raw_ddr_risk_review.py` and
[dedicated operator hardware ownership review](docs/P07_B5_3_OPERATOR_PRE_EXECUTION_MEMORY_REVIEW.md)
identify and preserve each unproven ownership condition. This
review does NOT contact KV260 or grant a physical launch; 8 old
and 5 new explicit approvals are still required after operator
risk assessment and recovery planning. **No B5.3 raw board run has
occurred**; strict 26,260-record physical/scalar byte equality,
B5.4 final acceptance and P07-B closure remain OPEN. Do not merge
PR #49 or #50 with `main` until whole P07-B is completed and
operator explicitly signs off.

**2026-11-01 P07-B.5.3 genuine corrected B5 RAW A53 ELF/map PC-ADMITTED; dedicated B5 capture and physical-raw parity infrastructure IMPLEMENTED / NATIVE-ONLY:**
Operator separately rebuilt the corrected new B5 raw-trace A53 application
and independently passed exact frozen original 27core/source SHA, original
accepted PS/PL routed P03 XSA, TRAIN input and **real linked ELF/map**
PC-only admission: `P07_B5_GENUINE_RAW_CAPTURE_VITIS_SOURCE_ELF_OFFLINE_PREFLIGHT_PASS=1`.
Genuine new ELF SHA `0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf`;
map SHA `1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8`;
A53 low-DDR footprint `[0x00000000,0x00107BC0)` (1,080,256 bytes),
raw sidecar candidate `[0x42000000,0x420CD280)` (840,320 bytes),
new B5 mailbox `[0x43FF0100,0x43FF0200)` (256 bytes).
[Operator genuine admission ledger](docs/P07_B5_3_2026_11_01_REAL_VITIS_RAW_ELF_PC_ADMISSION.json)
retains all exact identity proofs and explicitly proves **no** physical
board/raw neuron execution, no DDR physical owner exclusivity and no
permission inferred from the successful build.
Dedicated B5 physical `vivado/p07_b5_raw_trace_xsdb_run.tcl`,
`scripts/p07_b5_raw_physical_capture.py` (PC-only default preflight,
13 distinct operator approvals before destructive execution) and
`scripts/p07_b5_raw_physical_verify.py` (independent original 27core
readback provenance + 256B B5 mailbox + original signed scalar **840320B
per-neuron exact bytewise parity**) are now source-controlled with
host-only negative safety tests. No KV260 run attempted via these.
Physical raw capture, DDR owner risk acceptance and real reboot witness
**still OPEN**. Original V3 ELF and route/input sources untouched,
original official MNIST TEST sealed; B5.4/B6/P08-B remain gated.
Nothing merged into `main`, PR #49/#50 remain drafts.
See [B5.3 hardware capture/readback and PC-only runbook](docs/P07_B5_3_RAW_TRACE_CAPTURE_DEVELOPMENT.md).

**2026-11-01 P07-B.5.3 genuine first Vitis build succeeded; offline admission correctly rejected stale V3 runtime ID (FIXED IN NEW SOURCE, REBUILD REQUIRED):**
Actual Vitis 2025.2 source/ELF/map build emitted
`P07_B5_RAW_A53_ELF_AND_MAP_BUILT=1` in
`/home/dna/p07_b5_raw_trace_build_20261101T202750Z`, with no
board execution. Offline preflight returned
`P07_B5_NEW_RAW_OFFLINE_NO_GO=NO-GO: experimental B5 ELF polluted by original firmware identity`.
Source review found an old `P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3`
**runtime xil_printf** in otherwise correctly named new B5 firmware;
the existing strict checker was CORRECT to fail. Changed B5-only status
print to `P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1`, retained binary
identity scan, added source-stage / post-link preflight checks and
native negative regression. Old genuine Vitis ELF/map are preserved but
**not admitted**, must not be executed, and cannot be patched; operator
must build a new isolated B5 ELF/map, then re-run PC-only admission.
No acceptance of physical DDR ownership or B5 raw neuron parity.
[Detailed diagnosis and fix](docs/P07_B5_3_RAW_TRACE_CAPTURE_DEVELOPMENT.md).
All P07-B work remains on draft PRs #49/#50, no merge to `main`.

**2026-11-01 P07-B.5.3.2 separate RAW trace A53 integration — PC NATIVE COMPLETE, VITIS/BOARD NOT YET VERIFIED:**
User independently generated original frozen TRAIN0 **840,320-byte** host
scalar trace, SHA256 `7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`,
FNV64 `0xB59CA8594D6E64AD`, original monolithic trace SHA
`4bef8f76965d4080a7c4ec2f3feab7c805e636d6397afb80a4a09f07733aea35`.
This is a strong original signed scalar reference, **NOT physical trace**.
Original user evidence:
`/home/dna/Thesis_Evidence/p07_b5_train0_expected_raw_20261101T200800Z.bin`
and [scalar reference ledger](docs/P07_B5_3_TRAIN0_SCALAR_RAW_ORACLE_USER_ACCEPTANCE.json).
Separate, new B5-only A53 diagnostic source
`P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1` now integrates
an actual P03 bank7/bank1-verified raw trace capture at each
original dispatch hook *before* HLS slot eviction, with 26x1010
strict-order raw records and final 840320-byte flush. Unique B5
candidate mailbox `[0x43FF0100,0x43FF0200)`; trace sidecar
candidate `[0x42000000,0x420CD280)`. Both physically **UNAUTHORIZED**
until independent DDR owner admission and new per-run approvals.
New isolated Vitis build sources and PC-only exact original source/ELF/map/
XSA/route admission exist; **operator has NOT built the distinct
B5 ELF/map with real Vitis**, and no new B5 physical launcher/board
capture/physical SHA has been produced. The accepted original V3 ELF,
P03 PL/RTL, B2.4 freeze, TEST seal and four-run B5.2 physical
receipts remain unmodified. New native GCC C hook+capture integration
exercises 26,260 simulated trace records, actual bounded serializer,
and fail-closed corrupt/mismatched P03 metadata cases. CI-native
result must not be reported as genuine FPGA readback.
See [B5.3 new firmware/offline build handoff](docs/P07_B5_3_RAW_TRACE_CAPTURE_DEVELOPMENT.md).
P07-B.5.3 remains **IN PROGRESS**; B5.4/P07-B.6/P08-B remain gated.
Draft PR #49 and #50 UNMERGED; no `main` changes until complete
P07-B and explicit operator approval.

**2026-11-01 P07-B.5.2 FOUR GENUINE ORIGINAL 27CORE PHYSICAL SESSIONS / INDEPENDENT SCALAR FNV64 ACCEPTED:**
User supplied the complete original TRAIN0 repeat verification and full
four-session scalar-vs-physical report, confirming original TRAIN ordinals
`[0,1,2,0]`, each independently checked against original signed 27-core
DDR, routes, exact original frozen 26-tick integer oracle and actual 256B
physical mailbox. Genuine 702 HLS dispatches/26 barriers **per image**;
all seven original scalar/physical numerical checks **TRUE** for all four.
Consolidation `P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1`,
`genuine_independently_verified_sessions=4`,
`distinct_train_validation_frames=3`,
`all_three_distinct_frames_scalar_vs_physical_equal=true`,
`train0_repeat_physical_metrics_and_FNV64_equal=true`.
Original TRAIN0 repeat predicted class 1, 1,514 original source spikes,
1,489 P03 packets/NEXT inserts, 31,512 external CURRENT events and
physical trace `0xB59CA8594D6E64AD`. Its entire physical 256B mailbox
SHA256 `5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`
was **identical** to the earlier genuine TRAIN0 physical run.
Reports remain on operator PC:
`$HOME/Thesis_Evidence/p07_b5_verify_train0_repeat_20261101T194457Z.json`,
`$HOME/Thesis_Evidence/p07_b5_fourrun_original_train_20261101T194900Z.json`.
[Bounded B5.2 four-session ledger](docs/P07_B5_2_2026_11_01_REAL_FOUR_SESSION_FINGERPRINT_ACCEPTANCE.json).
**B5.1 and B5.2 are ACCEPTED WITH EXPLICIT BOUNDS**; B5.3 direct
840320B *physical* HLS neuron trace readback/bytewise scalar comparison
and separate authentic operator reboot evidence remain OPEN; the existing
B5.2 PC verifier itself states both `false`. Original official TEST
still SEALED and previous V3 ELF/RTL/frozen model unchanged. P07-B.5
final acceptance NOT complete. Distinct B5.3 **native-only C raw trace
recorder** development has started on the same draft PR #50, with a
candidate separate trace sidecar `[0x42000000,0x420CD280)` that has
only been checked for non-overlap against *known original software
DDR ranges*. Actual physical DDR ownership, new Vitis ELF/map hashes,
new dedicated physical launcher, on-board capture/readback, and final
source/trace parity are NOT yet proven or authorized. See
`docs/P07_B5_3_RAW_TRACE_CAPTURE_DEVELOPMENT.md`.

**2026-11-01 P07-B.5.2 real TRAIN2 physical plus scalar numerical PASS:**
The operator's original TRAIN-derived ordinal2 KV260 execution passed
702/702 dispatches, 26/26 barriers, 702 page-ins, 699 dirty plus three
final page-outs. Readout class **1** matched original TRAIN label **1**,
counts `[0,25,0,2,0,0,0,0,1,0]`. Independent frozen scalar comparison
passed all seven checks: 41,990 external input events, 1,484 source spikes,
1,456 P03 packets/1,456 NEXT insertions, and full 26-tick physical
FNV64 `0x9C12E0386A7E41CB` all exact. Raw actual physical mailbox
SHA256 `cdf26c256cd0fbf1c4c901d53cd2caaf3b1a2e3e945a82c64aa354eed7d6e5d6`.
The physically captured original ordinal2 evidence is at
`/home/dna/Thesis_Evidence/p07_b5_train2_real_20261101T192124Z`;
verified scalar report
`/home/dna/Thesis_Evidence/p07_b5_verify_train2_20261101T192721Z.json`;
provenance [ledger](docs/P07_B5_2_REAL_TRAIN2_PHYSICAL_NUMERICAL_ACCEPTANCE.json).
**All three original distinct TRAIN ordinals 0,1,2 now have physical+scalar
fingerprint acceptance**, but B5.2 ordinal0 repeat, four-run consolidation,
B5.3 raw 840320B physical neuron trace, and B5.4 acceptance are OPEN.
Original TEST remains sealed; P07-B.6/P08-B remain gated.

**2026-11-01 P07-B.5.2 genuine original TRAIN1 26-tick physical/independent scalar PASS:**
The operator physically staged all 27 original 512KiB P02 cores, original
16KiB descriptor, 80KiB output/896KiB input route tables and pinned
TRAIN validation **ordinal1** ingress, and independently reread them.
The genuine accepted V3 A53 ELF completed **702 dispatches, 26 barriers,
702 page-ins, 699 dirty and 3 final page-outs**. Readout prediction=**2**
(equal to original TRAIN label2), ten readout counts
`[0,0,25,0,0,0,0,0,0,0]`, 71,994 CURRENT events, 1,852 neuron spikes
and 1,827 P03 packets / 1,827 NEXT insertions. Full trace FNV64
`0x0EAC411F49856BF3` physically equaled independent frozen scalar.
The user's actual independent B5 verifier reported
`P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1` for **this
single physical ordinal1 session**. Physical 256B mailbox SHA256
`4410de8c57df98250b0184d352e8edccaeb74bd23a91610579142a44cabf0d95`;
external evidence `p07_b5_train1_real_20261101T045754Z` and
`p07_b5_verify_train1_20261101T050334Z.json`. Detailed
[ordinal1 provenance ledger](docs/P07_B5_2_REAL_TRAIN1_PHYSICAL_NUMERICAL_ACCEPTANCE.json).
**Historical ordinal1 status (superseded by the later ordinal2 PASS above):**
At this point ordinal0 and ordinal1 were physically verified; the subsequent
ordinal2 result is recorded above. Original ordinal0 reboot repeat,
four-run consolidation and strict 840320B physical raw-neuron trace parity
remain OPEN. No
user-attested cold reboot proof supplied for this run. B5.4/P07-B.6/P08-B
still gated. B2 official TEST SEALED.

**2026-11-01 P07-B.5 operator B5.1/B5.2 read-only acceptance (not new physical runs):**
Original frozen TRAIN validation ordinals 0/1/2 independent scalar replay
**PASS**, marker `P07_B5_THREE_FROZEN_TRAIN_SCALAR_REFERENCE_PASS=1`,
external report `/home/dna/Thesis_Evidence/p07_b5_three_train_reference_20261101T044416Z.json`.
Independent B5 verifier of **existing original genuine ordinal0 physical**
run **PASS**, marker `P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1`,
external report `/home/dna/Thesis_Evidence/p07_b5_verify_train0_20261101T044755Z.json`.
This B5 verifier marker applies only to the evidence run explicitly given,
**not yet** original ordinal1/2 physical or ordinal0 independent restart.
B5.2 new physical runs and B5.3 full raw physical trace acceptance remain
OPEN. Detailed P07-B.4 cross-cutting challenges and exact remedies:
`docs/P07_B4_HARDWARE_BRINGUP_CHALLENGES_AND_RESOLUTIONS.md`.

**2026-11-01 P07-B.5 MULTIFRAME TRAIN VALIDATION STARTED — NOT PHYSICALLY ACCEPTED:**
The operator's genuine original B4m TRAIN validation0 physical evidence
was independently replayed using the frozen source scalar integer oracle,
full 26-tick per-compartment bank7 FNV64 and all packet/input/readout
counters. User confirmed
`P07_B4M_V3_ORACLE_VS_PHYSICAL_ALL_CHECKS_MATCH=1` with external signed
report `/home/dna/Thesis_Evidence/p07_b4m_v3_scalar_parity_20261101T043214Z.json`.
This **completes a bounded single-frame reference fingerprint comparison**;
no raw neuron trace equality or additional physical validation is claimed.
P07-B.5 work has begun on separate draft PR #50
(`agent/v3-p07-b5-scaled-multiframe-validation`), based on still-draft
P07-B PR #49. B5.1 PC-only strict original frozen TRAIN ordinals 0,1,2
scalar replay/checks and B5.2 multi-real-run 0/1/2+independent 0-repeat
host verifier are implemented; they have **not** been run on the operator's
original frozen files or new board evidence. B5.3 signed separate RAW
26×1010 neuron physical trace (840,320 bytes) and B5.4 independent
cold-reboot/user acceptance remain OPEN. See
`docs/P07_B5_SCALED_TRAIN_MULTIFRAME_VALIDATION.md`.
P07-B.6 final freeze and P08-B scaling measurements must not start
until B5 physically validated and user accepted. Official MNIST TEST
remains SEALED; original P03 RTL, B2.4 checkpoint and V3 ELF unchanged.

**2026-11-01 P07-B.4m real V3 trained 26-tick STRUCTURAL PASS:**
Operator reran genuine 27-core TRAIN0 V3 on the physical KV260 after
A53 takeover success. Same-session original frozen model/bindings/route/
TRAIN DDR readback succeeded, V3 A53 ELF executed and independent
256B mailbox structural verification passed. Real 702 dispatches,
26 barriers, 702 page-ins, 699 dirty + 3 final page-outs, 31512
CURRENT events, 1514 bank7 source spikes, 1489 captured/inserted
NEXT packets, 1010 compartments checked per timestep. Physical
readout class=1, counts=`[0,25,0,0,0,0,0,0,0,0]`; trace
FNV64=`0xB59CA8594D6E64AD`. Actual 256B physical mailbox SHA
`5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`.
This strongly supports corrected P08 synapse/route metadata as the
V2 first-dispatch failure fix. **Independent neuron numerical parity
NOT YET VERIFIED**; full raw physical per-neuron transcript not present.
Original frozen TEST remains SEALED. Read-only numerical reference
fingerprint checker `scripts/p07_b4m_v3_train0_scalar_vs_physical.py`
added and awaits operator execution on genuine local V3 evidence.
Keep P07-B.4m open and PR #49 draft until parity is assessed.

**2026-11-01 P07-B.4m V3 preliminary physical takeover attempt:**
Operator's authentic V3 execute passed host-only original 27-core P02
metadata / ELF/route gates, then **failed before FPGA programming, DDR
staging or A53 ELF launch** when the B4i stop/PS-width gate saw XSDB
`Cannot halt processor core: power down`. No physical V3 inference result
exists for this attempt. The historical Tcl only recognized
`The core is powered down`; it now accepts exactly both variants and
runs the original bounded retries + PS FPD/LPD 128-bit checks + guarded
reset / confirmed A53 #0 halt. Native mock recovery/fail-closed tests
added. Evidence preserved in external V3 run folder
`p07_b4m_diag_v3_real_20261101T040103Z`. Board reboot mandatory.
P07-B.4m remains OPEN; avoid classifying this as an HLS error.

**2026-11-01 P07-B.4m physical V2 first-dispatch diagnosis:**
A user-run genuine V2 KV260 session with exact original-model and TRAIN
readbacks failed at stage 9, HLS `P03_DISPATCH_CORE_STATUS=0x4`
(SYNAPSE_ROW_BOUNDS), while `DISPATCH_STATUS=0x22` and one PL
completed dispatch were observed. Scheduler.first_fault=10,
pager.first_failure_kind=3, trace.first_fault=0. The accepted B4l
registration only encodes core ID and compartments; P08 RTL requires
synapse count [33:18] and route count [46:34]. This is a direct,
source-verified software metadata omission consistent with the physical
failure. An isolated V3 firmware repair and native tests were added
without modifying the frozen model/accepted shell. The operator
subsequently built genuine V3 ELF SHA
`66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`
and GNU map SHA
`148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede`,
with EXACT low-DDR PT_LOAD `[0,0x00106B00)`. Strict original-model
V3 offline admission passed. A separate V3 SHA-pinned same-session
hardware launcher and CI mock tests are committed; actual V3 KV260
run and independent parity remain PENDING. Full 26-tick
inference and numerical parity gates still OPEN. Preserve real V2
mailbox SHA `79c20f53664afabd3d349b3dccc0f3fc0f1824706863cb5d1409cb9ce493077d`.

**2026-10-31 P07-B.4m diagnostic V2 continuation (NOT physically accepted):**
The user built the real DIAGNOSTIC_V2 A53 ELF and passed the independent
original B2.4 offline source/route/ELF admission. Exact ELF SHA
`952393251a6910c5ca87b817ffdb2d08c0d5239f0f60b350908a78f375936a45`,
map SHA `864624c6511aa5eba204a89fc2f1e3b8a3a46a434a18baa88753282ef5b131da`;
PT_LOAD `[0x00000000,0x00106B00)`, with low-DDR boot-firmware
exclusivity still unproven. A separately SHA/identity-pinned diagnostic V2
same-session original-model physical runner, XSDB Tcl, and native synthetic
safety tests were added on existing draft PR #49. Physical V2 execution,
complete original 702-dispatch/26-tick inference and numerical parity have
**not** been reported or accepted. See
`docs/P07_B4M_2026_10_31_STAGE9_DIAGNOSTIC_V2_HANDOFF.md`.

See [consolidated B4m development and exact gates](docs/P07_B4M_COMPLETE_INFERENCE_DEVELOPMENT.md).
**Official B2 TEST SEALED.**
P06-B1/P06-B2 are merged, while draft P07-B PR #49 is unmerged.
Track A P07-A and P08-A latency baseline remain separately accepted.

**P07-B entry is a GO for DESIGN and implementation work, not an
authorization to label scaled physical results as accepted or to
unseal the Track B official MNIST TEST.** After P08-A, independently
validate the **real frozen 784→1000→10 signed24 trained P06-B
checkpoint**, **27 logical P02 contexts**, 26 hidden core shards
plus one readout, all within the same **three resident slots and
one physical HLS engine** from P05.

First formalize physical PS/PL DDR ownership, K26 address range,
P02 512KiB stride and a versioned complete-frame A53 ingress
protocol; P06-B1.3's `P06B13I1/P06B13R1` is currently a HOST
protocol, whereas the original P05 physical firmware accepts only
one external axon/core and cannot stream the B2 application as-is.
Independently native-test the A53 parser/serializer and fail-closed
CRC/ownership/capacity paths, then implement deterministic 27-core
paging, dirty writeback, NEXT event-bank routed fanout, barrier
scheduling and per-image reset with no stale packets.

Verify a bounded **TRAIN-derived validation** first-mismatch
corpus on the actual KV260, initially small physical cases,
eventually all 27 cores, all P02 initial contexts and full
26-tick trained dense integer state/spike/readout parity versus
the independent source oracle. Only after separate user
acceptance of the physical board implementation, frozen
bitstream/ELF/runtime/run IDs and the previously predeclared
TEST protocol may B2 official MNIST TEST be considered. Do NOT
evaluate B2 TEST during P07-B development.

**Do not claim a 27-core physical demonstration until
independent evidence confirms every core, correct paging
and routing, per-core DDR contents, packet ordering,
per-image reset and board predictions.** B1.5's modeled
341–382 MB page-engine transfer totals are not physical
scaled measurements; P08-B will measure actual traffic,
latency, throughput and energy separately. Distinguish
Track A's 94.56% *official TEST* from Track B's 97.08%
*train-derived validation* and their distinct checkpoints.

---

# P08 — Independent physical baseline and scaling measurements

**Status:** **P08-A LATENCY-ONLY ACCEPTED BY USER (POWER/ENERGY P08-A4 DEFERRED). P08-B SCALED TRACK IS ACTIVE:** P07-B physical acceptance and P08-B4.1/B4.2/B4.4/B4.4.2 results are recorded above; P08-B4.5 reset-integrity optimization is the active next milestone; P08-B4.6 paired Track A/Track B comparison follows. Power/energy remain deferred and official Track B MNIST TEST remains sealed.

## P08-A — Compact physical KV260 latency baseline

**Status (2026-10-18 project timeline): P08-A LATENCY-ONLY COMPLETION EXPLICITLY ACCEPTED BY USER; MERGE OF PR #45 TO `main` AUTHORIZED. A3 SIX ORIGINAL KV260 PHYSICAL SESSIONS NUMERICALLY VERIFIED BY USER (A2.1 MEDIANS 35.7023 / 35.6946 / 35.6696 ms; A2.2 35.7234 / 35.7163 / 35.7220 ms; PAIR MEDIAN DELTAS +16.840 / +25.400 / +29.710 µs; MEAN +23.984 µs / SD 6.551 µs). A5 P07-PARITY-GATED CPU PRELOADED RUN MEDIANS 25.6147 / 25.6001 / 25.5735 ms, RAW784→CLASS MEDIANS 30.3930 / 30.3147 / 30.2579 ms, CPU/PHYSICAL REPORT SOURCE HASH MATCH USER VERIFIED. P08-A4 POWER/ENERGY DEFERRED/UNMEASURED. CPU/FPGA ENDPOINTS NON-EQUIVALENT; NO PURE PL SPEEDUP OR VERIFIED PL HZ. CORRECTED A5 FINAL PYTEST SUMMARY NOT POSTED; MERGE OUTCOME VERIFIED SEPARATELY FROM GITHUB.** P07-A accepted accuracy and physical numerical parity remain frozen; **do not rerun official MNIST TEST** for this experiment.

| Gate | State | Authoritative reference |
| --- | --- | --- |
| P08-A1 measurement boundary audit | User approved latency-first direction; deferred power/energy | [Measurement contract](docs/P08_A1_MEASUREMENT_CONTRACT.md) |
| P08-A2.1 per-image A53 timing source | Original frozen A2.1 ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`; **KV260 FIRST1024 PAIRED PHYSICAL RUN SUCCESS (USER ATTESTED)** | [Image timing method](docs/P08_A2_1_LATENCY_SIDECAR.md) |
| P08-A2.2 per-tick seven-boundary timing source | User reports regressions and Vitis build PASS after false-positive regression fix; **ELF SHA256 attested** `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`; **KV260 EXECUTED as A3.1 16-image pilot AND A3.2.2 first1024 paired session (USER ATTESTED)** | [Per-tick timing method and sources](docs/P08_A2_2_TIMING_METHODS.md) |
| **P08-A3.1 physical 16-image validation pilot** | **PHYSICAL FUNCTIONAL GATE PASS (USER-ATTESTED 2026-10-18)**: first 16 distinct TRAIN-derived validation images, 26×10 output flags per image and selected 26×42 full trace exact to independent oracle; A2.1 image and A2.2 per-tick timing sidecar terminal/CRC/clock/route consistency PASS. **User-supplied numerical pilot: median 35.4432 ms (31.2682–41.2175 ms), CNTFRQ_EL0 99,999,001 Hz; 1,024-frame repeated baseline NOT RUN.** [Exact pilot numbers](docs/P08_A3_1_PHYSICAL_LATENCY_RESULTS.md) and [physical acceptance](docs/P08_A3_1_PHYSICAL_ACCEPTANCE.md) | [Pilot protocol](docs/P08_A3_1_PHYSICAL_PILOT_PROTOCOL.md) |
| **P08-A3.2 repeated latency characterization** | **USER-ATTESTED PHYSICAL THREE-PAIR COMPLETE:** paired median A2.2−A2.1 full A53 image service +16.840, +25.400, +29.710 µs (mean +23.984 µs, n=3 run pairs); within-image median delta range 24.730 µs, p95 range 73.541 µs. P07 original packed neural oracle + tick/image timing integrity PASS on each accepted pair; original 1,024 TRAIN-derived validation sample identities unchanged; 1,023 ordinary frames analyzed each run. **Aggregate source JSON/report hash not independently file-sealed here; PL achieved Hz not independently calibrated; no pure PL speed or CI claim.** | [Complete six-run results](docs/P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md), [repeated protocol](docs/P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md) |
| P08-A4 power and energy | **DEFERRED**; no sensor selection or power measurements authorized | Future explicit user decision |
| **P08-A5 CPU software reference and final closeout** | **HOST BENCHMARK/DUAL NUMERICAL PROOF/FINAL REVIEW REPORT USER-ATTESTED PASS; LATENCY-ONLY FINAL APPROVAL PENDING.** Original frozen packed 26-tick preloaded CPU scalar per-run medians **25.6147 / 25.6001 / 25.5735 ms**; original raw784 encoder→class medians **30.3930 / 30.3147 / 30.2579 ms**; three sequential PC passes across the same 1024 canonical TRAIN validation images; original full 1024 P07 physical-neural/original-oracle and full-26-tick parity PASS. Stage descriptor/pixel/manifest SHA256 and accepted A2.1 physical run bound to six-session KV260 results PASS. Generated report, source hashes, p95/stdev and CPU environment posted and reviewed. **Not an isolated PL acceleration claim, not optimized native C, CPU/board scopes differ; achieved PL frequency uncalibrated.** Corrected A5 final native pytest summary not pasted (not falsely claimed PASS); user **EXPLICITLY ACCEPTED LATENCY-ONLY P08-A AND AUTHORIZED PR #45 MERGE**. Actual GitHub merge outcome tracked separately. | [Measured A5 CPU/FPGA results and SHA256s](docs/P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md), [P08-A FINAL ACCEPTANCE CANDIDATE — signature/merge stop gate](docs/P08_A_LATENCY_ONLY_FINAL_ACCEPTANCE_CANDIDATE.md), [A5 protocol](docs/P08_A5_CPU_REFERENCE_PROTOCOL.md) |

For the active Track A **physical latency** study, collect actual A53 per-frame (26-tick) service intervals, event encoding/bank-write/dispatch/trace/route/barrier intervals, hardware PL dispatch and page counters with **separate clock domains**, and CPU comparison endpoints. Host JTAG polls, HLS clock estimates and simulator cycles are not board latency data. Report benchmark overhead and selected full-trace perturbation explicitly.

**Entry gate to scaled Track B:** accept original P07-A frozen accuracy plus a genuine **physical, independently numerically verified P08-A latency baseline** before implementing B hardware. Power/energy are *not* an active prerequisite during this user-approved deferral; do not silently resume them or claim measured Loihi efficiency.

## P08-B — Scaled physical resource/traffic/energy study

Repeat the same measurement method for the frozen scaled model. In addition,
record logical core count, three resident slots, actual HLS dispatches,
per-core paging hits/misses/evictions, bytes moved, routed packet
fanout/barrier time, event-bank occupancy and resource mapping across all
cores; compare these against P08-A.

The active reset-integrity sequence is P08-B4.5. The repeated paired
Track A/Track B comparison is P08-B4.6 and follows the two reset variants.

Report two different model sizes and checkpoints: improvements in
classification accuracy and costs from model scaling are not pure FPGA
architecture speedups. Avoid claiming direct Intel Loihi power/latency
comparisons where workload or scope differs. An extra physical engine is a
deferred, optional optimization only after one-engine baseline and scaled
bottlenecks are measured.
---

# P09 — Thesis comparison and closure

**Status:** PLANNED.

First close the complete **Track A evidence
chain** (published-method scope, independently
trained/frozen exact checkpoint, source oracle,
P03 HLS image, board-local physical predictions,
official-test accuracy, power/energy, and
measurement provenance). **If Track B is not
successful**, this result must remain a fully
valid standalone thesis contribution.

If Track B passes P06-B/P07-B/P08-B,
add its **separate** reproducible
checkpoint, accuracy and physical data,
plus a measured compact-vs-scaled comparison:
model capacity, classification accuracy,
contexts, paging, routed event traffic,
true complete-sample latency, throughput
and total/dynamic energy.

**No hidden claim inflation:** project-trained
snnTorch-method checkpoints are not
released author pretrained weights;
static-analog input is not our
deterministic event encoder; hardware
P03 integer reset is not snnTorch
subtract-reset; a faster/smaller
model is not a pure architecture
comparison to a different model;
Loihi-1 transistor/native SRAM/NoC
or published chip-level energy
equivalence is not established.

Close only with immutable commit,
checkpoint/data/bitstream/ELF
fingerprints, independent regressions,
physical first-mismatch and board
performance evidence, and explicit
unknowns/non-comparable claims.

---

## Deferred/future directions

- multi-engine physical execution pending single-engine latency characterization;

These are intentionally not prerequisites for the initial v3 roadmap unless later evidence makes them necessary:

- full PL-owned scheduling instead of PS-owned orchestration;
- on-FPGA/on-chip learning;
- Loihi 2 architectural targeting;
- real-time sensor/event input;
- multi-board scaling;
- physically asynchronous FPGA circuitry.
