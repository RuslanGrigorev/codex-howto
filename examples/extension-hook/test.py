import os,sys,unittest,json,subprocess
sys.path.insert(0,os.getcwd())
import hook_runner
class Tests(unittest.TestCase):
    def event(self,command):return {'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':command}}
    def test_allow(self):self.assertEqual(hook_runner.evaluate(self.event('git status --short')), {})
    def test_denial(self):
        for command in ['git push','git status --short; echo changed','python -c "print(1)"','']:
            r=hook_runner.evaluate(self.event(command))['hookSpecificOutput']
            self.assertEqual(r['hookEventName'],'PreToolUse');self.assertEqual(r['permissionDecision'],'deny')
    def test_apply_patch(self):
        r=hook_runner.evaluate({'hook_event_name':'PreToolUse','tool_name':'apply_patch','tool_input':{'command':'*** Begin Patch'}})
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'deny')
    def test_wrong_event(self):
        with self.assertRaises(ValueError):hook_runner.evaluate({'hook_event_name':'Unknown'})
    def test_process(self):
        p=subprocess.run([sys.executable,'-S',hook_runner.__file__],input=json.dumps(self.event('git push')),text=True,capture_output=True,timeout=4)
        self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'],'deny')
    def test_invalid_json(self):
        p=subprocess.run([sys.executable,'-S',hook_runner.__file__],input='{',text=True,capture_output=True,timeout=4)
        self.assertEqual(p.returncode,2)
if __name__=='__main__':unittest.main()
