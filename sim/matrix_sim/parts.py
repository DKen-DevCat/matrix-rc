"""Fusion から書き出した部品（STL＋parts.json）を読み、Params に反映する。

書き出しは sim/fusion/export_for_sim.py（Fusion の中で動かす）。部品の役割はコンポーネント名の頭で決める：

- upper_*  上段に載るもの（上段の板、電池、XIAO、LTE …）
- lower_*  下段に付くもの（下段の板、モーター、カム …）
- wheel_rl / wheel_rr / wheel_fl / wheel_fr  車輪（後ろ左・後ろ右・前左・前右）。後ろ左が左モーター、後ろ右が右モーター
- それ以外の名前は無視する（ねじなど。質量に効くものは upper_／lower_ を付ける）

座標は「x が前、y が左、z が上、原点は車体の後端・中心線・地面」、ばねが伸びきった状態で組む（sim/fusion/README.md）。
慣性は MuJoCo がメッシュの形と質量から計算する（部品ごとに密度一様、Fusion と同じ仮定）。
"""
from dataclasses import dataclass
import json
from pathlib import Path
import struct

import numpy as np

from .params import Params, Wheel

DRIVEN = {"wheel_rl": "left", "wheel_rr": "right", "wheel_fl": None, "wheel_fr": None}
SCALES = (1.0, 0.01, 0.001, 0.0254)  # m・cm・mm・inch → m


@dataclass(frozen=True)
class Part:
    name: str
    stl: Path
    mass: float               # kg
    com: tuple[float, float, float]        # m（Fusion の計算値。読み込みの検算に使う）
    bbox_min: tuple[float, float, float]   # m
    bbox_max: tuple[float, float, float]   # m
    stl_scale: float          # STL の座標 × これ ＝ m

    @property
    def role(self) -> str:
        if self.name in DRIVEN:
            return "wheel"
        for r in ("upper", "lower"):
            if self.name.startswith(r + "_"):
                return r
        return "ignore"

    @property
    def size(self) -> np.ndarray:
        return np.subtract(self.bbox_max, self.bbox_min)

    @property
    def center(self) -> np.ndarray:
        return (np.array(self.bbox_min) + np.array(self.bbox_max)) / 2


def read_stl_vertices(path: Path) -> np.ndarray:
    """バイナリ STL の頂点（n×3）。ASCII STL にも対応する。"""
    data = path.read_bytes()
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if len(data) == 84 + 50 * n:
            rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                                count=n, offset=84)
            return rec["v"].reshape(-1, 3).astype(float)
    words = data.decode("ascii", "replace").split()
    return np.array([[float(x) for x in words[i + 1:i + 4]] for i, w in enumerate(words) if w == "vertex"])


def infer_scale(stl_size: np.ndarray, bbox_size: np.ndarray) -> float:
    """STL の大きさと parts.json の大きさ（m）を比べて、STL の単位を当てる。"""
    ratio = float(np.max(bbox_size) / np.max(stl_size))
    best = min(SCALES, key=lambda s: abs(np.log(ratio / s)))
    if abs(np.log(ratio / best)) > 0.05:
        raise ValueError(f"STL の単位が分からない（比 {ratio:.5g}）")
    return best


def load_parts(folder: Path) -> list[Part]:
    folder = Path(folder)
    meta = json.loads((folder / "parts.json").read_text())
    parts = []
    for e in meta["parts"]:
        stl = folder / e["stl"]
        v = read_stl_vertices(stl)
        bmin, bmax = np.array(e["bbox_min"]), np.array(e["bbox_max"])
        scale = infer_scale(v.max(0) - v.min(0), bmax - bmin)
        parts.append(Part(e["name"], stl, e["mass"], tuple(e["com"]), tuple(bmin), tuple(bmax), scale))
    return parts


def apply(base: Params, parts: list[Part]) -> Params:
    """部品から寸法・質量・車輪の位置を Params に移す（ばね・モーター・摩擦は base のまま）。"""
    by = {r: [p for p in parts if p.role == r] for r in ("upper", "lower", "wheel")}
    missing = [r for r in ("upper", "lower") if not by[r]] + sorted(set(DRIVEN) - {p.name for p in by["wheel"]})
    if missing:
        raise ValueError(f"部品が足りない：{missing}")

    def extent(ps, axis):
        return (min(p.bbox_min[axis] for p in ps) * 1000, max(p.bbox_max[axis] for p in ps) * 1000)

    wheels, radius, width = [], 0.0, 0.0
    for p in sorted(by["wheel"], key=lambda p: p.name):
        c = p.center * 1000
        wheels.append(Wheel(float(c[0]), float(c[1]), DRIVEN[p.name]))
        radius = max(radius, p.size[2] * 500)
        width = max(width, p.size[1] * 1000)
    uy = extent(by["upper"], 1)
    return base.with_(
        upper_x=extent(by["upper"], 0), upper_z=extent(by["upper"], 2), width=uy[1] - uy[0],
        lower_x=extent(by["lower"], 0), lower_z=extent(by["lower"], 2),
        lower_width=float(np.subtract(*extent(by["lower"], 1)[::-1])),
        wheels=tuple(wheels), wheel_radius=radius, wheel_width=width,
        upper_mass=sum(p.mass for p in by["upper"]) * 1000,
        lower_mass=sum(p.mass for p in by["lower"] + by["wheel"]) * 1000,
        wheel_mass=sum(p.mass for p in by["wheel"]) * 1000 / len(by["wheel"]),
        parts=tuple(p for p in parts if p.role in ("upper", "lower")),
    )
