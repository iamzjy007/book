"""Bilingual word studies, backed only by the two local scripture editions."""
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache
from math import log2
import re
import sqlite3
from . import DB, ROOT, SOURCES

PSALMS = {"PSA"}
WISDOM = {"JOB", "PRO", "ECC", "SOL"}
PAUL = set("ROM 1CO 2CO GAL EPH PHI COL 1TH 2TH 1TI 2TI TIT PHM".split())
NEW = PAUL | set("MAT MAR LUK JOH ACT HEB JAM 1PE 2PE 1JO 2JO 3JO JUD REV".split())
GROUPS = {"psalms": PSALMS, "wisdom": WISDOM, "paul": PAUL, "nt": NEW}
POETRY = PSALMS | WISDOM

# Conservative morphology. Pronouns, prepositions and word order still participate
# in the sense patterns. The FTS concordance separately provides Porter stemming.
FORMS = {}
for family in """
pray prays praying prayed
lead leads led leading
cast casts casting
carry carries carrying carried
burden burdens
bind binds binding bound
wound wounds
renew renews renewing renewed
direct directs directed directing
restore restores restoring restored
abide abides abiding
guard guards guarded guarding
give gives giving gave given
portion portions
soul souls
heart hearts
mind minds
eagle eagles
pasture pastures
water waters
walk walks walked walking
reap reaps reaping
fight fights fighting fought
sow sows sowing
endure endures enduring endured
strengthen strengthens strengthened strengthening
redeem redeems redeemed redeeming
refuge refuges
stand stands standing stood
mercy mercies
love loves loved loving
work works working worked
believe believes believing believed
hope hopes hoping hoped
forgive forgives forgiving forgave forgiven
comfort comforts comforting comforted
call calls calling called
word words
""".strip().splitlines():
    root, *forms = family.split()
    FORMS.update({f:root for f in forms})

WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
SENTENCE = re.compile(r"[^.!?;\n]+")
ANCHORS = set("""
atonement salvation righteousness righteous sanctify sanctified holiness
redemption redeem intercession supplication trespass trespasses transgression
perseverance steadfast infirmity anoint anointed anointing forgiveness
affliction covenanted covenant stronghold eternal mercy merciful grace
repent repentance iniquity deliverance salvation psalms workmanship intercede
""".split())
STOP = set("""
a an the as it its this that these those my your our his her their me us i we
you they he she them him to from in out for of by through under about and or
but nor than then which who whom whose what when how all some any many much
very indeed must shall will may was were is are am be been being has have had
do does did doing not so also up at on into with over unto can could would
should everything nothing something let there here because if until no now
day thing things come comes make made go get said says without between
""".split())
WEAK_CLUES = set("""
also again always never some much many even every such each other same another
another after before first last far too once away around side left right whole
get got goes going gone done comes take taken put look looks see seen said says
saying tell told knew know knows shall may must able like great greatly long
today day days year years near through man men son sons thing he's it's don't
took takes brought brings which such did will while since along went going
""".split())


def forms(text):
    words = (m[0].lower().replace("’", "'") for m in WORD.finditer(text))
    return tuple(FORMS.get(w, w) for w in words)


@lru_cache(maxsize=2048)
def alternatives(field):
    return tuple(forms(x) for x in field.split(";") if x)


def contains(tokens, phrase):
    return any(tokens[i:i+len(phrase)] == phrase for i in range(len(tokens)-len(phrase)+1))


def lexical_keys(tokens):
    """Adjacent content words, allowing up to two function words between them."""
    previous = None
    for i, word in enumerate(tokens):
        if word in STOP or len(word) < 3:
            continue
        yield word, i, i+1
        if previous is not None and i-previous <= 3 and tokens[previous] != word:
            yield " ".join(tokens[previous:i+1]), previous, i+1
        previous = i


def build_collocations(db):
    # All statistics count distinct English verses. Only attestations in at
    # least two chapters may become automatic collocation leads.
    occurrences = defaultdict(list)
    chapters = {}
    for rid, code, ch, verse in db.execute(
        "SELECT rowid,code,ch,text FROM verses WHERE edition='engwebp' AND text<>''"
    ):
        chapters[rid] = (code,ch)
        keys = {key for clause in re.split(r"[.,;:!?—\n]", verse)
                for key,_,_ in lexical_keys(forms(clause))}
        for key in keys:
            occurrences[key].append(rid)
    db.execute("DROP TABLE IF EXISTS word_keys")
    db.execute("DROP TABLE IF EXISTS word_examples")
    db.execute("CREATE TABLE word_keys(term TEXT PRIMARY KEY, docs INTEGER, lift REAL) WITHOUT ROWID")
    db.execute("CREATE TABLE word_examples(term TEXT, verse_id INTEGER, PRIMARY KEY(term,verse_id)) WITHOUT ROWID")
    n = len(chapters)
    for key, ids in sorted(occurrences.items()):
        parts = key.split()
        count = len(ids)
        lift = 0.
        if len(parts) > 1:
            if not 3 <= count <= 300 or len({chapters[i] for i in ids}) < 2:
                continue
            lift = count*n/(len(occurrences[parts[0]])*len(occurrences[parts[-1]]))
            if lift < 6:
                continue
        db.execute("INSERT INTO word_keys VALUES (?,?,?)", (key,count,lift))
        if lift or key in ANCHORS or (4 <= count <= 90 and len({chapters[i] for i in ids}) >= 2):
            db.executemany("INSERT INTO word_examples VALUES (?,?)", ((key,i) for i in ids))


def install_senses(db):
    rows = []
    for line in (SOURCES / "word-senses.txt").read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith("#"):
            continue
        ref, en, zh, variants, cues, exclude, usage = line.split("|")
        code, cv = ref.split()
        ch, v = map(int,cv.split(":"))
        pair = db.execute("SELECT edition,text FROM verses WHERE code=? AND ch=? AND first<=? AND last>=?",(code,ch,v,v)).fetchall()
        pair = dict(pair)
        if not en or not zh or en.casefold() not in pair.get("engwebp", "").casefold() or zh not in pair.get("cmn-cu89s", ""):
            raise ValueError(f"底本未找到指定措辞：{line}")
        rows.append((code,ch,v,en,zh,variants,cues,exclude,usage))
    if not rows:
        raise ValueError("word-senses.txt 缺少词义条目")
    db.execute("CREATE TABLE IF NOT EXISTS word_senses(code TEXT,ch INTEGER,v INTEGER,en TEXT,zh TEXT,variants TEXT,cues TEXT,exclude TEXT,usage TEXT,PRIMARY KEY(code,ch,v,en))")
    db.execute("DELETE FROM word_senses")
    db.executemany("INSERT INTO word_senses VALUES (?,?,?,?,?,?,?,?,?)", rows)


def install(db):
    install_senses(db)
    install_indexes(db)


def install_indexes(db):
    db.execute("DROP TABLE IF EXISTS word_concordance")
    db.execute("CREATE VIRTUAL TABLE word_concordance USING fts5(text, tokenize='porter unicode61',content='')")
    db.execute("INSERT INTO word_concordance(rowid,text) SELECT rowid,text FROM verses WHERE edition='engwebp' AND text<>''")
    build_collocations(db)


@dataclass(frozen=True)
class Sense:
    code: str
    ch: int
    v: int
    name: str
    en: str
    zh: str
    variants: str
    cues: str
    exclude: str
    usage: str
    chinese: str
    start: int
    end: int

    @property
    def ref(self):
        span = str(self.start) if self.start == self.end else f"{self.start}–{self.end}"
        return f"{self.name} {self.ch}:{span}"


def senses(db, group=None):
    rows = db.execute("""
        SELECT s.code,s.ch,s.v,b.name,s.en,s.zh,s.variants,s.cues,s.exclude,s.usage,v.text,v.first,v.last
        FROM word_senses s JOIN books b ON b.code=s.code AND b.edition='cmn-cu89s'
        JOIN verses v ON v.code=s.code AND v.edition=b.edition AND v.ch=s.ch AND s.v BETWEEN v.first AND v.last
        ORDER BY s.rowid""")
    return [Sense(*r) for r in rows if group is None or r[0] in GROUPS[group]]


def contexts(text):
    # Do not let an unrelated sentence elsewhere in the same article license a sense.
    for sentence in SENTENCE.findall(re.sub(r",\s+(?=(?:and|but|yet)\b)", ". ", text, flags=re.I)):
        matches = list(WORD.finditer(sentence))
        if matches and not sentence.lstrip().startswith(("#","http","URL:","Video:","Date:")):
            yield sentence, matches, forms(sentence)


def match_senses(entries, text):
    index = defaultdict(list)
    for entry in entries:
        for p in dict.fromkeys((forms(entry.en), *alternatives(entry.variants))):
            index[p[0]].append((p,entry))
    best = {}
    for sentence, positions, tokens in contexts(text):
        for i, word in enumerate(tokens):
            for phrase,e in index.get(word,()):
                end = i+len(phrase)
                if tokens[i:end] != phrase:
                    continue
                left, right = tokens[max(0,i-12):i], tokens[end:end+12]
                if any(contains(tokens[max(0,i-12):end+12],p) for p in alternatives(e.exclude)):
                    continue
                support = sum(contains(left,p) or contains(right,p) or
                              (len(phrase)>=3 and contains(phrase,p)) for p in alternatives(e.cues))
                if e.cues and not support:
                    continue
                score = min(len(phrase),5)*2 + min(support,3)*2
                fragment = sentence[positions[i].start():positions[end-1].end()]
                if e not in best or score > best[e][0]:
                    best[e] = score,fragment
    return [(entry,frag) for entry,(_,frag) in sorted(best.items(),key=lambda item:-item[1][0])]


def corpus(db, words, group=None, limit=6):
    # FTS expressions are constructed from ASCII word tokens, never raw user input.
    parts = ['"'+w+'"' for w in words]
    if not parts:
        return []
    params = []
    restrict = ""
    if group is not None:
        codes = sorted(GROUPS[group])
        restrict = " AND e.code IN ("+",".join("?" for _ in codes)+")"
        params.extend(codes)
    sql = """
        SELECT b.name,e.ch,z.first,z.last,e.text,z.text FROM word_concordance f
        JOIN verses e ON e.rowid=f.rowid
        JOIN books b ON b.code=e.code AND b.edition='cmn-cu89s'
        JOIN verses z ON z.edition=b.edition AND z.code=e.code AND z.ch=e.ch AND e.first=z.first AND e.last=z.last
        WHERE word_concordance MATCH ? """+restrict+" ORDER BY f.rank,e.rowid LIMIT ?"
    queries = ['"'+" ".join(words)+'"']
    if len(parts)>1:
        queries.extend(["NEAR("+" ".join(parts)+", 6)", " AND ".join(parts)])
    results = {}
    for query in queries:
        for row in db.execute(sql, (query,*params,limit)):
            results[row] = None
        if len(results)>=limit:
            break
    return list(results)[:limit]


def excerpt(text, fragment, radius=22):
    start = text.index(fragment)
    lo,hi = max(0,start-radius), min(len(text),start+len(fragment)+radius)
    return ("…" if lo else "")+text[lo:hi]+("…" if hi<len(text) else "")


def format_pair(row):
    name,ch,lo,hi,en,zh = row
    ref = str(lo) if lo==hi else f"{lo}–{hi}"
    return f"{name} {ch}:{ref}　{zh}\n  WEB　{en}"


def discover(db, text, used, used_refs):
    # Retrieve on English evidence only. Verse alignment alone supplies no
    # Chinese word boundaries. Require independent context in the same verse.
    candidates = []
    keys = {}
    for line in text.splitlines():
        if line.lstrip().startswith(("#", "URL:", "Date:", "http")):
            continue
        for clause in re.split(r"[.,;:!?—]", line):
            positions = list(WORD.finditer(clause))
            tokens = forms(clause)
            for key,lo,hi in lexical_keys(tokens):
                if key in WEAK_CLUES or (hi-lo>1 and tokens[lo] in WEAK_CLUES and tokens[hi-1] in WEAK_CLUES):
                    continue
                nearby = set(tokens[max(0,lo-10):lo]+tokens[hi:hi+10]) - STOP - WEAK_CLUES - set(key.split())
                if not nearby:
                    continue
                fragment = clause[positions[lo].start():positions[hi-1].end()]
                if key not in used:
                    candidates.append((key,fragment,nearby))
                    keys[key] = None
    if not candidates:
        return None
    def stats(terms):
        data = {}
        items = sorted(set(terms))
        for i in range(0, len(items), 400):
            chunk = items[i:i+400]
            marks = ",".join("?" for _ in chunk)
            for key,df,lift in db.execute(f"SELECT term,docs,lift FROM word_keys WHERE term IN ({marks})",chunk):
                data[key] = (df,lift)
        return data
    weights = stats(keys)
    candidates = [c for c in candidates if c[0] in weights]
    candidates.sort(key=lambda c: (c[0] in ANCHORS or bool(ANCHORS.intersection(c[0].split())),
                                   min(weights[c[0]][1],100)), reverse=True)
    evidence = {}
    for key,fragment,neighbors in candidates:
        evidence.setdefault(key, []).append((fragment,neighbors))
    common = [k for k in evidence if weights[k][1] or k in ANCHORS][:16]
    rare = sorted((k for k in evidence if " " not in k and k not in ANCHORS and 4 <= weights[k][0] <= 90),
                  key=lambda k:weights[k][0])[:8]
    evidence = {key:evidence[key] for key in common+rare}
    if not evidence:
        return None
    frequencies = stats(w for choices in evidence.values() for _,ns in choices for w in ns)
    total = db.execute("SELECT count(*) FROM word_concordance").fetchone()[0]
    best = None
    for key,choices in evidence.items():
        rows = db.execute("""
            SELECT b.name,e.ch,z.first,z.last,e.text,z.text,e.code FROM word_examples x
            JOIN verses e ON e.rowid=x.verse_id
            JOIN books b ON b.code=e.code AND b.edition='cmn-cu89s'
            JOIN verses z ON z.edition=b.edition AND z.code=e.code AND z.ch=e.ch
                         AND z.first=e.first AND z.last=e.last
            WHERE x.term=? ORDER BY e.rowid""", (key,))
        for record in rows:
            row, code = record[:6], record[6]
            if row[:3] in used_refs:
                continue
            verse = forms(row[4])
            windows = [set(verse[max(0,i-8):i] + verse[j:j+8])
                       for term,i,j in lexical_keys(verse) if term == key]
            for fragment,neighbors in choices:
                for window in windows:
                    shared = sorted((w for w in neighbors & window if 0 < frequencies.get(w,(0,))[0] <= 1200),
                                    key=lambda w:(frequencies[w][0],w))
                    if not shared or (len(shared)==1 and (not weights[key][1] or frequencies[shared[0]][0]>100)):
                        continue
                    gains = [log2(total/frequencies[w][0]) for w in shared[:3]]
                    # Register matters among comparable lexical leads. One rare
                    # local anchor carries more weight than this genre prior.
                    register = 3 if code in NEW else 1 if code in POETRY else 0
                    score = (sum(gains) + min(5,log2(max(1,weights[key][1]))) + register,
                             -len(row[4]))
                    if best is None or score > best[0]:
                        best = score,fragment,shared,row
    return best


def author_prose(text):
    paragraphs = re.split(r"\n\s*\n", text.strip())
    citation = re.compile(r"(?i)^[\w .]+ \d+:[\d, –—\-]+\s*\(?(?:AMPC|NKJV)\)?(?:\s+See less)?$")
    return "\n".join(p for i,p in enumerate(paragraphs)
                     if not citation.fullmatch(p.strip()) and not p.lstrip().startswith("#")
                     and not re.match(r"(?i)^[\w .]+ \d+:[\d, –—\-]+\s*\(?(?:AMPC|NKJV)\)?\s",p.strip())
                     and not (i+1<len(paragraphs) and citation.fullmatch(paragraphs[i+1].strip())))


def packet_notes(db, text):
    prose = author_prose(text)
    hits = match_senses(senses(db), prose)
    notes = []
    groups = defaultdict(list)
    for e,frag in hits:
        groups[e.ref].append((e,frag))
    for ref,entries in list(groups.items())[:4]:
        lines = [f"原文「{frag}」可参「{e.zh}」。{e.usage}" for e,frag in entries[:2]]
        e = entries[0][0]
        lines.append("和合本　"+ (e.chinese if len(entries)>1 else excerpt(e.chinese,e.zh)))
        notes.append(f"- {ref}　"+"\n  ".join(lines))
    if len(notes) < 4:
        used = {" ".join(forms(frag)) for _,frag in hits}
        used_refs = {(e.name,e.ch,e.start) for e,_ in hits}
        candidate = discover(db,prose,used,used_refs)
        if candidate:
            _,frag,shared,row = candidate
            notes.append(f"- 全经查词线索「{frag}」，同节近处另见 {', '.join(shared[:3])}。请对读辨义。\n  {format_pair(row)}")
    return notes


def lookup(db, query, group=None, context=False):
    entries = senses(db,group)
    query_tokens = forms(query)
    if query_tokens:
        hits = match_senses(entries,query)
        for e in entries:
            if any(contains(p,query_tokens) for p in (forms(e.en),*alternatives(e.variants))) and not any(x==e for x,_ in hits):
                hits.append((e,query))
        for e in entries:
            if query_tokens in alternatives(e.cues) and not any(x==e for x,_ in hits):
                hits.append((e,query))
    else:
        hits = [(e,query) for e in entries if query.strip() and query in e.zh]
    def surrounding(name, ch, lo, hi):
        if not context:
            return ""
        rows = db.execute("""
            SELECT v.first,v.last,v.text FROM verses v JOIN books b USING(edition,code)
            WHERE b.edition='cmn-cu89s' AND b.name=? AND v.ch=?
            AND v.first<=? AND v.last>=? ORDER BY v.first""", (name,ch,hi+1,lo-1))
        return "\n  上下文　"+" ".join(f"〔{i if i==j else f'{i}–{j}'}〕{t}" for i,j,t in rows)
    result = [f"{e.ref}　{e.en} → {e.zh}\n  {e.chinese}\n  {e.usage}"+surrounding(e.name,e.ch,e.start,e.end)
              for e,_ in hits[:8]]
    if query_tokens:
        rows = corpus(db,[m[0].lower().replace("’","'") for m in WORD.finditer(query)][:16],group)
    else:
        codes = sorted(GROUPS[group]) if group else []
        scope = " AND z.code IN ("+",".join("?" for _ in codes)+")" if codes else ""
        rows = db.execute("""
            SELECT b.name,z.ch,z.first,z.last,e.text,z.text FROM verses z
            JOIN books b USING(edition,code)
            JOIN verses e ON e.edition='engwebp' AND e.code=z.code AND e.ch=z.ch AND e.first=z.first AND e.last=z.last
            WHERE z.edition='cmn-cu89s' AND instr(z.text,?)>0"""+scope+" ORDER BY z.rowid LIMIT 6", (query,*codes))
    for row in rows:
        result.append("同词经节　"+format_pair(row)+surrounding(*row[:4]))
    return result


if __name__ == "__main__":
    with closing(sqlite3.connect(DB.as_uri() + "?mode=rw", uri=True)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        install(db)
