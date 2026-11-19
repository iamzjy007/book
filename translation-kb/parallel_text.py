"""Retrieve parallel passages and expose local evidence. No verse IDs in ranking."""
from dataclasses import dataclass
import re

from wordstudy import STOP, WEAK_CLUES, FORMS, WORD


def content(text):
    result = []
    for token in WORD.finditer(text):
        surface = token[0]
        key = FORMS.get(surface.lower(), surface.lower())
        if key not in STOP and key not in WEAK_CLUES and len(key) > 1:
            result.append((key, surface))
    return result


def local_alignment(left, right):
    """Local ordered match with linear gaps; return score and original token indices."""
    scores = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    best = (0, 0, 0)
    for i, (a, _) in enumerate(left, 1):
        for j, (b, _) in enumerate(right, 1):
            scores[i][j] = max(0, scores[i-1][j-1] + (3 if a == b else -2),
                               scores[i-1][j]-1, scores[i][j-1]-1)
            if scores[i][j] > best[0]:
                best = scores[i][j], i, j
    score, i, j = best
    pairs = []
    while scores[i][j] > 0:
        same = left[i-1][0] == right[j-1][0]
        if scores[i][j] == scores[i-1][j-1] + (3 if same else -2):
            if same:
                pairs.append((i-1, j-1))
            i, j = i-1, j-1
        elif scores[i][j] == scores[i-1][j]-1:
            i -= 1
        else:
            j -= 1
    return score, pairs[::-1]


@dataclass
class Match:
    ref: tuple
    source: str
    english: str
    score: int
    anchors: list
    residual: list
    reference_only: list
    bm_rank: int

    @property
    def supported(self):
        return self.score >= 13 and len(set(self.anchors)) >= 4


def ranked(db, source):
    query = content(source)
    if len(query) < 4:
        return []
    keys = list(dict.fromkeys(k for k, _ in query))
    expression = " OR ".join('"' + k + '"' for k in keys)
    rows = db.execute("""
        WITH hits AS (SELECT rowid, rank FROM word_concordance
                      WHERE word_concordance MATCH ? ORDER BY rank, rowid LIMIT 24)
        SELECT v.code,v.ch,v.first,v.text FROM hits JOIN verses v ON v.rowid=hits.rowid
        ORDER BY hits.rank, v.rowid""", (expression,))
    matches = []
    for position, (code, ch, verse, english) in enumerate(rows, 1):
        target = content(english)
        score, pairs = local_alignment(query, target)
        aligned = {i for i, _ in pairs}
        ref_aligned = {j for _, j in pairs}
        matches.append(Match((code,ch,verse), source, english, score,
                             [query[i][0] for i, _ in pairs],
                             [surface for i, (_,surface) in enumerate(query) if i not in aligned],
                             [surface for j, (_,surface) in enumerate(target) if j not in ref_aligned],
                             position))
    return sorted(matches, key=lambda m: (-m.score, m.bm_rank))


def windows(text):
    for para in text.splitlines():
        tokens = list(WORD.finditer(para))
        for i in range(0, len(tokens), 60):
            end = min(i+84, len(tokens))
            yield para[tokens[i].start():tokens[end-1].end()]
            if end == len(tokens):
                break


def best_parallel(db, source):
    best = None
    for window in windows(source):
        matches = ranked(db, window)
        if matches and matches[0].supported and (best is None or matches[0].score > best.score):
            best = matches[0]
    return best


def scope_terms(text):
    return re.findall(r"\b(?:not|never|neither|nor|no|unless|until|if|only|may|must|might|shall|will|"
                      r"cannot|[a-z]+n['’]t)\b", text.lower())
