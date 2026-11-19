# 先知话语英译中知识库

**新的翻译研究课题**　[从经文互文到译文取舍](research/课题.md) 说明怎样分开检验出处、分句意义和中文语感，附 66 卷跨译本实验、语义辖域示例和第三方模型盲评办法。现有制包命令会在没有明确出处或长引命中时，用全经索引寻找平行段落，并列出需要复核的原文和经文用词。

**只想试用**　把 [单篇翻译包](packet-example.md) 发给聊天模型，输入“请按文件要求翻译”。包内是 DYDI 第 003 篇全文，以及该篇“浇灌”的已确认约定。

**已有初稿**　同一个模型可以接着做语义复核、中文朗读和定稿对照。 [六个真实片段的逐轮记录](revision-cases.json) 保留了每处改动及理由。研究设计与验收结果见 [词语检索与多轮审校专项研究](专项研究.md)。

## 为另一篇原文生成翻译包

在本目录打开 PowerShell，使用 Python 3.9 或更新版本，SQLite 需支持 FTS5。脚本仅用标准库，制包和查经均可离线运行。手机或网页聊天模型只需收到生成的 Markdown。

```powershell
python lookup.py ../DYDI_Messages_Declaring_Your_Destiny.txt --book dydi --chapter 30 --out dydi-030.md
python lookup.py ../Daily_Words_The_Lords_Glory_with_Lori.txt --book lori --chapter 1 --out lori-001.md
```

独立的 UTF-8 原稿省略 `--chapter`。其他作品用 `--book other`，只检索通用条目。合订本按章标题提取正文，略过采集网址等元数据。每次选一个新输出文件名。上传生成的 Markdown 即可。

默认包包含精简指令和当前命中的提示。若首次委托重要篇章，或希望模型逐项遵守全部指南，在命令末加 `--full-guide`。也可单独把 [完整风格指南](style-guide.md) 与原文交给模型。

## 条目的依据与边界

[SQLite 库](bible-style.sqlite3) 内有 37 条风格与作品规则。16 条来自原指南，9 条来自首轮用户评阅，3 条来自用户复评（其中 1 条修订旧规则），其余 9 条来自新增 18 篇的英中审校。新条目标记为“编辑审校”，供后续译者核对语境，用户明确裁定的局部译法优先。[可读规则源](rules.sql) 逐条列出英文触发表达、中文处理、作品、适用范围及出处。

## 离线经文与译名

数据库另收简体《新标点和合本》与 World English Bible 各 66 卷，以及 [186 条有经节出处的人名、地名、称号和常用搭配](scripture-terms.txt)。这些属于底本参照。已评阅的作品约定继续优先，例如第 003 篇仍保留“我的荣耀”。[底本来源、逐卷条数、节号差异及文件校验值](经文底本与覆盖.md)

生成翻译包的命令同上。篇内标有 AMPC 或 NKJV 时，优先从独立出处行提取章节目，附和合本中文供核对。已有准确的和合本引文原样保留，来源标识照录。其他篇章优先查原文明引的章节目，最多显示两处，每处最多取所引范围前三节（底本合节完整显示）。没有可用出处时，脚本按段每四词取连续八个英文词，找到只匹配一节的片段时附一处双语候选。短引及改写可能漏检。直接查经支持罗马数字卷名如 I Corinthians、常见缩写如 Ps. 以及不连续节号如 Revelation 10:3, 5-7。

需要完整经文范围，或想查一个尚未建立映射的词，可直接运行下列命令。查词最多显示二十条，按所输入的原文片段匹配。

```powershell
python scripture.py --ref "诗篇 23:1-6"
python scripture.py --ref "Genesis 24:30"
python scripture.py --find "恩惠慈爱"
```

## 从词或短语查到一段经文

```powershell
python scripture.py --word mercy --collection psalms --context
python scripture.py --word "guard your heart" --collection paul --context
python scripture.py --word "保守" --collection wisdom
python scripture.py --word "mustard seed" --collection nt
```

`--word` 先列适用义项，再给最多六处中英经文。英文依次检索整组词、邻近共现和同节共现，支持词形变化。中文支持从和合本措辞反查。限定范围可选诗篇、智慧书（约伯记、箴言、传道书、雅歌）、保罗十三封书信、新约，省略时查全经。`--context` 附同章前后各一节中文。需要更长上下文、底本合节或节号有异时用 `--ref`，两译本分别显示其节号。

查 *mercy* 时，诗篇 25:6 的恳求能看到“怜悯”，诗篇 23:6 的成对措辞能看到“恩惠慈爱”。查 *burden* 时，加拉太书 6:2 是彼此担当重担，6:5 是各人担当自己的担子。模型先看施事、动作和受词，再决定借哪几个字。

单篇翻译包自动执行这一步，通常无需手动查词。每篇最多附四处新增词语用例，其中全经自动找到的线索最多一处；另选最多三条句法提示。各条用例给出命中的英文、出处和中文。完整的 [词义与搭配表](word-senses.txt) 和 [句法表](syntax-patterns.txt) 也能直接阅读。

## 用同一模型续审

下面以已有英中合订本为例。单篇原稿和初稿可省略 `--chapter`。作业文件保存原稿副本、当前译文和各轮修改；可以中断后继续。

```powershell
python revision.py init lori129.db ../Daily_Words_The_Lords_Glory_with_Lori.txt ../Daily_Words_The_Lords_Glory_with_Lori_zh.txt --book lori --chapter 129
python revision.py next lori129.db --out 本轮.json
python revision.py apply lori129.db 模型答复.json
```

把“本轮.json”给同一个聊天模型，请它按其中格式返回 JSON。每次用一个新文件名导出下一轮。它可以提交零处修改。语义和朗读都查过，定稿对照再无可说明的改善，才标为“已收敛”。若定稿对照发现新问题，会再走一轮；最多六次。遇到改稿循环保留上次译文，达到上限仍有改动则记录待复核。

**审校已有校注的作品时，在初始化作业时带上原决定。** 可重复使用 `--note "本节已有的译法、出处和理由"`。例如《禧年书》23:25 的英文作 *a child of three weeks*，中文参考和本章上下文都支持“三周大的孩子”；第 47 章另有“七年期”的用法。模型每一遍都能看到这一层证据。若某个词已经由评阅者明确锁定，再用 `--protect "需要保留的原有措辞"`。

有兼容 Chat Completions 的模型端点时，下面的命令会连续执行。本例 URL 是本机服务的配置示例。模型名称填服务实际提供的标识；需要鉴权的服务可通过环境变量 `TRANSLATION_API_KEY` 提供密钥。配置的服务会收到本篇英中材料和本轮所需的知识库提示。[接口协议示例](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

```powershell
$env:TRANSLATION_CHAT_URL = 'http://127.0.0.1:8080/v1/chat/completions'
$env:TRANSLATION_MODEL = '你的模型标识'
python revision.py run lori129.db --worker python model_worker.py
python revision.py export lori129.db --out 定稿.txt
python revision.py history lori129.db --out 审校记录.json
```

中断后可重用同一条 `run` 命令。已完成的轮次存于事务中。同一作业绑定首次自动运行的模型配置。格式错误或服务失败默认每轮尝试三次，耗尽后保留进度。每处改动要能在英文和当前中文中定位，保留原段落和已锁措辞。可在初始化时用 `--protect "准确的原有中文"` 追加锁定。对带出处的现成和合本整节，程序识别与底本汉字一致的连续引文；节号不全、改写或只引半节时，仍由模型结合上下文复核。

## 验证与重建

```powershell
python validate.py --books ..
python wordstudy.py
```

第一条运行回归测试、在内存中重建并比对词义和搭配索引、核对两个底本和示例包，并统计两本文库的篇级触发情况。仅验证分发组件时省略 `--books ..`。第二条从已有 SQLite 经文和词义表重建词语索引。更换经文底本时按 [底本说明](经文底本与覆盖.md) 重建。

## 怎样吸收评语

逐条记录你确认的原句、上下文和译法。仅改动一处时，确认范围限于该处。可复用的意见补上适用条件，再找一个相似而应区别处理的例子验证。同步更新 SQL 和 SQLite 后，拿一篇未评过的原文生成新包，检查提示能否在合适的地方出现。整篇样本经你明确认可后再纳入范例。
