# 资源路径：埃塞／伪经骨干补漏 R02

日期：2026-11-13（北京时间）。对照此前三类资源清单查漏；失败站经本地代理 `127.0.0.1:10808` 重试。

本轮新增 **7** 条调查（含 1 条 PO 交叉引用）；并对 R01 的 Beta 入口做代理重试补证。不是 7 部新古书。

## 三类清单对照（是否已纳入正式条目）

### 1. 学术主阵地

| 资源 | 状态 |
|---|---|
| Beta maṣāḥǝft | R01 已立；本批代理重试仍为反爬挑战页 |
| HMML／EMML／EMIP | R01 已立 |
| Princeton Digital PUL Ethiopic | **本批正式纳入** |
| Cambridge CUDL Ethiopian | **本批正式纳入**（代理后 200） |
| Manchester Ethiopic | R01 已立 |

### 2. 英文尽量完整、可溯源合集

| 资源 | 状态 |
|---|---|
| ethiopiancanon.com | R01 已立 |
| Atrons EOTC81 | R01 已立 |
| GitHub cpradmin/ethiopian-bible | R01 已立 |
| Archive 埃塞／正教圣经条目 | R01 已立 |
| ethiopiabible.com 在线读 | **本批正式纳入**（R01 仅地图提及） |
| YHWH Geʽez reader | **本批正式纳入** |
| 商业 Ultimate 案例 | R01 已立 |

### 3. 公版经典译本与校勘（次经／伪经骨干）

| 资源 | 状态 |
|---|---|
| CCEL Charles | R01 已立 |
| Archive Charles Enoch／Dillmann Jubilees | 挂在 ETH-Enoch／ETH-Jubilees |
| Online Critical Pseudepigrapha | **本批正式纳入** |
| Sacred Texts 基督教总索引 | **仍 403**；单篇既往可用，不虚立成功网关 |
| Patrologia Orientalis | **交叉引用**既有 `resource-map-lori_b`＋队列 `csco-po`，不重复建库 |
| STEPBible | **本批正式纳入**独立入口 |

## 本批路径要点

- [Princeton Ethiopic](https://dpul.princeton.edu/ethiopic_manuscripts) — 代理＋宽松 SSL，200。  
- [Cambridge Ethiopian MSS](https://cudl.lib.cam.ac.uk/collections/ethiopianmanuscripts) — 代理 200（直连曾 403）。  
- [OCP](https://pseudepigrapha.org/) — 代理 200。  
- [ethiopiabible.com](https://ethiopiabible.com/read-the-ethiopian-bible-online-in-english/) — 200。  
- [Geʽez reader about](https://www.yhwhyaway.com/about-the-geez-bible.html) — 200。  
- [STEPBible](https://www.stepbible.org/) — 200。  
- PO：交叉引用既有地图；`about.brepolis.net` 仍 403。  
- Beta：代理 200 但是 cookie 挑战页，未计完整首页。

工作记录：[workers/ethiopic_r02.json](workers/ethiopic_r02.json)。

## 断点

`ethiopic-systematic` 三类清单的**正式条目层**已基本齐（Sacred Texts 总索引与 POD 说明页仍阻）。下一步仍可：浏览器过 Beta 反爬、Harden1920／EMML515、本地 EPUB 对照；或切回 e-Clavis ECCA518。
