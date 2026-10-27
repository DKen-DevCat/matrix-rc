# 物理演算の検証環境（README.md を参照）
PY := .venv/bin/python

.PHONY: setup test report report-quick calibrate sample view

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

# ARGS="--parts fusion/export"（Fusion の形状）や ARGS="--measured"（実測値）を足せる
report:
	$(PY) -m matrix_sim.report $(ARGS)

report-quick:
	$(PY) -m matrix_sim.report --quick $(ARGS)

# calibration/*.csv の実測値で何が置き換わるかを表示する
calibrate:
	$(PY) -m matrix_sim.calibrate

# Fusion の書き出しの見本（fusion/sample）を作り直す。params.py を変えたら実行する
sample:
	$(PY) -m matrix_sim.sample fusion/sample

# macOS ではウィンドウ表示に mjpython が要る
view:
	.venv/bin/mjpython -m matrix_sim.view $(ARGS)
