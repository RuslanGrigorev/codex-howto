# Подсказки: local-mcp

Редактируемая копия создаётся командой `python scripts/verify.py --prepare local-mcp` из корня исходников. Работайте с `mcp_server.py` в `.learning/workspaces/local-mcp`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

stdout занят протоколом; отладочные сообщения направляйте в stderr.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Проверьте initialize, уведомление и запрос по одному; затем чтение нескольких строк stdin.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Ограничьте путь учебным каталогом, учитывая нормализацию. Успех метода класса не равен работающему stdio-процессу.

</details>

## Проверка

```bash
python scripts/verify.py --exercise local-mcp --workspace .learning/workspaces/local-mcp
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
