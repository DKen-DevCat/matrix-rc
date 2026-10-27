"""シミュレーションそのものが正しく動いているか（解析解と比べる）。"""
import math

import mujoco
import pytest

from matrix_sim import scenarios
from matrix_sim.params import DESIGN

G = 9.81


def _spring_mass(k: float, m: float, dt: float) -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_string(f"""
<mujoco><option timestep="{dt}" integrator="implicitfast" gravity="0 0 0"/>
  <worldbody><body><joint name="x" type="slide" axis="1 0 0" stiffness="{k}"/>
    <geom type="sphere" size="0.01" mass="{m}"/></body></worldbody></mujoco>""")


def test_free_fall_time():
    v = scenarios.Vehicle(DESIGN, z0=0.2, charged=False)
    while v.wheel_bottom_min() > 0.0005:
        v.step()
    assert v.t == pytest.approx(math.sqrt(2 * (0.2 - 0.0005) / G), rel=0.02)


def test_spring_mass_period_and_energy():
    # 上段の質量と、ばね 4 本の合計で振動させる。周期 2π√(m/k)、エネルギーが保たれる
    m, k = DESIGN.upper_mass / 1000, DESIGN.spring_k
    model = _spring_mass(k, m, DESIGN.timestep)
    d = mujoco.MjData(model)
    d.qpos[0] = -DESIGN.stroke / 1000
    crossings, prev = [], d.qpos[0]
    while d.time < 0.2:
        mujoco.mj_step(model, d)
        if prev < 0 <= d.qpos[0]:
            crossings.append(d.time)
        prev = d.qpos[0]
    period = crossings[1] - crossings[0]
    assert period == pytest.approx(2 * math.pi * math.sqrt(m / k), rel=0.01)
    energy = 0.5 * m * d.qvel[0] ** 2 + 0.5 * k * d.qpos[0] ** 2
    assert energy == pytest.approx(DESIGN.spring_energy, rel=0.02)


def test_drive_speed_matches_motor_model():
    v = scenarios.Vehicle(DESIGN)
    v.throttle = DESIGN.throttle
    scenarios.run(v, 0.5)
    assert v.speed() == pytest.approx(DESIGN.drive_speed(), rel=0.03)


def test_latch_holds_spring_compressed():
    v = scenarios.Vehicle(DESIGN)
    scenarios.run(v, 0.3)
    q = v.h.data.qpos[v.h.lift_q]
    assert q == pytest.approx(-DESIGN.stroke / 1000, abs=0.0005)


def test_jump_height_is_below_momentum_bound():
    # 上段がばねのエネルギーを全部受け取り、下段を完全非弾性に引き上げたときの高さが上限
    mu, ml = DESIGN.upper_mass / 1000, DESIGN.lower_mass / 1000
    vu = math.sqrt(2 * DESIGN.spring_energy / mu)
    bound = (mu * vu / (mu + ml)) ** 2 / (2 * G) * 1000
    lift = scenarios.jump_in_place(DESIGN).lift_mm
    assert 0.8 * bound < lift < bound


def test_result_does_not_depend_on_timestep():
    a = scenarios.jump_in_place(DESIGN).lift_mm
    b = scenarios.jump_in_place(DESIGN.with_(timestep=DESIGN.timestep / 2)).lift_mm
    assert a == pytest.approx(b, rel=0.03)
