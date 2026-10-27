"""Params → MuJoCo のモデル（MJCF）。

座標：x が前、y が左、z が上。下段の原点は「後端・中心線・地面（車輪の接地点の高さ）」で、
伸びた状態で地面に置いたときの C3 の寸法がそのまま使える。部品は箱と円柱で近似する。
Fusion から形状を書き出したら、ここを STL に差し替える（PR B）。
"""
from dataclasses import dataclass
import math

import mujoco

from .params import Params

# カムがばねを縮めた状態で保持する強さ（20N で 0.2mm しかずれない）。発射で 0 にする
LATCH_KP = 1e5
LATCH_KD = 150.0


def _mm(v: float) -> float:
    return v / 1000


def _v(*xs: float) -> str:
    return " ".join(f"{x:.6g}" for x in xs)


def front_x(p: Params) -> float:
    """車体のいちばん前の位置 mm（上段・下段・前輪のうち前に出ているもの）。段差までの距離の基準。"""
    return max(p.lower_x[1], p.upper_x[1], max(w.x for w in p.wheels) + p.wheel_radius)


def xml(p: Params, step_x: float | None = None) -> str:
    """step_x（m）を渡すと、そこから前に高さ step_height の段差を置く。"""
    lx0, lx1 = p.lower_x
    lz0, lz1 = p.lower_z
    ux0, ux1 = p.upper_x
    uz0, uz1 = p.upper_z
    r, hw = _mm(p.wheel_radius), _mm(p.wheel_width) / 2
    chassis_mass = (p.lower_mass - p.wheel_mass * len(p.wheels)) / 1000
    tilt = math.radians(p.tilt_deg)
    axis = _v(math.sin(tilt), 0, math.cos(tilt))

    # ギアで増幅されたロータの慣性。走行モーターの付いた車輪だけに効く（前輪は自由回転）
    w0, ts = p.drive_motor.at(p.battery_v)
    wheels = []
    for i, w in enumerate(p.wheels):
        armature = p.drive_armature if w.driven else 0.0
        wheels.append(f"""
      <body name="wheel{i}" pos="{_v(_mm(w.x), _mm(w.y), r)}">
        <joint name="wheel{i}" type="hinge" axis="0 1 0" armature="{armature:.6g}" damping="1e-6"/>
        <geom class="tire" type="cylinder" size="{_v(r, hw)}" zaxis="0 1 0" mass="{p.wheel_mass / 1000:.6g}"/>
      </body>""")

    drive = []
    for i, w in enumerate(p.wheels):
        if w.driven:
            # 直線モデル τ = Ts·u − (Ts/ω0)·ω を MuJoCo の中で解く（逆起電力の項を陰的に扱えるので安定）。u はデューティ
            drive.append(f'<general name="drive_{w.driven}" joint="wheel{i}" ctrlrange="-1 1" '
                         f'gainprm="{ts:.6g}" biastype="affine" biasprm="0 0 {-ts / w0:.6g}" forcerange="{-ts:.6g} {ts:.6g}"/>')

    step = ""
    if step_x is not None:
        h = _mm(p.step_height)
        step = f'<geom name="step" type="box" pos="{_v(step_x + 0.5, 0, h / 2)}" size="{_v(0.5, 0.5, h / 2)}" rgba=".55 .55 .6 1"/>'

    return f"""
<mujoco model="matrix-rc">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{p.timestep}" integrator="implicitfast"/>
  <default>
    <geom friction="{p.floor_friction} 0.005 0.0001" solref="{p.contact_timeconst} 1" condim="3"/>
    <default class="tire"><geom condim="4" rgba=".15 .15 .15 1"/></default>
  </default>
  <worldbody>
    <light pos="0 0 1" dir="0 0 -1"/>
    <geom name="floor" type="plane" size="0 0 0.05" rgba=".85 .85 .8 1"/>
    {step}
    <body name="lower" pos="0 0 0">
      <freejoint name="root"/>
      <geom name="lower" type="box" pos="{_v(_mm(lx0 + lx1) / 2, 0, _mm(lz0 + lz1) / 2)}"
            size="{_v(_mm(lx1 - lx0) / 2, _mm(p.lower_width) / 2, _mm(lz1 - lz0) / 2)}"
            mass="{chassis_mass:.6g}" rgba=".8 .8 .82 1"/>
      <site name="front" pos="{_v(_mm(front_x(p)), 0, _mm(lz0 + lz1) / 2)}"/>
      {"".join(wheels)}
      <body name="upper" pos="0 0 0">
        <joint name="lift" type="slide" axis="{axis}" range="{-_mm(p.stroke)} 0"
               stiffness="{p.spring_k}" springref="0" damping="0.05"/>
        <geom name="upper" type="box" pos="{_v(_mm(ux0 + ux1) / 2, 0, _mm(uz0 + uz1) / 2)}"
              size="{_v(_mm(ux1 - ux0) / 2, _mm(p.width) / 2, _mm(uz1 - uz0) / 2)}"
              mass="{p.upper_mass / 1000:.6g}" rgba=".55 .7 .95 1"/>
        <site name="imu" pos="{_v(_mm(ux0 + ux1) / 2, 0, _mm(uz0 + uz1) / 2)}"/>
      </body>
    </body>
  </worldbody>
  <contact>
    {"".join(f'<exclude body1="upper" body2="wheel{i}"/>' for i in range(len(p.wheels)))}
  </contact>
  <actuator>
    {"".join(drive)}
    <general name="latch" joint="lift" gainprm="{LATCH_KP}" biastype="affine" biasprm="0 {-LATCH_KP} {-LATCH_KD}"/>
  </actuator>
  <sensor>
    <accelerometer name="imu" site="imu"/>
  </sensor>
</mujoco>
"""


@dataclass
class Handles:
    model: mujoco.MjModel
    data: mujoco.MjData
    lift_q: int        # lift 関節の qpos 番号
    lift_v: int        # lift 関節の qvel 番号
    wheel_bodies: list[int]
    wheel_v: dict[str, int]   # "left"/"right" → 車輪関節の qvel 番号
    act: dict[str, int]       # アクチュエータ名 → 番号
    front_site: int
    lower_body: int
    upper_body: int


def load(p: Params, step_x: float | None = None) -> Handles:
    m = mujoco.MjModel.from_xml_string(xml(p, step_x))
    d = mujoco.MjData(m)
    jid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
    bid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)
    wheel_v = {}
    for i, w in enumerate(p.wheels):
        if w.driven:
            wheel_v[w.driven] = m.jnt_dofadr[jid(f"wheel{i}")]
    return Handles(
        model=m,
        data=d,
        lift_q=m.jnt_qposadr[jid("lift")],
        lift_v=m.jnt_dofadr[jid("lift")],
        wheel_bodies=[bid(f"wheel{i}") for i in range(len(p.wheels))],
        wheel_v=wheel_v,
        act={m.actuator(i).name: i for i in range(m.nu)},
        front_site=mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "front"),
        lower_body=bid("lower"),
        upper_body=bid("upper"),
    )
