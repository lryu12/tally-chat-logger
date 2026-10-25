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

## 007: Sync route handlers (`def`) over async
Date: 2026-10-21
**Context:** FastAPI runs `async def` routes on the event loop and plain `def` routes in a threadpool. My database layer (`connect()`, `insert_run`, the test fixtures) is synchronous psycopg.
**Decision:** Plain `def` route handlers with sync psycopg.
**Alternatives considered:** `async def` routes with psycopg's `AsyncConnection` (far higher concurrency ceiling, but it means rewriting the db layer and fixtures, and one blocking call inside an `async def` freezes every request).
**Why:** The existing code is sync, and FastAPI contains blocking calls in worker threads (about 40 by default), which is well above the load of a personal logger with a handful of users. Blocking is hard to get wrong this way.
**Tradeoffs:** The ceiling is about 40 simultaneous requests, and each request waiting on the database or an external API holds a thread. Moving to async later means changing the db layer and tests together.
**Revisit when:** the app grows past what the threadpool can handle, or I need to call external APIs (Telegram, Strava, the LLM) in parallel within one request.

## 008: Free hosting: Render for the app, Neon for Postgres
Date: 2026-10-24
**Context:** I need to deploy the app (Telegram webhook plus FastAPI) and a Postgres database for $0. My priorities, from most to least important: stay free, then the bot answering instantly, then data never disappearing.
**Decision:** Run the Docker image on Render's free web service in Ohio, with Neon's free Postgres in AWS US East 2 (Ohio). Run `alembic upgrade head` manually from my machine against Neon before each deploy, and keep the container's `CMD` limited to starting uvicorn.
**Alternatives considered:** Render Postgres (a third-party source says free databases expire after 30 days; unverified), Supabase (a third-party source says free projects pause after 7 idle days; unverified), Fly.io and Railway (roughly $5/month, so not free), migrations in the container's startup command (a failed migration would crash the app, and with no SSH it is hard to debug).
**Why:** Neon's free plan (from their signup page) gives 1 GB, scales to zero, and has 10 branches, which fits this data size. Putting the database on a separate host avoids tying its lifetime to a free app host. Both are in Ohio, so queries stay low-latency. Render's free tier (from their page) has no one-off jobs, so there is no place to run a separate migrate step there. Manual migrations keep schema changes a deliberate step.
**Tradeoffs:** The free app spins down when idle, so the first message after a quiet period is slow (0.1 CPU, 512 MB RAM). Telegram retries failed webhooks, and `UNIQUE (channel, external_id)` on `raw_messages` makes redelivery safe. No SSH or persistent disk, so logs in the Render dashboard are the only window in. Free-tier retention is not guaranteed, and I have not verified Neon's policy for inactive projects, so I need my own `pg_dump` backups. Migrating by hand is a step I can forget.
**Migration order rule:** adding a column or table: migrate first, then deploy. Removing something: deploy first, then migrate. Renaming or changing a type: expand and contract across separate releases. With a single instance and one user I can accept a brief mismatch during a deploy.
**Revisit when:** the data starts to matter more than the cost, cold starts become annoying, I want migrations automated in CI, or I scale beyond one instance (the startup-migration race returns).

## 009: Telegram message identity, edits, and access control
Date: 2026-10-24
**Context:** The webhook stores each incoming message in `raw_messages`, which is unique on `(channel, external_id)`. A Telegram update carries `update_id` (unique per update) and `message.message_id` (unique only within one chat). A Telegram bot is publicly searchable, so anyone can message it or call its webhook URL.
**Decision:** `external_id` is `"{chat_id}:{message_id}"`. Version 1 handles `message` updates only and ignores `edited_message`. The webhook checks the `X-Telegram-Bot-Api-Secret-Token` header against a secret, then checks the sender's Telegram user id against an allowlist from an env var. Failing the secret check returns 401. Failing the allowlist returns 200 and stores nothing.
**Alternatives considered:** `update_id` as the id (an edit would arrive as a new row, so one message could be stored twice), `message_id` alone (collides across chats, and an edit would be silently dropped by `ON CONFLICT DO NOTHING`), handling edits in version 1 (needs a rule for what happens to an activity already confirmed from the original text).
**Why:** The composite id is stable across Telegram's retries, so redelivery is a no-op, and it stays unique if I ever add a second user or a group. Ignoring edits keeps raw storage append-only. Returning 200 to non-allowlisted senders avoids Telegram retrying and avoids telling strangers anything.
**Tradeoffs:** A corrected message is not picked up, so I resend instead of editing. The allowlist and secret are env vars I must set on Render and locally.
**Revisit when:** I find myself editing messages. The likely design is to store each edit as a new `raw_messages` row keyed by `update_id` and re-run the confirm step.

## 010: Replying to Telegram messages
Date: 2026-10-26
**Context:** After the webhook stores a message, the bot should confirm it. Telegram has no reply channel for a webhook, so a reply is either a separate API call or a JSON body returned from the webhook. It is also the first outbound call from the app, and it carries the bot token.
**Decision:** A separate `sendMessage` call using `httpx`, made after the transaction commits and on every delivery, including duplicates. If the call fails, the route returns 502 so Telegram redelivers the update. Error messages and logs never contain the token (the URL contains it).
**Alternatives considered:** Replying inside the webhook response (no extra call and no token in code, but I can't see whether it was delivered or send more than one message, and the confirm flow in 004 will need the separate call anyway), `python-telegram-bot` (brings its own update loop, which overlaps with FastAPI), `BackgroundTasks` (faster response, but failures are silent and it is harder to test), replying only when the row is new (a failed reply would never be retried, because the retry looks like a duplicate), returning 200 on a failed reply (a failure would go unnoticed and nothing would retry it).
**Why:** The stored message is already committed before the reply, so a failed reply loses no data, and a 502 only makes Telegram retry. The `ON CONFLICT` on `raw_messages` makes the retry safe, and replying on every delivery makes the retry useful. `httpx` is already a dependency and a single POST needs no framework. A 5-second timeout stops a hung call from holding a thread and a database connection.
**Tradeoffs:** A rare duplicate "Saved" if the reply succeeds but the response is lost. A permanently broken token (revoked or missing on Render) makes Telegram retry for about a day. Each webhook request now waits on Telegram's API. `httpx` error text includes the URL, so every error from `send_message` is rewrapped with a fixed message and `from None`, and a test checks that the token never appears in the traceback.
**Revisit when:** the LLM parser adds slow work after the acknowledgement (move the work or the reply to a background task or queue), I need buttons or message edits for the confirm step, or duplicate replies become annoying (store a `replied_at` on `raw_messages`).
