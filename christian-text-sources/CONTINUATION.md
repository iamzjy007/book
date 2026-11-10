# 收到“继续”时的恢复协议

1. 拉取／读取 `iamzjy007/book` 的main最新版本，先检查本地未提交修改和远端差异，保留未推成果。没有本地环境时从GitHub直接读取本目录。
2. 读README、PLAN、REPORT、progress、queue及sessions最新报告；当前执行近现代65条的内容获取，保留古代110条；不执行原研究目录扩展新书目的队列。
3. `books/*/record.json` 是权威状态。先运行scripts/import_modern.py恢复可能先于manifest落盘的导入档案，再运行scripts/report.py恢复派生汇总；这两个命令均不访问正文网络。不要按README或日志的旧计数覆盖新记录。
4. 取queue.tasks第一个任务继续：active_scope来源优先，其中queued按sequence排列；同来源初检完成后，按updated_at最早的未决项回访，避免某一受阻条目反复占据首位。fulltext_online条目可跳过一般性重复检索，后续仍需版本择定和翻译前校勘。
5. 读目标record的attempts、resources、next_action。记录本次真实检索式、实际打开URL、语种、编译者／年代、覆盖范围、是否要求登录／借阅、访问时间。不可把HTTP成功或目录条目自动升级成全文。
6. 有效新结果先原子写回record，重建派生文件；每3—5条或不超过一个传统批次提交成果。网络受阻也要持久化已知信息和具体替代路径。
7. 推送main使用普通提交或GitHub push_files；禁止强推。成功后重新读取main最新提交SHA并核本批关键文件。若不可写，保存本地成果并明确未推送，不能声称完成。
8. 每批sessions报告写明：完成ID、未决项、已尝试入口、下一项及停止原因。用户中断／环境中断后不把running视为后台仍在工作；本项目没有会话结束后自行工作的服务。

用户只需发送“继续”。若同仓库有其他任务，默认按此原始内容获取目录继续；完整指令可写“继续 christian-text-sources 的内容获取”。


## 当前交接点（近现代内容获取）

请读sessions中编号最大的阶段报告及progress.json的next_task，不能沿用历史报告里的旧断点。当前来源为 `modern-christian-resources`。近现代ID带 `modern:` 前缀，原ID和来源文件保存在provenance及inventory/modern-import.json。导入脚本可幂等重复运行，不覆盖已有获取状态；全量65条接入后不再重复建档。

中断可发生在单条保存、汇总或推送之间：先保留本地文件，再核远端main；重建派生文件后，从queue取下一项。未保存完成的单条重新核查，已落盘的attempts、resources、updated_at和next_action是续接依据。每批推送后核远端SHA与关键文件；不依赖会话记忆。用户说“继续”即可执行本目录当前来源。

旧交接点：古代110条首轮初检完成，59条仍需补齐，首项原为 `dydi_a:east-aphrahat`。当前不优先执行此历史断点；其具体next_action仍在原档案中保留。没有安装后台服务，会话结束后不会继续自行获取。
