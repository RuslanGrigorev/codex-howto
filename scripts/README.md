# Инструменты практикума Codex CLI

Сборка сохраняет статическую архитектуру Python/Jinja/Markdown. Требования среды и команды установки находятся в корневом README. Ученику готового ZIP не нужно устанавливать зависимости сборки.

| Команда | Проверяемая область |
| --- | --- |
| `python scripts/check_project.py catalog` | ID, зависимости, файлы уроков, quiz и источники |
| `python scripts/check_project.py exercises` | Эталоны проходят; starter и отрицательные варианты не проходят |
| `python scripts/check_project.py config` | Ограниченный контракт учебных конфигураций, не полная схема Codex |
| `python scripts/check_cross_references.py` | Локальные Markdown-ссылки |
| `python scripts/build_website.py --output .learning/site` | Сайт и локальные учебные файлы без сети |
| `python scripts/browser_check.py --site .learning/site` | Настоящий браузер, file:// и заблокированная внешняя сеть |
| `python scripts/verify.py --profile offline` | Агрегированный локальный прогон |
| `python scripts/verify.py --profile live` | Нативный Codex; модель только при явном согласии |
| `python scripts/package_course.py` | Детерминированный ZIP-кандидат с манифестом |
| `python scripts/verify.py --profile release` | Допуск по полному набору доказательств |
| `python scripts/check_updates.py --help` | Сравнение официальных источников, сеть только по запросу |
| `python scripts/check_publication.py --git-history` | Сигнатуры и отдельный Gitleaks истории |

Сборщик не является универсальным удалятором: корень проекта, чужой непустой каталог и symlink отклоняются. Вывод пишется через staging. Если сборка не удалась, предыдущая остаётся.

Проверки упражнений не являются OS-песочницей. Учебный Python-код запускается на вашей машине с ограниченным набором переменных окружения. Результаты хранятся в .learning, не коммитятся и не подменяют независимую ручную приёмку.

[Правила валидации](../reference/validation.md) содержат условия каждого профиля и ограничения доказательств.
