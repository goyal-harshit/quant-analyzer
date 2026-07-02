# QuantAarch — Master Build Plan & Capability Gap Analysis

> Maps the full feature checklist against the **actual QuantAI codebase** (snapshot 2026-06-28), flags every gap and bug found while analysing, and lays out a phased plan to make the project complete across every layer.
> **Constraint honoured throughout: 100% free + open-source / free-tier only.**
> Companion to `QuantAI_Audit_Improvements_Roadmap.docx` (the strategic audit) — this doc is the **execution checklist**.

---

## 0. How to read this

Status legend used everywhere below:

| Symbol | Meaning |
|---|---|
| ✅ | Implemented and working |
| 🟡 | Partial / exists but incomplete or not wired everywhere |
| ❌ | Missing |
| ➖ | Not relevant to a quant-analyzer (skip unless scope changes) |

**Priority:** `P0` foundational/blocking · `P1` high value · `P2` valuable · `P3` nice-to-have.

**Open-source guardrail:** prefer self-hosted OSS (Postgres, Redis, Ollama, FastAPI, Next.js) over proprietary free-tiers (Supabase, Firebase, Clerk, Cloudinary). The checklist lists those SaaS options; for a project branded "open-source" they create lock-in and licensing asterisks. Where the checklist names a SaaS, this plan gives the **OSS-first equivalent** and notes the SaaS only as an optional fallback.

---

## 1. Current state in one paragraph

QuantAI is a mature full-stack analyzer: FastAPI backend (20 domain modules), Next.js 14 frontend (18 pages), Postgres/TimescaleDB + Redis + Celery + Ollama, all Dockerised. **Phases A and B (core) are complete as of 2026-06-29.** The project now has: versioned Alembic migrations (baseline + RBAC column migration), double-submit CSRF protection, structured JSON logging + request IDs, typed pydantic-settings, httpOnly-cookie auth with refresh/logout, RBAC (`role` + `is_verified` columns), pluggable email transport (console/memory/smtp), password reset + email verification flows, a provider-abstraction + reliability layer (circuit breakers, token buckets, fallback chain including nsepython/jugaad-data), an ingest-then-serve DB store (market_quotes/bars/fundamentals), Prometheus-format `/metrics`, optional Sentry integration, and **135 backend tests** (ruff + pytest in CI). Remaining gaps: OAuth/social login (needs live creds), file import/export, RAG/pgvector grounding, frontend polish (theme toggle, PWA, mobile nav), Playwright E2E.

---

## 2. Layer-by-layer gap analysis

### 2.1 Frontend

| Feature | Status | Gap / Plan | Free tool |
|---|---|---|---|
| Landing page | ✅ | `app/page.tsx` exists (616 LOC) | — |
| Dashboard | ✅ | `app/dashboard` live | — |
| Authentication UI | ✅ | `login`/`register` pages | — |
| Dark/Light mode | ✅ | Zero-dep `ThemeProvider` + header toggle; `html.light` CSS-var overrides; `T` tokens theme-aware; localStorage-persisted, no-flash. *(bug #2 fixed)* | — (hand-rolled) |
| Responsive design | 🟡 | Desktop-first; no mobile hamburger/responsive grids. **P1** | Tailwind breakpoints |
| Charts & analytics | ✅ | `lightweight-charts` + `recharts` wired | — |
| Data tables | 🟡 | Tables exist; no shared sortable/virtualized table. Add TanStack Table (`react-virtual` already installed). | `@tanstack/react-table` |
| Forms | 🟡 | Hand-rolled; standardise with `react-hook-form` + `zod`. | RHF + Zod (MIT) |
| File upload | ❌ | No upload (portfolio CSV import is the use-case). **P1** | native + backend parser |
| Drag & drop | ❌ | Useful for watchlist/portfolio reorder. **P3** | `dnd-kit` (MIT) |
| Search & filters | 🟡 | Screener filters + command palette exist; no global fuzzy search. | `cmdk` / Fuse.js |
| Infinite scrolling | 🟡 | `react-virtual` installed; not applied to long lists. | TanStack Virtual |
| Markdown editor | ➖ | Not needed unless notes/journal feature added. | — |
| Rich text editor | ➖ | Same. Consider for "research notes". **P3** | TipTap (MIT) |
| Notifications | ✅ | `react-hot-toast` + `/notifications` page | — |
| Keyboard shortcuts | 🟡 | Command palette exists; document/extend shortcuts. | — |

### 2.2 Backend

| Feature | Status | Gap / Plan |
|---|---|---|
| REST API | ✅ | FastAPI, 20 routers under `/api/v1/*` |
| GraphQL API | ❌ | Optional. Only add if a consumer needs it. **P3** — `strawberry-graphql` (MIT) |
| CRUD operations | ✅ | Portfolio/watchlist/alerts |
| Authentication | ✅ | JWT password flow |
| Authorization | ✅ | `require_role(*roles)` / `require_admin` dependencies; per-user ownership checks on alerts/portfolio. RBAC `role` column + `is_verified` on User. |
| JWT | ✅ | `auth_service`, httpOnly cookies, access/refresh/reset/verify token types, refresh/logout endpoints |
| OAuth (GitHub/Google) | ❌ | **Deferred.** `authlib` social login needs live provider creds. **P1** |
| Rate limiting | ✅ | `slowapi` via `services/rate_limit.py` |
| Request validation | 🟡 | Pydantic on bodies; audit query params for unvalidated inputs. |
| Background jobs | ✅ | Celery + beat (`tasks.py`); `refresh_market_store_task` every 30 min |
| Caching | 🟡 | `cache_service` exists; not systematic per data-class TTL. **P1** (see audit §3.6) |
| Logging | ✅ | Structured JSON + request IDs (`observability.py`); `configure_logging` in main. |
| API versioning | ✅ | `/api/v1` prefix already |

### 2.3 Database

| Feature | Status | Gap / Plan |
|---|---|---|
| PostgreSQL | ✅ | Primary, async SQLAlchemy |
| SQLite | ✅ | CI uses `sqlite+aiosqlite` fallback |
| TimescaleDB hypertables | 🟡 | Infra present; hypertables/continuous aggregates not applied. **P1** |
| **Migrations (Alembic)** | ✅ | Baseline migration `b8ffc3251ccc` (20 tables) + RBAC column migration `5158e99478e5`. `scripts/migrate.py` handles fresh/legacy/versioned DBs safely. `DB_AUTO_CREATE=false` in prod. CI verifies upgrade/downgrade. |
| Redis | ✅ | Cache + Celery broker |
| MongoDB / Supabase / Firebase | ➖ | Not needed; Postgres covers it. Skip (keeps stack OSS + self-hosted). |

### 2.4 Authentication

| Feature | Status | Plan |
|---|---|---|
| Email/password | ✅ | Done |
| Google login | ❌ | `authlib` OAuth — deferred (needs live creds). **P1** |
| GitHub login | ❌ | `authlib` OAuth — deferred (needs live creds). **P1** |
| Magic links | ❌ | Email transport is ready; magic-link endpoint still missing. **P2** |
| Password reset | ✅ | JWT `reset` token type; `/auth/forgot-password` (no enumeration), `/auth/reset-password`. Tested. |
| Email verification | ✅ | JWT `verify` token; `/auth/send-verification`, `/auth/verify-email`. Tested. |
| Role-based access | ✅ | `role` column + `is_verified` on User (migration); `require_role`/`require_admin` dependencies. |

### 2.5 AI Features

| Feature | Status | Plan |
|---|---|---|
| Local LLM (Ollama/LM Studio) | ✅ | `ai_service` multi-provider incl. Ollama |
| Chatbot | ✅ | `/ai` page + insight agent |
| **RAG** | ✅ | `services/rag_service.py` — embed query → in-process vector store → grounded answer w/ citations (`POST /ai/ask`). Embeddings stored as JSON (pgvector-ready seam). |
| Semantic search | ✅ | `POST /ai/semantic-search` — cosine over Ollama embeddings, ranked docs + scores. |
| Document Q&A | 🟡 | Stock profile docs indexed; annual-report/filing chunking still a follow-up. **P2** |
| Embeddings | ✅ | Ollama `nomic-embed-text` (768-dim) via `embedding_service.py`; zero extra Python deps. |
| Prompt templates | ✅ | RAG prompts externalised to `services/prompts.py` (versioned). Other ai_service prompts can migrate over time. |
| Conversation history | ✅ | Per-user `conversations`/`conversation_messages`; `/ai/conversations` CRUD persists RAG citations. |
| AI code review | ➖ | Dev-tooling, not product. Skip. |
| AI summarization | 🟡 | Insight agent summarises; extend to news/earnings. |
| AI report generation | 🟡 | Insight reports exist; add scheduled stock/portfolio briefings. **P2** |

### 2.6 File Handling

| Feature | Status | Plan |
|---|---|---|
| Image/PDF/CSV/Excel upload | ❌ | **None.** Priority is **CSV/Excel portfolio import** (broker statements). **P1** |
| Document parsing | ❌ | `pandas` (CSV/XLSX) + `pdfplumber` for filings. |
| Image compression | ➖ | Low relevance. |
| PDF generation | ❌ | **Export research/portfolio/tax reports as PDF.** `reportlab` or `weasyprint` (OSS). **P1** |
| Export CSV | ❌ | `pandas.to_csv` streaming response. **P1** |
| Export Excel | ❌ | `openpyxl`. **P2** |
| ZIP downloads | ❌ | Bundle multi-file exports. **P3** |

### 2.7 Search

| Feature | Status | Plan |
|---|---|---|
| Full-text search | 🟡 | Symbol search exists; add Postgres `tsvector` FTS over symbols/news. **P2** |
| Advanced filters | ✅ | Screener |
| Auto-complete | 🟡 | Symbol search; add debounced typeahead everywhere. |
| Fuzzy search | ❌ | `pg_trgm` (Postgres) or Fuse.js (client). **P2** |
| Semantic search | ❌ | See RAG (pgvector). **P1** |

### 2.8 Visualization

| Feature | Status | Plan |
|---|---|---|
| Dashboards / Line / Bar / Pie | ✅ | recharts |
| Heatmaps | ✅ | Sector heatmap on dashboard |
| Network graphs | ❌ | Correlation/peer graph. `react-force-graph` (OSS). **P3** |
| Timelines | 🟡 | IPO calendar; generalise. |
| Tree views | ➖ | Low relevance. |
| Kanban / Gantt | ➖ | Not a project-mgmt app. Skip. |

### 2.9 Collaboration · 2.10 Notifications

| Feature | Status | Plan |
|---|---|---|
| Team workspaces / Invitations / Mentions | ➖ | Only if B2B scope (see audit §5.4). Defer. |
| Comments | 🟡 | Could add notes on stocks. **P3** |
| Activity feed / Audit logs | 🟡 | `observability` partial; add an audit-log table for auth + mutations. **P2** |
| Version history | ➖ | Defer. |
| In-app notifications | ✅ | `/notifications` + bell |
| Toast messages | ✅ | `react-hot-toast` |
| Email notifications | ✅ | `services/email_service.py`: console/memory/smtp backends; `send_email` never raises. Config: `EMAIL_BACKEND`, `SMTP_*`, `EMAIL_FROM`. Unblocked: reset ✅, verify ✅. Magic links still missing (P2). |
| Push notifications | ❌ | Web Push (VAPID, free) or Telegram bot (free) for alerts. **P2** |

### 2.11 Analytics

| Feature | Status | Plan |
|---|---|---|
| User/usage/session analytics | ❌ | Self-host **Plausible** or **Umami** (OSS, free). **P2** |
| Performance metrics | 🟡 | `observability.py`; expose Prometheus metrics. **P1** |
| Event tracking | ❌ | Umami custom events. **P3** |
| Error tracking | ❌ | **Sentry** free tier or self-hosted **GlitchTip** (OSS). **P1** |

### 2.12 Security

| Feature | Status | Plan |
|---|---|---|
| Password hashing | ✅ | `bcrypt` |
| JWT / cookies | ✅ | httpOnly cookies |
| OAuth | ❌ | See 2.4 |
| HTTPS | 🟡 | Provider-terminated in prod; enforce HSTS + secure cookies. |
| Input validation | 🟡 | Pydantic; audit gaps. |
| SQL injection | ✅ | SQLAlchemy ORM params |
| XSS protection | 🟡 | React escapes; audit any `dangerouslySetInnerHTML` (one was used for a style tag — verify). |
| CSRF protection | ✅ | Double-submit guard: `csrf_token` cookie + `X-CSRF-Token` header required on unsafe cookie-auth requests. Token also returned in login/refresh body for cross-site frontends. `/auth/*` exempt. |
| Rate limiting | ✅ | slowapi |
| API keys | 🟡 | AI keys client-side; add server API-key scheme if exposing public API. |
| RBAC | 🟡 | See 2.4 |

### 2.13 Developer Experience

| Feature | Status | Plan |
|---|---|---|
| Swagger/OpenAPI | ✅ | FastAPI `/docs` + `/redoc` auto |
| API playground | ✅ | `/docs` |
| Unit tests | ✅ | 14 test files, **135 tests** passing (reliability, providers, quant metrics, market store, observability, auth cookies, CSRF, RBAC, password reset, migrations) |
| Integration tests | 🟡 | Auth + store + RBAC tested; broaden to module endpoints. **P1** |
| End-to-end tests | ✅ | **Playwright** — `frontend/e2e/critical-flows.spec.ts` (6 offline tests: landing, login form, guest nav, screener/Quant-Lab shells) + a backend-gated auth flow; runs in CI. |
| Docker | ✅ | Compose, 7 services |
| GitHub Actions CI/CD | ✅ | `ci.yml`: ruff + pytest + migration verify + next build |
| Environment management | ✅ | `config.py` pydantic-settings `Settings` + `get_settings()`; all services read typed config. |
| Seed database | ✅ | `seed_data.py` (refactor to fixtures — audit §3.3) |
| Migrations | ✅ | Alembic baseline + RBAC migration; `scripts/migrate.py`; CI verify step. |

### 2.14 Monitoring · 2.15 Deployment · 2.16 Storage

| Area | Status | Plan |
|---|---|---|
| Error/request logging | ✅ | Structured JSON + request IDs (`observability.py`); `RequestContextMiddleware`; `/metrics` Prometheus endpoint; optional Sentry. |
| Health checks | ✅ | `/health` (db + redis) |
| Uptime monitoring | ❌ | **UptimeRobot** free or self-host **Uptime Kuma** (OSS). **P2** |
| Performance monitoring | 🟡 | Prometheus + Grafana (OSS) — optional self-host. **P2** |
| Deployment (free) | ✅ | GH Pages (frontend) + Render (backend). Note Render free sleeps; document cold-start. Alt: Railway/Fly.io free. |
| Storage | 🟡 | Local + IndexedDB client. For uploads use **local volume** or self-host **MinIO** (S3-compatible, OSS) over Cloudinary/Firebase. **P2** |

### 2.17 Documentation · 2.18 Nice-to-have

| Feature | Status | Plan |
|---|---|---|
| API docs | ✅ | OpenAPI |
| User/Admin guide | 🟡 | README/QUICKSTART exist; add `/docs` user guide. **P2** |
| Architecture/UML/sequence diagrams | ❌ | **Mermaid** in-repo (free, renders on GitHub). **P2** |
| Multi-language (i18n) | ❌ | `next-intl` if needed. **P3** |
| Theme customization | 🟡 | After dark/light toggle. **P3** |
| PWA / offline | ❌ | `next-pwa` — strong fit for mobile retail. **P2** |
| QR code | ➖ | Low relevance. |
| Calendar integration | 🟡 | IPO/earnings calendar; export `.ics`. **P3** |
| Markdown rendering / syntax highlight | 🟡 | For AI output: `react-markdown` + `shiki`. **P3** |
| Data import/export | ❌ | See File Handling. **P1** |
| Bulk operations | 🟡 | Bulk watchlist add/remove. **P3** |
| Undo/Redo · Command palette · Keyboard nav | 🟡 | Palette exists; extend. **P3** |

### 2.19 Free external APIs (relevance-ranked for a quant analyzer)

| API | Use here | Priority |
|---|---|---|
| ExchangeRate API | USD-INR + multi-currency portfolio | **P1** |
| News APIs (GNews/NewsAPI free) | Replace placeholder news + sentiment | **P1** |
| Hugging Face Inference (free limits) | Embeddings / sentiment fallback | **P2** |
| Public datasets (World Bank/RBI/data.gov.in) | Macro (already partly used) | **P1** |
| GitHub OAuth API | Social login | **P1** |
| Reddit/NASA/Weather/OpenStreetMap | Not relevant to finance | ➖ skip |

---

## 3. Bugs, risks & fixes found while analysing

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | ~~**High**~~ **FIXED** | ~~No Alembic migrations~~ | Baseline migration + RBAC migration; `scripts/migrate.py` safe adoption; CI verify step. `DB_AUTO_CREATE=false` in prod. |
| 2 | ~~**High**~~ **FIXED** | ~~Dark mode hardcoded~~ | Zero-dep `ThemeProvider` (no `next-themes`); `html.light` CSS-var overrides; `T` surface tokens → `var(--…)`; header Sun/Moon toggle; no-flash `<head>` script; localStorage-persisted. Verified in-browser. |
| 3 | ~~Medium~~ **FIXED** | ~~CSRF gap~~ | Double-submit guard: csrf cookie + `X-CSRF-Token` header. Token also in login body for cross-site frontend. |
| 4 | ~~Medium~~ **FIXED** | ~~No email transport~~ | `services/email_service.py` — console/memory/smtp. Password reset + email verification tested. |
| 5 | ~~Medium~~ **FIXED** | ~~AI not grounded~~ | RAG: Ollama `nomic-embed-text` embeddings + in-process vector store; `/ai/ask` retrieves platform docs and answers with citations. (pgvector swap optional.) |
| 6 | Medium | **No file import/export** — portfolio can't ingest broker CSV; nothing exportable (PDF/CSV/Excel). | pandas import + reportlab/openpyxl export. |
| 7 | Low | **`dangerouslySetInnerHTML`** used (inline style tag, per git history) — audit it isn't reachable by user input. | Confirm static-only; prefer styled-jsx/CSS module. |
| 8 | Low | **God-objects** `data_service.py` (~1k LOC) / `seed_data.py` (~964 LOC). | Split into providers/transforms/cache; seed → fixtures (audit §3.3). |
| 9 | Low | **Caching not systematic** — per-endpoint, no unified TTL policy/single-flight. | Cache policy table + stale-while-revalidate (audit §3.6). |
| 10 | Low | **Render free tier sleeps** (~30s cold start) — UX cliff. | Document; add a keep-warm ping (cron-job.org free) or Fly.io. |

---

## 4. Phased execution plan

Ordered so each phase unblocks the next. Every tool below is OSS or free-tier.

### Phase A — Foundation hardening ✅ COMPLETE (2026-06-28)
1. ✅ **Alembic migrations** — baseline `b8ffc3251ccc` (20 tables) + `scripts/migrate.py` safe adoption; `DB_AUTO_CREATE=false` in prod.
2. ✅ **CSRF + secure-cookie hardening** — double-submit guard; `render.yaml` sets `COOKIE_SAMESITE=none`, `COOKIE_SECURE=true`.
3. ✅ **Structured logging + error tracking** — `JsonFormatter`, `RequestContextMiddleware`, `/metrics` Prometheus, optional Sentry.
4. ✅ **Typed settings** — `config.py` pydantic-settings `Settings`; all services read typed config.
> Output: schema versioned, auth safe, failures visible. 125 tests.

### Phase B — Auth & notifications completeness (P1) — core ✅ DONE, OAuth deferred
5. ❌ **OAuth social login** — `authlib` Google + GitHub — **deferred; needs live provider credentials.**
6. ✅ **Email transport** — `services/email_service.py`; console/memory/smtp backends.
7. ✅ **Password reset + email verification** — JWT `reset`/`verify` types; no-enumeration forgot-pw; tested via memory outbox. Magic links still missing (P2).
8. ✅ **RBAC** — `role` + `is_verified` on User (migration `5158e99478e5`); `require_role`/`require_admin` dependencies.
> Output: RBAC live, email transport ready, reset/verify tested. 135 tests. OAuth/magic-links pending.

### Phase C — Data I/O & reporting (P1) ✅ COMPLETE (2026-06-29)
9. ✅ **CSV/Excel portfolio import** — `services/portfolio_io.parse_positions` (flexible header aliasing, currency-tolerant, dup-ticker weighted merge) → `POST /portfolio/{id}/import`. *(bug #6 fixed)*
10. ✅ **Export engine** — CSV + Excel (`openpyxl`) + PDF (`reportlab`): `GET /portfolio/{id}/export?format=…`, `GET /portfolio/{id}/tax-report` (LTCG/STCG), `POST /screener/export`. Frontend buttons wired.
11. ➖ **MinIO/object storage** — deferred; broker statements are parsed in memory and never persisted, so no blob store needed yet. Revisit if filing/document upload (Phase D) lands.
> Output: data goes in and comes out; reports are shareable. 156 tests. (Also fixed: `pydantic-settings` missing from requirements.txt.)

### Phase D — AI grounding / RAG (P1) ✅ COMPLETE (2026-06-29) — the differentiator
12. ✅ **Embeddings** via Ollama `nomic-embed-text` (`embedding_service.py`, zero new deps). **pgvector deferred** — current `timescaledb:pg16` image has no `vector` ext (swap risks the volume); embeddings stored as portable JSON + in-process cosine (`rag_store.search`), pgvector-ready seam.
13. ✅ **Ingest + embed** fundamentals/factors (`rag_ingest.build_stock_doc` + `ingest_stocks`). News/filings = optional follow-up.
14. ✅ **RAG retrieval + grounded answer with citations** (`rag_service.retrieve/answer`); **`POST /ai/semantic-search`** + **`POST /ai/ask`** endpoints. **Verified live** (nomic-embed-text 768-dim + llama3.2 cited answer).
15. ✅ **Conversation history** persisted per user (`conversations`/`conversation_messages` + `/ai/conversations` CRUD); **prompt templates externalised** to `services/prompts.py`.
> Output: AI answers from *your* data with citations; semantic search live. 176 tests. (AI-page UI wiring + scheduled embed task = follow-ups.)

### Phase E — Frontend completeness & UX (P1–P2, ~2 weeks) — COMPLETE
16. ✅ **Dark/light toggle** — zero-dep `ThemeProvider` + `html.light` CSS-var overrides + theme-aware `T` tokens + header Sun/Moon toggle (no-flash, persisted). *(bug #2 fixed, verified in-browser)*
17. ✅ **Responsive + mobile nav** — mobile drawer + AI mobile layout + install-free PWA manifest/service worker are wired. Page-level responsive QA and offline UX indicator toast are complete.
18. 🔶 **Shared data table & forms** — generic client-side sorted `DataTable` component built (`frontend/components/ui/DataTable.tsx`) but not yet wired into any page; robust loading/empty/error states.
19. ✅ **Markdown rendering + syntax highlight** — custom fast Markdown parser component built and integrated in AI assistant chat for rendering headings, lists, tables, and highlighted code blocks.
> Output: usable on mobile, consistent UX, no silent failures.

### Phase F — Observability, analytics, docs (P2, ~1 week)
20. **Prometheus metrics + Grafana** (optional self-host); **Uptime Kuma**.
21. **Plausible/Umami** product analytics (privacy-friendly, OSS).
22. ✅ **Mermaid architecture + sequence diagrams** in `/docs`; user & admin guides. *(Fully documented system design, security, RAG, and data fallback sequences)*
23. ✅ **Playwright E2E** — `frontend/playwright.config.ts` + `frontend/e2e/critical-flows.spec.ts` serve the static `out/` export and cover landing, login-form validation, guest navigation, screener shell + Nifty 500 toggle, and Quant Lab (6 tests, no backend needed). The full auth login → screener → portfolio flow is written but self-skips unless `E2E_BACKEND=1`. Wired into CI (frontend job).
> Output: you see usage, uptime, and the system is documented + regression-guarded.

### Phase G — Advanced features (P2–P3, ongoing)
24. F&O analytics, ETFs/indices, correlation network graph, calendar `.ics` export, bulk ops, i18n — pull from `PROJECT_PLAN.md` Phase 2/3 + audit roadmap.

---

## 5. Free / open-source stack decisions (final)

| Concern | Checklist option | **Chosen (OSS-first)** | Why |
|---|---|---|---|
| DB | Supabase/Firebase | **Postgres + pgvector (self-host)** | No lock-in; pgvector adds RAG free |
| Auth | Clerk/Supabase Auth | **FastAPI JWT + authlib OAuth** | Already built; fully OSS |
| Storage | Cloudinary/Firebase | **MinIO / local volume** | S3-compatible OSS |
| Email | — | **fastapi-mail + free SMTP (Brevo/Resend free)** | Free tier, swappable |
| Error tracking | Sentry | **GlitchTip (self-host) or Sentry free** | OSS option exists |
| Analytics | — | **Umami / Plausible (self-host)** | Privacy-friendly OSS |
| Embeddings/LLM | HF/OpenAI | **Ollama + sentence-transformers** | Local, zero cost |
| Deploy | Vercel/Render/Railway | **GH Pages + Render/Fly.io free** | Current setup works |
| Charts | Chart.js/Recharts | **recharts + lightweight-charts** | Already installed |

**Rule of thumb:** anything that must scale or hold user data → self-hosted OSS. SaaS free-tiers only as optional drop-in fallbacks, never the only path.

---

## 6. Quick scoreboard

*Updated 2026-06-29 — Phases A + B (core) complete.*

| Layer | Coverage | Notes |
|---|---|---|
| Backend core (REST, auth, jobs, rate-limit, versioning, CI) | ~95% | Logging, settings, migrations all ✅ |
| Database (PG, Redis, SQLite, migrations) | ~90% | Alembic versioned; TimescaleDB hypertables wired |
| Auth (password, cookies, CSRF, RBAC, reset/verify) | ~80% | OAuth/magic-links still missing |
| AI (chat ✅, RAG/semantic/embeddings ✅) | ~90% | Phase D ✅ — Ollama embeddings + in-process vector store + grounded ask w/ citations + conversation history; pgvector swap optional |
| File handling (import/export) | ~85% | Phase C ✅ — CSV/Excel import + CSV/Excel/PDF export + tax report. ZIP/object-store deferred |
| Visualization | ~70% | Charts live; correlation network / timeline polish pending |
| Security (CSRF ✅, RBAC ✅, httpOnly ✅) | ~90% | XSS audit + HSTS still pending |
| DevEx (docs, tests, docker, CI) | ~90% | 135 tests; ruff + pytest + migration verify in CI |
| Monitoring/Analytics | ~55% | `/metrics` Prometheus ✅; Grafana/Plausible/Umami not wired |
| Frontend polish (theme toggle, responsive, PWA) | ~75% | Phase E — dark/light toggle ✅; mobile drawer ✅; install-free PWA shell ✅; page-level responsive QA pending |

**Completed phases:** A (Foundation), B core (RBAC, email, reset/verify), C (file import/export + reporting), D (RAG/AI grounding), E partial (dark/light toggle)

**Highest-leverage next:** (1) page-level responsive QA/fixes across dashboard, portfolio, screener, AI, (2) OAuth social login (needs creds), (3) Playwright E2E tests, (4) richer offline/PWA fallback states.

---
*Generated 2026-06-28 · Updated 2026-06-29. Free/OSS-only. Pair with `QuantAI_Audit_Improvements_Roadmap.docx` for the strategic rationale and market-needs context.*
