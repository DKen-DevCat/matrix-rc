"""段差越えをウィンドウで見る（macOS は mjpython で起動する：make view）。

    mjpython -m matrix_sim.view --parts model/export --trigger 40        # 採用案（前傾 0°・1000rpm）
    mjpython -m matrix_sim.view --tilt 20 --motor 500rpm --trigger 25    # 比較用
"""
import argparse
from pathlib import Path
import time

import mujoco
import mujoco.viewer

from . import calibrate, parts, scenarios
from .build import front_x
from .params import DESIGN
from .sweep import MOTORS, adopted_option


def main() -> None:
    ap = argparse.ArgumentParser()
    adopted = adopted_option(DESIGN)
    ap.add_argument("--tilt", type=float, default=adopted.tilt_deg)
    ap.add_argument("--motor", choices=list(MOTORS), default=adopted.motor)
    ap.add_argument("--trigger", type=float, default=40, help="発射する段差までの距離 mm")
    ap.add_argument("--slow", type=float, default=4, help="スロー再生の倍率")
    ap.add_argument("--parts", type=Path, help="部品モデルのフォルダ（make model が作る model/export など）")
    ap.add_argument("--measured", action="store_true", help="sim/calibration/*.csv の実測値を使う")
    a = ap.parse_args()

    base = calibrate.measured() if a.measured else DESIGN
    p = base.with_(tilt_deg=a.tilt, drive_motor=MOTORS[a.motor])
    if a.parts:
        p = parts.apply(p, parts.load_parts(a.parts))
    step_x = front_x(p) / 1000 + scenarios.RUN_UP
    v = scenarios.Vehicle(p, step_x=step_x)
    v.throttle = p.throttle
    with mujoco.viewer.launch_passive(v.h.model, v.h.data) as viewer:
        viewer.cam.lookat[:] = [step_x, 0, 0.03]
        viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 0.35, 90, -5
        start = time.time()
        while viewer.is_running() and v.t < 3.0:
            if v.front_x() >= step_x - a.trigger / 1000:
                v.release()
            while v.t < (time.time() - start) / a.slow:
                v.step()
            viewer.sync()
        while viewer.is_running():
            time.sleep(0.05)


if __name__ == "__main__":
    main()
