#!/usr/bin/env python3
"""Extract input-only development cases from the supplied DeepSeek Markdown bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import research_assistant as ra


def section(text, heading):
    lines=text.splitlines();starts=[i for i,line in enumerate(lines) if line==heading]
    if len(starts)!=1:raise ValueError('Expected one section: '+heading)
    body=[]
    for line in lines[starts[0]+1:]:
        if line.startswith('## '):break
        body.append(line)
    while body and (not body[-1].strip() or body[-1].strip()=='---'):body.pop()
    result='\n'.join(body).strip()
    if not result:raise ValueError('Empty input section')
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def import_bundle(source,output):
    source=Path(source);output=Path(output)
    if output.exists():raise ValueError('Output exists; use a new directory to preserve prior imports')
    files=sorted(source.rglob('*'))
    manifest={str(p.relative_to(source)):digest(p.read_bytes()) for p in files if p.is_file()}
    cases=[];case_sources={}
    for path in sorted((source/'ideas').glob('idea_*.md')):
        raw=path.read_text(encoding='utf-8')
        scenario=section(raw,'## 【输入（可直接粘贴）】')
        case_id='case_'+str(len(cases)+1).zfill(2)
        cases.append({'id':case_id,'scenario':scenario})
        case_sources[case_id]=str(path.relative_to(source))
    if not cases:raise ValueError('No idea inputs found')
    comparisons=[]
    for first in sorted((source/'baselines').glob('baseline_v1_idea_*.md')):
        second=first.with_name(first.name.replace('baseline_v1_','baseline_v2_',1))
        if not second.exists():continue
        inputs=[];metadata=[]
        for path in [first,second]:
            raw=path.read_text(encoding='utf-8')
            inputs.append(section(raw,'## 一、输入（被评稿件，原文粘贴）'))
            metadata.append(next((line for line in raw.splitlines() if '元信息：' in line),None))
        # Ignore formatting whitespace only; any substantive input change remains a confound.
        normalized=[re.sub(r'\s+','',s) for s in inputs]
        comparisons.append({'case':first.stem.replace('baseline_v1_',''),
                            'files':[first.name,second.name],
                            'input_sha256':[digest(s.encode('utf-8')) for s in inputs],
                            'same_input_ignoring_whitespace':normalized[0]==normalized[1],
                            'reported_metadata':metadata,
                            'execution_provenance':'self_reported_not_independently_verified'})
    protocol={'status':'synthetic_development_inputs_no_scores',
              'generation_policy':'Input-only synthetic development cases. Run conditions in separate contexts; do not expose source expectations or simulated supervisor opinions. Record actual model and skill/knowledge versions. This is not a held-out test set.',
              'cases':cases}
    report={'source':str(source.resolve()),'source_file_count':len(manifest),
            'source_sha256':manifest,'case_sources':case_sources,'case_count':len(cases),'baseline_comparisons':comparisons,
            'limitations':['No new model run or human rating performed.',
                           'Published-paper identities and local PDFs not verified by this importer.',
                           'Legacy expected verdicts and rejection thresholds are not current scoring criteria.']}
    ra.atomic_json(output/'scenarios.json',protocol)
    ra.atomic_json(output/'intake.json',report)
    return {'output':str(output),'case_count':len(cases),'source_file_count':len(manifest),
            'baseline_input_matches':{r['case']:r['same_input_ignoring_whitespace'] for r in comparisons}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Path to the supplied evaluation directory')
    parser.add_argument('--output',type=Path,required=True,help='New local output directory')
    args=parser.parse_args()
    print(json.dumps(import_bundle(args.source,args.output),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
