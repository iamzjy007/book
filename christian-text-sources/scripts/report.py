#!/usr/bin/env python3
"""Generate current report from actual durable records, not claimed completeness."""
import json
from refresh import ROOT,LABELS,run
run()
p=json.loads((ROOT/'progress.json').read_text())
lines=['# 内容获取阶段报告','','日期：2026-11-10 UTC。原研究110条均已建档，在线资源获取持续按档案记录推进。','', '| 状态 | 条数 |','|---|---|']
lines += [f"| {LABELS.get(k,k)} | {v} |" for k,v in p['counts'].items()]
lines += ['',f"下一任务：`{p['next_task']}`。详见[继续协议](CONTINUATION.md)和[完整目录](CATALOG.md)。",'','## 统计边界','','对应版本正文可直达不代表古代原作无缺，也不代表扫描逐页已校勘；部分正文包括选译与残篇。扫描候选只有版源／定位，还需打开正文页。仅书目不能算取得原始内容。所有在线资源只留路径，临时页面与预览不入库。','','## 已有基础检索','','110条已逐条保存Internet Archive题名索引请求与至多3个候选。132个原研究出处URL已作访问检查，结果在档案attempts中；其中HTTP 200也可能是人机验证。人工判定单独记录，自动结果不会升级全文状态。','','## 阶段记录','']
lines += [f'- [{x.name}](sessions/{x.name})' for x in sorted((ROOT/'sessions').glob('*.md'))]
(ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')
