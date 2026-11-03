import json,re,tempfile,unittest,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import pipeline as p

class ResumeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=p.manifest();cls.book=next(b for b in cls.m['sections'] if b['id']=='apocryphal-esther');cls.realroot=p.ROOT
 def test_canonical_exclusion(self):
  c=[b for b in self.m['sections'] if b['scope']=='excluded_canonical_66']
  self.assertEqual(len(c),66);self.assertEqual(c[0]['title'],'GENESIS');self.assertEqual(c[-1]['title'],'REVELATION')
  self.assertEqual(next(b['scope'] for b in self.m['sections'] if b['id']=='the-shepherd-of-hermas'),'included')
 def test_first_book_extraction_covers_text(self):
  count=0
  with zipfile.ZipFile(p.SOURCE) as z:
   for u in self.book['units']:
    s=p.source_unit(self.book,u);body=ET.fromstring(z.read(u['href'])).find(p.X+'body')
    original=re.sub(r'\s+',' ',''.join(body.itertext())).strip()
    for skip in s['skipped_navigation']:original=original.replace(skip['text'],'')
    recovered=' '.join((v.get('verse','')+' '+v['text']).strip() for v in s['blocks'])
    self.assertEqual(re.sub(r'\s+','',original),re.sub(r'\s+','',recovered))
    count+=sum(v['kind']=='verse' for v in s['blocks'])
  self.assertEqual(count,98)
 def test_resume_draft_corruption_and_interrupted_write(self):
  u=self.book['units'][0];valid=p.read(self.realroot/'zh'/self.book['id']/(u['id']+'.json'))
  with tempfile.TemporaryDirectory() as tmp:
   p.ROOT=Path(tmp)
   try:
    path=p.ROOT/'zh'/self.book['id']/(u['id']+'.json')
    self.assertEqual(p.validate(self.book,u)[0],'pending')
    p.save(path.with_suffix('.json.tmp'),valid)
    self.assertEqual(p.validate(self.book,u)[0],'pending')
    draft={**valid,'reviewed':False};p.save(path,draft)
    self.assertEqual(p.validate(self.book,u)[0],'draft')
    p.save(path,valid);self.assertEqual(p.validate(self.book,u)[0],'complete')
    cp=p.checkpoint({'source_sha256':self.m['source_sha256'],'sections':[self.book]})
    self.assertEqual(cp['completed_units'],1);self.assertEqual(cp['next']['unit_id'],self.book['units'][1]['id'])
    path.write_text('{broken');self.assertEqual(p.validate(self.book,u)[0],'invalid')
    bad={**valid,'blocks':valid['blocks'][:-1]};p.save(path,bad)
    self.assertEqual(p.validate(self.book,u)[0],'invalid')
    bad={**valid,'source_sha256':'changed'};p.save(path,bad)
    self.assertEqual(p.validate(self.book,u)[0],'invalid')
   finally:p.ROOT=self.realroot
 def test_changed_source_stops_resume(self):
  orig=p.SOURCE
  with tempfile.TemporaryDirectory() as tmp:
   try:
    p.SOURCE=Path(tmp)/'changed.epub';p.SOURCE.write_bytes(b'changed')
    with self.assertRaisesRegex(ValueError,'Source EPUB changed'):p.manifest()
   finally:p.SOURCE=orig
 def test_completed_book(self):
  for u in self.book['units']:self.assertEqual(p.validate(self.book,u),('complete',None))

if __name__=='__main__':unittest.main()
