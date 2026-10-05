#!/usr/bin/env python3
"""Проверки курса. PASS относится только к названной проверке, не ко всему продукту."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,re,shutil,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
from course_core import (canonical_hash,check_course,clean_env,contained,exercise_ids,
                         lessons,load_json,sha256,spec_hash,tree_hash,learning_path)

def get_repo_root():return Path(__file__).resolve().parent.parent

def compute_tree_sha256(root_dir,exclude_dirs=None):return tree_hash(Path(root_dir))

def environment():
    return {'os':platform.system(),'python':platform.python_version(),'codex':None,
            'provider':None,'model':None,'browsers':[]}

def overall(cases):
    if not cases:return 'NOT_RUN'
    if any(c['status']=='FAIL' for c in cases):return 'FAIL'
    if any(c['status']!='PASS' for c in cases):return 'BLOCKED'
    return 'PASS'

def evidence(root,path):
    p=contained(path,root)
    return {'path':p.relative_to(root).as_posix(),'sha256':sha256(p),'type':'file'}

def run_command(command,*,cwd,env=None,timeout=60):
    try:
        p=subprocess.run(command,cwd=cwd,env=env,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=timeout)
        return p.returncode,p.stdout+'\n'+p.stderr
    except subprocess.TimeoutExpired:return 124,'Превышен таймаут'
    except OSError as exc:return 127,str(exc)

def execute_case(root,sid,command,*,timeout=60,cwd=None,env=None):
    code,text=run_command(command,cwd=cwd or root,env=env,timeout=timeout)
    path=learning_path(root,'evidence/logs/'+sid+'.log');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('COMMAND '+json.dumps(command,ensure_ascii=False)+'\nEXIT '+str(code)+'\n'+text,encoding='utf-8')
    return {'scenario_id':sid,'status':'PASS' if code==0 else 'BLOCKED' if code==2 else 'FAIL',
            'message':text[-1500:],'evidence':[evidence(root,path)]}

def prepare_exercise(root,exercise_id):
    if exercise_id not in exercise_ids(root):raise ValueError('Неизвестный exercise_id')
    source=contained(root/'examples'/exercise_id/'starter',root/'examples')
    base=learning_path(root,'workspaces');base.mkdir(parents=True,exist_ok=True)
    destination=contained(base/exercise_id,base)
    # Повторная подготовка не затирает работу ученика.
    if destination.exists():raise ValueError('Каталог уже существует; исходники не перезаписаны')
    if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):raise ValueError('Symlink в упражнении')
    shutil.copytree(source,destination)
    return destination

def run_exercise_check(exercise_id,workspace_path):
    root=get_repo_root().resolve()
    try:
        if exercise_id not in exercise_ids(root):raise ValueError('Неизвестный exercise_id')
        if not re.fullmatch(r'[a-z0-9-]+',exercise_id):raise ValueError('Некорректный exercise_id')
        base=(root/'.learning/workspaces').resolve()
        contained(base,root)
        resolved=contained(Path(workspace_path),base)
        if not resolved.is_dir():raise ValueError('Рабочий каталог не найден; сначала --prepare')
        if any(p.is_symlink() for p in resolved.rglob('*')):raise ValueError('Symlink внутри workspace запрещён')
        test=contained(root/'examples'/exercise_id/'test.py',root/'examples')
        if not test.is_file():raise ValueError('Независимый test.py не найден')
        before=tree_hash(resolved)
        case=execute_case(root,'EXERCISE-'+exercise_id,[sys.executable,'-S',str(test)],cwd=resolved,
                          env=clean_env(resolved),timeout=15)
        from progress import record_exercise
        digest=canonical_hash({'workspace':before,'test':sha256(test),'case':case})
        path=record_exercise(root,exercise_id,case['status']=='PASS',digest)
        print(case['message']);print('Прогресс: '+str(path))
        return 0 if case['status']=='PASS' else 1
    except (ValueError,OSError,KeyError) as exc:
        print('Проверка отклонена: '+str(exc),file=sys.stderr);return 2

def run_offline_checks(root):
    commands=[
        ('CHK-CATALOG',[sys.executable,'scripts/check_project.py','catalog']),
        ('CHK-COVERAGE',[sys.executable,'scripts/check_coverage.py']),
        ('CHK-EXERCISES',[sys.executable,'scripts/check_project.py','exercises']),
        ('CHK-CONFIG',[sys.executable,'scripts/check_project.py','config']),
        ('CHK-PUBLIC-FILES',[sys.executable,'scripts/check_publication.py']),
        ('CHK-UNIT',[sys.executable,'-m','pytest','-q','scripts/tests']),
        ('CHK-SITE',[sys.executable,'scripts/build_website.py','--output','.learning/site']),
    ]
    cases=[execute_case(root,sid,cmd,timeout=180) for sid,cmd in commands]
    if cases[-1]['status']=='PASS':
        cases.append(execute_case(root,'CHK-SITE-LINKS',[sys.executable,'scripts/check_site.py','--site','.learning/site'],timeout=60))
        cases.append(execute_case(root,'CHK-BROWSER',[sys.executable,'scripts/browser_check.py','--site','.learning/site'],timeout=180))
    else:
        cases.append({'scenario_id':'CHK-SITE-LINKS','status':'BLOCKED','message':'Сайт не собран','evidence':[]})
        cases.append({'scenario_id':'CHK-BROWSER','status':'BLOCKED','message':'Сайт не собран','evidence':[]})
    return cases

def run_live_checks(root,env_info,*,allow_model_call=False,model=None,provider='openai',codex_home=None):
    binary=shutil.which('codex')
    blocked=lambda sid,msg:{'scenario_id':sid,'status':'BLOCKED','message':msg,'evidence':[]}
    if not binary:return [blocked('LIVE-CLI','Codex CLI не найден'),blocked('LIVE-EXEC','Нет реального CLI')]
    c=execute_case(root,'LIVE-CLI',[binary,'--version'])
    code,text=run_command([binary,'--version'],cwd=root)
    expected=load_json(root/'sources.json')['target_cli']
    match=re.search(r'\b\d+\.\d+\.\d+\b',text)
    env_info.update(codex=match.group(0) if match else None,provider=provider,model=model)
    if code or not match or match.group(0)!=expected:
        c['status']='FAIL';c['message']='Версия CLI не совпала с целевой '+expected
        return [c,blocked('LIVE-EXEC','Несовместимая версия')]
    if not allow_model_call or not model or codex_home is None:
        return [c,blocked('LIVE-EXEC','Нужны --allow-model-call, --model и отдельный --codex-home; вызовы модели могут тарифицироваться')]
    try:
        learning_path(root,'codex-home')
        home=contained(codex_home,root/'.learning')
        if not home.is_dir():raise ValueError('Изолированный CODEX_HOME не подготовлен')
        ws=Path(tempfile.mkdtemp(prefix='live-',dir=root/'.learning'))
        token='COURSE_'+os.urandom(12).hex();(ws/'marker.txt').write_text(token,encoding='utf-8')
        env=clean_env(ws);env['CODEX_HOME']=str(home)
        cmd=[binary,'--ask-for-approval','never','exec','--json','--sandbox','read-only',
             '--skip-git-repo-check','--cd',str(ws),'--model',model]
        if provider!='openai':cmd+=['--oss','--local-provider',provider]
        cmd+=['Прочитай marker.txt. Ответь по-русски и приведи точное содержимое файла. Не изменяй файлы.']
        before=tree_hash(ws)
        try:
            proc=subprocess.run(cmd,cwd=ws,env=env,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=180)
            rc=proc.returncode;events=proc.stdout.splitlines()
            text=proc.stdout+'\nSTDERR\n'+proc.stderr
        except subprocess.TimeoutExpired:
            rc=124;events=[];text='Таймаут реального вызова Codex'
        import importlib.util
        spec=importlib.util.spec_from_file_location('course_stream',root/'examples/cli-stream/solution/stream_parser.py')
        parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
        result=parser.CodexStreamParser().parse_stream(events,process_exit_code=rc)
        passed=result['success'] and token in result['output_text'] and tree_hash(ws)==before
        log=learning_path(root,'evidence/logs/LIVE-EXEC.log');log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(json.dumps({'command':cmd,'exit_code':rc,'result':result,'workspace_unchanged':tree_hash(ws)==before},ensure_ascii=False)+'\n'+text,encoding='utf-8')
        case={'scenario_id':'LIVE-EXEC','status':'PASS' if passed else 'FAIL','message':'Реальный exec: чтение файла, JSONL, код завершения и отсутствие изменений','evidence':[evidence(root,log)]}
        return [c,case]
    except (ValueError,OSError) as exc:return [c,blocked('LIVE-EXEC',str(exc))]

def check_release_gate(root,evidence_dir,artifact):
    """Только существующие доказательства. Недостающие сценарии блокируют выпуск."""
    errors=[];seen={}
    try:
        required={x['scenario_id']:x for x in load_json(root/'validation.json')['required_cases']}
        if len(required)!=len(load_json(root/'validation.json')['required_cases']):raise ValueError('Повтор обязательного scenario_id')
        if not required:raise ValueError('Пустой обязательный набор проверок')
        tree,spec=tree_hash(root),spec_hash(root)
        source_registry=load_json(root/'sources.json')
        target=source_registry['target_cli']
        if 'DOCS-SCOPE-REVIEW' in required:
            from check_coverage import check as check_coverage
            coverage=check_coverage(root,require_complete=True)
            errors.extend('Покрытие: '+msg for msg in coverage['errors'])
        if evidence_dir is None or not evidence_dir.is_dir():raise ValueError('Нет каталога доказательств')
        if artifact is None or not artifact.is_file():raise ValueError('Нет проверяемого ZIP-кандидата')
        from package_course import validate_package
        errors.extend(validate_package(artifact,expected_tree=tree))
        artifact_sha=sha256(artifact)
        for report in sorted(evidence_dir.glob('*.json')):
            data=load_json(report)
            if not isinstance(data,dict) or data.get('schema_version')!=1:errors.append(f'{report.name}: неверная схема');continue
            if data.get('candidate_tree_sha256')!=tree or data.get('spec_sha256')!=spec:
                errors.append(f'{report.name}: доказательства от другого дерева/спецификации');continue
            if not isinstance(data.get('cases'),list):errors.append(report.name+': cases должен быть массивом');continue
            for case in data['cases']:
                if not isinstance(case,dict):errors.append(report.name+': case должен быть объектом');continue
                sid=case.get('scenario_id')
                if not isinstance(sid,str):errors.append('scenario_id должен быть строкой');continue
                if sid not in required:errors.append(f'Неизвестный scenario_id: {sid}');continue
                if sid in seen:errors.append('Дублирующий scenario_id: '+sid);continue
                seen[sid]=case
                if case.get('status')!='PASS':errors.append(sid+': '+str(case.get('status')))
                method=required[sid].get('method','manual')
                if method=='manual' and (not isinstance(data.get('reviewer'),str) or not data['reviewer'].strip() or not isinstance(case.get('notes'),str) or not case['notes'].strip()):
                    errors.append(sid+': нет ручной подписи и пояснения')
                if method=='live':
                    env=data.get('environment',{})
                    if not isinstance(env,dict):errors.append(sid+': environment должен быть объектом');continue
                    if env.get('codex')!=target or (required[sid].get('model_required',True) and (not env.get('model') or not env.get('provider'))):
                        errors.append(sid+': нет точной версии CLI/модели/провайдера')
                if required[sid].get('artifact_required') and data.get('artifact_sha256')!=artifact_sha:
                    errors.append(sid+': проверен другой артефакт')
                refs=case.get('evidence')
                if not isinstance(refs,list) or not refs:errors.append(sid+': нет файлов доказательства');continue
                for ref in refs:
                    try:
                        path=contained(root/ref['path'],root/'.learning/evidence')
                        if not path.is_file() or not re.fullmatch(r'[a-f0-9]{64}',str(ref.get('sha256',''))) or sha256(path)!=ref['sha256']:
                            raise ValueError('Нет файла или не совпал SHA-256')
                    except (OSError,ValueError,KeyError,TypeError) as exc:errors.append(sid+': '+str(exc))
        missing=sorted(set(required)-set(seen))
        if missing:errors.append('Нет обязательных результатов: '+', '.join(missing))
    except (OSError,ValueError,KeyError,TypeError) as exc:errors.append(str(exc))
    return errors

def run_release_checks(root,evidence_dir,artifact=None):
    errors=check_release_gate(root,evidence_dir,artifact)
    return [{'scenario_id':'RELEASE-GATE','status':'FAIL' if errors else 'PASS','message':'\n'.join(errors) or 'Обязательные доказательства сопоставлены с кандидатом','evidence':[]}]

def main():
    ap=argparse.ArgumentParser(description='Проверки автономного курса Codex CLI')
    ap.add_argument('--profile',choices=['offline','live','release'],default='offline')
    ap.add_argument('--exercise');ap.add_argument('--prepare');ap.add_argument('--workspace',type=Path)
    ap.add_argument('--report',type=Path);ap.add_argument('--evidence-dir',type=Path);ap.add_argument('--artifact',type=Path)
    ap.add_argument('--allow-model-call',action='store_true');ap.add_argument('--model')
    ap.add_argument('--provider',choices=['openai','ollama','lmstudio'],default='openai');ap.add_argument('--codex-home',type=Path)
    args=ap.parse_args();root=get_repo_root()
    if args.prepare:
        try:print('Подготовлено: '+str(prepare_exercise(root,args.prepare)));return 0
        except (ValueError,OSError) as exc:print(str(exc),file=sys.stderr);return 2
    if args.exercise:
        return run_exercise_check(args.exercise,args.workspace or root/'.learning/workspaces'/args.exercise)
    env=environment();before=tree_hash(root)
    if args.profile=='offline':cases=run_offline_checks(root)
    elif args.profile=='live':cases=run_live_checks(root,env,allow_model_call=args.allow_model_call,model=args.model,provider=args.provider,codex_home=args.codex_home)
    else:cases=run_release_checks(root,args.evidence_dir,args.artifact)
    if tree_hash(root)!=before:cases.append({'scenario_id':'TREE-UNCHANGED','status':'FAIL','message':'Исходники изменились во время проверки','evidence':[]})
    report={'schema_version':1,'profile':args.profile,'candidate_tree_sha256':before,'spec_sha256':spec_hash(root),
            'environment':env,'cases':cases,'overall':overall(cases),'timestamp':datetime.now(timezone.utc).isoformat()}
    if args.artifact and args.artifact.is_file():report['artifact_sha256']=sha256(args.artifact)
    path=args.report or learning_path(root,'reports/'+args.profile+'.json')
    try:
        path=contained(path,root/'.learning')
        learning_path(root,path.relative_to(root/'.learning').as_posix())
    except ValueError as exc:print('Недопустимый путь отчёта: '+str(exc),file=sys.stderr);return 2
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for c in cases:print(c['scenario_id']+': '+c['status'])
    print('Итог: '+report['overall']+'; отчёт: '+str(path))
    return 0 if report['overall']=='PASS' else 1 if report['overall']=='FAIL' else 2
if __name__=='__main__':sys.exit(main())
