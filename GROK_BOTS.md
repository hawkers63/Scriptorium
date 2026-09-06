# Grok Bot roster — Scriptorium

Copyright (c) 2026 Mark Hawksworth. All rights reserved.
These prompts are part of the Scriptorium work and may not be copied
or adapted for another project without Mark's consent.

Paste the body of a `*_agent.md` file into a Grok Bot custom
instruction. Invoke **one** bot per session. Do not chain bots.

| Bot | File | Mandate | Default posture |
|---|---|---|---|
| Coding assistant | `AGENTS.md` | Incremental implementation in `scriptorium.py` | Writes code only after Mark authorises the task; commit local, **ask before push** |
| Bug Hunter | `bug_hunter.md` | Static analysis of logic, state, and consistency | Read-only except one draft note |
| Enhancement Architect | `enhancement_agent.md` | New-feature design that respects shipped/deferred history | Read-only except one draft note |
| Environment Admin | `environment_admin.md` | Ollama, packages, note archiving on Windows 11 | No source edits |
| **Workspace Clerk** | `workspace_clerk.md` | Local files under `C:\\Scriptorium`; note numbering; hygiene | File work only; never push |
| **Repository Steward** | `repo_steward.md` | GitHub `hawkers63/Scriptorium`; copyright; professional standards | Sync only after Mark says push |

## Anti-swarm rule (every bot)

Bots must not call, spawn, mention-ping, or hand off to another bot.
One session, one mandate, one deliverable, then stop. Full text of
the rule lives in each prompt so a pasted instruction is self-contained.

## How to start a session

1. Choose exactly one row from the table.
2. Paste that file into the Grok Bot instruction.
3. Give a single, bounded task.
4. Do not open a second bot on the same task while the first is running.
