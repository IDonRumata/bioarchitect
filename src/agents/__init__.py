"""AI-агенты на базе Anthropic Claude (Haiku 4.5 + Sonnet 4.6).

Все агенты используют один общий клиент ``src.agents.client.ClaudeClient`` с
включённым Prompt Caching. Промпты — в ``src/agents/prompts/*.md``,
версионируются в git.

Список агентов:
    - orchestrator      — классификация ввода (текст/фото/команда)
    - vision_phase1     — распознавание продуктов на фото
    - vision_phase2     — весовая оценка
    - ocr_lab           — извлечение значений из бланка анализов
    - rag               — образовательные ответы из базы (Censor)
    - coach             — мотивация, weekly summary (Censor)
    - censor            — финальный фильтр (нерушим)
"""
