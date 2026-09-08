from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Neuromorphic Digital Twin"
manifest_path = PROJECT / "references" / "m13_1_reference_manifest.json"
module_path = PROJECT / "src" / "neuromorphic_twin" / "m13_reference_manifest.py"
test_path = PROJECT / "tests" / "test_m13_1_reference_manifest.py"
doc_path = PROJECT / "docs" / "M13_1_REFERENCE_BASELINE.md"

# Correct and strengthen the machine-readable provenance record.
data = json.loads(manifest_path.read_text(encoding="utf-8"))
catalyst = data["catalyst_n1"]
catalyst["pin_kind"] = "lightweight Git tags resolved directly to commit"
catalyst["latest_master_observed_at_freeze"] = "47f3fa3cc3c596724d91498a5085225fcba12a49"
catalyst["paper"]["title"] = "Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with Programmable Synaptic Plasticity"
catalyst["paper"]["identity_rule"] = (
    "The DOI/Zenodo record is the stable publication identity. Catalyst-controlled secondary sources observed "
    "on 2026-09-08 use more than one title string for this DOI, so title text is descriptive rather than the pin."
)
data["m13_1_validated_environment"] = {
    "validation_date": "2026-09-08",
    "os": "Ubuntu 24.04.4 LTS (GitHub-hosted ubuntu-24.04 runner)",
    "python": "3.11.16",
    "iverilog": "12.0 (Ubuntu package 12.0-2build2)",
    "project_environment": {
        "pytest": "9.1.1",
        "numpy": "2.4.6",
        "brian2": "2.9.0",
        "brian2_loihi": "0.5.2",
        "result": "complete thesis regression suite passed"
    },
    "catalyst_rtl": {
        "result": "25/25 native run_regression.sh testbenches passed",
        "normalization": "working-directory relocation only; Catalyst source checkout remained clean"
    },
    "catalyst_cpu": {
        "pytest": "9.1.1",
        "neurocore": "1.0.0",
        "numpy": "2.4.6",
        "matplotlib": "3.11.1",
        "pyserial": "3.5",
        "result": "56/56 sdk/tests/test_simulator.py tests passed"
    },
    "note": "These are the exact M13.1 closure-validation versions, kept separate from source-declared minimum requirements."
}
manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

# Make tag kind and exact validation environment normative in the validator.
module = module_path.read_text(encoding="utf-8")
module = module.replace(
    '    if catalyst.get("primary_tag") != M13_CATALYST_TAG:\n        raise ValueError("Catalyst N1 primary tag differs from the frozen M13.1 pin")\n',
    '    if catalyst.get("primary_tag") != M13_CATALYST_TAG:\n        raise ValueError("Catalyst N1 primary tag differs from the frozen M13.1 pin")\n'
    '    if catalyst.get("pin_kind") != "lightweight Git tags resolved directly to commit":\n'
    '        raise ValueError("Catalyst N1 tag-kind provenance changed")\n'
)
module = module.replace(
    '    required_tags = {catalyst["primary_tag"], catalyst["equivalent_tag"]}\n'
    '    if not required_tags.issubset(tags):\n'
    '        raise ValueError(f"Catalyst checkout is missing frozen tags at HEAD: required={sorted(required_tags)} actual={tags}")\n',
    '    required_tags = {catalyst["primary_tag"], catalyst["equivalent_tag"]}\n'
    '    if not required_tags.issubset(tags):\n'
    '        raise ValueError(f"Catalyst checkout is missing frozen tags at HEAD: required={sorted(required_tags)} actual={tags}")\n'
    '    for tag in sorted(required_tags):\n'
    '        if _git(root, "cat-file", "-t", tag) != "commit":\n'
    '            raise ValueError(f"Catalyst frozen tag is no longer lightweight/direct-to-commit: {tag}")\n'
)
module = module.replace(
    '    change = _mapping(data, "change_control")\n',
    '    env = _mapping(data, "m13_1_validated_environment")\n'
    '    if env.get("python") != "3.11.16" or not str(env.get("iverilog", "")).startswith("12.0"):\n'
    '        raise ValueError("M13.1 exact closure-validation environment changed")\n'
    '    if _mapping(env, "catalyst_rtl").get("result") != "25/25 native run_regression.sh testbenches passed":\n'
    '        raise ValueError("M13.1 Catalyst RTL validation result changed")\n'
    '    if _mapping(env, "catalyst_cpu").get("result") != "56/56 sdk/tests/test_simulator.py tests passed":\n'
    '        raise ValueError("M13.1 Catalyst CPU validation result changed")\n\n'
    '    change = _mapping(data, "change_control")\n'
)
module_path.write_text(module, encoding="utf-8")

# Lock the provenance correction and closure environment in focused tests.
test = test_path.read_text(encoding="utf-8")
needle = '    assert catalyst["license"] == "Apache-2.0"\n'
test = test.replace(
    needle,
    needle
    + '    assert catalyst["pin_kind"] == "lightweight Git tags resolved directly to commit"\n'
    + '    assert catalyst["latest_master_observed_at_freeze"] == "47f3fa3cc3c596724d91498a5085225fcba12a49"\n',
    1,
)
insert = '''\n\ndef test_m13_1_exact_closure_environment_is_recorded_separately_from_minimums() -> None:\n    data = load_reference_manifest()\n    env = data["m13_1_validated_environment"]\n    assert env["python"] == "3.11.16"\n    assert env["iverilog"].startswith("12.0")\n    assert env["project_environment"]["brian2_loihi"] == "0.5.2"\n    assert env["catalyst_rtl"]["result"].startswith("25/25")\n    assert env["catalyst_cpu"]["result"].startswith("56/56")\n    assert data["catalyst_n1"]["native_simulation"]["tool_requirement"] == ">=12"\n    assert data["catalyst_n1"]["sdk_reference"]["python_requirement"] == ">=3.9"\n'''
if "test_m13_1_exact_closure_environment_is_recorded_separately_from_minimums" not in test:
    test += insert

test_path.write_text(test, encoding="utf-8")

# Correct the human-readable provenance and append exact direct-observation evidence.
doc = doc_path.read_text(encoding="utf-8")
doc = doc.replace(
    "Both `v2.3-paper` and `n1-final` resolve to the same commit. No GitHub Release object exists for the repository, so the tag+commit pair is the stable software pin.",
    "Both `v2.3-paper` and `n1-final` are lightweight Git tags whose refs resolve directly to the same commit. No GitHub Release object exists for the repository, so the tag+commit pair is the stable software pin. M13.1 verifies both tag object types as `commit`, not annotated tag objects."
)
doc = doc.replace(
    "Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with\nProgrammable Synaptic Plasticity and FPGA Validation",
    "Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with\nProgrammable Synaptic Plasticity"
)
anchor = "## M13.1 pass boundary\n"
block = '''## M13.1 validated execution environment\n\nThe source-declared minimum requirements above are deliberately distinct from the exact environment used for the successful M13.1 closure gate. The accepted direct-observation environment on 2026-09-08 was:\n\n```text\nUbuntu:              24.04.4 LTS (GitHub-hosted ubuntu-24.04 runner)\nPython:              3.11.16\nIcarus Verilog:      12.0 (Ubuntu package 12.0-2build2)\npytest:              9.1.1\nproject numpy:       2.4.6\nproject Brian2:      2.9.0\nproject Brian2Loihi: 0.5.2\nCatalyst neurocore:  1.0.0\nCatalyst matplotlib: 3.11.1\nCatalyst pyserial:   3.5\n```\n\nThe complete thesis regression suite passed in this environment. The pinned Catalyst checkout then passed exact commit/tag/blob verification while clean, all **25/25** testbenches enumerated by its native `run_regression.sh`, and all **56/56** tests in `sdk/tests/test_simulator.py`. These results establish that the external reference boundaries selected by M13.1 are independently runnable; they do not establish that Catalyst behavior is Loihi ground truth.\n\nTwo development-only Class-H issues were found and corrected before closure: an older M12.5 documentation test expected the exact already-intended power-exclusion wording, and the first M13.1 RTL harness falsely interpreted Catalyst's `0 FAILED` summary text as a failure. Neither issue changed project computation or Catalyst source.\n\nThe DOI `10.5281/zenodo.18727094` remains the stable Catalyst N1 publication identity. Catalyst-controlled secondary sources observed during M13.1 use more than one title string for that DOI, so M13 records the DOI as normative and treats publication-title text as descriptive metadata.\n\n'''
if "## M13.1 validated execution environment" not in doc:
    doc = doc.replace(anchor, block + anchor, 1)
doc_path.write_text(doc, encoding="utf-8")
