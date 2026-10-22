# Progress

## Current focus
Phase 1, Step 4: idempotent insert_run

## Phases
### Phase 0: Setup
- [x] Repo, .gitignore, .env.example, README
- [x] uv project, pytest, ruff
- [x] Docker Compose with Postgres
- [x] CI workflow green
- [x] DECISIONS.md started

### Phase 1: Data foundation
- [x] Branch: phase-1-schema
- [x] Tooling decided: Alembic + psycopg 3
- [x] Migration 0001: users, raw_messages, activities, runs
- [x] insert_run (idempotent, one transaction)
- [x] Tests: duplicate insert, bad data rejected, rollback on failure
- [ ] FastAPI /health endpoint that checks the database
- [ ] Dockerfile, CI Postgres service
- [ ] Deploy

### Phase 2: Chat logging for lifts
- [ ] Telegram bot stores raw messages
- [ ] LLM parser with schema validation and confirm buttons
- [ ] Lift tables migration
- [ ] Eval set (30-50 messages) and accuracy number

### Phase 3: Backfill from notes
### Phase 4: Strava ingestion
### Phase 5: LeetCode and spaced repetition
### Phase 6: Analytics and weekly review
### Phase 7: Dashboard and synthetic demo
### Phase 8 (optional): Music x running
### Phase 9: Hardening and README polish
### Phase 10: Brand work (Notion adapter)

## Open questions
(none yet)

## Log
- 2026-10-21: created this file
