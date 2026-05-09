# Architecture Decision Records

ADR — короткие документы, фиксирующие архитектурные решения и их обоснования.
Формат — на основе [Michael Nygard's template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

## Зачем

Через 6 месяцев никто не вспомнит, **почему** выбрали Hetzner вместо AWS,
sops вместо Doppler или почему Reference Object Detection заглушен на MVP.
ADR отвечает на эти вопросы и предотвращает повторное обсуждение.

## Когда писать

- Меняешь стек / провайдера → ADR.
- Делаешь нетривиальную развилку (архитектура, безопасность, юридическая) → ADR.
- Откладываешь реализацию фичи на потом с обоснованием → ADR.

## Когда НЕ писать

- Тривиальные решения (имя переменной, форматирование).
- Решения, которые легко откатить.

## Шаблон

```markdown
# ADR-NNNN: <название>

- **Дата:** YYYY-MM-DD
- **Статус:** proposed | accepted | deprecated | superseded by ADR-XXXX
- **Авторы:** Андрей, Claude

## Контекст
Какую задачу решаем, что изменилось, почему понадобилось решение.

## Решение
Что выбрали.

## Альтернативы
Что рассматривали и почему отвергли.

## Последствия
Плюсы, минусы, что становится сложнее.
```

## Список ADR

| № | Название | Статус |
|---|---|---|
| 0001 | Monorepo layout | accepted |
| 0002 | Reference Object Detection отложен на v2.0 | accepted |
| 0003 | Secrets management: sops + age (не Doppler) | accepted |
| 0004 | Recovery Index — clamp компонентов в [0, max] | accepted |
| 0005 | Embedding-модель для RAG | proposed (open) |
