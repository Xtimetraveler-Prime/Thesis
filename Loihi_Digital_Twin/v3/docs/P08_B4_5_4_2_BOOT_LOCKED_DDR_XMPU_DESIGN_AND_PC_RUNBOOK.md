# P08-B4.5.4.2 — Protected Backup: Trusted-Boot XMPU Design (HOST ONLY)

**Status:** sourced architectural design, versioned symbolic six-DDR-XMPU
candidate, native negative tests, and CI. NOT an FSBL build, register image,
XMPU configuration script, A53 guard provisioning, boot media modification
or physical board approval. `P08_B4542_NEW_KV260_HARDWARE_PROOF=0`.

## Design decision and important privilege correction

**Chosen architecture:** the original 13.5 MiB immutable 27-core P02
backup is loaded/authenticated by a *controlled trusted boot path*, then
a secure boot actor configures DDR XMPU regions to prevent all subsequent
writes, verifies and locks the configuration, and only then hands
off to the nonsecure A53 SNN runtime. This directly serves B4.5.1's
*authenticate once* goal, unlike a software A53 MMU read-only mapping,
which would not control RPU/PL DMA or other DDR writes.

The backup is exactly
`[0x43000000,0x43D80000)` (27 x 524288 = 14155776 B).
The DDR XMPU fixed 1 MiB granularity gives
`[0x43000000,0x43E00000)` (14 MiB), **overprotecting 512 KiB**
`[0x43D80000,0x43E00000)`. No physical owner proof exists for this
extra range or for the 13.5 MiB backup under the active KV260 boot.

**Crucial:** a catch-all, *read-allowed/write-denied* region for **all
masters** would prevent writes, but could also permit previously
unauthorized DDR reads, silently weakening existing isolation. Our
candidate therefore uses a higher-priority exception *only* for future
verified reader IDs:

| Per-port symbolic region | Address | ID/mask | Reads | Writes | Status |
| --- | --- | --- | --- | --- | --- |
| Priority 14 — catch-all denial | `[0x43000000,0x43E00000)` | `ID=0, MASK=0` matching all 10-bit MIDs | DENY | DENY | PROPOSED, NOT PROGRAMMED |
| Priority 15 — exact reader allow-list | Same | **UNKNOWN**; needs actual per-port AXI ID/mask from current boot/PL/APU | ALLOW only future vetted IDs | DENY | DISABLED/UNRESOLVED |

This design deliberately **does not yet allow A53 or PL to read the
backup**. It is a negative-only symbolic validation that every write to
the protected 14 MiB would be denied *if the proposed model were actually
installed*. It cannot be copied directly into FSBL yet. Region slots 14
and 15 may be occupied by existing boot XMPU configuration; we need the
exact present region/priority/default-security profile from the
dedicated test boot image. We cannot overwrite those slots or grant
additional readers until their full security consequences are audited.

The candidate includes every DDR XMPU port 0–5 and statically evaluates
**all 1024 possible 10-bit AXI Master IDs**, both secure and nonsecure
traffic and six protected address cases. Master-ID match is based on
AMD's documented equation `(AXI_MasterID & MASK) == (ID & MASK)`,
and higher matching region numbers take precedence. The simulation
cannot establish the actual path a transaction takes through DDR
XMPU ports, read back register values or prove future hardware access
policies.

## Source research and attribution (not copied vendor code)

This protection strategy adapts **AMD-published architecture and
documentation**, not a prior research group's implementation.
The source-level candidate and tests were authored for this thesis;
no AMD programming source code or XMPU register writes were copied
into this repository.

1. **AMD UG1085, XMPU Instances.** Six DDR XMPUs; DDR granularity 1 MiB.
   https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances
2. **AMD UG1085, Memory Protection Unit.** Independent read/write
   permission checks across DDR ports and AXI master IDs.
   https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/AMD-Memory-Protection-Unit
3. **AMD UG1085, XMPU Regions / Master ID Validation.** There are
   16 regions per XMPU; higher-numbered matching regions have priority;
   10-bit ID/mask equation. The symbolic priority-14 deny and
   priority-15 reader-only exception are **our proposed arrangement**,
   not AMD's prescribed allocation for this KV260.
   https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Regions
   https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Master-ID-Validation
4. **AMD UG1085, Configuration.** Only secure masters can configure
   or read XMPU registers, normally during trusted boot, then locked.
   The lock and POR-vs-system-reset behavior must be confirmed on
   the actual K26/boot configuration.
   https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Configuration
   https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Protection-of-Slaves
5. **AMD UG1137, Partition Loading and Hooks in FSBL.** The FSBL can
   load partitions into DDR and provides
   `XFsbl_HookBeforeHandoff(u32 EarlyHandoff)` for customization.
   The accepted Vitis 2025.2 FSBL's exact sequencing, early handoff,
   pre-existing XMPU lock state, source-partition lifetime and
   authentication behavior require inspection before choosing this
   hook. This document does **not** assert the hook is already suitable.
   https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Partition-Loading
   https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Hooks-in-FSBL
6. **AMD UG1283, Bootgen `load` partition attribute.** A distinct
   data partition can conceptually be placed at an intended DDR load
   address. Whether our precise 13.5 MiB P02 concatenation can be
   safely staged/authenticated with current boot tooling is UNTESTED.
   https://docs.amd.com/r/en-US/ug1283-bootgen-user-guide/load
7. **AMD/Xilinx public FSBL hook skeleton** is a location reference,
   not code integrated into our frozen runtime:
   https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hooks.c

### Candidate trusted boot ordering — still only a design

Proposed **separate removable/recoverable development boot configuration**;
do not rewrite the existing QSPI, BootROM, TF-A, accepted P03 bitstream
or production Linux images for this experiment.

The expected trusted stage would first authenticate the boot source,
load exactly the 27 original P02 records, independently check their
original SHA-256 values, quiesce relevant writers, establish all six
per-port XMPU regions with explicit reader whitelist and readback, then
lock and verify them, **before any A53 inference handoff**. Staging,
partition-load DMA or debug writes after lock must be forbidden. A
trusted boot attestation, exact boot provenance and a mechanism for
the nonsecure runtime's cheap `backup_lock_valid` callback need
separate design/implementation. A software flag alone is NOT proof
of continuing XMPU protection.

Current original ELFs start at physical `0x0` and occupy
`[0,0x109BC0)`. The boot owner for that low-DDR address interval,
heap/stack and MMU/cache attributes remains a SEPARATE blocker.
Even a successful XMPU RO implementation on `0x43000000` would not
alone authorize those A53 binaries for JTAG download.

**No physical side effects:** this step creates neither a valid
`BOOT.BIN` nor a `xfsbl_hooks.c` replacement. It does not
reconfigure the board, run `xsdb`, enable the two backup guard
callbacks, claim reader MIDs, perform a denial-write experiment,
or access official MNIST TEST.

## Complete operator setup and source discovery

Use the **new descendant branch** `agent/v3-p08-b4542-xmpu-boot-policy`.
Do not merge draft parent PRs, and do not edit the accepted external
report files.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b4542-xmpu-boot-policy
git pull --ff-only origin agent/v3-p08-b4542-xmpu-boot-policy
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Accepted PC-only physical-owner GAPS evidence (not ownership proof):
export P08_B454_GAP_REPORT="$HOME/Thesis_Evidence/p08_b454_ddr_owner_gap_20261105T051850Z.json"

# Accepted prior both-A53 genuine offline admission report (read-only reference):
export P08_B454_ACCEPTED_PAIR="$HOME/Thesis_Evidence/p08_b45_pair_independent_20261105T045733Z.json"

# Candidate policy lives INSIDE the freshly fetched repository:
export P08_B4542_POLICY_JSON="$PWD/config/p08_b4542_xmpu_boot_candidate.json"

# NEW external no-overwrite host-only risk-policy artifact:
export P08_B4542_POLICY_REPORT="$HOME/Thesis_Evidence/p08_b4542_xmpu_policy_pc_$(date -u +%Y%m%dT%H%M%SZ).json"
```

If any old evidence path has moved, locate it and update the
corresponding export to the exact ORIGINAL file. **Do not** use
a similarly named file just because it exists.

```bash
find "$HOME/Thesis_Evidence" -type f -name 'p08_b454_ddr_owner_gap_*.json' -print
find "$HOME/Thesis_Evidence" -type f -name 'p08_b45_pair_independent_*.json' -print
```

Then verify the *accepted* hashes explicitly:

```bash
test -s "$P08_B454_GAP_REPORT" &&
test -s "$P08_B454_ACCEPTED_PAIR" &&
test -s "$P08_B4542_POLICY_JSON" &&
test ! -e "$P08_B4542_POLICY_REPORT" &&
echo "P08_B4542_PC_ONLY_INPUTS_PRESENT=1"

sha256sum "$P08_B454_GAP_REPORT" "$P08_B454_ACCEPTED_PAIR"
# Gap must equal:
# 7a1d87cf3278245a4a5ed612773ac228097e506f464861c3e1b69856f6ba56f2
# Parent pair must equal:
# 03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1
```

### Native tests first (no Vitis, board or JTAG)

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b4542_xmpu_boot_policy.py
```

### Evaluate hypothetical six-port policy, write new PC-only JSON

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b4542_xmpu_boot_policy.py \
  --gap-report "$P08_B454_GAP_REPORT" \
  --candidate "$P08_B4542_POLICY_JSON" \
  --out "$P08_B4542_POLICY_REPORT"

sha256sum "$P08_B4542_POLICY_REPORT"
python3 -m json.tool "$P08_B4542_POLICY_REPORT"
```

Expected **mathematical/symbolic-only** markers:

```text
P08_B4542_SIX_PORT_SYMBOLIC_WRITE_DENIAL_PC_ONLY_PASS=1
P08_B4542_REAL_READER_ALLOWLIST_READY=0
P08_B4542_FSBL_BOOT_PROTECTION_PROVEN=0
P08_B4542_XMPU_REGISTERS_PROGRAMMED=0
P08_B4542_NEW_A53_FIRMWARE_PROVISIONED=0
P08_B4542_BOARD_JTAG_DDR_ACTION_AUTHORIZED=0
```

The report's conclusion is
`SYMBOLIC_WRITE_DENY_CONTRACT_PASS_READERS_AND_REAL_BOOT_NOT_READY_NO_GO`.
This is correct even when the source/geometry/mask/precedence models
pass every host regression. Never treat this as physical write exclusion.

## Optional read-only local boot-source discovery for the NEXT submilestone

The current policy simulation deliberately cannot fill in the actual
secure boot image's XMPU region slots or master IDs. To plan the
next submilestone without guessing, operators can locate existing
local **sources only**. Do not build, modify or boot anything based
on these paths. The variable below is an EXISTING installation path,
not a newly created output:

```bash
export P08_B4542_VITIS_INSTALL="$HOME/Vivado/2025.2"

find "$P08_B4542_VITIS_INSTALL" "$PWD/vivado/build" \
  -type f \( -name 'xfsbl_hooks.c' -o -name 'xfsbl_handoff.c' \
          -o -name 'psu_init.c' -o -name '*.bif' \) \
  -print 2>/dev/null | head -80
```

Results identify potential input files to review for *actual*
Vivado 2025.2 boot PS/XMPU sequencing. Finding a file is not proof it
belongs to the active board boot image; any later analysis must
pin its SHA-256 and reconcile boot media, FSBL ELF, secure actors and
partition provenance.

## Engineering decisions needed before a *future* hardware-enabled design

- Inventory the actual Vivado/Vitis 2025.2 PS configuration and
  FSBL-generated XMPU region assignments, including whether per-port
  region slots 14 and 15 can be safely dedicated to backup and how
  existing default permissions/other masters would be affected.
- Determine the exact AXI Master ID(s) and security attributes that
  the A53 and P03 PL accesses present at **each** DDR XMPU port.
  A catch-all with `read_allowed=true` is specifically prohibited;
  it risks granting unintended reads.
- Inspect the actual compiled FSBL
  `XFsbl_HookBeforeHandoff`/early-handoff ordering and the full
  trusted boot partition path before writing any hook code. Verify no
  earlier FSBL/boot security setup irreversibly locks relevant XMPUs.
- Establish continuous exclusive DDR ownership across FSBL/TF-A,
  U-Boot, Linux, APU/RPU/PMU and PL-DMA, including the extra 512 KiB
  and the low-DDR ELF overlap risk.
- Select and verify how the nonsecure A53 obtains **genuine trusted
  continuing protection evidence** without untrusted XMPU register
  writes. This may require a reviewed EL3 monitor interface; none
  is implemented yet.
- Only afterward create a distinct signed/provisioned guard variant,
  a NEW boot image on recovery-capable development media, full
  read-only preflight, and a newly admitted ELF and evidence root.
  Before physical programming or first 16-frame pilot, request new
  explicit operator consent and document recovery. Original two
  B4.5.3 ELFs remain preserved and fail closed.

## Relationship to thesis contribution

AMD's XMPU/FSBL mechanism is **not** an original neuromorphic research
invention. The project's contribution is the frozen Loihi-inspired
27-context reset architecture and the independently verifiable
performance/integrity comparison, including transparent modeling
of the trustworthy boot boundary and security-performance tradeoff.
Cite UG1085/UG1137/UG1283 in thesis methods when claiming the
protection architecture is derived from AMD's existing technology.
