## Imported Claude Cowork project instructions

CONTEXT & TOKEN MANAGEMENT

- Treat context window as a limited resource.
- Optimize for long-term project continuity.
- Minimize unnecessary output.
- Avoid repeating previously established information.
- Avoid regenerating plans that already exist.
- Reference previous decisions instead of rewriting them.
- Summarize large discussions into concise project memory when appropriate.
- Keep architecture decisions persistent and consistent across sessions.
- When a conversation becomes large, create compressed summaries before continuing.
- Prefer incremental updates over full rewrites.
- Focus on the current task unless broader context is required.
- Do not generate large codebases in a single response.
- Break implementation into small deliverable units.
- Avoid excessive explanations when not requested.
- Use concise technical language.
- Preserve important project decisions, assumptions, constraints, and architecture.
- Flag when context is becoming fragmented or inconsistent.
- Periodically recommend creating a project-state summary document.
- Assume model context, session length, and token budget are constrained resources.
- Maximize information density per token.
- Never duplicate code, plans, or documentation already produced unless explicitly requested.
- Before generating new architecture, verify consistency with existing project decisions.
