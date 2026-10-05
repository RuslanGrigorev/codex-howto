from pathlib import Path
from check_publication import scan
from course_core import clean_env

def test_signature_scan_detects_synthetic_key_without_echo(tmp_path):
    synthetic='sk-'+'X'*40
    (tmp_path/'example.txt').write_text(synthetic)
    findings=scan(tmp_path)
    assert findings and synthetic not in str(findings)

def test_auth_file_name_detected(tmp_path):
    (tmp_path/'auth.json').write_text('{}')
    assert scan(tmp_path)

def test_child_env_does_not_inherit_tokens(monkeypatch,tmp_path):
    monkeypatch.setenv('OPENAI_API_KEY','not-a-real-key')
    monkeypatch.setenv('GITHUB_TOKEN','not-a-real-key')
    env=clean_env(tmp_path)
    assert 'OPENAI_API_KEY' not in env and 'GITHUB_TOKEN' not in env
