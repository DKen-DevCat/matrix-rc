"""段差越えをウィンドウで見る（macOS は mjpython で起動する：make view）。

    mjpython -m matrix_sim.view --tilt 20 --motor 500rpm --trigger 25
"""
import argparse
import time

import mujoco
import mujoco.viewer

from . import scenarios
from .build import front_x
from .params import DESIGN
from .sweep import MOTORS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tilt", type=float, default=20)
    ap.add_argument("--motor", choices=list(MOTORS), default="500rpm")
    ap.add_argument("--trigger", type=float, default=25, help="発射する段差までの距離 mm")
    ap.add_argument("--slow", type=float, default=4, help="スロー再生の倍率")
    a = ap.parse_args()

    p = DESIGN.with_(tilt_deg=a.tilt, drive_motor=MOTORS[a.motor])
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
