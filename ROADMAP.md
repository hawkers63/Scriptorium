# Scriptorium Roadmap

**Read this file, `MEMORY.md`, and `AGENTS.md` at the start of every session.**
When Mark says "lets get started", that is the cue to open these three files
before doing anything else.

Current shipped version: **2.3** (state-consistency fixes, live counts,
presets, review shortcuts). This roadmap scopes the next three releases:
**2.4 → 2.6**.

Scope through v2.3 was drawn from twelve accumulated review notes
(`notes/01_Active/notes_001.txt` – `notes_012.txt`), written independently by
three different reviewers (ChatGPT/Codex, Claude, Grok) across v1.0–v2.0.
Where two or more reviewers converged on the same finding, that finding is
treated as reliable. All findings were cross-checked against the actual v2.0
source (`scriptorium.py`, 1,297 lines) on 2026-08-31 — every "still open" item
was confirmed absent from the code, not just asserted by a note.

v2.4 was inserted ahead of the previously-planned tray/autostart release at
Mark's request, on the strength of a thirteenth note (`notes_013.txt`,
31 Aug, Mark/Codex) proposing multi-tone composition and an expanded role
list — unrelated to tray/autostart, so it did not fit the existing v2.4 slot
without pushing that work back a step. The former v2.4 (tray) is now v2.5,
and the former v2.5 (bug diagnosis) is now v2.6.

---

## How to use this document

Each release lists **Goal**, **Tasks** (with the note(s) that raised them and
the general code location), and an **Acceptance checklist** to verify before
tagging the version. Work through tasks in the listed order — later tasks in
a release sometimes depend on earlier ones (noted inline). Update
`MEMORY.md` as tasks complete; tick items here only once verified, not once
written.

Do not re-derive fixes from the older notes (001–008) — those defects are
already closed in v2.0. Notes 009–013 are the live backlog this roadmap is
built from.

---

## v2.1 — Release Integrity & Configuration Safety

**Goal:** close the gap between what's on disk and what's in Git, and stop
configuration problems from crashing the app, lying about privacy, or
silently failing to save.

1. **Fix the repository sync helper** (notes_011 Finding 1 — HIGH).
   `update_repo.bat` only stages three hard-coded files and doesn't stop on
   a failed commit/push, so it can report success while the remote is
   missing `scriptorium.spec`, `icon/`, and other tracked-but-unpushed
   files. Confirmed today: `git ls-tree HEAD` has no `scriptorium.spec`.
   Replace it with a `git add --all` + fail-fast version (snippet already
   drafted in notes_011). Decide what belongs in `.gitignore` (the spec and
   icons should be tracked; the current `.gitignore` already says the spec
   is meant to be tracked but the file was never actually added).
2. **Commit the currently-untracked project files** that should be in
   source control: `scriptorium.spec`, `icon/`, `AGENTS.md` and the three
   role-instruction files, the restructured `notes/01_Active/` tree,
   `scriptorium.bat`-adjacent housekeeping. Confirm nothing under
   `scriptorium_config.json` or other secrets is included.
3. **Normalise loaded configuration values** (notes_009 Fix 2, notes_010
   Fix 2, notes_011 Finding 2). `load_config()` only checks the root is a
   dict; an invalid `default_mode`, a stringy `"false"` for a boolean flag,
   or an unrecognised `backend` value is merged unchanged. Add
   `normalise_config()` and call it from `load_config()`.
4. **Make `run_backend()` fail closed** on an unrecognised backend string
   instead of defaulting to Claude (notes_010 Bug 5 / notes_011 Finding 2).
   This is the one privacy-relevant bug in the whole backlog: today the
   status bar can say "stays on this machine" while the request actually
   goes to Anthropic.
5. **Make `save_config()` report success/failure truthfully**, and have
   `SettingsDialog._save()` keep the dialog open and show an error instead
   of closing on a failed write (notes_011 Finding 3).
6. **Surface an unreadable config file in the UI**, not just via `print()`
   (notes_010 Fix 6, notes_011 Finding 10) — the packaged `.exe` has no
   console (`scriptorium.spec` sets `console=False`), so today that warning
   is simply invisible to a user running the standalone build.

### Acceptance checklist
- [ ] Fresh `git clone` of `main` contains `scriptorium.spec` and `icon/`,
      and `pyinstaller scriptorium.spec` builds from that clean clone.
- [ ] `update_repo.bat` exits non-zero and prints a failure (not "complete")
      when a commit or push is forced to fail.
- [ ] Hand-edit `scriptorium_config.json` with an invalid `backend`, a
      stringy boolean, and an out-of-range `default_mode`; app boots
      cleanly, status bar and actual dispatch agree, privacy notice still
      appears for the cloud backend.
- [ ] Make `save_config()` fail (e.g. read-only file); Settings dialog
      stays open with a visible error; in-memory config is unchanged.
- [ ] A corrupted `scriptorium_config.json` produces a visible dialog, not
      just a console line, in a `pythonw`-launched session.

---

## v2.2 — Backend Robustness

**Goal:** every network/parsing failure from Claude or Ollama becomes a
specific, actionable `BackendError` — never a generic "Unexpected error",
and never an uncaught exception that reaches the Tk callback boundary.

Depends on v2.1's `normalise_config`/fail-closed `run_backend` being in
place first (envelope checks build on the same functions).

1. **Validate response envelopes before extraction** (notes_009 Fix 3,
   notes_010 Fix 3, notes_011 Finding 4). Both `call_anthropic()` and
   `call_ollama()` currently assume the decoded JSON is a dict with the
   expected nested shape; a non-object root, a scalar content block, or a
   null `message` raises `AttributeError`/`TypeError` instead of a friendly
   error. Add a shared `_payload_object()` guard and type-check `content` /
   `message` before use.
2. **Catch `TimeoutError` on both backends** (notes_010 Bug 4, notes_011
   Finding 5, notes_012 §3.2). Confirmed absent: neither `except` tuple
   currently includes it, and it is not a `URLError` subclass on Python
   3.10+, so a slow request surfaces as "Unexpected error: timed out".
3. **Add the missing `json.JSONDecodeError` handler to `call_ollama()`**
   (Claude's path already has one; Ollama's doesn't).
4. **Move Ollama model detection off the Tk thread** (notes_009 Fix 4,
   notes_010 Fix 1, notes_011 Finding 6, notes_012 §3.4). `_detect_models()`
   currently blocks the modal Settings dialog for up to 3 seconds.
5. **Guard worker→UI delivery against a destroyed window** (notes_009
   Finding 5, notes_010 Bug 6/Fix 4, notes_011 Finding 7, notes_012 §3.1).
   `_on_close()` invalidates request ownership but the background thread's
   `self.after(...)` call itself is unguarded; closing the app while a
   request is in flight can throw `TclError` on the worker thread — visible
   as a post-exit crash dialog on the packaged `.exe` specifically because
   `disable_windowed_traceback=False` in `scriptorium.spec`.
6. **Fix the placeholder-sentinel nonce collision** (notes_012 Bug A —
   confirmed reproducible today). If source text already contains something
   shaped like a sentinel (e.g. a pasted `⟦PH0⟧` left over from a previous
   failed run), `restore_placeholders()` cannot tell it apart from a real
   one and corrupts the text. Mix a per-call `secrets.token_hex()` nonce
   into every generated sentinel.

### Acceptance checklist
- [ ] Mock/point each backend at a non-JSON, non-object, and malformed
      response in turn; every case produces a specific `BackendError`
      dialog, never "Unexpected error".
- [ ] Force a timeout on each backend; friendly timeout message appears.
- [ ] Settings remains movable/closable while Detect is running against a
      deliberately slow/unreachable Ollama endpoint.
- [ ] Start a request, close the app immediately; no crash dialog, no
      orphaned traceback (test against the packaged `.exe`, not just
      `python scriptorium.py` — the console build masks this one).
- [ ] Paste text containing a literal `⟦PH0⟧`-shaped string alongside a real
      `[Name]` placeholder; Process and Accept; original prose is not
      corrupted.

---

## v2.3 — Editor State Polish & Usability Features

**Goal:** close the last state-consistency gap (Accept-during-processing),
then ship the three usability features every reviewer has independently
proposed since notes_002 and that still don't exist in v2.0.

1. **Stop Accept from silently cancelling a newer in-flight request**
   (notes_010 Bug 9/Fix 7, notes_011 Finding 9, notes_012 §3.5). Today only
   `process_btn` is disabled while busy; clicking Accept while a second
   request is running commits the *old* revision and discards the one
   still being generated, with no warning. Add `_set_processing_state()` /
   `accept_btn` and disable Accept for the life of a request.
2. **Catch the Word-export illegal-XML `ValueError`** (notes_009 Fix 6,
   notes_010 Fix 5, notes_011 Finding 8). `python-docx` raises `ValueError`
   for text containing control characters (common from PDF-sourced paste);
   `export_file()` only catches `ImportError`/`OSError` today.
3. **Bound and de-duplicate the undo stack** (notes_009 Fix 7, notes_011
   Finding 11). Currently unbounded across a session and records no-op
   snapshots (e.g. Clear on an already-empty pane).
4. **Live word/character counts** (proposed independently in notes_002,
   006, 009, 010, 012 — the single most-requested feature across every
   review, still unimplemented). Bind `<<Modified>>` on `original_box`,
   refresh `_refresh_status()` on every edit, not just after an action.
5. **Named writing presets** (notes_002, 005, 006, 009, 010 — second
   most-requested, still unimplemented). A `WRITING_PRESETS` dict that
   populates the existing Mode/Strength/Role/Tone controls; controls stay
   independently editable afterwards. Do not persist the last-used preset
   to config on this pass — keep it toolbar-local.
6. **Keyboard shortcuts for Accept/Reject/Copy revision/Undo** (notes_009
   Feature 3, notes_011 Feature 3). Process/Import/Export already have
   bindings; the review actions don't. Add a small `_bind_shortcuts()`
   registry; do not intercept Ctrl+C/Ctrl+V inside the Original textbox.

### Acceptance checklist
- [ ] Display revision A, start Process for B, click Accept: Accept is
      disabled/refused until B completes; A is not silently committed.
- [ ] Export text containing a control character (e.g. U+000B) to `.docx`;
      friendly error dialog, no traceback.
- [ ] A long session of repeated Clear/Import/Paste does not grow
      `undo_stack` past its cap; Clear on an empty pane is a no-op.
- [ ] Typing, pasting, cutting and undoing in the Original pane updates the
      word/character count live, with no action click required.
- [ ] Each preset sets exactly the four documented controls and remains
      hand-editable afterwards; "(none)" is a no-op.
- [ ] Ctrl+Shift+A / Esc / Ctrl+Shift+C / Ctrl+Z fire the right action and
      ordinary Ctrl+C/Ctrl+V still work for text selection in Original.

---

## v2.4 — Multi-Tone Composition & Expanded Roles

**Goal:** implement notes_013's two proposals — combining up to a handful of
tones in one request instead of a single choice, and widening the role menu
— while holding the line on Scriptorium's core contract: a tone or role may
change wording, register and rhythm, never add content. Roles and tones
actually added were curated down from notes_013's full lists (18 candidate
roles, 14 candidate tones); see the code comments beside `ROLES` and
`TONE_INSTRUCTIONS` for why each omission was left out — mostly heavy overlap
with something already on the menu.

1. **Data-driven, composable tones** (notes_013). Replace the single generic
   "steer the tone towards: X" prompt line with `TONE_INSTRUCTIONS` — an
   explicit, bounded instruction per tone — plus `build_tone_instruction()`,
   which treats an ordered list as dominant-tone-first-with-supporting-tones
   rather than joining labels into a string. `TONES` is derived from
   `TONE_INSTRUCTIONS` so the two cannot drift apart.
2. **Tone validation as a single boundary** (notes_013). `validate_tones()`
   is the sole place that drops duplicates/unknowns, enforces
   `MAX_SELECTED_TONES`, and rejects a genuinely contradictory pair via
   `TONE_CONFLICTS` (Concise+Detailed, Casual+Formal) — config loading,
   preset application, the picker dialogue and prompt construction all call
   through it rather than keeping separate copies of the rules.
3. **Config migration** (notes_013). `default_tone` (string) becomes
   `default_tones` (ordered list); `normalise_tone_config()` migrates an
   existing installation's old key on load and folds an invalid/conflicting
   stored selection back to `["Concise"]` rather than crashing.
4. **Compact tone picker UI** (notes_013). `TonePickerDialog` replaces the
   single-select `CTkOptionMenu` with a toolbar button that opens an ordered
   checkbox picker (Clear/Cancel/Apply). Deliberately capped at
   `TONE_PICKER_LIMIT = 2` even though the data model and `validate_tones()`
   support `MAX_SELECTED_TONES = 3` — notes_013's own recommendation, so a
   two-tone combination can be checked against real output before the picker
   is opened up to three with a one-line change.
5. **Curated new tones** (notes_013, narrowed). Added Casual, Direct,
   Empathetic, Detailed, Constructive and Persuasive alongside the existing
   six, chosen to cover a distinct stylistic dimension each (register, force,
   interpersonal manner, detail, purpose) rather than padding the list with
   near-synonyms. "Detailed" and "Persuasive" carry the strictest bounding
   text of any tone, since both are the ones most likely to be misread as
   licence to add content.
6. **Curated new roles** (notes_013, narrowed). Added Engineer, Journalist,
   Lawyer, Project Manager and Technical Writer to the existing six, again
   trimmed from notes_013's eighteen candidates down to entries that don't
   substantially duplicate an existing role. Lawyer and Journalist in
   particular carry an explicit "never imply legal advice" / "never fabricate
   attribution" guard in their instruction text, per notes_013's cautions.

### Acceptance checklist
- [x] A single selected tone behaves exactly as before (one bounded
      instruction, no dominant/supporting language in the prompt).
- [ ] Two selected tones show correct dominant/supporting phrasing, and a
      real run against the live backend changes wording/register only — no
      new facts, figures or invented detail (check combinations involving
      Detailed or Persuasive specifically). **Blocked** — Mark's configured
      Claude API key is identity-linked and needs an `anthropic-workspace-id`
      header `call_anthropic()` doesn't send; no workspace ID was available
      in the console to add it. Pre-existing, unrelated to v2.4 — see the
      "Deferred" section below. Retry once a key/header fix is in place, or
      against Ollama instead.
- [x] The picker refuses a third tone even though `validate_tones()` itself
      accepts three; ticking a third checkbox shows the limit message and
      the checkbox reverts.
- [x] Choosing Concise+Detailed or Casual+Formal in the picker is refused
      with the conflict message; a hand-edited config with that pairing in
      `default_tones` falls back to `["Concise"]` on load rather than
      crashing.
- [x] A config file with the legacy `default_tone` string still loads
      correctly and is silently migrated to `default_tones` on next save.
      **Caught a real bug while verifying this**: `load_config()` always
      seeds its working dict from `DEFAULT_CONFIG` (which already supplies
      `default_tones: ["Concise"]`) before merging in the loaded file, so
      `normalise_tone_config()` found a valid list already present and
      never actually reached the legacy-string branch — an old file with
      only `default_tone` silently lost the user's real value to the
      default instead of migrating it. Fixed by checking for the legacy
      key first, rather than as a fallback for a missing/malformed list.
- [x] The three existing presets still apply their original single tone
      correctly now that it is stored as a one-item list.
- [ ] Spot-check the Lawyer and Engineer roles against real source text:
      no invented legal interpretation, obligation, or technical conclusion
      not already present. **Blocked** on the same Claude API issue above.

---

## v2.5 — Tray, Autostart & Distribution Polish

**Goal:** the deferred, higher-risk lifecycle feature (minimise-to-tray /
start-with-Windows) that every earlier note has correctly pushed to "later,
once the packaging and shutdown model are stable" — v2.0's packaging and
v2.2's shutdown hardening now make this a reasonable release. Bundle in the
remaining small distribution-polish items so packaging work lands together.

1. **Minimise to tray / start with Windows** (notes_008 full spec, notes_012
   Feature 2). Settings-gated (`minimise_to_tray`, `start_with_windows`,
   `start_minimised` config keys). `_on_close()` withdraws instead of
   destroying when the option is on; a `ctypes`-based `Shell_NotifyIcon`
   wrapper (no new pip dependency) or `pystray`+`pillow` if the ctypes path
   proves painful; `winreg` `HKCU\...\Run` entry launching `pythonw.exe
   scriptorium.py --minimised`. Ship with a visible Quit path from day one
   — never trap the user with a broken tray icon and no window.
2. **Give the packaged `.exe` its icon and version metadata** (notes_011
   Finding 13). `icon/icon-96.ico` already exists but `scriptorium.spec`
   sets `icon=None`; add it plus a minimal PyInstaller version-info
   resource (depends on v2.1's spec actually being tracked in Git).
3. **Fix the frozen-build config fallback path** (notes_010 Bug 11, notes_011
   Finding 12). If `%LOCALAPPDATA%\Scriptorium` creation fails, the code
   currently falls back to a bare loose file in the user's home folder
   instead of a dedicated subfolder — a later successful launch won't find
   it, so settings appear to reset.
4. **One-time source→frozen config migration prompt** (notes_011 Finding
   14). A user moving from `python scriptorium.py` to the standalone `.exe`
   currently loses their API key/preferences silently because the two
   modes use different config paths by design; offer an explicit,
   one-time "import your existing settings?" prompt instead.
5. **Softer / Stronger one-click re-run** (notes_003/notes_012 Feature 3).
   Small, independent — two buttons that nudge `strength_var` one notch and
   re-run `process()`. Low-risk polish to land alongside the packaging work.

### Acceptance checklist
- [ ] Close the window with "minimise to tray" on: window vanishes, process
      stays alive, tray icon appears; left-click restores and focuses it.
- [ ] Tray Quit ends the process and removes the icon; Alt+F4 with the
      option off quits normally as before.
- [ ] Log off/on (or reboot) with "start with Windows" ticked: app starts
      minimised, no console flash, `pythonw.exe` confirmed via Task
      Manager.
- [ ] Untick "start with Windows" in Settings; `HKCU\...\Run` value is gone
      (`reg query`).
- [ ] Packaged `.exe` shows the Scriptorium icon in Explorer/taskbar and
      populated FileDescription/ProductVersion fields.
- [ ] Deleting/renaming `%LOCALAPPDATA%\Scriptorium` and relaunching
      produces a dedicated fallback folder, not a loose file in `~`.
- [ ] First run of the `.exe` after having used the source version offers
      the import prompt; declining leaves both configs untouched.

---

## v2.6 — Bug Diagnosis & Resolution Session

**Goal:** this release is deliberately **not** pre-scoped with a fixed
feature/fix list, per Mark's designation — it is a dedicated diagnosis
session against whatever state v2.1–v2.5 actually left the app in,
including anything those releases introduced.

Run this as a structured pass, in order:

1. **Regression-verify every acceptance checklist item from v2.1–v2.5**
   against the real app (source run *and* the packaged `.exe` — several
   confirmed defects in this backlog, e.g. the post-close crash dialog,
   only manifest in the windowed build, not `python scriptorium.py`).
2. **Fresh static review pass** — re-read `scriptorium.py` end to end
   against its then-current line count and cross-check the two deferred,
   never-confirmed suspicions sitting in the backlog since notes_010/011:
   - S1: a custom `anthropic_model` not present in `ANTHROPIC_MODELS` may
     be silently replaced by the first `CTkOptionMenu` value on Settings
     Save.
   - S2: `paste_original()`'s `sel.first`/`sel.last` selection-replace may
     not work on some CustomTkinter/Tk builds and could silently fall back
     to "always insert at caret".
   Confirm or dismiss both against the real running GUI — the roadmap has
   deliberately left them unconfirmed because they need actual Tk
   interaction, not static reading.
3. **Live GUI walkthrough** of both editing modes' full lifecycle: Process
   → Accept/Reject/Undo/Copy/Export, for each of Claude and Ollama
   backends, deliberately racing the state-consistency scenarios this
   backlog has repeatedly found (edit-during-processing, Reject/Clear/
   Import/Undo while busy, Settings Save mid-request).
4. **Triage and fix** whatever the above turns up, smallest-safe-change
   style, consistent with every prior note's philosophy in this project.
5. **Update this roadmap** with a v2.7+ scope once the diagnosis is
   complete — do not pre-write it now; that defeats the purpose of a
   dedicated diagnosis session.

---

## Deferred / explicitly out of scope for v2.1–v2.6

- Migrating the API key to Windows Credential Manager (`keyring`) — real
  architectural change, correctly flagged as out-of-scope by every note
  since notes_001. Revisit only if the plaintext-config risk is ever
  actually exploited or Mark asks for it directly.
- Splitting `scriptorium.py` into multiple modules — every note that raised
  it (notes_006 §4) explicitly deferred it as "not yet, avoid two things
  moving at once". The file is ~1,300 lines and still proportionate.
- "Suggest 3 alternatives" per request (notes_001) — changes the response
  schema, UI state and token cost; correctly ordered last by every review
  that mentions it, and not picked up in this roadmap either.
- Recent-revisions history panel (notes_003/005/006) — sound idea, but
  every subsequent review has consistently prioritised the items above it;
  revisit after v2.6 if it's still wanted.
- `anthropic-workspace-id` header support — discovered 2026-09-01 while
  hand-testing v2.4: `call_anthropic()` has never sent this header, and an
  identity-linked API key now needs one (`HTTP 400`). Not fixed because
  Anthropic's console showed no Workspace ID value to use for Mark's key
  (Workspace "Default") — revisit once a usable ID is available, or if
  Mark switches to a non identity-linked key instead (no header needed
  either way). Pre-existing, unrelated to v2.4 — would affect a v2.3
  single-tone request identically.

---

## Source notes reference

| Note | Date (2026) | Author | Target version | Status |
|---|---|---|---|---|
| notes_001–002 | 25 Aug | ChatGPT / Antigravity | v1.0 | Closed by v1.1–v1.4 |
| notes_003–004 | 26 Aug | Antigravity / Claude | v1.2 | Closed by v1.3–v1.4 |
| notes_005 | 27 Aug | Claude | v1.4 | Closed by v1.5–v1.7 |
| notes_006–007 | 27 Aug | Grok | v1.5 | Closed by v1.7–v2.0 |
| notes_008 | 28 Aug | Mark & Grok | v1.7 | Partially closed (tray deferred → v2.5) |
| notes_009 | 29 Aug | ChatGPT / Codex | v1.9 | Partially closed by v2.0; remainder → v2.1–v2.3 |
| notes_010 | 29 Aug | Grok | v2.0 | **Open — basis for v2.1–v2.3** |
| notes_011 | 31 Aug | ChatGPT / Codex | v2.0 | **Open — basis for v2.1–v2.3, v2.5** |
| notes_012 | 31 Aug | Lynne | v2.0 (delta) | **Open — basis for v2.2–v2.3, v2.5** |
| notes_013 | 31 Aug | Mark / Codex | v2.3 | **Open — basis for v2.4** |

All confirmed still-open as of 2026-08-31 by direct inspection of
`scriptorium.py` (v2.0, 1,297 lines): no `normalise_config`, no
`TimeoutError` handling, no `PRESETS`/`WRITING_PRESETS`, no
`<<Modified>>`/`KeyRelease` binding, no `accept_btn`, no `secrets` import,
no `_payload_object`/`_post_to_ui`/`_remember_for_undo`, and HEAD is missing
`scriptorium.spec` and `icon/`.
