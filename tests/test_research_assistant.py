import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ra',ROOT/'tools/research_assistant.py')
ra=importlib.util.module_from_spec(spec); spec.loader.exec_module(ra)

class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.doc={'id':'a','title':'mechanism','text':'机制 因果 mediation','verified':False}
        self.version=ra.build_index(self.home,[self.doc])

    def project(self):
        return {'schema_version':1,'project_id':'test','knowledge_version':self.version,
                'assessment_date':'2021-06-01','stage':'Clarity','next_action':None,
                **{k:[] for k in ('facts','claims','uncertainties','decisions','questions','audit')}}

    def test_dates(self):
        self.assertEqual(ra.temporal('2022','2021'),'当代镜头')
        self.assertEqual(ra.temporal('2025','2026-09-09'),'评估时点前已存在')
        self.assertEqual(ra.temporal('2021','2021-06-01'),'时序待确认')
        self.assertEqual(ra.temporal('2021-05','2021-06-01'),'评估时点前已存在')
        with self.assertRaises(ValueError): ra.temporal('2021-99','2022')

    def test_search_and_pinned_version(self):
        self.assertEqual(ra.search(self.home,'机制')[0]['id'],'a')
        self.assertFalse(ra.search(self.home,'absent'))
        second=ra.build_index(self.home,[dict(self.doc,id='b',text='new topic')])
        self.assertNotEqual(self.version,second)
        self.assertFalse(ra.search(self.home,'机制'))
        self.assertEqual(ra.search(self.home,'机制',self.version)[0]['id'],'a')
        self.assertEqual(ra.build_index(self.home,[self.doc]),self.version)

    def test_failed_build_preserves_current(self):
        before=(self.home/'current.json').read_bytes()
        with self.assertRaises(Exception): ra.build_index(self.home,[self.doc,self.doc])
        self.assertEqual((self.home/'current.json').read_bytes(),before)

    def test_revision_and_history(self):
        first=ra.save_project(self.home,'test',self.project(),0)
        with self.assertRaises(ValueError): ra.save_project(self.home,'test',first,0)
        changed=copy.deepcopy(first); changed['facts']=[{'value':'患者自主性','source':'用户第2轮'}]
        changed['questions']=[{'question':'研究谁','answer':'患者','status':'resolved'}]
        second=ra.save_project(self.home,'test',changed,1)
        self.assertEqual(second['revision'],2)
        self.assertEqual(json.loads((self.home/'projects/history/test/1.json').read_text()),first)
        self.assertEqual(json.loads((self.home/'projects/test.json').read_text())['facts'],changed['facts'])
        with self.assertRaises(ValueError): ra.save_project(self.home,'../escape',changed,2)

    def test_audit_requires_evidence(self):
        p=self.project(); p['audit']=[{'state':'存在缺口'}]
        with self.assertRaises(ValueError): ra.save_project(self.home,'test',p,0)
        p['audit']=[{'state':'待确认'}]
        self.assertEqual(ra.save_project(self.home,'test',p,0)['audit'],p['audit'])

    def test_card_cannot_claim_verification_without_locator(self):
        c={'id':'x','kind':'editorial','claim':'claim','applies_to':[], 'exceptions':[],
           'source':{},'verified':True,'tags':[]}
        with self.assertRaises(ValueError): ra.validate_card(c)
        c['verified']=False; ra.validate_card(c)

    def test_zotero_sync_and_failure(self):
        def get(route):
            if '/collections/' in route:
                return [{'key':'ITEM0001','data':{'itemType':'journalArticle','title':'Example','abstractNote':'abstract'}}]
            if '/children' in route:
                return [{'key':'ATT00001','data':{'contentType':'application/pdf'}}]
            return {'content':'causal evidence mechanism'}
        result=ra.sync_zotero(self.home,'COLL0001',get)
        self.assertEqual(result['chunks'],2)
        self.assertEqual(ra.coverage(self.home)[0]['items_with_text'],1)
        path=self.home/'zotero/COLL0001/snapshot.json'; before=path.read_bytes()
        def fail(route): raise OSError('offline')
        with self.assertRaises(OSError): ra.sync_zotero(self.home,'COLL0001',fail)
        self.assertEqual(path.read_bytes(),before)
        def missing(route):
            if '/fulltext' in route: raise OSError('unindexed')
            return get(route)
        result=ra.sync_zotero(self.home,'COLL0001',missing)
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(result['chunks'],1) # stale text not retained
        self.assertEqual(ra.coverage(self.home)[0]['items_without_text'],1)
        result=ra.sync_zotero(self.home,'COLL0001',lambda route:[])
        self.assertEqual(result['chunks'],0) # removed member disappears

    def test_pdf_fallback_retains_page_and_reports_empty_pages(self):
        def get(route):
            if '/collections/' in route:
                return [{'key':'ITEM0001','data':{'itemType':'journalArticle','title':'Example'}}]
            if '/children' in route:
                return [{'key':'ATT00001','data':{'contentType':'application/pdf'}}]
            raise OSError('no cached text')
        with patch.object(ra, 'pdf_pages', return_value=[(1,'Evidence on page one'),(2,'')]):
            result=ra.sync_zotero(self.home,'COLL0001',get,extract_pdfs=True)
        snapshot=json.loads((self.home/'zotero/COLL0001/snapshot.json').read_text())
        doc=snapshot['documents'][1]
        self.assertEqual(doc['pdf_page'],1)
        self.assertFalse(doc['verified'])
        self.assertEqual(result['failures'][0]['empty_pages'],[2])
        with patch.object(ra, 'pdf_pages', side_effect=FileNotFoundError):
            result=ra.sync_zotero(self.home,'COLL0001',get,extract_pdfs=True)
        self.assertEqual(result['chunks'],1)
        self.assertEqual(result['failures'][0]['reason'],'FileNotFoundError')

    def test_repeated_pagination_aborts(self):
        batch=[{'key':str(i)} for i in range(100)]
        with self.assertRaises(ValueError): ra.paginated('/items',lambda route:batch)

if __name__=='__main__': unittest.main()
