"""検証結果を docs/sim-report.md（表）と docs/sim/（CSV・コマ送りの画像）に書き出す。

    python -m matrix_sim.report           # 全部（数分かかる）
    python -m matrix_sim.report --quick   # ばらつきなし・粗い刻み（動作確認用）
"""
import argparse
import csv
import datetime
from pathlib import Path
import struct
import zlib

import mujoco
import numpy as np

from . import calibrate, cam, checks, parts, scenarios
from .build import front_x
from .params import N20_300RPM, DESIGN, Params
from .sweep import adopted_option, PASS, TRIALS, Option, evaluate

ROOT = Path(__file__).resolve().parents[2]
OUT_MD = ROOT / "docs" / "sim-report.md"
OUT_DIR = ROOT / "docs" / "sim"

# 採用案は前傾 0°・1000rpm（2026-10-28）。前傾 0° は走行モーター 4 種、前傾案は 300／500rpm で比較する
OPTIONS = [Option(0, m) for m in ("300rpm", "500rpm", "800rpm", "1000rpm")] + [Option(t, m) for t in (10, 15, 20) for m in ("300rpm", "500rpm")]
TRIGGERS = list(range(0, 61, 5))


def _png(path: Path, rgb: np.ndarray) -> None:
    """依存を増やさずに PNG を書く（RGB 8bit）。"""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def filmstrip(p: Params, trigger_mm: float, path: Path, times=(-0.05, 0.03, 0.08, 0.14, 0.22, 0.6)) -> None:
    """段差越えを横から見たコマ送り（発射の瞬間を 0 とした時刻）。"""
    step_x = front_x(p) / 1000 + scenarios.RUN_UP
    v = scenarios.Vehicle(p, step_x=step_x)
    v.throttle = p.throttle
    m, d = v.h.model, v.h.data
    r = mujoco.Renderer(m, 240, 320)
    cam_ = mujoco.MjvCamera()
    cam_.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam_.lookat[:] = [step_x, 0, 0.03]
    cam_.distance, cam_.azimuth, cam_.elevation = 0.32, 90, -5
    scenarios.run(v, 3.0, lambda v: not (v.front_x() >= step_x - trigger_mm / 1000))
    t0 = v.t
    frames = []
    # 発射前のコマは、発射の少し前に戻せないので「今」を使う（−0.05 は発射直前の姿勢とほぼ同じ）
    pending = sorted(times)
    while pending and pending[0] <= 0:
        r.update_scene(d, cam_); frames.append(r.render()); pending.pop(0)
    v.release()
    while pending:
        scenarios.run(v, pending[0] - (v.t - t0))
        r.update_scene(d, cam_); frames.append(r.render()); pending.pop(0)
    r.close()
    _png(path, np.concatenate(frames, axis=1))


def _pose(upright: float) -> str:
    return "水平" if upright > 0.9 else ("傾く" if upright > 0 else "ひっくり返る")


def build(quick: bool = False, base: Params = DESIGN, measured: tuple[str, ...] = (), source: str = "") -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trials = 1 if quick else TRIALS
    triggers = TRIGGERS[::2] if quick else TRIGGERS
    lines = [
        "# 物理演算による事前検証の結果",
        "",
        f"生成：{datetime.date.today()}（`cd sim && make report`）。数値の前提は `sim/matrix_sim/params.py`、限界は `sim/README.md`。",
        f"形状：{'部品モデル（' + source + '）' if base.parts else '箱と円柱の近似（図面 C3 の寸法）'}。"
        f"実測で置き換えた値：{'、'.join(measured) if measured else 'なし（モーターの特性・摩擦・接触の硬さは推定値。実測で合わせ込むまで目安として読む）'}。",
        "",
        f"## 1. 寸法の干渉（{'部品の外形' if base.parts else '図面 C3'}）",
        "",
    ]
    issues = checks.all_issues(base)
    lines += [f"- {i.what}（{i.overlap_mm:g}mm）" for i in issues] or ["- なし"]
    if base.parts:
        lines += ["", "重心（parts.json の値とメッシュから計算した値の差。2mm を超えたら、密度の違う部品を分けて書き出す）："]
        lines += [f"- {'上段' if r == 'upper' else '下段'}：{d:.1f}mm" + ("　**要確認**" if d > 2 else "")
                  for r, d in parts.com_mismatch_mm(base).items()]

    c = cam.analyze(base)
    lines += [
        "",
        "## 2. カムとジャンプ用モーター（計算）",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| 必要トルク（摩擦なし／摩擦込み） | {c.peak_torque_ideal:.3f} ／ {c.peak_torque:.3f} N·m |",
        f"| 高減速 N20 の停動トルク（{base.battery_v}V、{'実測' if 'jump_motor' in measured else '推定'}） | {c.stall_torque:.3f} N·m |",
        f"| 停動トルクに対する割合 | {c.margin * 100:.0f}%（基準 50% 以下） |",
        f"| チャージ時間（発射 → 次のチャージ完了） | {c.charge_time:.2f} 秒（目標 3〜4 秒） |",
        "",
        "## 3. その場ジャンプ（前傾角ごと）",
        "",
        f"走行モーターは採用案（{adopted_option(base).motor}）。"
        + "前傾 20° の着地は走行モーターの電気ブレーキ（逆起電力）の強さでも変わる："
        + "、".join(f"{name} だと{_pose(scenarios.jump_in_place(base.with_(tilt_deg=20, drive_motor=m)).upright)}"
                   for name, m in (("300rpm", N20_300RPM), (adopted_option(base).motor, base.drive_motor))) + "。",
        "",
        "| 前傾 | 車輪の上がった高さ | 滞空（1 回目） | 着地後の姿勢 | 上段の最大加速度（発射〜着地） |",
        "|---|---|---|---|---|",
    ]
    for tilt in (0, 10, 15, 20, 25, 30):
        j = scenarios.jump_in_place(base.with_(tilt_deg=tilt))
        lines.append(f"| {tilt}° | {j.lift_mm:.0f}mm | {j.airtime_s:.2f} 秒 | {_pose(j.upright)} | {j.peak_accel_g:.0f}g |")

    adopted = adopted_option(base)
    options = [adopted] + [o for o in OPTIONS if o != adopted]
    windows = evaluate(base, options, triggers, trials=trials)
    head = " | ".join(f"{t}" for t in triggers)
    lines += [
        "",
        f"## 4. 助走付きの段差越え（高さ {base.step_height:g}mm）",
        "",
        f"発射した瞬間の「車体の前端から段差までの距離」（mm）ごとに、{trials} 回中の成功回数。"
        + ("" if quick else f"ばらつき：床の摩擦 0.5〜1.0、上段の質量 ±10%、ばね ±10%、発射タイミング ±20ms。合格は {PASS} 回以上（設計書② 1章）。"),
        "「タイミングの幅」は合格する距離の幅を走行の速さで時間に直したもの。操作者がこの幅の中で Space を押す必要がある。",
        "",
        f"| 案 | 速さ | {head} | タイミングの幅 |",
        "|---|---|" + "---|" * len(triggers) + "---|",
    ]
    with open(OUT_DIR / "step_sweep.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["tilt_deg", "motor", "speed_mps", "trigger_mm", "successes", "trials"])
        for w in windows:
            cells = " | ".join(f"**{w.rates[t]}**" if w.rates[t] >= w.threshold else str(w.rates[t]) for t in triggers)
            lines.append(f"| {w.option.label} | {w.speed:.2f}m/s | {cells} | {w.window_ms:.0f}ms |")
            for t in triggers:
                wr.writerow([f"{w.option.tilt_deg:g}", w.option.motor, f"{w.speed:.3f}", t, w.rates[t], trials])

    lines += ["", "コマ送り（横から。発射の直前 → 0.03 → 0.08 → 0.14 → 0.22 → 0.6 秒後）：", ""]
    for o, t, name in ((adopted, 40, "step_current"), (Option(0, "300rpm"), 20, "step_old_300"), (Option(20, "500rpm"), 25, "step_tilt20_500")):
        filmstrip(o.params(base), t, OUT_DIR / f"{name}.png")
        lines += [f"- {o.label}、{t}mm 手前で発射", "", f"  ![{o.label}](sim/{name}.png)", ""]

    dr = scenarios.drop_test(base, 300)
    lines += [
        "## 5. 落下（30cm、設計書② 8章）",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| 上段の最大加速度 | {dr.peak_accel_g:.0f}g（上下段のストッパーと床の接触の硬さ＝推定値に強く依存する。基準値は実測後に決める） |",
        f"| 着地後の姿勢 | {'水平' if dr.upright > 0.9 else 'ひっくり返る'} |",
        f"| 跳ね返り | {dr.bounced_mm:.0f}mm（縮んだばねが伸び返す分。ばねの減衰と O リングの効果は推定） |",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--parts", type=Path, help="部品モデルのフォルダ（parts.json のある場所。make model が作る model/export など）")
    ap.add_argument("--measured", action="store_true", help="sim/calibration/*.csv の実測値を使う")
    a = ap.parse_args()
    base, measured = DESIGN, ()
    if a.measured:
        o = calibrate.overrides()
        base, measured = base.with_(**o), tuple(o)
    if a.parts:
        base = parts.apply(base, parts.load_parts(a.parts))
    OUT_MD.write_text(build(a.quick, base, measured, str(a.parts or "")))
    print(f"wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
