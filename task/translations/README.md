# 中文翻译 · 第三方模型入口

1. 在此目录运行 `python -X utf8 ../workflow.py verify` 和 `python -X utf8 ../workflow.py resume`。读原 christian-text-translations/PLAN.md、GLOSSARY.md、对应 review 与 edition、next_unit、neighbors。当前种子按原队列保留 110 份输入，51 份候选，5 篇已冻结 127 个单元，106 个已自校。默认接《皮奥尼乌斯殉道记》lori_b:lb13 的 VII.1-6，按 Gebhardt 1902 印页 101 末至 102 页核实原文和跨页句。review 含待核项和术语意见；已有草稿在 next_unit.body。
2. 未冻结的候选先读题页、篇首篇尾和中间连续页，检查版权、残缺、所选语种、版本关系。新候选先用 freeze 保存版本及全篇稳定单元。登记时核实真实页图和 SHA-256；如暂缓，应用 blocked_source 或 deferred_incomplete，附 reason 和下一定位。解除阻碍后按 ID 指定接回。
3. 从第一个非 self_reviewed 单元读起。保留章段、自然段、缺文、拟补、异文、引文与选本说明；已有 draft 先逐句对照。可先存 draft，再以新的 revision 和键保存 self_reviewed。保存后检查下一单元；最后一个完成时整篇自动进入 translated_self_reviewed。独立审校和未来改版另行记录。
4. 一次请求用 `python -X utf8 ../workflow.py save /path/to/result.json`。翻译请求格式如下，替换占位符，revision 取实时查询。receipt 保存每次草稿和自校，unit 保存当前正文、锚点、状态与规范化 SHA-256。收到请求结果不确定时原样重试。

```json
{"id":"lori_b:lb13","revision":0,"request_key":"<唯一键>","operation":"draft","unit":"VII.1-6","body":"<实际中文译文>","review_note":"<实核页、术语、异文及疑点>","observed_at":"<实际日期或带时区时间>","next_action":"<本段待校重点或下一单元动作>"}
```

freeze 与上例共用 id、revision、request_key、observed_at、next_action；operation 设为 freeze，替换 unit/body 为 edition 和 units。edition 需包含 language、edition、source_urls、artifacts（每项 url、sha256）和 completeness（verified 为 true，scope、limits 说明边界）；可保留校本页码与版本来源全部附加信息。units 依原文顺序列出整书，每项 id、source_locator、source_anchor 都必填。首次冻结后如底本实际变化，应先另立版本迁移记录、核对原稿，再安排迁移；当前写入口只支持一个冻结版本。

5. 运行 `python -X utf8 ../workflow.py resume --id lori_b:lb13` 读回；用 `python -X utf8 ../workflow.py export --id lori_b:lb13` 输出当前 Markdown 正文（包括已保存草稿）；正式交付前核 book.status 和 unit.status，并附 book.review。新事实存于本库。仓库旧 translation.md、queue.json 和脚本记录的是基线版。访问 Git 的第三方模型须同步更新后的 SQLite 再接手。完整交班操作见 [总指南](../README.md)。


## 附件优先队列

`priority_queue` 保存 `D:/work/workspace/git/priority.txt` 的用户排序，不改写原有 51 条固定翻译候选顺序。先查看：

```sql
SELECT rank,title,book_id,status,next_action FROM priority_queue ORDER BY rank;
```

`blocked_source` 表示没有核实可译底本；`needs_completeness_check` 表示已有候选入口但尚未通过完整性门槛；取得并核实全篇后才可冻结版本、建立 unit 并进入翻译。`book_id` 尚未匹配的条目保持 NULL。处理完成后同步更新该行的 status、next_action、updated_at。该队列不是自动“就绪”标志，也不替换原 queue。

当前附件前 3 项的进度（2026-11-15）：

- Mingana《早期基督教神秘家文选》是多篇作品组成的选集。1934 年卷 7 开放扫描中，Simon of Taibutheh 的叙利亚文印页 281–320 对应 scan leaves n292–n331，页序连续。已另建 `dydi_a:east-mingana-mystics:simon-taibutheh`，按印页冻结 40 个断点单元，并从叙利亚文开始翻译；p281 开篇句已保存为未完成草稿。英译版权状态未解决，因此只作辅助对照，不作为中文转译底本。之后需逐篇建立其他作者的独立记录，不能将整卷当成单一作品。
- 吉兹《约西蓬》已找到 EAP704/2/3 Marawe Krestos 手稿（1595–1605）。抽检全部 174 张数字影像：003–167 为文字影像，168–174 为书册边缘、装订或封面影像；已将文字影像 003–167 界定为本项目的有界可译范围，冻结为 165 个按影像续跑的单元。它不是“全书104章已核全”的声明；译者需逐处标示缺损和不可读字。英国国家图书馆注明手稿状况很差、边缘大面积缺损且仅供研究。现有 Bowman 英译是 Hebrew Sepher Yosippon 的完整译本，不是埃塞俄比亚 Ge’ez 版本；Binyam 研究提供部分对读，不是全书英译。可在已证实平行处作标明来源的辅助参照，不能无标记补写为吉兹原文。
- 《我主遗训》已冻结 Rahmani 1899 叙利亚文—拉丁文对照本，75 个断点单元。序言 I.0 已复核并自校，`magnanimitas` 依对页叙利亚文和赛11:2语境改为“能力”；第一节 I.1 已初译并自校。中文以 Rahmani 拉丁译文为底本，参照对页叙利亚文核词，不冒称直接由叙利亚文翻译。底本为单一见证本，不是现代校勘本；未纳入前言、导论、校勘装置和索引。下一单元 I.2。

## 多模型审校升级

当前翻译库已升级 v3。Luna 初译、Astra 对照审校和修订的请求格式、版本规则及恢复方法见 [REVIEW.md](REVIEW.md)。
