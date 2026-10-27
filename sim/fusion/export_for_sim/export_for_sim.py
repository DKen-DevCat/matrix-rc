"""Fusion のスクリプト：物理演算用に部品を書き出す（matrix-rc）。

役割の付いたコンポーネント（upper_* / lower_* / wheel_rl / wheel_rr / wheel_fl / wheel_fr）ごとに
STL（バイナリ）と、質量・重心・外形（parts.json）を書き出す。使い方は sim/fusion/README.md。
座標は組み立てたまま（ワールド座標）で書き出すので、Fusion 側で「x が前・z が上・原点は後端の中心線の地面」に組んでおく。
"""
import json
import os
import traceback

import adsk.core
import adsk.fusion

WHEELS = ("wheel_rl", "wheel_rr", "wheel_fl", "wheel_fr")
CM = 0.01  # Fusion の内部単位（cm）→ m


def has_role(name):
    return name in WHEELS or name.startswith("upper_") or name.startswith("lower_")


def part_name(occ):
    # 部品名はコンポーネント名。同じコンポーネントを複数置くと区別できないので、車輪は 4 つ別のコンポーネントにする
    return occ.component.name


def inside_exported_parent(occ):
    """親のどこかがすでに役割付きなら、親ごと書き出されるので子は飛ばす。"""
    parent = occ.assemblyContext
    while parent:
        if has_role(part_name(parent)):
            return True
        parent = parent.assemblyContext
    return False


def point(p):
    return [p.x * CM, p.y * CM, p.z * CM]


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("デザインを開いてから実行してください。")
            return
        dlg = ui.createFolderDialog()
        dlg.title = "書き出し先のフォルダ（matrix-rc の sim/fusion/export など）"
        if dlg.showDialog() != adsk.core.DialogResults.DialogOK:
            return
        out = dlg.folder

        em = design.exportManager
        entries, seen = [], set()
        for occ in design.rootComponent.allOccurrences:
            name = part_name(occ)
            if not has_role(name) or inside_exported_parent(occ):
                continue
            if name in seen:
                ui.messageBox(f"同じ名前の部品が 2 つあります：{name}\n車輪などは別々のコンポーネントにしてください。")
                return
            seen.add(name)
            stl = name + ".stl"
            opts = em.createSTLExportOptions(occ, os.path.join(out, stl))
            opts.isBinaryFormat = True
            opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
            em.execute(opts)
            props = occ.physicalProperties
            bb = occ.boundingBox
            entries.append({
                "name": name,
                "stl": stl,
                "mass": props.mass,                 # kg（材料の密度から計算。部品の実測があれば材料で合わせる）
                "com": point(props.centerOfMass),
                "bbox_min": point(bb.minPoint),
                "bbox_max": point(bb.maxPoint),
            })

        missing = [w for w in WHEELS if w not in seen]
        with open(os.path.join(out, "parts.json"), "w", encoding="utf-8") as f:
            json.dump({"source": design.parentDocument.name, "units": "kg, m", "parts": entries}, f,
                      indent=2, ensure_ascii=False)
        msg = f"{len(entries)} 個の部品を書き出しました：\n{out}"
        if missing:
            msg += f"\n\n見つからなかった車輪：{', '.join(missing)}"
        ui.messageBox(msg)
    except Exception:
        if ui:
            ui.messageBox("書き出しに失敗しました：\n" + traceback.format_exc())
