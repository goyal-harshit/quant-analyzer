# Lessons Learned: Data Prioritisation

## Issue
Mock seed data was prioritized at the beginning of the fallback chains for `get_price_history`, `get_quote`, and `get_fundamentals` in `data_service.py`. This resulted in stale 2024 dates and mock values showing up in the UI, even when live endpoints were functioning correctly.

## Resolution
Re-ordered fallback chains so that they check memory cache first, Redis cache second, live API endpoints third, and fallback to local seed data only when all else fails. Added robust calculations for missing fields (like `change` and `change_pct`) when yfinance/Fast API doesn't provide them but prices are present.

## Rules for Future Reference
- Live APIs must always take precedence over static seed data unless offline/dev mode is explicitly configured.
- Avoid nesting post-processing logic inside conditional fallback blocks where they might be bypassed on successful live loads.

---

## Issue 2: Hook Refactoring & Variable Scope Mismatch (TypeScript compilation error)
When refactoring the `useStockInsight` custom hook to support the dynamic `refreshSeed` parameter, the destructuring of `refetchInsight` was removed in the page import block, but a secondary button handler on the same page still referenced `refetchInsight()`. This caused a TypeScript type error and aborted the production build compilation.

## Resolution
Modified the secondary button handler to trigger the `setRefreshSeed(prev => prev + 1)` cache-bypass trigger. This resolved the compilation error, removed the dead reference, and correctly hooked up the secondary UI refresh button to the fresh data pipeline.

## Rules for Future Reference
- Always search a file for all usages of destructured variables from a custom hook before modifying the hook's return signature.
- Run `npm run build` after modifying any custom hooks to verify that no page layouts or components contain stale references.

---

## Issue 3: PowerShell Wildcard Characters in File Deletion (`[ticker]`)
When attempting to delete the backup file `frontend/app/stocks/[ticker]/StockDetailClient (1).tsx` using the `Remove-Item` command, the command completed without error but did not delete the file. This occurred because PowerShell treats square brackets `[...]` as wildcards, and thus failed to match the literal path.

## Resolution
Used the `-LiteralPath` parameter instead of the positional path argument: `Remove-Item -LiteralPath "..." -Force`. This bypasses wildcard expansion and correctly target the file with literal brackets.

## Rules for Future Reference
- Always use the `-LiteralPath` parameter in PowerShell's `Remove-Item`, `Get-Item`, or other file commands if the target file or directory contains brackets (`[` or `]`), which is common in Next.js dynamic routes.

---

## Issue 4: Redis reconnect-per-call stalled batch cache reads (production perf bug)
While wiring the 500-name broad screener, a `NIFTY500` screen took **547s**. Root cause was in `services/cache_service.py`: when Redis is unreachable (`REDIS_URL=""` in `render.yaml` prod, or Redis down locally), `_get_raw` called `_connect()` on *every* `get`, and `_connect` re-attempted a full `from_url(...).ping()` each time. A batch of 500 factor-cache lookups became 500 sequential connection timeouts.

## Resolution
Added a reconnect cooldown (`_connect_retry_at`, 30s window) so a failed connect isn't retried on every call, plus `socket_connect_timeout`/`socket_timeout=2` on `from_url`, and an early-out when `redis_url` is empty. A 500-name screen dropped from 547s → ~4.5s. This is a general fix — any batch of cache ops against a down Redis was affected, not just the screener.

## Rules for Future Reference
- Any lazily-connected external client (Redis, DB, HTTP) must back off after a failed connect — never retry the connect inside a per-item hot loop. Cache the failure state with a cooldown.
- When adding a code path that fans a cache/DB call across a large collection, test it with the dependency **down**, not just up — the degraded path is where latency cliffs hide.
- Prod parity matters: `render.yaml` runs with `REDIS_URL=""`, so "Redis is optional" must actually be fast, not just functional.
