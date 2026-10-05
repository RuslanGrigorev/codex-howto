"""Локальный прогресс ученика, совместимый с progress.js. Не сертификат."""
from __future__ import annotations
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from course_core import load_json, lessons, learning_path, contained, sha256
COURSE_ID = 'codex-cli-course-ru'

def validate(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('course_id') != COURSE_ID or not isinstance(data.get('lessons'), dict):
        raise ValueError('Несовместимый формат прогресса')
    for records in (data['lessons'], data.get('unmapped', {})):
        if not isinstance(records, dict): raise ValueError('Ожидался объект записей')
        for lid, r in records.items():
            if not re.fullmatch(r'[a-z0-9][a-z0-9.@-]*', lid) or lid in {'constructor', 'prototype', '__proto__'}:
                raise ValueError('Неверный ID')
            if not isinstance(r, dict) or type(r.get('revision')) is not int or r['revision']<1 or type(r.get('read')) is not bool:
                raise ValueError('Повреждённая запись урока')
            if 'needs_review' in r and type(r['needs_review']) is not bool: raise ValueError('Неверный needs_review')
            for key in ('quiz','exercise','codex_run'):
                v=r.get(key)
                if v is None: continue
                if not isinstance(v,dict) or type(v.get('passed')) is not bool or not isinstance(v.get('completed_at'),str): raise ValueError('Повреждённый результат')
                datetime.fromisoformat(v['completed_at'].replace('Z','+00:00'))
                if key=='quiz' and (type(v.get('score')) not in (int,float) or not 0<=v['score']<=1): raise ValueError('Неверный балл')
                if key=='exercise' and 'execution_hash' in v and not re.fullmatch(r'[a-f0-9]{64}',v['execution_hash']): raise ValueError('Неверный хеш')
    return data

def migrate(data, revisions):
    result=copy.deepcopy(validate(data));result.setdefault('unmapped',{})
    for lid,r in list(result['lessons'].items()):
        if lid not in revisions: result['unmapped'][lid]=result['lessons'].pop(lid)
        else: r['needs_review']=r['revision']!=revisions[lid] or r.get('needs_review',False)
    return result

def record_exercise(root: Path, exercise_id: str, passed: bool, execution_hash: str):
    path=learning_path(root,'progress.json')
    if path.exists() and path.stat().st_size>1024*1024: raise ValueError('Прогресс больше 1 МиБ')
    catalog=lessons(root)
    data=load_json(path) if path.exists() else {'schema_version':1,'course_id':COURSE_ID,'course_version':'0.3.0','lessons':{},'unmapped':{}}
    data=migrate(data,{k:l['revision'] for k,l in catalog.items()})
    for lid,l in catalog.items():
        if l.get('exercise_id')!=exercise_id: continue
        r=data['lessons'].get(lid)
        if not r or r['revision']!=l['revision'] or r.get('needs_review'):
            if r: data['unmapped'][lid+'@'+str(r['revision'])]=r
            r={'revision':l['revision'],'read':False,'quiz':None,'exercise':None,'codex_run':None,'needs_review':False}
            data['lessons'][lid]=r
        r['exercise']={'passed':passed,'execution_hash':execution_hash,'completed_at':datetime.now(timezone.utc).isoformat()}
    validate(data);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
    return path


def record_codex_run(root: Path, lid: str, evidence_path: Path):
    """Explicit learner self-attestation; never generates release evidence."""
    catalog=lessons(root)
    if lid not in catalog or not catalog[lid].get('live_required'):
        raise ValueError('Нет такого урока с нативной практикой')
    proof=contained(evidence_path,root/'.learning')
    if not proof.is_file() or proof.stat().st_size==0: raise ValueError('Нужен непустой локальный протокол')
    path=learning_path(root,'progress.json')
    if path.exists() and path.stat().st_size>1024*1024: raise ValueError('Прогресс больше 1 МиБ')
    data=load_json(path) if path.exists() else {'schema_version':1,'course_id':COURSE_ID,'course_version':'0.3.0','lessons':{},'unmapped':{}}
    data=migrate(data,{k:l['revision'] for k,l in catalog.items()})
    rec=data['lessons'].get(lid);revision=catalog[lid]['revision']
    if not rec or rec['revision']!=revision or rec.get('needs_review'):
        if rec:data['unmapped'][lid+'@'+str(rec['revision'])]=rec
        rec={'revision':revision,'read':False,'quiz':None,'exercise':None,'codex_run':None,'needs_review':False}
        data['lessons'][lid]=rec
    rec['codex_run']={'passed':True,'completed_at':datetime.now(timezone.utc).isoformat(),'attestation':'learner','evidence_sha256':sha256(proof)}
    validate(data);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
    return path

if __name__=='__main__':
    import argparse,sys
    p=argparse.ArgumentParser(description='Локальный самоотчёт ученика, не сертификация и не release PASS')
    p.add_argument('--record-codex-run',required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args()
    try:
        path=record_codex_run(Path(__file__).resolve().parent.parent,a.record_codex_run,a.evidence)
        print('Сохранён самоотчёт ученика: '+str(path))
    except (OSError,ValueError,KeyError,TypeError) as exc:print(str(exc),file=sys.stderr);sys.exit(2)
