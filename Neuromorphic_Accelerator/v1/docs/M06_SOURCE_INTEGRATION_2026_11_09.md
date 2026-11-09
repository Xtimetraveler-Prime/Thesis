> **LATEST M06 CONTINUOUS PAGING + ORIGINAL VIVADO HANDOFF (2026-11-09):** This report remains the source-only single-session paged neural+AXI behavioral baseline. M06 has since added **source-only** continuous multi-window exact sparse LIF with positive-delay recurrent events across window boundaries (up to 256 SOFTWARE ticks, NOT new M05 RTL), independent M02/M03 parity and integrated shadow epochs. Added owner read-only original 2025.2 vendor mem_sc exact 4×256 SI /1×128 MI port/simulator model contract query for future genuine AXI XSim, plus six committed machine-checked HOST stimulus cases. Total M06 source-only regressions now **92** (67 prior +11 multiwindow +8 simulated probe auditor +6 AXI golden vectors). **No original generated vendor XSim yet**, no warning inventory repeated, no physical DDR. [Authoritative new owner Vivado commands and extraction](M06_CONTINUOUS_AND_VENDOR_XSIM_HANDOFF_2026_11_09.md). Older 67-test content below is historical.

# M06 — source-only neural paging, AXI behavioral transfer, and speculative epoch boundary

**Status 2026-11-09 UTC:** M06 IN PROGRESS on independent new draft PR #80, branch agent/neuromorphic-accelerator-v1-m06-ddr-residency. M05 PR #79 was accepted and merged into main at b908fd94d2ab817c2f118573b8fd374476707bf6, and the M06 branch was created FROM that exact main merge. No physical FPGA, real DDR, DMA, PS Linux, MMIO, JTAG, Vivado/XSim generated SmartConnect, synthesis, bitstream, full post-route or timing test occurs in this increment. **All new execution here is host Python and simulated bytearray/AXI behavior.** The 63 unresolved original PS memory SmartConnect warning occurrences are preserved as an M06 integration-risk register, NOT waived.

## Why this is real M06 progress rather than another D4 warning inventory

The original M01 architecture study chose option B, configurable whole-block LRU residency, as the initial implementation baseline; A (individual state) and C (pinned-prefix hybrid) remain later matched controls. The original M05 accepted signed32 rolling event scheduler handles 1,024 on-chip neurons, 4,096 synapses, up to 4,096 individual signed-W16 deliveries/tick, delays 1..8 and 64 ticks/run. M06 now **actually executes M02-exact sparse recurrent LIF work through a canonical memory/cache interface** rather than merely predicting traffic from an arbitrary access list. It then exercises that same interface through a strictly scoped 256b-to-128b Python AXI behavior model, with both negative transfer-fault cases and independent neural parity. It does NOT wire these Python modules to physical HLS RTL; that is future vendor/board integration.

### A. Exact paged neural state

Code: src/neuromorphic_accelerator_v1/m06_paged_replay.py and preexisting m06_block_residency.py.

- A neuron state access is a logical neuron ID, translated to the correct full block and byte offset with validated Geometry. Resident data is explicitly bounded by resident_budget_bytes. Dirty blocks are written to the canonical image on eviction/flush; LRU and page generations enforce identity. A revoked EMULATED owner lease, stale version, duplicate transfer, invalid page/record or interrupted transfer prevents continued execution through a sticky poisoned cache. The cache also validates exact full-page read size, integer generation, positive transfer count, and writeback acknowledgment tuple/version before changing resident or dirty tags; malformed transport responses quarantine the cache.
- Signed16 LIF computation, eligibility, zero/canceling individual deliveries, positive-delay recurrent synapse fanout, per-tick admitted-delivery bound and sorted external ingress follow the original accepted M02/M03/M05 behavior. Every evaluated voltage is read from the **actual modeled block cache** and the new voltage is written back through that cache. Only the nonzero-neuron set, static neuron configuration, adjacency and future event buckets remain conceptual on-chip metadata. This is not DDR-backed synapse/adjacency virtualization yet.
- For >=6-byte state records, bytes 0..1 store signed16 little-endian voltage; bytes 2..5 store unsigned32 (last_completed_tick+1) with zero = never evaluated in the epoch; following bytes remain reserved and unchanged. The model rejects a future-dated watermark on state reloading, and dirty eviction/restoration preserves both voltage and watermark. The initial >=16B row width in matched study mirrors the *size* proposed in M01, but this record layout is source-only and **is not a new authenticated FPGA/PS memory ABI**. For 2..5-byte rows, the initial voltage-only baseline remains supported.
- **Current session/continuation limit:** each paged neural run begins from the M02 initial state at logical tick zero with a fresh cache. Although the modeled state includes a last-update watermark and the shadow epoch can commit a final canonical image, resuming the next invocation at nonzero logical time, retaining recurrent deliveries across sessions, recovering a physical crash and relocating synaptic adjacency/weights to DDR are NOT implemented; those remain M06 tasks before full-scale virtualization claims.
- The exhaustive full-neuron per-tick voltage trace is a **test-only observer copy** and does not decide runtime spike firing or next-tick eligibility. It is excluded from the traffic counters; it would require additional observation traffic if captured from physical off-chip state. Exact comparisons to the independently implemented M02 dense/event and M03 exact sparse oracles cover seeded recurrent, 64-tick, wheel wrap, high signed current, persistent last-update and repeated page churn. A fault or admission overflow quarantines the run; it cannot be committed to canonical through the accepted shadow-epoch protocol below.

### B. Explicit 256-bit upstream to 128-bit downstream behavioral AXI4 model

Code: src/neuromorphic_accelerator_v1/m06_axi_transport.py; tests/test_m06_axi_transport.py.

- This is a **host simulation of an aligned full-width AXI4 INCR envelope**, not functional RTL verification of the original 2025.2 AMD AXI SmartConnect, not a captured vendor trace and not a physical DDR controller.
- The modeled DMA-side (upstream SI) data width is 256 bits (32 bytes/beat); modeled PS/HP0-side (downstream MI) width is 128 bits (16 bytes/beat). Explicit lower/upper byte-lane and WSTRB 32-bit to 2×16-bit mapping, AR/AW SIZE 5→4 and beat count 1→2 are verified through deterministic host source tests, including high-order bytes. A 256b burst is split before any **4KiB** boundary, and at most 128 upstream/256 downstream beats per burst. Range/alignment checks reject out-of-bounds 32-bit logical address offsets, booleans and unsupported shapes.
- Logged independent channel-side, synthetic held-VALID/READY handshake samples include U_AW/U_W/U_B/U_AR/U_R and D_AW/D_W/D_B/D_AR/D_R. A deterministic READY cadence produces stalls and per-payload SHA256 stability samples; watchdog timeout, RRESP/BRESP error and lost B after potentially accepted W data all reject. The code **serializes** channels and DOES NOT implement real vendor arbitration, reordering, outstanding-transaction rules, USER signal semantics, Xilinx simulation libraries, or clock-domain conversion.
- Unlike the very first purely atomic CanonicalImage bytearray backend, the AXI behavioral backend deliberately updates bytes after individual accepted downstream W beats. Thus a W stall after a prior W acceptance or a lost B response can produce an **uncertain, partially modified page**. AXIModelImage.uncertain_pages prevents any subsequent canonical snapshot or read via a fresh cache from treating it as trusted state, until a separately designed recovery/epoch mechanism exists. The cache is sticky poisoned on transport errors. Do NOT automatically retry an unknown-commit transfer.
- The reported bytes/transactions/READY stalls are **source-defined counts**; no hardware clocks, DDR latency, bandwidth, bus arbitration, physical performance or power may be inferred. Physical addresses are not reserved/owned: the model's logical_bus_base is an abstract address offset. No particular Linux DDR region is approved.

AMD PG247 (2026 documentation) says AXI SmartConnect **can** perform unequal-width conversions, that downsizing and multi-threading are not simultaneously supported, and that USER byte-lane propagation has defined padding/truncation behavior; this is documentation of a generic IP capability, **not an attestation for the exact generated 2025.2 D3 memory SmartConnect instance or its original BD 41-2384/41-237/41-3281 warnings**:
- https://docs.amd.com/r/en-US/pg247-smartconnect/Width-Conversion
- https://docs.amd.com/r/en-US/pg247-smartconnect/User-Defined-Signal-Propagation
- https://docs.amd.com/r/en-US/pg247-smartconnect/Feature-Comparison

### C. Explicit speculative epoch / abort / commit model

Code: src/neuromorphic_accelerator_v1/m06_shadow_epoch.py.

The original M05 rolling kernel may emit provisional rows before a late failure. M06 cannot treat those rows or partial DDR writes as a completed stateful inference. To model a safe future memory boundary, ShadowEpoch creates a **separate software shadow canonical image**, executes the paged neural run with an AXI-model-backed cache against that shadow, then compares every full-trace voltage/spike against an independent M02 dense oracle **and** verifies exact final canonical voltage+watermark bytes. Its strict state machine is:

    PREPARED -> RAN_UNCOMMITTED -> VALIDATED_UNCOMMITTED -> COMMITTED
                      \                         \
                       FAILED_REQUIRES_ABORT -> ABORTED
    PREPARED -------------------------------> ABORTED

The original canonical image remains unchanged until successful independent verification, canonical lease/version/byte comparison, then one **single-threaded Python bytearray update**. Faulty, corrupted, stale, incomplete or unverified work is not published. A simulated missing write response may alter partial bytes **in the SHADOW**, but abort discards that image without changing original canonical bytes.

**Critical limitation:** this is a software-only feasibility contract. Real DDR does NOT provide atomic page or multi-page writeback, Python bytearray swap is NOT a physical operation, the shadow image was cloned without modeled DMA cost, and independent M02 verification is a *test* oracle rather than a proposed host critical-path algorithm. A real PS/PL implementation must secure a separately owned DDR shadow region, decide transaction/commit marker and crash/reboot atomicity, and account for state-copy traffic. Recovery after a crashed physical write is **NOT DESIGNED / NOT PROVEN**.

### D. Same neural roles, different ID locality: 12-case source-only traffic experiment

Code: src/neuromorphic_accelerator_v1/m06_matched_experiment.py, scripts/m06_matched_source_study.py and tests/test_m06_matched_experiment.py.

Exactly **64 logical neurons**, **8 active roles**, **8 ticks**, and 64 spike-producing external events are evaluated for each case. Clustered neuron IDs 0..7 and dispersed IDs 0,8,..56 get the identical ordered roles and current values, so there are 64 successful spikes and 64 actual LIF evaluations in every case; full neuron traces are independently checked against M02 dense. Each evaluated neuron is read and written through BlockCache backed by AXIModelImage, with static 16-byte records, variable block size and budget. This is **role-isomorphic**, NOT identical neuron identities/weight matrices and NOT physical FPGA work matching. The script saves a fresh JSON result, never overwrites old owner evidence.

**Actual model output from source-only GitHub Actions run 42664323737, not from physical hardware:**

| Neurons/block | Resident budget | Clustered modeled bytes / transactions | Dispersed modeled bytes / transactions |
| ---: | ---: | ---: | ---: |
| 4 | 256 bytes | 256 / 4 | 8192 / 128 |
| 4 | 512 bytes | 256 / 4 | 1024 / 16 |
| 8 | 256 bytes | 256 / 2 | 16384 / 128 |
| 8 | 512 bytes | 256 / 2 | 16384 / 128 |
| 16 | 256 bytes | 512 / 2 | 16384 / 64 |
| 16 | 512 bytes | 512 / 2 | 16384 / 64 |

These 12 cells are **software model accounting ONLY**, and include no DMA setup, real bandwidth, clock stalls, physical cache-tag RAM, Linux-owned address, synapse fetch, nonzero-set resource cost, real host traffic, dynamic scheduling overhead, or energy. They demonstrate *why locality and block-granularity selection matter*, not a measured speedup.

The new GitHub workflow for M06 executes all tests, reruns accepted M01–M05 source regressions, prints all 12 source-only rows and uploads an explicitly labeled 30-day source-only JSON artifact. It makes no hidden use of Vivado or FPGA hardware.

## Test and owner-verification boundary

Before last-update extensions there were 60 new M06 host regression methods (initial 15 baseline + 12 paged replay + 17 AXI behavioral link + 6 matched study + 10 shadow epoch) and inherited M05 discovered 430 tests. Additional 3 exact temporal state/watermark tests and 4 malformed backing-page/acknowledgment tests bring the M06 count to **67**, subject to final CI readback. Use the latest GitHub Actions M06 workflow (source-only) and all inherited M01–M05 workflows at the final branch HEAD; any previous individual CI failure was a source/test fixture error subsequently corrected and original logs must not be falsified.

### Local Ubuntu / VS Code terminal verification — NO Vivado/board needed

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    git status --short

    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05*.py' -q
    python3 -m unittest discover -s tests -p 'test_m04*.py' -q
    python3 -m unittest discover -s tests -p 'test_m03*.py' -q
    python3 -m unittest discover -s tests -p 'test_m02*.py' -q
    python3 -m unittest discover -s tests -p 'test_m01*.py' -q

    mkdir -p "$HOME/Thesis_Evidence"
    python3 scripts/m06_matched_source_study.py \
      --output "$HOME/Thesis_Evidence/m06_model_only_matched_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

The CLI creates an EXCLUSIVE NEW report file; no originals are overwritten. It is intentionally safe for any PC with Python 3 standard library; no dependency on Vivado, a GPU, Linux PS serial/UART or physical DDR/board. Source-only CI is already independent, so this owner-local rerun is optional for development progress.

### Next ONE genuine tool-dependent gate (requires owner Vivado workstation)

Not another static warning inventory: perform a **functional offline Vivado 2025.2 vendor-generated mem_sc AXI-MM datapath simulation** using the exact original immutable D3 generated IP files. The gate must drive real 256b AXI4 AW/W/B and AR/R with a deterministic memory image at the actual 128b MI, both data halves, nontrivial per-byte WSTRB, several aligned INCR lengths including split-boundary bursts, downstream stalls, response errors, ID/USER widths observed from actual original endpoint properties, and reset/fault paths. Verify accepted handshakes and bytes using independent scoring against the source ABI; do not infer USER semantics from m00..m05 warnings alone. **No fabricated XSim PASS**, no use of a simulated Python model as substitution for vendor IP. This actual functional experiment has not yet been executed or constructed from the owner's generated hierarchy; source-only CI cannot validate it.

Stop before any physical DDR allocation, Linux MMIO, FPGA bitstream, board programming, JTAG or physical PS memory experiments until the owner separately authorizes a safe reserved region and confirms vendor protocol integration. M06 milestone remains OPEN; draft PR #80 UNMERGED.
