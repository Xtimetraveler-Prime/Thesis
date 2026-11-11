# M08 tests explained — entry/read-only and hardware-readiness contracts

**Status:** M08.1 source under development; **NOT M08 acceptance or FPGA execution.** Do not reinterpret CI fixture data as a captured physical KV260 observation. Genuine board runs and original vendor place-and-route require local operator evidence.

## Scope and independent evidence

M08.1 is intended to answer **what is actually available on the development PC and the KV260?**, before risking unowned PS DDR or programming a PL design that lacks a proven Linux driver.

- `m08_entry.py`: immutable five-ZIP M06 acceptance SHA256 list from original M06 acceptance report, input-shape-only kernel DMA address guard, and a deliberately **never automatically ready** physical evidence checklist.
- `m08_capture_readonly.py`: host or KV260-on-device Linux inventory. Every subprocess is a named read-only argv, never `shell=True`. No `sudo`, `/dev/mem`, `vivado -mode batch`, flash, FPGA programming, DMA, or DDR memory writes. Output is a unique operator-owned mode-0700 folder with JSON and SHA receipt.
- `m08_receipt_audit.py` and `m08_audit_readonly.py`: independent SHA and schema/command-scope auditor. It detects file tampering and fake ready-to-DMA claims but **cannot cryptographically verify** that a board supplied an authentic boot log; owner observation/independent device and toolchain evidence remains necessary.
- `docs/M08_PHASED_HARDWARE_PLAN.md`: exact next gates (Vivado BD build, kernel-owned buffer, physical neural parity, matched hardware benchmarks, performance evidence and M09 handoff).

### Test-by-test meaning (host-only synthetic negative/positive fixtures)

| Test | Input and method | PASS means / what it does NOT mean |
| --- | --- | --- |
| `test_readiness_is_nonclaim_even_when_all_self_reported` | Missing, malformed and complete operator-text evidence IDs | An empty list fails readiness; even a complete *self-report* requires independent audit. No fabricated physical PASS. |
| `test_physical_dma_requires_kernel_owned_buffer_and_32bit_bound` | Valid 64B-aligned kernel API *claim*, then bare devmem, guessed allocator, invalid mask/bounds/alignment, booleans, negative/overflow cases | Only structural shape of declared DMA buffer is admitted. This is NOT a real allocation/driver proof, and `physical_allocation_verified=false` is mandatory. |
| `test_archive_inventory_is_sha_strict_no_faked_owner_vivado_pass` | Empty evidence directory, wrong/duplicate/symlink files, and SHA mismatch | Five accepted original M06 ZIP names must each appear once and have **their independently published exact SHA256**, without copies or mutations. Synthetic files cannot be accepted as Vivado evidence. |
| `test_host_capture_fake_safe_tools_does_not_claim_board` | Synthetic read-only command results from a PC environment | Records host source hashes/version observations and explicit no-board/DDR flags; a host OS cannot identify a live KV260. |
| `test_board_local_observation_is_not_fpga_attestation` | Synthetic Linux DT model text (a positive name and missing-model negative) | Evidence is labeled *local OS observation*, not a bitstream/AXI/DDR proof even if a string says KV260. |
| `test_exclusive_evidence_no_overwrite_or_invented_host_pass` | New output folder, SHA receipt, attempt to overwrite | Original evidence bytes are unchanged; no accepted pass is replaced by a later run. |
| `test_command_allowlist_and_board_device_file_allowlist` | Unapproved shell/Vivado/physical memory operations | Fail closed before executing any nonallowlisted command or reading device memory. |
| `test_real_cli_host_is_explicit_read_only_and_exclusive` | Genuine local read-only capture in CI's Ubuntu host, repeat same folder | Output is reproducible in structure with local timestamps/source SHA, no board PASS, and refusal to overwrite. CI runner is a workstation, NOT the KV260. |
| `test_host_receipt_audits_only_integrity_not_real_board` | Source-only fake host capture + independent SHA256 verifier | SHA, command allowlist and false physical readiness flags are enforced; it does not authenticate identity of a real KV260. |
| `test_board_local_receipt_never_authenticates_board_or_dma` | Synthetic DT payload + independent auditor | Even a board-local capture only proves receipt consistency. |
| `test_modified_receipt_is_rejected_even_with_valid_json` | Change one JSON field, preserve original receipt | SHA256 mismatch must fail. |
| `test_self_consistent_but_false_physical_or_extended_commands_rejected` | Regenerate valid SHA for fabricated DDR READY/board program, unauthorized command or fake archive state | Integrity alone cannot grant physical authority; auditor rejects fabricated status and unapproved captures. |
| `test_cli_preserves_accepted_receipt_and_exclusive_output` | Audit output in a new file, attempted repeat | Independent JSON result is only integrity-pass and is never overwritten. |

**CI:** `.github/workflows/neuromorphic_accelerator_m08_host_preflight.yml` runs `test_m08*.py`, inherited M07 and full v1 unittest discovery in a single process. It performs a real **host-only** inventory on Ubuntu GitHub Actions, validates the independent receipt and retains a marked `m08-1-host-only-physical-not-run` archive. No board, HLS synthesis, original AMD XSim, physical DMA or real DDR is exercised by CI.

### Test sources vs real hardware acceptance

The accepted M05 signed32 engine and accepted M06 signed16 pager differ in arithmetic width; they cannot automatically be compared as matched 4-way physical variants. M06's 64 KiB canonical memory is a simulated bytearray/RTL scratch, not Linux-owned DDR. The original AMD interconnect and historical M05 DMA memory graph do not supply a genuine kernel driver/bitstream. Before **any** physical latency/throughput figure, the exact original generated vendor sources, addresses, XSA/bitstream, DDR ownership, AXI transfer integrity and M02 independent neural reference must all be verified on target.

No owner board measurements are available yet; that absence should be shown as **OPEN**, not hidden or represented by model-only counters.

## Evidence acceptance strategy

The first genuinely useful owner deliverable is a **PC-host** preflight receipt with the original M06 ZIP digest matches and, if the board boots, a **separate board-local** receipt. Capture a serial boot log if the KV260 never reaches a usable Linux shell. These observations determine whether to pursue the current on-device Linux/driver path or a recovery/isolated boot plan.

Physical M08 acceptance requires future separately documented tests: signed neural trace parity, fail-closed fault behavior, actual DDR read/write and W-before-R ordering, real FIFO/backpressure, timing boundaries, routed utilization, and repeatable independent runs. A synthetic CI fixture must never be used for that acceptance.
