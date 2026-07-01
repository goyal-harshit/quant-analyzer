# Tasks: Phase F — Architecture Documentation & Guides

- [x] Create `/docs/architecture.md` with system design and Mermaid diagrams
  - [x] Write system architecture overview
  - [x] Embed Mermaid architecture block diagram
  - [x] Embed Mermaid sequence diagram for Double-Submit CSRF + httpOnly auth
  - [x] Embed Mermaid sequence diagram for RAG / AI Grounding flow
  - [x] Embed Mermaid sequence diagram for Multi-Source Fallback Chain with Circuit Breakers
  - [x] Add Database Hypertable Schema spec
- [x] Create `/docs/guides.md` with user & admin documentation
  - [x] Write User Manual (Screener, Portfolio imports, expected headers, Alerts)
  - [x] Write Admin Manual (Ingestion, RAG reindexing, Observability metrics, troubleshooting)

## Review
- **Architecture Specification**: Created [architecture.md](file:///c:/Users/harsh/Downloads/project/docs/architecture.md) detailing the container topology, database hypertables, and security controls. Included Mermaid diagrams for system architecture, double-submit CSRF auth flows, RAG semantic search grounding, and multi-source provider fallback logic.
- **Operational Guides**: Created [guides.md](file:///c:/Users/harsh/Downloads/project/docs/guides.md) with comprehensive user instructions for Screener filtering and broker CSV/Excel holdings imports (including expected column aliasing). Documented admin procedures for local Ollama setup, reindexing triggers, Prometheus metrics scraping, and circuit breaker status monitoring.
