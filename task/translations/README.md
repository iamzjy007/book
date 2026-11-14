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

