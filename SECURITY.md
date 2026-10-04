# Политика безопасности / Security Policy

## Обзор

Безопасность проекта **Codex How-To** имеет первостепенное значение. Этот документ описывает наши практики безопасности и способы сообщения об уязвимостях.

## Поддерживаемые версии

| Версия | Статус |
|---|---|
| Ветка `main` | ✅ Активна |

## Принципы безопасности в материалах курса

1. **Никаких секретов и токенов в коде**:
   - Все примеры и конфигурации используют фиктивные токены или плейсхолдеры.
   - Спецификация напоминает о недопустимости сохранения секретов в `.agents/skills` или `AGENTS.md`.
2. **Изоляция и контроль выполнения**:
   - В курсе (особенно в модулях `03-safety`, `07-mcp` и `09-extensions`) подробно описаны механизмы ограничения прав `--ask`, песочницы `--sandbox` и проверка доверия к плагинам.
3. **100% Офлайн**:
   - Никакие примеры или тесты не отправляют данные во внешние облачные сервисы.

## Как сообщить об уязвимости

Если вы обнаружили уязвимость безопасности в репозитории:

1. Перейдите в раздел безопасности репозитория:
   **[https://github.com/RuslanGrigorev/codex-howto/security/advisories](https://github.com/RuslanGrigorev/codex-howto/security/advisories)**
2. Нажмите **"Report a vulnerability"**.
3. Опишите сценарий воспроизведения, потенциальное влияние и предложите решение.

---

## English Summary

- Report security vulnerabilities privately via [GitHub Security Advisories](https://github.com/RuslanGrigorev/codex-howto/security/advisories).
- The project practices 100% offline isolation; never commit secrets or tokens.
