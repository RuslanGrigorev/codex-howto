"""Mutation tests of the REAL release gate; no substitute production logic."""
import copy,json,zipfile
from pathlib import Path
import pytest
from course_core import tree_hash,spec_hash,sha256
from package_course import package,validate_package
from verify import check_release_gate

@pytest.fixture
def gate(tmp_path):
    root=tmp_path
    (root/'openspec').mkdir();(root/'openspec/spec.md').write_text('Test fixture specification')
    (root/'sources.json').write_text(json.dumps({'target_cli':'0.160.0'}))
    required=[{'scenario_id':'AUTO','method':'automated'}, {'scenario_id':'MANUAL','method':'manual','artifact_required':True}, {'scenario_id':'LIVE','method':'live'}]
    (root/'validation.json').write_text(json.dumps({'required_cases':required}))
    site=root/'.learning/site'
    for name in ['index.html','source/LICENSE','source/NOTICE.md','source/course.json','source/scripts/verify.py','assets/progress.js']:
        p=site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('Independent fixture '+name)
    files={p.relative_to(site).as_posix():sha256(p) for p in site.rglob('*') if p.is_file()}
    (site/'.codex-course-build').write_text(json.dumps({'candidate_tree_sha256':tree_hash(root),'files':files}))
    artifact=package(root,site,root/'.learning/candidate.zip')
    log=root/'.learning/evidence/logs/check.log';log.parent.mkdir(parents=True);log.write_text('Fixture evidence; not a real model run.')
    data={'schema_version':1,'candidate_tree_sha256':tree_hash(root),'spec_sha256':spec_hash(root),'artifact_sha256':sha256(artifact),
          'reviewer':'test-fixture','environment':{'codex':'0.160.0','model':'fixture-model','provider':'fixture-provider'},
          'cases':[{'scenario_id':x['scenario_id'],'status':'PASS','notes':'fixture check','evidence':[{'path':'.learning/evidence/logs/check.log','sha256':sha256(log)}]} for x in required]}
    directory=root/'.learning/evidence/release';directory.mkdir()
    def evaluate(edit=None):
        changed=copy.deepcopy(data)
        if edit:edit(changed)
        (directory/'results.json').write_text(json.dumps(changed))
        return check_release_gate(root,directory,artifact)
    return root,site,artifact,log,data,directory,evaluate

def test_real_gate_accepts_complete_matching_fixture(gate):
    assert not gate[-1]()

@pytest.mark.parametrize('status',['FAIL','BLOCKED','NOT_RUN','SKIP',None])
def test_nonpass_blocks(gate,status):
    assert gate[-1](lambda d:d['cases'][0].update(status=status))

@pytest.mark.parametrize('change',[
    lambda d:d['cases'].pop(),
    lambda d:d['cases'].append(copy.deepcopy(d['cases'][0])),
    lambda d:d['cases'][0].update(scenario_id='UNKNOWN'),
    lambda d:d['cases'][0].update(scenario_id=[]),
    lambda d:d.update(cases=[42]),
    lambda d:d.update(cases={}),
    lambda d:d.update(candidate_tree_sha256='0'*64),
    lambda d:d.update(spec_sha256='0'*64),
    lambda d:d.update(artifact_sha256='0'*64),
    lambda d:d.pop('reviewer'),
    lambda d:d['cases'][1].pop('notes'),
    lambda d:d['environment'].update(codex='999.0.0'),
    lambda d:d['environment'].pop('model'),
    lambda d:d['cases'][0].update(evidence=[]),
    lambda d:d['cases'][0]['evidence'][0].update(sha256='0'*64),
    lambda d:d['cases'][0]['evidence'][0].update(path='README.md'),
    lambda d:d['cases'][0]['evidence'][0].update(path='../outside.log'),
])
def test_real_gate_rejects_mutated_evidence(gate,change):
    assert gate[-1](change)

def test_missing_proof_file_blocks(gate):
    gate[3].unlink();assert gate[-1]()

def test_changed_source_invalidates_evidence(gate):
    (gate[0]/'new.py').write_text('new source');assert gate[-1]()

def test_corrupt_package_blocks(gate):
    gate[2].write_bytes(b'not a zip');assert gate[-1]()

def test_symlink_evidence_outside_rejected(gate,tmp_path):
    root,_,_,log,*_=gate
    outside=root/'outside.txt';outside.write_text(log.read_text())
    log.unlink();log.symlink_to(outside)
    assert gate[-1]()

def test_missing_reports_do_not_pass(gate):
    root,_,artifact,_,_,directory,_=gate
    assert check_release_gate(root,directory,artifact)

def test_packager_refuses_stale_sources(gate):
    root,site,*_=gate;(root/'source.py').write_text('changed')
    with pytest.raises(ValueError):package(root,site,root/'.learning/new.zip')

def test_packager_refuses_modified_site(gate):
    root,site,*_=gate;(site/'index.html').write_text('tampered')
    with pytest.raises(ValueError):package(root,site,root/'.learning/new.zip')

def test_packager_refuses_output_inside_site(gate):
    root,site,*_=gate
    with pytest.raises(ValueError):package(root,site,site/'new.zip')

def test_reproducible_zip(gate):
    root,site,artifact,*_=gate
    other=package(root,site,root/'.learning/second.zip')
    assert artifact.read_bytes()==other.read_bytes()


def test_zip_manifest_malformed_shapes(tmp_path):
    import json,zipfile
    from package_course import validate_package
    for i,manifest in enumerate([None,[],42,{"schema_version":1,"files":[]},{"schema_version":1,"files":{"a":3}}]):
        path=tmp_path/f"malformed-{i}.zip"
        with zipfile.ZipFile(path,"w") as z:z.writestr("manifest.json",json.dumps(manifest))
        assert validate_package(path,expected_tree="a"*64)
