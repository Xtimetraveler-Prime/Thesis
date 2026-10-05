# P02.2 Acceptance Record

**Phase:** P02 — DDR-backed logical-core virtualization  
**Sub-milestone:** P02.2 — Software reference and transfer-model validation  
**Accepted:** 2026-10-05

## Independent focused verification

The combined P02.1/P02.2 focused gate was independently reproduced:

```text
..............    [100%]
```

This is fourteen passing focused test indicators with no reported failures or
errors.

The gate covered:

- fixed 512 KiB DDR ABI layout;
- deterministic context serialization and payload hashing;
- sparse-bank densification;
- fixed logical-core DDR addressing;
- 428 KiB full resident-payload page-in accounting;
- 104 KiB mutable-only page-out accounting;
- resident-state/event preservation across eviction and reload;
- equality of full versus mutable-only writeback results;
- protection of static banks;
- explicit victim writeback before replacement.

## Independent full regression

The complete inherited v3 pytest suite was also independently rerun.

Observed tail:

```text
........................................................................ [ 88%]
.........    [100%]
```

No failures or errors were reported.

## Acceptance decision

P02.2 is accepted as the software oracle for P02.3 hardware development.

This acceptance freezes:

- DDR as authoritative state for non-resident logical cores;
- 428 KiB as the complete resident payload transferred on page-in;
- 428 KiB as the simple full page-out policy;
- 104 KiB as the legal mutable-only page-out policy;
- the rule that partial writeback must be observationally identical to full
  writeback when static banks are unchanged;
- explicit page-out-before-page-in replacement ordering.

No physical AXI transfer, bandwidth, or latency is claimed yet.
