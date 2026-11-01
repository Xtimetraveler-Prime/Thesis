"""B6.1 read-only Git LitReview.md blob-preservation check; no main mutation."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b6_literature_merge_guard as lit

def fake_git(monkeypatch,output,status=0):
    def run(args,**kwargs):
        assert args[0]=="git"
        assert args[1]=="-C"
        assert args[-3]=="origin/main" or args[-3]=="main"
        assert args[-2]=="--" and args[-1]=="LitReview.md"
        assert kwargs.get("capture_output") is True and kwargs.get("check") is False
        return subprocess.CompletedProcess(args,status,stdout=output,stderr="")
    monkeypatch.setattr(lit.subprocess,"run",run)

def test_exact_origin_main_Git_blob_identity_read_only(tmp_path,monkeypatch):
    fake_git(monkeypatch,f"100644 blob {lit.EXPECTED_BLOB_SHA}\tLitReview.md\n")
    report=lit.verify_literature(tmp_path,"origin/main")
    assert report["main_literature_content_bytewise_preservation_verified"] is True
    assert report["github_main_branch_merged_by_this_tool"] is False
    assert report["original_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    assert report["board_contact"] is False

@pytest.mark.parametrize("line",[
    "",
    "100644 blob "+("a"*40)+"\tLitReview.md\n",
    "120000 blob 3c45d0a0d0b55378d3564d8f82282803a8eb1a3e\tLitReview.md\n",
    "100644 blob 3c45d0a0d0b55378d3564d8f82282803a8eb1a3e\tUnexpected.md\n",
    "100644 blob 3c45d0a0d0b55378d3564d8f82282803a8eb1a3e\tLitReview.md\n100644 blob deadbeef\tOTHER\n"
])
def test_reject_main_literature_absent_mutated_symlink_or_double_line(tmp_path,monkeypatch,line):
    fake_git(monkeypatch,line)
    with pytest.raises(lit.LiteratureNoGo):
        lit.verify_literature(tmp_path,"origin/main")

def test_ref_must_be_exact_local_main_or_origin_main(tmp_path):
    with pytest.raises(lit.LiteratureNoGo,match="only exact"):
        lit.verify_literature(tmp_path,"refs/heads/evil")
    with pytest.raises(lit.LiteratureNoGo,match="only exact"):
        lit.verify_literature(tmp_path,"HEAD")

def test_no_git_mutation_network_or_merge_calls():
    source=(ROOT/"scripts/p07_b6_literature_merge_guard.py").read_text()
    assert "ls-tree" in source
    assert "EXPECTED_BLOB_SHA" in source
    for forbidden in ("git push","git merge","git reset","git checkout",
                      "git pull","git fetch","git commit","subprocess.Popen",
                      "program_hw_devices","xsdb"):
        assert forbidden not in source
