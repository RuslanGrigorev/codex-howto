"""Нативный формат событий; отрицательные примеры обязательны."""
import json,os,sys,unittest
sys.path.insert(0,os.getcwd())
from stream_parser import CodexStreamParser
class Tests(unittest.TestCase):
    def parse(self,*events,code=0):
        return CodexStreamParser().parse_stream([json.dumps(e) for e in events],process_exit_code=code)
    def test_message(self):
        r=self.parse({'type':'thread.started','thread_id':'demo'},{'type':'turn.started'},
             {'type':'item.completed','item':{'id':'1','type':'agent_message','text':'Готово'}},
             {'type':'turn.completed','usage':{}})
        self.assertTrue(r['success']);self.assertEqual(r['output_text'],'Готово')
    def test_failed(self):
        self.assertFalse(self.parse({'type':'turn.started'},{'type':'turn.failed','error':{'message':'Сбой'}})['success'])
    def test_error_with_completed(self):
        self.assertFalse(self.parse({'type':'turn.started'},{'type':'error','message':'Ошибка'},{'type':'turn.completed'})['success'])
    def test_empty(self): self.assertFalse(self.parse()['success'])
    def test_truncated(self): self.assertFalse(self.parse({'type':'turn.started'})['success'])
    def test_bad_json(self): self.assertFalse(CodexStreamParser().parse_stream(['{'])['success'])
    def test_not_object(self): self.assertFalse(CodexStreamParser().parse_stream(['[]'])['success'])
    def test_exit(self): self.assertFalse(self.parse({'type':'turn.started'},{'type':'turn.completed'},code=7)['success'])
    def test_missing_start(self): self.assertFalse(self.parse({'type':'turn.completed'})['success'])
    def test_future_event(self):
        r=self.parse({'type':'turn.started'},{'type':'future.event'},{'type':'turn.completed'})
        self.assertTrue(r['success']);self.assertTrue(r['warnings'])
    def test_duplicate(self): self.assertFalse(self.parse({'type':'turn.started'},{'type':'turn.completed'},{'type':'turn.completed'})['success'])
if __name__=='__main__':unittest.main()
