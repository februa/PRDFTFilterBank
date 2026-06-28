from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPFLOW_REPO = ROOT.parent / "spflow"
if SPFLOW_REPO.exists():
    sys.path.insert(0, str(SPFLOW_REPO / "src"))

from spflow import Flow  # type: ignore

from scene_adapter import SimulationConfig, render_scene, run_subband_beamforming


def main() -> None:
    config = SimulationConfig()
    x, positions = render_scene(config)
    outputs = (
        Flow.from_value((x, positions))
        .map(lambda value: run_subband_beamforming(value[0], value[1], config))
        .to_list()
    )
    y_time, _, beam_angles_deg = outputs[0]
    print("beams:", y_time.shape[0])
    print("samples:", y_time.shape[1])
    print("angle range:", float(np.min(beam_angles_deg)), float(np.max(beam_angles_deg)))


if __name__ == "__main__":
    main()
