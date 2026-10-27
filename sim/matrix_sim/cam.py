"""L1：渦巻きカムの計算（準静的）。

カムは 1 方向に回り、揚程を cam_lift_angle（rad）かけて直線的に stroke まで上げ、段差で一気に落とす（C4）。
残りの角度（2π − cam_lift_angle）は揚程 0 のまま空回りする。
"""
from dataclasses import dataclass
import math

import numpy as np

from .params import Params

G = 9.81


def follower_force(p: Params, x: float) -> float:
    """ばねを x（m）縮めた状態でフォロワーに要る力 N。上段の重さのぶんは差し引く。"""
    return max(0.0, p.spring_k * x - p.upper_mass / 1000 * G)


def required_torque(p: Params, theta: float) -> float:
    """カム角 theta（rad、揚程区間の始まりが 0）で要るトルク N·m（摩擦込み）。"""
    if theta < 0 or theta >= p.cam_lift_angle:
        return 0.0
    dr = p.stroke / 1000 / p.cam_lift_angle  # 揚程の増え方 m/rad
    x = dr * theta
    return follower_force(p, x) * dr / p.cam_efficiency


@dataclass(frozen=True)
class CamResult:
    peak_torque: float        # 摩擦込み N·m
    peak_torque_ideal: float  # 摩擦なし N·m
    stall_torque: float       # ジャンプ用モーターの停動トルク N·m（電池電圧）
    margin: float             # peak_torque / stall_torque
    stalls: bool
    charge_time: float        # 発射してから次のチャージ完了まで s（止まるなら inf）


def analyze(p: Params, n: int = 2000) -> CamResult:
    w0, ts = p.jump_motor.at(p.battery_v)
    thetas = np.linspace(0, p.cam_lift_angle, n, endpoint=False)
    torques = np.array([required_torque(p, t) for t in thetas])
    peak = float(torques.max())
    stalls = peak >= ts
    if stalls:
        charge = math.inf
    else:
        # 負荷のある区間は ω = ω0 (1 − T/Ts) で積分、空回り区間は無負荷
        dtheta = p.cam_lift_angle / n
        charge = float(np.sum(dtheta / (w0 * (1 - torques / ts))))
        charge += (2 * math.pi - p.cam_lift_angle) / w0
    return CamResult(
        peak_torque=peak,
        peak_torque_ideal=peak * p.cam_efficiency,
        stall_torque=ts,
        margin=peak / ts,
        stalls=stalls,
        charge_time=charge,
    )
