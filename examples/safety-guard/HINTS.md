# Подсказки: safety-guard

Редактируемая копия создаётся командой `python scripts/verify.py --prepare safety-guard` из корня исходников. Работайте с `guard.py` в `.learning/workspaces/safety-guard`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Строковый startswith не устанавливает принадлежность пути каталогу.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Учитывайте нормализацию и компоненты пути. Пути Windows нельзя считать POSIX-путями без явного разбора.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Проверка пути — часть приложения, не изоляция произвольного кода на уровне ОС.

</details>

## Проверка

```bash
python scripts/verify.py --exercise safety-guard --workspace .learning/workspaces/safety-guard
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
