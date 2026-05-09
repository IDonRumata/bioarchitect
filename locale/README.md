# Локализация

BioArchitect поддерживает 4 языка с момента запуска:

| Код | Язык | Аудитория |
|---|---|---|
| `ru` | Русский | Беларусь, РФ, KZ, водители из СНГ в EU |
| `en` | English | Глобальная аудитория |
| `pl` | Polski | Польша (большой % дальнобойщиков EU) |
| `de` | Deutsch | Германия / Австрия (рынок Tank&Rast) |

## Структура

```
locale/
├── messages.pot          # шаблон, генерируется make i18n-extract
├── ru/LC_MESSAGES/
│   ├── messages.po       # ручной перевод
│   └── messages.mo       # компилируется make i18n-compile
├── en/LC_MESSAGES/
├── pl/LC_MESSAGES/
└── de/LC_MESSAGES/
```

## Как добавить новую строку

1. В коде используй `_()`:
   ```python
   from src.core.i18n import _

   await message.answer(_("Привет!"))
   ```

2. Извлеки строки:
   ```bash
   make i18n-extract
   make i18n-update
   ```

3. Открой `locale/<lang>/LC_MESSAGES/messages.po`, добавь перевод.

4. Скомпилируй:
   ```bash
   make i18n-compile
   ```

## Переводчики

- RU: Андрей (носитель).
- EN: Андрей + DeepL Pro для проверки.
- PL: фриланс-переводчик (нанимаем перед спринтом 7).
- DE: фриланс-переводчик.

Каждый язык требует ревью до релиза. До спринта 6 — только RU + EN
(машинный перевод DeepL для PL/DE как заглушка).
