# 书目调查 · 第三方模型入口

在此目录运行。默认项目 christian-literature-catalog；切到现代项目必须明确指定。每次先 verify，再 resume：

```sh
python -X utf8 ../workflow.py verify
python -X utf8 ../workflow.py resume
python -X utf8 ../workflow.py resume --id eclavis-systematic
python -X utf8 ../workflow.py resume --project modern-christian-resources --id versions
```

读取返回的规约路径、对应 CONTINUATION.md 和 cursor。埃塞 R02 之后有多个未决目标，选取一个记录在案的目标；e-Clavis 已扫描 177 项，下一项 ECCA518；现代 versions 从 dydi_a:willard-renovation 的版本线索接续。存量记录为 365 份调查、361 项资源，古今两个项目内的 ID 分别解析。先按别名、原题、机构及原调查检查重复。对同作品新增补证时引用旧 ID。

**组织与时间查询。** project / protocol 存项目与规约，task / checkpoint 保存研究线和历史版本，resume 取最新检查点，resource / observation / evidence / scan_item 保存事实。source_file 存旧原件；receipt 存新调查请求（含未挂书目的证据）。时间查询示例：

```sql
SELECT project_id,title,observed_at,updated_at FROM resource ORDER BY observed_at DESC;
SELECT ordinal,external_id,decision,observed_at FROM scan_item ORDER BY ordinal DESC LIMIT 10;
SELECT url,detail_json,observed_at FROM evidence WHERE project_id=? AND resource_id=?;
```

**保存格式。** 下面是 versions 的请求轮廓，尖括号须替换成实际核验结果。取 resume 返回的 revision 和完整 cursor，复制旧游标后只改本轮已证实的字段。source URL、实读范围和未决事项保留原义。

```json
{"project":"modern-christian-resources","id":"versions","revision":0,"request_key":"<一次性提交键>","observed_at":"<YYYY-MM-DD>","finding":"<本次结论与限制>","next_action":"<下一核查动作>","cursor":{"record_id":"dydi_a:willard-renovation","last_verified_url":"<实查URL>","date":"<核验日>","scope":"<实读范围>"},"observations":[{"id":"<新调查ID>","resource_id":"dydi_a:willard-renovation","finding":"<版本判断>"}],"sources":[{"resource_id":"dydi_a:willard-renovation","url":"<实查URL>","read_scope":"<实际查阅内容>"}]}
```

新增资源用 resources 数组，每项给 id、title、kind 和具体书目字段。observations 追加调查，sources 挂到资源；尚无法挂书目的来源仍留在 receipt。调查可选 task_status 和 recommended_task（同项目已有任务）。按实查逐项保存 e-Clavis 时还须给 scan 对象，字段 ordinal、ecca（字符串）、title、url、decision，可选 resource_id。必须匹配上次 next_ecca 和连续序号；保留原游标的未决问题，填写 last_completed_ecca/title、下一题名、ID、URL。索引重排应先核对前后稳定 ID，另行迁移断点。按 [总指南](../README.md) 执行 save、重试与读回。业务规则详见两个原项目的 PLAN，完整性、访问失败、未查得和已确认分开登记。

