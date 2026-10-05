import copy,json,shutil,subprocess
from pathlib import Path
import pytest
from progress import validate,migrate
ROOT=Path(__file__).resolve().parents[2]

def valid():return {'schema_version':1,'course_id':'codex-cli-course-ru','lessons':{'one':{'revision':1,'read':True}}}

@pytest.mark.parametrize('record',[42,[],{}, {'revision':True,'read':False},{'revision':1,'read':'yes'},{'revision':1,'read':True,'quiz':{'passed':True,'score':float('nan'),'completed_at':'bad'}}])
def test_python_rejects_bad_record(record):
    d=valid();d['lessons']['one']=record
    with pytest.raises((ValueError,TypeError)):validate(d)

def test_revision_migration_does_not_overwrite_history():
    d=valid();new=migrate(d,{'one':2});assert new['lessons']['one']['needs_review'];assert not d['lessons']['one'].get('needs_review')

def test_removed_lesson_archived():
    assert 'one' in migrate(valid(),{})['unmapped']

def test_javascript_actual_progress_module():
    node=shutil.which('node')
    assert node,'Node.js нужен для unit-проверки JS; отсутствие не считается PASS'
    r=subprocess.run([node,str(ROOT/'scripts/tests/progress_checks.cjs'),str(ROOT/'scripts/website_templates/progress.js')],capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stdout+r.stderr
