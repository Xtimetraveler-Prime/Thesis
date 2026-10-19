"""P06-B2.1 opt-in width-parametric 784→H→10 trainable integer-forward model.

Track A's frozen 32-neuron training model, checkpoints, numerical recurrence,
training/validation IDX reader and official-test protocol remain UNMODIFIED.
This new model calls their accepted strict-spike/STE integer step kernel but
makes *every* hidden dimension explicit and exports all signed integer edges
through the B1.2 source graph compiler contract.

B2.1 is a training FOUNDATION, not a trained/checkpointed model or test accuracy.
Only canonical 60k TRAIN archive + its 50k/10k train-derived split is admissible
for a future B2.2 actual fit; the official 10k TEST archive is never accessed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct

import torch
from torch import nn

from .compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec, PopulationSpec,
    ProjectionConnection, ProjectionSpec,
)
from .p06_a3_data import SPLIT_SCHEMA, TRAIN_FILES, TrainingSplit
from .p06_a3_training import (
    HIDDEN_LIF, OUTPUT_LIF, LOGIT_SCALE, WEIGHT_CLAMP,
)
from .p06_input_contract import (
    ENCODER_PROFILE, READOUT_PROFILE, INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS,
    OUTPUT_CLASSES,
)
from .p06_integer_oracle import LIFParameters, STATE_MIN, STATE_MAX
from .p06_train_export import _convert_params
from .p06_train_forward import (
    _integer_step, _ste_round_half_away, _ste_saturate24,
)

B21_SCHEMA = "p06-b2.1-scaled-integer-forward-contract-v1"
B21_MAX_HIDDEN_NEURONS = 1000
B21_DEFAULT_HIDDEN_NEURONS = 1000
B21_SOURCE_INPUT = "pixels"
B21_HIDDEN_NAME = "hidden"
B21_READOUT_NAME = "readout"


@dataclass(frozen=True, slots=True)
class B21Settings:
    hidden_neurons: int = B21_DEFAULT_HIDDEN_NEURONS
    seed: int = 20261019
    epochs: int = 8
    batch_size: int = 64
    learning_rate: float = 0.05
    surrogate_width: float = 16.0
    validation_go_floor: float = 0.60

    def __post_init__(self) -> None:
        if type(self.hidden_neurons) is not int or not 1 <= self.hidden_neurons <= B21_MAX_HIDDEN_NEURONS:
            raise ValueError("hidden_neurons must be integer 1..1000")
        if type(self.seed) is not int or type(self.epochs) is not int or self.epochs < 1:
            raise ValueError("B2 seed must be integer and epochs positive")
        if type(self.batch_size) is not int or self.batch_size < 1:
            raise ValueError("batch size must be positive")
        for name in ("learning_rate", "surrogate_width", "validation_go_floor"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if not (0 < value <= 1 if name == "validation_go_floor" else value > 0):
                raise ValueError(f"{name} outside predeclared admissible range")


def require_train_only_split(split: TrainingSplit) -> dict:
    """Future-fit B2.2 admission: no synthetic IDX or official TEST partition.

    Reuses accepted Track A original 60k TRAIN-only checksum/split parser,
    without asking that frozen loader to download/open any file here.
    """
    if not isinstance(split, TrainingSplit):
        raise TypeError("B2.1 requires a validated TrainingSplit object")
    manifest = split.manifest
    if manifest.get("schema") != SPLIT_SCHEMA:
        raise ValueError("B2 requires original canonical MNIST TRAIN-only schema")
    if (manifest.get("image_count") != 60000
            or manifest.get("train_count") != 50000
            or manifest.get("validation_count") != 10000
            or manifest.get("split_seed") != 20261013):
        raise ValueError("B2 split changed relative to accepted Track A TRAIN/validation policy")
    if (manifest.get("official_test_set") != "sealed: no t10k archives opened"
            or len(split.images) != 60000 * INPUT_CHANNELS
            or len(split.labels) != 60000):
        raise ValueError("B2 source or official-test seal violation")
    if (len(split.train_indices) != 50000 or len(split.validation_indices) != 10000
            or len(set(split.train_indices)) != 50000
            or len(set(split.validation_indices)) != 10000
            or set(split.train_indices) & set(split.validation_indices)):
        raise ValueError("B2 train/validation partition overlap or missing IDs")
    for _kind, (filename, expected_md5) in TRAIN_FILES.items():
        stored = manifest.get("archives", {}).get(_kind, {})
        if stored.get("filename") != filename or stored.get("source_md5") != expected_md5:
            raise ValueError("B2 requires accepted canonical TRAIN archive checksum metadata")
    # Trust signature-bearing manifest only after the *existing* source
    # reader has verified compressed MD5/IDX SHA. This function is a second
    # admission check, NOT a substitute for load_train_validation(strict=True).
    return manifest


class B21IntegerSNN(nn.Module):
    """PyTorch integer-valued forward identical to Track A recurrence.

    Differentiation uses the frozen surrogate gradient; forward uses float64
    to keep exact integral weighted sums and its existing saturate/STE kernel.
    Scaling changes tensor shape ONLY, not 25+1 phase encoding or LIF math.
    """

    def __init__(self, hidden_neurons: int, *,
                 hidden: LIFParameters = HIDDEN_LIF,
                 readout: LIFParameters = OUTPUT_LIF,
                 surrogate_width: float = 16.0):
        super().__init__()
        B21Settings(hidden_neurons=hidden_neurons, surrogate_width=surrogate_width)
        if not isinstance(hidden, LIFParameters) or not isinstance(readout, LIFParameters):
            raise TypeError("B2.1 LIF params must be independent oracle LIFParameters")
        self.hidden_neurons = hidden_neurons
        self.hidden_config, self.output_config = hidden, readout
        self.surrogate_width = float(surrogate_width)
        self.w_input_hidden = nn.Parameter(
            torch.zeros(hidden_neurons, INPUT_CHANNELS, dtype=torch.float32))
        self.w_hidden_output = nn.Parameter(
            torch.zeros(OUTPUT_CLASSES, hidden_neurons, dtype=torch.float32))
        self.register_buffer(
            "phase_offsets",
            (17 * torch.arange(INPUT_CHANNELS, dtype=torch.int64)) % INPUT_TICKS,
        )

    @classmethod
    def initialized(cls, settings: B21Settings) -> "B21IntegerSNN":
        if not isinstance(settings, B21Settings):
            raise TypeError("B21Settings required")
        model = cls(settings.hidden_neurons, surrogate_width=settings.surrogate_width)
        rng = torch.Generator(device="cpu").manual_seed(settings.seed)
        with torch.no_grad():
            model.w_input_hidden.uniform_(-6, 6, generator=rng)
            model.w_hidden_output.uniform_(-4, 4, generator=rng)
        return model

    def _effective(self) -> tuple[torch.Tensor, torch.Tensor]:
        return (
            _ste_saturate24(_ste_round_half_away(self.w_input_hidden.to(torch.float64))),
            _ste_saturate24(_ste_round_half_away(self.w_hidden_output.to(torch.float64))),
        )

    def forward(self, pixels: torch.Tensor) -> torch.Tensor:
        if not isinstance(pixels, torch.Tensor) or pixels.ndim != 2 or pixels.shape[1] != INPUT_CHANNELS:
            raise ValueError("B2 expects [batch,784] raw uint8 images")
        if pixels.dtype != torch.uint8:
            raise TypeError("B2 raw pixels must be uint8, never analog normalized")
        if pixels.device != self.w_input_hidden.device:
            raise ValueError("B2 pixels and weights must share device")
        if pixels.shape[0] <= 0:
            raise ValueError("B2 batch must not be empty")
        raw = pixels.to(torch.int64)
        wih, who = self._effective()
        batch = pixels.shape[0]
        hc = torch.zeros((batch, self.hidden_neurons), dtype=torch.float64, device=pixels.device)
        hv = torch.zeros_like(hc)
        hr = torch.zeros((batch, self.hidden_neurons), dtype=torch.int64, device=pixels.device)
        oc = torch.zeros((batch, OUTPUT_CLASSES), dtype=torch.float64, device=pixels.device)
        ov = torch.zeros_like(oc)
        orefr = torch.zeros((batch, OUTPUT_CLASSES), dtype=torch.int64, device=pixels.device)
        previous = torch.zeros_like(hc)
        counts = torch.zeros_like(oc)
        for tick in range(TOTAL_TICKS):
            if tick < INPUT_TICKS:
                phase = (self.phase_offsets + tick) % INPUT_TICKS
                spikes = ((phase + 1) * raw // 255 > phase * raw // 255).to(torch.float64)
                ih_in = spikes @ wih.T
            else:
                ih_in = torch.zeros_like(hc)
            ho_in = previous @ who.T  # NEXT-epoch readout.
            hc, hv, hr, hidden_spikes = _integer_step(
                hc, hv, hr, ih_in, self.hidden_config, self.surrogate_width)
            oc, ov, orefr, readout_spikes = _integer_step(
                oc, ov, orefr, ho_in, self.output_config, self.surrogate_width)
            counts = counts + readout_spikes
            previous = hidden_spikes
        return counts

    @torch.no_grad()
    def effective_signed_weights(self) -> tuple[torch.Tensor, torch.Tensor]:
        if not torch.isfinite(self.w_input_hidden).all() or not torch.isfinite(self.w_hidden_output).all():
            raise ValueError("B2 model contains nonfinite trainable weights")
        rounded = tuple(
            torch.sign(w.to(torch.float64)) * torch.floor(torch.abs(w.to(torch.float64)) + 0.5)
            for w in (self.w_input_hidden.detach(), self.w_hidden_output.detach())
        )
        for weight in rounded:
            if torch.any(weight < STATE_MIN) or torch.any(weight > STATE_MAX):
                raise ValueError("B2 integer weight exceeds signed24 P03 packer range")
        return tuple(w.to(torch.int32).cpu().contiguous() for w in rounded)

    @torch.no_grad()
    def to_network_spec(self) -> NetworkSpec:
        wih, who = self.effective_signed_weights()
        h = self.hidden_neurons
        return NetworkSpec(
            populations=(
                PopulationSpec(B21_HIDDEN_NAME, h, _convert_params(self.hidden_config)),
                PopulationSpec(B21_READOUT_NAME, OUTPUT_CLASSES, _convert_params(self.output_config)),
            ),
            input_populations=(InputPopulationSpec(B21_SOURCE_INPUT, INPUT_CHANNELS),),
            input_projections=(InputProjectionSpec(
                "pixels_to_hidden", B21_SOURCE_INPUT, B21_HIDDEN_NAME,
                tuple(ProjectionConnection(src, dst, int(wih[dst, src]))
                      for dst in range(h) for src in range(INPUT_CHANNELS)),
            ),),
            projections=(ProjectionSpec(
                "hidden_to_readout", B21_HIDDEN_NAME, B21_READOUT_NAME,
                tuple(ProjectionConnection(src, dst, int(who[dst, src]))
                      for dst in range(OUTPUT_CLASSES) for src in range(h)),
            ),),
        )

    @torch.no_grad()
    def integer_weight_sha256(self) -> str:
        """Dimension-bound signed32 little-endian digest, distinct from frozen A3."""
        h = hashlib.sha256()
        for label, weight in zip(("input_hidden", "hidden_readout"),
                                 self.effective_signed_weights(), strict=True):
            tag = f"B2.1/{label}/{tuple(weight.shape)}".encode()
            h.update(struct.pack("<H", len(tag)))
            h.update(tag)
            for row in weight.tolist():
                for value in row:
                    h.update(struct.pack("<i", value))
        return h.hexdigest()


def foundation_manifest(settings: B21Settings, model: B21IntegerSNN) -> dict:
    if not isinstance(settings, B21Settings) or not isinstance(model, B21IntegerSNN):
        raise TypeError("B2.1 settings/model required")
    if settings.hidden_neurons != model.hidden_neurons:
        raise ValueError("B2 manifest topology and model tensor width mismatch")
    return {
        "schema": B21_SCHEMA,
        "architecture": [INPUT_CHANNELS, settings.hidden_neurons, OUTPUT_CLASSES],
        "connections_dense": (INPUT_CHANNELS + OUTPUT_CLASSES) * settings.hidden_neurons,
        "training_settings": asdict(settings),
        "hidden_lif": asdict(model.hidden_config),
        "readout_lif": asdict(model.output_config),
        "input_encoder": ENCODER_PROFILE,
        "readout": READOUT_PROFILE,
        "timesteps": TOTAL_TICKS,
        "quantization": "signed24 STE round-half-away forward, exact float64 sums",
        "effective_integer_weights_sha256": model.integer_weight_sha256(),
        "model_state": "SEEDED_UNTRAINED_B2_1_FOUNDATION",
        "train_validation_only": True,
        "official_mnist_test_status": "SEALED_NOT_ACCESSED",
        "checkpoint_frozen": False,
        "B1_2_packed_mapping_verified_for_this_weight_set": False,
        "physical_kv260_execution": "NOT_TESTED",
    }
