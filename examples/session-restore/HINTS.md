# Подсказки: session-restore

Редактируемая копия создаётся командой `python scripts/verify.py --prepare session-restore` из корня исходников. Работайте с `session_manager.py` в `.learning/workspaces/session-restore`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Храните историю отдельно от идентификатора выбранной записи.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Сопоставьте поведение с точными ожиданиями независимого test.py. Не добавляйте произвольное восстановление файлов.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Самодельный класс нужен только для автономной практики Python. Реальное продолжение выполняется через codex resume.

</details>

## Проверка

```bash
python scripts/verify.py --exercise session-restore --workspace .learning/workspaces/session-restore
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
