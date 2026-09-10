import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import research_assistant as ra
import research_workflows as wf


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.docs=[{'id':'a:1:0','title':'Study A','text':'patient autonomy evidence',
                    'kind':'pdf_fulltext','date':'2023','verified':False,
                    'zotero_key':'ITEM0001','attachment_key':'ATT00001','pdf_page':1},
                   {'id':'a:2:0','title':'Study A','text':'patient autonomy context',
                    'kind':'pdf_fulltext','date':'2023','verified':False,
                    'zotero_key':'ITEM0001','attachment_key':'ATT00001','pdf_page':2},
                   {'id':'b','title':'Study B','text':'patient autonomy',
                    'kind':'pdf_fulltext','date':'2021','verified':False,'zotero_key':'ITEM0002'},
                   {'id':'c','title':'Editorial','text':'patient autonomy',
                    'kind':'editorial','date':'2024','verified':True,'zotero_key':'ITEM0003'}]
        self.version=ra.build_index(self.home,self.docs)

    def new_project(self):
        p={'schema_version':1,'project_id':'original','stage':'Clarity',
           'assessment_date':'2026-09-09','knowledge_version':self.version,'next_action':'collect one case',
           **{k:[] for k in ('facts','claims','uncertainties','decisions','questions','audit')}}
        p['questions']=[{'question':'Who?','status':'resolved','answer':'patients'}]
        return ra.save_project(self.home,'original',p,0)

    def test_bilingual_search_filter_diversity(self):
        self.assertFalse(ra.search(self.home,'患者自主性'))
        found=ra.search(self.home,'患者自主性',expand=True,year_from=2022,year_to=2026,
                        kinds=['pdf_fulltext'],per_source=1)
        self.assertEqual(len(found),1);self.assertEqual(found[0]['zotero_key'],'ITEM0001')
        self.assertEqual(ra.search(self.home,'patient',verified_only=True)[0]['id'],'c')
        self.assertFalse(ra.search(self.home,'patient absent',match_all=True))
        with self.assertRaises(ValueError):ra.search(self.home,'x',year_from=2026,year_to=2022)

    def test_read_context_pinned_and_diff(self):
        newer=ra.build_index(self.home,[dict(self.docs[0],text='changed'),self.docs[2]])
        result=wf.read_document(self.home,'a:1:0',self.version,1)
        self.assertEqual(len(result['page_context']),2)
        self.assertIn('evidence',result['document']['text'])
        diff=wf.version_diff(self.home,self.version,newer)
        self.assertEqual(diff['changed'],['a:1:0']);self.assertEqual(len(diff['removed']),2)

    def test_card_drift_audit_is_not_verification(self):
        card={'id':'test-card','kind':'editorial','claim':'test','applies_to':[],'exceptions':[],
              'tags':[],'verified':False,'source':{'document_ids':['a:1:0'],
              'evidence':'patient autonomy evidence','document_hashes':{'a:1:0':hashlib.sha256(self.docs[0]['text'].encode()).hexdigest()}}}
        ra.atomic_json(self.home/'cards/test.json',card)
        self.assertTrue(wf.audit_cards(self.home)['cards'][0]['quote_present'])
        ra.build_index(self.home,[dict(self.docs[0],text='different evidence')])
        row=wf.audit_cards(self.home)['cards'][0]
        self.assertIn('source_text_changed',row['issues']);self.assertFalse(row['verified'])
        self.assertFalse(json.loads((self.home/'cards/test.json').read_text())['verified'])

    def test_fork_export_no_overwrite(self):
        original=self.new_project();child=wf.fork_project(self.home,'original','alternative')
        self.assertEqual(child['knowledge_version'],original['knowledge_version'])
        child['facts']=['child only'];ra.save_project(self.home,'alternative',child,1)
        self.assertEqual(wf.load_project(self.home,'original'),original)
        with self.assertRaises(ValueError):wf.fork_project(self.home,'original','alternative')
        export=wf.handoff(self.home,'alternative')
        self.assertIn('patients',Path(export['path']).read_text())

    def test_packet_honors_project_version(self):
        self.new_project();ra.build_index(self.home,[dict(self.docs[0],text='no match',title='unrelated')])
        packet=wf.evidence_packet(self.home,'患者自主性','original',2022,2026)
        self.assertEqual(packet['knowledge_version'],self.version)
        self.assertEqual(len(packet['paper_candidates']),1)
        self.assertEqual(len(packet['standards']),1)

    def test_research_plan_survives_history_fork_export_and_invalid_save(self):
        original=self.new_project()
        plan={'schema_version':1,'source_nature':'synthetic',
              'constraints':{'months_available':12,'prohibited_methods':[]},
              'resources':[{'id':'logs','description':'Usage logs','source':'Oral promise',
                            'availability':'uncertain','permission':'pending'}],
              'routes':[{'id':'process','question':'How does feedback change?',
                         'claim_scope':'Process explanation','minimum_evidence':'Repeated episodes',
                         'fallback':'Narrow question','methods':['observation'],
                         'requires':['logs'],'estimated_months':10}]}
        original['research_plan']=copy.deepcopy(plan)
        second=ra.save_project(self.home,'original',original,1)
        changed=copy.deepcopy(second)
        changed['research_plan']['resources'][0]['availability']='unavailable'
        third=ra.save_project(self.home,'original',changed,2)
        history=json.loads((self.home/'projects/history/original/2.json').read_text())
        self.assertEqual(history['research_plan'],plan)
        invalid=copy.deepcopy(third)
        invalid['research_plan']['routes'][0]['requires']=['missing']
        with self.assertRaises(ValueError):ra.save_project(self.home,'original',invalid,3)
        self.assertEqual(wf.load_project(self.home,'original'),third)
        child=wf.fork_project(self.home,'original','plan-alternative')
        self.assertEqual(child['research_plan'],third['research_plan'])
        export=Path(wf.handoff(self.home,'plan-alternative')['path']).read_text()
        self.assertIn(json.dumps(child['research_plan'],ensure_ascii=False,indent=2),export)

    def test_latest_whole_item_replaces_stale_chunks(self):
        ra.atomic_json(self.home/'zotero/ZZZZ0001/snapshot.json',{'synced_at':'2026-01-01','collection':'ZZZZ0001','documents':self.docs[:2]})
        ra.atomic_json(self.home/'zotero/AAAA0001/snapshot.json',{'synced_at':'2026-02-01','collection':'AAAA0001','documents':[dict(self.docs[0],text='new')]})
        merged=ra.merged_snapshots(self.home)
        self.assertEqual(len(merged),1);self.assertEqual(merged[0]['text'],'new')

    def test_pdf_cache_reuses_and_invalidates_by_content(self):
        file=self.home/'source.pdf';file.write_bytes(b'first')
        attachment={'path':str(file),'linkMode':'linked_file'}
        fake=types.SimpleNamespace(__version__='test',PdfReader=lambda path:types.SimpleNamespace(pages=[types.SimpleNamespace(extract_text=lambda:'text')]))
        with patch.dict(sys.modules,{'pypdf':fake}):
            ra.pdf_pages(attachment,cache_home=self.home)
            with patch.object(fake,'PdfReader',side_effect=AssertionError('cache miss')):
                self.assertEqual(ra.pdf_pages(attachment,cache_home=self.home),[(1,'text')])
            file.write_bytes(b'second')
            with patch.object(fake,'PdfReader',side_effect=ValueError('changed file parsed')):
                with self.assertRaises(ValueError):ra.pdf_pages(attachment,cache_home=self.home)

    def test_publication_alert_not_cleared_by_later_no_hit(self):
        doc=dict(self.docs[0],doi='10.1234/example')
        ra.atomic_json(self.home/'quality/publication-updates.json',{
            'checked_at':'2026-01-01','items':[{'doi':'10.1234/example','status':'notice_found','notices':[{'type':'correction'}]}]})
        ra.atomic_json(self.home/'quality/doi-updates.json',{
            'checked_at':'2026-02-01','items':[{'doi':'10.1234/example','status':'no_notice_in_checked_metadata'}]})
        status=wf.source_status(self.home,doc)
        self.assertEqual(status['status'],'review_required')
        self.assertEqual(len(status['observations']),2)
        self.assertEqual(wf.source_status(self.home,dict(doc,doi='10.1234/other'))['status'],'not_checked')

    def test_same_report_overwrite_preserves_legacy_alert(self):
        old={'checked_at':'2026-01-01','items':[{'doi':'10.1234/x','status':'notice_found'}]}
        ra.atomic_json(self.home/'quality/doi-updates.json',old)
        new={'checked_at':'2026-02-01','items':[{'doi':'10.1234/x','status':'unknown'}]}
        wf.preserve_publication_report(self.home,'doi-updates.json',new)
        wf.preserve_publication_report(self.home,'doi-updates.json',new)
        result=wf.source_status(self.home,{'doi':'10.1234/x'})
        self.assertEqual(result['status'],'review_required')
        self.assertEqual(len(result['observations']),2)
        self.assertEqual(len(list((self.home/'quality/publication-history').glob('*/*.json'))),2)

    def test_semantic_overlay_conflicts_staleness_and_human_label(self):
        card={'id':'sample','claim':'patient autonomy'}
        doc={'id':'card:sample','text':json.dumps(card)}
        digest=hashlib.sha256(json.dumps(card,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        report={'knowledge_version':self.version,'reviewer_type':'human','reviewer':'teacher',
                'reviews':[{'card_id':'sample','card_sha256':digest,'verdict':'supported','reason':'checked'}]}
        folder=self.home/'quality/semantic-reviews'
        ra.atomic_json(folder/'a.json',report)
        self.assertEqual(wf.semantic_status(self.home,doc,self.version)['status'],'human_supported')
        adverse=copy.deepcopy(report);adverse['reviewer_type']='model'
        adverse['reviews'][0]['verdict']='overstated'
        ra.atomic_json(folder/'b.json',adverse)
        self.assertEqual(wf.semantic_status(self.home,doc,self.version)['status'],'review_required')
        stale=wf.semantic_status(self.home,doc,'different-version')
        self.assertEqual(stale['status'],'pending');self.assertEqual(stale['stale_reviews'],2)
        changed=dict(doc,text=json.dumps(dict(card,claim='changed')))
        self.assertEqual(wf.semantic_status(self.home,changed,self.version)['status'],'pending')
        (folder/'broken.json').write_text('{')
        self.assertEqual(wf.semantic_status(self.home,doc,self.version)['status'],'review_required')

    def test_packet_pins_once_during_concurrent_rebuild(self):
        original=ra.search;versions=[]
        def changing_search(*args,**kwargs):
            versions.append(args[2])
            if len(versions)==1:ra.build_index(self.home,[dict(self.docs[0],text='changed')])
            return original(*args,**kwargs)
        with patch.object(ra,'search',side_effect=changing_search):
            packet=wf.evidence_packet(self.home,'patient')
        self.assertEqual(versions,[self.version,self.version])
        self.assertEqual(packet['knowledge_version'],self.version)

    def test_packet_marks_adverse_card_for_review(self):
        card={'id':'sample','kind':'editorial','claim':'patient autonomy','verified':False,
              'applies_to':[],'exceptions':[],'tags':[],'source':{'document_ids':['a:1:0']}}
        ra.atomic_json(self.home/'cards/sample.json',card)
        carddoc=dict(self.docs[3],id='card:sample',text=json.dumps(card),verified=False)
        version=ra.build_index(self.home,self.docs+[carddoc])
        digest=hashlib.sha256(json.dumps(card,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        ra.atomic_json(self.home/'quality/semantic-reviews/review.json',{
            'knowledge_version':version,'reviewer_type':'model','reviewer':'test',
            'reviews':[{'card_id':'sample','card_sha256':digest,'verdict':'contradicted','reason':'counterexample'}]})
        # Avoid source diversification selecting the fixture editorial instead of the card.
        with patch.object(ra,'search',return_value=[carddoc]):
            packet=wf.evidence_packet(self.home,'patient')
        self.assertEqual(packet['standards'][0]['evidence_use'],'review_required')
        self.assertFalse(packet['standards'][0]['verified'])

    def test_doctor_detects_missing_pinned_snapshot(self):
        self.new_project();new=ra.build_index(self.home,[dict(self.docs[0],text='new')])
        (self.home/'knowledge'/(self.version+'.sqlite')).unlink()
        result=wf.doctor(self.home)
        self.assertEqual(result['current_version'],new)
        self.assertIn('project_snapshot_missing',[r['issue'] for r in result['findings']])

if __name__=='__main__':unittest.main()
