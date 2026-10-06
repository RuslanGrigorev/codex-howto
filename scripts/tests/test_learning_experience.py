"""Регрессии реального сборщика: ссылки, материалы, каталог и границы полноты."""
import json
import logging
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit
import pytest
from bs4 import BeautifulSoup
from build_website import WebsiteConfig, build_website, material_url
from check_coverage import check
from check_site import check as check_site
from course_core import source_files

ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    root = tmp_path_factory.mktemp('learning-site')/'source'
    root.mkdir()
    for src in source_files(ROOT):
        target = root/src.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    output=root/'.learning/site'
    build_website(WebsiteConfig(root, output, landing=True, language='ru'), logging.getLogger(__name__))
    return root, output


def test_multilesson_modules_and_stable_ids():
    data=json.loads((ROOT/'course.json').read_text(encoding='utf-8'))
    assert len(data['modules'])==10
    assert sum(len(m['lessons']) for m in data['modules'])==62
    for module in data['modules']:
        assert len(module['lessons'])>=4
        assert (ROOT/module['path']).is_file()
        for lesson in module['lessons']:
            assert lesson['outcome'] and not lesson['outcome'].endswith('и проверить результат на учебном примере.')
            text=(ROOT/lesson['path']).read_text(encoding='utf-8')
            assert 'Предпосылки' not in text
            assert 'Что нужно перед началом' in text


def test_mapping_does_not_claim_semantic_completeness():
    mapped=check(ROOT)
    assert mapped['status']=='PASS'
    assert mapped['mapped_lessons']==62
    assert mapped['meaning']=='STRUCTURAL_MAPPING_ONLY'
    assert not mapped['inventory_complete']
    assert check(ROOT, require_complete=True)['status']=='FAIL'


def test_all_display_links_and_runtime_assets(generated):
    root, site=generated
    errors,count=check_site(site)
    assert not errors, errors
    assert count>100


def test_nine_exercises_have_all_four_local_materials(generated):
    root,site=generated
    course=json.loads((root/'course.json').read_text(encoding='utf-8'))
    count=0
    for m in course['modules']:
        for lesson in m['lessons']:
            if not lesson.get('exercise_id'):continue
            page=site/lesson['path'].replace('.md','.html')
            soup=BeautifulSoup(page.read_text(encoding='utf-8'),'html.parser')
            links=soup.select('.exercise-materials a[href]')
            assert len(links)==4
            for link in links:
                assert not urlsplit(link['href']).scheme
                dest=(page.parent/unquote(link['href'])).resolve()
                assert dest.is_relative_to(site)
                assert dest.is_file()
            count+=1
    assert count==9


def test_footer_has_no_badges_or_placeholder_links(generated):
    _,site=generated
    for rel in ['index.html','guide.html','02-workflow/goal-control.html']:
        soup=BeautifulSoup((site/rel).read_text(encoding='utf-8'),'html.parser')
        assert not soup.select('a[href="#"]')
        assert 'codex-cli-course-ru' not in soup.footer.get_text()
        assert not soup.select('img[src*="shields.io"]')
        for forbidden in ['Previous','Next','Home','Edit on GitHub']:
            assert forbidden not in soup.get_text()


def test_raw_solution_exactly_matches_source(generated):
    root,site=generated
    for src in (root/'examples').glob('*/solution/*.py'):
        assert (site/'source'/src.relative_to(root)).read_bytes()==src.read_bytes()
        assert (site/unquote(material_url(src.relative_to(root).as_posix()))).is_file()


def test_material_html_is_escaped_not_executed(tmp_path):
    root=tmp_path/'repo';root.mkdir();(root/'README.md').write_text('# Example\n[code](examples/solution.py)',encoding='utf-8')
    (root/'examples').mkdir();(root/'examples/solution.py').write_text('<script>alert("wrong")</script>',encoding='utf-8')
    site=root/'site';build_website(WebsiteConfig(root,site),logging.getLogger(__name__))
    soup=BeautifulSoup((site/'materials/examples/solution.py.html').read_text(encoding='utf-8'),'html.parser')
    assert not soup.select('script')
    assert soup.code.get_text()=='<script>alert("wrong")</script>'


@pytest.mark.parametrize('link',['examples/missing.py','missing.md','../escape.py','#'])
def test_missing_or_escaping_link_fails_before_swap(tmp_path,link):
    root=tmp_path/'repo';root.mkdir();(root/'README.md').write_text('# Before',encoding='utf-8')
    site=root/'site';cfg=WebsiteConfig(root,site)
    build_website(cfg,logging.getLogger(__name__))
    original=(site/'index.html').read_bytes()
    (root/'README.md').write_text('# After\n[bad]('+link+')',encoding='utf-8')
    with pytest.raises((ValueError,RuntimeError)):
        build_website(cfg,logging.getLogger(__name__))
    assert (site/'index.html').read_bytes()==original


def test_goal_lessons_follow_catalog_order(generated):
    _,site=generated
    soup=BeautifulSoup((site/'02-workflow/plan-goal.html').read_text(encoding='utf-8'),'html.parser')
    links=soup.select('.page-nav a')
    assert [a['href'] for a in links]==['planning.html','goal-control.html']


def test_module_home_has_all_registered_lessons(generated):
    root,site=generated
    for m in json.loads((root/'course.json').read_text(encoding='utf-8'))['modules']:
        page=site/m['path'].replace('README.md','index.html')
        soup=BeautifulSoup(page.read_text(encoding='utf-8'),'html.parser')
        links={a['href'] for a in soup.select('article a[href]')}
        for l in m['lessons']:
            assert Path(l['path']).with_suffix('.html').name in links


def test_hints_are_readable_with_expandable_sections(generated):
    _,site=generated
    soup=BeautifulSoup((site/'materials/examples/small-fix/HINTS.md.html').read_text(encoding='utf-8'),'html.parser')
    assert len(soup.select('details'))==3
    assert len(soup.select('h1'))==1
    assert not soup.select('pre.source-code')
