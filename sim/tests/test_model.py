"""コードから組んだ 3D モデル（model/export）が、params と設計書②の重量表に合っていること。

model/export は `make model`（Blender）で作り直す。ここでは書き出し済みのものを読む（テストに Blender は要らない）。
"""
import json
from pathlib import Path

import pytest

from matrix_sim import checks, parts, scenarios
from matrix_sim.params import DESIGN
from matrix_sim.sweep import PASS, Option, adopted_option, evaluate

EXPORT = Path(__file__).resolve().parents[1] / "model" / "export"


@pytest.fixture(scope="module")
def model():
    ps = parts.load_parts(EXPORT)
    return ps, parts.apply(DESIGN, ps)


def test_export_lists_every_role(model):
    ps, _ = model
    names = {p.name for p in ps}
    assert {"wheel_rl", "wheel_rr", "wheel_fl", "wheel_fr", "upper_plate", "upper_battery", "lower_plate",
            "lower_motor_l_can", "lower_motor_l_gear", "lower_motor_r_can", "lower_motor_r_gear",
            "lower_jump_can", "lower_jump_gear", "lower_cam_switch", "lower_springs"} <= names


def test_masses_match_params_and_design_doc(model):
    # 設計書② 4 章（2026-10-29 に部品の型番で見直し、走行モーターを Pololu 136:1 に）：上段 68g、下段（車輪込み）41.5g、合計 109.5g
    _, q = model
    assert q.upper_mass == pytest.approx(DESIGN.upper_mass, abs=0.5)
    assert q.lower_mass == pytest.approx(DESIGN.lower_mass, abs=0.5)
    assert q.wheel_mass == pytest.approx(DESIGN.wheel_mass, abs=0.05)


def test_battery_is_the_purchased_cell(model):
    # EEMB LP603449-PCM-LD：34.5×51×6.3mm、セル 22g＋保護回路
    ps, _ = model
    b = next(p for p in ps if p.name == "upper_battery")
    size = sorted(round((hi - lo) * 1000, 1) for lo, hi in zip(b.bbox_min, b.bbox_max))
    assert size == [6.3, 34.5, 51.0]
    assert 22 <= b.mass * 1000 <= 24


def test_drive_motors_sit_on_the_wheel_axle(model):
    # N20 の軸の高さ（断面の中心）が車輪の中心に合っている
    ps, _ = model
    for n in ("lower_motor_l_gear", "lower_motor_r_gear"):
        m = next(p for p in ps if p.name == n)
        assert (m.bbox_min[2] + m.bbox_max[2]) / 2 * 1000 == pytest.approx(DESIGN.wheel_radius)


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
    # 縮めきった電池の下面がカムの上面から 2mm 以上離れているか、平面で 2mm 以上離れている
    gap_z = (batt.bbox_min[2] * 1000 - DESIGN.stroke) - cam.bbox_max[2] * 1000
    gap_x = max(cam.bbox_min[0] - batt.bbox_max[0], batt.bbox_min[0] - cam.bbox_max[0]) * 1000
    assert gap_z >= 2.0 or gap_x >= 2.0


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
    # 下段の上面はいちばん高い下段の部品（カムのスイッチ）までで、ピンやばねの先端までは伸びない
    sw = next(p for p in ps if p.name == "lower_cam_switch")
    assert q.lower_z[1] < pins.bbox_max[2] * 1000
    assert q.lower_z[1] == pytest.approx(sw.bbox_max[2] * 1000)


def test_densities_are_plausible():
    # 質量と体積から出る密度が、樹脂（約 1）〜金属（約 8）の範囲。外れていたら置き場所か質量の割り振りが怪しい
    meta = json.loads((EXPORT / "parts.json").read_text())
    for e in meta["parts"]:
        assert 0.5 <= e["density_g_cm3"] <= 9.0, (e["name"], e["density_g_cm3"])


def test_part_coms_match_mesh_coms(model):
    # parts.json の重心（Blender の体積重心）と MuJoCo がメッシュから出す重心が一致する（読み込みの検算）
    _, q = model
    assert all(d < 0.5 for d in parts.com_mismatch_mm(q).values())


def test_detailed_model_clears_the_step_with_margin(model):
    # 2026-10-29：N20 1000rpm（127g、前後にずらす）では 40mm 手前の 1 点だけ 8/10 だった。
    # Pololu 136:1 を一直線に並べると 109g・跳躍 41mm になり、25〜45mm 手前の 5 点で 10 回中 9〜10 回
    _, q = model
    [w] = evaluate(q, [adopted_option(q)], [25, 30, 35, 40, 45])
    assert all(n >= PASS for n in w.rates.values()), w.rates


def test_detailed_model_jumps_at_least_c4_target(model):
    # C4 の目標 40mm を取り戻した（127g では 37mm だった）
    _, q = model
    assert scenarios.jump_in_place(q).lift_mm >= 40


def test_aligned_rear_wheels_keep_heading_over_the_step(model):
    # 見つかったこと（2026-10-29）：後輪を前後にずらすと、段差の角に当たる時刻が左右でずれ、越えたあと平均 6°・最大 33° 向きが変わった。
    # 揃えると 1° 前後。越えたこと（4 輪とも段差の上）も確かめる（ばらつきなしの 1 回）
    import math
    _, q = model
    r = scenarios.step_climb(q, 35)
    assert r.outcome == "cleared"
    v = scenarios.last_vehicle
    m = v.h.data.xmat[v.h.lower_body].reshape(3, 3)
    assert abs(math.degrees(math.atan2(m[1, 0], m[0, 0]))) < 3.0


def test_light_build_flips_on_drop_without_damping(model):
    # 見つかったこと（2026-10-29）：下段が 41.5g に軽くなった今の構成は、ばねにほぼ減衰がない（0.05N·s/m）と
    # 30cm の落下で跳ね返り（約 80mm）の間に前後に回って裏返る。127g の N20 の構成では立っていた。
    # 縮むときだけ効く減衰（4〜8N·s/m）で半分ほど立つ。対策は設計書② 10 章の決めること。対策を入れたら書き換える
    _, q = model
    assert scenarios.drop_test(q, 300).upright < 0


def _xy_overlap(a, b):
    return min(a.bbox_max[0], b.bbox_max[0]) - max(a.bbox_min[0], b.bbox_min[0]) > 0 and \
        min(a.bbox_max[1], b.bbox_max[1]) - max(a.bbox_min[1], b.bbox_min[1]) > 0


def test_every_upper_part_keeps_2mm_above_lower_parts_when_compressed(model):
    # 縮めきっても、上段のどの部品も下段のどの部品（ばね・ピンを除く）から 2mm 以上離れている。
    # 落下で縮めきりを 1.6mm 越える（test_jump）ので、2mm 未満だと当たる（見つかったこと：寝かせる前のカム位置スイッチは 0.8mm だった）
    ps, _ = model
    for u in (p for p in ps if p.role == "upper"):
        for lo in (p for p in ps if p.role == "lower" and not p.passes_through):
            if _xy_overlap(u, lo):
                gap = (u.bbox_min[2] * 1000 - DESIGN.stroke) - lo.bbox_max[2] * 1000
                assert gap >= 2.0, (u.name, lo.name, round(gap, 2))


def test_guide_pins_do_not_pierce_upper_parts(model):
    # ガイドピン（とねじの頭 φ4）は上段の板だけを貫き、板の上の部品とは重ならない
    # （見つかったこと：ばねを四隅に移した直後は、後ろのピンが GPS と DRV 基板を貫いていた）
    ps, _ = model
    for sx, sy in DESIGN.springs:
        for u in (p for p in ps if p.role == "upper" and p.name != "upper_plate"):
            inside_x = u.bbox_min[0] * 1000 - 2 < sx < u.bbox_max[0] * 1000 + 2
            inside_y = u.bbox_min[1] * 1000 - 2 < sy < u.bbox_max[1] * 1000 + 2
            assert not (inside_x and inside_y), (u.name, sx, sy)


def test_springs_sit_on_both_plates(model):
    # ばね（外径 7）の座が上段・下段の板の上に収まる（見つかったこと：x 87 だと前の端から 0.5〜2.5mm はみ出していた）
    ps, _ = model
    r = DESIGN.spring_od / 2
    for name in ("upper_plate", "lower_plate"):
        pl = next(p for p in ps if p.name == name)
        for sx, sy in DESIGN.springs:
            assert pl.bbox_min[0] * 1000 <= sx - r and sx + r <= pl.bbox_max[0] * 1000, (name, sx)
            assert pl.bbox_min[1] * 1000 <= sy - r and sy + r <= pl.bbox_max[1] * 1000, (name, sy)


def test_model_jumps_like_the_box_model(model):
    # 箱と円柱の近似（params の寸法と質量）は、下段が軽い今の構成では部品モデルより 2 割ほど高く跳ぶ
    # （部品モデル 41mm、箱 50mm）。レポートと判定は部品モデルを正とする。大きく離れたら近似の見直しが要る
    _, q = model
    assert scenarios.jump_in_place(q).lift_mm == pytest.approx(scenarios.jump_in_place(DESIGN).lift_mm, rel=0.25)


def test_tilt_option_fails_in_detailed_model(model):
    # 見つかったこと（2026-10-29）：部品モデルでは前傾 20°・500rpm の案は合格しない（その場ジャンプでも 10° 以上でひっくり返る）。
    # 箱の近似では 25mm で合格するので、前傾案を検討し直すときは部品モデルで見る。前傾案は採用していない
    _, q = model
    [w] = evaluate(q, [Option(20, "500rpm")], [20, 25, 30])
    assert all(n < PASS for n in w.rates.values()), w.rates
