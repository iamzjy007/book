# 收到“继续”时执行

1. 找到仓库（本环境 `/workspace/outputs/book`）；先查git状态并获取远端main，不覆盖未提交内容。新环境可重新克隆。只读本目录协议，不能误入原获取目录的next_task。
2. 读取 README、PLAN、GLOSSARY、REPORT、progress.json、queue.json及最近session；恢复入口只依赖落盘文件和Git历史，无需前一会话记忆。
3. 运行 `python christian-text-translations/scripts/check.py`。若源提交后的源档案哈希变化，先比较变更，登记版本迁移，不静默切换底本；若正文/record哈希不同，先修复或重新核验。派生文件可用 `python christian-text-translations/scripts/check.py --refresh` 重建，再运行无参数检查。
4. 检查本地未提交成果、正文中未登记的块、draft和pending推送。先恢复这些内容；不对已哈希确认self_reviewed的单元重复初译。与远端合并冲突时逐项保留正文和待核记录，不使用自动“全取我方”。
5. 由queue第一个非完成、非deferred/blocked任务接续；已有record则从第一个非self_reviewed单元开始，read原文定位前后各一单元及本书术语，完成旧稿自校后再译下一段。未建record先过完整性门槛并冻结单元表。
6. 对疑难、缺损、异文、经文参照、二手译本分别登记。不能因未决注释存在就把正文漏译，也不能因全文译出就隐去待核项。
7. 每单元原子落盘；每篇／每批更新状态和阶段日志，校验、提交、推送main、核远端。未满整书时仅将已实际完成单元记进度。
8. 停止时写实际last unit、下一个unit、源页及下一步。如果意外中止未写日志，以哈希校验和未登记正文恢复，不靠日志推断不存在的译文。无后台任务；“继续”会启动下一阶段，不表示离线仍在翻译。
