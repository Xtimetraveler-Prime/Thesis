# P02.3a Acceptance Record

**Phase:** P02 — DDR-backed logical-core virtualization  
**Sub-milestone:** P02.3a — Resident-bank page walker and ownership path  
**Accepted:** 2026-10-05

## Independent RTL verification

The directed RTL preflight was independently reproduced with:

```text
..............    [100%]
PASS: p02_context_page_bank_walker
PASS: P02.3a preflight completed successfully.
```

No FAIL or ERROR marker was reported.

The RTL gate traverses the complete configured bank depths rather than only
sampling boundary addresses.

## Independent full regression

The complete v3 Python regression was independently rerun.

Observed tail:

```text
........................................................................ [ 88%]
.........    [100%]
```

No failures or errors were reported.

## Acceptance decision

P02.3a is accepted as the PL-side resident-bank traversal and Port-B ownership
oracle for P02.3b.

This accepts:

- complete 428 KiB page-in traversal;
- complete 428 KiB full page-out traversal;
- 104 KiB mutable-only page-out traversal;
- exact DDR offset / resident bank / word-address mapping;
- 512 KiB record-base alignment rejection;
- explicit page ownership over the P05 Port-B transaction boundary;
- response-owner latching through the final acknowledgement;
- physical cycle and transferred-byte accounting.

P02.3a does not claim AXI burst behavior, routed HP0 integration, or physical DDR
latency/bandwidth. Those remain P02.3b/P02.4.
