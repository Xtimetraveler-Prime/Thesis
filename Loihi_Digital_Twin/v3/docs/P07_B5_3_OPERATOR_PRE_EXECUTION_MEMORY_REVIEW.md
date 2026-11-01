# P07-B.5.3 — Pre-execution physical DDR owner and JTAG risk review

**STATE (2026-11-01): NEW B5 ELF/MAP PC ADMISSION PASS; ORIGINAL TRAIN0
B5 RAW PC PREFLIGHT OPERATOR PASS; REAL B5 PHYSICAL RUN NOT YET AUTHORIZED
OR ATTEMPTED.** Keep draft PRs #49/#50 unmerged and frozen original
V3 ELF/P03 bitstream/B2.4 network/MNIST TEST untouched.

Operator's actual successful PC-only preflight printed:

```text
P07_B4M_DIAG_V3_ALL_27_ORIGINAL_P02_METADATA_COUNTS_HOST_VERIFIED=1
P07_B5_NEW_RAW_GENUINE_A53_ELF_MAP_AND_ORIGINAL_TRAIN_HOST_PASS=1
P07_B5_NEW_RAW_840320B_DDR_OWNER_INDEPENDENTLY_PROVEN=0
P07_B5_NEW_LOW_DDR_0_TO_0x107BC0_EXCLUSIVITY_PROVEN=0
P07_B5_NEW_RAW_PC_ONLY_PREFLIGHT_PASS=1
P07_B5_BOARD_CONTACT=0
P07_B5_NEW_RAW_LAUNCH_AUTHORIZED_BY_PREFLIGHT=0
```

This is **source, ELF/map and signed original-image proof only**.
A preflight PASS does not establish physical ownership or authorize
a destructive board run. The new `--mode execute` path MUST NOT be
treated as routine follow-on to a successful `--mode preflight`.

## Exact admitted genuine B5 artifact identities (do not rebuild or patch)

| Artifact | Signed actual value |
| --- | --- |
| New B5 A53 ELF SHA256 | `0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf` |
| New B5 GNU map SHA256 | `1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8` |
| Accepted P03 shell XSA SHA256 | `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f` |
| Genuine B5 A53 ELF physical load | `[0x00000000,0x00107BC0)` |
| Original accepted V3 A53 physical load | `[0x00000000,0x00106B00)` |
| New low-DDR footprint growth | 4,288 bytes |
| Original 27 × 512KiB P02 records | `[0x40000000,0x40D80000)` |
| B5 26-tick 1010-neuron raw trace buffer | `[0x42000000,0x420CD280)` (840,320 bytes) |
| Original V3 terminal mailbox | `[0x43FF0000,0x43FF0100)` |
| **New B5 terminal mailbox** | `[0x43FF0100,0x43FF0200)` |
| **P03-wide adapter address aperture** | `[0x40000000,0x44000000)`, **64MiB** |
| Official MNIST TEST | `SEALED_NOT_ACCESSED` |

**Important distinction:** Both the new B5 trace buffer and the new
B5 mailbox are **inside** the P03 adapter's broad 64MiB DDR
backing aperture. They are outside the 27 actual P02 context records
and the narrower original TRAIN/route/descriptor/mailbox allocations.
This narrower non-overlap is a necessary geometry sanity check,
**NOT physical ownership evidence** against Linux's RAM allocator,
U-Boot, TF-A/BL31, FSBL, PMU firmware, RPU, other A53 cores, PL DMA,
reserved-memory nodes, or other consumers. The previously accepted
V3 standalone app also did NOT establish low-DDR firmware exclusivity.

For background, consult AMD's **Kria KV260 Starter Kit DS986**, the
K26 SOM boot-memory/firmware documentation, and the **XSDB Zynq
UltraScale+ MPSoC** target/memory-access reference:
- https://docs.amd.com/r/en-US/ds986-kv260-starter-kit/Starter-Kit-Firmware-and-Software
- https://docs.amd.com/r/en-US/ds986-kv260-starter-kit/Product-Details
- https://docs.amd.com/r/2024.2-English/ug1725-xsdb-reference-guide/Debugging-Applications-on-Zynq-UltraScale-MPSoC

These references establish the general platform boot/debug
environment; they do **not** reserve the addresses above for B5.

## Required next safety work — before asking for physical execution

1. The operator must review **this exact allocated DDR envelope and
   ELF footprint**, the original 27 signed P02 records, original
   route/ingress staging addresses, QSPI firmware + Linux/TF-A
   ownership, any other cores and DMA masters. When possible,
   obtain a **read-only prior-boot inventory** of the KV260
   `/proc/iomem`, active device-tree `reserved-memory` entries
   and boot log. Treat those as observations, not as comprehensive
   proof that future suspended/halted firmware no longer uses a
   region. Do **not** write to DDR to probe ownership.
2. Decide whether there is convincing documented exclusive ownership
   or whether this is an **explicitly operator-accepted unproven
   destructive DDR coexistence risk**. An observed free range or
   passing PC tool must never automatically change the report fields
   `..._independently_proven=0` to `1`.
3. Confirm a fresh KV260 cold power cycle **before** any new run,
   dedicated JTAG ownership, no critical Linux users/processes
   needing recovery, and an externally recoverable board. The
   existing physical stager halts/discards Linux, uses the original
   P03 PL bitstream, and physically stages/readbacks all 27 original
   records + descriptor + routes + **TRAIN0**, all before B5 ELF
   download. This is not safe to run on a needed Linux session.
4. If and ONLY IF independent physical preflight, operator risk
   acceptance and recovery plan are satisfactory, a separate
   decision can authorize the exact B5 `--mode execute` with
   **eight original signed-model approvals plus five B5 new
   firmware/sidecar/low-DDR/mailbox approvals**. Actual approval is
   explicit flags on that session; no one should set all flags
   automatically merely because a PC review passed.
5. Any JTAG physical attempt requires a cold power cycle afterward,
   including failed/partial attempts. **Never resume halted Linux.**
   Keep an entirely new external physical evidence folder and
   preserve all prior V3 physical and B5 ELF/map evidence unchanged.
6. After an actual authorized B5 run, use
   `scripts/p07_b5_raw_physical_verify.py` **PC-only** to
   authenticate the same-session original source readbacks,
   ELF/map and B5 mailbox, and compare the exact **840,320B**
   *physical* raw per-neuron trace against the original frozen scalar
   trace. A successful comparison does not by itself establish DDR
   exclusive ownership or formal P07-B.5.4 completion.

## PC-only memory risk report — safe to run now

From the repository V3 directory with the **same environment as the
already passing B5 physical preflight**, run:

```bash
export P07_B5_DDR_RISK_REPORT="$HOME/Thesis_Evidence/p07_b5_raw_ddr_risk_review_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b5_raw_ddr_risk_review.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P07_B4M_STAGE" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --offline-report "$P07_B5_RAW_OFFLINE" \
  --out "$P07_B5_DDR_RISK_REPORT"
cat "$P07_B5_DDR_RISK_REPORT"
```

Expected PC-only status (the correct behavior still identifies risk):

```text
P07_B5_RAW_REAL_VITIS_ELF_MAP_AND_SOURCE_MEMORY_CONTRACT_PASS=1
P07_B5_RAW_CAPTURE_INSIDE_P03_BROAD_DDR_APERTURE=1
P07_B5_RAW_INDEPENDENT_DDR_AND_BOOT_OWNER_PROOF=0
P07_B5_RAW_BOARD_EXECUTION_AUTHORIZED=0
P07_B5_RAW_BOARD_CONTACT=0
```

### Status of P07-B

P07-B.5.1 original scalar and B5.2 four real original
TRAIN fingerprint-parity sessions: **accepted**.
B5.3 original scalar raw trace, new distinct A53 ELF and
original PC preflight: **accepted**.
B5.3 genuine physical raw 26×1010-neuron trace, independent
840,320B bytewise equality: **NOT YET COLLECTED OR ACCEPTED**.
B5.4 final acceptance and P07-B.6/P08-B: **OPEN**.
Original official TEST remains SEALED; PRs #49/#50 remain draft.
