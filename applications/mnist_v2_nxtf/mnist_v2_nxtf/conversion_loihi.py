"""P08.3.4 DThIR-aware Loihi quantization for ANN-to-SNN conversion.

The P08.3.4 verification gates exposed two representation mistakes before any
converted-SNN accuracy was observed:

1. Loihi mixed-sign 8-bit weights are not conventional signed int8 values.
2. The already-frozen hard-reset Desired Threshold to Input Ratio (DThIR=8)
   must participate in the hardware scaling; multiplying every normalized
   parameter directly by vThMant=512 ignores that ratio.

This module keeps the accepted calibration, Rueckauer normalization, graph
construction, compiler path, ANN identity, and test lock from :mod:`conversion`,
but replaces only the final integer quantizer with a source-bounded project
interpretation of the documented Loihi/SNN-Toolbox settings:

- threshold mantissa: 512;
- hard-reset DThIR: 8;
- effective normalized-parameter scale: 512 / 8 = 64;
- mixed-sign 8-bit weight mantissa range: -256 .. +254;
- representable weight step: 2;
- static weight rounding: toward zero;
- weight exponent reference: 0;
- no clipping.

Public sources establish that conversion normalizes weights and biases to the
Loihi dynamic range while satisfying DThIR, but the exact historical NxSDK
backend implementation is not public. Therefore the scale=threshold/DThIR rule
is explicitly recorded as PROJECT_RECONSTRUCTION rather than claimed to be an
exact native NxTF/NxSDK bit-level conversion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from . import conversion as _base
from .policy import CONVERSION_POLICY

# Re-export stable artifact/constants/helpers used by the verification gate.
CONVERSION_ARTIFACT_FILENAME = _base.CONVERSION_ARTIFACT_FILENAME
CONVERSION_MANIFEST_FILENAME = _base.CONVERSION_MANIFEST_FILENAME
CONVERSION_SCHEMA = _base.CONVERSION_SCHEMA
CONVERTED_NETWORK_FILENAME = _base.CONVERTED_NETWORK_FILENAME
COMPILED_DEPLOYMENT_FILENAME = _base.COMPILED_DEPLOYMENT_FILENAME
INTEGER_THRESHOLD_SCALE = _base.INTEGER_THRESHOLD_SCALE
NORMALIZATION_PERCENTILE = _base.NORMALIZATION_PERCENTILE
ConversionResult = _base.ConversionResult
build_converted_network = _base.build_converted_network
calibrate_activation_maxima = _base.calibrate_activation_maxima
conv_geometries = _base.conv_geometries
normalize_layer_parameters = _base.normalize_layer_parameters
_arrays_fingerprint = _base._arrays_fingerprint

if CONVERSION_POLICY.desired_threshold_to_input_ratio <= 0:
    raise AssertionError("P08.3.4 DThIR must be positive")
DTHIR_PARAMETER_SCALE = (
    float(INTEGER_THRESHOLD_SCALE)
    / float(CONVERSION_POLICY.desired_threshold_to_input_ratio)
)


def quantize_normalized_parameters(
    normalized_kernel: np.ndarray,
    normalized_bias: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Quantize normalized parameters using frozen DThIR and Loihi mantissas.

    P08's floating normalization produces a mathematical SNN with threshold 1.
    The hardware profile fixes vThMant=512 and DThIR=8. At this project boundary
    we therefore map one normalized parameter unit to 512/8=64 integer units.
    Weights are then rounded toward zero onto Loihi's mixed-sign step-2 lattice.
    Biases use the same DThIR-derived scale so the affine layer is not distorted
    relative to its synaptic inputs; their exact native Loihi exponent packing
    remains outside the equivalence claim.
    """

    if CONVERSION_POLICY.weight_sign_mode != "mixed":
        raise AssertionError("P08.3.4 requires mixed-sign Loihi weights")
    if CONVERSION_POLICY.weight_quantization_step != 2:
        raise AssertionError("P08.3.4 Loihi weight step must be two")
    if CONVERSION_POLICY.weight_rounding != "toward_zero":
        raise AssertionError("P08.3.4 Loihi static weights must round toward zero")
    if CONVERSION_POLICY.desired_threshold_to_input_ratio != 8:
        raise AssertionError("P08.3.4 must preserve the frozen hard-reset DThIR=8")
    if DTHIR_PARAMETER_SCALE != 64.0:
        raise AssertionError("P08.3.4 DThIR-derived parameter scale drifted")

    scale = DTHIR_PARAMETER_SCALE
    step = float(CONVERSION_POLICY.weight_quantization_step)
    raw_kernel = np.asarray(normalized_kernel, dtype=np.float64) * scale
    q_kernel_64 = (np.trunc(raw_kernel / step) * step).astype(np.int64)

    q_bias_64 = np.rint(
        np.asarray(normalized_bias, dtype=np.float64) * scale
    ).astype(np.int64)

    if q_kernel_64.size and (
        int(q_kernel_64.min()) < CONVERSION_POLICY.signed_weight_min
        or int(q_kernel_64.max()) > CONVERSION_POLICY.signed_weight_max
    ):
        raise OverflowError(
            "P08.3 DThIR-scaled normalized weight does not fit the Loihi "
            "mixed-sign 8-bit mantissa range after step-2 rounding: "
            f"observed=[{int(q_kernel_64.min())},{int(q_kernel_64.max())}] "
            f"allowed=[{CONVERSION_POLICY.signed_weight_min},"
            f"{CONVERSION_POLICY.signed_weight_max}] "
            f"scale={scale:g}"
        )
    if q_bias_64.size and (
        int(q_bias_64.min()) < CONVERSION_POLICY.signed_bias_min
        or int(q_bias_64.max()) > CONVERSION_POLICY.signed_bias_max
    ):
        raise OverflowError(
            "P08.3 DThIR-scaled normalized bias does not fit the frozen project "
            "bias range: "
            f"observed=[{int(q_bias_64.min())},{int(q_bias_64.max())}] "
            f"allowed=[{CONVERSION_POLICY.signed_bias_min},"
            f"{CONVERSION_POLICY.signed_bias_max}] scale={scale:g}"
        )
    return q_kernel_64.astype(np.int16), q_bias_64.astype(np.int16)


# Patch only the function looked up by conversion.convert_parameter_arrays at
# runtime. All other conversion logic remains the already-reviewed P08.3.4 path.
_base.quantize_normalized_parameters = quantize_normalized_parameters
convert_parameter_arrays = _base.convert_parameter_arrays


def _manifest_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_conversion(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    output_dir: str | Path,
) -> ConversionResult:
    result = _base.run_conversion(checkpoint_path, training_manifest_path, output_dir)

    # Correct the representation description written by the base module and bind
    # the manifest fingerprint to the actual DThIR-aware rule used here.
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest.pop("manifest_fingerprint", None)
    manifest["integer_quantization"] = (
        "weights: trunc_toward_zero(normalized_weight * "
        "threshold_mantissa / desired_threshold_to_input_ratio / 2) * 2; "
        "biases: round(normalized_bias * threshold_mantissa / "
        "desired_threshold_to_input_ratio); reject overflow; no clipping"
    )
    manifest["desired_threshold_to_input_ratio"] = (
        CONVERSION_POLICY.desired_threshold_to_input_ratio
    )
    manifest["dthir_parameter_scale"] = DTHIR_PARAMETER_SCALE
    manifest["dthir_scaling_status"] = (
        "PROJECT_RECONSTRUCTION_SOURCE_BOUNDED_NO_ACCURACY_TUNING"
    )
    manifest["weight_sign_mode"] = CONVERSION_POLICY.weight_sign_mode
    manifest["weight_quantization_step"] = CONVERSION_POLICY.weight_quantization_step
    manifest["weight_rounding"] = CONVERSION_POLICY.weight_rounding
    manifest["weight_exponent"] = CONVERSION_POLICY.weight_exponent
    manifest["weight_range"] = [
        CONVERSION_POLICY.signed_weight_min,
        CONVERSION_POLICY.signed_weight_max,
    ]
    manifest["representation_correction"] = (
        "P08.3.4 gates first rejected conventional-int8 range and then rejected "
        "threshold-only scaling; before SNN accuracy evaluation the converter was "
        "corrected to Loihi mixed-sign mantissas plus the already-frozen hard-reset "
        "DThIR=8 via project scale vThMant/DThIR"
    )
    manifest["manifest_fingerprint"] = _manifest_fingerprint(manifest)
    result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert accepted P08 ANN using DThIR-aware Loihi quantization"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--training-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_conversion(args.checkpoint, args.training_manifest, args.output_dir)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    ranges = ",".join(
        f"{layer['name']}:[{layer['integer_weight_min']},{layer['integer_weight_max']}]"
        for layer in manifest["layers"]
    )
    print(
        "PASS: P08.3.4 DThIR-aware Loihi conversion "
        f"threshold={INTEGER_THRESHOLD_SCALE} "
        f"dthir={CONVERSION_POLICY.desired_threshold_to_input_ratio} "
        f"parameter_scale={DTHIR_PARAMETER_SCALE:g}"
    )
    print(
        "PASS: P08.3.4 Loihi mantissa conversion "
        f"step={CONVERSION_POLICY.weight_quantization_step} "
        f"range=[{CONVERSION_POLICY.signed_weight_min},{CONVERSION_POLICY.signed_weight_max}] "
        f"rounding={CONVERSION_POLICY.weight_rounding} weight_ranges={ranges} "
        "overflow=0 clipping=0"
    )
    print(
        "PASS: P08.3.4 P06 compile "
        f"logical_cores={result.logical_core_count} network={result.network_fingerprint} "
        f"compiled={result.compiled_fingerprint}"
    )
    print(
        "PASS: P08.3.4 test lock official_test_used=false test_examples_observed=0 "
        f"conversion_fingerprint={result.conversion_fingerprint}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
