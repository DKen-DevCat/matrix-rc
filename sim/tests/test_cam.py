"""L1：渦巻きカムのトルクとチャージ時間（C4 の手計算と照合する）。"""
import math

import pytest

from matrix_sim import cam
from matrix_sim.params import DESIGN


def test_spring_values_match_c4():
    # C4：4 本 × 0.5N/mm × 10mm → 0.1J、縮めきりで合計 20N
    assert DESIGN.spring_k == pytest.approx(2000)
    assert DESIGN.spring_energy == pytest.approx(0.1)
    assert cam.follower_force(DESIGN, DESIGN.stroke / 1000) == pytest.approx(20 - DESIGN.upper_mass / 1000 * 9.81, rel=1e-6)


def test_peak_torque_matches_c4_hand_calculation():
    # C4：20N × 1.9mm ≒ 0.04N·m、摩擦込みで約 0.08N·m
    r = cam.analyze(DESIGN)
    assert r.peak_torque_ideal == pytest.approx(0.0385 - DESIGN.upper_mass / 1000 * 9.81 * 0.001923, rel=0.02)
    assert 0.06 < r.peak_torque < 0.09


def test_torque_needs_no_force_before_spring_engages():
    # 縮め始めは上段の重さで足りるので、カムに要るトルクは 0
    assert cam.required_torque(DESIGN, 0.0) == 0.0


def test_charge_time_is_integral_of_loaded_speed():
    r = cam.analyze(DESIGN)
    w0, _ = DESIGN.jump_motor.at(DESIGN.battery_v)
    unloaded = 2 * math.pi / w0
    # 負荷があるぶん、無負荷で 1 回転する時間より長い
    assert r.charge_time > unloaded
    assert r.charge_time < unloaded * 2


def test_motor_too_weak_is_reported_as_stall():
    weak = DESIGN.with_(jump_motor=DESIGN.jump_motor.__class__(6.0, 30, 0.05))
    r = cam.analyze(weak)
    assert r.stalls
    assert math.isinf(r.charge_time)
