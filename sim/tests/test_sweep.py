"""成功率の表から「タイミングの幅」を出す計算。"""
import pytest

from matrix_sim.sweep import Option, Window


def _w(rates):
    return Window(Option(20, "300rpm"), rates, speed=0.2)


def test_window_is_measured_span_of_passing_distances():
    # 15・20・25mm が合格 → 幅 10mm、0.2m/s で 50ms
    w = _w({10: 5, 15: 8, 20: 10, 25: 9, 30: 3})
    assert w.window_ms == pytest.approx(50)


def test_window_uses_longest_contiguous_run():
    # 間に不合格を挟む合格は余裕に数えない
    w = _w({10: 9, 15: 2, 20: 9, 25: 9, 30: 9, 35: 1})
    assert w.window_ms == pytest.approx(50)


def test_single_passing_distance_has_zero_width():
    assert _w({10: 3, 15: 8, 20: 3}).window_ms == 0
    assert _w({10: 3, 15: 3}).window_ms == 0
