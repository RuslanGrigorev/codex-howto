"""Минимальный MCP stdio для доверенного учебного каталога.
JSON-RPC через отдельные строки. Журналы только в stderr. Не для враждебных файлов.
Спецификация транспорта: modelcontextprotocol.io/specification/2025-11-25/basic/transports
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path,PureWindowsPath
MAX_LINE=1024*1024
SUPPORTED=('2025-11-25','2025-06-18','2025-03-26','2024-11-05')
class LocalMcpHandler:
    def __init__(self,workspace_root):
        self.workspace_root=Path(workspace_root).resolve()
        self.initialized=False
    def handle_request(self,req):
        rid=req.get('id') if isinstance(req,dict) else None
        def error(code,message):return {'jsonrpc':'2.0','id':rid,'error':{'code':code,'message':message}}
        def result(value):return {'jsonrpc':'2.0','id':rid,'result':value}
        if not isinstance(req,dict) or req.get('jsonrpc')!='2.0' or not isinstance(req.get('method'),str):
            return error(-32600,'Некорректный JSON-RPC запрос')
        method=req['method'];params=req.get('params',{})
        if not isinstance(params,dict):return None if 'id' not in req else error(-32602,'params должен быть объектом')
        if 'id' not in req:
            if method=='notifications/initialized':self.initialized=True
            return None
        if method=='initialize':
            version=params.get('protocolVersion')
            return result({'protocolVersion':version if version in SUPPORTED else SUPPORTED[0],
                           'serverInfo':{'name':'course-local-files','version':'1.0.0'},
                           'capabilities':{'tools':{'listChanged':False}}})
        if method=='ping':return result({})
        if method=='tools/list':
            return result({'tools':[{'name':'read_file_safe','description':'Прочитать небольшой текст из учебного каталога',
                'inputSchema':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False},
                'annotations':{'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False}}]})
        if method=='tools/call':
            if params.get('name')!='read_file_safe':return error(-32602,'Неизвестный инструмент')
            args=params.get('arguments',{})
            rel=args.get('path') if isinstance(args,dict) else None
            try:
                if not isinstance(rel,str) or not rel or '\x00' in rel or rel.startswith(('~','/','\\')) or '\\' in rel or PureWindowsPath(rel).drive:
                    raise ValueError('Требуется относительный путь')
                raw=self.workspace_root/rel
                # Запрещаем symlink-компоненты. Конкурентную замену файлов другой
                # программой этот учебный сервер не изолирует.
                if raw.is_symlink() or any(p.is_symlink() for p in raw.parents if p!=self.workspace_root):
                    raise ValueError('Символические ссылки запрещены')
                target=raw.resolve()
                if not target.is_relative_to(self.workspace_root) or target==self.workspace_root:raise ValueError('Выход из учебного каталога')
                if not target.is_file():raise ValueError('Обычный файл не найден')
                with target.open('rb') as f: content=f.read(65537)
                if len(content)>65536:raise ValueError('Файл больше 64 КиБ')
                text=content.decode('utf-8')
                return result({'content':[{'type':'text','text':text}],'isError':False})
            except (OSError,ValueError,UnicodeError) as exc:
                return result({'content':[{'type':'text','text':'Чтение отклонено: '+str(exc)}],'isError':True})
        return error(-32601,'Метод не поддерживается')

def main():
    ap=argparse.ArgumentParser(description='Учебный локальный MCP stdio');ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    if not args.root.is_dir():print('Учебный каталог не найден',file=sys.stderr);return 2
    handler=LocalMcpHandler(args.root)
    while True:
        line=sys.stdin.buffer.readline(MAX_LINE+1)
        if not line:break
        if len(line)>MAX_LINE:print('Превышен размер запроса',file=sys.stderr);return 2
        if not line.strip():continue
        try:response=handler.handle_request(json.loads(line))
        except (ValueError,UnicodeError):response={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Некорректный JSON'}}
        if response is not None:print(json.dumps(response,ensure_ascii=False),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
