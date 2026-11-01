#!/usr/bin/env python3
"""Read-only P07-B6 merge preservation guard for main-only LitReview.md.

The user independently committed LitReview.md directly to main while
stacked draft P07-B PRs were under development. Never force-push,
reset, overwrite main or substitute the old draft branch's tree.
This program checks the exact Git *blob* identity on the user's
fetched origin/main (pre-merge) or local main (after merge).
No network operation, no pull request merge, no file mutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

import p07_b5_scaled_validation as b5

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
EXPECTED_BLOB_SHA="3c45d0a0d0b55378d3564d8f82282803a8eb1a3e"
EXPECTED_FILE="LitReview.md"
RECORD_SCHEMA="p07-b6-main-only-literature-git-blob-preservation-v1"
ALLOW_REFS=("origin/main","main")

class LiteratureNoGo(ValueError):
    pass

def require(ok:bool,why:str)->None:
    if not ok: raise LiteratureNoGo("NO-GO: "+why)

def verify_literature(repo:Path,ref:str)->dict:
    require(ref in ALLOW_REFS,"only exact origin/main or local main may be inspected")
    require(repo.is_dir() and not repo.is_symlink(),
            "real existing Git repository required")
    proc=subprocess.run(["git","-C",str(repo),"ls-tree",ref,"--",EXPECTED_FILE],
                        capture_output=True,text=True,timeout=30,check=False)
    require(proc.returncode==0,"cannot read "+ref+" Git tree: "+proc.stderr.strip())
    line=proc.stdout.strip()
    match=re.fullmatch(
        r"100644 blob ([0-9a-f]{40})\tLitReview[.]md",line
    )
    require(match is not None,
            "main literature file missing, renamed, symlinked, or not regular Git blob")
    require(match.group(1)==EXPECTED_BLOB_SHA,
            "main LitReview.md content differs from original main-only commit")
    return {
        "schema":RECORD_SCHEMA,
        "git_ref_examined":ref,
        "lit_review_path":EXPECTED_FILE,
        "original_independent_main_blob_sha":EXPECTED_BLOB_SHA,
        "checked_main_tree_literature_blob_sha":match.group(1),
        "main_literature_content_bytewise_preservation_verified":True,
        "github_main_branch_merged_by_this_tool":False,
        "original_B2_4_27core_model_changed":False,
        "original_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact":False,
    }

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,default=REPO)
    parser.add_argument("--ref",choices=ALLOW_REFS,default="origin/main")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    try:
        b5.require_external_report(args.out)
        result=verify_literature(args.repo,args.ref)
        b5.write_report(args.out,result)
        print("P07_B6_MAIN_LITREVIEW_ORIGINAL_BLOB_IDENTICAL_PASS=1")
        print("P07_B6_GIT_MERGED_BY_THIS_TOOL=0")
        print("P07_B6_BOARD_CONTACT=0")
        print("P07_B6_MAIN_LITERATURE_AUDIT="+str(args.out))
        return 0
    except (ValueError,KeyError,TypeError,OSError,
            subprocess.TimeoutExpired) as error:
        print("P07_B6_LITERATURE_BLOB_NO_GO="+str(error),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
