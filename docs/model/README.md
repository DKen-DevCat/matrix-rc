# 3D モデルの図

`cd sim && make model` で `sim/model/build_model.py` が作り直す（Blender）。PNG を直接いじらない。

| ファイル | 中身 |
|---|---|
| `iso.png` | 斜めから |
| `side.png` | 左から（伸びた状態） |
| `side_compressed.png` | 左から（ばねを 10mm 縮めた状態。上段の部品がタイヤ・下段に当たらないことを見る） |
| `top.png` | 上から |
| `front.png` | 前から |

部品の置き場所と質量は `sim/model/build_model.py` の PARTS 表、物理演算に読ませた結果は `docs/sim-report.md`。
