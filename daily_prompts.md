# Daily and session prompts — Scriptorium Grok Bots

Copyright (c) 2026 Mark Hawksworth. All rights reserved.

These are **user messages**, not standing instructions. Paste one
into the already-configured Clerk or Steward. Do not schedule them
on a timer.

## Access rule

Clerk and Steward may **name** another mandate when the current job
cannot finish without it. They may not **become** that bot, load
its prompt, or start a second session.

Required-only handoff looks like this, then stop:

```
HANDOFF
Need: Repository Steward
Why: local updates are complete; commit/push is outside Clerk scope
Suggested prompt: (one of the blocks below)
```

Mark copies that suggested prompt into the Steward (or Verifier,
Calibrator, Archivist). One handoff card per session. Never chain
Clerk → Steward → Verifier in one go.

Daily pair: Clerk and Steward only.
Not daily: Bug Hunter, Enhancement Architect, Environment Admin,
Release Verifier, Prompt Calibrator, Note Archivist.

---

## 1. Morning desk check — Clerk

Use on a day you expect to touch `C:\\Scriptorium`. Skip on days
you will not open the project.

```
Desk check only. Do not edit source.

1. List uncommitted paths under C:\\Scriptorium (or say if you
   cannot see that tree).
2. Confirm scriptorium_config.json is not among them.
3. Give the next free notes_NNN.txt number across 00_Drafts and
   01_Active.
4. One-line APP_VERSION from scriptorium.py.

Then stop. No MEMORY.md rewrite, no commit, no GitHub.
```

---

## 2. End of coding session — Clerk

Use when you have finished editing but have **not** decided to
publish yet.

```
Session close-out. Do not push.

Summarise what changed this session (paths only).
Flag anything that must not be committed (config, dist, exe,
__pycache__).
If work actually shipped in-tree, draft three MEMORY.md lines
I can paste — do not write MEMORY.md unless I say "write it".

If the tree is ready to publish, emit one Steward HANDOFF card
with a commit message that names the version or the hygiene
item. Do not commit yourself.
```

---

## 3. Commit once updates are done — Steward

Use only after you have reviewed the Clerk close-out (or your
own diff) and want the remote updated. This is the prompt that
matches "commit the files once all updates have been made".

```
All updates for this session are done. Synchronise
C:\\Scriptorium with origin/main.

1. Compare local and remote. List files that would be added,
   modified, or deleted.
2. Refuse if scriptorium_config.json, dist/, build/, *.exe,
   or any API key would be included.
3. If the list is clean, commit on main with message:

   <replace with the message from the Clerk HANDOFF, or write
    one British-English sentence naming the change>

4. Push origin main once.
5. Report the commit SHA and stop.

Do not open issues, do not start the Verifier, do not pull
MEMORY.md in full.
```

Shorter form, once you trust the ritual:

```
Updates are done. Show the change list, exclude secrets and
build artefacts, then commit and push main. Stop after the SHA.
```

---

## 4. Pull first — Steward

Use when the Windows box may be behind GitHub (for example after
the copyright or bot-prompt commits made from this project).

```
Pull only. git pull origin main into C:\\Scriptorium.
Do not commit local dirty files away. If the tree is dirty,
stop and list the local paths instead.
```

---

## Not daily — keep these on the shelf

**Notes piling up in `00_Drafts`** — Archivist:

```
Archive pass only. Inventory 00_Drafts and 01_Active. Next
number? Move notes_0XX.txt to 01_Active if I name it closed.
Do not delete. Do not touch scriptorium.py.
```

**Version about to ship** — Verifier:

```
Verify <version>. Check APP_VERSION against version_info.txt,
ast.parse scriptorium.py, and that the live config mtime is
unchanged. Do not rebuild the exe unless I say rebuild.
```

**Prompt text just changed** — Calibrator:

```
Calibrate <function or tone name> against Ollama llama3.2:3b
only. Isolated config. Cap at eight backend calls. Report-only
unless I authorise a guard-text fix.
```

Do not turn any of those three into a morning habit. They are
how a quiet pair becomes a swarm.
