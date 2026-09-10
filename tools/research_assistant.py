#!/usr/bin/env python3
"""Local evidence search, read-only Zotero ingestion and revisioned project state (optional pypdf for PDF extraction)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
STAGES = {'Clarity', 'Prompt', 'Challenge', 'Evaluate'}
STATES = {'已有支持', '待确认', '存在缺口', '不适用'}


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def slug(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', value):
        raise ValueError('ID must contain lowercase letters, digits, _ or - (max 80).')
    return value


def temporal(source_date, assessed):
    """Conservative interval comparison for year/month/day precision."""
    def bounds(value):
        import calendar
        if re.fullmatch(r'\d{4}', value):
            y = int(value)
            return date(y, 1, 1), date(y, 12, 31)
        if re.fullmatch(r'\d{4}-\d{2}', value):
            y, m = map(int, value.split('-'))
            return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
        d = date.fromisoformat(value)
        return d, d
    if not source_date:
        return '时序待确认'
    lo, hi = bounds(source_date)
    a, b = bounds(assessed)
    if lo > b:
        return '当代镜头'
    if hi <= a:
        return '评估时点前已存在'
    return '时序待确认'


def terms(text):
    text = text.lower()
    result = re.findall(r'[a-z0-9]+', text)
    for run in re.findall(r'[\u3400-\u9fff]+', text):
        result.extend([run] if len(run) == 1 else [run[i:i+2] for i in range(len(run)-1)])
    return result


def markdown_docs(root=ROOT):
    paths = [root/'profiles/misq.md', root/'profiles/misq_submission_guide.md']
    paths += sorted((root/'profiles/knowledge').glob('*.md'))
    docs = []
    for path in paths:
        lines = path.read_text(encoding='utf-8').splitlines()
        for start in range(0, len(lines), 24):
            text = '\n'.join(lines[start:start+28])
            relative = path.relative_to(root).as_posix()
            docs.append({'id': f'{relative}:{start+1}', 'title': relative,
                         'text': text, 'locator': f'{relative}:L{start+1}',
                         'kind': 'legacy_distillation', 'verified': False})
    return docs


def validate_card(card):
    if not isinstance(card,dict): raise ValueError('Card must be an object')
    required = {'id','kind','claim','applies_to','exceptions','source','verified','tags'}
    if not required <= card.keys():
        raise ValueError('Card missing required fields')
    slug(card['id'])
    if not isinstance(card['claim'],str) or not card['claim'].strip(): raise ValueError('claim must be nonempty text')
    for field in ('applies_to','exceptions','tags'):
        if not isinstance(card[field],list) or not all(isinstance(x,str) for x in card[field]):
            raise ValueError(field+' must be a list of strings')
    if card['kind'] not in {'policy','editorial','methodology','case','synthesis'}:
        raise ValueError('Invalid card kind')
    if type(card['verified']) is not bool:
        raise ValueError('verified must be boolean')
    if not isinstance(card['source'], dict):
        raise ValueError('source must be an object')
    for field in ('title','doi','date','locator','evidence','zotero_key','attachment_key'):
        value=card['source'].get(field)
        if value is not None and not isinstance(value,str): raise ValueError('source.'+field+' must be text or null')
    ids=card['source'].get('document_ids',[])
    if not isinstance(ids,list) or not all(isinstance(i,str) for i in ids): raise ValueError('document_ids must be string list')
    hashes=card['source'].get('document_hashes',{})
    if not isinstance(hashes,dict) or not all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) for h in hashes.values()):
        raise ValueError('document_hashes must map IDs to SHA256 strings')
    if card['verified'] and not all(card['source'].get(k) for k in ('title','locator','evidence')):
        raise ValueError('Verified cards require a title, locator and supporting evidence')
    if card['source'].get('date'): temporal(card['source']['date'],date.today().isoformat())
    if card['kind'] == 'case':
        fields = {'research_question','author_claim','analyst_interpretation','design','findings','limitations'}
        if not fields <= card.keys():
            raise ValueError('Case card missing fields (use null for unknowns)')


def card_docs(folder):
    docs = []
    seen = set()
    for path in sorted(Path(folder).glob('*.json')):
        card = json.loads(path.read_text(encoding='utf-8'))
        validate_card(card)
        if card['id'] in seen:
            raise ValueError('Duplicate card ID: '+card['id'])
        seen.add(card['id'])
        docs.append({'id':'card:'+card['id'], 'title':card['claim'],
                     'text':json.dumps(card, ensure_ascii=False), 'kind':card['kind'],
                     'locator':card['source'].get('locator'), 'verified':card['verified'],
                     'date':card['source'].get('date'), 'doi':card['source'].get('doi'),
                     'zotero_key':card['source'].get('zotero_key')})
    return docs


def build_index(home, docs):
    """Immutable content-addressed snapshots; publish pointer only after commit."""
    home = Path(home)
    encoded = json.dumps(sorted(docs, key=lambda x:x['id']), ensure_ascii=False, sort_keys=True).encode()
    version = hashlib.sha256(encoded).hexdigest()[:20]
    folder = home/'knowledge'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/(version+'.sqlite')
    if not target.exists():
        fd, tmp = tempfile.mkstemp(dir=folder, suffix='.sqlite')
        os.close(fd)
        try:
            with sqlite3.connect(tmp) as db:
                db.execute('CREATE TABLE docs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
                db.execute('CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, tokens)')
                for d in docs:
                    db.execute('INSERT INTO docs VALUES (?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
                    db.execute('INSERT INTO search VALUES (?,?)',(d['id'],' '.join(terms(d['title']+' '+d['text']))))
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    atomic_json(home/'current.json', {'version':version,'documents':len(docs),'published_at':now()})
    return version


# Explicit query aids, not a learned translation or a semantic similarity model.
QUERY_TERMS = {
    '患者': ['patient', 'patients'], '自主性': ['autonomy', 'autonomous'],
    '医疗': ['healthcare', 'clinical'], '推荐': ['recommendation', 'recommender'],
    '机制': ['mechanism', 'mechanisms'], '因果': ['causal', 'causality'],
    '访谈': ['interview', 'interviews'], '定性': ['qualitative'],
    '设计科学': ['design science'], '理论': ['theory', 'theorizing'],
    '公平': ['fairness', 'equity'], '信任': ['trust'], '隐私': ['privacy'],
    '平台': ['platform'], '创新': ['innovation'], '贡献': ['contribution'],
}


def open_index(home, version=None):
    home = Path(home).resolve()
    version = version or json.loads((home/'current.json').read_text())['version']
    if not re.fullmatch(r'[0-9a-f]{20}', version): raise ValueError('Invalid knowledge version')
    target = home/'knowledge'/(version+'.sqlite')
    if not target.exists(): raise ValueError('Pinned knowledge version not available')
    return sqlite3.connect(target.as_uri()+'?mode=ro', uri=True), version


def source_key(doc):
    doi = (doc.get('doi') or '').lower().strip()
    doi = re.sub(r'^(https?://(?:dx\.)?doi\.org/|doi:\s*)', '', doi)
    return doi or doc.get('zotero_key') or (doc.get('title') if doc.get('kind')=='legacy_distillation' else None) or doc['id']


def search(home, query, version=None, limit=5, *, year_from=None, year_to=None,
           kinds=None, verified_only=False, per_source=None, expand=False, match_all=False):
    if year_from and year_to and year_from > year_to: raise ValueError('Invalid year range')
    if per_source is not None and per_source < 1: raise ValueError('per_source must be positive')
    if expand and match_all: raise ValueError('Expansion uses alternative terms; do not combine with match=all')
    expanded = [word for key, values in QUERY_TERMS.items() if key in query for word in values] if expand else []
    tokens = list(dict.fromkeys(terms(query+' '+' '.join(expanded))))[:64]
    if not tokens: return []
    match = (' AND ' if match_all else ' OR ').join('"'+t+'"' for t in tokens)
    db, version = open_index(home, version)
    result, counts = [], {}
    try:
        rows = db.execute('SELECT docs.payload FROM search JOIN docs ON docs.id=search.id '
                          'WHERE search MATCH ? ORDER BY bm25(search), docs.id', (match,))
        for row in rows:
            d=json.loads(row[0])
            if kinds and d.get('kind') not in kinds: continue
            if verified_only and d.get('verified') is not True: continue
            year=re.search(r'\b(?:19|20)\d{2}\b', d.get('date') or '')
            if year_from or year_to:
                if not year: continue
                y=int(year.group())
                if (year_from and y<year_from) or (year_to and y>year_to): continue
            key=source_key(d)
            if per_source and counts.get(key,0)>=per_source: continue
            counts[key]=counts.get(key,0)+1
            d.update(knowledge_version=version, query_expansion=expanded,
                     matched_terms=[t for t in tokens if t in set(terms(d['title']+' '+d['text']))])
            result.append(d)
            if len(result)>=limit: break
    finally: db.close()
    return result


def local_get(route):
    # Do not send loopback requests through a system HTTP proxy, nor follow redirects off-host.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request('http://127.0.0.1:23119'+route, headers={'Zotero-API-Version':'3'})
    with opener.open(req, timeout=8) as response:
        data = response.read().decode('utf-8')
        return data if route.endswith('/file/view/url') else json.loads(data)


def paginated(route, get=local_get):
    rows, start, seen = [], 0, set()
    while True:
        batch = get(route+('?' if '?' not in route else '&')+f'limit=100&start={start}')
        if not isinstance(batch, list): raise ValueError('Expected Zotero item array')
        if not batch: break
        keys = [r['key'] for r in batch]
        if any(k in seen for k in keys): raise ValueError('Repeated Zotero page; snapshot not published')
        seen.update(keys); rows.extend(batch); start += len(batch)
        if len(batch)<100: break
    return rows


def pdf_pages(attachment, get=local_get, cache_home=None):
    """Read an existing local attachment without modifying it; optional pypdf dependency."""
    from pypdf import PdfReader
    path = attachment.get('path', '')
    if attachment.get('linkMode') != 'linked_file' or not Path(path).is_absolute():
        # The local API exposes the resolved path for both stored and linked files.
        url = get('/api/users/0/items/'+attachment['key']+'/file/view/url')
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'file' or parsed.netloc not in {'', 'localhost'}:
            raise ValueError('Expected local file URL')
        path = urllib.parse.unquote(parsed.path)
    cache_path = None
    if cache_home is not None:
        import pypdf
        digest = hashlib.sha256(('pdf-pages-v1:'+pypdf.__version__).encode())
        with open(path,'rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''): digest.update(block)
        cache_path=Path(cache_home)/'pdf-cache'/(digest.hexdigest()+'.json')
        if cache_path.exists():
            cached=json.loads(cache_path.read_text())
            return [(row[0],row[1]) for row in cached]
    reader = PdfReader(path)
    pages = [(i+1, page.extract_text() or '') for i, page in enumerate(reader.pages)]
    if cache_path is not None: atomic_json(cache_path,pages)
    return pages


def sync_zotero(home, collection, get=local_get, extract_pdfs=False, refresh_pdfs=False):
    if not re.fullmatch('[A-Z0-9]{8}', collection): raise ValueError('Use an eight-character Zotero collection key')
    rows = paginated('/api/users/0/collections/'+collection+'/items/top',get)
    docs, failures = [], []
    for row in rows:
        item = row['data']; key = row['key']
        if item.get('itemType') in {'attachment','note','annotation'}: continue
        title = item.get('title','')
        docs.append({'id':'zotero:'+key,'title':title,'text':item.get('abstractNote',''),
                     'kind':'metadata','verified':False,'zotero_key':key,'doi':item.get('DOI'),
                     'date':item.get('date'),'locator':'Zotero metadata','item_version':row.get('version')})
        # A failure on metadata enumeration aborts the snapshot; unreadable full text is reported.
        children = paginated('/api/users/0/items/'+key+'/children',get)
        for child in children:
            data=child['data']; attachment=child['key']
            if data.get('contentType')!='application/pdf': continue
            try:
                full=get('/api/users/0/items/'+attachment+'/fulltext')
                content=full.get('content','')
                if not content.strip(): raise ValueError('empty indexed text')
                for offset in range(0,len(content),1800):
                    docs.append({'id':f'zotero:{attachment}:{offset}', 'title':title,
                                 'text':content[offset:offset+2100], 'kind':'indexed_fulltext',
                                 'verified':False,'zotero_key':key,'attachment_key':attachment,
                                 'doi':item.get('DOI'), 'date':item.get('date'),
                                 'locator':f'Zotero 索引文本 offset {offset}（非 PDF 页码）'})
            except Exception as exc:
                if extract_pdfs:
                    try:
                        pages = pdf_pages(dict(data, key=attachment), get, cache_home=None if refresh_pdfs else home)
                        readable = [(page, text) for page, text in pages if text.strip()]
                        if not readable:
                            raise ValueError('No extractable PDF text; OCR may be needed')
                        for page, text in readable:
                            for offset in range(0, len(text), 1800):
                                docs.append({'id':f'zotero:{attachment}:p{page}:{offset}',
                                             'title':title, 'text':text[offset:offset+2100],
                                             'kind':'pdf_fulltext', 'verified':False,
                                             'zotero_key':key, 'attachment_key':attachment,
                                             'doi':item.get('DOI'), 'date':item.get('date'),
                                             'pdf_page':page,
                                             'locator':f'PDF physical page {page}, offset {offset}'})
                        if len(readable) < len(pages):
                            failures.append({'attachment_key':attachment,
                                             'reason':'partial_pdf_text',
                                             'empty_pages':[p for p,t in pages if not t.strip()]})
                        continue
                    except Exception as fallback:
                        exc = fallback
                failure = {'attachment_key':attachment,'reason':type(exc).__name__}
                if hasattr(exc, 'code'): failure['http_status'] = exc.code
                failures.append(failure)
    # Keep collections separate. Old snapshots remain available to existing projects.
    destination=Path(home)/'zotero'/collection
    atomic_json(destination/'snapshot.json', {'collection':collection,'synced_at':now(),
                'items':len(rows),'failures':failures,'documents':docs})
    return {'collection':collection,'items':len(rows),'chunks':len(docs),'failures':failures}


def merged_snapshots(home):
    """Choose a whole item's latest observed collection copy, never mix old/new chunks."""
    snapshots=[json.loads(p.read_text()) for p in sorted((Path(home)/'zotero').glob('*/snapshot.json'))]
    snapshots.sort(key=lambda s:(s['synced_at'],s['collection']))
    items={}
    for snapshot in snapshots:
        grouped={}
        for d in snapshot['documents']:
            grouped.setdefault(d['zotero_key'],[]).append(d)
        items.update(grouped)
    return [d for key in sorted(items) for d in items[key]]


def coverage(home):
    """Observed collection coverage, not a claim of complete journal coverage."""
    from collections import Counter
    result=[]
    for path in sorted((Path(home)/'zotero').glob('*/snapshot.json')):
        snap=json.loads(path.read_text())
        docs=snap['documents']
        metadata=[d for d in docs if d['kind']=='metadata']
        fulltext=[d for d in docs if d['kind'] in {'indexed_fulltext','pdf_fulltext'}]
        readable={d['zotero_key'] for d in fulltext}
        years=Counter()
        for d in metadata:
            match=re.search(r'\b(?:19|20)\d{2}\b', d.get('date') or '')
            years[match.group() if match else 'unknown']+=1
        result.append({'collection':snap['collection'],'synced_at':snap['synced_at'],
                       'metadata_items':len(metadata),'items_with_text':len(readable),
                       'items_without_text':len({d['zotero_key'] for d in metadata}-readable),
                       'text_chunks':len(fulltext),'years':dict(sorted(years.items())),
                       'failure_counts':dict(Counter(f['reason'] for f in snap['failures']))})
    return result


def validate_project(data):
    slug(data['project_id'])
    if data.get('schema_version')!=1 or data.get('stage') not in STAGES:
        raise ValueError('Unsupported schema or stage')
    date.fromisoformat(data['assessment_date'])
    if not re.fullmatch('[0-9a-f]{20}',data['knowledge_version']): raise ValueError('Invalid knowledge version')
    for field in ('facts','claims','uncertainties','decisions','questions','audit'):
        if not isinstance(data.get(field),list): raise ValueError(field+' must be a list')
    for row in data['audit']:
        if not isinstance(row,dict): raise ValueError('Audit entries must be objects')
        if row.get('state') not in STATES: raise ValueError('Invalid audit state')
        if row['state']=='存在缺口' and not all(row.get(k) for k in ('source','evidence','applicability')):
            raise ValueError('Confirmed deficiency requires source, evidence and applicability')
    for q in data['questions']:
        if not isinstance(q,dict) or not isinstance(q.get('question'),str) or not q['question'].strip():
            raise ValueError('Question entries need nonempty question text')
        if q.get('status') not in {'open','resolved','deferred'}: raise ValueError('Invalid question status')
        if q['status']=='resolved' and not q.get('answer'): raise ValueError('Resolved question needs answer')
    if 'research_plan' in data:
        from research_planning import assess_plan
        assess_plan(data['research_plan'])


def save_project(home, project_id, data, expected):
    import fcntl
    slug(project_id); validate_project(data)
    if data['project_id']!=project_id: raise ValueError('Project ID mismatch')
    folder=Path(home)/'projects'; folder.mkdir(parents=True,exist_ok=True)
    path=folder/(project_id+'.json')
    with open(folder/(project_id+'.lock'),'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=json.loads(path.read_text()) if path.exists() else None
        actual=old['revision'] if old else 0
        if expected!=actual: raise ValueError(f'Stale revision: expected {expected}, current {actual}')
        if not (Path(home)/'knowledge'/(data['knowledge_version']+'.sqlite')).exists():
            raise ValueError('Knowledge snapshot missing')
        data=dict(data,revision=actual+1,updated_at=now())
        if old: atomic_json(folder/'history'/project_id/(str(actual)+'.json'),old)
        atomic_json(path,data)
    return data


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--home',type=Path,default=ROOT/'.local')
    sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('build')
    p=sub.add_parser('search'); p.add_argument('query'); p.add_argument('--version'); p.add_argument('--limit',type=int,default=5)
    p.add_argument('--year-from',type=int); p.add_argument('--year-to',type=int)
    p.add_argument('--kind',action='append'); p.add_argument('--verified-only',action='store_true')
    p.add_argument('--per-source',type=int); p.add_argument('--expand',action='store_true')
    p.add_argument('--match',choices=['any','all'],default='any')
    p=sub.add_parser('sync-zotero'); p.add_argument('collection'); p.add_argument('--extract-pdfs',action='store_true'); p.add_argument('--refresh-pdfs',action='store_true')
    sub.add_parser('collections')
    sub.add_parser('coverage')
    p=sub.add_parser('project'); p.add_argument('action',choices=['new','show','save']); p.add_argument('id'); p.add_argument('--file',type=Path); p.add_argument('--expected-revision',type=int); p.add_argument('--assessment-date',default=date.today().isoformat())
    from research_workflows import add_commands, dispatch
    add_commands(sub)
    args=ap.parse_args(); home=args.home.resolve()
    if args.cmd=='build':
        docs=markdown_docs()+card_docs(home/'cards')+merged_snapshots(home)
        output={'version':build_index(home,docs),'documents':len(docs)}
    elif args.cmd=='search':
        output=search(home,args.query,args.version,max(1,min(50,args.limit)),
                      year_from=args.year_from,year_to=args.year_to,kinds=args.kind,
                      verified_only=args.verified_only,per_source=args.per_source,
                      expand=args.expand,match_all=args.match=='all')
    elif args.cmd=='coverage': output=coverage(home)
    elif args.cmd=='collections':
        output=[{'key':r['key'],'name':r['data']['name']} for r in paginated('/api/users/0/collections')]
    elif args.cmd=='sync-zotero': output=sync_zotero(home,args.collection,extract_pdfs=args.extract_pdfs,refresh_pdfs=args.refresh_pdfs)
    elif args.cmd!='project': output=dispatch(args,home)
    else:
        slug(args.id); path=home/'projects'/(args.id+'.json')
        if args.action=='show': output=json.loads(path.read_text())
        elif args.action=='new':
            version=json.loads((home/'current.json').read_text())['version']
            data={'schema_version':1,'project_id':args.id,'knowledge_version':version,
                  'assessment_date':args.assessment_date,'stage':'Clarity','next_action':None,
                  **{k:[] for k in ('facts','claims','uncertainties','decisions','questions','audit')}}
            output=save_project(home,args.id,data,0)
        else:
            if args.file is None or args.expected_revision is None: ap.error('save needs --file and --expected-revision')
            output=save_project(home,args.id,json.loads(args.file.read_text()),args.expected_revision)
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError,sqlite3.Error) as exc:
        raise SystemExit(f'{type(exc).__name__}: {exc}')
