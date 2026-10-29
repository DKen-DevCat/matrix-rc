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
    armature: float | None = None  # kg·m²。ロータの慣性 × 減速比²（減速後の軸に換算）。None なら無負荷回転数から推定
    torque_limit: float | None = None  # N·m。ギアボックスが受けられる瞬間トルクの上限（停動トルクより小さいとき）

    def at(self, volts: float) -> tuple[float, float]:
        """電圧 volts での (無負荷の角速度 rad/s, 停動トルク N·m)。どちらも電圧に比例するとみなす。"""
        s = volts / self.rated_v
        return self.no_load_rpm * 2 * math.pi / 60 * s, self.stall_torque * s

    @property
    def reflected_inertia(self) -> float:
        """減速後の軸から見たロータの慣性 kg·m²。N20 100:1（6V で 300rpm）を 2e-6 とし、減速比は回転数に反比例するとして推定。

        実測のモーターは電池電圧を定格にして作られる（calibrate）ので、回転数を 6V 相当に直してから比べる。
        """
        if self.armature is not None:
            return self.armature
        rpm_at_6v = self.no_load_rpm * 6.0 / self.rated_v
        return ARMATURE_100_1 * (300.0 / rpm_at_6v) ** 2


# N20 100:1 の、減速後の軸から見たロータの慣性（推定）
ARMATURE_100_1 = 2e-6
# 真上跳びで 30mm 段差を越えるのに要る前進の速さ m/s。概算は車体 91mm ÷ 30mm より高い滞空 0.16 秒 ≒ 0.57m/s だが、
# 物理演算では 0.54m/s（800rpm 級）でも越えるので、設計書②・C4 の「0.5m/s 以上」を基準にする
REQUIRED_RUN_SPEED = 0.5


# 走行用 N20（6V 300rpm）。停動トルクは推定（汎用 N20 100:1 の公称値の目安）。
N20_300RPM = Motor(rated_v=6.0, no_load_rpm=300, stall_torque=0.06)
# 高速化案（設計書② 7章「500rpm 級」）。停動トルクはギア比に反比例として推定。
N20_500RPM = Motor(rated_v=6.0, no_load_rpm=500, stall_torque=0.036)
# 真上跳び＋前進で 30mm 段差を越えるのに要る速さ（0.5m/s 以上）のための候補。停動トルクは同じく推定。
N20_800RPM = Motor(rated_v=6.0, no_load_rpm=800, stall_torque=0.0225)
N20_1000RPM = Motor(rated_v=6.0, no_load_rpm=1000, stall_torque=0.018)
# Pololu 136:1 Sub-Micro Plastic Planetary Gearmotor 6Dx19L（#2358）：6V で無負荷 500rpm、停動 8oz·in（0.0565N·m）、1.25g（メーカー値）。
# 長さ 19mm なので左右 2 個を一直線に並べられる（2026-10-29 採用）。ギアは樹脂で、瞬間トルクの推奨上限は 3.5oz·in 程度（同シリーズの値）
N20_LENGTH = 24.0      # N20 の長さ（缶 15＋ギアボックス 9）mm
POLOLU_136_LENGTH = 19.0   # Pololu 136:1 の長さ（モーター 9.3＋ギアボックス 9.7）mm
POLOLU_136 = Motor(rated_v=6.0, no_load_rpm=500, stall_torque=0.0565,
                   # ロータは N20 の半分の径で慣性はおよそ 1/16、減速比 136:1 を掛けて 2.3e-7（推定）
                   armature=2.3e-7,
                   # 樹脂ギアの瞬間トルクの推奨上限 3.5oz·in（Pololu が同シリーズの 700:1 に書く値。136:1 も同じとみなす：推定）
                   torque_limit=0.0247)
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
    lower_x: tuple[float, float] = (1.0, 90.0)    # 下段の前後の範囲（四隅のばねの座が板に載るよう、上段と同じ長さ。2026-10-29）
    lower_width: float = 39.0     # 車輪の内側の面（|y| 20.5）から 1mm 離す（2026-10-29）
    lower_z: tuple[float, float] = (11.0, 23.0)   # 下段の下面・上面（地面から、伸びた状態）。走行モーター（N20、高さ 10）の軸を車輪の中心 16mm に合わせ、その上に板（厚さ 2）
    upper_x: tuple[float, float] = (1.0, 90.0)
    upper_z: tuple[float, float] = (44.0, 58.0)   # 上段の板の下面・上面（伸びた状態。すき間 21mm）。縮めきると下面 34mm で車輪上端 32mm に 2mm の余裕（2026-10-29、φ32 に合わせて 6mm 上げた）
    wheel_radius: float = 16.0     # タイヤ φ32（Pololu 1087/1088 32×7mm、2026-10-29 に φ26 から変更）
    wheel_width: float = 7.0
    wheels: tuple[Wheel, ...] = (
        Wheel(23.0, 24.0, "left"),   # 左後輪（左モーター）。外側の面が車体の幅 55 に揃う
        Wheel(23.0, -24.0, "right"),  # 右後輪（右モーター）。左右を同じ位置に揃える（2026-10-29。前後にずらすと段差の角に当たる時刻がずれ、向きが変わる）
        Wheel(75.0, 24.0, None),     # 前輪は自由回転。前の端が車体の前端 91 に揃う
        Wheel(75.0, -24.0, None),
    )
    # ばね（＝ガイドピン）の位置 (x, y) mm と、ばねの外径。電池（幅 34.5）を板の裏に置くので四隅に寄せる（2026-10-29）
    springs: tuple[tuple[float, float], ...] = ((6.0, 15.5), (6.0, -15.5), (86.0, 15.5), (86.0, -15.5))   # 外径 7 が両方の板（x 1〜90、下段は幅 39）に収まる
    spring_od: float = 7.0

    # ---- 質量（設計書② 4章。部品ごとの内訳は sim/model/build_model.py の PARTS 表）----
    upper_mass: float = 68.0       # 上段の小計（電池 LP603449-PCM-LD 23g を含む）
    lower_mass: float = 41.5       # 下段の小計（車輪 4 輪 12.8g を含む。走行モーターを 1.25g の 6mm 遊星にした）
    wheel_mass: float = 3.2        # 1 輪あたり（Pololu の公称）

    # ---- ジャンプ（設計書② 7章・C4）----
    spring_count: int = 4
    spring_rate: float = 0.5       # N/mm（1 本あたり）
    spring_free_length: float = 25.0
    stroke: float = 10.0           # 縮める量 mm（すき間 21 → 11）
    tilt_deg: float = 0.0          # ばね軸（ガイドピン）の前傾角。0 が現行の図面
    cam_lift_angle: float = 5.2    # rad。揚程 10mm をこの角度で上げる（C4）
    cam_efficiency: float = 0.5    # 摩擦込みの効率（C4 の「摩擦込みで約 0.08N·m」に相当）

    # ---- 電気 ----
    battery_v: float = 3.7         # 1S リポの公称
    drive_motor: Motor = POLOLU_136  # 2026-10-29 に N20 1000rpm から変更（左右を一直線に並べ、後輪の前後のずれをなくす）
    jump_motor: Motor = N20_1000_1
    throttle: float = 1.0          # ファームの速度上限 MAX_DUTY（1-b は env:xiao_1b で 1.0。firmware/src/main.cpp）

    # ---- 接触（推定。1-a の実測で合わせ込む）----
    floor_friction: float = 0.8
    contact_timeconst: float = 0.004  # s。小さいほど硬い接触
    stop_timeconst: float = 0.002  # s。上下段のストッパー（M2 ねじの頭＋O リング）の硬さ（推定）
    spring_damping: float = 0.05   # N·s/m。上下段の間の減衰（ばね 4 本の内部摩擦。推定。ほぼ減衰なし）
    step_height: float = 30.0      # 越えたい段差

    # ---- 計算 ----
    timestep: float = 0.0002       # s。ばねの開放が速いので細かく

    # ---- Fusion から読んだ部品（matrix_sim.parts.apply が入れる）。None なら箱と円柱で近似 ----
    parts: tuple | None = None

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
