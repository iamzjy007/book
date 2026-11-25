"""Compile the Chinese reading edition from the frozen source and two translation series."""
import argparse
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import pipeline
from ethiopian_editorial import body_of, render, tag

TITLE = '埃塞俄比亚文献'
CANON = '创世记 出埃及记 利未记 民数记 申命记 约书亚记 士师记 路得记 撒母耳记上 撒母耳记下 列王纪上 列王纪下 历代志上 历代志下 以斯拉记 尼希米记 以斯帖记 约伯记 诗篇 箴言 传道书 雅歌 以赛亚书 耶利米书 耶利米哀歌 以西结书 但以理书 何西阿书 约珥书 阿摩司书 俄巴底亚书 约拿书 弥迦书 那鸿书 哈巴谷书 西番雅书 哈该书 撒迦利亚书 玛拉基书 马太福音 马可福音 路加福音 约翰福音 使徒行传 罗马书 哥林多前书 哥林多后书 加拉太书 以弗所书 腓立比书 歌罗西书 帖撒罗尼迦前书 帖撒罗尼迦后书 提摩太前书 提摩太后书 提多书 腓利门书 希伯来书 雅各书 彼得前书 彼得后书 约翰一书 约翰二书 约翰三书 犹大书 启示录'.split()
EDITORIAL = dict(zip(
    'cover title-page table-of-contents about-the-ultimate-ethiopian-bible preface-to-the-lsv-bible introduction-to-the-lsv-bible preface-to-the-apocrypha introduction-to-the-apocrypha key-scriptures the-good-news-of-salvation exclusive-hardcover-discount about-the-bible genesis-chronologies table-of-nations timeline-of-history ages-and-dispensations map-of-israel jerusalem-in-the-1st-century glossary the-faith-once-delivered covenant-of-the-ccc convictions-of-the-ccc positions-of-the-ccc'.split(),
    '封面 书名页与版权 目录 关于《埃塞俄比亚圣经大全》 《圣经直译标准本》序言 《圣经直译标准本》导论 典外文献序言 典外文献导论 重要经文 救恩的喜讯 获取数字藏书和有声书 关于圣经 创世记年表 万国表 历史年表 时代与经纶 以色列地图 一世纪的耶路撒冷 术语表 从前交付的信仰 基督徒圣约联盟的盟约 基督徒圣约联盟的信念 基督徒圣约联盟的立场'.split()
))


def page(title, contents):
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">'
            f'<head><title>{escape(title)}</title><style>.table-wrap{{max-width:100%;overflow-x:auto}} table{{border-collapse:collapse}} td,th{{border:1px solid;padding:.25em}} img{{max-width:100%;height:auto}} .caption{{display:block;margin:.5em 0 1em;line-height:1.5}}</style></head><body>{contents}</body></html>')


def reading_text(text, name):
    parts = []
    links = []
    for line in text.splitlines():
        if not line.strip():
            continue
        heading = re.fullmatch(r'(#{1,6}) (.+)', line)
        if heading:
            level = len(heading[1])
            ident = f'h{len(parts)}'
            parts.append(f'<h{level} id="{ident}">{escape(heading[2])}</h{level}>')
            if level > 1:
                links.append((f'{name}#{ident}', heading[2]))
        else:
            parts.append(f'<p>{escape(line)}</p>')
    return ''.join(parts), links


def build(draft):
    root = pipeline.ROOT
    source = pipeline.manifest()
    history = root / 'history-patristics'
    hm = pipeline.read(history / 'manifest.json')
    if source['source_sha256'] != hm['source_sha256']:
        raise ValueError('两套译文登记的英文底本不一致')
    mapped = {b['id']: (history, b) for b in hm['sections'] if b['scope'] == 'included'}
    mapped.update({b['id']: (root, b) for b in source['sections'] if b['scope'] == 'included'})
    canonical = iter(CANON)
    missing = []
    docs = []
    targets = {}
    cover_asset = None
    with ZipFile(pipeline.SOURCE) as original:
        media = {}
        for s in source['sections']:
            sid = s['id']
            name = f'{sid}.xhtml'
            links = []
            for unit in s['units']:
                targets[Path(unit['href']).name] = (name, unit['id'])
            if sid in mapped:
                location, book = mapped.pop(sid)
                if [u['id'] for u in book['units']] != [u['id'] for u in s['units']]:
                    raise ValueError(sid)
                title = re.sub(r'^\d+_', '', book['title_zh'])
                body, links = reading_text((location / 'output' / (book['title_zh']+'.txt')).read_text('utf-8-sig'), name)
            elif s['scope'] == 'excluded_canonical_66':
                title = next(canonical)
                body = f'<h1>{title}</h1><p>请参阅正典《{title}》书卷</p>'
            else:
                title = EDITORIAL[sid]
                body = ''
                for unit in s['units']:
                    src = pipeline.source_unit(s, unit)
                    f = root / 'editorial-zh' / (unit['id']+'.txt')
                    if sid == 'table-of-contents':
                        continue
                    if f.exists() or not src['blocks']:
                        zh = f.read_text('utf-8-sig').splitlines() if f.exists() else []
                        if len(zh) != len(src['blocks']) or not all(zh):
                            raise ValueError(f'{f} 与英文段块未对齐')
                        chunk = render(original, s, unit, body_of(original, unit), zh, media)
                        if sid == 'cover':
                            cover_asset, = media
                        body += f'<div id="{unit["id"]}">{chunk}</div>'
                        if unit != s['units'][0] and src['blocks'] and unit['label'] != 'Continuation':
                            links.append((f'{name}#{unit["id"]}', zh[0]))
                        elif unit['id'] == 'c1M3H':
                            links.append((f'{name}#{unit["id"]}', '教会所拒绝的异端教导'))
                    else:
                        missing.append((sid, unit['id'], len(src['blocks'])))
                        body += f'<div id="{unit["id"]}"><p>本页待补译。</p></div>'
            docs.append((name,title,body,links))
            if sid == 'title-page' and (root / 'editorial-zh' / 'machine-drafts.json').exists():
                notes = pipeline.read(root / 'editorial-zh' / 'machine-drafts.json')
                if any('needs_bilingual_review' in item['review'] for item in notes.values()):
                    docs[-1] = (name, title, body + '<p>本版说明：新增散页中部分为初译，仍待逐段核校。原书图件照录。</p>', links)
        contents = body_of(original, {'href': 'OEBPS/c15.xhtml'})
    assert not mapped and next(canonical, None) is None
    for sid,unit,count in missing:
        print(f'{sid} {unit} {count}')
    if missing and not draft:
        raise SystemExit(f'尚有 {len(missing)} 个散页单元须补译')
    title = TITLE + ('（组装校样）' if draft else '')
    def link(name,label):
        return f'<li><a href="{name}">{escape(label)}</a></li>'
    headings = iter('旧约|新约|圣经补篇|通行次经|东正教次经|犹太与基督教传说及伪经|新约典外文献与使徒教父|典外及伪托福音书|彼拉多文献群|典外及伪托行传|典外及伪托启示录|早期教会重要著作、信经与典外史料|古代犹太与基督教史|古代教会书信（按作者）|附录'.split('|'))
    labels = {name: label for name, label, _, _ in docs}
    visible_toc = '<h1>目录</h1>'
    for entry in contents:
        if tag(entry) == 'h1':
            continue
        anchors = entry.findall('.//' + pipeline.X + 'a')
        if not anchors:
            visible_toc += f'<h2>{next(headings)}</h2>'
            continue
        links = []
        for anchor in anchors:
            name, unit = targets[anchor.get('href').split('#')[0]]
            label = labels[name]
            if unit == 'c1M3H':
                name += '#' + unit
                label = '教会所拒绝的异端教导'
            links.append(f'<a href="{name}">{escape(label)}</a>')
        visible_toc += '<p>' + ' · '.join(links) + '</p>'
    toc = '<ol>'+''.join(
        link(name,label) if not links else f'<li><a href="{name}">{escape(label)}</a><ol>'+''.join(link(*x) for x in links)+'</ol></li>'
        for name,label,_,links in docs
    )+'</ol>'
    types = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml','.gif':'image/gif','.webp':'image/webp'}
    manifest = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    manifest += ''.join(f'<item id="s{i}" href="{x[0]}" media-type="application/xhtml+xml"/>' for i,x in enumerate(docs))
    for i, name in enumerate(media):
        props = ' properties="cover-image"' if name == cover_asset else ''
        manifest += f'<item id="m{i}" href="{name}" media-type="{types[Path(name).suffix.lower()]}"{props}/>'
    spine = ''.join(f'<itemref idref="s{i}"/>' for i in range(len(docs)))
    package = (f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="edition">'
               f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="edition">urn:sha256:{source["source_sha256"]}:zh</dc:identifier>'
               f'<dc:title>{title}</dc:title><dc:language>zh-CN</dc:language><meta property="dcterms:modified">2026-11-25T00:00:00Z</meta></metadata>'
               f'<manifest>{manifest}</manifest><spine>{spine}</spine></package>')
    output = root.parent / (title+'.epub')
    with TemporaryDirectory(dir=output.parent) as temp:
        candidate = Path(temp) / output.name
        with ZipFile(candidate,'w',ZIP_DEFLATED) as result:
            result.writestr('mimetype','application/epub+zip',ZIP_STORED)
            result.writestr('META-INF/container.xml','<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
            result.writestr('OEBPS/content.opf',package)
            result.writestr('OEBPS/nav.xhtml',page('目录','<nav epub:type="toc"><h1>目录</h1>'+toc+'</nav>'))
            for name,label,body,_ in docs:
                result.writestr('OEBPS/'+name,page(label,visible_toc if name == 'table-of-contents.xhtml' else body))
            for name,data in media.items():
                result.writestr('OEBPS/'+name,data)
        candidate.replace(output)
    print(f'{output} · {len(docs)} 个条目 · {len(missing)} 个待译单元')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', action='store_true')
    build(parser.parse_args().draft)
