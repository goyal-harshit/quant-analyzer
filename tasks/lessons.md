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
