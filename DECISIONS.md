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
