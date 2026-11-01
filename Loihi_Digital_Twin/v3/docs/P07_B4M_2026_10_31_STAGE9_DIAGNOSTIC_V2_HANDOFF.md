# P07-B.4m physical inference handoff — bounded closeout (2026-10-31)

**Status: engineering implementation complete, physical full-inference
ACCEPTANCE BLOCKED (NOT PASSED).** Keep PR #49 draft and unmerged pending
an explicit decision to merge or separately freeze the unresolved work.
Do not start a new P07-B.4m micro-milestone.

## Immutable original trained deployment (never modify)

- Accepted B2.4 27-core 784→1000→10, 26 tick model:
  compilation SHA `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`.
- Original frozen DDR bundle physical stage/readback:
  SHA `3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`.
- Original descriptor (16KiB) SHA:
  `2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb`.
- Original TRAIN input route image (896KiB) SHA:
  `380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8`.
- Original output route image (80KiB) SHA:
  `2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103`.
- Frozen original TRAIN ordinal-0 input (123,216B) SHA:
  `2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126`.
- Official MNIST TEST remains SEALED. All numerical parity remains UNVERIFIED.

## Accepted real hardware results

1. KV260 original 27×512KiB DDR contexts, descriptor, routing tables and
   original TRAIN frame were independently read back byte-for-byte **PASS**.
2. Genuine standalone B4m A53 ELF SHA
   `ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70`
   was downloaded and ran to terminal mailbox DONE, but **firmware FAIL**;
   702 dispatches / 26 barriers **NOT achieved**.
3. Original 256B physical failure mailbox SHA
   `4ff427fca04f75b89712c7ea81d7065710ce46de586f6eb07ec8bd1ea1105baf`:
   **stage=9, P03_HW_PROTOCOL=-5, dispatch completed register=1**.
   PS width, P03 MMIO identity, B2.4 metadata, frozen route mount,
   pager initialization and scheduler initialization all succeeded.
   No independent full-inference receipt was accepted.
4. PC-only reconstruction of original first TRAIN frame / frozen core-0
   P03 image: **51 tick-0 input events, 39 compartments, 30,576
   synapse entries, 784 registered axons, zero HLS input-semantic
   violations**. This makes original data formatting less suspect,
   but **DOES NOT prove the real PL subfault**.

## Bounded follow-up: isolate the real first-dispatch protocol subfault

The existing V1 A53 firmware only preserves high-level stage 9.
`software/p07/p07_b4m_full_board_diag.c` is a NEW isolated
`P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2` candidate, built separately
using `scripts/build_p07_b4m_diag.sh` plus
`software/p07/build_p07_b4m_diag.py`. It does NOT change the V1 ELF,
original model, PL bitstream, input routes or numerical algorithm.

When and ONLY when it ends in firmware FAIL, it captures a uniquely
tagged B4D2 payload in mailbox words 47..62:
- [47] B4D2 marker;
- [48] P03 adapter last polled raw status, [49] B3c2 scheduler first fault,
  [50] B3a pager first failure, [51] physical trace first failure;
- [52] dispatch status, [53] HLS core status, [54] active core/slot/bank,
  [55] physical packet count, [56] debug status, [57] global status;
- [58] paging status, [59] pending bytes, [60] dispatch config,
  [61] debug config, [62] debug address.

The original host-only mailbox decoder recognizes only the B4D2
marker before interpreting those values; a V1 failed mailbox remains
supported and its missing telemetry is explicitly NOT fabricated.
The strict original `p07_b4m_verify_full_receipt.py` remains unchanged.

**Important:** The V2 firmware is currently **BUILD-ONLY**. Neither the
older V1 hash-pinned XSDB runner nor the original V1 offline admission
gate will authorize it, and they MUST NOT be bypassed by swapping ELFs.
Any V2 physical experiment requires (a) genuine operator-local Vitis
ELF/map rebuild with new SHA, (b) independent ELF/memory/boot-firmware
review, (c) a separately source/SHA-pinned V2 admission+XSDB launcher,
and (d) new explicit destructive-run consent. DO NOT re-run the KV260
with either old commands or a manually substituted ELF.

PC only, user-buildable diagnostic candidate:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4M_DIAG_BUILD_DIR="$HOME/p07_b4m_diag_v2_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4m_diag.sh
```

Expected on a genuine operator-local build:
`P07_B4M_DIAG_V2_A53_ELF_AND_MAP_BUILT=1`,
`P07_B4M_REAL_BOARD_RUN_AUTHORIZED=0`,
`P07_B4M_EXPANDED_LOW_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0`.
Record the new ELF and GNU map SHA and actual `readelf_layout.txt`;
none are known until the user builds them.

## Handoff to next work

**Stop condition for B4m:** physical data placement passed; one full
trained inference attempt failed at P03 protocol after the first PL
dispatch; original model is untouched; preserved original signed
failure evidence and PC-only source audit. Never mark B4m fully accepted,
never merge PR #49 solely because the diagnostic candidate compiles,
and never unseal official TEST.

**Next-milestone work that can proceed independently:** documenting the
hardware/software control interface, repeatable tooling and measurement
methodology; host-native verification, benchmarking infrastructure and
non-destructive analysis; literature/digital-twin architecture write-up.
Tasks requiring 26-tick physical outputs, real inference accuracy,
per-neuron numerical parity or energy/latency benchmarks of successfully
completed inference remain gated.

A single narrowly scoped future board run with new telemetry may be
justified if it decisively identifies the P03 dispatch/debug subfault.
If time budget is exhausted, retain the unresolved failure as a precisely
measured research limitation and proceed to independent next milestones.
