"""Реальный Chromium: file://, внешний доступ блокируется, квизы и прогресс проверяются."""
from __future__ import annotations
import argparse,json,os,shutil,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--site',type=Path,required=True);ap.add_argument('--mode',choices=['file','http','embedded'],default='file');args=ap.parse_args();site=args.site.resolve()
    try:from playwright.sync_api import sync_playwright
    except ImportError:print('BLOCKED: Playwright не установлен');return 2
    requests=[];errors=[];server=None;origin=None;checks=[]
    if args.mode=='http':
        from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
        from threading import Thread
        from functools import partial
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(site)))
        origin=f'http://127.0.0.1:{server.server_port}/'
        Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as pw:
            binary=os.environ.get('COURSE_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
            browser=pw.chromium.launch(headless=True,**({'executable_path':binary} if binary else {}))
            context=browser.new_context(offline=args.mode!='http',viewport={'width':1440,'height':1000})
            def route(r):
                if origin and r.request.url.startswith(origin):return r.continue_()
                if r.request.url.startswith(('http:','https:','ws:','wss:')):requests.append(r.request.url)
                r.abort()
            context.route('http**/*',route)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            def load(path):
                if args.mode=='file':return page.goto(path.as_uri(),wait_until='load')
                if args.mode=='http':
                    from urllib.parse import quote
                    return page.goto(origin+quote(path.relative_to(site).as_posix()),wait_until='load')
                # Only a supplemental DOM/render test. No navigation/file:// claim.
                from bs4 import BeautifulSoup
                soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser');scripts=[]
                for node in soup.select('script[src]'):
                    local=(path.parent/node['src']).resolve()
                    if not local.is_relative_to(site):raise ValueError('Script outside bundle')
                    scripts.append(local.read_text(encoding='utf-8'));node.decompose()
                for node in soup.select('link[rel=stylesheet]'):
                    local=(path.parent/node['href']).resolve()
                    if not local.is_relative_to(site):raise ValueError('Style outside bundle')
                    style=soup.new_tag('style');style.string=local.read_text(encoding='utf-8');node.replace_with(style)
                page.goto('about:blank');page.set_content(str(soup),wait_until='load')
                for script in scripts:page.add_script_tag(content=script)
            page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:','ws:','wss:')) and not (origin and r.url.startswith(origin)) else None)
            # Каждая сгенерированная страница открывается в реальном браузере.
            pages=[p for p in site.rglob('*.html') if 'source' not in p.relative_to(site).parts]
            for path in pages:
                response=load(path)
                if page.locator('html').get_attribute('lang')!='ru':errors.append('Нет lang=ru: '+path.name)
                # Все script/style/img должны существовать в поставке.
                missing=page.evaluate("""() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)""")
                errors.extend(missing)
            load(site/'index.html');page.locator('#course-search').fill('/goal')
            if page.locator('#search-results a').count()==0:errors.append('Поиск не находит /goal')
            course=json.loads((site/'source/course.json').read_text(encoding='utf-8'))
            lesson=next(l for m in course['modules'] for l in m['lessons'] if l.get('quiz_path'))
            url=site/lesson['path'].replace('.md','.html');load(url)
            page.evaluate('CodexProgress.reset()');page.locator('#mark-read').click()
            if page.evaluate('(id)=>CodexProgress.lessonStatus(id).complete',lesson['id']):errors.append('Чтение ошибочно завершило урок')
            quiz=json.loads((site/'source'/lesson['quiz_path']).read_text(encoding='utf-8'))
            if any('undefined' in text or not text.strip() for text in page.locator('#quiz-form legend').all_inner_texts()):errors.append('Не отображается текст вопроса')
            # Сначала все неправильные, затем все правильные ответы.
            for should_pass in (False,True):
                for q in quiz['questions']:
                    choice=next(o for o in q['options'] if o['is_correct']==should_pass)
                    page.locator('input[name="'+q['id']+'"][value="'+choice['id']+'"]').check()
                page.locator('#quiz-form button[type=submit]').click()
                actual=page.evaluate('(id)=>CodexProgress.getState().lessons[id].quiz.passed',lesson['id'])
                if actual!=should_pass:errors.append('Неверная оценка квиза')
            before=page.evaluate('CodexProgress.exportJSON()')
            for bad in ['{"schema_version":1,"course_id":"codex-cli-course-ru","lessons":[]}',
                        '{"schema_version":1,"course_id":"codex-cli-course-ru","lessons":{"start.overview":42}}']:
                accepted=page.evaluate('(text)=>{try{CodexProgress.importJSON(text);return true;}catch(e){return false;}}',bad)
                if accepted or page.evaluate('CodexProgress.exportJSON()')!=before:errors.append('Импорт повреждённого состояния не атомарен')
            page.evaluate('CodexProgress.reset()');page.evaluate('(s)=>CodexProgress.importJSON(s)',before)
            if page.evaluate('CodexProgress.exportJSON()')!=before:errors.append('JSON round-trip нарушен')
            checks.extend(['all-pages','search-goal','quiz-negative-positive','invalid-import-atomic','progress-roundtrip'])
            if args.mode in {'file','http'}:
                page.reload(wait_until='load')
                if page.evaluate('CodexProgress.exportJSON()')!=before: errors.append('Прогресс не сохраняется после перезагрузки')
                load(site/'index.html')
                if page.evaluate('CodexProgress.exportJSON()')!=before: errors.append('Прогресс не переносится между страницами')
                checks.append('reload-and-cross-page-storage')
            # All four material links must really open in an ordinary browser.
            for module in course['modules']:
                for item in module['lessons']:
                    if not item.get('exercise_id'): continue
                    load(site/item['path'].replace('.md','.html'))
                    links=page.locator('.exercise-materials a').evaluate_all('(xs)=>xs.map(a=>a.getAttribute("href"))')
                    if len(links)!=4: errors.append('Не все материалы: '+item['id'])
                    for link in links:
                        target=(site/item['path']).parent/link
                        load(target.resolve())
                        if page.locator('h1').count()!=1: errors.append('Нет заголовка материала: '+link)
            checks.append('36-material-pages')
            load(site/'index.html');page.screenshot(path=str(site.parent/'browser-desktop.png'),full_page=True)
            page.locator('#theme-toggle').click()
            if page.locator('html').get_attribute('data-theme')!='dark': errors.append('Тема не переключается')
            page.screenshot(path=str(site.parent/'browser-dark.png'),full_page=True)
            for width in (390,768,1440):
                page.set_viewport_size({'width':width,'height':900})
                for target in (site/'index.html',site/'02-workflow/goal-control.html',site/'reference/commands.html'):
                    load(target)
                    if page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1'): errors.append(f'Переполнение {width}: {target.name}')
            checks.append('light-dark-and-responsive')
            page.set_viewport_size({'width':390,'height':844});load(site/'index.html')
            if page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1'):errors.append('Горизонтальное переполнение на мобильном экране')
            out=site.parent/'browser-mobile.png';page.screenshot(path=str(out),full_page=True)
            browser.close()
    except Exception as exc:
        text=str(exc);print(text,file=sys.stderr)
        return 2 if any(x in text for x in ('Executable','playwright install','ERR_BLOCKED_BY_ADMINISTRATOR')) else 1
    if server:server.shutdown();server.server_close()
    print(json.dumps({'mode':args.mode,'checks':checks,'file_navigation_verified':args.mode=='file','pages_opened':len(pages),'external_requests':requests,'errors':errors},ensure_ascii=False,indent=2))
    return 1 if errors or requests else 0
if __name__=='__main__':sys.exit(main())
