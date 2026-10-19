# Tally

A conversational logger for self-improvement: text the bot what you did
("ran 5k, 27:40", "bench 3x5 @185"), and it turns that into structured data
and weekly insights.

**Status:** in development. Currently: project setup, local Postgres, and CI.
Next: database schema and chat logging.

## Planned features
- Natural-language logging for lifts, runs, and LeetCode solves via Telegram
- Strava ingestion
- Weekly review and progress analytics

## Tech stack
Python, FastAPI, Postgres, Docker Compose, GitHub Actions

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/) and Docker.

```bash
uv sync
cp .env.example .env     # then edit .env with your own values
docker compose up -d     # starts Postgres
uv run pytest
```

## Design decisions
See [DECISIONS.md](DECISIONS.md) for why I chose Postgres, a shared
`activities` table with typed detail tables, Telegram, and LLM parsing
with confirmation.