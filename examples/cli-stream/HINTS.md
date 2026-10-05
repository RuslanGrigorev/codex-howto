# Подсказки: cli-stream

Редактируемая копия создаётся командой `python scripts/verify.py --prepare cli-stream` из корня исходников. Работайте с `stream_parser.py` в `.learning/workspaces/cli-stream`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

JSONL — последовательность событий, не один итоговый объект.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Нужны и успешное завершение turn, и подходящий код процесса. Пустой и оборванный поток не успешны.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Обработайте turn.failed, error и плохой JSON. Для неизвестного будущего события сохраните предупреждение, а не выдуманный текст.

</details>

## Проверка

```bash
python scripts/verify.py --exercise cli-stream --workspace .learning/workspaces/cli-stream
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
