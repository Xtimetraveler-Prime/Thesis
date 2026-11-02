# P08-B4.4 — Original full1024 KV260 single-session A53 service-time audit (PC ONLY)

## ACCEPTED: actual original 1023 ordinary-frame six-phase A53 latency report (2026-11-02 UTC)

The operator ran the signed read-only B4.4 six-phase audit against the
actual full1024 B4.2 physical evidence and independent provenance report,
with these exact success markers:

~~~text
P08_B4_4_ONE_ORIGINAL_VERIFIED_1024_SESSION_A53_DESCRIPTIVE_TIMING_PASS=1
P08_B4_4_ACTUAL_A53_CNTFRQ_EL0_HZ=99999001
P08_B4_4_1023_ORDINARY_MEDIAN_SERVICE_MS=13034.111500773894
P08_B4_4_1023_ORDINARY_P95_SERVICE_MS=13167.109029419204
P08_B4_4_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0
~~~

The **exact actual full1024 physical evidence directory** is now known:
 /home/dna/Thesis_Evidence/p08_b4_2_original1024_physical_20261102T145943Z

Immutable resulting **single-session descriptive timing report**:
 /home/dna/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json

**Operator report SHA256: 4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81**.

This report binds back to the unchanged independent B4.2 physical
numerical/FNV/timing report SHA256
297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032
and original full1024 numerical scalar SHA256
7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8.
This is ONE physically accepted JTAG session; its 1023 ordinary
image-timing statistics exclude selected trace ordinal 1023.

### Per-phase original A53 measured service breakdown

| B2.3 original A53 measured phase | 1023-frame median ms | Share of SUM of full service ticks |
|---|---:|---:|
| Restore 27 frozen B2.4 mutable logical-core contexts | 5826.693269 | 44.695321% |
| Encode B1.3 original input | 18.673677 | 0.143253% |
| Restart original virtualized scheduler | 228.098739 | 1.749822% |
| All 26 ticks, 702 dispatches, physical paging/routing/nested trace | 6935.069581 | 53.215729% |
| Validate inference receipt | 0.000430 | 0.000003512% |
| Commit original neural result journal | 25.534815 | 0.195872% |

Combined **state reset/restore + 26-tick mixed software/PL execution**
accounts for **97.9110497583%** of total measured ordinary A53 service
time (sum-based, not median-based). The ordinary whole-service
median is **13.034111501 seconds/image** and P95 is **13.167109029
seconds/image**, normalized with the actual observed A53 frequency
99,999,001Hz. The earlier 1024-INCLUSIVE time distribution's min,
median, P95 and max MUST NOT be conflated with the 1023 ordinary
stats. Phase medians do not algebraically sum to service median.

**Crucial source-level interpretation** (verified directly against
software/p08/p08_b2_context_reset.c and image-only firmware):

Every image calls p08_b2_reset_image. This requires all 27 original
immutable backup 512KiB records to be SHA256-verified **before first
destructive mutable copy**; then each 512KiB context is memcpy'd to
the live mutable DDR, D-cache cleaned, barriered, invalidated, and
SHA256-verified again as a correct destination. The source code
requires a 27-context total of exactly **14,155,776 bytes = 13.5MiB**
of mutable COPY per image (13.5GiB copied for 1024 images),
plus **at least 27MiB SHA-256 source/destination verification read
traffic per image** and other copy/cache reads/writes.
Hence the ~44.7% reset phase is NOT solely a DDR copy or a PL
compute cost. It includes software cryptographic integrity checks,
cache maintenance and repeated source/destination scans.
The integrity checks were intentionally added for correctness and
the exact frozen-model physical state guarantee; removing them
without new proof would change the experiment's contract.

The ~53.2% 26-tick phase is also NOT PL-only neural engine compute:
firmware calls the original P07 virtualized 27-core scheduler and
includes 702 physical P03 dispatches plus MMIO/polling, dynamic
context paging/trace readbacks, routing and barriers. The
six-stage sidecar **does not separately quantify** PL time,
CPU polling time, per-page DMA/memcpy or neural arithmetic. No
PL clock source was independently calibrated to seconds. Do
NOT use these results to assert a PL-only 13-second neuron engine
or an algorithm speedup/slowdown relative to the single-core
Track A network.

### Accepted interpretation and experiment design gate

1. The two dominant measured phase shares (44.695% reset and
   53.216% all-tick mixed control/PL) suggest where to profile,
   not which resource is the root cause. The highest-priority
   next **separately instrumented** candidates are original
   full-context SHA/flush/memcpy/verify subspans and nested
   per-core pager page-in/page-out, MMIO dispatch/poll and
   trace-readback spans. Do NOT modify the signed accepted
   B2.3 ELF or call an optimized run equivalent without separate
   independently verified scalar/FNV parity.
2. Before any new destructive optimization experiment, preserve
   the accepted unmodified 1024-source run and compare **A53
   image-service boundaries** only, with actual per-run CNTFRQ
   and ordinary-frame ordinal 1023 trace isolation. Per-image
   measured scope includes context reset and result journal.
3. Original Track A six physical sessions form THREE A2.1-vs-A2.2
   instrumentation pairs, not genuine A-vs-B counterbalanced
   pairs. A fair A-vs-B temporal comparison needs new, distinct
   accepted runs in AB/BA/AB order, each coldboot/recovery
   independently controlled and evaluated at the run level.
   Network sizes differ: A 42 neurons/26 dispatches; B
   1010 neurons/702 dispatches and 27-context paging. Even a
   repeated difference remains a system/workload comparison,
   not an equivalent-neural-workload speedup.
4. Genuine 1023-image B timings were measured within ONE
   independently verified physical session. They are an
   accepted descriptive physical bottleneck baseline, NOT
   the repeated six-session P08-B4.4 Track A/B benchmark,
   boot/DDR/DMA exclusive ownership proof, pure PL time,
   or energy data. Official TEST remains sealed.

---

**Status:** Original 1024 TRAIN-derived validation scalar oracle and genuine
single-session KV260 neural/timing physical evidence independently accepted.
Final repeated Track A/B latency benchmark PENDING.

External signed independent B4.2 report:
 /home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json
SHA256: **297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032**.
Original frozen full1024 independent scalar:
 /home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json
SHA256: **7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8**.
The exact physical session evidence directory name was NOT pasted;
use the original operator shell environment variable P08_B4_PHYSICAL.

## Operator B4.2 first 1024 inclusive scalar-matched physical A53 timing summary

| Reported service duration metric | Raw A53 CNTVCT_EL0 ticks |
|---|---:|
| Count | 1024 |
| Minimum | 1,283,832,503 |
| Median | **1,303,433,920** |
| P95 nearest rank | 1,316,697,749 |
| Maximum | 1,327,299,037 |

The full-sample maximum exceeds minimum by ~3.386% of minimum,
and P95 exceeds median by ~1.018%. These describe within-session
frame-to-frame variation only; NOT repeatability across cold boots.
The actual B4 A53 CNTFRQ denominator was NOT in the user excerpt.

Conditional illustration ONLY: if actual B4 CNTFRQ is 100 MHz, median
is ~13.03434 seconds/image; min ~12.83833s, P95 ~13.16698s,
max ~13.27299s. The product 1024 x median is ~3.7075 hours,
but is NOT wall-clock elapsed duration because timing excludes
prelaunch setup and any gaps between measured service windows.
The accepted earlier Track A physical sessions observed
99,999,001 Hz, but this DOES NOT establish the B4 A53 frequency.

Original Track A A2.1/A2.2 3-pair ordinary 1023-image service
medians were approximately 35.67–35.72ms. Both tracks use the
same original TRAIN-derived 1024-source sequence and 26 neural
ticks, but their workload complexities are NOT matched:
A is 42 neurons, one logical core and 26 FPGA dispatches/image;
B is 1010 neurons, 27 logical cores virtualized in three physical
slots, with context reset/paging and 702 FPGA dispatches/image.
No isolated PL-only speedup/slowdown is supported by their ratio.
See docs/P08_B1_MATCHED_TRACK_A_LATENCY_CONTRACT.md and
docs/P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md.

## New read-only script: independently sealed frequency and six-phase breakdown

scripts/p08_b4_4_single_run_timing_audit.py checks the accepted
independent physical-report SHA, its original neural acceptance flags,
the original scalar oracle pin, the captured full1024 physical timing
sidecar's SHA-256, the accepted terminal mailbox SHA, all 1024
CRC-checked 256B timing records, exact actual A53 CNTFRQ_EL0 and
monotonic/additive six-phase timings. It produces new no-overwrite
external JSON without modifying or contacting the KV260.

Run in your PC/VS Code terminal, no hardware:

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b4-fullscale
git pull --ff-only origin agent/v3-p08-b4-fullscale
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b4_4_single_run_timing_audit.py \
  tests/test_p08_b4_2_monitor_mailbox_pc_only.py

export P08_B4_INDEPENDENT_REPORT="/home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json"
test "$(sha256sum "$P08_B4_INDEPENDENT_REPORT" | cut -d' ' -f1)" = \
  "297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032"

# IMPORTANT: Set to the EXACT prior accepted physical B4.2 session
# evidence directory. Do not infer it from the independent report filename.
# export P08_B4_PHYSICAL="/home/dna/Thesis_Evidence/<EXACT OLD B4 RUN>"

test -f "$P08_B4_PHYSICAL/full1024_capture/timing1024_physical.bin"
test -f "$P08_B4_PHYSICAL/full1024_capture/mailbox_terminal_physical.bin"

export P08_B4_4_DESCRIPTIVE="$HOME/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B4_4_DESCRIPTIVE"
PYTHONPATH="$PWD/src" python scripts/p08_b4_4_single_run_timing_audit.py \
  --report "$P08_B4_INDEPENDENT_REPORT" \
  --evidence "$P08_B4_PHYSICAL" \
  --out "$P08_B4_4_DESCRIPTIVE"
sha256sum "$P08_B4_4_DESCRIPTIVE"
~~~

The signed audit prints the ACTUAL frequency and normalizes all
counter ticks to milliseconds, computing ordinary-frame statistics
on **1023 images** while separately preserving selected trace
ordinal 1023. The six disjoint A53 phase intervals are:

1. Original 27-logical-core mutable context restore.
2. Frozen B1.3 original input encoding.
3. Virtual pager/scheduler reinitialization.
4. All 26 simulation ticks with 702 P03 FPGA dispatches,
   paging, routing and nested neural trace.
5. Final neural receipt validation.
6. Neural result journal commit.

Do not treat phase medians as additive. Per-frame phase SUMs
and cross-frame MEANS are additive; six phase medians generally
do not sum to the total-service median. All A53 counter times
exclude external host JTAG, initial PL programming and after-service
timing-sidecar commits. The PL FPGA cycle counter belongs
to a separate clock domain and has not been independently
calibrated to seconds.

Expected success markers:

~~~text
P08_B4_4_ONE_ORIGINAL_VERIFIED_1024_SESSION_A53_DESCRIPTIVE_TIMING_PASS=1
P08_B4_4_ACTUAL_A53_CNTFRQ_EL0_HZ=<actual measured B4 value>
P08_B4_4_1023_ORDINARY_MEDIAN_SERVICE_MS=<computed result>
P08_B4_4_1023_ORDINARY_P95_SERVICE_MS=<computed result>
P08_B4_4_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0
~~~

**Next:** use the phase shares and audited 1023-image durations to
design independently rebooted, original matched-source physical A/B
measurement sessions, partially counterbalanced AB/BA/AB, with
pair-level uncertainty and trace-scope isolation. The existing
six physical Track A A2.1/A2.2 sessions are timing-instrumentation
comparisons WITHIN Track A, not three matched A-versus-B pairs.
Official MNIST TEST remains SEALED; DDR boot/DMA exclusivity remains
unproven; no energy, isolated PL speedup, or six-session performance
claim is supported by this single verified B4.2 session.
