"""Exercise restart safety, provenance and source-ID collisions in isolation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from import_modern import import_catalog

class ImportTests(unittest.TestCase):
    def test_restart_preserves_acquisition_and_recovers_orphan(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'inventory').mkdir(); (root/'books/ancient').mkdir(parents=True)
            old={'id':'dydi_b:B01','sequence':1,'source_catalog':'ancient/catalog.json', 'acquisition':{'status':'fulltext_online'}}
            (root/'books/ancient/record.json').write_text(json.dumps(old))
            manifest={'source_commit':'old','records':[{'id':old['id'],'sequence':1,'path':'books/ancient/record.json'}]}
            (root/'inventory/manifest.json').write_text(json.dumps(manifest))
            item={'catalog_id':'dydi_b:B01','title':'A modern book', 'sources':[{'url':'https://example.org/book'}], 'kind':'book','group':'books','next':'read'}
            catalog=root/'input.json';catalog.write_text(json.dumps({'items':[item],'merges':{}}))
            self.assertEqual(import_catalog(root,catalog,'test')['added'],1)
            p=root/'books/modern--dydi_b--B01/record.json'; rec=json.loads(p.read_text())
            rec['acquisition']['status']='partial_online';rec['acquisition']['attempts']=[{'result':'durable evidence'}];p.write_text(json.dumps(rec))
            # Simulate a crash after a record write but before manifest update.
            (root/'inventory/manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(import_catalog(root,catalog,'test')['added'],0)
            self.assertEqual(json.loads(p.read_text()),rec)
            self.assertEqual(len(json.loads((root/'inventory/manifest.json').read_text())['records']),2)
            self.assertEqual(json.loads((root/'books/ancient/record.json').read_text()),old)
            # A renamed source ID with the same title and exact source set is an alias.
            renamed=copy.deepcopy(item);renamed['catalog_id']='changed:id'
            # A column at the same institution has a distinct title and stays distinct.
            column=copy.deepcopy(item);column.update(catalog_id='column:id',title='A distinct column')
            catalog.write_text(json.dumps({'items':[item,renamed,column]}))
            self.assertEqual(import_catalog(root,catalog,'test')['added'],1)
            self.assertEqual(import_catalog(root,catalog,'test')['added'],0)
            self.assertEqual(len(json.loads((root/'inventory/manifest.json').read_text())['records']),3)

if __name__=='__main__': unittest.main()
