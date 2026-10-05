# Подсказки: custom-skill

Редактируемая копия создаётся командой `python scripts/verify.py --prepare custom-skill` из корня исходников. Работайте с `validator.py` в `.learning/workspaces/custom-skill`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Отделите чтение SKILL.md от проверки полей name и description.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Проверьте отсутствующий файл, неправильное имя и потенциально опасные данные.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Локальный валидатор не доказывает, что Codex обнаружил навык: для этого нужен отдельный нативный вызов.

</details>

## Проверка

```bash
python scripts/verify.py --exercise custom-skill --workspace .learning/workspaces/custom-skill
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
