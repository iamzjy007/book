# 016 古代未决回访（task/sources）

时间：2026-11-14（Asia/Shanghai）。范围：仅古代未决；经 `task/sources` 的 verify／resume／save／resume --id。未改 modern 队列，未改 baselined 的 record.json／progress／queue。

## 完成

| ID | 原状态 | 新状态 | 要点 |
|---|---|---|---|
| `dydi_a:east-aphrahat` | partial_online | fulltext_online | 逐开 DSC 1–23 叙利亚语正文；Parisot PS 1.1／1.2 IA 扫描可开；Gwynn 仍 8 篇 |
| `dydi_a:east-steps` | scan_candidate | fulltext_online | 打开 Kmosko PS 1.3 扫描；Index Sermonum 与 SERMO I 起页已核 |
| `dydi_a:east-isaac-ii` | metadata_only | metadata_only | 重开 syri.ac：CSCO 554/555 仅 IV–XLI；仍无开放全文 |

收据键见 SQLite `receipt`；权威进度在 `task/sources/state.sqlite3`。

## 下一项（古代未决，按 last_checked／sequence）

`dydi_a:east-isaac-iii`（metadata_only）：查 CSCO 637/638 可读本及手稿开放影像。

停止原因：本轮小批 3 条已 save 并 resume --id 回读；verify 通过。
