"""Drawings for 設計書③ 中継ペアモデル (Phase 2)."""
from lib import *


def r1():
    s = Svg(1240, 760)
    s.heading("R1  運用配置図 ― 中継ペアモデル（Phase 2）",
              "2台を同じハードで作り、片方（B）を電波の良い入口に停めて中継役にする。もう片方（A）が店の奥へ入る")
    # outdoor area
    s.rect(30, 90, 1180, 160, "#f4fbf6", GREEN_S, 1, 10, "6 4")
    s.text(46, 114, "屋外（園内の通路）― LTE 良好", 13, weight="bold", fill=GREEN_S)
    # tower
    tx, ty = 200, 236
    s.poly([(tx - 22, ty), (tx, ty - 95), (tx + 22, ty)], INK, 2)
    s.line(tx - 14, ty - 32, tx + 14, ty - 32)
    s.line(tx - 8, ty - 60, tx + 8, ty - 60)
    for rr in (14, 26, 38):
        s.path(f"M{tx + rr * 0.7},{ty - 95 - rr * 0.7} A{rr},{rr} 0 0 1 {tx + rr * 0.7},{ty - 95 + rr * 0.7}", GREEN_S, 1.6)
    s.text(tx, ty + 18, "携帯基地局", 11, "middle")
    # shop
    SX, SY, SW, SH = 300, 250, 880, 400
    s.rect(SX, SY, SW, SH, "#fbfbfc", INK, 0, 0)
    s.line(SX, SY, SX + 330, SY, INK, 6)
    s.line(SX + 470, SY, SX + SW, SY, INK, 6)
    s.line(SX, SY, SX, SY + SH, INK, 6)
    s.line(SX + SW, SY, SX + SW, SY + SH, INK, 6)
    s.line(SX, SY + SH, SX + SW, SY + SH, INK, 6)
    s.text(SX + 400, SY - 10, "入口", 13, "middle", "bold")
    s.text(SX + SW - 20, SY + SH - 18, "ショップの中（LTE 弱い・床すれすれ）", 13, "end", "bold", MUTED)
    # shelves
    for i in range(3):
        s.rect(SX + 120 + i * 230, SY + 150, 150, 26, "#e9ecef", GRAY_S, 1, 3)
    s.text(SX + 195, SY + 168, "棚", 10, "middle", fill=MUTED)
    # vehicle B at entrance
    bx, by = SX + 400, SY - 58
    s.rect(bx - 28, by - 16, 56, 32, ORANGE, ORANGE_S, 2, 6)
    s.text(bx, by + 5, "B", 15, "middle", "bold", ORANGE_S)
    s.text(bx + 40, by - 2, "機体B（中継役）", 12, weight="bold", fill=ORANGE_S)
    s.text(bx + 40, by + 15, "入口の外側に停車・LTE 良好", 11, fill=MUTED)
    # vehicle A inside
    ax, ay = SX + 640, SY + 230
    s.rect(ax - 28, ay - 16, 56, 32, BLUE, BLUE_S, 2, 6)
    s.text(ax, ay + 5, "A", 15, "middle", "bold", BLUE_S)
    s.text(ax - 40, ay + 42, "機体A（探索役）", 12, "end", "bold", BLUE_S)
    s.text(ax - 40, ay + 59, "店の奥へ入る", 11, "end", fill=MUTED)
    # ESP-NOW range
    rr = 390
    s.path(f"M{bx - rr},{SY} A{rr},{rr} 0 0 0 {bx + rr},{SY}", PURPLE_S, 1.4, dash="8 5")
    s.text(bx + rr - 10, SY + 120, "ESP-NOW の届く範囲（目安 10〜30m）", 11, "end", fill=PURPLE_S)
    s.line(bx + 10, by + 18, ax - 14, ay - 18, PURPLE_S, 2.4, end=None)
    s.label_bg((bx + ax) / 2 + 30, (by + ay) / 2, "ESP-NOW（数ms）", 12, PURPLE_S, weight="bold")
    # LTE links
    s.line(tx + 30, ty - 95, bx - 30, by - 10, GREEN_S, 2.6, end="arrg")
    s.label_bg((tx + bx) / 2, (ty - 95 + by) / 2 - 12, "LTE 強い", 12, GREEN_S, weight="bold")
    s.line(tx + 30, ty - 80, ax - 30, ay, RED_S, 1.6, "6 5", end="arrr")
    s.label_bg((tx + ax) / 2 - 40, (ty - 80 + ay) / 2 + 40, "LTE 弱い（壁・床すれすれ）", 12, RED_S)
    # notes
    s.note_box(30, 668, 640, [
        "・B が近いほど A の操作が軽くなる。B が離れても A 自身の LTE で動き続ける（切り替えの瞬間はない）。",
        "・2台はまったく同じハード。役割（中継役／探索役）は操作画面から切り替える。",
    ], "運用", 12)
    s.title_block("R1", "運用配置図（中継ペア）")
    return s


def r2():
    s = Svg(1240, 700)
    s.heading("R2  通信経路図 ― 中継ペアモデル",
              "同じ操作パケットを「A の LTE」と「B 経由」の両方に流し、受け手が先に届いた方を使う（重複は捨てる）")
    s.box(30, 230, 190, 150, "操作用PC", ["ブラウザ", "（1人で A/B 切替", " または 2人で分担）"], BLUE, BLUE_S)
    s.box(300, 200, 230, 210, "中継サーバ（VPS）",
          ["機体ごとに経路を複数保持", "下り：全経路に同じ命令", "上り：連番で先着採用", "経路ごとの遅延を表示"], BLUE, BLUE_S)
    s.line(220, 280, 300, 280, BLUE_S, 2, end="arrb")
    s.line(300, 330, 220, 330, BLUE_S, 2, end="arrb")
    # B
    s.box(700, 110, 220, 130, "機体B（中継役）", ["LTE 良好", "A の分も中継する", "自分は停車・映像は任意"], ORANGE, ORANGE_S, 12, 14)
    # A
    s.box(980, 330, 230, 170, "機体A（探索役）",
          ["2経路で受信し連番で", "先着採用・重複破棄", "300ms どの経路からも", "届かなければ停止"], BLUE, BLUE_S, 12, 14)
    # path 1: VPS - LTE - A direct (weak)
    s.poly([(530, 380), (620, 380), (620, 450), (980, 450)], RED_S, 2, "7 5", end="arrr")
    s.label_bg(800, 440, "経路①  A の LTE（弱い・遅い：100〜300ms）", 12, RED_S)
    # path 2: VPS - LTE - B - ESP-NOW - A
    s.poly([(530, 250), (600, 250), (600, 175), (700, 175)], GREEN_S, 2.4, end="arrg")
    s.label_bg(640, 165, "LTE 良好", 11, GREEN_S)
    s.poly([(920, 175), (1095, 175), (1095, 330)], PURPLE_S, 2.6, end=None)
    s.add(f'<polygon points="{1089},{318} {1101},{318} {1095},{330}" fill="{PURPLE_S}"/>')
    s.label_bg(1010, 165, "ESP-NOW（数ms）", 12, PURPLE_S, weight="bold")
    s.label_bg(820, 290, "経路②  B 経由（速い：40〜80ms）", 12, GREEN_S, weight="bold")
    # packet format box
    s.rect(30, 520, 760, 150, "#f8f9fa", GRAY_S, 1.2, 8)
    s.text(46, 545, "操作パケット（全経路共通・約 32 バイト）", 13, weight="bold")
    cols = [("機体ID", 70), ("連番 seq", 100), ("送信時刻", 100), ("キー W/A/S/D/Space", 170), ("ジャンプID", 100), ("認証タグ（AES-GCM）", 180)]
    x = 46
    for name, w in cols:
        s.rect(x, 562, w, 40, "#ffffff", INK, 1.2, 0)
        s.text(x + w / 2, 587, name, 11, "middle")
        x += w
    s.lines(46, 625, ["・受け手は「最後に採用した seq より新しいものだけ」使う → 二重に届いても1回分しか効かない（古い命令の再送も拒否）。",
                      "・ジャンプは ジャンプID で1回だけ実行。B は中身を復号せず、そのまま転送する（B が乗っ取られても命令を偽造できない）。"], 11, gap=20)
    s.title_block("R2", "通信経路図（中継ペア）")
    return s


def r3():
    s = Svg(1240, 840)
    s.heading("R3  シーケンス図 ― 中継ペアモデル",
              "B が近いとき・B が離れたとき・どの経路も途絶えたとき の3場面。経路を切り替える処理はどこにもない")
    lanes = [("操作用PC", 110, BLUE_S), ("中継サーバ", 360, BLUE_S), ("機体B（中継）", 640, ORANGE_S), ("機体A", 950, BLUE_S)]
    top, bot = 110, 760
    for name, x, c in lanes:
        s.rect(x - 75, top - 30, 150, 36, "#fff", c, 1.6, 6)
        s.text(x, top - 6, name, 13, "middle", "bold", c)
        s.line(x, top + 6, x, bot, GRAY_S, 1.2, "5 4")
    def msg(x1, x2, y, label, color=INK, dash=None, marker="arr", lab_dy=-6):
        s.line(x1, y, x2, y, color, 1.8, dash, end=marker)
        s.label_bg((x1 + x2) / 2, y + lab_dy, label, 11, color)
    def note(x, y, txt, color=MUTED, anchor="start"):
        s.text(x, y, txt, 11, anchor, fill=color)
    # scene 1
    s.rect(20, 130, 1200, 210, "#f4fbf6", GREEN_S, 0.8, 6, "4 3")
    s.text(32, 150, "場面1：B が近くにいる", 12, weight="bold", fill=GREEN_S)
    msg(110, 360, 180, "キー状態 seq=101", BLUE_S, marker="arrb")
    msg(360, 640, 205, "seq=101（LTE）", GREEN_S, marker="arrg")
    msg(640, 950, 230, "seq=101（ESP-NOW）", PURPLE_S, marker=None)
    s.add(f'<polygon points="942,224 954,230 942,236" fill="{PURPLE_S}"/>')
    note(960, 234, "45ms で到着 → 採用", GREEN_S)
    msg(360, 950, 290, "seq=101（A の LTE・遅い）", RED_S, "6 4", "arrr")
    note(960, 294, "180ms で到着 → 重複なので捨てる", RED_S)
    # scene 2
    s.rect(20, 360, 1200, 170, "#fff8f0", ORANGE_S, 0.8, 6, "4 3")
    s.text(32, 380, "場面2：B が離れた（ESP-NOW が届かない）", 12, weight="bold", fill=ORANGE_S)
    msg(110, 360, 410, "seq=102", BLUE_S, marker="arrb")
    msg(360, 640, 435, "seq=102", GREEN_S, marker="arrg")
    s.line(640, 460, 780, 460, PURPLE_S, 1.8, "3 3")
    s.text(790, 465, "✕ 届かない", 12, fill=RED_S, weight="bold")
    msg(360, 950, 495, "seq=102（A の LTE）", RED_S, "6 4", "arrr")
    note(960, 499, "180ms で到着 → 採用（ラグが戻るだけ）", ORANGE_S)
    # scene 3
    s.rect(20, 550, 1200, 190, "#fdf2f2", RED_S, 0.8, 6, "4 3")
    s.text(32, 570, "場面3：どの経路も途絶えた", 12, weight="bold", fill=RED_S)
    msg(110, 360, 600, "seq=103", BLUE_S, marker="arrb")
    s.line(360, 625, 560, 625, RED_S, 1.8, "3 3")
    s.text(570, 630, "✕", 13, fill=RED_S, weight="bold")
    s.line(360, 650, 760, 650, RED_S, 1.8, "3 3")
    s.text(770, 655, "✕", 13, fill=RED_S, weight="bold")
    s.rect(880, 670, 300, 56, RED, RED_S, 1.5, 6)
    s.text(1030, 693, "最後の受信から 300ms → 自分で停止", 12, "middle", "bold", RED_S)
    s.text(1030, 712, "LED 赤点滅・モーターで警告音", 11, "middle", fill=RED_S)
    s.line(950, 610, 950, 670, RED_S, 3)
    s.title_block("R3", "シーケンス図（中継ペア）")
    return s


if __name__ == "__main__":
    for fn in (r1, r2, r3):
        fn().save(f"{fn.__name__}.svg")
