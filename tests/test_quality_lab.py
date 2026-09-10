import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import quality_lab as q
import blind_eval as be
import research_assistant as ra

class QualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.doc={'id':'source','title':'Patient autonomy','text':'Scope matters.',
                  'kind':'pdf_fulltext','zotero_key':'ITEM0001','verified':False}
        self.version=ra.build_index(self.home,[self.doc])

    def test_toc_parser_excludes_front_matter_and_footer(self):
        raw='''Management Information Systems Quarterly | Vol 46 | Iss 1 (https://aisel.aisnet.org/misq/vol46/iss1/)
L1: ## Front Matter
L2: cite9†Editorial Board L3: ## Editorial
L4: cite11†Editor's Comments: Scope matters
L5: ## Articles
L6: cite12†PDF L7: cite13†Research A
L8: cite14†Journal Home
L9: cite15†Most Popular Papers
Select an issue:
'''
        rows=q.parse_toc(raw)
        self.assertEqual([e['title'] for e in rows[0]['entries']],["Editor's Comments: Scope matters",'Research A'])
        self.assertTrue(rows[0]['parse_complete'])
        self.assertFalse(q.parse_toc(raw.replace('Select an issue:',''))[0]['parse_complete'])

    def test_empty_directory_never_claims_complete(self):
        result=q.reconcile(self.home,self.home)
        self.assertEqual(len(result['missing_issue_sources']),19)

    def test_title_normalization_preserves_substantive_differences(self):
        self.assertEqual(q.title_key("Editor's Comments: Scope!"),q.title_key('scope'))
        self.assertNotEqual(q.title_key('evidence from a trial'),q.title_key('evidence of a trial'))

    def test_reverse_update_finds_notice(self):
        def get(url):
            if '/works/' in url:return {'message':{'DOI':'10.1234/test'}}
            return {'message':{'items':[{'DOI':'10.1234/notice','update-to':[{'DOI':'10.1234/test','type':'retraction'}]}]}}
        result=q.doi_updates(self.home,['10.1234/test'],get)
        self.assertEqual(result['items'][0]['status'],'update_metadata_found')
        self.assertEqual(result['items'][0]['notices'][0]['doi'],'10.1234/notice')

    def test_network_failure_stays_unknown(self):
        def get(url):raise OSError('offline')
        self.assertEqual(q.doi_updates(self.home,['10.1234/test'],get)['items'][0]['status'],'unknown')

    def test_repeated_cursor_fails(self):
        batch=[{'DOI':f'10.1234/{i}'} for i in range(100)]
        with self.assertRaises(ValueError):q.paged_crossref({},lambda url:{'message':{'items':batch,'next-cursor':'*'}})

    def test_semantic_review_pins_card_and_evidence(self):
        card={'id':'sample','kind':'editorial','claim':'Scope matters','source':{},'applies_to':[],'exceptions':[],'tags':[],'verified':False}
        ra.atomic_json(self.home/'cards/arbitrary-filename.json',card)
        review={'knowledge_version':self.version,'reviewer_type':'model','reviewer':'test model','reviews':[{
            'card_id':'sample','card_sha256':hashlib.sha256(json.dumps(card,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            'verdict':'supported','reason':'same proposition','scope_check':'limited','counterevidence_check':'not found in provided excerpt',
            'evidence':[{'document_id':'source','quote':'Scope matters.'}]}]}
        file=self.home/'review.json';ra.atomic_json(file,review)
        self.assertFalse(q.submit_semantic(self.home,file)['verified_changed'])
        review['reviews'][0]['evidence'][0]['quote']='Invented';ra.atomic_json(file,review)
        with self.assertRaises(ValueError):q.submit_semantic(self.home,file)

    def paired(self):
        return {'cases':[{'id':'case','scenario':'question','baseline':{'text':'baseline answer','model':'same','generated_at':'now','context_policy':'baseline'},
                         'skill':{'text':'skill answer','model':'same','generated_at':'now','context_policy':'skill'}}]}

    def test_blind_mapping_separated_and_pending_not_zero(self):
        file=self.home/'pairs.json';ra.atomic_json(file,self.paired())
        result=be.prepare(self.home,file,seed=10);exp=Path(result['experiment'])
        packets=json.loads((exp/'rater/comparisons.json').read_text())
        self.assertEqual(set(packets[0]),{'id','scenario','A','B'})
        result=be.summarize(exp,[exp/'rater/ratings.json'])
        self.assertEqual(result['status'],'awaiting_real_human_ratings')
        self.assertIsNone(result['mean_paired_difference'])

    def test_ratings_unblind_correctly_and_reject_duplicate(self):
        file=self.home/'pairs.json';ra.atomic_json(file,self.paired())
        exp=Path(be.prepare(self.home,file,seed=3)['experiment']);key=json.loads((exp/'coordinator/key.json').read_text())[0]
        rows=json.loads((exp/'rater/ratings.json').read_text());row=rows[0]
        row.update(rater_id='teacher',preference='tie',reason='test rating')
        for arm in ['A','B']:row[arm]={d:4 if key[arm]=='skill' else 2 for d in be.DIMENSIONS}
        rating=exp/'rater/ratings.json';ra.atomic_json(rating,rows)
        result=be.summarize(exp,[rating]);self.assertEqual(result['mean_paired_difference']['relevance'],2)
        with self.assertRaises(ValueError):be.summarize(exp,[rating,rating])

    def test_empty_generated_responses_refused(self):
        p=self.paired();p['cases'][0]['skill']['text']=''
        file=self.home/'pairs.json';ra.atomic_json(file,p)
        with self.assertRaises(ValueError):be.prepare(self.home,file)
        self.assertFalse((self.home/'evaluations').exists())

    def test_incomplete_ratings_still_validate_and_deduplicate(self):
        file=self.home/'pairs.json';ra.atomic_json(file,self.paired())
        exp=Path(be.prepare(self.home,file)['experiment'])
        rating=exp/'rater/ratings.json'
        rows=json.loads(rating.read_text());row=rows[0]
        row['rater_id']='teacher'
        ra.atomic_json(rating,rows)
        with self.assertRaises(ValueError):be.summarize(exp,[rating,rating])
        for invalid in [0,6,True,2.5,'4']:
            row['A']['relevance']=invalid;ra.atomic_json(rating,rows)
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):be.summarize(exp,[rating])
        row['A']['relevance']=None;row['preference']='invalid';ra.atomic_json(rating,rows)
        with self.assertRaises(ValueError):be.summarize(exp,[rating])
        row['preference']='tie'
        for arm in ['A','B']:row[arm]={d:3 for d in be.DIMENSIONS}
        ra.atomic_json(rating,rows)
        result=be.summarize(exp,[rating])
        self.assertEqual(result['pending_rows'],1)
        self.assertIsNone(result['mean_paired_difference'])
        row['reason']='Synthetic test';row['rater_id']=' teacher '
        duplicate=copy.deepcopy(row);duplicate['rater_id']='teacher'
        ra.atomic_json(rating,[row,duplicate])
        with self.assertRaises(ValueError):be.summarize(exp,[rating])

    def test_summary_reports_omitted_cases(self):
        file=self.home/'pairs.json';ra.atomic_json(file,self.paired())
        exp=Path(be.prepare(self.home,file)['experiment'])
        rating=self.home/'empty-ratings.json';ra.atomic_json(rating,[])
        result=be.summarize(exp,[rating])
        blind_id=json.loads((exp/'coordinator/key.json').read_text())[0]['id']
        self.assertEqual(result['unrated_case_ids'],[blind_id])
        self.assertEqual(result['pending_rows'],0)
        self.assertEqual(result['case_rating_counts'],{blind_id:0})

    def test_summary_weights_cases_equally(self):
        pairs=self.paired();second=copy.deepcopy(pairs['cases'][0]);second['id']='second'
        pairs['cases'].append(second)
        file=self.home/'pairs.json';ra.atomic_json(file,pairs)
        exp=Path(be.prepare(self.home,file)['experiment'])
        keys=json.loads((exp/'coordinator/key.json').read_text());rows=[]
        for index,key in enumerate(keys):
            for teacher in range(3 if index==0 else 1):
                row={'id':key['id'],'rater_id':str(teacher),'preference':'tie','reason':'Synthetic test'}
                for arm in ['A','B']:
                    value=(5 if index==0 else 1) if key[arm]=='skill' else 3
                    row[arm]={d:value for d in be.DIMENSIONS}
                rows.append(row)
        rating=self.home/'ratings.json';ra.atomic_json(rating,rows)
        result=be.summarize(exp,[rating])
        self.assertEqual(result['rating_count'],4)
        self.assertEqual(result['mean_paired_difference']['relevance'],0)
        self.assertEqual(result['unrated_case_ids'],[])

    def test_fusion_pins_version_and_deduplicates(self):
        newer=ra.build_index(self.home,[dict(self.doc,id='new',text='unrelated',title='unrelated')])
        hits=q.multi_search(self.home,['Patient','autonomy'],version=self.version)
        self.assertEqual(len(hits),1);self.assertEqual(hits[0]['knowledge_version'],self.version)
        self.assertFalse(q.multi_search(self.home,['Patient']))

if __name__=='__main__':unittest.main()
