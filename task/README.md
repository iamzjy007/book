# 书籍任务交接入口

在完整的 book 仓库里运行。三个目录各自带一份已初始化的 SQLite 数据库、schema.sql 和 README.md，共用上一级 workflow.py。Python 3.10+ 标准库即可，首次接手直接读取现成数据库。

| 工作 | 进入目录 | 当前种子断点（2026-11-14） |
|---|---|---|
| [书目研究](catalog/README.md) | task/catalog | 古代默认埃塞 R02 后续，另有 e-Clavis ECCA518；现代默认 versions |
| [获取正文](sources/README.md) | task/sources | 175 条档案，当前优先现代范围，下一项 modern:dydi_c:MC04 |
| [翻译中文](translations/README.md) | task/translations | 110 条输入、51 条候选；4 篇译毕自校，《皮奥尼乌斯殉道记》VII.1-6 |

**复制给第三方 AI**：“在完整 book 仓库进入我指定的 task 子目录，先读该目录 README.md，执行 verify、resume。说明当前依据与下一动作，再开展实际工作。用 save 存档，重新打开库读回断点；成果交由我推送。” 旧文档的检索、版本和翻译质量要求继续适用；新框架的写入与交付顺序以本指南和本次委托为准。

## 从新会话接手

1. 先查看 Git 状态及当前版本，保留未交付成果。从目录内运行下列两条命令。也可以在仓库根目录用 `python -X utf8 task/workflow.py resume --stage sources` 等价调用。只读 GitHub 网页的模型需要能执行 SQLite/Python 的工作区才能保存。
2. 对照子目录指南、源项目 PLAN 和恢复结果执行一小步。保存前把实际结果写成 UTF-8 的 JSON 请求，放在仓库外。每次逻辑提交生成唯一 request_key；同一提交重试保持相同请求内容和键。
3. 执行 save，再用相同 ID 的 resume 读回 revision、成果和下一动作。中断在提交前会回滚；丢失响应可原样重试；过期版本须先重新读取和对账。读回新断点后，关闭数据库连接再让下一位使用同一份更新后的仓库。
4. 三个 SQLite 是各自的进度权威；旧目录保留输入、原始文献和冻结说明。旧汇总脚本不会消费新库中的增量。若有人从旧流程继续写过，verify 会报告已登记文件的差异。另用 git status / git diff 核对新增材料，按记录合并再交接。不要拿种子重建覆盖已有收据。
5. 跨机器顺序交班，提交／推送后让接手者取最新提交。同一机器的两个写者由 SQLite 事务及 revision 检查保护。不同 Git 分支上的二进制数据库无法逐行合并，分叉时从各自 receipt.payload_json 逐笔核对重放；过期版本和内容冲突需人工处理。

```sh
python -X utf8 ../workflow.py verify
python -X utf8 ../workflow.py resume
python -X utf8 ../workflow.py save /path/to/result.json
```

## 时间、追踪和验证

- created_at、updated_at 是可变实体的数据库建档／最后变更时间，标准写入口使用 UTC。checkpoint、receipt 是追加记录。导入时两个时间相近是正常的。
- 书目 resource.observed_at、observation.observed_at 取原工作批次日期，scan_item.observed_at 取会话中的扫描日；evidence.observed_at 取来源实际访问字段。获取 attempt.observed_at、locator.observed_at 取各次检索和访问记录。翻译 unit.reviewed_at 对旧记录取书内该批自校日期，新写入取实际自校日期。原件只有日期就保留日期，缺失留 NULL。古籍成书年代在原书目字段里。
- baseline 记录原输入路径、提交与 SHA-256，核验文本时统一 LF。翻译另核冻结的获取档案和译文块哈希。verify 检查库结构、外键、基线文件及译文块；不能据此认定翻译质量或在线来源仍然有效。
- 从 task 目录运行 `python -X utf8 test_resume.py` 可在临时副本验证交付时种子断点和恢复流程。它带有基线断言，库继续推进后请用发布时的种子版本运行。seed.py 用于从干净的旧目录生成一个全新文件，如 `python -X utf8 seed.py sources /path/to/new.sqlite3`，已有目标会拒绝覆盖。

## 从书目到译稿的执行计划

① 在 catalog 对作品、机构或版本登记调查与证据。② 选定对象后从 task 目录运行 `python -X utf8 intake.py sources <目录资源ID> --project <书目项目名>`。现代 ID 由程序添加 modern: 命名空间。③ 在 sources 获取、核实并保存正文定位和可读范围。④ 选定 fulltext_online 条目后运行 `python -X utf8 intake.py translations <获取档案ID>`，形成冻结输入快照，候选从完整性检查开始。重复移交已登记的候选会返回已有 ID。⑤ 在 translations 核底本、冻结单元、保存草稿、自校、导出。历史候选继续使用各自的冻结底本；版本变更应另记迁移，保留已有译文和依据。各阶段的默认队列互相独立，明确指定 --id 可立即接手刚移交的对象。

