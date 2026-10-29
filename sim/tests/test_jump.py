"""その場ジャンプと落下（設計書② 7章・8章）。"""
from matrix_sim import scenarios
from matrix_sim.params import DESIGN, N20_300RPM


def test_design_jumps_and_lands_upright():
    # C4 の目標は 4cm 以上（見積もり 4〜6cm）。2026-10-29 に部品を型番どおりにして 127g になり 37mm 前後に下がった
    # （目標との差は test_design_decisions.test_heavier_build_jumps_lower_than_c4_target に固定）
    r = scenarios.jump_in_place(DESIGN)
    assert 30 <= r.lift_mm <= 60
    assert r.upright > 0.95


def test_tilt_trades_height_for_forward_speed():
    flat = scenarios.jump_in_place(DESIGN).lift_mm
    tilted = scenarios.jump_in_place(DESIGN.with_(tilt_deg=20)).lift_mm
    assert tilted < flat


def test_tilt_up_to_15_degrees_lands_upright():
    for tilt in (10, 15):
        assert scenarios.jump_in_place(DESIGN.with_(tilt_deg=tilt)).upright > 0.9, tilt


def test_tilt_25_degrees_and_more_tips_over():
    # 見つかったこと：上段を 6mm 上げた（2026-10-28）ことで重心が上がり、前傾 20° のその場ジャンプは境目になった
    # （走行モーターの電気ブレーキの強さで、300rpm だと鼻から落ち、1000rpm だと立つ。境目なので固定せず、レポート 3 章に注記する）。
    # 25° 以上は走行モーターによらずひっくり返る（箱と円柱の近似で見た結果。部品モデルは 25° でも立つ：docs/sim-report.md の 3 章）
    for m in (N20_300RPM, DESIGN.drive_motor):
        assert scenarios.jump_in_place(DESIGN.with_(tilt_deg=25, drive_motor=m)).upright < 0.5
        assert scenarios.jump_in_place(DESIGN.with_(tilt_deg=30, drive_motor=m)).upright < 0


def test_drop_from_300mm_lands_upright():
    # 設計書② 8章：30cm から落とす。加速度の基準値は 1-a の実測後に決める（今は記録だけ）
    r = scenarios.drop_test(DESIGN, 300)
    assert r.upright > 0.9
    assert 0 < r.peak_accel_g < 500


def _lift_extremes(p, run):
    """lift 関節の最小・最大（m）を記録しながら run(v) を回す。"""
    v = scenarios.Vehicle(p, z0=0.3, charged=False) if run == "drop" else scenarios.Vehicle(p)
    lo, hi = 0.0, -1.0

    def watch(v):
        nonlocal lo, hi
        q = v.h.data.qpos[v.h.lift_q]
        lo, hi = min(lo, q), max(hi, q)

    if run == "jump":
        scenarios.run(v, 0.2)
        v.release()
    scenarios.run(v, 1.0, watch)
    return lo * 1000, hi * 1000


def test_stops_hold_the_stroke_on_jump_and_drop():
    # ストッパーは硬い：伸びきり・縮めきりを 2mm 以上越えない（O リングのつぶれ程度）。
    # 2026-10-29 に上段が 60→68g になり、30cm 落下で縮めきりを 1.6mm 越えるようになった（それまでは 1.5mm 以内）。
    # 越えても電池の下面はカムの上面から 0.7mm 以上離れている
    for run in ("jump", "drop"):
        lo, hi = _lift_extremes(DESIGN, run)
        assert lo > -DESIGN.stroke - 2.0, (run, lo)
        assert hi < 1.5, (run, hi)


def test_airtime_is_first_flight_only():
    # 1 回目の離陸から 1 回目の着地まで。ひっくり返って寝ている時間や跳ね返りは数えない
    r = scenarios.jump_in_place(DESIGN)
    assert 0.1 < r.airtime_s < 0.25
    flipped = scenarios.jump_in_place(DESIGN.with_(tilt_deg=30))
    assert flipped.airtime_s < 0.3
