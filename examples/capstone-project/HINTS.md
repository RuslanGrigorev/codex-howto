# Подсказки: capstone-project

Редактируемая копия создаётся командой `python scripts/verify.py --prepare capstone-project` из корня исходников. Работайте с `processor.py` в `.learning/workspaces/capstone-project`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Сначала установите контракт одной записи, затем считайте агрегаты.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Обработайте пустой список отдельно. Счёт относится к диапазону 0–100, а pass_rate к 0–1.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Сортировка при равных результатах должна быть воспроизводимой. Проверьте точные ожидания в независимом test.py.

</details>

## Проверка

```bash
python scripts/verify.py --exercise capstone-project --workspace .learning/workspaces/capstone-project
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
