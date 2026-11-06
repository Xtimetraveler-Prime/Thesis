#!/usr/bin/env python3
"""P08-B4.6.3 PC-only frozen-source A/B A53 image-service boundary audit.

NO JTAG, XSDB, Vivado, subprocess, board reads or source rewriting. This
checks a pinned source revision, not the A2.1 ELF or any physical timers.
It cannot establish numerical parity, equal work, or physical admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = "p08-b46-a-vs-b-auth-once-service-boundary-static-audit-v1"
# Git blob identities of the ORIGINAL frozen source at B4.6 parent head.
# A changed firmware, timer, or launcher must be reviewed as a NEW arm.
PINNED_BLOBS = {
    "software/p08/p08_a2_board.c": "22d56b83e9e917889c7c9dd0dbf9bef9003a2a26",
    "software/p08/p08_b45_perf_once_full1024_a53.c": "2799620de02bebbe43ccdf45ca2657920936d1da",
    "software/p08/p08_b2_service_meter.c": "5f13798281a55c8e8ddaa3eb969b351b461b53cf",
    "scripts/run_p08_a3_2_1024.sh": "3c03d9f5a0f3bf3261542dde6cd5f3abcaea1e93",
    "scripts/p08_b45_perf_full1024_physical_run.py": "1c607a57aa8528a777a77508199ff4ebae77518e",
}

class BoundaryNoGo(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise BoundaryNoGo("NO-GO: " + message)


def blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") +
                        b"\0" + payload).hexdigest()


def compact_c(body: str) -> str:
    # Only used AFTER byte-exact Git blob SHA admission.
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    body = re.sub(r"//[^\n]*", "", body)
    return re.sub(r"\s+", "", body)


def function(source: str, name: str) -> str:
    m = list(re.finditer(r"\b" + re.escape(name) +
                        r"\s*\([^;{}]*\)\s*\{", source))
    require(len(m) == 1, f"missing/ambiguous C definition: {name}")
    start = m[0].end() - 1
    depth = 0
    for idx in range(start, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start:idx + 1]
    raise BoundaryNoGo("NO-GO: unbalanced C definition: " + name)


def ordered(source: str, tokens: tuple[str, ...], label: str) -> None:
    body = compact_c(source)
    end = -1
    for token in tokens:
        marker = compact_c(token)
        pos = body.find(marker, end + 1)
        require(pos >= 0, label + ": missing/reordered " + token)
        end = pos


def inspect_sources(v3_root: Path) -> dict:
    """Pure read-only source audit; suitable for synthetic native tests."""
    require(v3_root.is_absolute() and v3_root.is_dir(),
            "absolute existing v3 source directory required")
    root = v3_root.resolve()
    require((root / "LOIHI_TWIN_ROADMAP.md").is_file(),
            "v3 source root is not the accepted project")
    sources: dict[str, str] = {}
    pinned: dict[str, str] = {}
    for path, expected in PINNED_BLOBS.items():
        candidate = root / path
        require(candidate.is_file() and not candidate.is_symlink() and
                candidate.resolve().is_relative_to(root),
                "missing/symlink frozen source: " + path)
        payload = candidate.read_bytes()
        actual = blob_sha(payload)
        require(actual == expected, "frozen Git blob drift: " + path)
        sources[path] = payload.decode("utf-8")
        pinned[path] = actual

    a = compact_c(sources["software/p08/p08_a2_board.c"])
    b = compact_c(sources["software/p08/p08_b45_perf_once_full1024_a53.c"])
    meter = compact_c(sources["software/p08/p08_b2_service_meter.c"])
    a_service = function(a, "execute_image")
    b_main = function(b, "main")
    meter_end = function(meter, "p08_b2_meter_finish")

    ordered(a_service, (
        "t.service_start=read_ticks(NULL);",
        "load_image_record(frame)",
        "t.after_ingress=read_ticks(NULL);",
        "p07_a2_run_frame(",
        "t.after_neural=read_ticks(NULL);",
        "commit_frame_result(frame,&res)",
        "t.after_commit=read_ticks(NULL);",
        "p08_write_record(&t)",
    ), "Track A image service")
    ordered(a_service, (
        "commit_frame_result(frame,&res)",
        "if(frame==dataset.trace_frame)flush_region(P07_A4_TRACE_BASE,65536u);",
        "t.after_commit=read_ticks(NULL);",
        "p08_write_record(&t)",
        "p08_header(0u,frame+1u,0u)",
    ), "Track A trace and timing sidecar")
    require("p08_clock_rate()" in a and
            "p08_counter_hz=p08_clock_rate();" in a and
            "p07_a4_run_images(dataset.frame_count,&ops" in a,
            "Track A counter frequency or frame driver drift")
    require("P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1" in a,
            "Track A original A2.1 source identity drift")

    ordered(b_main, (
        "p08_b45_perf_reset_bind(&reset_state,&reset_config,B45_MODE)",
        "for(index=0u;index<B23_FRAMES;index++)",
        "uint64_t now=observed_counter();",
        "p08_b2_meter_start(&meter,index,cntfrq,now)",
        "p08_b45_perf_reset_image(&reset_state,&reset_receipt)",
        "p08_b2_meter_mark(&meter,P08_B2_AFTER_STATE_RESTORE,",
        "p08_b2_encode_frame(",
        "p08_b2_meter_mark(&meter,P08_B2_AFTER_B13_INGRESS,",
        "prepare_new_scheduler()",
        "p08_b2_meter_mark(&meter,P08_B2_AFTER_SCHEDULER_REINIT,",
        "p07_b4m_full_run(",
        "p08_b2_meter_mark(&meter,P08_B2_AFTER_ALL_26_TICKS,",
        "p08_b2_meter_mark(&meter,P08_B2_AFTER_RECEIPT_VALIDATE,",
        "commit_journal(index,pixels,wire_bytes,&reset_receipt)",
        "p08_b2_meter_mark(&meter,P08_B2_AFTER_JOURNAL_COMMIT,",
        "p08_b2_meter_finish(&meter,&timing)",
        "commit_timing(index,&timing)",
        "commit_reset_profile(index,&reset_receipt,cntfrq,",
        "mailbox(UINT32_C(0xC0DE0000),index,0u,index+1u,cntfrq)",
    ), "Track B authenticate-once service")
    ordered(meter_end, (
        "candidate.service_entry_cntvct=m->cntvct[0];",
        "candidate.service_commit_cntvct=m->cntvct[6];",
        "candidate.total_service_cycles=m->cntvct[6]-m->cntvct[0];",
    ), "B software meter endpoints")
    require('P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V2' in b and
            "#defineB23_FRAMES1024u" in b and
            "#defineB23_DISPATCHES702u" in b and
            "#defineB23_SELECT_TRACE1023u" in b and
            "#defineB45_MODEP08_B45_AUTHENTICATED_ONCE" in b and
            "cntfrq=observed_frequency();" in b,
            "B V2 identity, mode, dataset, dispatch or clock drift")

    launcher_a = sources["scripts/run_p08_a3_2_1024.sh"]
    launcher_b = sources["scripts/p08_b45_perf_full1024_physical_run.py"]
    require("P08_A3_2_PREFLIGHT_ONLY" in launcher_a and
            "P08_A3_2_CONFIRM_DDR_OVERWRITE" in launcher_a and
            "0x40000000..0x43FFFFFF" in launcher_a and
            "PINNED_ELF_SHA=fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0" in launcher_a,
            "A original guarded DDR staging or A2.1 ELF gate drift")
    require("APPROVALS = (" in launcher_b and
            "TAKEOVER_TCL" in launcher_b and
            "six_original_ddr_transfers_overwrite_approved" in launcher_b and
            "reboot_and_recovery_approved" in launcher_b and
            "if args.mode == \"preflight\":" in launcher_b,
            "B original guarded run, independent recovery or preflight drift")

    result = {
        "schema": SCHEMA,
        "source_only_static_audit_pass": True,
        "frozen_git_blob_sha1": pinned,
        "arm_A": "A_ORIGINAL_A2_1_42_NEURONS_26_DISPATCHES",
        "arm_B": "B_AUTH_ONCE_UNPROTECTED_V2_1010_NEURONS_702_DISPATCHES",
        "A_start": "CNTVCT before load_image_record(frame) and P07 run_frame prepare/reset",
        "A_end": "CNTVCT after original compact neural journal flush; before P08 timing record/header",
        "B_start": "CNTVCT before per-image 27-context reset and ingress encode",
        "B_end": "CNTVCT after B neural journal commit; before B timing/reset sidecars and progress mailbox",
        "both_a53_cntvct_and_per_session_cntfrq": True,
        "both_broad_entry_to_neural_journal_commit_scope_present": True,
        "A_per_frame_p07_prepare_and_master_restore_inside_timer": True,
        "B_per_frame_mutable_context_reset_inside_timer": True,
        "B_one_time_SHA_bind_outside_timer": True,
        "A_timing_record_and_header_outside_timer": True,
        "B_timing_reset_profile_and_progress_mailbox_outside_timer": True,
        "selected_trace_ordinal_1023_to_exclude": 1023,
        "ordinary_expected_count_each": 1023,
        "A_B_same_neural_workload": False,
        "A_B_same_internal_phases_or_reset_algorithm": False,
        "A_B_physical_timer_boundary_equivalence_proven": False,
        "A_B_JTAG_DDR_staging_and_recovery_equivalence_proven": False,
        "A_B_compiled_ELFs_admitted_by_this_audit": False,
        "original_A2_1_ELF_recovered_by_this_audit": False,
        "B_original_immutable_backup_hardware_protected": False,
        "new_six_session_hardware_authorization_granted": False,
        "new_A_B_physical_sessions_performed": False,
        "new_physical_statistics_accepted": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "next_gate": "review timer-scope differences and per-arm DDR/JTAG ownership/recovery; "
                     "recover A2.1 ELF or separately validate reconstruction; "
                     "require new per-session authorization before any physical action",
    }
    return result


def audit(v3_root: Path, out: Path) -> dict:
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink(),
            "new absolute no-overwrite output required")
    target = out.resolve()
    root = v3_root.resolve()
    require(not target.is_relative_to(root) and
            not any(target.is_relative_to(d) for d in
                    (Path("/tmp"), Path("/var/tmp"))),
            "audit evidence must be durable outside checkout and temporary dirs")
    result = inspect_sources(v3_root)
    # Exclusive creation; failed source audits NEVER emit a success report.
    with out.open("x", encoding="utf-8") as fd:
        json.dump(result, fd, sort_keys=True, indent=2)
        fd.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v3-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(args.v3_root, args.out)
    except (BoundaryNoGo, OSError, TypeError, ValueError) as exc:
        print("P08_B46_AB_SERVICE_BOUNDARY_SOURCE_NO_GO=" + str(exc),
              file=sys.stderr)
        return 3
    print("P08_B46_AB_FROZEN_SERVICE_BOUNDARY_SOURCE_AUDIT_PASS=1")
    print("P08_B46_AB_PHYSICAL_BOUNDARY_EQUIVALENCE_PROVEN=0")
    print("P08_B46_AB_A21_ELF_SOURCE_ADMITTED=0")
    print("P08_B46_AB_NEW_HARDWARE_AUTHORIZED=0")
    print("P08_B46_AB_BOUNDARY_REPORT=" + str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
