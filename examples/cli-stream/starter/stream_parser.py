"""Заготовка парсера событий codex exec --json. Не готовое решение."""
class CodexStreamParser:
    def parse_stream(self, lines, process_exit_code=0):
        # Разберите отдельные JSONL-события, терминальное состояние и код процесса.
        # Пустой поток, turn.failed и повреждённый JSON не могут дать успех.
        raise NotImplementedError('Сначала изучите test.py и нативные события')
