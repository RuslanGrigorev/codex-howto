import copy,json
import pytest
from check_updates import approved,compare_candidate,parse_slash_commands

def baseline():
    snap={'slash_commands':['/goal'],'config_keys':['model'],'config_schema_sha256':'a'*64,'source_hashes':{'s':'b'*64}}
    return {'target_cli':'0.160.0','baseline_snapshot':snap,'sources':[{'id':'s','lesson_ids':['one']} ]}
def candidate():return {'candidate_cli':'0.160.0',**baseline()['baseline_snapshot']}

def test_unobserved_version_is_not_compatible():
    assert compare_candidate(baseline(),{'candidate_cli':'999.0.0'})['status']=='INCOMPLETE'

def test_identical_snapshot_only_unchanged():
    assert compare_candidate(baseline(),candidate())['status']=='UNCHANGED'

def test_changed_schema_same_keys_requires_review():
    c=candidate();c['config_schema_sha256']='c'*64
    assert compare_candidate(baseline(),c)['status']=='REVIEW_REQUIRED'

def test_new_version_alone_never_declared_compatible():
    c=candidate();c['candidate_cli']='999.0.0'
    assert compare_candidate(baseline(),c)['status']=='REVIEW_REQUIRED'

def test_changed_source_maps_affected_lessons():
    c=candidate();c['source_hashes']={'s':'x'*64}
    assert compare_candidate(baseline(),c)['affected_lessons']==['one']

@pytest.mark.parametrize('url',['http://github.com/a','https://github.com.evil.test/a','https://user:pw@github.com/a','file:///etc/passwd','https://127.0.0.1/a'])
def test_nonofficial_or_unsafe_url_rejected(url):
    with pytest.raises(ValueError):approved(url)

def test_parse_enum_rejects_unknown_shape():
    with pytest.raises(ValueError):parse_slash_commands('some other Rust source')

def test_parse_enum_honors_serialized_name():
    src='pub enum SlashCommand {\n'+''.join(n+',\n' for n in ['Model','Plan','Goal','Review','New','Resume','Fork','Diff','Mcp','Status'])+'#[strum(serialize = "setup-default-sandbox")]\nElevateSandbox,\n}'
    assert '/setup-default-sandbox' in parse_slash_commands(src)
