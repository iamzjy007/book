# 017 古代 partial／metadata 41 条连续处理

时间：2026-11-14（Asia/Shanghai）。范围：古代未决中 `partial_online` 25 + `metadata_only` 16 = **41 条**。全部经 `task/sources` save；本文件随一次 main 推送落盘。

## 结果概览（相对本轮开始时的 41 条）

| 结果 | 约数 | 说明 |
|---|---|---|
| 升为 fulltext_online | 4 | `east-abuqurrah-icons`（Arendzen 1897）、`B04`（Oxy. V 840）、`B05`（Oxy. X 1224）、`east-john-dalyatha`（Hansbury 2006 IA PDF，现代版权风险已注明） |
| 仍为 partial_online | 23 | 含 `east-ammar-proof`（Mikhail PhD 英译附录）、多数外典／修道／拉丁条目；已复核入口或纠正误命中 |
| 仍为 metadata_only | 14 | 含 Isaac III、John Solitary、Joseph Stages、问答书、若干希腊／拉丁书目项；本轮重开入口但仍无原语全文 |

权威进度：`task/sources/state.sqlite3`（verify 通过）。未改 baselined 旧 `record.json`／`progress.json`／`queue.json`。

## 说明
- 自动 IA 模糊命中中的明显误匹配（如 B01／B06／B09）已在 attempt 中否决。
- Aelred IA 葡萄牙语 2017 卷不升 fulltext，保持 partial。
