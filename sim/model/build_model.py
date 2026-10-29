"""機体の 3D モデルを Blender でコードから組み、物理演算が読む形（STL＋parts.json）と図を書き出す。

    cd sim && make model        # = blender -b --python model/build_model.py -- --out model/export --render ../docs/model

寸法の正本は matrix_sim/params.py（車体・車輪・上下段の高さ）と、この中の PARTS 表（部品の置き場所と質量）。
質量は設計書②の 4 章「重量の見積もり」を部品に割り振ったもので、実物を量ったら PARTS の値を直す。
座標は sim/fusion/README.md と同じ：x が前、y が左、z が上。原点は車体の後端・左右の中心線・地面。ばねは伸びきった状態。
部品名の頭（upper_／lower_／wheel_）で役割を決める（matrix_sim/parts.py）。

Fusion で組みたいときは、書き出した STL を読み込めばよい（任意）。
"""
import json
import math
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from matrix_sim.params import DESIGN  # noqa: E402

P = DESIGN
MM = 1.0  # Blender の 1 単位を 1mm として組む（STL は mm、parts.json は m）

# ---- 色（図用）
C_PLATE_U, C_PLATE_L = (0.72, 0.82, 0.98, 1), (0.80, 0.82, 0.86, 1)
C_BATT, C_BOARD, C_MOTOR, C_WHEEL, C_METAL, C_CAM, C_SPRING = (0.95, 0.65, 0.30, 1), (0.30, 0.55, 0.35, 1), (0.35, 0.35, 0.40, 1), (0.20, 0.20, 0.22, 1), (0.75, 0.75, 0.78, 1), (0.85, 0.30, 0.30, 1), (0.55, 0.40, 0.85, 1)

W = P.width / 2            # 27.5
UZ0, UZ1 = P.upper_z       # 上段の板の下面・上面の目安（params。板の上に部品が載る）
LZ0, LZ1 = P.lower_z       # 下段の下面・上面
PLATE = 2.0                # 板の厚み mm
REAR_L, REAR_R, FRONT = P.wheels[0], P.wheels[1], P.wheels[2]
R, WW = P.wheel_radius, P.wheel_width
AXLE_Z = R                 # 車軸の高さ（車輪の中心）
TOP = UZ0 + PLATE          # 上段の板の上面

# N20 ギアモーター：断面 12（幅）×10（高さ）、缶 15mm＋ギアボックス 9mm、3mm の D 軸。合計 約 10g（缶 6.5g、ギア 3.5g、推定）
N20_W, N20_H, N20_CAN, N20_GEAR = 12.0, 10.0, 15.0, 9.0
MZ = (AXLE_Z - N20_H / 2, AXLE_Z + N20_H / 2)          # 走行モーターの高さ（軸を車輪の中心に合わせる）
L_IN = REAR_L.y - WW / 2                               # 左後輪の内側の面
R_IN = REAR_R.y + WW / 2                               # 右後輪の内側の面（負）

# ---- 部品表：(名前, 形, 質量 g, 色, 出典)
# 形は ("box", (x0,x1), (y0,y1), (z0,z1)) か ("cyl_y", cx, (y0,y1), cz, r) か ("cyl_z", cx, cy, (z0,z1), r) か ("cyls_z", [(x,y)...], (z0,z1), r)
# 出典の「推定」は実物を量ったら直す（make model → make report で作り直す）
PARTS = [
    # ---- 上段
    ("upper_plate",   ("box", (P.upper_x[0], P.upper_x[1]), (-W, W), (UZ0, TOP)), 20.0, C_PLATE_U, "推定（樹脂の板 約 12g＋配線）"),
    ("upper_battery", ("box", (11.0, 62.0), (-17.25, 17.25), (UZ0 - 6.3, UZ0)), 23.0, C_BATT,
     "EEMB LP603449-PCM-LD：34.5×51×6.3mm、セル 22g（メーカー）＋保護回路とリード 約 1g（推定）。板の裏、四隅のばねの内側"),
    ("upper_xiao",    ("box", (68.0, 85.8), (-10.5, 10.5), (TOP, TOP + 9.0)), 5.0, C_BOARD, "XIAO ESP32S3 Sense：21×17.8mm の 2 段重ね、高さ 約 9mm、5g（推定）"),
    ("upper_lte",     ("box", (31.0, 63.0), (-16.0, 16.0), (TOP, TOP + 6.0)), 12.0, C_BOARD, "LTE ボード＋アンテナ：30×30 を確保、12g（推定。型番未定）"),
    # 後ろの部品は x 9 から（後ろのガイドピン x 6 とねじの頭 φ4 を避ける）
    ("upper_gps",     ("box", (9.5, 29.5), (3.5, 23.5), (TOP, TOP + 6.0)), 5.0, C_BOARD, "GPS（MAX-M10S 基板）：20×20、5g（推定）"),
    ("upper_switch",  ("box", (9.5, 29.5), (-8.5, -2.5), (TOP, TOP + 4.0)), 1.0, C_METAL, "電源スイッチ：1g（推定）"),
    ("upper_driver",  ("box", (9.5, 29.5), (-23.5, -12.5), (TOP, TOP + 4.0)), 2.0, C_BOARD, "DRV8833＋MOSFET：2g（推定。1-b は小型のモジュール）"),
    # ---- 下段
    ("lower_plate",   ("box", (P.lower_x[0], P.lower_x[1]), (-P.lower_width / 2, P.lower_width / 2), (LZ1 - PLATE, LZ1)), 8.0, C_PLATE_L, "樹脂の板 85×41×2mm、密度 1.2 として 約 8g"),
    ("lower_motor_l_can",  ("box", (REAR_L.x - N20_W / 2, REAR_L.x + N20_W / 2), (L_IN - 0.5 - N20_GEAR - N20_CAN, L_IN - 0.5 - N20_GEAR), MZ), 6.5, C_MOTOR, "N20 1000rpm 級（左）の缶：推定"),
    ("lower_motor_l_gear", ("box", (REAR_L.x - N20_W / 2, REAR_L.x + N20_W / 2), (L_IN - 0.5 - N20_GEAR, L_IN - 0.5), MZ), 3.5, C_METAL, "N20（左）のギアボックス：推定"),
    ("lower_motor_r_can",  ("box", (REAR_R.x - N20_W / 2, REAR_R.x + N20_W / 2), (R_IN + 0.5 + N20_GEAR, R_IN + 0.5 + N20_GEAR + N20_CAN), MZ), 6.5, C_MOTOR, "N20 1000rpm 級（右）の缶：推定"),
    ("lower_motor_r_gear", ("box", (REAR_R.x - N20_W / 2, REAR_R.x + N20_W / 2), (R_IN + 0.5, R_IN + 0.5 + N20_GEAR), MZ), 3.5, C_METAL, "N20（右）のギアボックス：推定"),
    ("lower_jump_can",  ("box", (40.0, 40.0 + N20_CAN), (-N20_W / 2, N20_W / 2), (LZ1 - PLATE - N20_H, LZ1 - PLATE)), 6.5, C_MOTOR, "ジャンプ用 N20（高減速）の缶：推定"),
    ("lower_jump_gear", ("box", (40.0 + N20_CAN, 40.0 + N20_CAN + N20_GEAR), (-N20_W / 2, N20_W / 2), (LZ1 - PLATE - N20_H, LZ1 - PLATE)), 3.5, C_METAL, "ジャンプ用 N20 のギアボックス：推定"),
    ("lower_cam",     ("cyl_z", 60.0, 0.0, (LZ1, LZ1 + 2.0), 6.0), 2.0, C_CAM, "カム：仮の形と位置（C4 で未確定）"),
    ("lower_cam_switch", ("box", (62.0, 81.8), (7.0, 17.2), (LZ1, LZ1 + 6.4)), 1.0, C_METAL, "マイクロスイッチ SS-10GL13：19.8×6.4×10.2mm を寝かせて置く（高さ 6.4）、1g（推定）"),
    ("lower_axle_f",  ("cyl_y", FRONT.x, (-FRONT.y + WW / 2, FRONT.y - WW / 2), AXLE_Z, 1.5), 1.0, C_METAL, "前輪の軸 φ3：推定"),
    ("lower_pins",    ("cyls_z", list(P.springs), (LZ1, TOP + 4.0), 1.0), 2.0, C_METAL, "ガイドピン M2 ×4：推定"),
    ("lower_springs", ("cyls_z", list(P.springs), (LZ1, UZ0), P.spring_od / 2), 2.0, C_SPRING, "ばね ×4（外径 7、0.5N/mm）：推定"),
    # ---- 車輪（Pololu 32×7mm、1 輪 3.2g：メーカー）
    ("wheel_rl", ("cyl_y", REAR_L.x, (REAR_L.y - WW / 2, REAR_L.y + WW / 2), AXLE_Z, R), 3.2, C_WHEEL, "Pololu 1087/1088"),
    ("wheel_rr", ("cyl_y", REAR_R.x, (REAR_R.y - WW / 2, REAR_R.y + WW / 2), AXLE_Z, R), 3.2, C_WHEEL, "Pololu 1087/1088"),
    ("wheel_fl", ("cyl_y", FRONT.x, (FRONT.y - WW / 2, FRONT.y + WW / 2), AXLE_Z, R), 3.2, C_WHEEL, "Pololu 1087/1088"),
    ("wheel_fr", ("cyl_y", P.wheels[3].x, (P.wheels[3].y - WW / 2, P.wheels[3].y + WW / 2), AXLE_Z, R), 3.2, C_WHEEL, "Pololu 1087/1088"),
]
PASSES_THROUGH = {"lower_pins", "lower_springs"}       # 上段を貫く／上段に押されて縮む部品（干渉の確認と下段の外形から外す）


# ---------------------------------------------------------------- メッシュを作る

def _mesh(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box_geom(x, y, z):
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
    v = [(a, b, c) for a in (x0, x1) for b in (y0, y1) for c in (z0, z1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return v, f


def cyl_geom(axis, c1, c2, span, r, n=48):
    """axis="y"：中心 (c1=x, c2=z)、y が span。axis="z"：中心 (c1=x, c2=y)、z が span。"""
    a0, a1 = span
    ring = []
    for i in range(n):
        t = 2 * math.pi * i / n
        if axis == "y":
            ring.append((c1 + r * math.cos(t), c2 + r * math.sin(t)))   # (x, z)
        else:
            ring.append((c1 + r * math.cos(t), c2 + r * math.sin(t)))   # (x, y)
    verts = []
    for a in (a0, a1):
        for p, q in ring:
            verts.append((p, a, q) if axis == "y" else (p, q, a))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i) if axis == "z" else (i, n + i, n + j, j))
    cap0, cap1 = list(range(n)), list(range(n, 2 * n))
    if axis == "z":
        faces.append(tuple(reversed(cap0)))
        faces.append(tuple(cap1))
    else:
        faces.append(tuple(cap0))
        faces.append(tuple(reversed(cap1)))
    return verts, faces


def merge(geoms):
    verts, faces = [], []
    for v, f in geoms:
        off = len(verts)
        verts += v
        faces += [tuple(i + off for i in face) for face in f]
    return verts, faces


def make_part(name, shape, color):
    if shape[0] == "cyls_z":
        v, f = merge([cyl_geom("z", x, y, shape[2], shape[3], 24) for x, y in shape[1]])
    elif shape[0] == "box":
        v, f = box_geom(shape[1], shape[2], shape[3])
    elif shape[0] == "cyl_y":
        v, f = cyl_geom("y", shape[1], shape[3], shape[2], shape[4])
    elif shape[0] == "cyl_z":
        v, f = cyl_geom("z", shape[1], shape[2], shape[3], shape[4])
    else:
        raise ValueError(shape)
    ob = _mesh(name, v, f)
    ob.color = color
    return ob


# ---------------------------------------------------------------- 体積・重心・外形

def volume_centroid(ob):
    """閉じたメッシュの体積（mm³）と体積重心（mm）。原点を頂点にした四面体の和。"""
    me = ob.data
    vol, cx, cy, cz = 0.0, 0.0, 0.0, 0.0
    for poly in me.polygons:
        vs = [me.vertices[i].co for i in poly.vertices]
        for k in range(1, len(vs) - 1):
            a, b, c = vs[0], vs[k], vs[k + 1]
            v6 = a.dot(b.cross(c))
            vol += v6
            cx += v6 * (a.x + b.x + c.x)
            cy += v6 * (a.y + b.y + c.y)
            cz += v6 * (a.z + b.z + c.z)
    vol6 = vol
    if abs(vol6) < 1e-9:
        raise ValueError(f"{ob.name}: 体積がゼロ（メッシュが閉じていない）")
    return vol6 / 6, (cx / (4 * vol6), cy / (4 * vol6), cz / (4 * vol6))


def bbox(ob):
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


# ---------------------------------------------------------------- 書き出し

def export(objects, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    prev = out / "parts.json"       # 部品名を変えたときに古い STL を残さない（前回このスクリプトが書いたものだけ消す）
    if prev.exists():
        for e in json.loads(prev.read_text()).get("parts", []):
            (out / e["stl"]).unlink(missing_ok=True)
    entries = []
    for name, _, mass_g, _, source in PARTS:
        ob = objects[name]
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.wm.stl_export(filepath=str(out / f"{name}.stl"), export_selected_objects=True, ascii_format=False, global_scale=1.0)
        vol, com = volume_centroid(ob)
        lo, hi = bbox(ob)
        entries.append({
            "name": name, "stl": f"{name}.stl", "mass": mass_g / 1000,
            "com": [c / 1000 for c in com],
            "bbox_min": [c / 1000 for c in lo], "bbox_max": [c / 1000 for c in hi],
            "volume_mm3": round(vol, 1), "density_g_cm3": round(mass_g / vol * 1000, 2),
            "source": source,
            **({"passes_through": True} if name in PASSES_THROUGH else {}),
        })
    (out / "parts.json").write_text(json.dumps({
        "source": "sim/model/build_model.py（Blender でコードから組んだモデル。寸法は params.py、質量は設計書② 4 章）",
        "units": "kg, m", "parts": entries}, ensure_ascii=False, indent=2))
    return entries


# ---------------------------------------------------------------- 図

def render(objects, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "OBJECT"
    sc.display.shading.show_object_outline = True
    sc.display.shading.show_cavity = True
    world = bpy.data.worlds.new("white")
    world.color = (1.0, 1.0, 1.0)
    sc.world = world
    sc.display.shading.background_type = "WORLD"
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"

    center = (P.length / 2, 0.0, UZ1 / 2)   # 注視点：車体の中央
    target = bpy.data.objects.new("target", None)
    sc.collection.objects.link(target)
    target.location = center
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tr = cam.constraints.new("TRACK_TO")
    tr.target, tr.track_axis, tr.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"

    cx, _, cz = center
    views = {
        "iso":   ("PERSP", (cx - 185.0, -190.0, cz + 115.0), None),
        "side":  ("ORTHO", (cx, -400.0, cz), 120.0),
        "top":   ("ORTHO", (cx, 0.0, 400.0), 120.0),
        "front": ("ORTHO", (cx + 455.0, 0.0, cz), 90.0),
    }
    upper = [objects[n] for n, *_ in PARTS if n.startswith("upper_")]
    springs = objects["lower_springs"]

    def shoot(name, view, suffix=""):
        kind, loc, ortho = views[view]
        cam_data.type = kind
        cam.location = loc
        if kind == "ORTHO":
            cam_data.ortho_scale = ortho
        else:
            cam_data.lens = 50
        target.location = center if view != "top" else (cx, 0.0, 0.0)
        sc.render.filepath = str(out / f"{name}{suffix}.png")
        bpy.ops.render.render(write_still=True)

    for v in views:
        shoot(v, v)
    # 縮めた状態：上段を stroke だけ下げ、ばねを同じだけ縮める（下端は下段の板の上面に固定）
    h = P.upper_z[0] - P.lower_z[1]
    for ob in upper:
        ob.location.z -= P.stroke
    springs.scale.z = (h - P.stroke) / h
    springs.location.z = P.lower_z[1] * (1 - springs.scale.z)
    shoot("side", "side", "_compressed")
    for ob in upper:
        ob.location.z += P.stroke
    springs.scale.z, springs.location.z = 1.0, 0.0


# ---------------------------------------------------------------- main

def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else HERE / "export"
    rend = Path(argv[argv.index("--render") + 1]) if "--render" in argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects = {name: make_part(name, shape, color) for name, shape, _, color, _ in PARTS}
    entries = export(objects, out)
    total = {r: sum(e["mass"] for e in entries if e["name"].startswith(r)) * 1000 for r in ("upper", "lower", "wheel")}
    print(f"wrote {out}/parts.json: {len(entries)} parts, upper {total['upper']:.1f}g, lower {total['lower']:.1f}g, wheels {total['wheel']:.1f}g")
    if rend:
        render(objects, rend)
        print(f"rendered to {rend}")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
