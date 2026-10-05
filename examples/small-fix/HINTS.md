# Подсказки: small-fix

Редактируемая копия создаётся командой `python scripts/verify.py --prepare small-fix` из корня исходников. Работайте с `discount.py` в `.learning/workspaces/small-fix`, а не с эталоном.

<details><summary>Подсказка 1 — с чего начать</summary>

Скидка задана долей, а не процентом: 0.2 означает 20%.

</details>

<details><summary>Подсказка 2 — что проверить</summary>

Сначала проверьте 0 ≤ discount ≤ 1. Вне диапазона нужен ValueError.

</details>

<details><summary>Подсказка 3 — границы результата</summary>

Для допустимого входа сохраните price * (1 - discount); границы 0 и 1 включены.

</details>

## Проверка

```bash
python scripts/verify.py --exercise small-fix --workspace .learning/workspaces/small-fix
```

Не редактируйте независимый [тест](test.py), чтобы получить зачёт. [Исходные файлы](starter/) и [эталонное решение](solution/) доступны локально. Перед просмотром эталона запишите свою попытку и причину ошибки. Автономный Python-тест не подтверждает работу клиента Codex.
