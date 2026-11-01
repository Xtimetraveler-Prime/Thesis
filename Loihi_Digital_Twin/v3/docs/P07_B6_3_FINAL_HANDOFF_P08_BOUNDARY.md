# P07-B.6.3 — Final original 27-core physical FPGA handoff and P08-B boundary

**STATUS (2026-11-01): B6.3 GENUINE FINAL PHYSICAL REPRODUCIBILITY
HANDOFF USER ACCEPTED. `P07_B6_final_hardware_freeze_accepted=true`,
`P07_B_complete=true`, B6.2 portable archive created and fully
independently reverified, main-only `LitReview.md` original Git blob
verified. P08-B has NOT begun. MNIST official TEST remains SEALED.**
The final user's accepted report includes `github_main_merged=false`
at its historical time of execution; subsequent dependency-order
PR integration must be verified separately.

**POST-ACCEPTANCE GITHUB INTEGRATION (2026-11-01):** Following genuine
B6.3 `P07_B_complete=true` acceptance, normal Git merges
PR #49 `48b5db1f6430e594b2fce03aefa9136935249546`,
PR #50 `1328e2cd04ae43f7dde1aa3e898f81be2c1ac6ea`,
and PR #51 `a59fa21eb5ffff8586c33c65b291a6ea2bfca6e4`
were completed into `main`. Independent `main:LitReview.md`
retains its exact original blob SHA
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`.
[Post-merge source provenance](P07_B_2026_11_01_POST_MERGE_INTEGRATION_ACCEPTED.json).
The accepted historical operator report's
`github_main_merged=false` is correct *at the time the operator
ran it*, not the later GitHub integration status. Original
MNIST TEST remains SEALED; P08-B not started.

## Final real operator-accepted original 27-core evidence

On 2026-11-01 the operator ran the original signed B6.2 full
reproducibility copy, a **separate independent auditor of all copied
files** (SHA256 and size), B6.3 PC-only `--mode review` and B6.3
`--mode accept`. All four commands succeeded. Final report:

`/home/dna/Thesis_Evidence/p07_b6_3_final_operator_accepted_20261101T233410Z.json`

Exact final markers:

```text
P07_B6_3_ORIGINAL_27CORE_SIGNED_PHYSICAL_ARCHIVE_FINAL_RECHECK_PASS=1
P07_B6_3_MAIN_ONLY_LITREVIEW_ORIGINAL_GIT_BLOB_PASS=1
P07_B6_3_ORIGINAL_MNIST_TEST_SEALED=1
P07_B6_3_NEW_BOARD_CONTACT=0
P07_B6_3_FINAL_OPERATOR_ACCEPTANCE=1
P07_B6_3_GITHUB_MAIN_MERGED=0
```

The copied archive
`/home/dna/Thesis_Evidence/p07_b6_full_reproducibility_20261101T233311Z`
had immutable `handoff_manifest.json` SHA256
`73491c0e4f1708ba726cb15e2fd64312d55b002c7d507f6ef0a0d868424fe431`;
independent audit report
`/home/dna/Thesis_Evidence/p07_b6_bundle_audit_20261101T233347Z.json`
had SHA256
`10399bc72bef7ce14db04e85685f2099ae2ab6f5461f6d0712fd7b4918111907`.
Original frozen 33 assets, all five real source-backed physical
sessions, original V3 and B5 ELF/map, original P03 XSA and B5 RAW
840320B full neuron parity were independently verified with
unchanged accepted hashes. B6.3 final recorded
`operator_final_P07_B_acceptance=true`,
`P07_B6_final_hardware_freeze_accepted=true`,
`P07_B_complete=true`. Full source-controlled exact results:
[Bounded final operator acceptance ledger](P07_B6_3_2026_11_01_FORMAL_OPERATOR_ACCEPTED_P07_B_CLOSEOUT.json).

**No extra neural behavior is being claimed**: selected original
TRAIN 0/1/2/0 only, original TRAIN0 entire 26×1010-neuron
physical raw-byte equality, no full packet-word trace equality,
no independently proven boot/Linux/DDR exclusive ownership, power
cycles operator-attested but not instrumentation-proven, no
asynchronous real-Loihi claim or official TEST accuracy.
Future P08 requires separately accepted measurement/test protocol.

The remainder of this page is the historically drafted B6.3 procedure.
Its earlier directions to run review/accept have already been carried
out and remain for reproducibility.

## Frozen hardware/software implementation

The selected original signed B2.4 checkpoint is a 784→1000→10
integer Loihi-inspired spiking network with **27 logical cores** in
DDR-backed 512KiB records, running through **3** physical HLS
execution slots on the original P03 KV260 programmable logic, with
26 global timesteps, **702** real HLS dispatches, **26** global
barriers and physical A53 PS paging/routing control. This is
**board-local PS/PL execution**, not a claim of fully asynchronous
real Loihi hardware.

A53 firmware identities:
- Original accepted 26-tick V3 physical launcher ELF SHA256
  `66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`,
  GNU map SHA256 `148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede`.
- Separate B5 original TRAIN0 debug-bank7 raw capture ELF SHA256
  `0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf`,
  GNU map SHA256 `1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8`.
- Accepted fixed P03 PS/PL FPGA shell XSA SHA256
  `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
- Original TRAIN-only frozen source and 33 frozen assets including 27
  DDR context records, plus input route table (20,384 registered
  routes), output route table (1,000), and frozen TRAIN ingress
  ordinals 0,1,2 remain immutable.
- P03/B5 physical backing aperture `[0x40000000,0x44000000)`.
  Original 27 context records occupy `[0x40000000,0x40D80000)`.
  B5 raw buffer `[0x42000000,0x420CD280)` and new B5
  256B terminal mailbox `[0x43FF0100,0x43FF0200)` are not
  proven exclusively owned by this application relative to Linux
  or boot firmware. B5 firmware low DDR LOAD `[0,0x00107BC0)`
  is also not independently proven exclusive. No new board run
  is needed to close B6.3's *reproducibility* objective.

## Evidence: exactly five genuine physical sessions

Original TRAIN 0/1/2/0 V3 sessions each passed signed original
26-tick software scalar fingerprints and all accepted physical
counts. The original TRAIN0 repeat matched the first physical
256B V3 mailbox byte-for-byte. The fifth **original TRAIN0** B5
raw physical session included **26×1010×32 = 840,320 bytes**
of original signed physical neuron state, physically read back
from PSU DDR and independently compared to the frozen original
scalar trace: both SHA256
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`,
26,260 neuron records exactly equal; 702 dispatches, 26 barriers,
all seven reference numerical checks PASS.

The operator's final B5.4 acceptance artifact is
`/home/dna/Thesis_Evidence/p07_b5_4_accepted_20261101T224134Z.json`,
SHA256 `d72abc426a0d7a54d5a70994f75de9fca31862441d6507feb0b57c3e3fbbf7b9`.
The five-session operator attestation SHA256 is
`4dd6cf0d02c477a2992b55b8bc2454ee9800c94ccce78f6cee25a32f2dc7fa31`.
Actual cold power cycles were **operator-attested**, not
independently hardware-instrumented.

The signed B6.1 seal is the genuine PC-only report
`/home/dna/Thesis_Evidence/p07_b6_original_freeze_seal_20261101T230852Z.json`.
Its `B5_formal_operator_acceptance_verified=true` and
`original_B24_manifest_entries_individually_SHA256_revalidated=33`
independently certify acceptance evidence and source hashes.
Its `B6_final_hardware_freeze_accepted=false` is correct.

## Required B6.2 portable source-backed archive

The archive must be generated by
`scripts/p07_b6_reproducibility_bundle.py`, using genuine
source originals and **the historical original V3 ELF/map paths**,
then independently audited by
`scripts/p07_b6_verify_reproducibility.py`.
This re-opens every copied file and checks SHA256 + exact size,
all 33 B2.4 frozen assets via the original native gate,
four complete original V3 physical-session directories and the
fifth raw capture directory, the raw trace SHA and the user-accepted
B5.4 attestation.

Use these actual discovered original V3 paths, not the similarly
named newer B5 firmware:
```bash
export P07_B4M_V3_ELF="/home/dna/p07_b4m_diag_v3_build_20261101T034702Z/vitis_workspace/p07_b4m_diag_v3_26tick.elf"
export P07_B4M_V3_MAP="/home/dna/p07_b4m_diag_v3_build_20261101T034702Z/vitis_workspace/p07_b4m_diag_v3_26tick.map"
sha256sum "$P07_B4M_V3_ELF" "$P07_B4M_V3_MAP"
```
The other actual original build V3 ELF under
`vitis_workspace/p07_b4m_diag_v3_26tick/build/` may be
identical; only use a SHA-matched accepted original ELF.
Never substitute or rebuild and change historical accepted bytes.

## New B6.3 final gate: review, then explicit operator acceptance

`scripts/p07_b6_final_handoff.py` **re-reads** actual source-backed
B6.2 archive and B6.2 original independent audit and requires
their exact equality to a fresh independent verification. It binds the
archive to the unchanged B6.1 original source seal, the exact B5.4
operator-accepted report and five physical-session attestation,
rechecks the exact 840,320B physical raw trace SHA, and independently
rechecks `origin/main:LitReview.md` via its Git blob
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`.

First verify the B6.2 archive and save the accepted actual output
path in `P07_B6_PACKAGE`, and the original independent B6.2 audit
path in `P07_B6_BUNDLE_AUDIT`.

**Review, PC-only; no acceptance:**
```bash
git -C "$HOME/Git/Thesis" fetch origin main
export P07_B6_3_REVIEW="$HOME/Thesis_Evidence/p07_b6_3_independent_final_review_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B6_3_REVIEW"
PYTHONPATH="$PWD/src" python scripts/p07_b6_final_handoff.py \
  --mode review \
  --seal "$P07_B6_SEAL" \
  --package "$P07_B6_PACKAGE" \
  --bundle-audit "$P07_B6_BUNDLE_AUDIT" \
  --b5-accept "$P07_B5_4_ACCEPT" \
  --out "$P07_B6_3_REVIEW"
cat "$P07_B6_3_REVIEW"
```
Expected `P07_B6_3_ORIGINAL_27CORE_SIGNED_PHYSICAL_ARCHIVE_FINAL_RECHECK_PASS=1`
and `P07_B6_3_FINAL_OPERATOR_ACCEPTANCE=0`.

**Separate explicit final bounded P07-B operator acceptance, only
after genuine B6.2 and B6.3 review PASS and personally checking
all source/FPGA/evidence limitations:**
```bash
export P07_B6_3_ACCEPT="$HOME/Thesis_Evidence/p07_b6_3_final_operator_accepted_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B6_3_ACCEPT"
PYTHONPATH="$PWD/src" python scripts/p07_b6_final_handoff.py \
  --mode accept \
  --seal "$P07_B6_SEAL" \
  --package "$P07_B6_PACKAGE" \
  --bundle-audit "$P07_B6_BUNDLE_AUDIT" \
  --b5-accept "$P07_B5_4_ACCEPT" \
  --confirm-final-acceptance \
    ACCEPT_P07_B_FINAL_27CORE_FREEZE_AND_HANDOFF_KEEP_TEST_SEALED_AND_MAIN_UNMERGED \
  --out "$P07_B6_3_ACCEPT"
cat "$P07_B6_3_ACCEPT"
```
Required final result:
`P07_B6_3_FINAL_OPERATOR_ACCEPTANCE=1`,
`P07_B6_final_hardware_freeze_accepted=true`,
`P07_B_complete=true`,
`official_MNIST_TEST=SEALED_NOT_ACCESSED`,
`github_main_merged=false`.
Only this genuine final accepted result can **formally close P07-B**.
It does not automatically merge PRs or start P08-B.

## P08-B benchmark handoff — scope, no automatic testing

P08-B can benchmark board-local PS/PL inference **only after** final
P07-B acceptance and separately reviewed benchmark procedures.
Benchmark records should distinguish FPGA accelerator timing,
DDR pager throughput, external PS control/runtime overhead and
end-to-end PC/board latency. Capture clocks, voltages, constraints,
FPD128 timing, input sources, image ordinals, page movement,
latencies and counter integrity. Do not use host-only simulation
numbers as if they were measured on KV260.

The frozen original model, accepted original P03 bitstream/XSA,
old V3 and B5 firmware and all original source evidence are
immutable baseline inputs. New benchmarks must use separately
versioned measurement additions and must not silently alter 26 ticks,
702 dispatches, 27 logical cores, 3 physical slots or signed TRAIN
route/ingress data. No official MNIST TEST access may be inferred
from a development TRAIN parity result: the predeclared official
TEST protocol remains separately sealed until explicitly authorized.

**PR dependency protection:** PR #49 (original P07-B) →
PR #50 (B5 validation) → PR #51 (B6 final freeze). They remain draft
and unmerged until the operator provides final P07-B accepted
evidence and explicitly authorizes merging. The original independent
`main:LitReview.md` must retain its exact Git blob SHA across
normal dependency-order PR integration, without force pushes.
