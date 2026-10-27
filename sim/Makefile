# 物理演算の検証環境（README.md を参照）
PY := .venv/bin/python

.PHONY: setup test report report-quick view

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

report:
	$(PY) -m matrix_sim.report

report-quick:
	$(PY) -m matrix_sim.report --quick

# macOS ではウィンドウ表示に mjpython が要る
view:
	.venv/bin/mjpython -m matrix_sim.view $(ARGS)
