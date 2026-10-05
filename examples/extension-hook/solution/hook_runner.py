"""Учебный PreToolUse: ограниченный список команд, без их выполнения.
Это демонстрация контракта hooks, не универсальная граница безопасности.
"""
import json,sys
ALLOWED={'git status --short','git diff --stat'}

def evaluate(event):
    if not isinstance(event,dict) or event.get('hook_event_name')!='PreToolUse':
        raise ValueError('Ожидалось событие PreToolUse')
    tool=event.get('tool_name');args=event.get('tool_input')
    command=args.get('command') if isinstance(args,dict) else None
    allow=tool=='Bash' and isinstance(command,str) and command in ALLOWED
    if allow:return {} # Не повышает разрешения Codex.
    return {'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny',
             'permissionDecisionReason':'Учебный hook разрешает только два точных запроса чтения Git.'}}

def main():
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('Слишком большой ввод')
        print(json.dumps(evaluate(json.loads(raw)),ensure_ascii=False))
        return 0
    except (ValueError,UnicodeError) as exc:
        print('Учебный hook: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
