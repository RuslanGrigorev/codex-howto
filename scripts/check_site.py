"""Локальные HTML-пути и запрет сетевых runtime-ресурсов во всём пакете."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit,unquote
from bs4 import BeautifulSoup

def check(site):
    site=site.resolve();errors=[];count=0;anchors={}
    for page in site.rglob('*.html'):
        if 'source' in page.relative_to(site).parts: continue
        count+=1;soup=BeautifulSoup(page.read_text(encoding='utf-8'),'html.parser')
        for node in soup.select('a[href],script[src],link[href],img[src],source[srcset],iframe[src]'):
            key=next((k for k in ('href','src','srcset') if node.get(k)),None)
            if not key:continue
            values=[x.strip().split()[0] for x in node[key].split(',')] if key=='srcset' else [node[key]]
            for value in values:
                url=urlsplit(value)
                if url.scheme or url.netloc:
                    if node.name!='a' and url.scheme!='data':errors.append(f'{page.relative_to(site)}: внешний runtime ресурс {value}')
                    if url.scheme in {'javascript','vbscript'}:errors.append('Исполняемая URL-схема запрещена')
                    continue
                target=(page.parent/unquote(url.path)).resolve() if url.path else page
                if not target.is_relative_to(site):errors.append(f'{page.relative_to(site)}: выход из пакета {value}');continue
                if not target.exists():errors.append(f'{page.relative_to(site)}: нет {value}');continue
                if target.is_file() and target.suffix=='.html' and url.fragment:
                    if target not in anchors:
                        other=BeautifulSoup(target.read_text(encoding='utf-8'),'html.parser')
                        anchors[target]={n['id'] for n in other.select('[id]')}
                    if unquote(url.fragment) not in anchors[target]:errors.append(f'{page.relative_to(site)}: нет якоря {value}')
    return errors,count

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);a=p.parse_args()
    errors,count=check(a.site)
    for e in errors:print(e)
    print(f'HTML-файлов: {count}; ошибок: {len(errors)}')
    raise SystemExit(bool(errors))
