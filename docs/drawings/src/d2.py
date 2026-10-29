"""Drawings for 設計書② 組み上げモデル (Phase 1-b)."""
from lib import *
import d1


def c1():
    s = Svg(1240, 680)
    s.heading("C1  システム構成図 ― 組み上げモデル（Phase 1-b）",
              "自宅Wi-Fi＋PC内サーバ を「携帯回線（LTE）＋東京のVPS」に差し替える。機体は名刺サイズに組み上げる")
    s.box(30, 150, 210, 230, "操作用PC（どこでも）",
          ["ブラウザ（操作画面）", "W1 と同じ画面", "キー状態を 50Hz 送信", "映像・音声・GPS 位置", "経路と遅延を表示"], BLUE, BLUE_S)
    s.box(330, 150, 230, 230, "中継サーバ（東京VPS）",
          ["Node.js（W1 と同じ）", "操作者ログイン・1台1人", "機体ごとの鍵で認証", "連番で古い命令を拒否", "ログ（録画・録音しない）"], BLUE, BLUE_S)
    s.line(240, 230, 330, 230, BLUE_S, 2, end="arrb")
    s.line(330, 300, 240, 300, BLUE_S, 2, end="arrb")
    s.label_bg(285, 220, "TLS", 11, BLUE_S)
    s.text(285, 330, "WebSocket", 10, "middle", fill=MUTED)
    s.text(285, 345, "（インターネット）", 10, "middle", fill=MUTED)
    # cellular
    s.box(650, 190, 150, 150, "携帯網・基地局", ["ドコモ or au", "（会場の実測で決定）", "800MHz 帯を優先"], GRAY, GRAY_S, 11, 13)
    s.line(560, 235, 650, 235, ORANGE_S, 2, end="arro")
    s.line(650, 295, 560, 295, GREEN_S, 2, end="arrg")
    s.label_bg(605, 225, "UDP 操作", 11, ORANGE_S)
    s.label_bg(605, 318, "UDP 映像等", 11, GREEN_S)
    s.text(605, 358, "DTLS-PSK", 10, "middle", fill=MUTED)
    s.text(605, 372, "で暗号化", 10, "middle", fill=MUTED)
    s.line(800, 235, 870, 235, ORANGE_S, 2, end="arro")
    s.line(870, 295, 800, 295, GREEN_S, 2, end="arrg")
    s.label_bg(835, 225, "LTE", 11, ORANGE_S)
    # vehicle
    s.rect(870, 95, 350, 440, "#fffaf3", ORANGE_S, 1.4, 12, "7 5")
    s.text(886, 119, "機体（名刺サイズ 91×55mm）", 14, weight="bold", fill=ORANGE_S)
    s.box(890, 140, 310, 70, "LTE Cat.1 bis（技適済み）", ["EG800AK-JP 等＋IoT SIM＋アンテナ"], PURPLE, PURPLE_S, 11, 13)
    s.box(890, 230, 310, 80, "XIAO ESP32S3 Sense", ["制御・映像 MJPEG・音声", "300ms 途絶で停止・範囲外で停止"], ORANGE, ORANGE_S, 11, 13)
    s.line(1045, 210, 1045, 230, sw=2, start="arr", end="arr")
    s.text(1058, 224, "UART", 10, fill=MUTED)
    s.box(890, 330, 150, 56, "GPS", ["MAX-M10S"], GREEN, GREEN_S, 11, 13)
    s.box(1050, 330, 150, 56, "走行・ジャンプ", ["W2 と同じ"], GRAY, GRAY_S, 11, 13)
    s.box(890, 400, 150, 56, "カメラ・マイク", ["XIAO に内蔵"], GRAY, GRAY_S, 11, 13)
    s.box(1050, 400, 150, 56, "リポ電池", ["600〜800mAh 高放電"], ORANGE, ORANGE_S, 11, 13)
    s.box(890, 470, 310, 50, "（後日追加）U137 LTE-M 予備回線", [], "#ffffff", GRAY_S, 11, 12, "5 4")
    s.line(965, 310, 965, 330, end="arr", start="arr")
    s.line(1125, 310, 1125, 330, end="arr")
    # satellites
    s.note_box(30, 430, 790, [
        "・機体は電源を入れると自分から VPS へ接続する。機体は外からの接続を受け付けない（NAT の内側でも動く）。",
        "・通信の仕組みは W1 と同じで、経路が「自宅Wi-Fi」から「LTE」に変わるだけ。経路を足せる作りは Phase 2 の中継で使う。",
        "・電波が弱いときは映像の画質を自動で下げ、音声を止めて、操作を最優先にする。",
        "・位置は GPS（屋外で 2〜5m）。屋内では GPS が効かないので、最後の位置と映像で判断する。",
        "・U137（LTE-M）は後日、屋内で操作が途絶える場合の予備回線として追加する。ピンはカム位置スイッチを",
        "  廃止して D8・D9 を U137 の UART に充て、GPS は U137 内蔵の GNSS に置き換える。",
    ], "設計のポイント")
    s.title_block("C1", "システム構成図（組み上げモデル）")
    return s


def c3():
    k = 4.0
    s = Svg(1300, 1000)
    s.heading("C3  外形図（三面図）― 組み上げモデル",
              "上段＝電子部品と電池（重い）、下段＝足回り。上下の間のばねでジャンプする。寸法は目安で、Phase 1-b2 の試作後に確定する")
    # 寸法の正本は sim/matrix_sim/params.py（2026-10-29：車輪 φ32、電池 LP603449、ばねを四隅に）
    L, Wd = 91, 55
    R, WW = 16, 7                      # 車輪 φ32 × 幅 7（Pololu 32×7mm）
    rearL, rearR, front = 23, 23, 75   # 車輪の中心 x（左後輪・右後輪・前輪）。後輪は左右で揃える（10-29）
    WY = 24                            # 車輪の中心 y（左右）
    LZ0, LZ1 = 11, 23                  # 下段の下面・上面
    UZ0, UZ1 = 44, 58                  # 上段の板の下面・上の部品の上端の目安
    SPRINGS = [(6, 15.5), (6, -15.5), (86, 15.5), (86, -15.5)]
    BATT = (11, 62, 34.5, 6.3)         # 電池 x0, x1, 幅, 厚さ
    LX0, LX1, LW = 1, 90, 39           # 下段の板の前後の範囲と幅
    STROKE = 10
    yy = lambda y: 27.5 - y            # 中心線からの y（左が＋）を、図の上端からの距離に直す
    # ---------- top view
    x0, y0 = 120, 150
    s.text(x0, y0 - 18, "上面図（上段を外して足回りを破線で表示）", 14, weight="bold")
    s.rect(x0, y0, L * k, Wd * k, "#fbfcfe", INK, 2, 6)
    def wheel_top(cx, wy):
        s.rect(x0 + (cx - R) * k, y0 + (yy(wy) - WW / 2) * k, 2 * R * k, WW * k, "#4b5563", INK, 1.2, 3)
    wheel_top(rearL, WY); wheel_top(rearR, -WY); wheel_top(front, WY); wheel_top(front, -WY)
    # motors in line (hidden): Pololu 136:1 6mm 遊星 φ6×19、2 個で 38mm。ギアボックス側を車輪に向ける
    s.rect(x0 + (rearL - 3) * k, y0 + yy(WY - WW / 2 - 0.5) * k, 6 * k, 19 * k, "none", GRAY_S, 1.3, 2, "5 3")
    s.rect(x0 + (rearR - 3) * k, y0 + yy(-WY + WW / 2 + 0.5 + 19) * k, 6 * k, 19 * k, "none", GRAY_S, 1.3, 2, "5 3")
    s.line(x0 + front * k, y0 + yy(WY - WW / 2) * k, x0 + front * k, y0 + yy(-WY + WW / 2) * k, GRAY_S, 1.3, "8 3 2 3")
    # jump motor + cam + switch (hidden)
    s.rect(x0 + 40 * k, y0 + yy(6) * k, 24 * k, 12 * k, "none", RED_S, 1.3, 2, "5 3")
    s.circle(x0 + 60 * k, y0 + 27.5 * k, 6 * k, "none", RED_S, 1.3, "3 2")
    s.text(x0 + 50 * k, y0 + yy(6) * k - 6, "ジャンプ用モーター＋カム", 10, "middle", fill=RED_S)
    s.rect(x0 + 62 * k, y0 + yy(17.2) * k, 19.8 * k, 10.2 * k, "none", GRAY_S, 1.2, 1, "4 2")
    s.text(x0 + 72 * k, y0 + yy(17.2) * k - 4, "カム位置SW", 9, "middle", fill=GRAY_S)
    for gx, gyy in SPRINGS:
        s.circle(x0 + gx * k, y0 + yy(gyy) * k, 3.5 * k, "none", PURPLE_S, 1.3, "3 2")
    s.text(x0 + 47 * k, y0 + yy(-15.5) * k + 4, "ばね×4（四隅の破線円）", 10, fill=PURPLE_S)
    s.text(x0 + (rearL + 4) * k, y0 + yy(12) * k, "左モーター", 9, fill=GRAY_S)
    s.text(x0 + (rearR + 4) * k, y0 + yy(-12) * k, "右モーター", 9, fill=GRAY_S)
    s.line(x0 + 95 * k, y0 + 27.5 * k, x0 + 110 * k, y0 + 27.5 * k, BLUE_S, 2.5, end="arrb")
    s.text(x0 + 96 * k, y0 + 25 * k, "前", 12, fill=BLUE_S, weight="bold")
    s.dim_h(x0, x0 + L * k, y0 + Wd * k + 40, "91（名刺の長辺）", y_from=y0 + Wd * k)
    s.dim_v(y0, y0 + Wd * k, x0 - 30, "55", x_from=x0)
    s.dim_h(x0, x0 + rearL * k, y0 + Wd * k + 18, f"{rearL}", y_from=y0 + Wd * k)
    s.dim_h(x0 + rearL * k, x0 + front * k, y0 + Wd * k + 18, f"{front - rearL}", y_from=y0 + Wd * k)
    # ---------- upper deck layout
    ux = 640
    s.text(ux, y0 - 18, "上段の部品配置（上から見た図）", 14, weight="bold")
    s.rect(ux, y0, L * k, Wd * k, "#fbfcfe", INK, 2, 6)
    bx0, bx1, bw, bt = BATT
    s.rect(ux + bx0 * k, y0 + yy(bw / 2) * k, (bx1 - bx0) * k, bw * k, "none", ORANGE_S, 1.4, 3, "6 3")
    s.rect(ux + 68 * k, y0 + yy(10.5) * k, 17.8 * k, 21 * k, BLUE, BLUE_S, 1.5, 3)
    s.text(ux + 76.9 * k, y0 + 26 * k, "XIAO", 11, "middle", "bold")
    s.text(ux + 76.9 * k, y0 + 30.5 * k, "＋Sense", 9, "middle")
    s.rect(ux + 87 * k, y0 + 23.5 * k, 3 * k, 8 * k, "#1f2933", INK, 1, 1)
    s.text(ux + 92 * k, y0 + 21 * k, "カメラ", 10)
    s.rect(ux + 31 * k, y0 + yy(16) * k, 32 * k, 32 * k, PURPLE, PURPLE_S, 1.5, 3, "6 3")
    s.lines(ux + 47 * k, y0 + 26 * k, ["LTE ボード", "（30×30 を確保）"], 10, "middle")
    s.rect(ux + 9.5 * k, y0 + yy(23.5) * k, 20 * k, 20 * k, GREEN, GREEN_S, 1.5, 3)
    s.lines(ux + 19.5 * k, y0 + yy(13.5) * k, ["GPS", "（空向き）"], 10, "middle")
    s.rect(ux + 9.5 * k, y0 + yy(-2.5) * k, 20 * k, 6 * k, GRAY, GRAY_S, 1.2, 2)
    s.text(ux + 19.5 * k, y0 + yy(-6.5) * k, "電源SW", 9, "middle")
    s.rect(ux + 9.5 * k, y0 + yy(-12.5) * k, 20 * k, 11 * k, GRAY, GRAY_S, 1.2, 2)
    s.text(ux + 19.5 * k, y0 + yy(-19) * k, "DRV・MOSFET", 9, "middle")
    s.rect(ux + 64 * k, y0 + 45 * k, 6 * k, 6 * k, "#fff", GRAY_S, 1, 1)
    s.text(ux + 71 * k, y0 + 50 * k, "LED", 9)
    s.rect(ux + 3 * k, y0 + 1.5 * k, 85 * k, 2 * k, "#ede9fe", PURPLE_S, 1, 1)
    s.text(ux + 45 * k, y0 - 2, "LTE フレキアンテナ（側面上縁に沿わせる）", 9, "middle", fill=PURPLE_S)
    s.text(ux + 45 * k, y0 + Wd * k + 20, "破線の橙：電池 LP603449（34.5×51×6.3、約 23g）を板の裏に固定。USB-C は後ろ向き", 11, "middle", fill=ORANGE_S)
    # ---------- side view
    gy = 830
    sx = 120
    s.text(sx, gy - 250, "側面図（左から見た図・伸びた状態）", 14, weight="bold")
    s.line(sx - 30, gy, sx + 100 * k, gy, INK, 1.2)
    s.add(f'<rect x="{sx - 30}" y="{gy}" width="{100 * k + 30}" height="10" fill="url(#hatch)"/>')
    for wx in (rearL, front):
        s.wheel_side(sx + wx * k, gy - R * k, R * k)
    # lower chassis
    lc_top = gy - LZ1 * k
    s.rect(sx + LX0 * k, lc_top, (LX1 - LX0) * k, (LZ1 - LZ0) * k, "#e5e7eb", INK, 1.5, 3)
    s.text(sx + 52 * k, lc_top + 8 * k, "下段（足回り・モーター・カム）", 11, "middle")
    # springs（四隅）とガイドピン
    up_bot = gy - UZ0 * k
    for gxx in (5, 87):
        s.spring(sx + gxx * k, up_bot, lc_top, 7, 5, PURPLE_S, 1.6)
        s.line(sx + gxx * k, up_bot - 6 * k, sx + gxx * k, lc_top, GRAY_S, 1, "3 2")
    # 電池（板の裏）
    s.rect(sx + bx0 * k, up_bot, (bx1 - bx0) * k, bt * k, "#fdebd3", ORANGE_S, 1.2, 2, "5 3")
    s.text(sx + (bx0 + bx1) / 2 * k, up_bot + 4.6 * k, "電池", 10, "middle", fill=ORANGE_S)
    # upper body
    s.rect(sx + 1 * k, up_bot - (UZ1 - UZ0) * k, 89 * k, (UZ1 - UZ0) * k, "#e8f0fe", BLUE_S, 1.8, 4)
    s.text(sx + 45 * k, up_bot - 6 * k, "上段（電子部品）", 11, "middle")
    s.rect(sx + 87 * k, up_bot - 11 * k, 3 * k, 6 * k, "#1f2933", INK, 1, 1)
    s.line(sx + 90 * k, up_bot - 8 * k, sx + 100 * k, up_bot - 8 * k, BLUE_S, 1.2, "4 3", end="arrb")
    s.dim_v(gy, up_bot - (UZ1 - UZ0) * k, sx + 95 * k + 30, f"約{UZ1}（伸び）", x_from=sx + 90 * k)
    s.dim_v(up_bot, lc_top, sx - 30, f"{UZ0 - LZ1}", x_from=sx + 3 * k)
    s.dim_v(gy, gy - R * k, sx - 70, f"{R}", x_from=sx + rearL * k)
    s.text(sx + 5 * k, gy + 30, "タイヤ φ32 × 幅7（Pololu 32×7mm）", 11, fill=MUTED)
    # ---------- front view
    fx = 760
    s.text(fx, gy - 250, "正面図", 14, weight="bold")
    s.line(fx - 20, gy, fx + 55 * k + 20, gy, INK, 1.2)
    s.add(f'<rect x="{fx - 20}" y="{gy}" width="{55 * k + 40}" height="10" fill="url(#hatch)"/>')
    s.rect(fx, gy - 2 * R * k, WW * k, 2 * R * k, "#4b5563", INK, 1.2, 3)
    s.rect(fx + (55 - WW) * k, gy - 2 * R * k, WW * k, 2 * R * k, "#4b5563", INK, 1.2, 3)
    s.rect(fx + (27.5 - LW / 2) * k, lc_top, LW * k, (LZ1 - LZ0) * k, "#e5e7eb", INK, 1.4, 3)
    s.rect(fx + yy(bw / 2) * k, up_bot, bw * k, bt * k, "#fdebd3", ORANGE_S, 1.2, 2, "5 3")
    s.rect(fx, up_bot - (UZ1 - UZ0) * k, 55 * k, (UZ1 - UZ0) * k, "#e8f0fe", BLUE_S, 1.8, 4)
    s.spring(fx + yy(15.5) * k, up_bot, lc_top, 6, 5, PURPLE_S, 1.4)
    s.spring(fx + yy(-15.5) * k, up_bot, lc_top, 6, 5, PURPLE_S, 1.4)
    s.circle(fx + 27.5 * k, up_bot - 8 * k, 3 * k, "#1f2933", INK, 1)
    s.text(fx + 27.5 * k, up_bot - 16 * k, "カメラ", 10, "middle")
    s.dim_h(fx, fx + 55 * k, gy + 34, "55", y_from=gy)
    # notes
    s.note_box(640, 418, 640, [
        "・走行モーター（Pololu 6mm 遊星、長さ 19）は左右一直線、後輪を揃える。前輪は自由回転。",
        "・重い部品（電池・LTE）は上段に載せる。上段が重いほど高く跳べる。",
        "・上段と下段はガイドピン（M2 ねじ）で上下だけ動く。ばねとピンは四隅（板の裏の電池と車輪を避ける）。",
        "・重さは約 110g（部品の型番で見直した内訳は設計書②の重量表）。",
        f"・上下のすき間 {UZ0 - LZ1}mm は縮めると {UZ0 - LZ1 - STROKE}mm（縮めた上段の下面 {UZ0 - STROKE}mm がタイヤ上端 {2 * R}mm に当たらない）。",
        "  10mm リフトのカム（直径 30mm 級）の収まり場所は未確定。1-b2 で「縮めた状態」の側面図で確定。",
    ], "設計メモ（2026-10-29：車輪 φ32・電池 LP603449）", 12)
    s.title_block("C3", "外形図（組み上げモデル 三面図）", "約 1:2.5（画面上）")
    return s


def c4():
    s = Svg(1300, 900)
    s.heading("C4  ジャンプ機構図 ― 渦巻きカム式",
              "高減速モーターでカムをゆっくり回してばねを縮め、カムの段差で一気に放す。サーボより力が出せ、1方向に回すだけで済む")
    panels = [(40, "① 待機（伸びた状態）", 0.0), (450, "② チャージ（縮める）", 1.0), (860, "③ 解放 → 跳躍", -0.4)]
    for px, title, comp in panels:
        base = 520
        s.rect(px, 100, 390, 470, "#ffffff", GRAY_S, 1.2, 10)
        s.text(px + 16, 128, title, 15, weight="bold")
        lift = 60 if comp < 0 else 0
        gy = base
        s.line(px + 20, gy, px + 370, gy, INK, 1.2)
        s.add(f'<rect x="{px + 20}" y="{gy}" width="350" height="8" fill="url(#hatch)"/>')
        # wheels + lower chassis
        wy = gy - 34 - lift
        s.wheel_side(px + 80, wy, 34)
        s.wheel_side(px + 310, wy, 34)
        lc_top = wy - 46
        s.rect(px + 40, lc_top, 310, 40, "#e5e7eb", INK, 1.5, 4)
        s.text(px + 195, lc_top + 26, "下段", 12, "middle", weight="bold")
        # cam on lower chassis
        cx, cy = px + 195, lc_top - 2
        stroke = 50 if comp >= 0.99 else 0
        up_bot = lc_top - 60 - lift * 0.3 + stroke
        if comp < 0:
            up_bot = lc_top - 60
        # upper body
        s.rect(px + 30, up_bot - 70, 330, 70, "#e8f0fe", BLUE_S, 1.8, 6)
        s.text(px + 195, up_bot - 40, "上段（電子部品・電池）", 12, "middle", weight="bold")
        # springs
        for sx in (px + 90, px + 300):
            s.spring(sx, up_bot, lc_top, 9, 5, PURPLE_S, 1.8)
        # guide pin
        s.line(px + 60, up_bot - 10, px + 60, lc_top + 30, GRAY_S, 2)
        s.line(px + 52, lc_top + 30, px + 68, lc_top + 30, GRAY_S, 3)
        # cam (snail) drawn on the side of lower chassis, follower hangs from upper body
        ccx, ccy = px + 195, lc_top + 20
        rot = {0.0: 0, 1.0: 300, -0.4: 359}[comp]
        s.add(f'<g transform="rotate({rot} {ccx} {ccy})"><path d="M{ccx},{ccy - 8} '
              f'A8,8 0 0 1 {ccx + 8},{ccy} A12,12 0 0 1 {ccx},{ccy + 12} A15,15 0 0 1 {ccx - 15},{ccy} '
              f'A18,18 0 0 1 {ccx},{ccy - 18} Z" fill="#fde2e2" stroke="{RED_S}" stroke-width="1.8"/></g>')
        s.circle(ccx, ccy, 3, RED_S, RED_S)
        # follower arm from upper body down past cam
        fy = ccy + (8 if comp < 0.99 else 18)
        s.poly([(px + 225, up_bot), (px + 225, fy + 6), (ccx + 2, fy + 6)], ORANGE_S, 2.4)
        s.circle(ccx + 2, fy + 1, 5, "#fff", ORANGE_S, 1.8)
        if comp >= 0.99:
            s.line(px + 340, up_bot - 110, px + 340, up_bot - 76, RED_S, 2.5, end="arrr")
            s.label_bg(px + 300, up_bot - 116, "引き下げる", 11, RED_S)
            s.text(px + 195, 555, "カムが太る側でフォロワーを押し下げ、ばねを縮める", 11, "middle", fill=MUTED)
        elif comp < 0:
            s.line(px + 195, up_bot - 80, px + 195, up_bot - 130, GREEN_S, 2.5, end="arrg")
            s.label_bg(px + 260, up_bot - 112, "上段が跳ね上がり", 11, GREEN_S)
            s.label_bg(px + 260, up_bot - 94, "下段を引っ張り上げる", 11, GREEN_S)
            s.text(px + 195, 555, "段差を越えるとフォロワーが外れ、ばねが一気に伸びる", 11, "middle", fill=MUTED)
        else:
            s.text(px + 195, 555, "フォロワーはカムの細い側。スイッチでカム位置を検知", 11, "middle", fill=MUTED)
    # calc table
    s.note_box(40, 600, 820, [
        "目標：3cm の段差を越える → 跳躍高さ 4cm 以上（余裕込み）。機体の重さ m＝約110g（上段 約68g・下段 約42g。10-29 に型番で見直し）。",
        "必要なエネルギー：m·g·h ＝ 0.11 × 9.8 × 0.04 ≒ 0.043J。上段が下段を引っ張る時の損失（約4割）と余裕を見て、ばねに 約0.1J を蓄える。",
        "ばね：4本 × ばね定数 約0.5N/mm × 縮め量 10mm → 蓄えるエネルギー ＝ 4 × ½ × 500 × 0.01² ＝ 0.1J。縮めきった時の力は合計 約20N。",
        "カムを回す力：トルク ≒ 力 × 半径の増え方（10mm ÷ 約5.2rad）＝ 20N × 1.9mm ≒ 0.04N·m。摩擦込みで 約0.08N·m。",
        "　→ N20 の高減速モーター（1000:1 前後）で回せる見込み。1回転 約3〜4秒 ＝ ジャンプの「チャージ時間」になる。",
        "跳躍の見積もり：上段の速さ √(2×0.1÷0.068) ≒ 1.7m/s → 下段を引っ張った後 約1.06m/s → 高さ 約5.7cm（物理演算では 4.1cm）。",
        "前進も要る：滞空 約0.16秒で車体 91mm が段差を通り過ぎるには 0.5m/s 以上（概算 91÷0.16≒0.57m/s）→ Pololu 136:1 をデューティ 1.0。",
        "　→ φ32・3.7V で 約0.52m/s、真上に跳ぶ。物理演算 10-29（110g）：段差の 25〜45mm 手前で 10 回中 9〜10 回。",
        "ばねの寸法：0.5N/mm を線径 0.55mm で作ると約15巻き、密着高さ 約9mm。自由長 15mm では 10mm 縮まない → 自由長 25mm 以上。",
        "※ 数値は計算上の目安。Phase 1-b2 の単体試作で、ばねの強さと縮め量を実測して決める。",
    ], "設計計算", 12)
    s.note_box(880, 600, 400, [
        "・SG90 サーボは力が足りないので使わない",
        "  （20N を直接引くには 2kgf 以上が必要）。",
        "・カムは1方向に回すだけ。MOSFET 1個で済む。",
        "・カム位置スイッチで「チャージ完了」を知る。",
        "・着地の衝撃対策に、XIAO と LTE ボードは",
        "  スポンジ両面テープで上段に固定する。",
    ], "なぜこの方式か", 12)
    s.title_block("C4", "ジャンプ機構図（渦巻きカム式）")
    return s


def c2():
    return d1.w2(lte=True)


if __name__ == "__main__":
    for fn in (c1, c2, c3, c4):
        fn().save(f"{fn.__name__}.svg")
