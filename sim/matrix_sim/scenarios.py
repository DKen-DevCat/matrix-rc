"""L2：物理演算のシナリオ（その場ジャンプ・段差越え・落下）。

ばねは「縮めきった状態をカムが保持している」ところから始め、発射の瞬間に保持の力を外す。
カムの段差で一気に開放するので、開放後の動きにカム形状はほとんど効かない（カムとの接触は PR B で足す）。
"""
from dataclasses import dataclass
import math

import mujoco
import numpy as np

from .build import Handles, front_x, load
from .params import Params

G = 9.81


class Vehicle:
    """1 台分の状態と、毎ステップの制御（走行モーターとカムの保持）。"""

    def __init__(self, p: Params, step_x: float | None = None, x0: float = 0.0,
                 z0: float = 0.0005, charged: bool = True):
        self.p = p
        self.h: Handles = load(p, step_x)
        m, d = self.h.model, self.h.data
        d.qpos[0:3] = [x0, 0, z0]
        d.qpos[3:7] = [1, 0, 0, 0]
        d.ctrl[self.h.act["latch"]] = -p.stroke / 1000
        if charged:
            d.qpos[self.h.lift_q] = -p.stroke / 1000
        else:
            self.release()
        self.throttle = 0.0
        mujoco.mj_forward(m, d)

    @property
    def t(self) -> float:
        return self.h.data.time

    def release(self) -> None:
        """カムの段差でフォロワーが外れる＝保持の力を 0 にする。"""
        i = self.h.act["latch"]
        self.h.model.actuator_gainprm[i, 0] = 0
        self.h.model.actuator_biasprm[i, :3] = 0

    def step(self) -> None:
        h, d = self.h, self.h.data
        for side in h.wheel_v:
            d.ctrl[h.act[f"drive_{side}"]] = self.throttle
        mujoco.mj_step(h.model, d)

    # ---- 観測 ----
    def wheel_centers(self) -> np.ndarray:
        return self.h.data.xpos[self.h.wheel_bodies]

    def wheel_bottom_min(self) -> float:
        return float(self.wheel_centers()[:, 2].min() - self.p.wheel_radius / 1000)

    def front_x(self) -> float:
        return float(self.h.data.site_xpos[self.h.front_site][0])

    def speed(self) -> float:
        return float(self.h.data.qvel[0])

    def upright(self) -> float:
        """下段の上向きベクトルの z 成分（1 で水平、0 で横倒し）。"""
        return float(self.h.data.xmat[self.h.lower_body][8])

    def accel_g(self) -> float:
        """上段に付けた加速度計の大きさ（g 単位、静止で 1）。"""
        return float(np.linalg.norm(self.h.data.sensordata[0:3]) / G)


def run(v: Vehicle, seconds: float, each=None) -> None:
    end = v.t + seconds
    while v.t < end:
        v.step()
        if each is not None and each(v) is False:
            return


# ---------------------------------------------------------------- その場ジャンプ

@dataclass(frozen=True)
class JumpResult:
    lift_mm: float          # 車輪の下端が地面から上がった最大の高さ
    airtime_s: float        # 1 回目の離陸から 1 回目の着地まで（全輪が地面から離れていた時間）
    upright: float          # 着地後の姿勢（1 で水平）
    peak_accel_g: float     # 発射から着地後の落ち着きまでの、上段の最大加速度


def jump_in_place(p: Params) -> JumpResult:
    v = Vehicle(p)
    run(v, 0.2)  # 置いた直後の揺れを落ち着かせる
    v.release()
    best, peak = 0.0, 0.0
    took_off = landed = None

    def watch(v: Vehicle):
        nonlocal best, peak, took_off, landed
        z = v.wheel_bottom_min()
        best = max(best, z)
        if took_off is None and z > 0.001:
            took_off = v.t
        elif took_off is not None and landed is None and z <= 0.001:
            landed = v.t
        peak = max(peak, v.accel_g())

    run(v, 0.8, watch)
    air = 0.0 if took_off is None else (landed if landed is not None else v.t) - took_off
    return JumpResult(best * 1000, air, v.upright(), peak)


# ---------------------------------------------------------------- 段差越え

@dataclass(frozen=True)
class StepResult:
    success: bool
    outcome: str            # "cleared" / "front_only" / "blocked" / "flipped"
    lift_mm: float
    speed_at_release: float  # m/s
    released_at_gap_mm: float


RUN_UP = 0.12  # 段差の手前、車体の前端までの助走 m


def step_climb(p: Params, trigger_mm: float, settle: float = 1.2) -> StepResult:
    """車体の前端が段差まで trigger_mm になった瞬間に発射する。発射後も前進し続ける。"""
    front0 = front_x(p) / 1000
    step_x = front0 + RUN_UP
    v = Vehicle(p, step_x=step_x)
    v.throttle = p.throttle  # 助走はファームの速度上限いっぱい
    trigger = trigger_mm / 1000

    def until_trigger(v: Vehicle):
        return not (v.front_x() >= step_x - trigger or v.t > 3.0)

    run(v, 3.0, until_trigger)
    gap = step_x - v.front_x()
    spd = v.speed()
    v.release()
    best = 0.0

    def watch(v: Vehicle):
        nonlocal best
        best = max(best, v.wheel_bottom_min())

    run(v, settle, watch)
    c = v.wheel_centers()
    on_top = (c[:, 0] > step_x + 0.002) & (c[:, 2] > p.step_height / 1000 + 0.5 * p.wheel_radius / 1000)
    if v.upright() < 0.7:
        outcome = "flipped"
    elif on_top.all():
        outcome = "cleared"
    elif on_top.any():
        outcome = "front_only"
    else:
        outcome = "blocked"
    return StepResult(outcome == "cleared", outcome, best * 1000, spd, gap * 1000)


# ---------------------------------------------------------------- 落下

@dataclass(frozen=True)
class DropResult:
    peak_accel_g: float
    upright: float
    bounced_mm: float   # 着地後に跳ね返った最大の高さ


def drop_test(p: Params, height_mm: float = 300.0) -> DropResult:
    v = Vehicle(p, z0=height_mm / 1000, charged=False)
    peak, landed, bounce = 0.0, False, 0.0

    def watch(v: Vehicle):
        nonlocal peak, landed, bounce
        z = v.wheel_bottom_min()
        if z < 0.0005:
            landed = True
        if landed:
            bounce = max(bounce, z)
        peak = max(peak, v.accel_g())

    run(v, math.sqrt(2 * height_mm / 1000 / G) + 0.8, watch)
    return DropResult(peak, v.upright(), bounce * 1000)
