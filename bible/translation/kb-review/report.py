"""Build the Chinese reading guide from the accepted ledger and local review index."""
from collections import Counter
from contextlib import closing
from datetime import datetime
from urllib.parse import quote
import json
import sqlite3

from scan import HERE, TRANSLATION, selected


def make_report(cache=None):
    ledger=json.loads((HERE/"changes.json").read_text(encoding="utf-8"))
    totals=Counter(e["work"] for e in ledger["edits"])
    units=set((e["book"],e["unit"]) for e in ledger["edits"])
    order="雅煞珥书 以诺一书 禧年书 所罗门智训 巴录一书 多比传 犹滴传 以斯帖补篇 便西拉智训 耶利米书信 但以理补篇 马加比一书 马加比二书 马加比三书 马加比四书 以斯拉一书 以斯拉二书 十二族长遗训 黑马牧人书 十二使徒遗训 彼得启示录".split()
    names={b["id"]:b["title_zh"] for b in selected()}
    with closing(sqlite3.connect(cache or TRANSLATION/".cache/kb-review/corpus.db",timeout=60)) as db:
        counts={w:(book,n,vs) for w,book,n,vs in db.execute(
            "SELECT work,min(book),count(*),count(verse) FROM corpus GROUP BY work")}
        sim=db.execute("SELECT count(similarity) FROM corpus").fetchone()[0]
        nref=db.execute("SELECT count(*) FROM parallels").fetchone()[0]
        nname=db.execute("SELECT count(*) FROM name_use").fetchone()[0]
        nphrases,nhits=db.execute("SELECT count(*),count(ref) FROM phrase_check").fetchone()
        sequence={(b,u,k):rid for rid,b,u,k in db.execute("SELECT rowid,book,unit,block FROM corpus")}
        titles={}
        patriarch=""
        for b,u,k,en,zh in db.execute("SELECT book,unit,kind,en,zh FROM corpus WHERE kind IN ('h1','h2') ORDER BY rowid"):
            if b=="testaments-of-the-twelve-patriarchs" and en.startswith("THE TESTAMENT OF "):
                patriarch=zh
            titles[b,u,en]=patriarch+" · "+zh if b=="testaments-of-the-twelve-patriarchs" and en.startswith("CHAPTER ") else zh
        assert set(counts)==set(order)
    chunks=sum(len(b["units"]) for b in selected())
    nblocks=sum(n for _,n,_ in counts.values())
    verses=sum(n for _,_,n in counts.values())
    lines=[
        "# 二十一部典外文献英中审校记录",
        f'本次依指定英文 EPUB 校订，采用[翻译知识库](https://github.com/iamzjy007/book/commit/{ledger["framework"]})。截至 {datetime.now():%Y-%m-%d %H:%M}，已在 {len(units)} 个英文文件单元中核定 {len(ledger["edits"])} 处修改，并写入正式段稿和可直接阅读的 TXT。可以[逐书对读英文、审前与审后](修订对照.md)，也可以查看[机器可读的完整记录](changes.json)。',
        "## 可以先读的几处",
        "- **《便西拉智训》26:28。** 原译作“主必为他预备刀剑”。英文是 *prepare him for the sword*，被预备的是那个人。现译“主必使他落在刀剑之下”，读者就能听出这是罪人的结局。",
        "- **《禧年书》23:25。** 定稿为“才三周大的孩子，看起来却像百岁老人”。我在中间稿按 47:9 的历法推成了三个七年期。回看本章幼童白头的异象、已有校注及 Wintermute 英译所用的 infant，保留“三周”有更直接的依据。这次撤回保存在改订记录的 earlier 项中。[Wintermute 英译，第 23 章](https://azahari.blog/wp-content/uploads/2025/01/the-old-testament-pseudepigrapha-volume-2-.pdf)",
        "- **《便西拉智训》6:21。** 愚昧人觉得智慧沉重难当。原译说“他便急忙将她抛开”，英文说的是 *will not hesitate*。修订为“他便毫不迟疑地把她抛开”，保留智慧的拟人，也保留他不肯忍耐的态度。",
        "- **《黑马牧人书》。** 劝人彼此照应时，*bear one another’s burdens* 与加拉太书 6:2 的“互相担当”相合。改为“彼此和睦，彼此探望，互相担当重担”，三个动作各有着落。",
        "- **《十二族长遗训》。** 五处卷首的 *copy* 恢复为“抄本”。流便一篇现在读作“这是流便遗训的抄本，记下他一百二十五岁临终前给众子的吩咐”。",
        "- **《以斯拉上》5:22–23。** 初稿把城名译成“耶利哥的子孙”，现按归回名录改为“耶利哥人三百四十五人”。相邻一句虽同样可以借用和合本“西拿人”的称法，却要保住本底本的三千三百三十人。和合本《以斯拉记》2:35 在这里是三千六百三十名。",
        "## 逐书结果",
        "点击书名可读本次汇编的译文。段块数含标题和无节号文字，经节数只计底本有节号之处。“改订”以一条有原文依据的段落改动计。",
        "| 作品 | 英中段块 | 有节号 | 改订 |", "|---|---:|---:|---:|",
    ]
    for w in order:
        book,n,v=counts[w]
        display={"犹滴传":"犹迪传（文件题《犹滴传》）","巴录一书":"巴录书","以斯拉一书":"以斯拉上","以斯拉二书":"以斯拉下"}.get(w,w)
        lines.append(f"| [{display}](../output/{quote(names[book]+'.txt')}) | {n:,} | {v:,} | {totals[w]} |")
    lines.extend([
        f"| 合计 | {nblocks:,} | {verses:,} | {len(ledger['edits'])} |",
        "## 怎样理解覆盖范围",
        f"在 {chunks} 个 EPUB 文件单元中逐块核对英文来源、中文段号与节序；{sim:,} 个段块均经本地英中语义相似度筛查。逐节检查否定与疑问、译文异常短缩、语法关系和词义线索。扫描另找到 {nname:,} 个经库人地名用例与 {nref} 个和英文圣经高度相近的段落。相似度是排查顺序；“改订”栏仅计读过英文、上下文并实际落笔的地方。这套检查仍可能漏过两种语言都通顺的细微误解。",
        f"对 {nphrases:,} 个正文与说明段另运行了全经词语检索，{nhits:,} 段返回带独立邻词的参考经节。例如《多比传》8:5 把荣耀、名、称颂、永远连在一起，可与诗篇 72:19 对读。这里的中文原已贴切，予以保留。另有两类误触：分出一份贡税时的 portion、食物使人有力时的 strength。实测后已[修订知识库](https://github.com/iamzjy007/book/commit/{ledger['framework_revision']})，并使已有版本说明能逐轮传给审校模型。",
        "保留了底本自身的文体和异文。《禧年书》3:6 的“骨中的骨，肉中的肉”与创世记吻合，沿用现译。《雅煞珥书》谱系中的 Shiloh 指人时译“示拉”，作地名时译“示罗”。书中已有的特例按原项目词表核对。神亲口说话用第一人称；叙事者、祷告者、书信作者及引语各守原有声音。",
        "本版把《耶利米书信》置于《巴录一书》第五章后，另立标题并从第 1 节重新编号。因此 21 部作品见于 20 份 TXT。《雅煞珥书》对应本目录的英文底本译稿；另存的希伯来文校订版有独立校勘记录。",
        "可在仓库根目录运行 `python -B -X utf8 bible/translation/kb-review/reconcile.py`，重新与英文锚点、正式段稿及二十份 TXT 核对。[本项目的专名及特例](../glossary.json) · [编译式多轮审校研究](../../../translation-kb/research/专项研究.md) · [本地语义模型资料](https://huggingface.co/intfloat/multilingual-e5-small)。",
        f"英文 EPUB 的 SHA-256 为 `{ledger['epub_sha256']}`。",
    ])
    reader=ledger.get("reader")
    if reader:
        groups=reader["samples"]
        total=sum(s["blocks"] for s in groups)
        decisions=Counter(c["verdict"] for s in groups for c in s["cases"])
        lines.extend(["## 各卷各抽一段独立复读",
            f"本地 Qwen3-4B 另读了 {len(groups)} 组、共 {total} 段英文和原译，按语义相似度、否定和句法线索选择复读位置。给出的提案逐一回到原文裁定。{decisions['核准线索']} 条线索核准，{decisions['另拟修订']} 条另拟了译文，{decisions['保留']} 条保留原译。完整取舍见[逐条记录](changes.json)。这批数字仅描述所抽各段，不能据以推算整书错误率。",
            "例如《所罗门智训》14:20，模型发现了指代不清，却把受拜者当成工匠。17–19 节交代受拜的是王，负责雕刻的是工匠。因此定稿明确写出二者。《多比传》1:2 的建议则要删掉地名基低斯，回查指定英文后保留原译。"])
    joined=""
    for idx,line in enumerate(lines):
        contiguous=idx and (line.startswith("|") and lines[idx-1].startswith("|") or line.startswith("- ") and lines[idx-1].startswith("- "))
        joined+=("" if idx==0 else "\n" if contiguous else "\n\n")+line
    entries=["# 逐书修订对照","各卷按英文底本顺序列出本次实际修改。每处先列原译和修订，再给出足以复查的英文及取舍。开卷说明和无节号段落按段号定位。"]
    for w in order:
        entries.append("## "+w)
        changes=sorted((e for e in ledger["edits"] if e["work"]==w),
                       key=lambda e:sequence[(e["book"],e["unit"],e["block"])])
        for e in changes:
            pos=titles.get((e["book"],e["unit"],e["section"]),e["section"])
            if pos=="EPISTLE OF JEREMIAH":
                pos="书信"
            if e["verse"]:
                pos+=f' · 第 {e["verse"]} 节'
            else:
                pos+=f' · {e["block"]}'
            link=f'../zh/{e["book"]}/{e["unit"]}.json'
            entries.extend([f'### {pos}　{e["category"]}',f'**审前**　{e["before"]}',
                            f'**审后**　{e["after"]}',f'**英文**　{e["en"]}',
                            f'{e["reason"]} [段稿 {e["unit"]}/{e["block"]}]({link})'])
    for name,body in (("审校报告.md",joined),("修订对照.md","\n\n".join(entries))):
        target=HERE/name
        tmp=target.with_suffix(".md.tmp")
        tmp.write_text(body+"\n",encoding="utf-8")
        tmp.replace(target)


if __name__=="__main__":
    make_report()
