"""Fusion の書き出し（STL＋parts.json）の読み込み。見本は箱と円柱のモデルから作る。"""
import json
from pathlib import Path

import numpy as np
import pytest

from matrix_sim import checks, parts, sample, scenarios
from matrix_sim.build import front_x
from matrix_sim.params import DESIGN

SAMPLE = Path(__file__).resolve().parents[1] / "fusion" / "sample"


def test_committed_sample_is_up_to_date(tmp_path):
    # 見本は sample.make で作り直せる（params を変えたら make sample で更新する）
    sample.make(tmp_path)
    assert json.loads((tmp_path / "parts.json").read_text()) == json.loads((SAMPLE / "parts.json").read_text())


def test_infer_scale_from_bbox():
    assert parts.infer_scale(np.array([91.0, 55, 14]), np.array([0.091, 0.055, 0.014])) == 0.001
    assert parts.infer_scale(np.array([9.1, 5.5, 1.4]), np.array([0.091, 0.055, 0.014])) == 0.01
    with pytest.raises(ValueError):
        parts.infer_scale(np.array([30.0, 5, 1]), np.array([0.091, 0.055, 0.014]))


def test_sample_reproduces_design_dimensions():
    p = parts.apply(DESIGN, parts.load_parts(SAMPLE))
    assert p.upper_x == pytest.approx(DESIGN.upper_x)
    assert p.upper_z == pytest.approx(DESIGN.upper_z)
    assert p.width == pytest.approx(DESIGN.width)
    assert p.wheel_radius == pytest.approx(DESIGN.wheel_radius, abs=0.05)
    assert p.wheel_width == pytest.approx(DESIGN.wheel_width)
    assert p.upper_mass == pytest.approx(DESIGN.upper_mass)
    assert p.lower_mass == pytest.approx(DESIGN.lower_mass)
    assert {w.driven for w in p.wheels} == {"left", "right", None}
    assert front_x(p) == pytest.approx(front_x(DESIGN), abs=0.1)
    assert len(checks.all_issues(p)) == 4  # 干渉の確認も同じ結果になる


def test_mesh_model_jumps_like_box_model():
    p = parts.apply(DESIGN, parts.load_parts(SAMPLE))
    assert scenarios.jump_in_place(p).lift_mm == pytest.approx(scenarios.jump_in_place(DESIGN).lift_mm, rel=0.03)


def test_mesh_model_drives_and_climbs_like_box_model():
    p = parts.apply(DESIGN.with_(tilt_deg=20), parts.load_parts(SAMPLE))
    assert scenarios.step_climb(p, 15).success == scenarios.step_climb(DESIGN.with_(tilt_deg=20), 15).success


def test_upper_deck_can_be_split_into_parts(tmp_path):
    # 上段を「板」と「電池」に分けても、合計の質量と外形は同じに読める
    sample.make(tmp_path)
    meta = json.loads((tmp_path / "parts.json").read_text())
    deck = next(e for e in meta["parts"] if e["name"] == "upper_deck")
    battery = dict(deck, name="upper_battery", mass=0.018)
    deck["mass"] = DESIGN.upper_mass / 1000 - 0.018
    meta["parts"].append(battery)
    (tmp_path / "parts.json").write_text(json.dumps(meta))
    p = parts.apply(DESIGN, parts.load_parts(tmp_path))
    assert p.upper_mass == pytest.approx(DESIGN.upper_mass)
    assert len([q for q in p.parts if q.role == "upper"]) == 2


def test_missing_wheel_is_an_error(tmp_path):
    sample.make(tmp_path)
    meta = json.loads((tmp_path / "parts.json").read_text())
    meta["parts"] = [e for e in meta["parts"] if e["name"] != "wheel_fr"]
    (tmp_path / "parts.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="wheel_fr"):
        parts.apply(DESIGN, parts.load_parts(tmp_path))


def test_unknown_names_are_ignored(tmp_path):
    sample.make(tmp_path)
    meta = json.loads((tmp_path / "parts.json").read_text())
    meta["parts"].append(dict(meta["parts"][0], name="screw_m2"))
    (tmp_path / "parts.json").write_text(json.dumps(meta))
    p = parts.apply(DESIGN, parts.load_parts(tmp_path))
    assert p.upper_mass == pytest.approx(DESIGN.upper_mass)
