# 正文获取 · 第三方模型入口

先运行 `python -X utf8 ../workflow.py verify` 和 `python -X utf8 ../workflow.py resume`。读返回的 catalog_record、已有 attempt / locator、版本和 next_action；方法见仓库根目录 christian-text-sources/PLAN.md、CONTINUATION.md。默认按活动范围、queued 优先、未决项最早更新、原序号排序。旧档案 175 条（古代 110、现代 65）；交付时首项 modern:dydi_c:MC04，要核具体 CTDA / Praxis 对象。指定任务时加 `--id modern:dydi_c:MC04`。

从题名和作者定位具体版本，打开相应正文页／馆藏件，记录语言、版次、覆盖、存取限制、实际动作和时间。书目页、选章、手稿索引与完整正文分别保存。此框架跟踪内容获取进度与实际入口；如涉及文件下载，字节级 HTTP 分片续传需由下载工具处理。已有记录指向在线文本时，保留 direct_file、parts、sample_urls 等原字段。

book 存来源项目、ID、状态与 next_action；baseline_json 是导入时的档案。attempt 是历次查找，locator 是版源和正文入口，二者带 observed_at。queue 是可继续的排序视图。每次保存追加本次尝试和新定位，含重试键与旧 revision。示例为格式说明，请用实查数据替换括号：

```json
{"id":"modern:dydi_c:MC04","revision":0,"request_key":"<唯一键>","status":"partial_online","observed_at":"<核验时间>","attempts":[{"date":"<核验时间>","query":"<查询或URL>","result":"<实际看到什么>"}],"locators":[{"url":"<实际URL>","kind":"partial","edition":"<版本或对象>","coverage":"<可见范围>","verification":"<核验依据>","language":"<语种>","rights_note":"<用途限制>","accessed":"<真实访问时间>"}],"next_action":"<下一入口或待核范围>"}
```

status 可取 partial_online、fulltext_online、metadata_only、scan_candidate、blocked、needs_review。定位类型还可用 metadata、restricted、edition_gateway。受阻时保存 attempt 和替代路径，locators 可以为空。全文／部分正文状态必须有对应类型及版本、覆盖、核验。时间用 YYYY-MM-DD 或带时区的 ISO 时间戳。运行 `python -X utf8 ../workflow.py save /path/to/result.json`，再 resume --id 回看本条、无参数 resume 看下一条。完成可用版本核验且准备翻译时，按 [总指南](../README.md) 显式移交；核实在线版本和冻结可译底本是两个阶段。

