"""Разбор codex exec --json. Код процесса передаётся отдельно от JSONL."""
from __future__ import annotations
import json
from typing import Iterable

class CodexStreamParser:
    def parse_stream(self, lines: Iterable[str], process_exit_code: int = 0) -> dict:
        errors, texts, warnings=[],[],[]
        count=0; started=False; terminal=None; seen=set()
        known={'thread.started','turn.started','turn.completed','turn.failed','error',
               'item.started','item.updated','item.completed'}
        for line in lines:
            if not line.strip(): continue
            count+=1
            try:
                event=json.loads(line)
                if not isinstance(event,dict) or not isinstance(event.get('type'),str):
                    raise ValueError('ожидался объект события с type')
            except (json.JSONDecodeError,ValueError) as exc:
                errors.append('Невалидный JSONL: '+str(exc));continue
            kind=event['type']
            if terminal is not None:
                errors.append('Событие после завершения turn');continue
            if kind=='turn.started':
                if started: errors.append('Повтор turn.started')
                started=True
            elif kind=='error': errors.append(str(event.get('message','Ошибка Codex')))
            elif kind=='turn.failed':
                terminal='failed';errors.append(str(event.get('error',{}).get('message','turn.failed')) if isinstance(event.get('error',{}),dict) else 'turn.failed')
            elif kind=='turn.completed':
                if not started: errors.append('Нет turn.started')
                terminal='completed'
            elif kind=='item.completed':
                item=event.get('item')
                if not isinstance(item,dict): errors.append('Неверный item');continue
                if item.get('type')=='agent_message':
                    if not isinstance(item.get('text'),str): errors.append('Нет текста agent_message');continue
                    key=item.get('id')
                    if key is not None and key in seen: errors.append('Повтор завершённого item');continue
                    if key is not None: seen.add(key)
                    texts.append(item['text'])
            elif kind not in known:
                warnings.append('Неизвестный тип события: '+kind)
        if not started: errors.append('Поток не содержит начала turn')
        if terminal!='completed': errors.append('Нет успешного turn.completed: поток пуст, оборван или завершился ошибкой')
        if process_exit_code!=0: errors.append('Ненулевой код процесса: '+str(process_exit_code))
        return {'success':not errors,'exit_code':process_exit_code,'output_text':'\n'.join(texts),
                'events_count':count,'errors':errors,'warnings':warnings}
