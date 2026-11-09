# 历史及教父作品翻译

2026-11-09 信望爱《使徒教父著作》参考修订已完成，实际对应范围、改译与底本差异见 [reference-review](reference-review/README.md)。网站只覆盖其中的使徒教父选集，不代表本轮重新审校了全部54项历史教父作品；次经参考修订另见 [上级记录](../reference-review/README.md)。

用户授权范围：原清单暂缓的54项，按原书顺序全译。遵循根style-guide.md及上级README中的忠实、自然、庄重原则；不把历史叙述或论辩改写成先知宣告。中文参考有对应段落时借鉴，但原文缺有和不同读法以英文为准。

本目录pipeline、queue、assemble独立运行，不能操作上一轮队列。每单元读取全部blocks、核对原XHTML及资产，逐段完整翻译、两轮审校，再reviewed=true；长单元先保存drafts，禁止摘要代替全文。refs/notes据实际填写。完成当前任务后持续queue.py claim自身名字直到null，不等待主代理。主代理统一汇编和推送。

具体恢复方式见上级README；本目录的源指纹、单元格式与上级一致，原EPUB位置已适配。

## 断点续译

在仓库根目录执行：

```sh
python bible/translation/history-patristics/queue.py status
python bible/translation/history-patristics/queue.py claim 自己的工作名
python bible/translation/history-patristics/assemble.py
python bible/translation/history-patristics/audit.py
python bible/translation/history-patristics/check_names.py
```

恢复时先看仍被认领的任务；同一工作名再次领取会返回原任务。只有确认原工作者已经停止后，才可用 `queue.py release 工作名` 释放其未完成任务。`zh` 保存逐单元译文，`drafts` 保存长章草稿；只有完整翻译、人工复核、结构验证均通过的单元，才标为完成。不得用队列计数代替全文审校，也不得因有草稿就宣称完成。

本阶段共有54项作品、1623个源单元，按原EPUB顺序编排。`output` 中仅汇编已完整译完的作品；未完成作品的已译单元仍保存在 `zh`。`progress.json`、源文指纹及工作队列共同支持中断恢复；若原EPUB内容改变，应先核对差异，不能直接清空进度重做。

`reference-sources.json` 记录实际使用的辅助英文资料。《犹太古史》遇疑似错字时可对照公开的旧英译，但参考本也可能保留同一错误，不能据此声称疑点已解决，更不能用另一版本替换用户指定的底本。相应中文典外文献仅作语言和专名参考。

`presentation-overrides.json` 记录少量经原XHTML核实的排版修正。例如《致奥托吕库斯书》第三卷第10章，英文数字430被排版标记错误拆成4和类似节号的30；汇编时按受源文指纹约束的规则接回“四百三十年”，不生成虚假的第30节。此类修正不删除或重排原文内容。
