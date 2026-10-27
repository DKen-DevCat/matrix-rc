"""実測値の CSV から Params を置き換える。"""
import math

import pytest

from matrix_sim import calibrate
from matrix_sim.params import DESIGN


def _write(folder, name, text):
    (folder / name).write_text(text)


def test_empty_templates_change_nothing(tmp_path):
    _write(tmp_path, "motor.csv", "# コメント\nmotor,volts,no_load_rpm,arm_mm,stall_force_g\n")
    assert calibrate.overrides(tmp_path) == {}
    assert calibrate.measured(tmp_path) == DESIGN


def test_committed_templates_are_empty():
    # リポジトリの CSV は見出しだけ（実測が入るまで推定値のまま）
    assert calibrate.overrides() == {}


def test_motor_uses_row_closest_to_battery_voltage(tmp_path):
    _write(tmp_path, "motor.csv",
           "motor,volts,no_load_rpm,arm_mm,stall_force_g\n"
           "drive,3.0,140,20,150\n"
           "drive,3.8,180,20,200\n"
           "jump,3.8,17,20,900\n")
    o = calibrate.overrides(tmp_path)
    m = o["drive_motor"]
    assert (m.rated_v, m.no_load_rpm) == (3.8, 180)
    assert m.stall_torque == pytest.approx(0.2 * 9.81 * 0.02)
    assert o["jump_motor"].stall_torque == pytest.approx(0.9 * 9.81 * 0.02)


def test_spring_rate_is_least_squares_through_origin(tmp_path):
    _write(tmp_path, "spring.csv", "compression_mm,force_g\n5,250\n10,520\n")
    k = calibrate.overrides(tmp_path)["spring_rate"]
    # 0.5N/mm 前後
    assert k == pytest.approx((5 * 2.4525 + 10 * 5.1012) / (25 + 100), rel=1e-3)


def test_friction_takes_slipperiest_surface(tmp_path):
    _write(tmp_path, "friction.csv", "surface,slip_angle_deg\ntile,30\ntile,32\ncarpet,40\n")
    mu = calibrate.overrides(tmp_path)["floor_friction"]
    assert mu == pytest.approx((math.tan(math.radians(30)) + math.tan(math.radians(32))) / 2)
