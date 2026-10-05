"""Один Markdown-рендерер для сборщика и проверок; никаких загрузок из сети."""
from markdown_it import MarkdownIt

def markdown(text: str, **_compat) -> str:
    return MarkdownIt('commonmark', {'html': True, 'linkify': False}).enable('table').render(text)
