## 001: Database choice
Date: 2026-10-19
**Context:** I need relational storage for activities, constraints to prevent duplicates, and room for raw JSON payloads.
**Decision:** Postgres.
**Alternatives considered:** SQLite (simpler, but weaker for a deployed multi-connection service), MongoDB (flexible documents, but my analytics are aggregations, joins, and window functions which are natural in SQL).
**Why:** JSONB handles varying payloads, and unique constraints make idempotency possible (e.g. raw payloads from Strava events and parser output).
**Tradeoffs:** More setup than SQLite, and I need Docker for local development, tiny bit of network latency.

## 002: Table organization
Date: 2026-10-19
**Context:** How to organize the data for new potential event types.
**Decision:** A shared activities table plus typed detail tables (runs, lift_sets, and so on).
**Alternatives considered:** Generic events table, separate typed tables with no sharedd (no single place for idempotency, and timeline needs a UNION).
**Why:** Few and stable activity types (runs, lifts, leetcode solves with clear shapes), efficient analytics (typed tables make pace trends, volume per exercise simple and database reject bad data).
**Tradeoffs:** A new activity type means new detail table, where generic desin needed is none.
***Revisit when:*** different activities get added.

## 003: Telegram as the chat interface
Date: 2026-10-19
**Context:** I need a low-friction way to log from my phone.
**Decision:** Telegram.
**Alternatives considered:** My own web chat UI (repetitive work, not much learning opportunities), DiscordAPI (To read ordinary messages like "ran 5k, 27:40", has to hold an always-on Gateway WebSocket connection).
**Why:** No long-lived connection to manage and webhooks fit a plain FastAPI endpoint, and mobile app and notifications come for free.
**Tradeoffs:** Messages aren't end-to-end encrypted and pass through Telegram's servers, which is unfavorable for personal data. 


## 004: Parse with an LLM and confirm before saving
Date 2026-10-19
**Context:** I need a way to insert data entries from user input.
**Decisions:** Parse with LLM and confirm before entry.
**Alternatives considered:** Fixed command forms (deterministic but defeats purpose of innovative way of logging), Regex rule-based parsing (rules will keep growing as application expands).
**Why:** Easy to forget or get lazy about logging, so make it conversational.
**Tradeoffs:** Cost per message, latency, API dependence, non-deterministic output.

## 005: Database migration tool
Date: 2026-10-19
**Context:** I need versioned, reproducible schema changes that apply the same way on my laptop, in CI, and on the deployed database.
**Decision:** Alembic, with migrations written as hand-written SQL (`op.execute`). No ORM models or autogenerate.
**Alternatives considered:** Jetbase (plain SQL-file migrations with locking and checksums, but newer and with a smaller community), SQLAlchemy `create_all` (no history, and it can't safely alter existing tables), plain `.sql` files with my own runner (simple, but I'd build version tracking, ordering, and rollback myself).
**Why:** Widely used in Python, so it's familiar to teams. It gives me a revision history with upgrade/downgrade, and it works with raw SQL, so I practice SQL directly.
**Tradeoffs:** It pulls in SQLAlchemy just for migrations, needs some config (`env.py`, driver URL prefix), and I write both upgrade and downgrade by hand. Downgrades can't restore dropped data.
**Revisit when:** I adopt SQLAlchemy models (autogenerate becomes useful), or the config overhead outweighs the benefits.

## 006: Database access layer
Date: 2026-10-19
**Context:** The app needs to read and write Postgres, including a transactional insert across `activities` and `runs` with idempotency via `ON CONFLICT`.
**Decision:** psycopg 3 with hand-written SQL. No ORM for now.
**Alternatives considered:** SQLAlchemy ORM (less SQL to write, but more abstraction between me and the queries I want to learn), SQLAlchemy Core (a middle ground), asyncpg (async-only and Postgres-specific, with a different API), psycopg2 (the older generation; psycopg 3 is its actively developed successor).
**Why:** The SQL is visible and easy to test and explain. psycopg 3 supports parameterized queries, explicit transactions, row factories (`dict_row`, `class_row`), JSONB handling, and pooling (`psycopg_pool`). It supports sync and async, so I can switch later, and it's the same driver Alembic uses through `postgresql+psycopg`.
**Tradeoffs:** SQL lives in strings, so mistakes appear at runtime, not at lint time. I map rows to objects myself, and boilerplate grows with the number of queries. I must always use parameter placeholders and never build SQL with f-strings (SQL injection). Pool and transaction handling is my job.
**Revisit when:** repetitive CRUD code piles up, at which point SQLAlchemy Core could cut boilerplate.
