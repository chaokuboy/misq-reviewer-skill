#!/usr/bin/env python3
"""Prepare blinded human comparisons from genuine saved responses; never fabricate ratings."""
import argparse
import json
from pathlib import Path
import random
from statistics import mean
import uuid

import research_assistant as ra

DIMENSIONS=['relevance','evidence_accuracy','discrimination','answerability','continuity','actionability']


def prepare(home,input_file,seed=None):
    data=json.loads(Path(input_file).read_text())
    if not data.get('cases'):raise ValueError('Need actual paired responses before blinding')
    experiment=Path(home)/'evaluations'/uuid.uuid4().hex[:12]
    public=experiment/'rater';private=experiment/'coordinator'
    rng=random.Random(seed) if seed is not None else random.SystemRandom()
    mapping=[];packets=[];ratings=[];ids=set()
    for case in data['cases']:
        if case['id'] in ids:raise ValueError('Duplicate case ID')
        ids.add(case['id'])
        for field in ['baseline','skill']:
            response=case[field]
            if not isinstance(response.get('text'),str) or not response['text'].strip():raise ValueError('Responses cannot be empty')
            for provenance in ['model','generated_at','context_policy']:
                if not response.get(provenance):raise ValueError('Missing generation provenance: '+provenance)
        if case['baseline']['model']!=case['skill']['model']:raise ValueError('Use same model for controlled comparison')
        arms=['baseline','skill'];rng.shuffle(arms)
        blind_id=uuid.uuid4().hex[:10]
        packets.append({'id':blind_id,'scenario':case['scenario'],
                        'A':case[arms[0]]['text'],'B':case[arms[1]]['text']})
        mapping.append({'id':blind_id,'case_id':case['id'],'A':arms[0],'B':arms[1],
                        'provenance':{k:{x:v for x,v in case[k].items() if x!='text'} for k in arms}})
        ratings.append({'id':blind_id,'rater_id':None,'A':{d:None for d in DIMENSIONS},
                        'B':{d:None for d in DIMENSIONS},'preference':None,'reason':None})
    public.mkdir(parents=True);private.mkdir()
    ra.atomic_json(public/'comparisons.json',packets)
    ra.atomic_json(public/'ratings.json',ratings)
    ra.atomic_json(private/'key.json',mapping)
    (public/'README.md').write_text('''# 盲评说明
仅向评分者提供 rater 文件夹，不提供 coordinator/key.json。
对每个维度按 1–5 分评分：1 明显无效/错误，3 部分有用但有明显缺陷，5 具体且有充分依据。
维度：相关性、证据准确性、问题区分力、可回答性、承接前文、推动下一步。
填写 rater_id、preference（A/B/tie）和理由。来源难以核实时写明理由，不猜分。
固定情境比较与真实多轮对话效果不同，应另开展连续研究任务。
匿名编码不能完全隐藏写作风格，不等同完全消除评审偏差。
''')
    return {'experiment':str(experiment),'rater_packet':str(public),'status':'awaiting_real_human_ratings','cases':len(packets)}


def summarize(experiment,rating_files):
    keys={r['id']:r for r in json.loads((Path(experiment)/'coordinator/key.json').read_text())}
    scores=[];seen=set();pending=0
    for file in rating_files:
        for row in json.loads(Path(file).read_text()):
            if row['id'] not in keys:raise ValueError('Unknown blind case')
            rater=row.get('rater_id')
            if rater is not None:
                if not isinstance(rater,str) or not rater.strip():raise ValueError('Rater ID must be a nonempty string')
                rater=rater.strip()
                identity=(row['id'],rater)
                if identity in seen:raise ValueError('Duplicate case/rater rating')
                seen.add(identity)
            preference=row.get('preference')
            if preference is not None and preference not in ['A','B','tie']:raise ValueError('Invalid preference')
            reason=row.get('reason')
            if reason is not None and (not isinstance(reason,str) or not reason.strip()):raise ValueError('Ratings need a reason')
            incomplete=rater is None or preference is None or reason is None
            for arm in ['A','B']:
                if not isinstance(row.get(arm),dict):raise ValueError('Ratings need A and B score objects')
                for dim in DIMENSIONS:
                    value=row[arm].get(dim)
                    if value is None:
                        incomplete=True;continue
                    if type(value) is not int or not 1<=value<=5:raise ValueError('Scores must be integers 1–5; missing is not zero')
            if incomplete:
                pending+=1;continue
            key=keys[row['id']];skill='A' if key['A']=='skill' else 'B';baseline='B' if skill=='A' else 'A'
            scores.append({'id':row['id'],'rater':rater,
                           'differences':{d:row[skill][d]-row[baseline][d] for d in DIMENSIONS},
                           'preference':'tie' if row['preference']=='tie' else key[row['preference']]})
    case_ids=sorted({s['id'] for s in scores})
    # Equal weight per case, then average across cases; multiple raters don't multiply sample size.
    aggregate={d:mean(mean(s['differences'][d] for s in scores if s['id']==cid) for cid in case_ids) for d in DIMENSIONS} if scores else None
    return {'status':'descriptive_results' if scores else 'awaiting_real_human_ratings',
            'rated_cases':len(case_ids),'total_cases':len(keys),'rating_count':len(scores),'pending_rows':pending,
            'unrated_case_ids':sorted(set(keys)-set(case_ids)),
            'case_rating_counts':{cid:sum(s['id']==cid for s in scores) for cid in sorted(keys)},
            'mean_paired_difference':aggregate,'ratings':scores,
            'note':'Descriptive paired ratings only, not proof of superiority. Incomplete ratings and small convenience samples limit inference.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--home',type=Path,default=ra.ROOT/'.local')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('prepare');p.add_argument('input',type=Path)
    p=sub.add_parser('summarize');p.add_argument('experiment',type=Path);p.add_argument('ratings',type=Path,nargs='+')
    a=ap.parse_args();result=prepare(a.home,a.input) if a.cmd=='prepare' else summarize(a.experiment,a.ratings)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
