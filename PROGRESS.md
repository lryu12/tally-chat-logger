# Progress

## Current focus
Phase 2, Step 2: LLM parser, starting with its output schema (what JSON the model must return)

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
- [x] FastAPI /health endpoint that checks the database
- [x] Dockerfile, CI Postgres service
- [x] Deploy

### Phase 2: Chat logging for lifts
- [x] Telegram webhook stores raw messages (secret header, allowlist, idempotent; DECISIONS 009)
- [x] Bot replies "Saved" after storing (DECISIONS 010; confirmed live: reply received, row in Neon)
- [ ] LLM parser with schema validation and confirm buttons
- [x] Lift tables migration (exercises + lift_sets; set_index counts per exercise)
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
- Real Render cold start time (not yet measured; record in DECISIONS 008)
- Neon's policy for inactive free projects (unverified)
- No pg_dump backup yet
- /start and other bot commands land in raw_messages as pending; the parser must skip them

## Log
- 2026-10-21: created this file
- 2026-10-27: webhook stores raw messages and replies "Saved" on Render + Neon
- 2026-10-28: lift tables migration merged and applied to Neon
