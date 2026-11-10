# 收到“继续”时的恢复协议

1. 拉取／读取 `iamzjy007/book` 的main最新版本，先检查本地未提交修改和远端差异，保留未推成果。没有本地环境时从GitHub直接读取本目录。
2. 读README、PLAN、REPORT、progress、queue及sessions最新报告；不执行原研究目录扩展新书目的队列，除非用户改变范围。
3. `books/*/record.json` 是权威状态。运行scripts/refresh.py恢复任何已经落盘但未汇总的记录。不要按README或日志的旧计数覆盖新记录。
4. 取queue.tasks中第一个queued项，按原sequence继续。全部初检后，优先短名单中partial／blocked／metadata／needs_review项，再处理其余未决项。fulltext_online条目可跳过一般性重复检索，后续仍需版本择定和翻译前校勘。
5. 读目标record的attempts、resources、next_action。记录本次真实检索式、实际打开URL、语种、编译者／年代、覆盖范围、是否要求登录／借阅、访问时间。不可把HTTP成功或目录条目自动升级成全文。
6. 有效新结果先原子写回record，重建派生文件；每3—5条或不超过一个传统批次提交成果。网络受阻也要持久化已知信息和具体替代路径。
7. 推送main使用普通提交或GitHub push_files；禁止强推。成功后重新读取main最新提交SHA并核本批关键文件。若不可写，保存本地成果并明确未推送，不能声称完成。
8. 每批sessions报告写明：完成ID、未决项、已尝试入口、下一项及停止原因。用户中断／环境中断后不把running视为后台仍在工作；本项目没有会话结束后自行工作的服务。

用户只需发送“继续”。若同仓库有其他任务，默认按此原始内容获取目录继续；完整指令可写“继续 christian-text-sources 的内容获取”。
