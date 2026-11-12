# M08 D3.2 — PS–PL protected AXI: PC boot-platform evidence matrix (2026-11-12)

**Gate:** M08 **D3.2** offline boot/PS provenance source implemented and corrected; **owner-PC successful inventory NOT YET RECEIVED/ACCEPTED**. Neither a file found by name nor a hash by itself authenticates which platform configuration actually ran. Dependent PS boot integration remains **BLOCKED pending owner receipt and real platform sources**. Original bit.bin SHA256 `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` stays **QUARANTINED**. No FPGA load, JTAG, AXI MMIO, PS register changes or boot modifications.

## 1. Proven prior original evidence versus incomplete boot evidence

The latest D3.2A handoff [M08_D3B_NEXT_CHAT_HANDOFF_2026_11_12.md](M08_D3B_NEXT_CHAT_HANDOFF_2026_11_12.md) reports owner-verified native D3.1 Vivado 2025.2 **block-design only**, K26 / KV260 SOM v1.4, PS HPM0 FPD/HPM1 FPD/HPM0 LPD disabled, PL0 *BD readback* at 99,999,001 Hz, TTC0 channel-2 fan A12. Native evidence receipt SHA256 `955677040227dd5eaef81e49421b6b4c56f2436ca829036d3836d217371043a1`; Vivado output XDC SHA256 `7b5f25d14ed1b45ba4c858277d661ba61c0490957370c195218b65de30d899ff`. **Not physical clock/fan or boot evidence**. Owner twice passed independent Icarus D3.2A PS policy and unintegrated liveness suites; neither is PS ATB/AIB hardware proof.

Historical D2 [original deployed M08 overlay review](M08_D2_OWNER_ORIGINAL_M08_DECODED_OVERLAY_FINDINGS_2026_11_12.md): real decompiled original M08 overlay DTS SHA256 `772c6b0bb299d0bf0665cc79063a198d331dc9543249e5c62f7f0cff18d9aabe` (original owner receipt status attested); original *deployed binary* DTBO named `m08-v1-fan-page-uio-review.dtbo` SHA256 `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` in owner PC evidence, but its bytes have **not** been re-read in this D3.2 development. The decoded overlay has only FPGA-full firmware/reset + independent `&amba` identity/page UIO devices, **no explicit PL0/assigned-clock or AFI properties**. That is a **fact about the overlay only**, not the boot base DTB/applied tree or the cause of the Linux stall. Stock `k26_starter_kits.dtbo` SHA256 `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1` is a historical filename/digest, **not locally recovered by this chat**. Earlier stock PC lookup was exhausted: do not restart broad blind stock searches.


### 2026-11-12 owner-PC first-run failure and corrective action

The owner's initial run rejected `$HOME/Thesis_Evidence/M08/m08_2b_path_a_uio_overlay_REVIEW_ONLY_tuzu33oo/m08-v1-fan-page-uio-review/m08-v1-fan-page-uio-review.dtbo` with `pinned original SHA256 mismatch`. **This was a scanner false positive due to filename collision, not evidence of original artifact modification.** That earlier folder is named `REVIEW_ONLY`; its actual SHA256 was not supplied, so no claim about its contents or deployment is justified. The previous scanner incorrectly demanded the deployed DTBO SHA `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` for *every* basename match.

The corrected **v2 inventory schema** records `historical_reference_filename_match`, `pinned_original_digest_match`, `historical_reference_comparison`, and a SHA256 for hashable candidates. `SAME_BASENAME_DIFFERENT_SHA256_CANDIDATE_ONLY` **does not abort the inventory and never authenticates the candidate**. Summary `pinned_originals` distinguishes matching byte paths, same-name different-byte paths, missing paths, and unhashed paths. Only `SHA256_MATCH_HISTORICAL_REFERENCE_BYTES_ONLY` sets the match flag, and even that is **not** proof of firmware deployment or boot execution.

**Milestone naming simplification:** Use the existing **M08 → D3 → D3.2 protected PS–PL AXI integration**. Evidence, boot/PS ownership, AXI containment and Linux integration are workstreams and acceptance criteria—not new numbered milestones for each test or operator receipt. Legacy D3.2A/B.1 labels remain as historical references; new work reports progress under **D3.2**.

## 2. Boot/FPD/driver ownership matrix (source-dependent, no false provenance)

| Boundary | Authentic input required for next review | Evidence from repository / historical owner texts | Present configuration owner / release |
|---|---|---|---|
| Original XSA / PS initialization | Exact original exported `.xsa`, generated `psu_init.c` / `psu_init.tcl`, platform/Vivado version and original SHA receipt | D3.1 BD Tcl/native report proves only a **standalone proposed PS preset**, not an XSA used for boot | **UNKNOWN; NOT SUPPLIED** |
| FSBL / PMUFW / ATF / U-Boot | Original boot-platform build manifests, boot-image components/versions and config provenance (no execution or unpacking) | No matching original firmware bytes/boot manifest authenticated by current D3.2B review | **UNKNOWN; NOT SUPPLIED** |
| ATB4 upstream of FPD HPM0 | Pinned UG1085 revision + exact boot-stage handler/source for RESP_EN, RESP_TYPE, timebase, prescale, IRQ, reset defaults and first-fault policy | D2/D3.2A propose **ATB instance 4**; no proof enabled or responsive at failed boot | **UNKNOWN; BLOCKED** |
| AIB13 + outstanding AR/R/AW/W/B | Boot-side isolation owner + ACK semantics + no-new-transaction/quiescent-drain evidence | D2/D3.2A identify **AIB instance 13**; no quiescence, ACK or late-response proof | **UNKNOWN; BLOCKED** |
| PL0 clock, PS reset | Genuine PS init/boot DT clock owner, `PL0_REF_CTRL`/CLKACT, `pl_resetn0` and independent runtime observation | D3.1 native *requested/reported* PL0 clock; failed-boot value **not captured** | **UNKNOWN; BLOCKED** |
| HPM0 128-bit PS AFI | Match original XSA GP0 width/AFI against boot-stage AFI and Linux ownership, exact version | Original M08 BD requested 128 bits; no verified boot AFI | **UNKNOWN; BLOCKED** |
| Linux base tree vs stock overlay vs *applied* tree | Versioned base `.dtb`, stock `.dtbo`, original M08 `.dtbo`, kernel/DTS build receipts, FPGA-region manager/driver source | Original **M08 overlay only** was decoded; independent `&amba` UIO clocks/gates absent | **UNKNOWN; BLOCKED** |
| Cooling / stock rollback | Independent owner-original fan operation/thermal and boot rollback; stock package receipt | PS TTC0 EMIO waveout2→A12 static source/XDC verified; hardware cooling after PL switching unverified | **UNKNOWN; BLOCKED** |

**Interpretation:** XSA ≠ firmware register writes at boot ≠ runtime PS register readback. Generated `psu_init` ≠ proof it was linked/executed. Stock DTBO ≠ Linux base DTB ≠ applied device tree. Vivado BD validation ≠ OS clock or AFI ownership. Boot component name/metadata ≠ authenticated boot-component selection. **A SHA match establishes bytes only**, not boot use.

## 3. New offline inventory / receipt tool

Implementation: `scripts/m08_d3b_boot_platform_inventory.py`; synthetic positive/negative tests: `tests/test_m08_d3b_boot_platform_inventory.py`. Default PC-only bounded roots are the v1 repo directory and `~/Thesis_Evidence/M08`; optionally enumerate **explicit owner-selected narrow folders** using repeated `--extra-dir`. Scanner walks local regular files only, ignores symlinks/large cache trees, limits depth/entry count, classifies XSA/PS-init, boot package metadata, FSBL/PMU/ATF/U-Boot, base and overlay DT, manifests and native logs. It does not inspect or unpack boot binary contents; `BOOT.BIN` carries only path/size/class and is **not hashed**. Other candidates are SHA256 streamed only within the 256-MiB per-file cap; over-limit files yield a recorded **unhashed** state. Historical stock/M08 DTBO filenames are **not** identity checks: an exact SHA256 match is recorded as matching historical reference bytes only; differing bytes are inventoried as a separate unverified candidate, and files over the hash limit are never claimed as matches. No filename, matching hash, or candidate search proves an image was deployed or booted. Unknown originals remain explicitly UNKNOWN, not a PASS.

No user files are copied into Git or the output. Receipt writer requires a freshly created **empty sibling** of historical owner evidence runs. It emits `00_boot_platform_inventory.json` and `99_evidence_sha256.txt` (relative SHA256 of the JSON). Only the output folder is written; all source/evidence trees are read-only. Existing evidence, parent immutable D3.1 receipt, old .bit.bin and stock image are never overwritten. A path discovery is **unattested** until the owner validates the output and, if required, supplies specific relevant source with exact version/provenance.

### Owner PC commands (NO BOARD)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3b_boot_platform_inventory.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
mkdir -p "$HOME/Thesis_Evidence/M08"
RUN="$(mktemp -d "$HOME/Thesis_Evidence/M08/m08_d3b_b1_inventory_XXXXXXXX")"
python3 scripts/m08_d3b_boot_platform_inventory.py --out-dir "$RUN"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 -m json.tool "$RUN/00_boot_platform_inventory.json" | less
printf 'Owner PC inventory evidence: %s\n' "$RUN"
```

Optional additional **local PC** folder (explicitly chosen and narrow): append `--extra-dir "$HOME/path/to/already_saved_platform_exports"` to the script invocation. No remote mounts, serial/JTAG devices, board SSH, firmware installation, synthetic PS register writes or physical MMIO. If the bounded scan rejects a large evidence root, **do not weaken limits blindly**; narrow with a reviewed extra input in a new run directory, record missing scope, and ask for review. Do not put the output in the original native run folder.

## 4. D3.2 evidence gate and stop conditions

**Current state:** corrected code and negative tests committed; CI review and owner replay are separate evidence classes; **not yet owner accepted**. There is no D3.2B owner-original inventory report for this branch and no authenticated original XSA, boot-stage ATB4/AIB13 enable/ACK, actual Linux base/applied DT, AFI, PL0 or independent fan-state provenance. The script never sets physical signoff flags true. **Next:** owner runs the inventory, preserves the raw JSON and SHA receipt, checks exact candidates and missing originals, then reviews source-specific findings before any dependent boot-time configuration implementation or protected HPM0 hardware candidate. Independent abstract AXI simulation research can proceed without pretending hardware is safe.
