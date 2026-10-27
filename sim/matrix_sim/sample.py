"""Fusion の書き出しと同じ形（STL＋parts.json）を、今の箱と円柱のモデルから作る。

Fusion がない環境でも読み込みの流れを試せるようにするための見本（sim/fusion/sample/）。
STL は Fusion の既定と同じ mm 単位のバイナリで書く。

    python -m matrix_sim.sample sim/fusion/sample
"""
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np

from .params import DESIGN, Params


def box(lo, hi) -> np.ndarray:
    """直方体の三角形（12×3×3）。外向きの面。"""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    f = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4),
         (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2), (1, 3, 7), (1, 7, 5)]
    return v[np.array(f)]


def cylinder_y(center, r, width, n=48) -> np.ndarray:
    """軸が y 向きの円柱の三角形。"""
    cx, cy, cz = center
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    ring = np.stack([cx + r * np.cos(a), np.zeros(n), cz + r * np.sin(a)], 1)
    left, right = ring + [0, cy + width / 2, 0], ring + [0, cy - width / 2, 0]
    cl, cr = np.array([cx, cy + width / 2, cz]), np.array([cx, cy - width / 2, cz])
    tris = []
    for i in range(n):
        j = (i + 1) % n
        tris += [(left[i], right[i], right[j]), (left[i], right[j], left[j]),
                 (cl, left[j], left[i]), (cr, right[i], right[j])]
    return np.array(tris)


def outward(tris: np.ndarray) -> np.ndarray:
    """閉じた三角形の集まりの向きを外向きにそろえる（符号付き体積が正になるように）。"""
    vol = np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6
    return tris if vol > 0 else tris[:, [0, 2, 1]]


def read_tris(path: Path) -> np.ndarray:
    from .parts import read_stl_vertices
    return read_stl_vertices(path).reshape(-1, 3, 3)


def write_stl(path: Path, tris: np.ndarray) -> None:
    out = [b"matrix-rc sample".ljust(80, b"\0"), struct.pack("<I", len(tris))]
    for t in tris:
        nrm = np.cross(t[1] - t[0], t[2] - t[0])
        nrm = nrm / (np.linalg.norm(nrm) or 1)
        out.append(struct.pack("<12fH", *nrm, *t.ravel(), 0))
    path.write_bytes(b"".join(out))


def make(folder: Path, p: Params = DESIGN) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ly = p.lower_width / 2
    shapes = {
        "upper_deck": (box((p.upper_x[0], -p.width / 2, p.upper_z[0]), (p.upper_x[1], p.width / 2, p.upper_z[1])), p.upper_mass),
        "lower_deck": (box((p.lower_x[0], -ly, p.lower_z[0]), (p.lower_x[1], ly, p.lower_z[1])),
                       p.lower_mass - p.wheel_mass * len(p.wheels)),
    }
    names = {("left", True): "wheel_rl", ("right", True): "wheel_rr", (True, False): "wheel_fl", (False, False): "wheel_fr"}
    for w in p.wheels:
        name = names[(w.driven, True)] if w.driven else names[(w.y > 0, False)]
        shapes[name] = (cylinder_y((w.x, w.y, p.wheel_radius), p.wheel_radius, p.wheel_width), p.wheel_mass)
    entries = []
    for name, (tris, grams) in shapes.items():
        tris = outward(tris)
        write_stl(folder / f"{name}.stl", tris)
        v = tris.reshape(-1, 3) / 1000
        entries.append({
            "name": name, "stl": f"{name}.stl", "mass": grams / 1000,
            "com": list((v.min(0) + v.max(0)) / 2),
            "bbox_min": list(v.min(0)), "bbox_max": list(v.max(0)),
        })
    (folder / "parts.json").write_text(json.dumps(
        {"source": "matrix_sim.sample（箱と円柱の見本）", "units": "kg, m", "parts": entries}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    make(Path(sys.argv[1] if len(sys.argv) > 1 else "fusion/sample"))
