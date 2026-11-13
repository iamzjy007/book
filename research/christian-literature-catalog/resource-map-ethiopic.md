# 埃塞俄比亚／吉兹圣经与东方手稿资源地图（第一批）

2026-11-13，`ethiopic_r01`。任务对应队列 `ethiopic-systematic` 与部分 `manuscript-east` 交叉入口。本轮是**目录层与入口核验**：实际打开或请求下列站点首页／说明／来源页；未通读手稿影像全文，未下载全书作翻译底本。作品级条目与补证见 [workers/ethiopic_r01.json](workers/ethiopic_r01.json)、[RESOURCE-PATHS-ETHIOPIC-01.md](RESOURCE-PATHS-ETHIOPIC-01.md)。

## 去重原则（本批强制）

| 情况 | 处理 |
|---|---|
| 已有作品记录（如 `dydi_c:C09` 诸王荣耀、`C10` Senodos、`C12` 约西蓬、`lori_b:lb02` 使徒遗范） | **不新建同名作品**；用 `supplements` 挂新入口 URL |
| 同一机构多镜像（`betamasaheft.eu`／`betamasaheft.awhamburg.de`／CAe） | 记为同一项目族；本批核验失败／SSL 障碍如实写，不另立“新项目” |
| 商业“完整 81 卷英文圣经”与学术拼装本 | 分条记录；标明公版拼装／扩出正典／非教会官方英译 |
| Charles 以诺／禧年公版英译 | 建作品记录一次；CCEL／Archive／ethiopiancanon 作版本入口，不复制成多部古书 |
| HMML／vHMML 已在 e-Clavis 批次中单篇引用 | 本批补**馆藏级总入口**，不重复扫已记具体稿号 |

## 资源能解决什么

| 资源与本轮访问证据 | 能做 | 不能据此声称 |
|---|---|---|
| [Beta maṣāḥǝft](https://betamasaheft.eu/)：本轮 SSL／握手失败；旧记录用过 `betamasaheft.awhamburg.de` 作品页；[CAe 镜像](https://cae.ethiopicist.com/) 200 OK | 埃塞／厄立特里亚手稿与作品 TEI、Clavis、馆藏关联；长期项目 2016–2040 | 本轮未打开主站全文；CAe 命中≠已读吉兹正文；不能当 81 卷英译 |
| [HMML 故事：EMML 已数字化](https://hmml.org/stories/the-ethiopian-manuscript-microfilm-library-is-now-digital/)；[Ethiopian Collection Guide PDF](https://hmml.org/assets/pdf/HMML_Ethiopian_Manuscript_Collection_Guide.pdf)；[Reading Room](https://www.vhmml.org/readingRoom/) 200 OK | 检索 EMML／EMIP／EMDA 等项目号；看目录与影像入口 | 目录开放≠每页可下载；EMIP 大量尚无完整编目；不替代校本 |
| [The Ethiopian Canon · Sources](https://ethiopiancanon.com/sources)：实际读分卷来源表与 Meqabyan／教会规程说明 | 追溯现代英文拼装本的公版底本与缺译说明；对照商业合集 | 不是教会官方英译；Josippon 等为近似；Meqabyan 现署 Clear Text 版权 |
| [Atrons EOTC 81](https://atrons.et/library/eotc81)：实际读 Amharic／Geʽez／KJVA 三入口与结构提示 | 教会侧多语对照入口；看 81 卷结构选择 | KJVA 不是从吉兹新译；不等于单本权威校勘 |
| [CCEL Charles OT Pseudepigrapha](https://www.ccel.org/ccel/charles/otpseudepig)：实际读作品摘要与格式列表 | 公版英译合集入口（含以诺等常用译本） | 1913 旧译；不是吉兹校勘本；收录范围≠埃塞正典清单 |
| [GitHub cpradmin/ethiopian-bible](https://github.com/cpradmin/ethiopian-bible)：实际读 README 摘要 | Geʽez＋转写开源数据层；可对照 | 英译仅对照层；非教会核准译本；许可 CC BY-NC-SA |
| [Manchester Ethiopic MSS](https://www.digitalcollections.manchester.ac.uk/collections/ethiopic)：实际读馆藏说明（含 Enoch MS 23、礼仪书） | 数字化抄本浏览与出处说明 | 45 件子集；含 Magdala 掠夺史；打开单件≠校读 |
| [ethiopiabible.com 在线读](https://ethiopiabible.com/read-the-ethiopian-bible-online-in-english/)：200 OK | 部分独特书卷公版英译在线 | 非 81 卷全覆盖；不等于校本 |
| [YHWH Ya’ Way Geʽez reader 说明](https://www.yhwhyaway.com/about-the-geez-bible.html)：200 OK | 进行中的吉兹—英文对照转写说明与稿本来源 | 目前仅诗篇等部分完成；非完整 81 卷 |
| [Archive：EOTC／Ethiopic Bible 条目](https://archive.org/details/ethiopian-orthodox-tewahedo-church-bible-bible)、[Etiopbiblia](https://archive.org/details/Etiopbiblia)：200 OK；旧链 `EOTXC_HOLYSCRIPTS_ALL_BOOKS` 本轮 404 | 发现阿姆哈拉／吉兹电子本线索 | 条目元数据≠官方定本；须核语种、卷数与 OCR 质量后再用 |
| [Archive：Charles Enoch](https://archive.org/details/thebookofenoch00unknuoft)、[Dillmann Jubilees Geʽez](https://archive.org/details/liberjubilaeorum00dilluoft)：200 OK | 公版校本／英译下载入口 | 未在本轮通读；页界待用时再核 |
| 本地／Amazon「Ultimate Ethiopian Bible」合集 | 作**商业合集案例**对照正典与扩出材料 | 非官方 Geʽez→英全译；含正典外材料；不可单独作学术底本 |
| [Princeton Digital PUL Ethiopic](https://dpul.princeton.edu/ethiopic_manuscripts) | 开放抄本集合 | R01 直连失败；**R02 经代理 10808 已核集合页**（见 ethiopic_r02） |
| [Cambridge CUDL Ethiopian](https://cudl.lib.cam.ac.uk/collections/ethiopianmanuscripts) | 重要馆藏数字化 | R01 直连 403；**R02 经代理已核集合页** |
| [Online Critical Pseudepigrapha](https://pseudepigrapha.org/) | 伪经校勘电子版 | R01 超时；**R02 经代理已核首页** |
| [STEPBible](https://www.stepbible.org/) | 多译本／原文工具 | R02 正式立独立入口（此前仅经 Atrons 提及） |
| Sacred Texts 基督教总索引 | 公版基督教文本总目 | **代理后仍 403**；单篇路径既往可用 |
| Patrologia Orientalis | 东方语系列 | 见 `resource-map-lori_b.md`＋队列 `csco-po`；R02 仅交叉引用 |

### 访问策略

大陆直连失败时，可经本地代理 `127.0.0.1:10808` 重试，并在工作记录写明 `access_note`。代理成功仍须区分：完整正文／反爬挑战页／仅集合首页。

## 与既有任务的关系

- **不取代**进行中的 `eclavis-systematic`（下一项仍为 Apocryphal Gospel of John ECCA518）。
- **启动** `ethiopic-systematic`：本批完成“资源地图＋缺书（以诺／禧年／Meqabyan）＋对 C09/C10/C12/lb02 的入口补证”；后续游标见 `queue.json`。
- **交叉** `manuscript-east`：本批只记 HMML／馆藏总入口；单件稿号仍按作品回查，不承诺整库翻页扫完。
- **交叉** `csco-po`：PO／CSCO 仍在 pending；ethiopiancanon 来源表中的 Harden Didascalia、Grebaut 等只作线索挂到作品，不宣称已扫全套 PO。

## 建议证据链

1. 作品身份：EOTC 81 卷清单／Fetha Nagast 相关计数／CAe 或 Beta 作品 ID。  
2. 原文层：吉兹抄本（HMML／馆藏）→ 印刷校本（Dillmann／Charles 等）。  
3. 英译层：公版 Charles／Brenton／WEB 拼装 ≠ Geʽez 直译；Meqabyan 等单独标注译出路径。  
4. 中文层：大陆／港台／网络分列（本批未做系统中文出版检索）。  
5. 商业合集：对照 ethiopiancanon 分卷来源表，记“多了什么／少了什么／是否标明出处”。
