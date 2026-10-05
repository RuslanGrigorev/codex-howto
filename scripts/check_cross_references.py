"""Проверка локальных Markdown-ссылок и каталога; никаких сетевых запросов."""
from pathlib import Path
from urllib.parse import urlsplit,unquote
from bs4 import BeautifulSoup
from markdown_adapter import markdown
from course_core import source_files,check_course

def errors_for(root):
    root=root.resolve();errors=[]
    for file in source_files(root):
        rel=file.relative_to(root)
        if file.suffix!='.md' or any(x.startswith('.') for x in rel.parts) or rel.parts[0]=='openspec':continue
        soup=BeautifulSoup(markdown(file.read_text(encoding='utf-8')),'html.parser')
        for a in soup.select('a[href],img[src]'):
            value=a.get('href',a.get('src',''));url=urlsplit(value)
            if url.scheme or url.netloc or not url.path:continue
            target=(file.parent/unquote(url.path)).resolve()
            if not target.is_relative_to(root):errors.append(f'{rel}: ссылка выходит из проекта: {value}')
            elif not target.exists():errors.append(f'{rel}: ссылка не существует: {value}')
    if (root/'course.json').exists():errors.extend(check_course(root))
    return errors

def main():
    errors=errors_for(Path.cwd())
    for e in errors:print(e)
    if not errors:print('Все локальные ссылки и каталог проверены')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
