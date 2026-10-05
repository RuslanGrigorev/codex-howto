"""Детерминированный автономный ZIP-кандидат. Сборка не означает допуск к релизу."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path,PurePosixPath
from course_core import tree_hash,load_json,sha256

def package(root,site,output):
    root,site,output=root.resolve(),site.resolve(),output.absolute()
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Symlink в пути ZIP')
    if output.resolve().is_relative_to(site):raise ValueError('ZIP нельзя писать внутрь собираемого сайта')
    if not (site/'index.html').is_file():raise ValueError('Нет собранного сайта')
    marker=load_json(site/'.codex-course-build')
    if not isinstance(marker,dict) or not isinstance(marker.get('files'),dict):raise ValueError('Некорректный маркер сборки')
    if marker.get('candidate_tree_sha256')!=tree_hash(root):raise ValueError('Сайт от другого дерева: сначала пересоберите')
    files={p.relative_to(site).as_posix():p for p in sorted(site.rglob('*')) if p.is_file()}
    expected={k:v for k,v in files.items() if k!='.codex-course-build'}
    if set(marker.get('files',{}))!=set(expected) or any(sha256(p)!=marker['files'][n] for n,p in expected.items()):raise ValueError('Сайт изменён после сборки')
    if any(p.is_symlink() for p in site.rglob('*')):raise ValueError('Symlink в сайте')
    manifest={'schema_version':1,'candidate_tree_sha256':tree_hash(root),'target_cli':load_json(root/'sources.json')['target_cli'],
              'files':{name:sha256(p) for name,p in files.items()}}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        def add(name,data):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
        for name,p in files.items():add(name,p.read_bytes())
        add('manifest.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2).encode())
    return output

def validate_package(path,expected_tree=None):
    errors=[]
    try:
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            if len(set(names))!=len(names):errors.append('Повтор ZIP-пути')
            for name in names:
                p=PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or '\\' in name:errors.append('Небезопасный ZIP-путь')
            manifest=json.loads(z.read('manifest.json'))
            if not isinstance(manifest,dict) or manifest.get('schema_version')!=1 or not isinstance(manifest.get('files'),dict):
                raise ValueError('Некорректный манифест ZIP')
            if any(not isinstance(k,str) or not isinstance(v,str) for k,v in manifest['files'].items()):
                raise ValueError('Некорректный путь или хеш манифеста')
            if expected_tree and manifest.get('candidate_tree_sha256')!=expected_tree:errors.append('Пакет от другого дерева исходников')
            expected=set(manifest['files'])|{'manifest.json'}
            if set(names)!=expected:errors.append('Манифест не совпадает с содержимым ZIP')
            for name,h in manifest['files'].items():
                if hashlib.sha256(z.read(name)).hexdigest()!=h:errors.append('Не совпал хеш '+name)
            for required in ['index.html','source/LICENSE','source/NOTICE.md','source/course.json','source/scripts/verify.py','assets/progress.js']:
                if required not in names:errors.append('Нет обязательного файла '+required)
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:errors.append(str(exc))
    return errors

def main():
    ap=argparse.ArgumentParser(description='Собрать автономный ZIP-кандидат курса')
    ap.add_argument('--site',type=Path,default=Path('.learning/site'));ap.add_argument('--output',type=Path,default=Path('.learning/dist/codex-course-candidate.zip'))
    args=ap.parse_args();root=Path(__file__).resolve().parent.parent
    try:
        p=package(root,args.site,args.output);errors=validate_package(p,tree_hash(root))
        if errors:raise ValueError('; '.join(errors))
        print('Кандидат собран (не подтверждение релиза): '+str(p));return 0
    except (ValueError,OSError) as exc:print(str(exc),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
