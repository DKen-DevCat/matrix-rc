"""図面の寸法だけで分かる干渉の確認（物理演算の前に見る）。

部品モデル（parts）があれば部品の外形ごとに、なければ箱の寸法で見る。
"""
from dataclasses import dataclass

from .params import Params


@dataclass(frozen=True)
class Issue:
    what: str
    overlap_mm: float


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return min(a[1], b[1]) - max(a[0], b[0])


def _boxes(p: Params, role: str) -> list[tuple[str, tuple, tuple, tuple]]:
    """(名前, x範囲, y範囲, z範囲) mm。部品があれば部品ごと、なければ箱 1 つ。"""
    if p.parts:
        return [(q.name, (q.bbox_min[0] * 1000, q.bbox_max[0] * 1000), (q.bbox_min[1] * 1000, q.bbox_max[1] * 1000),
                 (q.bbox_min[2] * 1000, q.bbox_max[2] * 1000)) for q in p.parts if q.role == role and not q.passes_through]
    if role == "upper":
        return [("上段", p.upper_x, (-p.width / 2, p.width / 2), p.upper_z)]
    return [("下段", p.lower_x, (-p.lower_width / 2, p.lower_width / 2), p.lower_z)]


def compressed_upper_vs_wheels(p: Params) -> list[Issue]:
    """ばねを縮めきったとき、上段（の各部品）の下面がタイヤの上端より下に来ないか。平面で重なる車輪だけ比べる。"""
    issues = []
    top = 2 * p.wheel_radius
    for name, xr, yr, zr in _boxes(p, "upper"):
        bottom = zr[0] - p.stroke
        for i, w in enumerate(p.wheels):
            in_x = _overlap(xr, (w.x - p.wheel_radius, w.x + p.wheel_radius)) > 0
            in_y = _overlap(yr, (w.y - p.wheel_width / 2, w.y + p.wheel_width / 2)) > 0
            if in_x and in_y and top > bottom:
                issues.append(Issue(f"縮めた{name}の下面（{bottom:g}mm）が車輪{i}の上端（{top:g}mm）に当たる", top - bottom))
    return issues


def compressed_upper_vs_lower(p: Params) -> list[Issue]:
    """ばねを縮めきったとき、上段の部品が下段の部品に食い込まないか。貫通部品（parts.json の passes_through）は除く。"""
    issues = []
    for un, ux, uy, uz in _boxes(p, "upper"):
        uz = (uz[0] - p.stroke, uz[1] - p.stroke)
        for ln, lx, ly, lz in _boxes(p, "lower"):
            d = min(_overlap(ux, lx), _overlap(uy, ly), _overlap(uz, lz))
            if d > 0:
                issues.append(Issue(f"縮めた{un}（下面 {uz[0]:g}mm）が{ln}（上面 {lz[1]:g}mm）に食い込む", d))
    return issues


def all_issues(p: Params) -> list[Issue]:
    return compressed_upper_vs_wheels(p) + compressed_upper_vs_lower(p)
