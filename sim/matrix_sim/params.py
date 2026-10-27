"""寸法・質量・ばね・モーター・摩擦の正本（シミュレーション用）。

数値の出典は Notion の設計書②（7章・4章）と図面 C3・C4（docs/drawings/src/d2.py）。
「推定」と書いたものはデータシートや実測がまだない値で、Phase 1-a の実測で合わせ込む（README の「合わせ込み」）。
長さは mm、質量は g で書き、SI 単位への変換は build.py で行う。
"""
from dataclasses import dataclass, field, replace
import math


@dataclass(frozen=True)
class Motor:
    """DC ギアモーターの直線モデル。トルクと回転数は定格電圧での値。"""
    rated_v: float
    no_load_rpm: float
    stall_torque: float  # N·m（減速後の軸）

    def at(self, volts: float) -> tuple[float, float]:
        """電圧 volts での (無負荷の角速度 rad/s, 停動トルク N·m)。どちらも電圧に比例するとみなす。"""
        s = volts / self.rated_v
        return self.no_load_rpm * 2 * math.pi / 60 * s, self.stall_torque * s


# 走行用 N20（6V 300rpm）。停動トルクは推定（汎用 N20 100:1 の公称値の目安）。
N20_300RPM = Motor(rated_v=6.0, no_load_rpm=300, stall_torque=0.06)
# 高速化案（設計書② 7章「500rpm 級」）。停動トルクはギア比に反比例として推定。
N20_500RPM = Motor(rated_v=6.0, no_load_rpm=500, stall_torque=0.036)
# ジャンプ用の高減速 N20（1000:1 前後）。推定。
N20_1000_1 = Motor(rated_v=6.0, no_load_rpm=30, stall_torque=0.30)


@dataclass(frozen=True)
class Wheel:
    x: float  # 車体の後端からの位置 mm
    y: float  # 中心線から左が正 mm
    driven: str | None  # "left" / "right" / None（自由回転）


@dataclass(frozen=True)
class Params:
    # ---- 車体（C3）----
    length: float = 91.0           # 名刺の長辺
    width: float = 55.0
    lower_x: tuple[float, float] = (3.0, 88.0)    # 下段の前後の範囲
    lower_width: float = 41.0
    lower_z: tuple[float, float] = (8.0, 20.0)    # 下段の下面・上面（地面から、伸びた状態）
    upper_x: tuple[float, float] = (1.0, 90.0)
    upper_z: tuple[float, float] = (32.0, 46.0)   # 上段の下面・上面（伸びた状態。すき間 12mm）
    wheel_radius: float = 13.0     # タイヤ φ26
    wheel_width: float = 6.0
    wheels: tuple[Wheel, ...] = (
        Wheel(15.0, 24.5, "left"),   # 左後輪（左モーター）
        Wheel(29.0, -24.5, "right"),  # 右後輪（右モーター。前後にずらして置く）
        Wheel(76.0, 24.5, None),     # 前輪は自由回転
        Wheel(76.0, -24.5, None),
    )

    # ---- 質量（設計書② 4章）----
    upper_mass: float = 60.0       # 上段の小計 55〜65g
    lower_mass: float = 45.0       # 下段の小計（車輪を含む）
    wheel_mass: float = 2.0        # 1 輪あたり（推定）

    # ---- ジャンプ（設計書② 7章・C4）----
    spring_count: int = 4
    spring_rate: float = 0.5       # N/mm（1 本あたり）
    spring_free_length: float = 25.0
    stroke: float = 10.0           # 縮める量 mm（すき間 12 → 2）
    tilt_deg: float = 0.0          # ばね軸（ガイドピン）の前傾角。0 が現行の図面
    cam_lift_angle: float = 5.2    # rad。揚程 10mm をこの角度で上げる（C4）
    cam_efficiency: float = 0.5    # 摩擦込みの効率（C4 の「摩擦込みで約 0.08N·m」に相当）

    # ---- 電気 ----
    battery_v: float = 3.7         # 1S リポの公称
    drive_motor: Motor = N20_300RPM
    jump_motor: Motor = N20_1000_1
    drive_armature: float = 2e-6   # kg·m²。ロータの慣性 × 減速比²（推定。N20 100:1）
    throttle: float = 0.8          # ファームの速度上限 MAX_DUTY（firmware/src/main.cpp）

    # ---- 接触（推定。1-a の実測で合わせ込む）----
    floor_friction: float = 0.8
    contact_timeconst: float = 0.004  # s。小さいほど硬い接触
    step_height: float = 30.0      # 越えたい段差

    # ---- 計算 ----
    timestep: float = 0.0002       # s。ばねの開放が速いので細かく

    def with_(self, **kw) -> "Params":
        return replace(self, **kw)

    # ---- 導出値（SI）----
    @property
    def spring_k(self) -> float:
        """上下段の間のばね定数の合計 N/m。"""
        return self.spring_count * self.spring_rate * 1000

    @property
    def spring_energy(self) -> float:
        """縮めきったときに蓄えるエネルギー J。"""
        return 0.5 * self.spring_k * (self.stroke / 1000) ** 2

    @property
    def wheelbase(self) -> float:
        xs = [w.x for w in self.wheels]
        return max(xs) - min(xs)

    @property
    def total_mass(self) -> float:
        return self.upper_mass + self.lower_mass

    def drive_speed(self) -> float:
        """走行の無負荷の速さ m/s（電池電圧 × 速度上限）。"""
        w0, _ = self.drive_motor.at(self.battery_v * self.throttle)
        return w0 * self.wheel_radius / 1000


DESIGN = Params()
