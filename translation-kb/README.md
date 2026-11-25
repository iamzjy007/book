# 先知话语英译中知识库

用于把英文基督教文章译成庄重、自然的现代中文。翻译包从和合本中选出与本篇有关的词句和出处，帮助译者保留原文的说话人、语气和比喻。

**直接试用**　把 [Lori 第 133 篇翻译包](examples/lori-133.md) 发给模型，输入“请按本包翻译，逐段核对用词，只交付中文定稿”。包内可以看到为什么 *My armor* 在该篇宜译作“我的军装”。另有 [DYDI 第 003 篇](examples/dydi-003.md) 可供对照。

## 翻译和审校一篇

在本目录运行下列命令。需要 Python 3.9 或更新版本，SQLite 支持 FTS5。制包和查经可以离线完成。

```powershell
python -B lookup.py ../Daily_Words_The_Lords_Glory_with_Lori.txt --book lori --chapter 133 --out 本篇翻译包.md
python -B check_terms.py 本篇翻译包.md 第133篇中文初稿.txt
```

第一条生成可交给模型的单篇文件，输出名请选尚未存在的文件。第二条把模型的初稿与本篇用词逐段核对。独立英文原稿省略 `--chapter`，其他作品用 `--book other`。已有中文合订本也可以直接交给第二条命令，程序会按包内篇号取文。

| 我想做什么 | 入口 |
| --- | --- |
| 查某个词在新约中的不同译法 | `python -B scripture.py --word armor --collection nt --context` |
| 核实整段经文 | `python -B scripture.py --ref "诗篇 23:1-6"` |
| 让同一模型依次做语义复核、朗读和定稿对照 | [多轮审校步骤](maintenance/使用详解.md#用同一模型续审)，入口为 `revision.py`。接入模型服务时搭配 `model_worker.py`。 |

## 哪些文件需要带走

- **聊天模型**只需收到生成的翻译包。
- **在另一台电脑制包和审校**，复制本层的 [bible-style.sqlite3](bible-style.sqlite3)、五个 Python 入口和整个 [kb](kb/) 目录。`kb/` 放共用程序及[完整风格指南](kb/style-guide.md)。
- **维护知识库**用 [maintenance](maintenance/) 中的编辑底稿、构建程序和回归用例。新旧约惯用词可分批导入。[增补与校验方法](maintenance/使用详解.md#后续增补旧约惯用词)
- **继续专项研究**从[词语检索与同一模型多轮审校](research/专项研究.md)读起。互文检索与串珠实验另见[研究课题](research/课题.md)。
