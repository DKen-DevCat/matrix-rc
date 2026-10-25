# choroq-rc — 遠隔操作チョロQ

小型チョロQを名刺サイズの遠隔操作ラジコンに改造する企画。関係者のみのクローズドなテーマパークで、離れた場所の PC から携帯回線（LTE）経由で操作する。カメラとマイクで状況を見ながら走り、ばねで 3cm の段差をジャンプで越える。

## 設計資料（Notion が正本）

| 資料 | リンク |
|---|---|
| 企画まとめ（要件・通信方式・「探す」を使わない理由・セキュリティ） | [遠隔操作チョロQ 企画まとめ](https://app.notion.com/p/40483592099280fbb83bc0a6249d027e) |
| 部品表 | [部品表（段階① 机上試作）](https://app.notion.com/p/40483592099281c78ccecd4a3678b4c2) |
| 設計書① Wi-Fiモデル（Phase 1-a：机上で動かす） | [設計書①](https://app.notion.com/p/4048359209928159a983d7952ce765e5) |
| 設計書② 組み上げモデル（Phase 1-b：名刺サイズ＋技適済みLTE） | [設計書②](https://app.notion.com/p/4048359209928180bff4c2664ca25574) |
| 設計書③ 中継ペアモデル（Phase 2：2台目＋ESP-NOW中継） | [設計書③](https://app.notion.com/p/4048359209928119847dd5f8c1aeed11) |

## フェーズ

| フェーズ | 内容 | 状態 |
|---|---|---|
| 1-a Wi-Fiモデル | XIAO ESP32S3 Sense を自宅 Wi-Fi で机上で動かす（操作・映像・音声・ラグ計測） | 部品の注文前 |
| 1-b1 LTE 化 | 1-a の車台のまま、技適済み LTE Cat.1 bis＋GPS＋東京の VPS に載せ替える | 未着手 |
| 1-b2 ジャンプ単体試作 | ばね＋渦巻きカム＋高減速 N20 を単体で試作し、助走付きで 3cm の段差を越えることを確認する | 未着手 |
| 1-b3 組み上げモデル | 1-b1 と 1-b2 の結果をもとに、名刺サイズの2段構造に統合する | 未着手 |
| 2 中継ペアモデル | 同じ機体をもう1台作り、ESP-NOW で中継する（B が近いと A の操作が軽くなる） | 未着手 |
| 後日 | U137（LTE-M）を予備回線として追加 | 未着手 |

設計書②は 1-b1〜1-b3 をまとめて扱う。段階の呼び方はこの表（Phase 1-a／1-b1／1-b2／1-b3／2）に統一する。

## 構成

```
web/        ブラウザの操作画面（キー状態を 50Hz で送信、映像・音声・遅延を表示）
server/     中継サーバ（Node.js。1-a は PC 内、1-b からは東京の VPS）
firmware/   機体のファームウェア（XIAO ESP32S3 Sense）
docs/drawings/      図面（W=Wi-Fiモデル、C=組み上げモデル、R=中継ペア）の SVG と PNG
docs/drawings/src/  図面の生成スクリプト
docs/review-*.md    設計レビューの記録
```

## レビュー

| 日付 | 内容 |
|---|---|
| [2026-10-25](docs/review-2026-10-25.md) | 計画・設計書①②③・図面の初回レビュー。段差越えの前進距離、ばね・カムの寸法、DTLS-PSK、U137 のピン案、1-b の分割など |

## 図面

| 図番 | 内容 |
|---|---|
| [W1](docs/drawings/w1.png) / [W2](docs/drawings/w2.png) / [W3](docs/drawings/w3.png) | Wi-Fiモデル：システム構成図／配線図／外形図 |
| [C1](docs/drawings/c1.png) / [C2](docs/drawings/c2.png) / [C3](docs/drawings/c3.png) / [C4](docs/drawings/c4.png) | 組み上げモデル：システム構成図／配線図／三面図／ジャンプ機構図 |
| [R1](docs/drawings/r1.png) / [R2](docs/drawings/r2.png) / [R3](docs/drawings/r3.png) | 中継ペア：運用配置図／通信経路図／シーケンス図 |

図面を描き直すとき（PNG への変換は macOS なら Google Chrome、Linux なら Chromium を使う。`CHROME=/path/to/chrome` で指定もできる）:

```sh
cd docs/drawings
python3 src/d1.py && python3 src/d2.py && python3 src/d3.py   # SVG を生成
src/render.sh *.svg                                            # PNG に変換
```

## 守ること

- 送信する部品は**技適済みのものだけ**を使う（机上の試験でも同じ）
- 参加者のスマホや「探す」ネットワークは使わない
- 映像と音声は録画・録音しない
- 操作が 300ms 届かなければ、機体が自分で止まる
- 機体とサーバの暗号化は DTLS-PSK（機体ごとの鍵）。自前の AES-GCM は使わない
