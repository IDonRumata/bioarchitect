-- BioArchitect — инициализация БД (выполняется при первом запуске postgres-контейнера)
-- Идемпотентно: безопасно повторно применять.

CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fuzzy search для food_items
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- шифрование чувствительных полей
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector для RAG embeddings
CREATE EXTENSION IF NOT EXISTS unaccent;      -- поиск без диакритики (PL/DE)
CREATE EXTENSION IF NOT EXISTS btree_gin;     -- индексы для составных запросов

-- pg_partman устанавливается отдельно (требует suparuser-расширения).
-- В dev-среде не используется; в продакшне ставится скриптом infra/postgres/install_partman.sh
