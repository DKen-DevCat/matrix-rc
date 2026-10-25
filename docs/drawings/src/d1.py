"""Drawings for 設計書① Wi-Fiモデル (Phase 1-a)."""
from lib import *


def w1():
    s = Svg(1240, 640)
    s.heading("W1  システム構成図 ― Wi-Fiモデル（Phase 1-a）",
              "自宅のWi-Fiだけで、PCのキー操作 → 機体の走行・ジャンプ → 映像・音声の返送までを一通り通す")
    # PC group
    s.rect(30, 100, 470, 330, "#fafbff", BLUE_S, 1.4, 12, "7 5")
    s.text(46, 124, "操作用PC（自宅）", 14, weight="bold", fill=BLUE_S)
    s.box(50, 145, 200, 250, "ブラウザ（操作画面）",
          ["W/A/S/D・Space を検出", "押下状態を 50Hz で送信", "映像・音声を再生", "ラグ・電池・経路を表示", "雑音除去（任意）"], BLUE, BLUE_S)
    s.box(280, 145, 200, 250, "中継サーバ",
          ["Node.js（同じPCで起動）", "ブラウザ ⇄ 機体を中継", "共有トークンで認証", "往復遅延の計測・記録", "経路を複数持てる作り"], BLUE, BLUE_S)
    s.line(250, 230, 280, 230, BLUE_S, 2, end="arrb")
    s.line(280, 300, 250, 300, BLUE_S, 2, end="arrb")
    s.label_bg(265, 220, "操作", 11, BLUE_S)
    s.label_bg(265, 322, "映像", 11, BLUE_S)
    s.text(265, 412, "WebSocket（PC内）", 11, "middle", fill=MUTED)
    # router
    s.box(570, 205, 150, 110, "自宅Wi-Fiルーター", ["2.4GHz", "（家庭用でOK）"], GRAY, GRAY_S)
    s.line(480, 235, 570, 235, ORANGE_S, 2, end="arro")
    s.line(570, 285, 480, 285, GREEN_S, 2, end="arrg")
    s.line(720, 235, 800, 235, ORANGE_S, 2, end="arro")
    s.line(800, 285, 720, 285, GREEN_S, 2, end="arrg")
    s.label_bg(525, 225, "UDP 操作", 11, ORANGE_S)
    s.label_bg(760, 225, "50Hz", 11, ORANGE_S)
    s.label_bg(525, 305, "UDP 映像", 11, GREEN_S)
    s.label_bg(760, 305, "音声・状態", 11, GREEN_S)
    # vehicle
    s.rect(800, 95, 410, 420, "#fffaf3", ORANGE_S, 1.4, 12, "7 5")
    s.text(816, 119, "機体（Seeed XIAO ESP32S3 Sense）", 14, weight="bold", fill=ORANGE_S)
    s.box(820, 140, 90, 48, "カメラ", ["OV3660"], ORANGE, ORANGE_S, 11, 13)
    s.box(820, 200, 90, 48, "マイク", ["デジタルMEMS"], ORANGE, ORANGE_S, 11, 13)
    s.box(960, 140, 230, 108, "ESP32-S3（制御）",
          ["操作の受信・停止判定", "映像 MJPEG 320×240", "音声 16kHz・状態送信"], ORANGE, ORANGE_S, 12, 14)
    s.line(910, 164, 960, 164, end="arr")
    s.line(910, 224, 960, 224, end="arr")
    s.box(820, 290, 170, 50, "DRV8833", ["モータードライバ"], GRAY, GRAY_S, 11, 13)
    s.box(820, 360, 170, 50, "走行モーター ×2", ["N20 約300rpm"], GRAY, GRAY_S, 11, 13)
    s.box(1020, 290, 170, 50, "MOSFET（AO3400）", ["一方向スイッチ"], GRAY, GRAY_S, 11, 13)
    s.box(1020, 360, 170, 50, "ジャンプ用モーター", ["N20 高減速＋渦巻きカム"], GRAY, GRAY_S, 11, 13)
    s.box(1020, 430, 170, 50, "カム位置スイッチ", ["縮みきりを検知"], GRAY, GRAY_S, 11, 13)
    s.box(820, 430, 170, 50, "状態LED WS2812B", ["撮影中・経路・電池"], GRAY, GRAY_S, 11, 13)
    s.poly([(1020, 248), (1020, 270), (905, 270), (905, 290)], end="arr")
    s.line(1105, 248, 1105, 290, end="arr")
    s.line(905, 340, 905, 360, end="arr")
    s.line(1105, 340, 1105, 360, end="arr")
    s.line(1105, 430, 1105, 410, dash="4 3")
    s.text(1112, 424, "カムで押す", 10, fill=MUTED)
    # notes
    s.note_box(30, 455, 740, [
        "・機体は自分からサーバへ接続する（機体側で待ち受けない）。1-b でもこの形を変えない。",
        "・操作は「今押されているキー」を 50Hz で送り続ける。300ms 届かなければ機体が自分で停止する。",
        "・1-b では「自宅Wi-Fi＋PC内サーバ」を「LTE＋東京のVPS」に差し替えるだけで済む作りにする。",
        "・電池は保護回路付きリポ 1S 1000mAh。ブザーの代わりに走行モーターを鳴らして音を出す。",
    ], "設計のポイント")
    s.title_block("W1", "システム構成図（Wi-Fiモデル）")
    return s


def w2(lte=False):
    s = Svg(1320, 1010 if lte else 900)
    if lte:
        s.heading("C2  配線図 ― 組み上げモデル（Phase 1-b）",
                  "W2 と同じピン割り当てに、LTE（技適済み Cat.1 bis）と GPS を追加。予約していた D6／D7／D8 を使う")
    else:
        s.heading("W2  配線図 ― Wi-Fiモデル（Phase 1-a）",
                  "ピンの割り当ては 1-b（組み上げモデル）と共通。1-b で使うピンは「予約」として空けておく")
    X, Y, W, H = 540, 170, 220, 340
    s.rect(X, Y, W, H, "#eef6ff", BLUE_S, 2, 10)
    s.text(X + W / 2, Y + 28, "XIAO ESP32S3 Sense", 15, "middle", "bold")
    s.text(X + W / 2, Y + 48, "（上から見た図）", 11, "middle", fill=MUTED)
    s.lines(X + W / 2, Y + 285, ["カメラ・マイクは基板内で接続済み", "microSD は挿さない（D8〜D10 と共用）"], 10, "middle", fill=MUTED)
    left = [("D0", "GPIO1"), ("D1", "GPIO2"), ("D2", "GPIO3"), ("D3", "GPIO4"), ("D4", "GPIO5"), ("D5", "GPIO6"), ("D6", "GPIO43")]
    right = [("5V", ""), ("GND", ""), ("3V3", ""), ("D10", "GPIO9"), ("D9", "GPIO8"), ("D8", "GPIO7"), ("D7", "GPIO44")]
    py = lambda i: Y + 80 + i * 30
    for i, (p, g) in enumerate(left):
        s.line(X - 30, py(i), X, py(i), sw=2)
        s.dot(X - 30, py(i), 3)
        s.text(X + 10, py(i) + 4, p, 12, weight="bold")
        s.text(X + 42, py(i) + 4, g, 10, fill=MUTED)
    for i, (p, g) in enumerate(right):
        s.line(X + W, py(i), X + W + 30, py(i), sw=2)
        s.dot(X + W + 30, py(i), 3)
        s.text(X + W - 10, py(i) + 4, p, 12, "end", "bold")
        if g:
            s.text(X + W - 42, py(i) + 4, g, 10, "end", fill=MUTED)
    # ---- D0 battery divider (top-left)
    s.poly([(X - 30, py(0)), (470, py(0)), (470, 150)])
    s.dot(470, 150)
    s.resistor_v(470, 95, 150, "100kΩ")
    s.netflag(470, 95, "VBAT")
    s.poly([(470, 150), (400, 150)])
    s.resistor_v(400, 150, 200, "100kΩ")
    s.gnd(400, 200)
    s.label_bg(320, 142, "電池電圧の監視（÷2）", 11, MUTED)
    # ---- D1..D4 → DRV8833
    DX, DY, DW, DH = 200, py(1) - 25, 160, 4 * 30 + 20
    s.rect(DX, DY, DW, DH, GRAY, GRAY_S, 1.6, 6)
    s.text(DX + DW / 2, DY - 8, "DRV8833 ブレイクアウト", 12, "middle", "bold")
    for i, name in enumerate(["AIN1", "AIN2", "BIN1", "BIN2"]):
        y = py(i + 1)
        s.line(DX + DW, y, X - 30, y)
        s.text(DX + DW - 6, y + 4, name, 11, "end")
    s.lines(DX + 8, DY + 30, ["AOUT1", "AOUT2", "", "BOUT1", "BOUT2"], 10, gap=22)
    # motors
    for k, (mx, my, lab) in enumerate([(110, DY + 30, "左モーター"), (110, DY + 105, "右モーター")]):
        s.circle(mx, my + 10, 20, "#fff", INK, 1.6)
        s.text(mx, my + 15, "M", 15, "middle", "bold")
        s.text(mx, my + 46, lab, 11, "middle")
        s.line(mx + 20, my + 4, DX, my - 4 + 0)
        s.line(mx + 20, my + 16, DX, my + 18)
    s.line(DX + 14, DY, DX + 14, DY - 34)
    s.netflag(DX + 14, DY - 34, "VBAT", anchor="end")
    s.text(DX + 22, DY + 14, "VM", 10, fill=MUTED)
    s.line(DX + 30, DY + DH, DX + 30, DY + DH + 14)
    s.gnd(DX + 30, DY + DH + 14)
    s.text(DX + 38, DY + DH + 12, "GND", 10, fill=MUTED)
    # decoupling caps near DRV
    cy0 = DY + DH + 50
    s.netflag(70, cy0, "VBAT")
    s.line(70, cy0, 150, cy0)
    s.cap_v(110, cy0, cy0 + 55, "100µF", polar=True)
    s.line(150, cy0, 190, cy0)
    s.cap_v(190, cy0, cy0 + 55, "0.1µF")
    s.line(110, cy0 + 55, 190, cy0 + 55)
    s.gnd(150, cy0 + 55)
    s.text(70, cy0 + 95, "DRV8833 の VM のすぐそばに付ける", 10, fill=MUTED)
    # ---- D5 → MOSFET → jump motor
    gy = 700
    s.poly([(X - 30, py(5)), (500, py(5)), (500, gy)])
    s.line(500, gy, 470, gy)
    s.add(f'<rect x="420" y="{gy - 6}" width="50" height="12" fill="#fff" stroke="{INK}" stroke-width="1.3"/>')
    s.text(445, gy - 12, "100Ω", 10, "middle")
    MX, MY = 250, gy - 32
    s.line(420, gy, MX + 62, gy)
    s.rect(MX, MY, 62, 64, "#fff", INK, 1.5, 4)
    s.text(MX + 31, MY + 28, "AO3400", 11, "middle", "bold")
    s.text(MX + 31, MY + 44, "N-ch", 10, "middle", fill=MUTED)
    s.text(MX + 68, gy - 5, "G", 10)
    s.text(MX + 31, MY + 12, "D", 10, "middle")
    s.text(MX + 31, MY + 60, "S", 10, "middle")
    s.dot(392, gy)
    s.poly([(392, gy), (392, gy + 25)])
    s.resistor_v(392, gy + 25, gy + 85, "100kΩ")
    s.gnd(392, gy + 85)
    s.line(MX + 31, MY + 64, MX + 31, MY + 120)
    s.gnd(MX + 31, MY + 120)
    # jump motor above drain
    s.line(MX + 31, MY, MX + 31, MY - 25)
    s.circle(MX + 31, MY - 45, 20, "#fff", INK, 1.6)
    s.text(MX + 31, MY - 40, "M", 15, "middle", "bold")
    s.line(MX + 31, MY - 65, MX + 31, MY - 95)
    s.netflag(MX + 31, MY - 95, "VBAT", anchor="end")
    # flyback diode
    dx = MX - 25
    s.poly([(MX + 31, MY - 85), (dx, MY - 85), (dx, MY - 52)])
    s.add(f'<polygon points="{dx - 8},{MY - 30} {dx + 8},{MY - 30} {dx},{MY - 46}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
    s.line(dx - 9, MY - 47, dx + 9, MY - 47, sw=2)
    s.line(dx, MY - 52, dx, MY - 47)
    s.poly([(dx, MY - 30), (dx, MY - 15), (MX + 31, MY - 15)])
    s.dot(MX + 31, MY - 15)
    s.dot(MX + 31, MY - 85)
    s.text(dx - 12, MY - 34, "SS14", 10, "end")
    s.lines(MX + 58, MY - 48, ["ジャンプ用モーター", "（N20 高減速）"], 11)
    # ---- right side
    rx = X + W + 30
    s.text(rx + 10, py(0) + 4, "未使用（USB給電のみ）", 11, fill=MUTED)
    s.line(rx, py(1), rx + 40, py(1))
    s.gnd(rx + 40, py(1))
    s.line(rx, py(2), rx + 70, py(2))
    s.netflag(rx + 70, py(2), "3V3")
    # WS2812
    LX, LY = 990, py(2) - 30
    s.rect(LX, LY, 150, 80, GRAY, GRAY_S, 1.5, 6)
    s.text(LX + 75, LY - 8, "状態LED WS2812B", 12, "middle", "bold")
    s.text(LX + 8, LY + 24, "VDD", 11)
    s.text(LX + 8, LY + 54, "DIN", 11)
    s.text(LX + 142, LY + 54, "GND", 11, "end")
    s.poly([(rx + 70 + 40, py(2)), (LX - 20, py(2)), (LX - 20, LY + 20), (LX, LY + 20)])
    s.poly([(rx, py(3)), (LX - 40, py(3)), (LX - 40, LY + 50), (LX, LY + 50)])
    s.add(f'<rect x="{LX - 90}" y="{py(3) - 6}" width="36" height="12" fill="#fff" stroke="{INK}" stroke-width="1.2"/>')
    s.text(LX - 72, py(3) - 10, "330Ω", 9, "middle")
    s.line(LX + 150, LY + 50, LX + 175, LY + 50)
    s.gnd(LX + 175, LY + 50)
    # cam switch on D9
    sy = py(4)
    s.line(rx, sy, 900, sy)
    s.dot(900, sy)
    s.line(900, sy, 930, sy - 14, sw=1.8)
    s.dot(940, sy)
    s.line(940, sy, 960, sy)
    s.gnd(960, sy)
    s.text(975, sy + 17, "カム位置SW（内部プルアップ）", 11)
    if not lte:
        # reserved
        for i, t in [(5, "予約：GPS の TX → D8（1-b）"), (6, "予約：LTE の TXD → D7（1-b）")]:
            s.line(rx, py(i), rx + 60, py(i), dash="4 3", color=GRAY_S)
            s.text(rx + 68, py(i) + 4, t, 11, fill=GRAY_S)
        s.line(X - 30, py(6), X - 90, py(6), dash="4 3", color=GRAY_S)
        s.text(X - 96, py(6) + 4, "予約：D6 → LTE の RXD（1-b）", 11, "end", GRAY_S)
    else:
        lte_part(s, X, Y, W, H, py, rx)
    # battery & switch from back pads
    by = Y + H
    s.text(X + 110, by + 56, "裏面パッド", 10, "middle", fill=MUTED)
    s.line(X + 70, by, X + 70, by + 60)
    s.text(X + 76, by + 14, "BAT+", 10, weight="bold")
    s.line(X + 150, by, X + 150, by + 120)
    s.text(X + 156, by + 14, "BAT−", 10, weight="bold")
    s.dot(X + 70, by + 60)
    s.line(X + 70, by + 60, X - 10, by + 60)
    s.netflag(X - 10, by + 60, "VBAT", anchor="end")
    # slide switch
    s.line(X + 70, by + 60, X + 70, by + 80)
    s.dot(X + 70, by + 80)
    s.line(X + 70, by + 80, X + 84, by + 108, sw=1.8)
    s.dot(X + 70, by + 112)
    s.text(X + 92, by + 100, "電源スイッチ", 11)
    s.line(X + 70, by + 112, X + 70, by + 140)
    BX, BY = X + 40, by + 140
    s.rect(BX, BY, 150, 56, "#fff4e6", ORANGE_S, 1.6, 6)
    s.text(BX + 75, BY + 24, "リポ電池 1S", 12, "middle", "bold")
    s.text(BX + 75, BY + 42, "1000mAh・保護回路付き", 10, "middle")
    s.text(BX + 30, BY - 6, "+", 13, weight="bold")
    s.line(X + 150, by + 120, X + 150, BY)
    s.text(X + 158, BY - 6, "−", 13, weight="bold")
    s.dot(X + 150, by + 120)
    s.line(X + 150, by + 120, X + 210, by + 120)
    s.gnd(X + 210, by + 120)
    # notes
    if lte:
        s.note_box(40, 838, 780, [
            "・LTE の VBAT は電池から直接取り、1000µF×2 を端子のすぐそばに。",
            "  通信の瞬間に約 2A 流れても電圧が落ちないようにする。",
            "・モジュールの UART は 1.8V 系の可能性が高い。評価ボードに",
            "  変換回路がなければ TXS0102 で 3.3V と変換する。",
            "・LTE の電源投入（PWRKEY）は評価ボードの自動起動設定を使う。",
            "・D6／D7 は起動時にログが出るため、受信側で読み捨てる。",
            "・電池は高放電タイプ（600〜800mAh）。GND はすべて共通。",
        ], "配線の注意（W2 からの追加分）")
        s.title_block("C2", "配線図（組み上げモデル）")
        return s
    s.note_box(860, 560, 445, [
        "・VBAT（電池＋、スイッチ通過後）は XIAO・DRV8833・ジャンプ",
        "  用モーターへ配る。モーターの電源を 3V3 から取らない。",
        "・充電は USB-C を挿したまま電源スイッチを ON にして行う。",
        "・D6／D7／D8 は 1-b で LTE と GPS に使うので空けておく。",
        "・ブザーは付けず、モーターを鳴らす音で代用する。",
        "・GND はすべて共通にする。",
    ], "配線の注意")
    s.title_block("W2", "配線図（Wi-Fiモデル）")
    return s


def lte_part(s, X, Y, W, H, py, rx):
    # D8 <- GPS TX
    GX, GY = 1150, py(5) - 35
    s.line(rx, py(5), GX, py(5))
    s.rect(GX, GY, 150, 82, GREEN, GREEN_S, 1.5, 6)
    s.text(GX + 75, GY + 16, "GPS MAX-M10S", 12, "middle", "bold")
    s.text(GX + 8, py(5) + 4, "TX", 11)
    s.text(GX + 8, GY + 60, "VCC", 11)
    s.text(GX + 142, GY + 60, "GND", 11, "end")
    s.text(GX + 75, GY + 76, "受信専用・技適不要", 9, "middle", fill=MUTED)
    s.line(GX, GY + 56, GX - 22, GY + 56)
    s.netflag(GX - 22, GY + 56, "3V3", anchor="end")
    s.line(GX + 150, GY + 56, GX + 165, GY + 56)
    s.gnd(GX + 165, GY + 56)
    # level shifter
    LX, LY = 870, 560
    s.rect(LX, LY, 140, 90, GRAY, GRAY_S, 1.5, 6)
    s.text(LX + 70, LY - 8, "レベル変換 TXS0102", 12, "middle", "bold")
    s.text(LX + 8, LY + 26, "A2", 11)
    s.text(LX + 8, LY + 60, "A1", 11)
    s.text(LX + 132, LY + 26, "B2", 11, "end")
    s.text(LX + 132, LY + 60, "B1", 11, "end")
    s.text(LX + 70, LY + 82, "A=3.3V  B=1.8V", 9, "middle", fill=MUTED)
    # D7 (right) -> A2
    s.poly([(rx, py(6)), (840, py(6)), (840, LY + 22), (LX, LY + 22)])
    # D6 (left) -> A1 routed under XIAO
    s.poly([(X - 30, py(6)), (520, py(6)), (520, 545), (850, 545), (850, LY + 56), (LX, LY + 56)])
    s.text(760, 540, "D6 → LTE の RXD", 10, fill=MUTED)
    s.text(846, 500, "D7 ← LTE の TXD", 10, fill=MUTED)
    # LTE board
    EX, EY = 1080, 560
    s.rect(EX, EY, 210, 190, PURPLE, PURPLE_S, 1.8, 8)
    s.text(EX + 105, EY - 8, "LTE Cat.1 bis（技適済み）", 12, "middle", "bold")
    s.lines(EX + 105, EY + 120, ["EG800AK-JP 評価ボード等", "SIM（IoT）を挿す", "800MHz 帯対応"], 10, "middle", fill="#4b3a7a")
    s.text(EX + 8, EY + 26, "TXD", 11)
    s.text(EX + 8, EY + 60, "RXD", 11)
    s.text(EX + 8, EY + 94, "VDD_EXT(1.8V)", 10)
    s.poly([(LX + 140, LY + 22), (EX, EY + 22)])
    s.poly([(LX + 140, LY + 56), (EX, EY + 56)])
    s.poly([(EX, EY + 90), (1040, EY + 90), (1040, LY + 110), (LX + 100, LY + 110), (LX + 100, LY + 90)])
    s.text(LX + 104, LY + 124, "VB", 9, fill=MUTED)
    s.line(LX + 40, LY + 90, LX + 40, LY + 110)
    s.netflag(LX + 40, LY + 110, "3V3", anchor="end")
    s.text(LX + 44, LY + 124, "VA", 9, fill=MUTED)
    # antenna
    ax_, ay_ = EX + 190, EY
    s.line(ax_, ay_, ax_, ay_ - 40, sw=1.6)
    s.poly([(ax_ - 12, ay_ - 52), (ax_, ay_ - 40), (ax_ + 12, ay_ - 52)], sw=1.6)
    s.text(ax_ - 16, ay_ - 30, "アンテナ", 10, "end")
    # VBAT + caps
    vy = EY + 190
    s.line(EX + 60, vy, EX + 60, vy + 40)
    s.text(EX + 66, vy - 6, "VBAT", 10, weight="bold")
    s.line(EX + 150, vy, EX + 150, vy + 40)
    s.text(EX + 156, vy - 6, "GND", 10, weight="bold")
    s.dot(EX + 60, vy + 40)
    s.line(EX + 60, vy + 40, EX - 20, vy + 40)
    s.netflag(EX - 20, vy + 40, "VBAT", anchor="end")
    s.line(EX + 150, vy + 40, EX + 150, vy + 100)
    s.cap_v(EX + 75, vy + 40, vy + 100, None, polar=True)
    s.line(EX + 60, vy + 40, EX + 110, vy + 40)
    s.cap_v(EX + 110, vy + 40, vy + 100, None, polar=True)
    s.line(EX + 75, vy + 100, EX + 150, vy + 100)
    s.gnd(EX + 150, vy + 100)
    s.text(EX + 160, vy + 76, "1000µF×2", 10)


def w3():
    k = 3.0  # px per mm
    s = Svg(1240, 900)
    s.heading("W3  外形図 ― Wi-Fiモデル（机上の試作車）",
              "タミヤのユニバーサルプレートに部品を載せた試作車。名刺サイズへの小型化は 1-b で行う")
    # ---------- top view
    x0, y0 = 170, 190
    L, Wd = 120, 60
    s.text(x0, y0 - 88, "上面図", 15, weight="bold")
    # wheels (rear), axle at 25mm from rear (left = rear)
    ax = x0 + 25 * k
    for wy in (y0 - 9 * k, y0 + (Wd + 2) * k):
        s.rect(ax - 17 * k, wy, 34 * k, 7 * k, "#4b5563", INK, 1.2, 3)
    # plate
    s.rect(x0, y0, L * k, Wd * k, "#fdfdfd", INK, 1.8, 4)
    for i in range(1, 24):
        for j in range(1, 12):
            s.add(f'<circle cx="{x0 + i * 5 * k}" cy="{y0 + j * 5 * k}" r="1.6" fill="#d0d5db"/>')
    # motors under plate (hidden)
    s.rect(ax - 6 * k, y0 + 2 * k, 12 * k, 26 * k, "none", GRAY_S, 1.3, 2, "5 3")
    s.rect(ax - 6 * k, y0 + 32 * k, 12 * k, 26 * k, "none", GRAY_S, 1.3, 2, "5 3")
    s.text(ax + 17 * k + 10, y0 - 9 * k + 15, "← 走行モーター（プレートの下・破線）", 11, fill=GRAY_S)
    # caster hidden
    s.circle(x0 + 108 * k, y0 + 30 * k, 9 * k, "none", GRAY_S, 1.3, "5 3")
    s.text(x0 + L * k + 14, y0 + 42 * k, "ボールキャスター（下・破線）", 11, fill=GRAY_S)
    # battery on top
    s.rect(x0 + 8 * k, y0 + 13 * k, 50 * k, 34 * k, "#fff1e0", ORANGE_S, 1.5, 4)
    s.text(x0 + 33 * k, y0 + 29 * k, "リポ電池", 12, "middle", "bold")
    s.text(x0 + 33 * k, y0 + 35 * k, "50×34×8", 10, "middle", fill=MUTED)
    # breadboard
    bx, by = x0 + 66 * k, y0 + 12.5 * k
    s.rect(bx, by, 47 * k, 35 * k, "#f8f9fa", GRAY_S, 1.4, 3)
    s.text(bx + 4, by - 6, "ミニブレッドボード 47×35", 10, fill=MUTED)
    s.rect(bx + 22 * k, by + 9 * k, 21 * k, 17.5 * k, BLUE, BLUE_S, 1.5, 3)
    s.text(bx + 32.5 * k, by + 19 * k, "XIAO", 11, "middle", "bold")
    s.rect(bx + 3 * k, by + 8 * k, 16 * k, 19 * k, GRAY, GRAY_S, 1.2, 2)
    s.text(bx + 11 * k, by + 19 * k, "DRV", 10, "middle")
    s.rect(bx + 3 * k, by + 29 * k, 10 * k, 4 * k, "#fff", GRAY_S, 1, 1)
    s.text(bx + 16 * k, by + 33 * k, "LED", 9)
    # camera at front edge
    s.rect(x0 + 115 * k, y0 + 25 * k, 6 * k, 10 * k, "#1f2933", INK, 1, 2)
    s.text(x0 + 124 * k, y0 + 23 * k, "カメラ（前向き）", 11)
    # front arrow
    s.line(x0 + 128 * k, y0 + 50 * k, x0 + 150 * k, y0 + 50 * k, BLUE_S, 2.5, end="arrb")
    s.text(x0 + 128 * k, y0 + 47 * k, "前", 12, fill=BLUE_S, weight="bold")
    # dims top
    s.dim_h(x0, x0 + L * k, y0 + Wd * k + 55, "120（プレート）", y_from=y0 + Wd * k)
    s.dim_h(x0, ax, y0 - 55, "25", y_from=y0)
    s.dim_v(y0, y0 + Wd * k, x0 - 40, "60", x_from=x0)
    s.dim_v(y0 - 9 * k, y0 + (Wd + 9) * k, x0 - 85, "約78（タイヤ含む）", x_from=ax - 17 * k)
    # ---------- side view
    gy = 760
    sx = x0
    s.text(sx, gy - 230, "側面図（左から見た図）", 15, weight="bold")
    s.line(sx - 40, gy, sx + 140 * k, gy, INK, 1.2)
    s.add(f'<rect x="{sx - 40}" y="{gy}" width="{140 * k + 40}" height="10" fill="url(#hatch)"/>')
    wcx, wcy = sx + 25 * k, gy - 17 * k
    s.wheel_side(wcx, wcy, 17 * k)
    s.rect(wcx - 12 * k, wcy - 5 * k, 26 * k, 10 * k, "#e5e7eb", INK, 1.2, 2)
    s.text(wcx + 1 * k, wcy + 4, "N20", 10, "middle")
    pl_y = gy - 25 * k
    s.rect(sx, pl_y, L * k, 3 * k, "#cfd4da", INK, 1.4, 1)
    # caster
    s.rect(sx + 104 * k, pl_y + 3 * k, 8 * k, 12 * k, "#e5e7eb", INK, 1.2, 1)
    s.circle(sx + 108 * k, gy - 5 * k, 5 * k, "#adb5bd", INK, 1.2)
    # battery & breadboard & xiao stack
    s.rect(sx + 8 * k, pl_y - 8 * k, 50 * k, 8 * k, "#fff1e0", ORANGE_S, 1.3, 2)
    s.rect(sx + 66 * k, pl_y - 9 * k, 47 * k, 9 * k, "#f8f9fa", GRAY_S, 1.3, 2)
    s.rect(sx + 88 * k, pl_y - 25 * k, 21 * k, 16 * k, BLUE, BLUE_S, 1.4, 2)
    s.text(sx + 98.5 * k, pl_y - 15 * k, "XIAO＋Sense", 10, "middle")
    s.rect(sx + 112 * k, pl_y - 22 * k, 6 * k, 8 * k, "#1f2933", INK, 1, 1)
    s.line(sx + 118 * k, pl_y - 18 * k, sx + 140 * k, pl_y - 18 * k, BLUE_S, 1.2, "4 3", end="arrb")
    s.text(sx + 122 * k, pl_y - 21 * k, "視野", 10, fill=BLUE_S)
    # side dims
    s.dim_v(gy, wcy, sx - 20, "17", x_from=wcx - 17 * k)
    s.dim_v(gy, pl_y - 25 * k, sx + 128 * k + 60, "約50", x_from=sx + 118 * k)
    s.dim_v(gy, gy - 12 * k, wcx + 75, "12", x_from=wcx + 14 * k)
    s.text(wcx + 88, gy - 6 * k, "最低地上高（モーター下面）", 10, fill=MUTED)
    s.label_bg(sx + 33 * k, pl_y - 10 * k - 2, "電池", 10, ORANGE_S)
    s.text(sx + 50 * k, gy + 34, "タイヤ φ34（N20 用セット品）", 11, "middle", fill=MUTED)
    # notes
    s.note_box(830, 120, 395, [
        "・プレートは 160×60mm の品を 120mm に切って使う。",
        "・走行モーターは N20 用の金具でプレートの下に固定する。",
        "・ボールキャスターはスペーサーで高さを合わせ、",
        "  車体が水平になるようにする。",
        "・ジャンプ機構は段階③で単体の試作機を作る。この",
        "  車台には「動作確認用のカムとスイッチ」だけ載せる。",
        "・寸法は目安。部品が届いたら実測して決める。",
    ], "製作メモ")
    s.title_block("W3", "外形図（Wi-Fiモデル 試作車）", "約 1:3.4（画面上）")
    return s


if __name__ == "__main__":
    for fn in (w1, w2, w3):
        fn().save(f"{fn.__name__}.svg")
