import json,logging,os,shutil
from pathlib import Path
import pytest
import verify
from build_website import WebsiteConfig,build_website,validate_output
from course_core import contained,learning_path,tree_hash

@pytest.fixture
def repo(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir();(root/'README.md').write_text('# Fixture')
    (root/'course.json').write_text(json.dumps({'modules':[{'id':'x','lessons':[{'id':'x.one','revision':1,'exercise_id':'known'}]}]}))
    f=root/'examples/known';(f/'starter').mkdir(parents=True);(f/'starter/code.py').write_text('value=1')
    (f/'test.py').write_text('from code import value\nassert value==1')
    monkeypatch.setattr(verify,'get_repo_root',lambda:root)
    return root

@pytest.mark.parametrize('kind',['root','parent','source','nonempty'])
def test_build_refuses_dangerous_path(tmp_path,kind):
    root=tmp_path/'repo';root.mkdir();(root/'README.md').write_text('# Safe')
    output={'root':root,'parent':tmp_path,'source':root/'examples','nonempty':root/'site'}[kind]
    if kind=='nonempty':output.mkdir();(output/'precious').write_text('keep')
    before=tree_hash(root)
    with pytest.raises(ValueError):validate_output(root,output)
    assert tree_hash(root)==before
    assert (root/'README.md').exists()

def test_build_refuses_symlink(tmp_path):
    root=tmp_path/'repo';root.mkdir();other=tmp_path/'elsewhere';other.mkdir();link=root/'site';link.symlink_to(other,target_is_directory=True)
    with pytest.raises(ValueError):validate_output(root,link)

def test_failed_rebuild_keeps_old_site(tmp_path):
    root=tmp_path/'repo';root.mkdir();(root/'README.md').write_text('# Before')
    cfg=WebsiteConfig(root,root/'site');build_website(cfg,logging.getLogger('test'))
    old=(root/'site/index.html').read_bytes()
    (root/'README.md').write_text('# After\n[broken](missing.md)')
    with pytest.raises((ValueError,RuntimeError)):build_website(cfg,logging.getLogger('test'))
    assert (root/'site/index.html').read_bytes()==old
    assert not list(root.glob('.codex-build-*'))

def test_prepare_never_overwrites(repo):
    ws=verify.prepare_exercise(repo,'known');(ws/'code.py').write_text('student edits')
    with pytest.raises(ValueError):verify.prepare_exercise(repo,'known')
    assert (ws/'code.py').read_text()=='student edits'

def test_prepare_unknown_rejected(repo):
    with pytest.raises(ValueError):verify.prepare_exercise(repo,'unknown')

def test_prepare_rejects_symlink_learning(repo,tmp_path):
    outside=tmp_path/'outside';outside.mkdir();(repo/'.learning').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):verify.prepare_exercise(repo,'known')
    assert not list(outside.iterdir())

def test_adjacent_workspace_does_not_execute(repo,tmp_path):
    outside=tmp_path/'repo-other';outside.mkdir();marker=outside/'executed'
    (outside/'test.py').write_text('from pathlib import Path\nPath("executed").write_text("bad")')
    assert verify.run_exercise_check('known',outside)==2
    assert not marker.exists()

def test_unknown_exercise_never_uses_student_test(repo):
    ws=verify.prepare_exercise(repo,'known');marker=ws/'executed'
    (ws/'test.py').write_text('from pathlib import Path\nPath("executed").write_text("bad")')
    assert verify.run_exercise_check('unknown',ws)==2
    assert not marker.exists()

def test_independent_test_ignores_student_test(repo):
    ws=verify.prepare_exercise(repo,'known');(ws/'test.py').write_text('raise RuntimeError("must not run")')
    # This fixture's module name is intentionally unambiguous.
    (ws/'code.py').rename(ws/'exercise_value.py')
    (repo/'examples/known/test.py').write_text('from exercise_value import value\nassert value == 1')
    assert verify.run_exercise_check('known',ws)==0
    data=json.loads((repo/'.learning/progress.json').read_text())
    assert data['lessons']['x.one']['exercise']['passed']
    assert not data['lessons']['x.one']['read']

def test_symlink_student_source_rejected(repo,tmp_path):
    ws=verify.prepare_exercise(repo,'known');(ws/'linked').symlink_to(tmp_path,target_is_directory=True)
    assert verify.run_exercise_check('known',ws)==2

def test_no_cli_is_blocked_not_mock_pass(monkeypatch,tmp_path):
    monkeypatch.setattr(verify.shutil,'which',lambda _:None)
    assert all(c['status']=='BLOCKED' for c in verify.run_live_checks(tmp_path,{}))
