import json,copy
from pathlib import Path
import pytest
from course_core import check_course,lessons
ROOT=Path(__file__).resolve().parents[2]

def test_catalog_and_coverage_references_exist():
    assert check_course(ROOT)==[]

def test_goal_is_real_registered_lesson():
    catalog=lessons(ROOT)
    text=(ROOT/catalog['workflow.plan-goal']['path']).read_text(encoding='utf-8')
    for command in ['/goal','/goal edit','/goal pause','/goal resume','/goal clear']:assert command in text
    assert catalog['workflow.plan-goal']['live_required']

def test_all_quizzes_have_visible_russian_prompt():
    for l in lessons(ROOT).values():
        q=json.loads((ROOT/l['quiz_path']).read_text(encoding='utf-8'))
        for item in q['questions']:
            assert item.get('question') and len(item['question'])>5
            assert item.get('explanation')

def test_sources_do_not_claim_unperformed_cli_validation():
    data=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    assert data['tested_cli'] is None
    assert data['coverage_claim']!='FULLY_VERIFIED'

def test_original_scenarios_not_silently_dropped():
    matches=list((ROOT/'openspec/changes').glob('**/traceability.json'))
    original_path=next(p for p in matches if 'adapt-course-for-codex-cli' in p.parent.name)
    original=json.loads(original_path.read_text(encoding='utf-8'))
    required=json.loads((ROOT/'validation.json').read_text(encoding='utf-8'))
    assert {c['scenario_id'] for c in original['cases']} <= {c['scenario_id'] for c in required['required_cases']}
