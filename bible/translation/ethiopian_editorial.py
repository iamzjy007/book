"""Read the source layout of the editorial pages and align it to their translations."""
import re
import xml.etree.ElementTree as ET
from posixpath import basename, dirname, normpath
from xml.sax.saxutils import escape, quoteattr

import pipeline

BLOCKS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr'}
CONTAINERS = {'table', 'thead', 'tbody', 'tfoot', 'div', 'ul', 'ol', 'li'}


def tag(node):
    return node.tag.rsplit('}', 1)[-1]


def plain(node):
    return ' '.join(''.join(node.itertext()).split())


def body_of(original, unit):
    return ET.fromstring(original.read(unit['href'])).find(pipeline.X + 'body')


def rows(body):
    return [[plain(cell) for cell in row] for row in body.iter(pipeline.X + 'tr')
            if plain(row)]


def render(original, section, unit, body, translations, media):
    source = pipeline.source_unit(section, unit)
    pairs = iter(zip(source['blocks'], translations, strict=True))
    cells_file = pipeline.ROOT / 'editorial-zh' / (unit['id'] + '.cells.json')
    source_rows = rows(body)
    cells = pipeline.read(cells_file) if cells_file.exists() else [None] * len(source_rows)
    table_colors = {}
    if unit['id'] in {'c1JU0', 'c1K72'}:
        css = original.read('OEBPS/stylesheet.css').decode('utf-8')
        for key, rules in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}', css):
            color = re.search(r'background-color:\s*(#[\da-fA-F]{6})\b', rules)
            if color:
                table_colors[key] = color[1]
    if len(cells) != len(source_rows):
        raise ValueError(f'{unit["id"]}: 表格行数不符')
    row_pairs = iter(zip(source_rows, cells, strict=True))

    def translate(text):
        text = ' '.join(text.split())
        if not text:
            return ''
        block, zh = next(pairs)
        if block['text'] != text:
            raise ValueError(f'{unit["id"]}: {block["id"]} 与原版结构不符')
        return zh

    def image(node):
        href = node.get('src') or node.attrib['{http://www.w3.org/1999/xlink}href']
        path = normpath(dirname(unit['href']) + '/' + href)
        dest = 'assets/' + path.removeprefix('OEBPS/').replace('/', '-')
        media[dest] = original.read(path)
        entry = pipeline.read(pipeline.ROOT / 'editorial-zh' / 'illustrations.json')[basename(path)]
        img = '<img src=' + quoteattr(dest) + ' alt=' + quoteattr(entry['alt']) + '/>'
        caption = '<br/>'.join(escape(line) for line in entry.get('caption', '').splitlines())
        return img + (f'<span class="caption">{caption}</span>' if caption else '')

    def visit(node):
        kind = tag(node)
        if kind == 'img' or node.tag == '{http://www.w3.org/2000/svg}image':
            return image(node)
        if kind == 'tr':
            text = plain(node)
            if not text:
                return ''
            translated_row = translate(text)
            originals, translated = next(row_pairs)
            if translated is None:
                if ''.join(originals) == translated_row.replace('\u00a0', ' '):
                    translated = originals
                elif unit['id'] == 'c1J2M':
                    label, rest = translated_row.split('：', 1)
                    value, note = rest.split('。', 1)
                    translated = [label, value, note]
                else:
                    raise ValueError(f'{unit["id"]}: 缺少逐列译文')
            if len(originals) != len(translated):
                raise ValueError(f'{unit["id"]}: 表格列数不符')
            if cells_file.exists() and translated_row != '｜'.join(translated):
                raise ValueError(f'{unit["id"]}: 散页译文与逐格译文不一致')
            result = []
            for cell, en, zh in zip(node, originals, translated, strict=True):
                if en and not zh:
                    raise ValueError(f'{unit["id"]}: 表格单元格缺译')
                attrs = ''.join(f' {key}={quoteattr(cell.get(key))}'
                                for key in ('rowspan', 'colspan') if key in cell.attrib)
                cell_tag = 'th' if tag(cell) == 'th' else 'td'
                if color := table_colors.get(cell.get('class')):
                    attrs += f' style="background-color:{color};color:#000"'
                value = escape(zh)
                if unit['id'] == 'c1K72' and en and (en.startswith('(GS) ') or
                        en.split(' (')[0] in {'Noah', 'Shem', 'Ham', 'Japheth'}):
                    value = f'<strong>{value}</strong>'
                result.append(f'<{cell_tag}{attrs}>{value}</{cell_tag}>')
            return '<tr>' + ''.join(result) + '</tr>'
        if kind in BLOCKS or not len(node):
            zh = translate(plain(node))
            imgs = ''.join(image(i) for i in node.iter(pipeline.X + 'img'))
            wrapper = kind if re.fullmatch(r'h[1-6]|p|span', kind) else 'p'
            value = escape(zh)
            for anchor in node.iter(pipeline.X + 'a'):
                href = anchor.get('href', '')
                if not href.startswith(('https://', 'http://')):
                    continue
                label = '点此' if plain(anchor) == 'Click here' else plain(anchor)
                if label not in zh:
                    raise ValueError(f'{unit["id"]}: 译文中找不到链接文字 {label!r}')
                value = value.replace(escape(label), f'<a href={quoteattr(href)}>{escape(label)}</a>', 1)
            return f'<{wrapper}>{value}{imgs}</{wrapper}>' if zh or imgs else ''
        inner = escape(translate(node.text or ''))
        for child in node:
            inner += visit(child) + escape(translate(child.tail or ''))
        if kind == 'table':
            return f'<div class="table-wrap"><table>{inner}</table></div>'
        return f'<{kind}>{inner}</{kind}>' if kind in CONTAINERS else inner

    result = ''.join(visit(child) for child in body)
    if next(pairs, None) is not None or next(row_pairs, None) is not None:
        raise ValueError(f'{unit["id"]}: 有未使用的译文')
    return result
