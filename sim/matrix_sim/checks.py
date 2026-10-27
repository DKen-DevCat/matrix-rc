"""図面の寸法だけで分かる干渉の確認（物理演算の前に見る）。"""
from dataclasses import dataclass

from .params import Params


@dataclass(frozen=True)
class Issue:
    what: str
    overlap_mm: float


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return min(a[1], b[1]) - max(a[0], b[0])


def compressed_upper_vs_wheels(p: Params) -> list[Issue]:
    """ばねを縮めきったとき、上段の下面がタイヤの上端より下に来ないか。

    上段は幅いっぱい（タイヤの真上を覆う）なので、平面で重なる車輪があれば高さで比べる。
    """
    bottom = p.upper_z[0] - p.stroke
    issues = []
    for i, w in enumerate(p.wheels):
        in_x = _overlap(p.upper_x, (w.x - p.wheel_radius, w.x + p.wheel_radius)) > 0
        in_y = _overlap((-p.width / 2, p.width / 2), (w.y - p.wheel_width / 2, w.y + p.wheel_width / 2)) > 0
        top = 2 * p.wheel_radius
        if in_x and in_y and top > bottom:
            issues.append(Issue(f"縮めた上段の下面（{bottom:g}mm）が車輪{i}の上端（{top:g}mm）に当たる", top - bottom))
    return issues


def all_issues(p: Params) -> list[Issue]:
    return compressed_upper_vs_wheels(p)
