"""Намеренная ошибка: JSONL разобран как один JSON-документ."""
import json
class CodexStreamParser:
    def parse_stream(self, lines, process_exit_code=0):
        data=json.loads(''.join(lines))
        return {'success':True,'output_text':str(data),'errors':[],'warnings':[],'exit_code':process_exit_code}
