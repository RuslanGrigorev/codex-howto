#!/usr/bin/env python3
"""Сбор/сравнение официальных источников. Никогда не устанавливает CLI и не правит курс."""
from __future__ import annotations
import argparse,hashlib,json,re,sys,urllib.request,urllib.parse
from pathlib import Path
from course_core import load_json
ALLOWED={'api.github.com','github.com','raw.githubusercontent.com','developers.openai.com','learn.chatgpt.com'}
LIMIT=8*1024*1024

def approved(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.hostname not in ALLOWED or p.username or p.password or p.port not in (None,443):raise ValueError('Источник не входит в HTTPS allowlist')
    return url
class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        approved(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_bytes(url):
    approved(url)
    request=urllib.request.Request(url,headers={'User-Agent':'codex-course-maintenance/0.2','Accept':'application/json,text/plain,text/html'})
    with urllib.request.build_opener(Redirects()).open(request,timeout=20) as r:
        approved(r.geturl());data=r.read(LIMIT+1)
    if len(data)>LIMIT:raise ValueError('Источник превышает лимит 8 МиБ')
    return data

def parse_slash_commands(source):
    match=re.search(r'pub enum SlashCommand\s*\{(.*?)\n\}',source,re.S)
    if not match:raise ValueError('Не найден enum SlashCommand')
    names=[];attrs=''
    for line in match.group(1).splitlines():
        line=line.strip()
        if not line or line.startswith('//'):continue
        if line.startswith('#['):attrs+=' '+line;continue
        m=re.fullmatch(r'([A-Z][A-Za-z0-9]+),',line)
        if not m:raise ValueError('Изменился синтаксис enum; нужен ручной разбор')
        override=re.search(r'to_string\s*=\s*"([^"]+)"',attrs) or re.search(r'serialize\s*=\s*"([^"]+)"',attrs)
        name=override.group(1) if override else re.sub(r'(?<!^)(?=[A-Z])','-',m.group(1)).lower()
        names.append('/'+name);attrs=''
    if len(names)<10:raise ValueError('Неполный список команд')
    return sorted(set(names))

def fetch_candidate(baseline):
    release=json.loads(fetch_bytes('https://api.github.com/repos/openai/codex/releases/latest'))
    tag=release['tag_name']
    if not re.fullmatch(r'rust-v\d+\.\d+\.\d+',tag):raise ValueError('Неизвестный формат стабильного релиза')
    base='https://raw.githubusercontent.com/openai/codex/'+tag+'/'
    source=fetch_bytes(base+'codex-rs/tui/src/slash_command.rs')
    schema=fetch_bytes(base+'codex-rs/core/config.schema.json')
    parsed=json.loads(schema)
    if not isinstance(parsed.get('properties'),dict):raise ValueError('Неизвестная структура официальной схемы')
    snapshots={}
    for item in baseline['sources']:
        if item.get('update_watch',True):snapshots[item['id']]=hashlib.sha256(fetch_bytes(item['url'])).hexdigest()
    return {'schema_version':1,'candidate_cli':tag.removeprefix('rust-v'),
            'slash_commands':parse_slash_commands(source.decode()),
            'config_keys':sorted(parsed['properties']),
            'config_schema_sha256':hashlib.sha256(schema).hexdigest(),
            'source_hashes':snapshots,'release_url':release['html_url']}

def compare_candidate(baseline,candidate):
    if not isinstance(candidate,dict) or not re.fullmatch(r'\d+\.\d+\.\d+',str(candidate.get('candidate_cli',''))):
        return {'status':'INCOMPLETE','issues':['Нет точной версии кандидата'],'affected_lessons':[]}
    required=['slash_commands','config_keys','source_hashes','config_schema_sha256']
    if any(not candidate.get(k) for k in required):
        return {'status':'INCOMPLETE','issues':['Недостаточно наблюдаемых данных: нужны команды, ключи схемы и хеши источников'],'affected_lessons':[]}
    snapshot=baseline.get('baseline_snapshot',{})
    issues=[];affected=set()
    old=set(snapshot.get('slash_commands',[]));new=set(candidate['slash_commands'])
    if old-new:issues.append({'removed_commands':sorted(old-new)})
    if new-old:issues.append({'added_commands':sorted(new-old)})
    for source in baseline.get('sources',[]):
        sid=source['id']
        if not source.get('update_watch',True):continue
        old_hash=snapshot.get('source_hashes',{}).get(sid)
        new_hash=candidate['source_hashes'].get(sid)
        if not old_hash or not new_hash or old_hash!=new_hash:
            affected.update(source.get('lesson_ids',[]));issues.append({'source_changed_or_unbaselined':sid})
    if snapshot.get('config_keys')!=candidate['config_keys'] or snapshot.get('config_schema_sha256')!=candidate['config_schema_sha256']:issues.append({'config_review_required':True})
    complete=all(snapshot.get(k) for k in required)
    same=complete and candidate['candidate_cli']==baseline['target_cli'] and not issues
    status='UNCHANGED' if same else 'REVIEW_REQUIRED' if complete else 'INCOMPLETE'
    return {'status':status,'baseline_cli':baseline['target_cli'],'candidate_cli':candidate['candidate_cli'],
            'affected_lessons':sorted(affected),'issues':issues,
            'note':'UNCHANGED означает равенство снимков, не проверенную совместимость новой модели/версии.'}

def migrate_progress_record(data,course_id,revisions):
    from progress import migrate,COURSE_ID
    try:
        if course_id!=COURSE_ID:raise ValueError('Чужой курс')
        return {'success':True,'error':None,'migrated_data':migrate(data,revisions)}
    except (ValueError,TypeError,KeyError) as exc:return {'success':False,'error':str(exc),'migrated_data':None}

def main():
    ap=argparse.ArgumentParser(description='Обновления источников: локально по умолчанию, сеть только с --fetch')
    ap.add_argument('--baseline',type=Path,default=Path(__file__).resolve().parent.parent/'sources.json')
    ap.add_argument('--candidate',type=Path);ap.add_argument('--fetch',action='store_true');ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    try:
        baseline=load_json(args.baseline)
        if args.fetch:
            if not args.output:raise ValueError('Для --fetch задайте --output; курс не изменяется')
            if args.output.resolve()==args.baseline.resolve():raise ValueError('Нельзя перезаписывать baseline')
            data=fetch_candidate(baseline)
        elif args.candidate:data=compare_candidate(baseline,load_json(args.candidate))
        else:data={'status':'INCOMPLETE','issues':['Кандидат не указан. Совместимость не оценивалась.']}
        if args.output:
            if args.output.resolve()==args.baseline.resolve():raise ValueError('Нельзя перезаписывать baseline')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(data,ensure_ascii=False,indent=2))
        return 0 if args.fetch or data.get('status')=='UNCHANGED' else 2
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'INCOMPLETE','error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
