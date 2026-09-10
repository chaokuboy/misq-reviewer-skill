import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import import_deepseek_eval as importer
import behavior_run
import research_assistant as ra


class ImportTests(unittest.TestCase):
    def test_dialogue_packet_preserves_turns_but_redacts_arm_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            ra.atomic_json(output/'dialogue-inputs.json',{'turns':['turn']*5})
            for arm in ['baseline','skill']:
                (output/arm).mkdir()
                (output/arm/'handoff.md').write_text('Facts and unknowns')
                for number in range(1,6):
                    (output/arm/f'dialogue_{number}.md').write_text('Answer '+str(output/arm/'handoff.md'))
            with patch.object(behavior_run.blind_eval,'prepare',return_value={'status':'test'}):
                behavior_run.collect_dialogue(output)
            pairs=json.loads((output/'dialogue-paired.json').read_text())['cases'][0]
            for arm in ['baseline','skill']:
                text=pairs[arm]['text']
                self.assertNotIn(str(output/arm),text)
                self.assertIn('Turn 5',text)
                self.assertIn('Facts and unknowns',text)

    def test_behavior_freeze_excludes_private_corpus_and_hashes_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';output=Path(tmp)/'run'
            ra.atomic_json(root/'.local/evaluations/deepseek-inputs-20260910/scenarios.json',
                           {'cases':[{'id':'case_02','scenario':'Actual question'}]})
            (root/'SKILL.md').write_text('skill',encoding='utf-8')
            (root/'profiles').mkdir();(root/'profiles/profile.md').write_text('profile')
            (root/'.local/private.txt').write_text('PRIVATE CORPUS')
            result=behavior_run.freeze(root,output)
            self.assertEqual(result['single_turn_cases'],3)
            self.assertFalse((output/'snapshot/.local').exists())
            manifest=json.loads((output/'manifest.json').read_text())
            self.assertEqual(manifest['files']['SKILL.md'],importer.digest(b'skill'))
            with self.assertRaises(ValueError):behavior_run.freeze(root,output)

    def test_behavior_collect_rejects_empty_output_before_blinding(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            ra.atomic_json(output/'manifest.json',{'snapshot_sha256':'test'})
            ra.atomic_json(output/'cases.json',{'cases':[{'id':'case','scenario':'question'}]})
            (output/'baseline').mkdir();(output/'baseline/case.md').write_text(' ')
            with self.assertRaises(ValueError):behavior_run.collect(output)
            self.assertFalse((output/'paired-responses.json').exists())

    def test_excludes_expectations_and_detects_changed_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';output=Path(tmp)/'output'
            (source/'ideas').mkdir(parents=True);(source/'baselines').mkdir()
            (source/'ideas/idea_01_near_publishable.md').write_text('# Expected verdict in title\n## 【输入（可直接粘贴）】\n> Actual question\n\n---\n## Expected\nSECRET RUBRIC\n',encoding='utf-8')
            for version,body in [('v1','Original input'),('v2','Changed input')]:
                (source/f'baselines/baseline_{version}_idea_01.md').write_text('## 一、输入（被评稿件，原文粘贴）\n'+body+'\n## 二、技能输出（原文，不要事后润色）\nAnswer',encoding='utf-8')
            result=importer.import_bundle(source,output)
            scenarios=json.loads((output/'scenarios.json').read_text())
            self.assertEqual(scenarios['cases'][0]['scenario'],'> Actual question')
            self.assertEqual(scenarios['cases'][0]['id'],'case_01')
            self.assertNotIn('near_publishable',(output/'scenarios.json').read_text())
            self.assertNotIn('SECRET RUBRIC',(output/'scenarios.json').read_text())
            self.assertFalse(result['baseline_input_matches']['idea_01'])
            with self.assertRaises(ValueError):importer.import_bundle(source,output)

    def test_ambiguous_or_missing_input_refused(self):
        for raw in ['# no section','## Input\n\n## Other','## Input\none\n## Input\ntwo']:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):importer.section(raw,'## Input')


if __name__=='__main__':unittest.main()
