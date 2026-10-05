"""Намеренно неправильный вариант: объявляет ошибку успешной."""
class CodexStreamParser:
    def parse_stream(self, lines, process_exit_code=0):
        return {'success':True,'output_text':'','errors':[],'warnings':[],'exit_code':0}
