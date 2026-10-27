"""設計案の総当たりと、ばらつきを入れた成功率。

設計書② 1章の合格基準「助走付きで 3cm の段差を越える（10 回中 8 回以上）」を、
床の摩擦・質量・ばねの強さ・発射のタイミングをばらつかせた 10 通りで判定する。
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import math
import random

from .params import N20_300RPM, N20_500RPM, Params
from . import scenarios

MOTORS = {"300rpm": N20_300RPM, "500rpm": N20_500RPM}
TRIALS = 10
PASS = 8


@dataclass(frozen=True)
class Option:
    tilt_deg: float
    motor: str  # MOTORS のキー

    def params(self, base: Params) -> Params:
        return base.with_(tilt_deg=self.tilt_deg, drive_motor=MOTORS[self.motor])

    @property
    def label(self) -> str:
        return f"前傾 {self.tilt_deg:g}°・{self.motor}"


def perturb(p: Params, seed: int) -> tuple[Params, float]:
    """1 回分のばらつき。返り値は (Params, 発射タイミングのずれ s)。seed 0 はばらつきなし。"""
    if seed == 0:
        return p, 0.0
    r = random.Random(seed)
    q = p.with_(
        floor_friction=r.uniform(0.5, 1.0),          # タイル〜カーペット（推定）
        upper_mass=p.upper_mass * r.uniform(0.9, 1.1),
        spring_rate=p.spring_rate * r.uniform(0.9, 1.1),
    )
    return q, r.uniform(-0.02, 0.02)  # ±20ms（ファームの制御周期とカム位置の検知のずれ）


def _trial(args) -> bool:
    p, trigger_mm, seed = args
    q, dt = perturb(p, seed)
    shifted = trigger_mm + dt * q.drive_speed() * 1000
    return scenarios.step_climb(q, max(0.0, shifted)).success


@dataclass(frozen=True)
class Window:
    option: Option
    rates: dict[float, int]   # 発射距離 mm → trials 回中の成功回数
    speed: float              # 走行の速さ m/s
    trials: int = TRIALS

    @property
    def threshold(self) -> int:
        """合格に要る成功回数（10 回中 8 回を trials 回に換算）。"""
        return math.ceil(PASS * self.trials / TRIALS)

    @property
    def passing(self) -> list[float]:
        return [t for t, n in self.rates.items() if n >= self.threshold]

    @property
    def window_ms(self) -> float:
        """合格する発射距離の幅を、走行の速さで時間に直したもの（操作のタイミングの余裕）。

        間に不合格を挟まない、いちばん長い連続区間の端から端まで（格子の刻み分は足さない）。
        """
        ts = sorted(self.rates)
        run_start = None
        span = 0.0
        for t in ts:
            if self.rates[t] >= self.threshold:
                run_start = t if run_start is None else run_start
                span = max(span, t - run_start)
            else:
                run_start = None
        return span / 1000 / self.speed * 1000


def evaluate(base: Params, options: list[Option], triggers: list[float],
             trials: int = TRIALS, workers: int | None = None) -> list[Window]:
    jobs, keys = [], []
    for o in options:
        p = o.params(base)
        for t in triggers:
            for s in range(trials):
                jobs.append((p, t, s))
                keys.append((o, t))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_trial, jobs, chunksize=4))
    counts: dict[tuple[Option, float], int] = {}
    for k, ok in zip(keys, results):
        counts[k] = counts.get(k, 0) + int(ok)
    return [Window(o, {t: counts[(o, t)] for t in triggers}, o.params(base).drive_speed(), trials) for o in options]
