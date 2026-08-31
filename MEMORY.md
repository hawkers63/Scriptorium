# Scriptorium — Session Memory

Incremental log of what happened in each Claude Code CLI session, newest
first. Read this alongside `ROADMAP.md` at the start of every session (cue:
Mark saying "lets get started").

---

## 2026-08-31 (continued) — v2.1 pushed; v2.2 (backend robustness) implemented

Pushed the two v2.1 commits to `origin/main` after Mark's go-ahead
(`94cad61..60d787c`).

All six v2.2 tasks from `ROADMAP.md` implemented in `scriptorium.py`
(APP_VERSION bumped to "2.2"), not yet committed:

- Added `_payload_object()` helper; `call_anthropic()` and `call_ollama()`
  now validate the decoded JSON is a dict, and that `content`/`message` are
  the expected shape, before indexing into them — a malformed envelope now
  raises a specific `BackendError` instead of a raw `AttributeError`/
  `TypeError`.
- Both backends now catch `TimeoutError` (not a `URLError` subclass on
  Python 3.10+, so it previously fell through to a generic "Unexpected
  error") and `call_ollama()` gained the `json.JSONDecodeError` handler
  Claude's path already had.
- `SettingsDialog._detect_models()` now runs `list_ollama_models()` on a
  daemon thread and applies the result via `self.after()` in a new
  `_finish_model_detection()`, instead of blocking the modal Settings
  dialog on the Tk thread for up to 3 seconds.
- Added `Scriptorium._post_to_ui()`; `process()`'s worker now posts to the
  UI thread through it (`try/except/else` so a failed success-post can't
  become a second error-post), guarding against `tk.TclError` when the
  window has been destroyed mid-request.
- Fixed the placeholder-sentinel nonce collision from notes_012 Bug A:
  `mask_placeholders()` now mixes a `secrets.token_hex(3)` nonce into every
  generated sentinel, so source text that already contains something
  shaped like `⟦PH0⟧` (e.g. left over from a prior failed run) can no
  longer collide with a freshly generated one and corrupt the restore.

**Verification performed:**
- `ast.parse()` syntax check — clean.
- Isolated logic tests (monkeypatched `urllib.request.urlopen`, no real
  network calls) covering: non-object JSON root for both backends, Ollama
  non-JSON body, Ollama null `message`, Anthropic non-dict content blocks,
  `TimeoutError` on both backends, and that valid envelopes still parse
  correctly — all pass, all produce a `BackendError` (never a raw
  exception) for the invalid cases.
- Placeholder round-trip test: source containing both a literal `⟦PH0⟧`
  and a real `[Name]` placeholder restores byte-for-byte with no false
  "appeared N times" warning (previously corrupted per notes_012).
- Launched the live GUI twice (before and after these changes) via
  PowerShell — clean window, correct title, no stderr.
- **Not yet verified live:** clicking Detect in Settings against a real or
  simulated slow Ollama endpoint (confirming the dialog stays responsive),
  and closing the app mid-request against the packaged `.exe` specifically
  (the `_post_to_ui` guard is logically identical to the already-proven
  `_claim_request`/worker pattern, but hasn't been driven through the
  actual Tk event loop this session — no GUI automation tool is set up for
  this native Tkinter app).

---

## 2026-08-31 (continued) — v2.1 tasks 1–6 implemented and committed

Git workflow confirmed with Mark for the rest of this roadmap: commit
locally as each task passes verification, but **ask before pushing** to
`origin/main` (AGENTS.md's auto-push-immediately directive was not
adopted).

All six v2.1 tasks from `ROADMAP.md` are done and locally committed
(not yet pushed — pending Mark's go-ahead):

- **Repo sync** (commit `4cf690a`): committed `scriptorium.spec`, `icon/`,
  `AGENTS.md` + the three role-instruction files, and the `notes/01_Active/`
  restructure — all previously untracked despite v2.0's commit message
  claiming "standalone packaging". Rewrote `update_repo.bat` to
  `git add --all` and fail fast/loud on a bad commit/push instead of always
  printing "Repository update complete".
- **Configuration safety** (scriptorium.py, APP_VERSION bumped to "2.1"):
  - Added `normalise_config()` — clamps `backend`/`default_mode`/
    `default_strength`/`default_role`/`default_tone`/`default_diff_view` to
    their allowed values and coerces stringy booleans
    (`privacy_ack`/`protect_placeholders`/`check_letter_conventions`);
    free-form fields (API key, model tags) are left untouched. Wired into
    every `load_config()` return path.
  - `run_backend()` now fails closed with a `BackendError` on an
    unrecognised backend string instead of silently defaulting to Claude —
    this was the one real privacy-consistency bug in the backlog (status
    bar could claim "stays on this machine" while text actually went to
    Anthropic).
  - `save_config()` now returns `True`/`False` instead of `None` either way.
  - `SettingsDialog._save()` builds a candidate dict, normalises it, and
    only commits it to `self.cfg` if the write actually succeeds; on
    failure it shows an error dialog and keeps the dialog open instead of
    closing on an unsaved change.
  - Added `Scriptorium._maybe_warn_unreadable_config()` — a visible
    `messagebox.showwarning` for a config file that couldn't be parsed.
    Previously this was `print()`-only, invisible in the packaged
    `.exe` (`console=False` in the spec).

**Verification performed:**
- `ast.parse()` syntax check — clean.
- Isolated logic tests (no GUI) for `normalise_config` (invalid enum,
  stringy bool, free-form fields preserved), `run_backend` fail-closed, and
  `save_config` return value on success/refused-unreadable — all pass.
- Launched the actual GUI (`python scriptorium.py`) via PowerShell,
  confirmed the process stays alive with the correct window title and no
  stderr/traceback, then closed it. Did **not** test the unreadable-config
  warning path against the live GUI — that would require corrupting the
  real `scriptorium_config.json`, which holds a live API key; covered
  instead by the isolated `save_config`/`load_config.unreadable` logic
  test.
- Did not test Settings-dialog save failure (e.g. read-only file) against
  the live GUI this session — flagged as a v2.1 acceptance-checklist item
  still to verify by hand.

**Two commits made, not yet pushed:**
1. `4cf690a` — repo hygiene (packaging assets, docs, update_repo.bat).
2. scriptorium.py config-safety changes + this file + `ROADMAP.md`
   (about to be committed).

**Remaining before v2.1 is done:** none of the code tasks — all six are
implemented. What's left is working through `ROADMAP.md`'s v2.1 acceptance
checklist by hand (fresh-clone build, forced commit/push failure, hand-edited
config values, forced `save_config` failure, corrupted config in the actual
running app) and getting Mark's go-ahead to push.

---

## 2026-08-31 — Roadmap established; v2.1 not yet started

**Context found on opening the project:** working tree at v2.0 (committed
94cad61, 2026-08-29), with three new review notes (`notes_010.txt`,
`notes_011.txt`, `notes_012.txt`) added since that commit, on top of the
nine already on file. `notes/` had also been restructured locally into
`notes/01_Active/` (git still showed the old `notes/notes_001-002.txt`
paths as deleted, untracked elsewhere).

**Work done this session:**
- Read all 12 existing notes (`notes_001`–`012`) plus `README.md`,
  `AGENTS.md`, `bug_hunter.md`, `enhancement_agent.md`,
  `environment_admin.md`, and reconciled their overlapping/superseding
  findings against each other.
- Cross-checked every "still open" claim in notes_009–012 directly against
  the live `scriptorium.py` (v2.0, 1,297 lines) rather than trusting the
  notes at face value — confirmed all of them are genuinely still absent
  from the code (no `normalise_config`, no `TimeoutError` handling, no
  presets, no live word count, no tray, etc.).
- Confirmed notes_011's Finding 1 (repo sync gap) directly: `git ls-tree
  HEAD` has no `scriptorium.spec` or `icon/`, `update_repo.bat` only stages
  three hard-coded files with no failure handling.
- Created `ROADMAP.md`, scoping v2.1 → v2.5:
  - **v2.1** — release integrity (repo sync) + configuration safety
    (normalise_config, fail-closed backend, truthful save reporting).
  - **v2.2** — backend robustness (envelope validation, timeouts, Detect
    off the Tk thread, worker shutdown guard, placeholder-sentinel nonce).
  - **v2.3** — Accept-during-processing fix, Word-export/undo-stack polish,
    plus the three most-requested usability features (live counts, named
    presets, review keyboard shortcuts).
  - **v2.4** — tray/autostart (deliberately deferred until now, per every
    prior note), packaged-exe icon/metadata, frozen-config-fallback fix,
    source→frozen migration prompt.
  - **v2.5** — designated by Mark as a dedicated bug diagnosis/resolution
    session; deliberately left unscoped beyond a verification procedure —
    see `ROADMAP.md` for the plan.
- Created this file (`MEMORY.md`) as the running session log.

**Not yet done:** no code in `scriptorium.py` has been touched this
session. v2.1 implementation has not started.

**Open question for Mark before touching code:** `AGENTS.md` (currently
untracked, not yet committed) directs auto-commit-and-push to `main` on
every completed/tested task with no confirmation step. That's a more
aggressive git posture than the default safe-by-default behaviour. Need
Mark's explicit steer on commit/push cadence before v2.1 work begins —
see the question asked in-session.
