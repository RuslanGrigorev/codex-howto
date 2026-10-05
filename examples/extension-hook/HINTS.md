# Подсказки: extension-hook

Редактируемая копия создаётся командой `python scripts/verify.py --prepare extension-hook` из корня исходников. Работайте с `hook_runner.py` в `.learning/workspaces/extension-hook`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Различайте hook_event_name входа и hookEventName внутри hookSpecificOutput результата.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Разрешайте только учебную безопасную команду. Дополнительный shell-оператор должен изменить решение.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Проверяйте и функцию, и исполняемый процесс со stdin/stdout; неверный JSON должен завершаться ошибкой.

</details>

## Проверка

```bash
python scripts/verify.py --exercise extension-hook --workspace .learning/workspaces/extension-hook
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
