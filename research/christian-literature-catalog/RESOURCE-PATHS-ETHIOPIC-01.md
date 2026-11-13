# 资源路径：埃塞俄比亚／吉兹文献 R01

日期：2026-11-13（北京时间）。启动队列任务 `ethiopic-systematic`；本轮为资源地图与缺书调查，**不推进** e-Clavis 字母游标（下一项仍为 Apocryphal Gospel of John ECCA518）。

新增调查 **12** 条（9 个入口／合集网关＋以诺／禧年／Meqabyan）；另对既有 4 条作品做 `supplements` 补证，**不复制成新作品**。计数不是 12 部新缺古书。

## 去重摘要

| 已有记录 | 本批动作 |
|---|---|
| `dydi_c:C09` 诸王荣耀 | 仅补 Beta 主站 URL 说明／正典语境 |
| `dydi_c:C10` Senodos | 补教会规程英译拼装表线索 |
| `dydi_c:C12` 约西蓬 | 补“无公版吉兹→英全译、仅近似”声明 |
| `lori_b:lb02` 使徒遗范 | 补 Harden 1920 埃塞传本英译指针 |
| 个别 vHMML 稿号（e-Clavis 批次） | 不重复立条；本批只记 HMML／EMML 总入口 |
| `EOTXC_HOLYSCRIPTS_ALL_BOOKS` | 404；改记可打开 Archive 条目 |

完整证据见 [workers/ethiopic_r01.json](workers/ethiopic_r01.json)、[resource-map-ethiopic.md](resource-map-ethiopic.md)。

## 入口与合集网关

### Beta maṣāḥǝft

- [CAe 可访问镜像](https://cae.ethiopicist.com/) — HTTP 200；作项目族入口。限制：本轮 `betamasaheft.eu` SSL 失败；不等于已读全部作品 TEI。
- [betamasaheft.eu](https://betamasaheft.eu/) — 规范主站；本轮未打开成功。

### HMML／EMML

- [EMML 数字化完成说明](https://hmml.org/stories/the-ethiopian-manuscript-microfilm-library-is-now-digital/) — 实际读胶卷数字化与 Reading Room 上线、约 4000 件描述里程碑。
- [Collection Guide PDF](https://hmml.org/assets/pdf/HMML_Ethiopian_Manuscript_Collection_Guide.pdf) — HTTP 200 确认 PDF；未通读导读全文。
- [vHMML Reading Room](https://www.vhmml.org/readingRoom/) — HTTP 200 入口；未整库翻页。

### 英文拼装与教会侧入口

- [ethiopiancanon.com/sources](https://ethiopiancanon.com/sources) — 实际读分卷来源、Meqabyan 手稿路径、八卷教会规程、Josippon 近似说明。
- [Atrons EOTC 81](https://atrons.et/library/eotc81) — 实际读 Amharic／Geʽez／KJVA 三选项；KJVA≠吉兹直译。
- [CCEL Charles OT Pseudepigrapha](https://www.ccel.org/ccel/charles/otpseudepig) — 实际读摘要与格式列表。
- [GitHub cpradmin/ethiopian-bible](https://github.com/cpradmin/ethiopian-bible) — 实际读 README：Geʽez＋转写为主。
- [Manchester Ethiopic](https://www.digitalcollections.manchester.ac.uk/collections/ethiopic) — 实际读 45 件说明、Enoch MS 23、Magdala 出处。
- [Archive EOTC Bible 条目](https://archive.org/details/ethiopian-orthodox-tewahedo-church-bible-bible)、[Etiopbiblia](https://archive.org/details/Etiopbiblia) — HTTP 200；未通读。
- [Amazon B0FFNHTD3W](https://www.amazon.com/dp/B0FFNHTD3W) — 商业 Ultimate 合集案例；本地另有同名 EPUB。不作官方底本。

### 在线阅读线索（轻量核验）

- [ethiopiabible.com](https://ethiopiabible.com/read-the-ethiopian-bible-online-in-english/) — HTTP 200；部分公版书卷在线。
- [Geʽez reader 说明](https://www.yhwhyaway.com/about-the-geez-bible.html) — HTTP 200；进行中转写，非全库。

## 新增作品调查

### 以诺一书

库存：本地《01以诺一书.pdf》等为线索，本批未核正式收录映射。

- [Charles Enoch Archive](https://archive.org/details/thebookofenoch00unknuoft) — 条目可打开；未通读。
- ethiopiancanon 来源表：Charles 1912 → 埃塞 42 章划分。
- Manchester 集合说明提及 MS 23；未开图像。

### 禧年书

库存：本地《06禧年书.pdf》线索未核。

- [Dillmann Liber Jubilaeorum](https://archive.org/details/liberjubilaeorum00dilluoft) — 条目可打开；未通读。
- ethiopiancanon：Charles 1902 → 埃塞 34 章。

### 1–3 Meqabyan

- ethiopiancanon：EMML 515／BnF Abb.55／EMML 652；署名更正说明已读。
- 本批未打开 EMML 515 图像；英译有版权声明。

## 待访／失败

- Princeton Ethiopic Digital PUL：超时  
- Cambridge CUDL Ethiopian：403  
- Online Critical Pseudepigrapha：超时  
- `betamasaheft.eu`：SSL  
- 旧 Archive `EOTXC_HOLYSCRIPTS_ALL_BOOKS`：404  

## 断点

- **e-Clavis**：仍停在 Apocryphal Gospel of John（ECCA518）。  
- **ethiopic-systematic**：本批资源地图完成；下一步见 `workers/ethiopic_r01.json` 的 `next_cursor`（Harden1920／EMML515／本地 EPUB 对照／待访馆藏）。  

本批未做大陆／港台正式出版穷尽检索，不作“未出版”结论。
