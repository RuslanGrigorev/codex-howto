"""Небольшие независимые проверки исходников и учебных контрактов."""
import argparse,json,subprocess,sys,tomllib
from pathlib import Path
from course_core import check_course,exercise_ids,clean_env,load_json
ROOT=Path(__file__).resolve().parent.parent

def exercises(root=ROOT):
    errors=[]
    for eid in sorted(exercise_ids(root)):
        folder=root/'examples'/eid;test=folder/'test.py'
        versions=[folder/'solution',folder/'starter']+sorted(folder.glob('broken_mutation*'))
        if len(versions)<3:errors.append(eid+': нет отрицательной мутации')
        for v in versions:
            if not v.is_dir():errors.append(eid+': нет '+v.name);continue
            try:
                r=subprocess.run([sys.executable,'-S',str(test)],cwd=v,env=clean_env(v),capture_output=True,text=True,timeout=15)
                ok=r.returncode==0 if v.name=='solution' else r.returncode==1
                print(eid+'/'+v.name+': '+('PASS' if ok else 'FAIL')+' (exit '+str(r.returncode)+')',flush=True)
                if not ok:errors.append(eid+'/'+v.name+': '+r.stdout+r.stderr)
            except subprocess.TimeoutExpired:errors.append(eid+'/'+v.name+': таймаут не засчитывается как ожидаемая ошибка')
    return errors

def config(root=ROOT):
    # Это ограниченный контракт ПОСТАВЛЯЕМЫХ ПРИМЕРОВ, не полная схема Codex.
    errors=[]
    for path in (root/'examples/config').glob('*.toml'):
        data=tomllib.loads(path.read_text(encoding='utf-8'))
        if set(data)-{'approval_policy','sandbox_mode','web_search','mcp_servers','model'}:errors.append('Неизвестные ключи учебного примера')
        if data.get('approval_policy') not in {'on-request','never'}:errors.append('Неверный approval_policy')
        if data.get('sandbox_mode') not in {'read-only','workspace-write','danger-full-access'}:errors.append('Неверный sandbox_mode')
    hooks=load_json(root/'examples/hooks/hooks.json')
    if set(hooks.get('hooks',{}))!={'PreToolUse'}:errors.append('Неверное событие hooks')
    for p in (root/'examples/subagents').glob('*.toml'):
        d=tomllib.loads(p.read_text(encoding='utf-8'))
        if not all(d.get(k) for k in ('name','description','developer_instructions')) or d.get('sandbox_mode')!='read-only':errors.append('Неверный учебный субагент')
    print('Проверен ограниченный контракт примеров. Полная официальная схема и CLI проверяются отдельно.')
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('check',choices=['catalog','exercises','config']);a=p.parse_args()
    try:errors={'catalog':lambda:check_course(ROOT),'exercises':exercises,'config':config}[a.check]()
    except (ValueError,OSError,KeyError,TypeError) as exc:errors=[str(exc)]
    for e in errors:print(e,file=sys.stderr)
    if not errors:print('PASS: '+a.check)
    return bool(errors)
if __name__=='__main__':sys.exit(main())
