# 古代基督教文献简体中文翻译

本目录独立承接 `christian-text-sources` 的底本档案。翻译范围、状态与获取状态分开管理。当前交付与实际下一步见 [REPORT.md](REPORT.md) 和 [progress.json](progress.json)。

- [执行计划](PLAN.md)：选本、完整性门槛、分段、审校及提交验收。
- [继续协议](CONTINUATION.md)：收到“继续”后的唯一接续入口。
- [术语表](GLOSSARY.md)、[候选及排除清单](inventory/books.json)、[队列](queue.json)。
- `books/<原档案slug>/translation.md` 为中文正文；`review.md` 为待核清单和术语建议；`source.json` 保存版本、页图校验值与依据；`record.json` 保存逐单元状态、定位及译文哈希。
- `sessions/` 记录阶段成果；不依赖聊天记录判断完成情况。

“全文译毕并自校”只表示所声明版本的正文全部译出并经过译者自身复核，不表示独立专家审定、原作无缺或异本问题已解决。本文献项目不沿用根目录现代先知信息风格指南中的局部称谓、纠错及经文套用例外；以本次用户规则为准。

所有最终交付保存在 `/workspace/outputs/book/christian-text-translations`，并随仓库提交到 main。临时下载、OCR、扫描预览在 `/tmp/christian-translation`，不作为已校订正文入库。
