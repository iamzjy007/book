"""Generate resumable English-to-Chinese drafts with a local Argos model."""
import argparse
import re
import tempfile
from zipfile import ZipFile

import pipeline
from ethiopian_editorial import body_of, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', help='Path to the Argos English–Chinese model archive')
    args = parser.parse_args()
    import ctranslate2
    from sentencepiece import SentencePieceProcessor

    chapter = re.compile(r'(?<=[.!?;])\s+(?=[A-Z“"‘\d])')
    out = pipeline.ROOT / 'editorial-zh'
    with tempfile.TemporaryDirectory() as temp, ZipFile(args.model) as model, ZipFile(pipeline.SOURCE) as original:
        prefix = next(x.rsplit('/', 1)[0] for x in model.namelist() if x.endswith('/sentencepiece.model'))
        from pathlib import Path
        directory = Path(temp)
        for member in ('sentencepiece.model', 'model/config.json', 'model/model.bin', 'model/shared_vocabulary.json'):
            target = directory / member
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(model.read(prefix + '/' + member))
        sp = SentencePieceProcessor(model_file=str(directory / 'sentencepiece.model'))
        engine = ctranslate2.Translator(str(directory / 'model'), device='cpu', intra_threads=4)
        terms = pipeline.read(pipeline.ROOT / 'glossary.json')['terms']
        fixed = {**terms, 'Patriarch': '族长', 'Masoretic Text (MT)': '马所拉文本（MT）',
                 'Samaritan Pentateuch (SP)': '撒马利亚五经（SP）', 'Septuagint (LXX)': '七十士译本（LXX）',
                 'Begetting Age': '生子年龄', 'Lifespan': '寿数', 'Year(s)(Approx.)': '年代（约）',
                 'Major Historical Event(s)': '重大历史事件', 'COVENANT CHRISTIAN COALITION': '基督徒圣约联盟',
                 'Seth': '塞特', 'Enosh': '以挪士', 'Kenan': '该南', 'Mahalalel': '玛勒列', 'Jared': '雅列',
                 'Enoch': '以诺', 'Methuselah': '玛土撒拉', 'Lamech': '拉麦', 'Noah': '挪亚'}

        def known(value):
            if re.fullmatch(r'[\d\s.,:/–—()+?*\-]*', value):
                return value
            date = re.fullmatch(r'(\d+(?:[––-]\d+)?)\s+(BC|AD)', value)
            if date:
                return ('公元前' if date[2] == 'BC' else '公元') + date[1] + '年'
            born = re.fullmatch(r'(.+) born', value)
            if born and born[1] in fixed:
                return fixed[born[1]] + '出生'
            return fixed.get(value)

        def chunks(text):
            for sentence in chapter.split(text):
                words = sentence.split()
                for index in range(0, len(words), 65):
                    yield ' '.join(words[index:index + 65])

        def translate(values):
            jobs = [list(chunks(text)) if known(text) is None else [] for text in values]
            fragments = list(dict.fromkeys(s for group in jobs for s in group))
            tokens = engine.translate_batch(sp.encode(fragments, out_type=str), max_batch_size=24,
                                            beam_size=3, max_decoding_length=288) if fragments else []
            mapped = {s: sp.decode(r.hypotheses[0]).strip() for s, r in zip(fragments, tokens, strict=True)}
            results = []
            for value, group in zip(values, jobs, strict=True):
                result = ''.join(mapped[s] for s in group) if group else known(value)
                if not result and value:
                    raise ValueError(f'空译文 {value[:100]}')
                results.append(result)
            return results

        from assemble_ethiopian import EDITORIAL
        receipts = out / 'machine-drafts.json'
        recorded = pipeline.read(receipts) if receipts.exists() else {}
        for s in pipeline.manifest()['sections']:
            if s['id'] not in EDITORIAL or s['id'] == 'table-of-contents':
                continue
            for u in s['units']:
                target = out / (u['id'] + '.txt')
                if target.exists():
                    continue
                source = pipeline.source_unit(s, u)
                if not source['blocks']:
                    continue
                table = rows(body_of(original, u))
                values = [b['text'] for b in source['blocks'] if b['kind'] != 'tr']
                translated = iter(translate(values + [cell for row in table for cell in row]))
                paragraphs = [next(translated) for _ in values]
                table_zh = [[next(translated) for _ in row] for row in table]
                if table:
                    pipeline.save(target.with_suffix('.cells.json'), table_zh)
                row_zh = iter('｜'.join(row) for row in table_zh)
                texts = iter(paragraphs)
                lines = [next(row_zh) if b['kind'] == 'tr' else
                         EDITORIAL[s['id']] if (zh := next(texts)) and b['kind'] == 'h1' else zh
                         for b in source['blocks']]
                recorded[u['id']] = {'source_sha256': u['sha256'], 'model': 'Argos EN→ZH 1.9',
                                     'blocks': len(lines), 'review': 'needs_bilingual_review'}
                pipeline.save(receipts, recorded)
                temporary = target.with_suffix('.txt.tmp')
                temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                temporary.replace(target)
                print(f'{u["id"]}: {len(lines)} 段，{len(table_zh)} 表格行', flush=True)


if __name__ == '__main__':
    main()
