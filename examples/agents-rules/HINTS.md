# Подсказки: agents-rules

Редактируемая копия создаётся командой `python scripts/verify.py --prepare agents-rules` из корня исходников. Работайте с `validator.py` в `.learning/workspaces/agents-rules`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Нужны две независимые проверки: обязательные разделы и запрещённые данные.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Не принимайте текст с похожим ключом или абсолютным пользовательским путём только потому, что есть заголовок.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Это учебная эвристика, не полноценный поиск секретов и не парсер всех инструкций Codex.

</details>

## Проверка

```bash
python scripts/verify.py --exercise agents-rules --workspace .learning/workspaces/agents-rules
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
