#!/usr/bin/env python3
"""Local evidence QA, issue reconciliation, retrieval evaluation and public DOI update checks."""
import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import unicodedata

import research_assistant as ra
import research_workflows as wf


def title_key(title):
    title=re.sub(r"^(editor.?s comments|guest editorial)\s*:\s*",'',title,flags=re.I)
    title=re.sub(r'\(open access\)','',title,flags=re.I)
    return ''.join(c for c in unicodedata.normalize('NFKC',title).casefold() if c.isalnum())


def parse_toc(text):
    issues=[]
    for part in re.split(r'(?=Management Information Systems Quarterly \| Vol \d+ \| Iss \d+)',text):
        head=re.search(r'Vol (\d+) \| Iss (\d+).*?(https://aisel\.aisnet\.org/misq/vol\d+/iss\d+/)',part)
        if not head:continue
        section=None;entries=[]
        for line in part.splitlines():
            if '†Journal Home' in line: break
            heading=re.search(r'## (.+)',line)
            if heading:
                section=heading.group(1).strip()
                continue
            if section not in {'Articles','Editorial','Editorials'}:continue
            for label in re.findall(r'cite\d+†([^]+)',line):
                if label=='PDF':continue
                entries.append({'title':label,'kind':'article' if section=='Articles' else 'editorial'})
        complete='Select an issue:' in part and any(e['kind']=='article' for e in entries)
        issues.append({'volume':int(head[1]),'issue':int(head[2]),'year':int(head[1])+1976,
                       'source_url':head[3],'parse_complete':complete,'entries':entries})
    return issues


def reconcile(home,folder):
    local=[d for d in ra.merged_snapshots(home) if d['kind']=='metadata']
    by_title={}
    for d in local:by_title.setdefault(title_key(d['title']),[]).append(d)
    issues=[];seen=set()
    for path in sorted(Path(folder).glob('*.txt')):
        for issue in parse_toc(path.read_text()):
            ident=(issue['volume'],issue['issue'])
            if ident in seen:raise ValueError('Duplicate issue source')
            seen.add(ident)
            for entry in issue['entries']:
                matched=by_title.get(title_key(entry['title']),[])
                entry['local_keys']=[d['zotero_key'] for d in matched]
                entry['status']='title_match' if len(matched)==1 else 'ambiguous' if matched else 'not_matched'
                if not matched:
                    candidates=sorted([(SequenceMatcher(None,title_key(entry['title']),title_key(d['title'])).ratio(),d) for d in local],key=lambda pair:pair[0],reverse=True)[:2]
                    entry['suggestions']=[{'score':round(score,3),'title':d['title'],'key':d['zotero_key']} for score,d in candidates if score>=0.85]
            issue['counts']=dict(Counter(e['status'] for e in issue['entries']))
            issues.append(issue)
    expected={(v,i) for v in range(46,51) for i in range(1,5) if (v,i)<=(50,3)}
    report={'checked_at':ra.now(),'scope':'MISQ 2022–2026 through 50(3); articles and editorials, excluding front matter',
            'missing_issue_sources':[list(x) for x in sorted(expected-seen)],'issues':issues,
            'totals':dict(Counter(e['status'] for i in issues for e in i['entries'])),
            'note':'Title matches are not DOI verification. Fuzzy suggestions require review; no automatic Zotero changes.'}
    ra.atomic_json(Path(home)/'quality/issue-reconciliation.json',report)
    return report


def get_json(url):
    # Only public bibliographic metadata is sent. Never send manuscript/fulltext to this endpoint.
    req=urllib.request.Request(url,headers={'User-Agent':'MISQ-local-research-assistant/1.0'})
    with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)


def paged_crossref(params,get=get_json):
    records=[];cursor='*';seen=set()
    for _ in range(50):
        url='https://api.crossref.org/works?'+urllib.parse.urlencode(dict(params,rows=100,cursor=cursor))
        payload=get(url)['message'];items=payload['items']
        if not items:return records
        for item in items:
            doi=item['DOI'].lower()
            if doi in seen:raise ValueError('Repeated DOI while paging Crossref')
            seen.add(doi);records.append(item)
        next_cursor=payload.get('next-cursor')
        if len(items)<100:return records
        if not next_cursor or next_cursor==cursor:raise ValueError('Crossref cursor did not advance')
        cursor=next_cursor
    raise ValueError('Crossref page budget exceeded; incomplete run not published as complete')


def update_check(home,get=get_json,dois=None):
    if dois: return doi_updates(home,dois,get)
    metadata=[d for d in ra.merged_snapshots(home) if d['kind']=='metadata']
    # Fetch all indexed update notices, not just notices published in the target year range.
    checks=[];notices=[]
    for issn in ['0276-7783','2162-9730']:
        try:
            rows=paged_crossref({'filter':'issn:'+issn+',is-update:true'},get)
            notices.extend(rows);checks.append({'issn':issn,'ok':True,'records':len(rows)})
        except Exception as exc:checks.append({'issn':issn,'ok':False,'error':type(exc).__name__+': '+str(exc)})
    targets={}
    for notice in notices:
        for update in notice.get('update-to',[]):
            target=ra.source_key({'doi':update.get('DOI',''),'id':''})
            targets.setdefault(target,[]).append({'notice_doi':notice['DOI'],'type':update.get('type','unknown'),
                                                  'updated':update.get('updated'),'title':notice.get('title',[])})
    rows=[]
    for d in metadata:
        doi=ra.source_key(d) if d.get('doi') else None
        alerts=targets.get(doi,[])
        rows.append({'zotero_key':d['zotero_key'],'doi':doi,'notices':alerts,
                     'status':'notice_found' if alerts else 'unknown' if not doi or not all(x['ok'] for x in checks) else 'no_notice_in_checked_feed'})
    report={'checked_at':ra.now(),'checks':checks,'items':rows,
            'limits':['No notice is not proof of no retraction/correction.',
                      'ISSN-scoped notices may miss notices registered under another journal; inspect publisher/Crossmark before strong use.',
                      'No automatic deletion or final retraction classification.']}
    wf.preserve_publication_report(home,'publication-updates.json',report)
    return report


def doi_updates(home,dois,get=get_json):
    rows=[]
    for raw in dict.fromkeys(dois):
        doi=ra.source_key({'doi':raw,'id':''})
        if not re.fullmatch(r'10\.\d{4,9}/\S+',doi):raise ValueError('Invalid DOI')
        row={'doi':doi,'checked_at':ra.now(),'status':'unknown'}
        try:
            work=get('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe=''))['message']
            notices=paged_crossref({'filter':'updates:'+doi},get)
            row['notices']=[{'doi':n['DOI'],'title':n.get('title',[]),'update_to':n.get('update-to',[])} for n in notices]
            row['record_update_to']=work.get('update-to',[])
            row['update_relations']={k:v for k,v in work.get('relation',{}).items()
                                     if any(word in k for word in ['retract','correct','update'])}
            row['status']='update_metadata_found' if notices or row['record_update_to'] or row['update_relations'] else 'no_notice_in_checked_metadata'
        except Exception as exc:row['error']=type(exc).__name__+': '+str(exc)
        rows.append(row)
    result={'checked_at':ra.now(),'scope':'DOI records and reverse updates filter','items':rows,
            'limits':'Public metadata may lag or omit notices. Unknown/errors never mean cleared. Inspect publisher/Crossmark for final status.'}
    wf.preserve_publication_report(home,'doi-updates.json',result)
    return result


def review_queue(home):
    docs,version=wf.documents(home)
    packets=[]
    for path in sorted((Path(home)/'cards').glob('*.json')):
        card=json.loads(path.read_text());ra.validate_card(card)
        ids=card['source'].get('document_ids',[])
        packets.append({'card_id':card['id'],'card_sha256':hashlib.sha256(json.dumps(card,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'claim':card['claim'],'applies_to':card['applies_to'],
                        'exceptions':card['exceptions'],'evidence':[docs[i] for i in ids if i in docs],
                        'missing_ids':[i for i in ids if i not in docs],
                        'review':{'verdict':None,'reason':None,'counterevidence':None,'reviewer':None},
                        'question':card.get('question')})
    output={'knowledge_version':version,'review_type':'semantic_review_pending','cards':packets,
            'instructions':'Judge supported / overstated / contradicted / insufficient. Check population, modality, causality, scope and exceptions. Do not auto-set verified.'}
    ra.atomic_json(Path(home)/'quality/semantic-review-queue.json',output)
    return {'cards':len(packets),'path':str(Path(home)/'quality/semantic-review-queue.json')}


def submit_semantic(home,file):
    review=json.loads(Path(file).read_text());docs,version=wf.documents(home,review['knowledge_version'])
    if review.get('reviewer_type') not in {'model','human'} or not review.get('reviewer'):
        raise ValueError('Declare reviewer type and identity')
    seen=set();cards={}
    for path in (Path(home)/'cards').glob('*.json'):
        card=json.loads(path.read_text());ra.validate_card(card)
        if card['id'] in cards:raise ValueError('Duplicate card ID')
        cards[card['id']]=card
    for row in review['reviews']:
        ra.slug(row['card_id'])
        if row['card_id'] in seen:raise ValueError('Duplicate card review')
        seen.add(row['card_id'])
        if row['card_id'] not in cards:raise ValueError('Unknown card ID')
        card=cards[row['card_id']]
        if row.get('card_sha256')!=hashlib.sha256(json.dumps(card,ensure_ascii=False,sort_keys=True).encode()).hexdigest():
            raise ValueError('Card changed since review')
        if row.get('verdict') not in {'supported','overstated','contradicted','insufficient'}:
            raise ValueError('Invalid semantic verdict')
        if not all(isinstance(row.get(k),str) and row[k].strip() for k in ['reason','scope_check','counterevidence_check']):
            raise ValueError('Semantic review needs reason, scope and counterevidence checks')
        if row['verdict']!='insufficient' and not row.get('evidence'):raise ValueError('Verdict needs evidence')
        for evidence in row.get('evidence',[]):
            doc=docs.get(evidence['document_id'])
            if not doc or not evidence.get('quote') or wf.normalize(evidence['quote']) not in wf.normalize(doc['text']):
                raise ValueError('Evidence quote missing from pinned document')
    import uuid
    destination=Path(home)/'quality/semantic-reviews'/(uuid.uuid4().hex+'.json')
    ra.atomic_json(destination,dict(review,recorded_at=ra.now(),note='No automatic verified promotion; a recorded judgment is not proof.'))
    return {'reviews':len(seen),'path':str(destination),'verified_changed':False}


def retrieval_eval(home,fixture):
    data=json.loads(Path(fixture).read_text());results=[]
    for case in data['queries']:
        relevant=set(case['relevant_keys'])
        if not relevant:raise ValueError('Retrieval query needs relevance labels')
        for mode in ['literal','expanded','multi_query']:
            queries=[case['query']] if mode!='multi_query' else [case['query']]+case.get('alternatives',[])
            hits=multi_search(home,queries,expand=mode!='literal',limit=5)
            keys=[h['zotero_key'] for h in hits]
            rank=next((i+1 for i,k in enumerate(keys) if k in relevant),None)
            results.append({'id':case['id'],'mode':mode,'recall_at_5':len(set(keys)&relevant)/len(relevant),
                            'reciprocal_rank':1/rank if rank else 0,'keys':keys})
    report={'checked_at':ra.now(),'label_status':data.get('label_status','unspecified'),'results':results,
            'note':'Small development set, not independent test or measured general recall.'}
    ra.atomic_json(Path(home)/'quality/retrieval-eval.json',report)
    return report


def multi_search(home,queries,expand=True,limit=5,version=None):
    db,version=ra.open_index(home,version);db.close()
    # Reciprocal-rank fusion of explicit query alternatives; no embedding service.
    scores={};chosen={}
    for query in dict.fromkeys(queries):
        hits=ra.search(home,query,version=version,limit=30,kinds=['pdf_fulltext','indexed_fulltext'],expand=expand,per_source=1)
        for rank,doc in enumerate(hits,1):
            key=ra.source_key(doc);scores[key]=scores.get(key,0)+1/(60+rank)
            chosen.setdefault(key,doc)
    return [dict(chosen[k],fusion_score=scores[k]) for k in sorted(scores,key=lambda k:(-scores[k],k))[:limit]]


def pdf_quality(path,out,ocr=False,pages=None,tessdata=None,ocr_all=False):
    import pymupdf
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    report={'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'pages':[],
            'limits':'Table structure and OCR are candidates. Formulas are retained visually, not converted to trustworthy LaTeX.'}
    with pymupdf.open(path) as doc:
        chosen=pages if pages is not None else range(1,len(doc)+1)
        if any(number<1 or number>len(doc) for number in chosen):raise ValueError('PDF page out of range')
        for number in chosen:
            page=doc[number-1];text=page.get_text(sort=True);flags=[];ocr_status='not_requested'
            if len(text.strip())<80:flags.append('sparse_text')
            if '\ufffd' in text:flags.append('replacement_characters')
            if ocr and ('sparse_text' in flags or ocr_all):
                try:
                    tp=page.get_textpage_ocr(language='eng',dpi=200,full=True,tessdata=str(tessdata) if tessdata else None)
                    text=page.get_text(textpage=tp);ocr_status='completed_unverified'
                except Exception as exc:ocr_status='failed: '+str(exc)
            tables=[]
            try:
                for table in page.find_tables().tables:
                    cells=table.extract()
                    first_rows=' '.join(str(c or '') for row in cells[:2] for c in row)
                    kind='figure_candidate' if re.search(r'\bFigure\s+\d',first_rows,re.I) else 'table_candidate'
                    tables.append({'bbox':list(table.bbox),'cells':cells,'classification':kind,'verified':False})
                if tables:flags.append('visual_region_review_required')
            except Exception as exc:flags.append('table_detection_failed: '+str(exc))
            page.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(out/f'page-{number}.png')
            blocks=[{'bbox':list(b[:4]),'text':b[4]} for b in page.get_text('blocks',sort=True) if b[6]==0]
            payload={'page':number,'text':text,'blocks':blocks,'tables':tables,'flags':flags,'ocr':ocr_status}
            ra.atomic_json(out/f'page-{number}.json',payload)
            report['pages'].append({'page':number,'characters':len(text),'tables':sum(t['classification']=='table_candidate' for t in tables),'figure_candidates':sum(t['classification']=='figure_candidate' for t in tables),'flags':flags,'ocr':ocr_status})
    ra.atomic_json(out/'report.json',report)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--home',type=Path,default=ra.ROOT/'.local')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('issues');p.add_argument('folder',type=Path)
    p=sub.add_parser('updates');p.add_argument('--doi',action='append');sub.add_parser('semantic-queue')
    p=sub.add_parser('semantic-submit');p.add_argument('review',type=Path)
    p=sub.add_parser('retrieval-eval');p.add_argument('fixture',type=Path)
    p=sub.add_parser('multi-search');p.add_argument('queries',nargs='+');p.add_argument('--version')
    p=sub.add_parser('pdf-quality');p.add_argument('pdf',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--ocr',action='store_true');p.add_argument('--pages',type=int,nargs='+');p.add_argument('--tessdata',type=Path);p.add_argument('--ocr-all',action='store_true')
    args=ap.parse_args();home=args.home.resolve()
    if args.cmd=='issues':result=reconcile(home,args.folder)
    elif args.cmd=='updates':result=update_check(home,dois=args.doi)
    elif args.cmd=='semantic-queue':result=review_queue(home)
    elif args.cmd=='semantic-submit':result=submit_semantic(home,args.review)
    elif args.cmd=='retrieval-eval':result=retrieval_eval(home,args.fixture)
    elif args.cmd=='multi-search':result=multi_search(home,args.queries,version=args.version)
    else:result=pdf_quality(args.pdf,args.output,args.ocr or args.ocr_all,args.pages,args.tessdata,args.ocr_all)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
