"""2026-10-28〜29 の設計判断を数値で固定する（真上跳び・車輪 φ32・電池 LP603449・ばねを四隅に・走行モーター Pololu 136:1 を一直線に）。

正本は params.py。図面（docs/drawings/src/d2.py）と結果（docs/sim-report.md）の数値が正本からずれたら落ちる。
"""
from pathlib import Path
import re

import pytest

from matrix_sim import checks, scenarios
from matrix_sim.params import DESIGN, N20_300RPM, N20_500RPM, N20_1000RPM, N20_LENGTH, POLOLU_136, POLOLU_136_LENGTH, REQUIRED_RUN_SPEED
from matrix_sim.report import OPTIONS
from matrix_sim.sweep import MOTORS, Option, adopted_option

ROOT = Path(__file__).resolve().parents[2]
D2 = ROOT / "docs" / "drawings" / "src" / "d2.py"
REPORT = ROOT / "docs" / "sim-report.md"



# ---- 走行モーター ----

def test_adopted_drive_motor_is_pololu_136():
    # 2026-10-29：N20 1000rpm（前後にずらす）から、Pololu 136:1 6mm 遊星（左右を一直線）に変更
    assert DESIGN.drive_motor is POLOLU_136
    assert DESIGN.throttle == 1.0   # 6V 定格を 1S で回すので速度の上限を 1.0（ファームの env:xiao_1b）


def test_adopted_drive_speed_exceeds_requirement():
    v = DESIGN.drive_speed()
    assert v > REQUIRED_RUN_SPEED
    assert v == pytest.approx(0.52, abs=0.01)  # 500rpm × 3.7V/6V × 1.0 × φ32


def test_old_drive_motor_was_too_slow_for_a_vertical_jump():
    assert DESIGN.with_(drive_motor=N20_300RPM).drive_speed() < REQUIRED_RUN_SPEED


def test_drive_motors_fit_in_line_between_the_rear_wheels():
    # 走行モーター 2 個（Pololu 136:1 は 19mm、N20 は 24mm）を一直線に並べられるか。車輪の内側の面の間は 41mm
    inner = 2 * (abs(DESIGN.wheels[0].y) - DESIGN.wheel_width / 2)
    assert 2 * POLOLU_136_LENGTH <= inner - 2 * 0.5   # Pololu：38mm、車輪との間に 0.5mm ずつ
    assert 2 * N20_LENGTH > inner                       # N20 は収まらない（だから前後にずらしていた）


def test_rear_wheels_are_aligned():
    rl, rr = DESIGN.wheels[0], DESIGN.wheels[1]
    assert rl.x == rr.x and rl.driven == "left" and rr.driven == "right"


def test_sweep_compares_adopted_motor_with_old_ones():
    assert {"300rpm", "500rpm", "800rpm", "1000rpm"} <= set(MOTORS)
    assert MOTORS["1000rpm"] is N20_1000RPM


def test_report_always_shows_adopted_and_old_option():
    # 採用案と、それが要った理由（旧 300rpm では越えない）が同じ表に並ぶこと
    assert adopted_option(DESIGN) == Option(0, "Pololu136")
    assert Option(0, "300rpm") in OPTIONS


def test_adopted_option_follows_measured_motor():
    # 実測で走行モーターを置き換えたら、採用案の行とコマ送りはそのモーターで動く（MOTORS の固定値に戻らない）
    measured = N20_1000RPM.__class__(rated_v=3.7, no_load_rpm=520, stall_torque=0.01)
    o = adopted_option(DESIGN.with_(drive_motor=measured))
    assert o.motor == "実測"
    assert o.params(DESIGN.with_(drive_motor=measured)).drive_motor is measured


def test_reflected_inertia_uses_6v_equivalent_rpm():
    # 実測のモーターは電池電圧が定格になる。3.7V で 617rpm の 1000rpm 級は、6V 定格の 1000rpm と同じ慣性
    measured = N20_1000RPM.__class__(rated_v=3.7, no_load_rpm=1000 * 3.7 / 6.0, stall_torque=0.011)
    assert measured.reflected_inertia == pytest.approx(N20_1000RPM.reflected_inertia, rel=1e-6)


def test_reflected_inertia_scales_with_gear_ratio():
    # 1000rpm 級は 300rpm（100:1）より減速比が小さいので、車輪から見たロータの慣性も小さい
    assert N20_1000RPM.reflected_inertia < N20_500RPM.reflected_inertia < N20_300RPM.reflected_inertia
    assert N20_300RPM.reflected_inertia == pytest.approx(2e-6)


# ---- 上段の高さ ----

def test_compressed_upper_deck_clears_wheels_by_2mm():
    bottom_when_compressed = DESIGN.upper_z[0] - DESIGN.stroke
    assert bottom_when_compressed - 2 * DESIGN.wheel_radius == pytest.approx(2.0)
    assert checks.all_issues(DESIGN) == []


def test_springs_are_preloaded_and_stroke_fits_in_gap():
    gap = DESIGN.upper_z[0] - DESIGN.lower_z[1]
    assert gap == pytest.approx(21.0)
    assert gap < DESIGN.spring_free_length  # 伸びきりでもばねは縮んでいる（がたつかない）
    assert gap - DESIGN.stroke >= 2.0       # 縮めきっても上下段がぶつからない


def test_raising_the_deck_did_not_change_jump_height():
    # ばねのエネルギーは同じなので、上段を 6mm 上げても跳躍高さは変わらないはず
    old = DESIGN.with_(upper_z=(38.0, 52.0))
    assert scenarios.jump_in_place(DESIGN).lift_mm == pytest.approx(scenarios.jump_in_place(old).lift_mm, rel=0.05)


def test_wheels_fit_inside_the_business_card_outline():
    # φ32×7 の車輪が、名刺サイズ（91×55）の外形からはみ出さない
    R, ww = DESIGN.wheel_radius, DESIGN.wheel_width
    assert min(w.x for w in DESIGN.wheels) - R >= 0
    assert max(w.x for w in DESIGN.wheels) + R <= DESIGN.length
    assert max(abs(w.y) for w in DESIGN.wheels) + ww / 2 <= DESIGN.width / 2


def test_lower_plate_clears_wheel_inner_faces():
    # 下段の板の端と車輪の内側の面に 1mm のすき間（見つかったこと：幅 41 のままだと φ32×7 の内側の面に 0mm で当たっていた）
    inner = min(abs(w.y) - DESIGN.wheel_width / 2 for w in DESIGN.wheels)
    assert inner - DESIGN.lower_width / 2 >= 1.0


def test_springs_clear_wheels():
    # 見つかったこと（2026-10-29）：電池（幅 34.5）を板の裏に置くと、旧位置（x 36/68、y ±17.5）のばねと重なる。
    # 四隅に寄せたばねは、車輪の内側の面にも当たらない
    r = DESIGN.spring_od / 2
    for sx, sy in DESIGN.springs:
        for w in DESIGN.wheels:
            in_x = abs(sx - w.x) < DESIGN.wheel_radius + r
            inner_face = abs(w.y) - DESIGN.wheel_width / 2
            if in_x and (sy > 0) == (w.y > 0):
                assert abs(sy) + r <= inner_face, (sx, sy, w)


def test_total_mass_after_motor_change():
    # 部品を型番どおりにして 127g、走行モーターを 1.25g の 6mm 遊星にして 109.5g（設計書② 4章）
    assert DESIGN.total_mass == pytest.approx(109.5)


# ---- 図面と結果が正本と合っていること ----

def test_c3_drawing_uses_params_dimensions():
    # C3 の描画スクリプト（d2.py の c3）の先頭に置いた寸法が、正本の params と一致する
    src = D2.read_text()
    c3 = src[src.index("def c3():"):src.index("def c4():")]
    ns = {}
    for line in c3.splitlines():
        line = line.strip()
        if line.startswith(("R, WW =", "rearL, rearR, front =", "WY =", "LZ0, LZ1 =", "UZ0, UZ1 =", "SPRINGS =")):
            exec(line.split("#")[0], {}, ns)
    assert (ns["R"], ns["WW"]) == (DESIGN.wheel_radius, DESIGN.wheel_width), "C3 の車輪"
    assert [ns["rearL"], ns["rearR"], ns["front"]] == [w.x for w in DESIGN.wheels[:3]], "C3 の車輪の前後位置"
    assert ns["WY"] == abs(DESIGN.wheels[0].y), "C3 の車輪の左右位置"
    assert (ns["LZ0"], ns["LZ1"]) == DESIGN.lower_z, "C3 の下段の高さ"
    assert (ns["UZ0"], ns["UZ1"]) == DESIGN.upper_z, "C3 の上段の高さ"
    assert sorted(ns["SPRINGS"]) == sorted(DESIGN.springs), "C3 のばねの位置"


def test_c4_drawing_states_adopted_drive_motor():
    src = D2.read_text()
    assert "Pololu 136:1" in src
    assert "真上に跳ぶ" in src


def test_committed_report_matches_params():
    # 既定（3D モデル、または箱と円柱・推定値）で作ったレポートなら、採用案の行の速さと干渉の結果が params と一致すること。
    # --measured で作り直したレポートは前提が違うので、ここでは見ない
    text = REPORT.read_text()
    if "実測で置き換えた値：なし" not in text:
        pytest.skip("レポートが実測値で作られている")
    assert "部品モデル（model/export）" in text or "箱と円柱の近似" in text, "レポートの形状が既定（make report / report-box）でない"
    assert "- なし" in text.split("## 2.")[0], "干渉の結果が params と違う（make report を実行し直す）"
    o = adopted_option(DESIGN)
    row = re.search(rf"^\| {re.escape(o.label)} \| ([\d.]+)m/s \|", text, re.M)
    assert row, "採用案の行がレポートにない（make report を実行し直す）"
    assert float(row.group(1)) == pytest.approx(DESIGN.drive_speed(), abs=0.01)
