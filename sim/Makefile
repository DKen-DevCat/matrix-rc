# 物理演算の検証環境（README.md を参照）
PY := .venv/bin/python

.PHONY: setup test report report-quick calibrate sample view model

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

# 既定は 3D モデル（model/export）の形と質量。ARGS="--measured"（実測値）を足せる。箱と円柱の近似は report-box
report:
	$(PY) -m matrix_sim.report --parts model/export $(ARGS)

report-quick:
	$(PY) -m matrix_sim.report --quick --parts model/export $(ARGS)

report-box:
	$(PY) -m matrix_sim.report $(ARGS)

# 機体の 3D モデルを Blender でコードから組み、model/export（STL＋parts.json）と docs/model（図）を作り直す
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
model:
	$(BLENDER) -b --python model/build_model.py -- --out model/export --render ../docs/model

# calibration/*.csv の実測値で何が置き換わるかを表示する
calibrate:
	$(PY) -m matrix_sim.calibrate

# Fusion の書き出しの見本（fusion/sample）を作り直す。params.py を変えたら実行する
sample:
	$(PY) -m matrix_sim.sample fusion/sample

# macOS ではウィンドウ表示に mjpython が要る。既定は採用案（前傾 0°・1000rpm）を 3D モデルで
view:
	.venv/bin/mjpython -m matrix_sim.view --parts model/export $(ARGS)
