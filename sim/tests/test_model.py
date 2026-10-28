"""コードから組んだ 3D モデル（model/export）が、params と設計書②の重量表に合っていること。

model/export は `make model`（Blender）で作り直す。ここでは書き出し済みのものを読む（テストに Blender は要らない）。
"""
import json
from pathlib import Path

import pytest

from matrix_sim import checks, parts, scenarios
from matrix_sim.params import DESIGN

EXPORT = Path(__file__).resolve().parents[1] / "model" / "export"


@pytest.fixture(scope="module")
def model():
    ps = parts.load_parts(EXPORT)
    return ps, parts.apply(DESIGN, ps)


def test_export_lists_every_role(model):
    ps, _ = model
    names = {p.name for p in ps}
    assert {"wheel_rl", "wheel_rr", "wheel_fl", "wheel_fr", "upper_plate", "upper_battery", "lower_plate",
            "lower_motor_l", "lower_motor_r", "lower_jump_motor"} <= names


def test_masses_match_design_doc_table(model):
    # 設計書② 4 章：上段 55〜65g、下段（車輪込み）約 45g、合計 100〜110g
    _, q = model
    assert 55 <= q.upper_mass <= 65
    assert 40 <= q.lower_mass <= 50
    assert 100 <= q.total_mass <= 110


def test_wheels_sit_where_params_say(model):
    _, q = model
    got = sorted((w.x, w.y, str(w.driven)) for w in q.wheels)
    want = sorted((w.x, w.y, str(w.driven)) for w in DESIGN.wheels)
    assert [g[:2] for g in got] == pytest.approx([w[:2] for w in want])
    assert [g[2] for g in got] == [w[2] for w in want]
    assert q.wheel_radius == pytest.approx(DESIGN.wheel_radius, abs=0.05)
    assert q.wheel_width == pytest.approx(DESIGN.wheel_width, abs=0.05)


def test_upper_plate_is_at_params_height(model):
    ps, _ = model
    plate = next(p for p in ps if p.name == "upper_plate")
    assert plate.bbox_min[2] * 1000 == pytest.approx(DESIGN.upper_z[0])
    assert plate.bbox_max[0] * 1000 == pytest.approx(DESIGN.upper_x[1])
    assert (plate.bbox_max[1] - plate.bbox_min[1]) * 1000 == pytest.approx(DESIGN.width)


def test_no_interference_when_compressed(model):
    # 部品ごとに見ても、縮めきった上段がタイヤにも下段の部品にも当たらない
    _, q = model
    assert checks.all_issues(q) == []


def test_battery_under_the_plate_clears_the_cam(model):
    ps, _ = model
    batt = next(p for p in ps if p.name == "upper_battery")
    cam = next(p for p in ps if p.name == "lower_cam")
    # 平面で 2mm 以上離れている（高さは縮めきると触れる寸法なので、平面で逃がす）
    gap_x = max(cam.bbox_min[0] - batt.bbox_max[0], batt.bbox_min[0] - cam.bbox_max[0]) * 1000
    assert gap_x >= 2.0


def test_lowest_upper_part_keeps_2mm_above_lower_plate(model):
    # 上段でいちばん低い部品（板の裏の電池）が、縮めきっても下段の板から 2mm 以上離れている
    ps, _ = model
    lowest = min(p.bbox_min[2] for p in ps if p.role == "upper") * 1000
    plate = next(p for p in ps if p.name == "lower_plate")
    assert lowest - DESIGN.stroke - plate.bbox_max[2] * 1000 >= 2.0


def test_guide_pins_pass_through_and_do_not_set_lower_extent(model):
    ps, q = model
    pins = next(p for p in ps if p.name == "lower_pins")
    assert pins.passes_through
    # 下段の上面はカム（板の上 2mm）までで、ピンの先端（44mm）までは伸びない
    assert q.lower_z[1] < pins.bbox_max[2] * 1000
    assert q.lower_z[1] == pytest.approx(DESIGN.lower_z[1] + 2.0)


def test_densities_are_plausible():
    # 質量と体積から出る密度が、樹脂（約 1）〜金属（約 8）の範囲。外れていたら置き場所か質量の割り振りが怪しい
    meta = json.loads((EXPORT / "parts.json").read_text())
    for e in meta["parts"]:
        assert 0.5 <= e["density_g_cm3"] <= 9.0, (e["name"], e["density_g_cm3"])


def test_part_coms_match_mesh_coms(model):
    # parts.json の重心（Blender の体積重心）と MuJoCo がメッシュから出す重心が一致する（読み込みの検算）
    _, q = model
    assert all(d < 0.5 for d in parts.com_mismatch_mm(q).values())


def test_model_jumps_like_the_box_model(model):
    _, q = model
    assert scenarios.jump_in_place(q).lift_mm == pytest.approx(scenarios.jump_in_place(DESIGN).lift_mm, rel=0.15)
