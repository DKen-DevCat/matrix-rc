# sim — 物理演算による事前検証

作る前に「図面どおりに動くか」を確かめるための環境。MuJoCo（無料の物理エンジン）で機体を箱と円柱に近似して動かし、設計書②の合格基準をテストとして判定する。結果は [docs/sim-report.md](../docs/sim-report.md)。

**シミュレーションは試作の代わりではない。** 明らかな失敗を作る前に潰し、試作で確かめることを絞るためのもの。モーターの特性・摩擦・接触の硬さは推定値で、Phase 1-a の部品で実測して合わせ込むまでは「傾向」として読む。

## 使い方

```sh
cd sim
make setup         # .venv を作って mujoco などを入れる（Python 3.10 以上。3.14 で確認）
make test          # 全テスト（10 秒ほど）
make report        # docs/sim-report.md と docs/sim/ を作り直す（数分）
make report-quick  # ばらつきなしの粗い版（10 秒ほど）
make report ARGS="--parts fusion/export"   # Fusion で組んだ形で作り直す（fusion/README.md）
make report ARGS="--measured"              # calibration/*.csv の実測値で作り直す
make calibrate     # 実測値で何が置き換わるかを表示する
make view ARGS="--tilt 20 --motor 500rpm --trigger 25"   # ウィンドウで見る（macOS は mjpython）
```

## 何を確かめるか

| 対象 | 方法 | 合格の基準（出典） |
|---|---|---|
| 寸法の干渉 | 図面の寸法だけで計算（`checks.py`） | 干渉なし（C3） |
| カムのトルク・チャージ時間 | 準静的な計算（`cam.py`） | 停動トルクの 50% 以下、3〜4 秒（C4・設計書② 7章） |
| その場ジャンプ | 物理演算（`scenarios.jump_in_place`） | 車輪が 40mm 以上上がる（C4） |
| 段差越え | 物理演算（`scenarios.step_climb`）＋ばらつき 10 通り（`sweep.py`） | 助走付きで 30mm を越える、10 回中 8 回以上（設計書② 1章） |
| 落下 | 物理演算（`scenarios.drop_test`） | 30cm から落として転倒しない。加速度は記録だけ（設計書② 8章） |

シミュレーション自体の正しさは `tests/test_physics_sanity.py` で解析解と比べて確かめている（自由落下の時間、ばね質量系の周期とエネルギー、走行速度とモーターの式、運動量から求めた跳躍高さの上限、時間刻みを半分にしても結果が変わらないこと）。

## 構成

| ファイル | 中身 |
|---|---|
| `matrix_sim/params.py` | 寸法・質量・ばね・モーター・摩擦の**正本**。出典と「推定」の区別を書く |
| `matrix_sim/build.py` | params → MuJoCo のモデル（MJCF） |
| `matrix_sim/scenarios.py` | その場ジャンプ・段差越え・落下 |
| `matrix_sim/cam.py` | カムのトルクとチャージ時間 |
| `matrix_sim/checks.py` | 寸法だけで分かる干渉 |
| `matrix_sim/sweep.py` | 設計案（前傾角 × 走行モーター）× 発射距離の総当たりと成功率 |
| `matrix_sim/report.py` | 結果の表・CSV・コマ送り画像 |
| `matrix_sim/view.py` | ウィンドウ表示 |
| `matrix_sim/parts.py` | Fusion の書き出し（STL＋parts.json）を読み、寸法・質量・車輪の位置を params に移す |
| `matrix_sim/sample.py` | 書き出しの見本（`fusion/sample/`）を箱と円柱のモデルから作る |
| `matrix_sim/calibrate.py` | 実測値（`calibration/*.csv`）で推定値を置き換える |
| `fusion/export_for_sim/` | Fusion の中で動かす書き出しスクリプト（手順は `fusion/README.md`） |

## モデルの前提と限界

- 車体は箱、タイヤは円柱。上段は下段に対してガイドピンの向き（前傾角）に沿ってだけ動く。ばね 4 本はその関節の剛性（合計 2000N/m）と、伸びきりのストッパーで表す
- ばねは「縮めきった状態をカムが保持している」ところから始め、発射の瞬間に保持の力を外す。カム形状との接触はまだ入れていない（カムの寸法が決まってから足す）
- 上下段のストッパーは関節の可動範囲で表し、硬さは `stop_timeconst`（推定）。上段と下段は親子の関係なので、ストッパーを越えてもぶつかり合いは計算しない（テストで 1.5mm 以内に収まることを確かめている）
- 走行モーターは直線モデル（トルク ＝ 停動トルク × デューティ − 逆起電力の項）。速度上限はファームの `MAX_DUTY` 0.8
- 上段と車輪の衝突は外している（図面どおりだと縮めたときに当たるため。`checks.py` で別に報告する）
- 接触の硬さ（`contact_timeconst`）と摩擦は推定。落下時の加速度はこれに強く依存する

## 合わせ込み（Phase 1-a の部品が届いたら）

`calibration/` の CSV に実測値を書き足し、`make calibrate` で何が置き換わるかを見て、`make report ARGS="--measured"` で結果を作り直す。CSV に行がなければ推定値のまま。

| CSV | 測るもの | 道具 |
|---|---|---|
| `motor.csv` | 走行用（`drive`）とジャンプ用（`jump`）の N20：電池電圧での無負荷の回転数と、軸に付けた腕でキッチンスケールを押して止めたときの表示 | スマホのスロー撮影、キッチンスケール、2cm 程度の腕 |
| `spring.csv` | ばね 1 本の、縮めた量と力 | キッチンスケール、ノギス |
| `friction.csv` | 4 輪をテープで止めた機体を板に載せ、傾けて滑り始める角度（床の種類ごと） | 板、スマホの傾き計、テープ |

床の摩擦は、測った中でいちばん滑りやすい床の値を使う（厳しい側で判定する）。
