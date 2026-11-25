"""Find local wording parallels for a selected sentence or two, without cross-reference data."""
import re
from functools import lru_cache
from math import isqrt

from kb.parallel_text import content


def echoes(db, focus):
    """Return up to two neighboring verses together, or one independently attested clue."""
    evidence = {}
    @lru_cache(maxsize=None)
    def frequency(key):
        return db.execute('SELECT count(*) FROM word_concordance WHERE word_concordance MATCH ?',
                          (f'"{key}"',)).fetchone()[0]

    # Experimental frequency ceiling for a lone clue, scaled to the size of this corpus.
    ceiling = isqrt(db.execute("SELECT count(*) FROM word_concordance").fetchone()[0])
    for clause in re.split(r"[.!?;:\n]+", focus):
        words = content(clause)
        for (left, a), (right, b) in zip(words, words[1:]):
            if left == right:
                continue
            # FTS includes inflected forms. Verify order and adjacency after stopword removal.
            query = f'NEAR("{left}" "{right}", 4)'
            rows = db.execute("""
                SELECT v.code,v.ch,v.first,v.text FROM word_concordance f
                JOIN verses v ON v.rowid=f.rowid WHERE word_concordance MATCH ? LIMIT 13
            """, (query,)).fetchall()
            if len(rows) > 12:
                continue
            hits = []
            for code, ch, verse, english in rows:
                keys = [k for k, _ in content(english)]
                if (left, right) in zip(keys, keys[1:]):
                    hits.append(((code, ch, verse), english))
            for ref, english in hits:
                evidence.setdefault(ref, {})[left, right] = (len(hits), a, b, english)

    groups = []
    for ref, clues in evidence.items():
        code, ch, verse = ref
        nearby = (code, ch, verse + 1)
        refs = [ref]
        if nearby in evidence and evidence[nearby].keys() - clues.keys():
            refs.append(nearby)
        distinct = {key: value for r in refs for key, value in evidence[r].items()}
        if len(distinct) == 1:
            pair, value = next(iter(distinct.items()))
            if value[0] > 1 or any(frequency(k) > ceiling for k in pair):
                continue
        groups.append((len(distinct), sum(1/v[0] for v in distinct.values()), refs))
    if not groups:
        return []
    groups.sort(reverse=True)
    if len(groups) > 1 and groups[0][:2] == groups[1][:2]:
        return []
    notes = []
    for code, ch, verse in groups[0][2]:
        clues = evidence[code, ch, verse].values()
        chinese = db.execute("""SELECT text FROM verses WHERE edition='cmn-cu89s'
            AND code=? AND ch=? AND first<=? AND last>=?""", (code,ch,verse,verse)).fetchone()
        if chinese:
            anchors = '、'.join(f'{a} … {b}' for _, a, b, _ in clues)
            english = next(iter(clues))[3]
            notes.append(f"{code} {ch}:{verse} · {anchors}\n{english}\n{chinese[0]}")
    return notes
