from pathlib import Path
from check_cross_references import errors_for

def test_missing_link(tmp_path):
    (tmp_path/'README.md').write_text('[bad](missing.md)')
    assert errors_for(tmp_path)

def test_valid_link(tmp_path):
    (tmp_path/'README.md').write_text('[ok](other.md)')
    (tmp_path/'other.md').write_text('# Other')
    assert not errors_for(tmp_path)

def test_escape_rejected(tmp_path):
    (tmp_path/'README.md').write_text('[bad](../outside.md)')
    assert errors_for(tmp_path)

def test_example_links_inside_code_are_not_navigation(tmp_path):
    (tmp_path/'README.md').write_text('```text\n[example](not-a-real-file)\n```')
    assert not errors_for(tmp_path)

def test_directory_without_readme_not_invented_requirement(tmp_path):
    (tmp_path/'01-topic').mkdir()
    (tmp_path/'01-topic/lesson.md').write_text('# Lesson')
    assert not errors_for(tmp_path)
