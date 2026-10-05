"""Ограниченный локальный поиск кандидатов в секреты + явная проверка истории Git."""
from __future__ import annotations
import argparse,json,re,shutil,subprocess,sys
from pathlib import Path
from course_core import source_files
ROOT=Path(__file__).resolve().parent.parent
# Сигнатуры — только один уровень проверки, не гарантия отсутствия секретов.
PATTERNS=[re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
          re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
          re.compile(r'\bgithub_pat_[A-Za-z0-9_]{50,}\b'),
          re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b'),
          re.compile(r'\bAKIA[0-9A-Z]{16}\b')]

def scan(root):
    findings=[]
    for path in source_files(root):
        rel=path.relative_to(root).as_posix()
        if path.name in {'auth.json','.env','id_rsa','id_ed25519'}:
            findings.append({'file':rel,'reason':'Файл, обычно содержащий учётные данные'})
        try:text=path.read_text(encoding='utf-8')
        except UnicodeError:continue
        for n,line in enumerate(text.splitlines(),1):
            if any(rx.search(line) for rx in PATTERNS):findings.append({'file':rel,'line':n,'reason':'Совпадение сигнатуры; значение скрыто'})
    return findings

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--git-history',action='store_true');ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args()
    findings=scan(args.root)
    if findings:print(json.dumps(findings,ensure_ascii=False,indent=2));return 1
    if args.git_history:
        tool=shutil.which('gitleaks')
        if not tool or not (args.root/'.git').exists():print('BLOCKED: нужны история Git и установленный Gitleaks');return 2
        return subprocess.run([tool,'git','--redact','--no-banner',str(args.root)],cwd=args.root).returncode
    print('PASS: сигнатуры текущих исходников. История Git, настройки сервиса и все типы секретов этим не проверены.');return 0
if __name__=='__main__':sys.exit(main())
