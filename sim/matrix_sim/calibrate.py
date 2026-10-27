"""実測値（sim/calibration/*.csv）から Params の推定値を置き換える。

    python -m matrix_sim.calibrate            # 何が置き換わるかを表示する
    python -m matrix_sim.report --measured    # 実測値を使って結果を作り直す

測り方は各 CSV の先頭のコメントと sim/README.md。行がない CSV は使わない（推定値のまま）。
"""
import csv
import math
from pathlib import Path

import numpy as np

from .params import DESIGN, Motor, Params

DIR = Path(__file__).resolve().parents[1] / "calibration"
G = 9.81


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [l for l in path.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def motor_from_rows(rows: list[dict], volts: float) -> Motor | None:
    """電池電圧にいちばん近い電圧の測定（何回かあれば平均）から、その電圧を定格とするモーターを作る。

    直線モデルなので、ほかの電圧へは比例させられる。
    """
    if not rows:
        return None
    v = min((float(r["volts"]) for r in rows), key=lambda x: abs(x - volts))
    at = [r for r in rows if float(r["volts"]) == v]
    rpm = sum(float(r["no_load_rpm"]) for r in at) / len(at)
    stall = sum(float(r["stall_force_g"]) / 1000 * G * float(r["arm_mm"]) / 1000 for r in at) / len(at)
    return Motor(rated_v=v, no_load_rpm=rpm, stall_torque=stall)


def spring_rate_from_rows(rows: list[dict]) -> float | None:
    """原点を通る直線の傾き N/mm（最小二乗）。"""
    if not rows:
        return None
    x = np.array([float(r["compression_mm"]) for r in rows])
    f = np.array([float(r["force_g"]) for r in rows]) / 1000 * G
    return float(x @ f / (x @ x))


def friction_from_rows(rows: list[dict]) -> dict[str, float]:
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["surface"], []).append(math.tan(math.radians(float(r["slip_angle_deg"]))))
    return {k: sum(v) / len(v) for k, v in by.items()}


def overrides(folder: Path = DIR, base: Params = DESIGN) -> dict:
    o: dict = {}
    motors = _rows(folder / "motor.csv")
    for key, field in (("drive", "drive_motor"), ("jump", "jump_motor")):
        m = motor_from_rows([r for r in motors if r["motor"] == key], base.battery_v)
        if m:
            o[field] = m
    k = spring_rate_from_rows(_rows(folder / "spring.csv"))
    if k:
        o["spring_rate"] = k
    mu = friction_from_rows(_rows(folder / "friction.csv"))
    if mu:
        o["floor_friction"] = min(mu.values())  # 滑りやすい床で判定する（厳しい側）
    return o


def measured(folder: Path = DIR, base: Params = DESIGN) -> Params:
    return base.with_(**overrides(folder, base))


def main() -> None:
    o = overrides()
    if not o:
        print("実測値はまだない（sim/calibration/*.csv に行を足す）。すべて推定値のまま。")
        return
    for k, v in o.items():
        print(f"{k}: {getattr(DESIGN, k)} → {v}")


if __name__ == "__main__":
    main()
