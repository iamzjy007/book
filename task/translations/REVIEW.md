# v3 多模型翻译与审校

现有库已迁移到 v3。完整结构由 schema.sql 与 review-schema.sql 组成。106 个已有译文单元各导入一份历史版本，作者登记 unknown (legacy import)。原自校状态保留，独立审校从尚未审查开始。

translation_version 追加保存正文、版本号、哈希、冻结底本指纹、执行者、操作、实际日期和建档时间。unit_review 绑定具体 version_id，记录审校人、类型、结论、来源核验、问题及日期。review_queue 列当前版本尚未通过原文对照审校的单元。原 book.status 仍表示初译／自校状态，独立审校由 resume.independent_review 返回。

先执行 python -X utf8 ../workflow.py verify，再执行 python -X utf8 ../workflow.py resume --id lori_b:lb09。next_review 返回 version_id、unit_id 和正文哈希。按 version_id 查询 translation_version.body，结合 edition 和原文定位逐句核验。初译请求可以加 model 字段，新版记录执行模型；旧格式仍兼容。

审校请求通过原有 save 命令提交，JSON 示例中的占位符须换成实际内容，revision 取书籍当前修订号：

{
  "id":"lori_b:lb09", "unit":"1", "revision":0,
  "request_key":"<唯一键>", "operation":"review",
  "version_id":1, "body_sha256":"<所审正文哈希>",
  "reviewer":"gpt-6-astra", "review_type":"source_check",
  "outcome":"changes_requested",
  "source_evidence":[{"locator":"<真实页码章段>","checked":"<实际核对范围>"}],
  "findings":[{"source":"<原文>","issue":"<问题>","suggestion":"<依据及建议>"}],
  "review_note":"<真实结论>", "observed_at":"<实际日期>",
  "next_action":"<下一动作>"
}

review_type 可取 source_check、style、human；outcome 可取 approved、changes_requested、unresolved。style 通过仍保留原文审校待办。程序检查数据关联与版本；审校者负责实际语义核验。执行者与日期须如实填写。

修改正文使用 operation=revise，给出 unit、expected_body_sha256、完整 body、model、review_note 及通用字段 id、revision、request_key、observed_at、next_action。程序保留旧稿、追加新版，并将该单元恢复 draft。旧审校绑定旧稿，新版重新进入待审队列。完成本段自校后再审最新版。建议一次修订一段并完成自校，再改下一段。

初译已完成的书可以继续 review/revise。独立审校从 review_queue 领取，与原初译 queue 独立。原队列完成不代表已通过第二模型审校。同一版本同类型以最后一次结论为准；修改文本或重新存为新版本后须重新审校。

迁移命令为 python -X utf8 ../translation_reviews.py。首次迁移会备份到 state.v2-backup.sqlite3，重复执行安全；备份留本地。新种子生成也自动迁移到 v3。测试命令 python -X utf8 ../test_translation_reviews.py 使用副本验证批准、重试、修改失效和过期审校回滚。

当前支持单元级审校；整章统校可将逐项意见挂入相关单元。后续如需多版本底本切换或整书发布签核，应单独设计版本迁移及发布记录。

