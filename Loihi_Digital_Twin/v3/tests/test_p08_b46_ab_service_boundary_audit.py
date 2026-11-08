"""B4.6.3 PC-only native negative tests; NO board, ELF, data or JTAG."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b46_ab_service_boundary_audit as gate


@pytest.fixture
def copy_frozen(tmp_path):
    root = tmp_path / "v3"
    root.mkdir()
    (root / "LOIHI_TWIN_ROADMAP.md").write_text("# test-only v3 marker\n")
    for rel in gate.PINNED_BLOBS:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    return root


def test_original_five_frozen_source_snapshots_admitted():
    data = gate.inspect_sources(ROOT)
    assert data["schema"] == gate.SCHEMA
    assert data["source_only_static_audit_pass"] is True
    assert data["rebuilt_A21_new_accepted_ELF_SHA256"] == "fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793"
    assert data["prior_A21_rebuilt_one_1024_physical_run_operator_attested"] is True
    assert data["prior_A21_standalone_run_is_one_of_six_future_counterbalanced_sessions"] is False
    assert data["frozen_git_blob_sha1"] == gate.PINNED_BLOBS
    assert data["both_broad_entry_to_neural_journal_commit_scope_present"] is True
    assert data["A_B_physical_timer_boundary_equivalence_proven"] is False
    assert data["new_six_session_hardware_authorization_granted"] is False
    assert data["official_MNIST_TEST"] == "SEALED_NOT_ACCESSED"


@pytest.mark.parametrize("rel", list(gate.PINNED_BLOBS))
def test_each_frozen_firmware_meter_and_launcher_is_byte_pinned(copy_frozen, rel):
    file = copy_frozen / rel
    file.write_bytes(file.read_bytes() + b"\n// unauthorized local source drift\n")
    with pytest.raises(gate.BoundaryNoGo, match="frozen Git blob drift"):
        gate.inspect_sources(copy_frozen)


def test_a_end_point_reordering_caught_even_if_revised_blob_is_re_pinned(
        copy_frozen, monkeypatch):
    rel = "software/p08/p08_a2_board.c"
    file = copy_frozen / rel
    text = file.read_text()
    assert "t.after_commit=read_ticks(NULL);" in text
    file.write_text(text.replace("t.after_commit=read_ticks(NULL);",
                                 "t.after_commit=0u;", 1))
    pins = dict(gate.PINNED_BLOBS)
    pins[rel] = gate.blob_sha(file.read_bytes())
    monkeypatch.setattr(gate, "PINNED_BLOBS", pins)
    with pytest.raises(gate.BoundaryNoGo, match="Track A .*missing/reordered"):
        gate.inspect_sources(copy_frozen)


def test_b_service_meter_end_point_change_caught_even_if_re_pinned(
        copy_frozen, monkeypatch):
    rel = "software/p08/p08_b2_service_meter.c"
    file = copy_frozen / rel
    text = file.read_text()
    assert "candidate.service_commit_cntvct=m->cntvct[6];" in text
    file.write_text(text.replace("candidate.service_commit_cntvct=m->cntvct[6];",
                                 "candidate.service_commit_cntvct=m->cntvct[5];"))
    pins = dict(gate.PINNED_BLOBS)
    pins[rel] = gate.blob_sha(file.read_bytes())
    monkeypatch.setattr(gate, "PINNED_BLOBS", pins)
    with pytest.raises(gate.BoundaryNoGo, match="B software meter endpoints"):
        gate.inspect_sources(copy_frozen)


def test_b_unauthenticated_mode_cannot_be_relabeled_once(copy_frozen, monkeypatch):
    rel = "software/p08/p08_b45_perf_once_full1024_a53.c"
    file = copy_frozen / rel
    file.write_text(file.read_text().replace(
        "#define B45_MODE P08_B45_AUTHENTICATED_ONCE",
        "#define B45_MODE P08_B45_UNCHECKED_CONTENT"))
    pins = dict(gate.PINNED_BLOBS)
    pins[rel] = gate.blob_sha(file.read_bytes())
    monkeypatch.setattr(gate, "PINNED_BLOBS", pins)
    with pytest.raises(gate.BoundaryNoGo, match="B V2 identity, mode"):
        gate.inspect_sources(copy_frozen)


def test_rebuilt_A21_risk_and_new_ELF_gate_cannot_silently_change(copy_frozen, monkeypatch):
    rel = "scripts/run_p08_b46_rebuilt_a21_1024.sh"
    file = copy_frozen / rel
    before = file.read_text()
    assert "P08_B46_CONFIRM_PWR_CYCLE_AFTER_ANY_ATTEMPT" in before
    file.write_text(before.replace("P08_B46_CONFIRM_PWR_CYCLE_AFTER_ANY_ATTEMPT",
                                   "UNSAFE_REPLACEMENT", 1))
    pins = dict(gate.PINNED_BLOBS)
    pins[rel] = gate.blob_sha(file.read_bytes())
    monkeypatch.setattr(gate, "PINNED_BLOBS", pins)
    with pytest.raises(gate.BoundaryNoGo, match="rebuilt A2.1 accepted candidate"):
        gate.inspect_sources(copy_frozen)


def test_symlink_in_original_sources_rejected(copy_frozen, tmp_path):
    rel = "software/p08/p08_a2_board.c"
    original = copy_frozen / rel
    spare = tmp_path / "spare"
    shutil.copyfile(original, spare)
    original.unlink()
    original.symlink_to(spare)
    with pytest.raises(gate.BoundaryNoGo, match="missing/symlink frozen source"):
        gate.inspect_sources(copy_frozen)


def test_tmp_and_existing_evidence_paths_are_no_go(copy_frozen, tmp_path):
    with pytest.raises(gate.BoundaryNoGo, match="durable"):
        gate.audit(copy_frozen, tmp_path / "report.json")
    assert not (tmp_path / "report.json").exists()
    with TemporaryDirectory(dir=Path.home(), prefix="b46_test_synthetic_") as folder:
        out = Path(folder) / "report.json"
        out.write_text("PRESERVED")
        with pytest.raises(gate.BoundaryNoGo, match="no-overwrite"):
            gate.audit(copy_frozen, out)
        assert out.read_text() == "PRESERVED"


def test_no_overwrite_and_clearly_false_physical_status(copy_frozen):
    # TemporaryDirectory is for disposable SYNTHETIC test output only.
    # Real user evidence is never authored by tests and must be durable.
    with TemporaryDirectory(dir=Path.home(), prefix="b46_test_synthetic_") as folder:
        out = Path(folder) / "one.json"
        report = gate.audit(copy_frozen, out)
        assert json.loads(out.read_text()) == report
        assert report["B_one_time_SHA_bind_outside_timer"] is True
        assert report["B_original_immutable_backup_hardware_protected"] is False
        assert report["A_B_compiled_ELFs_admitted_by_this_audit"] is False
        assert report["A_B_physical_timer_boundary_equivalence_proven"] is False
        with pytest.raises(gate.BoundaryNoGo, match="no-overwrite"):
            gate.audit(copy_frozen, out)


def test_source_audit_contains_no_board_operation_entry_points():
    text = (ROOT / "scripts" / "p08_b46_ab_service_boundary_audit.py").read_text()
    for forbidden in ("import subprocess", "subprocess.run(", "os.system(",
                      "socket.connect(", "xsdb ", "vivado -mode",
                      "P08_A3_2_CONFIRM_DDR_OVERWRITE=YES"):
        assert forbidden not in text
    assert "new_six_session_hardware_authorization_granted" in text
