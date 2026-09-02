# Scriptorium Roadmap

**Read this file, `MEMORY.md`, and `AGENTS.md` at the start of every session.**
When Mark says "lets get started", that is the cue to open these three files
before doing anything else.

Current shipped version: **2.24** (v2.9 bug-fix pass, v2.10 visual/UX
polish, v2.11 three-tone picker, v2.12 persisted user presets, v2.13 backend
retry transport, v2.14 hand-testing fixes, v2.15 Explorer drag-and-drop,
v2.17 readability metrics + shortcuts reference, v2.18 house-style
avoid-list, v2.19 headless batch/CLI mode, v2.20 in-session revision
history, v2.16 rich `CF_HTML` clipboard diff (shipped as build `2.21`),
v2.22 tray/start-up lifecycle gating, v2.23 drop-safety/preset-repair/
export/reading-time/clipboard polish, v2.24 protected-content fidelity
audit — see those sections below). All five notes_019 proposals and
notes_016's full original proposal set shipped by build 2.21, clearing the
backlog for the first time since notes_001 opened it; v2.22 closed a fresh
hand-testing defect (notes_020) found immediately after. notes_021's
second-generation hardening pass is under way (v2.23/v2.24 above;
cancellable retry transport remains — see v2.23's "notes_021 delivery
plan" note).

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
- [x] Two selected tones show correct dominant/supporting phrasing, and a
      real run against the live backend changes wording/register only — no
      new facts, figures or invented detail (check combinations involving
      Detailed or Persuasive specifically). **Tested against Ollama
      (llama3.1:8b), not Claude** — Mark's configured Claude API key is
      identity-linked and needs an `anthropic-workspace-id` header
      `call_anthropic()` doesn't send; no workspace ID was available in the
      console to add it (pre-existing, unrelated to v2.4 — see "Deferred"
      below). Direct+Detailed came back clean on the first try. **Persuasive
      +Confident did not** — it added unsupported evaluative adjectives
      ("cutting-edge", "remarkable", "ingenious design") and quietly
      loosened "lasts three months" to "up to three months" (word count
      20→39). Tightened `TONE_INSTRUCTIONS["Persuasive"]` and the shared
      closing guard in `build_tone_instruction()` to explicitly name
      evaluative/promotional adjectives and claim-scope changes as
      forbidden, not just "facts" and "certainty". Re-ran the same case 3x
      after the fix: no more scope-loosening or multi-adjective pile-ups,
      but a single mild evaluative adjective ("latest"/"significant"/
      "durable", "innovative"/"long-lasting design") still slipped in on 2
      of 3 attempts — real, if reduced, residual risk on this local model.
      Persuasive should be treated as the tone needing the most scrutiny in
      review before Accept; worth re-checking against Claude once its
      workspace-id issue is resolved, since a flagship model may follow the
      bounded instruction more reliably than an 8B quantised local one.
      Result stands regardless: this is exactly why the app never applies a
      revision without review — see `_on_success()`'s diff pane.
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
- [x] Spot-check the Lawyer and Engineer roles against real source text:
      no invented legal interpretation, obligation, or technical conclusion
      not already present. **Tested against Ollama (llama3.1:8b)**, same
      caveat as above re: Claude. Both clean — Engineer (pump-failure
      source) made only a tense tweak, no diagnosed cause added; Lawyer
      (tenancy-notice source) only inserted a missing article, no new
      obligation or interpretation.

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
   destroying when the option is on. Implemented with **`pystray`+`Pillow`**
   (Mark's choice over the ctypes path, to avoid hand-rolling a Win32
   message loop) — both optional: `TRAY_AVAILABLE` gates the Settings
   checkbox and is re-checked at every `_on_close()`, so a config with
   `minimise_to_tray: true` but the packages missing still just quits
   normally rather than trapping the user. `winreg` `HKCU\...\Run` entry
   (`set_autostart()`) launches `pythonw.exe scriptorium.py --minimised`
   from source or the `.exe` directly when frozen. The tray icon only
   exists while the window is hidden — created on minimise, torn down on
   restore or Quit — never left running in the background otherwise.
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
- [x] Close the window with "minimise to tray" on: window vanishes, process
      stays alive, tray icon appears; left-click restores and focuses it.
      Verified two ways: programmatically (driving the real `Scriptorium`/
      `pystray.Icon` objects end to end — `_on_close()` withdraws the
      window and a real tray icon appears; the icon's own "Show
      Scriptorium" callback deiconifies/refocuses and tears the icon
      down), **and by an actual click** — Mark restored a real minimised
      instance himself (launched via the literal registered autostart
      command, see below) by clicking its tray icon; confirmed
      `WindowVisualState: Normal`, `IsOffscreen: False`, on-screen at its
      normal geometry afterwards via UI Automation.
- [x] Tray Quit ends the process and removes the icon; Alt+F4 with the
      option off quits normally as before. Verified both paths
      programmatically (`_tray_quit` → real `destroy()`; `_on_close()` with
      `minimise_to_tray` off → real `destroy()`), plus the safety case:
      `minimise_to_tray: true` but `TRAY_AVAILABLE` false (packages
      missing) still quits normally rather than vanishing with no icon.
- [x] Log off/on (or reboot) with "start with Windows" ticked: app starts
      minimised, no console flash, `pythonw.exe` confirmed via Task
      Manager. **A real logon/reboot event itself was not triggered** —
      doing so would have ended the working session — but the actual
      registered command was run for real as the strongest available
      proxy: `set_autostart(True)` writes the exact
      `pythonw.exe ... --minimised` command line to `HKCU\...\Run`
      (confirmed via `winreg` read-back); launching that exact command
      line directly produced a `pythonw.exe` process with
      `MainWindowHandle: 0` and no title — genuinely started withdrawn,
      no window ever shown, no console flash — and clicking its tray icon
      (see above) restored it correctly. The only thing not literally
      exercised is Windows itself invoking the `Run` entry at a real
      logon, which is a well-established OS mechanism once the entry
      itself is confirmed correct.
- [x] Untick "start with Windows" in Settings; `HKCU\...\Run` value is gone.
      Verified against the real registry (`winreg` read after
      `set_autostart(False)`, and via a full Settings-dialog save cycle) —
      value confirmed removed both times, registry left clean afterwards.
- [x] Packaged `.exe` shows the Scriptorium icon in Explorer/taskbar and
      populated FileDescription/ProductVersion fields. Verified against a
      real `pyinstaller scriptorium.spec` build: `Get-Item ... .VersionInfo`
      shows the correct FileDescription/ProductVersion/CompanyName, and
      `System.Drawing.Icon.ExtractAssociatedIcon` confirms the icon
      resource is present. The packaged `.exe` (with the new `winreg`/
      `pystray`/`Pillow` imports) launches cleanly with no crash.
- [x] Deleting/renaming `%LOCALAPPDATA%\Scriptorium` and relaunching
      produces a dedicated fallback folder, not a loose file in `~`.
      Verified by simulating an `os.makedirs` failure on the primary path:
      `_config_dir()` now falls back to a same-named `Scriptorium`
      subfolder under the user's home directory, not a bare loose file,
      and only falls all the way back to a loose file if that second
      attempt also fails.
- [x] First run of the `.exe` after having used the source version offers
      the import prompt; declining leaves both configs untouched. Verified
      with a temp candidate config and a patched `CONFIG_PATH`/
      `sys.executable`: declining leaves the candidate file byte-for-byte
      unchanged and does not import its values into the live config;
      accepting imports the API key/mode/role/tones (applied to the live
      toolbar immediately, not just on next restart) while still leaving
      the source file untouched; a second launch does not ask again.

**One incident during hand-testing**: an early save-cycle test ran against
the *real* `scriptorium_config.json` instead of a patched path and briefly
flipped `minimise_to_tray`/`start_with_windows` to `true` in it (and wrote
a real, immediately-removed `HKCU\...\Run` entry). Caught and reverted
within the same session — confirmed both the config file and the registry
were restored to their prior (off) state, with the API key untouched
throughout. Every test after this one explicitly patches `CONFIG_PATH` to
a temp file.

---

## v2.6 — Bug Diagnosis & Resolution Session ✅ shipped 2026-09-01

**Goal:** this release was deliberately **not** pre-scoped with a fixed
feature/fix list, per Mark's designation — a dedicated diagnosis session
against whatever state v2.1–v2.5 actually left the app in. In practice it
was triggered by two new independent review notes (`notes_014`, Gale;
`notes_015`, Antigravity) landing the same day v2.5 shipped, both rediscovering
real defects in v2.5's own new tray/icon code — see "Source notes reference"
below.

**Step 1 (regression-verify v2.1–v2.5)** was *not* redone item-by-item — those
checklists were verified the same day with concrete, itemised evidence
(memory: `project_v24_status`). Instead this session spot-checked only what
its own changes touched: the packaged `.exe` icon/version metadata and the
tray minimise/restore path (both rewritten below), plus the new
single-instance behaviour.

**Step 2 (S1/S2)** — both notes_010/011's suspicions, and notes_015's own
"Confirmed"/"Addressed" verdicts on them, were re-tested directly against the
running widget/Tk code rather than taken on faith:
- **S1 dismissed.** Built the real `SettingsDialog` with a synthetic
  out-of-list `anthropic_model`, called the real `_save()`, inspected the
  resulting cfg. The custom value survived untouched end-to-end.
  `CTkOptionMenu` only calls `variable.set()` from its own dropdown-click
  callback or an explicit `.set()` — never from construction or `.get()` —
  and `normalise_config()` never touches `anthropic_model`. notes_015's
  "Confirmed" verdict (its Finding 4) does not hold up against the running
  code. No fix applied.
- **S2 not reproducible on this Tk build.** A throwaway `tk.Text` with a
  selection, caret deliberately moved away from `sel.first`, then the exact
  `delete("sel.first","sel.last")` call `paste_original()` uses: the `insert`
  mark correctly collapsed to the deletion start every time (documented Tk
  mark semantics). Hardened defensively anyway (explicit `sel.first` capture +
  `mark_set`) since it's a free two-line change protecting other Tk/platform
  builds — not claimed as a bug fix.

**Step 3/4 (triage and fix)** — confirmed-real bugs fixed, all hand-tested
against the live running code (not just read), each in its own isolated
process per this project's CTk multi-instance-interference gotcha:

1. **Icon assets desynced from disk** (both notes, HIGH). Mark had renamed
   `icon/icon-96.ico`/`icon-96.png` to `icon/Scriptorium-256.ico` +
   `Scriptorium-96.ico` outside git; `_minimise_to_tray()` and
   `scriptorium.spec` still pointed at the old filenames, so tray-minimise
   from source threw `OSError` and silently aborted. Fixed: new
   `_apply_window_icon()` sets the real title-bar/taskbar icon (verified via
   `WM_GETICON`/`GetClassLongPtrW` returning non-null handles, both from
   source and on the rebuilt packaged `.exe`); `_minimise_to_tray()` now tries
   `Scriptorium-96.ico` then `-256.ico`; `scriptorium.spec` updated to match
   and rebuilt clean (`ProductVersion 2.6.0.0`, icon resource present).
2. **No single-instance guard** (both notes, MODERATE). Added the
   `ctypes`-based named mutex (`Local\ScriptoriumSingleInstance`) +
   restore-event (`Local\ScriptoriumRestore`) design both notes proposed.
   **Found a real bug while testing this, not in either note**: the restore
   listener's daemon thread can receive the event before `Scriptorium.__init__`
   has actually reached `mainloop()`; `_post_to_ui`'s unguarded
   `winfo_exists()` then raises `RuntimeError: main thread is not in main
   loop` (not `TclError`) — uncaught, which killed the daemon thread
   permanently, silently disabling the restore mechanism for the rest of that
   process's life. Fixed by widening `_post_to_ui`'s except clause to include
   `RuntimeError`, and wrapping `_watch()`'s per-iteration body so no
   transient error can kill the listener thread. Verified with two genuinely
   separate processes: a second launch while the first is up correctly
   detects the mutex, signals, and exits without constructing a `Scriptorium`;
   the first instance restores correctly once its signal arrives after
   `mainloop()` is running, and — critically — no longer crashes if the
   signal arrives during the first instance's own startup window.
3. **Revision word-count delta computed against the live buffer**
   (notes_015 Finding 8). `_refresh_status()` now diffs against
   `self._result_source` (the text the revision was actually generated from,
   already used correctly by `_revision_is_stale()`) instead of the
   possibly-since-edited `original_box` contents. Verified: process a source,
   edit Original afterwards, confirm the delta still reflects the original
   request.
4. **Import encoding fallback** (notes_015 Finding 6). `import_file()`'s
   plain-text branch now tries `utf-8-sig` first (handles both BOM and plain
   UTF-8, stripping the BOM either way) and falls back to `cp1252` instead of
   retrying `utf-8-sig` after `utf-8` (which failed identically). Verified
   against a real BOM-prefixed UTF-8 file and a real CP1252 file with a curly
   apostrophe — both load clean text.
5. **`SettingsDialog` missing `transient()`** (notes_015 Finding 7). Added
   `self.transient(master)`; verified the dialog's `wm transient` now points
   at the main window.

### Acceptance checklist
- [x] Source run shows `Scriptorium-256.ico` in the title bar/taskbar (Win32
      `WM_GETICON`/class icon handles all non-null; verified live).
- [x] Minimise to tray from source succeeds (no `OSError`), real `pystray.Icon`
      created, window withdrawn; restore tears the icon down and un-withdraws.
- [x] Packaged `.exe` rebuilt from the updated spec: `FileDescription`/
      `ProductVersion`/`CompanyName` correct (`2.6.0.0`), icon resource
      extracts successfully, real window (found by title, not
      `Get-Process`'s unreliable `MainWindowHandle` — same automation gap as
      documented for this Tk app) has a non-null icon handle.
- [x] Second launch while one is running: existing instance restores via the
      real named-event signal, second process exits without constructing a
      `Scriptorium`, no second tray icon. The early-startup race found during
      testing (see above) no longer crashes the listener thread.
- [x] Process text, edit Original before acting on the revision: status bar's
      delta still reflects the original source text, not the edited buffer.
- [x] Import a UTF-8-BOM `.txt` and a CP1252 `.txt`: both load clean text.
- [x] Settings dialog's `wm transient` points at the main window.
- [x] S1 and S2 resolved (dismissed, with evidence, above) — no longer open
      suspicions.

**Incident during this session**: a stray `Scriptorium.exe` (both bootloader
and real process) was already running before the packaged-`.exe` rebuild step
and held a lock on `dist\`. It predated this session and its provenance was
unknown, so Mark was asked before it was closed (confirmed no unsaved work at
risk, since nothing in this app persists except via Export) — closed cleanly,
then the rebuild proceeded.

---

## v2.7 — Always-on-top & Copyable Change Summary ✅ shipped 2026-09-01

**Goal:** the two small, genuinely discretionary features both notes_014 and
notes_015 independently converged on. Deliberately excludes notes_014's
drag-and-drop proposal (see "Deferred" below) and everything else in either
note, which v2.6 already covered as bug fixes.

1. **Always-on-top toggle** (both notes). `DEFAULT_CONFIG["always_on_top"]`;
   a `SettingsDialog` checkbox under "Startup & window behaviour"; applied via
   `self.attributes("-topmost", ...)` in `__init__` and `_after_settings()`.
   Off by default; does not interact with tray minimise (a topmost window
   that's withdrawn stays withdrawn).
2. **Copyable change summary** (both notes). `summarise_diff()` reuses the
   `_tokenise`/`difflib.SequenceMatcher` machinery `render_diff()` already
   pays for — a one-line British-English word-level inserted/deleted/replaced
   summary. "Copy summary" button beside "Copy revision"; `Ctrl+Shift+M`
   shortcut.

### Acceptance checklist
- [x] Toggle "Keep Scriptorium on top" in Settings; window pins/releases
      immediately; setting persists across restart; a topmost window that's
      minimised to tray still withdraws normally. Verified against the real
      `SettingsDialog`/`Scriptorium.attributes("-topmost")`: off by default,
      ticking + Save applies immediately and persists in cfg.
- [x] Process a real edit; "Copy summary" and Ctrl+Shift+M both copy a
      correct one-line summary; an unprocessed pane shows a
      "nothing to summarise" status instead of copying garbage. Verified:
      clipboard held the exact `summarise_diff()` output ("2 words inserted,
      1 replaced" for a real sample edit), status bar confirmed it, and the
      no-revision case showed "nothing to summarise" without touching the
      clipboard or raising.

---

## v2.8 — Hand-testing fixes: layout, tray lifecycle, clipboard, packaging ✅ shipped 2026-09-01

**Goal:** four issues Mark found hand-testing v2.7 (the packaged `.exe`,
screenshots `1.jpg`/`2.jpg`), none from the notes backlog.

1. **Action bar overflow** — thirteen buttons on one `pack(side=...)` row
   overran the fixed 1180px window (≈1200px of buttons for ≈1156px of
   space) and overlapped in the middle; the "Copy" button rendering as an
   unreadable sliver next to Undo was that overlap, not a bug in Copy
   itself. Split into two rows: review/process actions (Process through
   Undo) on row 1, Original-pane and file actions (Paste, Copy, Export,
   Import, Clear) on row 2. Both "Copy" (original text) and "Copy summary"
   (diff summary) are kept — they copy different things — now that neither
   is cramped.
2. **Minimise/close semantics swapped** — previously the native minimise
   button did a plain OS iconify (an "open, minimised" taskbar entry) and
   only the titlebar close (X) consulted `minimise_to_tray`, which meant
   enabling tray made X stop being able to quit at all except via the tray
   icon's own menu. Now: the minimise button (`<Unmap>`, filtered to the
   window itself and an `iconic` state check) sends straight to the tray
   when `minimise_to_tray` + `TRAY_AVAILABLE`; the close button always ends
   the process via `_quit_app()`, which also tears down any live tray icon
   first. Settings checkbox label updated to match ("Send to the system
   tray when minimised").
3. **Right-click copy/paste** — both `original_box` and `revised_box`
   (Ctrl+C/Ctrl+V already worked; this is the point-and-click affordance)
   get a `<Button-3>` context menu: Copy (enabled only with a selection,
   works on the read-only `revised_box` too since selection/copy isn't
   blocked by Tk's `state=disabled`) and, Original only, Paste (enabled
   only when the clipboard holds text). Paste replaces a selection if
   present, otherwise inserts at the clicked point — this is what makes
   right-click-Paste on empty space actually land where you clicked.
4. **Root-cause fix for "Network error reaching the Claude API: [Errno 2]
   No such file or directory: ...\_MEI#####\base_library.zip"** — confirmed
   this only happens against the packaged `.exe` (the `_MEI` path is
   PyInstaller onefile's runtime extraction folder under `%TEMP%`; Python
   lazily pulls some stdlib modules from `base_library.zip` there on first
   use, e.g. the first network request, not at startup). Root cause: a
   generic "sweep `%TEMP%`" cleanup pass — Mark has three such tools
   installed (Privacy Eraser, Wise Care 365, WinTools.net) plus his own
   `Clean-Temps-and-Caches.bat` — deletes the live extraction folder out
   from under the still-running process. Mark's own script's "does NOT
   touch ... Scriptorium" comment doesn't actually protect it: the skip
   check only matches a directory argument whose own path contains
   "\Scriptorium", and it calls `robocopy /MIR` against `%TEMP%` itself
   (which doesn't match), wiping everything nested inside — including a
   `_MEI*` folder unrelated to Scriptorium by name. Fixed in
   `scriptorium.spec`: `runtime_tmpdir` now points at
   `%LOCALAPPDATA%\Scriptorium\runtime` instead of the default shared
   `%TEMP%` — the same directory the app already uses for its own config,
   which *does* match his script's existing exclusion and sits outside
   what "temp file" cleaners generally target. No `scriptorium.py` change
   needed; `APP_VERSION` bumped to "2.8" and `version_info.txt` to match.

### Acceptance checklist
- [x] Both action-bar rows fit the window with margin to spare. Verified
      programmatically against the real widget tree: row 1 (8 buttons)
      requests 780px, row 2 (5 buttons) 420px, against 1156px available on
      each row (window is 1180px, 12px padding each side) — no overlap.
- [x] Minimising (native button) with tray enabled sends the app straight to
      the tray with no taskbar entry; with tray off or unavailable it's a
      plain OS minimise as before. Closing (X) always ends the process and
      clears any tray icon. Verified against the real `Scriptorium`/
      `pystray.Icon` objects, both with `minimise_to_tray` on (iconify →
      real tray icon created, state `withdrawn`; `_finish_tray_restore()` →
      icon gone, state `normal`; re-minimise then `_on_close()` → tray icon
      cleared, `destroy()` called) and off (iconify → no tray icon, state
      `iconic`, i.e. unchanged default behaviour).
- [x] Right-click Copy works on a selection in both panes, including the
      disabled `revised_box`; right-click Paste on empty Original space
      lands at the click point; both disable their menu item when there's
      nothing to act on. Verified by calling the real handlers directly
      (`_copy_text_selection`, `_paste_at_click`) against real `CTkTextbox`/
      `tk.Text` widgets with real selections/clipboard content.
- [x] Packaged `.exe` rebuilt from the updated spec (`pyinstaller
      scriptorium.spec`, 2.8.0.0 confirmed via `VersionInfo`); launched for
      real and confirmed its extraction folder is
      `%LOCALAPPDATA%\Scriptorium\runtime\_MEI######`, not anywhere under
      `%TEMP%`, and survives a 20+ second soak with the process idle and
      responsive (one transient "folder not found" reading during this
      check turned out to be this session's own `Get-ChildItem` call
      racing the AV's first-scan of the freshly extracted folder, not a
      real deletion — re-checked and stable afterwards). Real config file
      (`scriptorium_config.json`) confirmed byte-identical before/after —
      this test never touched Settings.

---

## v2.9 — Bug-fix pass ✅ shipped 2026-09-02

**Goal:** three new independent review notes landed together on 2026-09-02
(notes_016 Mark/Codex — architecture proposals for v2.9+; notes_017 Lynne —
UI/UX visual audit; notes_018 Zoe — a fresh static bug hunt against v2.8).
Rather than one grab-bag release, the work was split: this version closes
every concrete, confirmed bug notes_018 found (all low individual risk, all
worth fixing on their own merits); notes_017's visual polish and notes_016's
five architecture proposals are scoped separately below (v2.10, v2.11/v2.12/v2.13/v2.15/v2.16) since
bundling correctness fixes with new-feature/visual work would make either
harder to verify in isolation.

1. **`always_on_top` omitted from boolean normalisation** (notes_018 Bug 1).
   `normalise_config()`'s stringy-boolean clamp named seven keys but not
   `always_on_top`; a hand-edited `"always_on_top": "false"` is
   Python-truthy, so the window would pin itself on top with Settings'
   checkbox showing unticked. Added to the clamp list.
2. **Win32 mutex/event handles not validated** (notes_018 Bug 2 + Suspicion
   S2). `_claim_single_instance()` and `_start_restore_listener()` never
   checked for a NULL `CreateMutexW`/`CreateEventW` handle, and
   `WaitForSingleObject`'s return was ignored — a failed `CreateEventW`
   would busy-spin the restore-listener thread at 100% CPU, flooding the Tk
   queue. A failed `CreateMutexW` would silently disable the single-instance
   guard instead of refusing to start. New `_kernel32()` helper declares
   proper `HANDLE`/`BOOL`/`DWORD` argtypes/restype (closing S2's 64-bit
   `HANDLE` truncation risk from the default `c_int` restype at the same
   time) and both call sites now treat a NULL handle as failure, not
   success; the restore-listener loop stops instead of spinning on
   `WAIT_FAILED`.
3. **`runtime_tmpdir` baked in at build time, not run time** (notes_018 Bug
   3 — the most consequential fix in this pass). The v2.8 onefile temp-dir
   fix computed `runtime_tmpdir` with `os.environ.get("LOCALAPPDATA", ...)`
   inside `scriptorium.spec`, which runs when PyInstaller *builds* the
   `.exe` — baking the builder's own account path into the bootloader.
   Anyone else running `dist\Scriptorium.exe` (or the same user after a
   profile change) would extract into the wrong, likely inaccessible,
   directory. Fixed by keeping `runtime_tmpdir` as the literal string
   `%LOCALAPPDATA%\Scriptorium\runtime` so PyInstaller's bootloader expands
   it itself at run time, per-user, as documented behaviour.
4. **Module docstring version string stale** (notes_018 Bug 4) — folded into
   the real version bump to 2.9 rather than fixed as a one-off.
5. **Tray-icon load failure was `print()`-only** (notes_018 Bug 5, partial —
   the tray-icon case only; the two "automatic save refused" cases the note
   flagged as optional were left as-is). `_minimise_to_tray()` now shows a
   `messagebox.showwarning` when neither `.ico` loads, since `print()` is
   invisible in the packaged `.exe` (`console=False`).
6. **`load_config()` rejected a BOM-prefixed config as unreadable** (notes_018
   Bug 6). Changed the read encoding from `utf-8` to `utf-8-sig`, matching
   `import_file()`'s existing BOM handling; `save_config()` still writes
   plain `utf-8` (Python's `json.dump` output is already BOM-free).
7. **Example config missing `always_on_top`** (notes_018 Bug 7). Added to
   `scriptorium_config.example.json`, matching `DEFAULT_CONFIG`'s key order.
8. **Unrecognised `backend` silently coerced to the cloud** (notes_018
   Suspicion S1 — raised as a product decision, not a confirmed defect, but
   fixed here on existing precedent rather than deferred). `normalise_config()`'s
   generic enum-clamp loop included `"backend"`, so a hand-edited typo (e.g.
   `"Ollama"`, `"local"`) was silently rewritten to `"anthropic"` *before*
   `run_backend()`'s own fail-closed check — added in v2.1 for exactly this
   scenario — ever saw it; `run_backend()`'s docstring already admitted this
   ("load_config() already normalises backend ... so reaching the else
   branch here means cfg was built some other way"). This is the same
   privacy failure mode v2.1 was built to close (status bar and actual HTTP
   dispatch disagreeing about whether text leaves the machine), reintroduced
   through the config-normalisation layer rather than `run_backend()`
   itself. `backend` is no longer in the enum-clamp loop — a missing key
   still defaults to `"anthropic"`, but a present-and-invalid value is left
   alone so `run_backend()`'s existing `BackendError` actually fires.
   `_refresh_status()` also no longer mislabels an unrecognised backend as
   "local"/Ollama in the status bar.

**Not fixed, deliberately** (notes_018 Suspicion S3): Reject does not abort
an in-flight HTTP call — the daemon thread stays blocked in `urlopen()` even
after `_invalidate_inflight()` bumps `_request_id`. Noted by the reviewer
only so it isn't mistaken for a UI-state bug; the actual requirement (stale
results cannot overwrite the UI, and the UI itself unlocks immediately) is
already met by the existing request-id mechanism. Aborting the socket itself
would need a different HTTP stack — not worth it for a cosmetic
connection-count concern.

### Acceptance checklist
- [x] Hand-edited `"always_on_top": "false"` normalises to Python `False`,
      `"true"` to `True`, matching the Settings checkbox. Verified via
      isolated `normalise_config()` calls against both stringy values plus
      a real `bool`.
- [x] A mistyped `backend` (e.g. `"Ollama"`) survives `normalise_config()`
      unchanged and `run_backend()` raises `BackendError` for it; a
      genuinely absent `backend` key still defaults to `"anthropic"`; a
      valid value is untouched either way. Verified against the real
      functions, all three cases.
- [x] A UTF-8-BOM-prefixed config file loads correctly (not flagged
      unreadable, values actually applied). Verified against a real temp
      file with a literal BOM prefix and `load_config()`/`CONFIG_PATH`
      patched to point at it.
- [x] `_kernel32()`'s `CreateMutexW`/`CreateEventW` are `HANDLE`-typed; a
      simulated NULL `CreateMutexW` handle makes `_claim_single_instance()`
      return `False`, not `True`. Verified via a stub kernel32 (a genuine
      OS-level `CreateMutexW` failure isn't practically triggerable from a
      test).
- [x] `runtime_tmpdir` is embedded in the rebuilt `.exe` as the literal
      `%LOCALAPPDATA%\Scriptorium\runtime` token, not an expanded path.
      Verified by scanning the built binary for the literal string.
      Launched the rebuilt `.exe` for real: extracted to
      `%LOCALAPPDATA%\Scriptorium\runtime\_MEI######`, survived a 15-second
      soak with both the bootloader and child process alive and
      `Responding: True`. Full cross-user portability (a second Windows
      account) was not exercised — impractical in-session — but the
      binary-level confirmation that the token is genuinely unexpanded is
      the direct fix for the root cause notes_018 identified.
- [x] Rebuilt `.exe`'s `FileVersion`/`ProductVersion` read `2.9.0.0`.
- [x] Tray-icon load failure shows a `messagebox.showwarning` and leaves
      `tray_icon` as `None` (fails safe, window stays open) instead of only
      printing. Verified by patching `resource_path()` to a nonexistent
      directory and `messagebox.showwarning` to a recording stub against the
      real `Scriptorium`/`_minimise_to_tray()`.
- [x] `ast.parse()` syntax check clean; full regression pass (WRITING_PRESETS
      validity, `DEFAULT_CONFIG` round-trip through `normalise_config`,
      `ROLES`/`TONES` membership, `validate_tones`) all still pass; real
      `Scriptorium()` constructs and destroys cleanly from source with no
      exception. The real `scriptorium_config.json` (holds the live API key)
      was confirmed byte-identical (same mtime) after every test — none of
      this session's tests wrote to it.

**Incident, handled correctly this session**: a stray `Scriptorium.exe` (v2.8,
both bootloader and child process) was already running before the
packaged-`.exe` rebuild step, predating this session. Mark was asked before
it was closed (nothing in the app persists except via Export) — confirmed,
closed cleanly, rebuild proceeded.

---

## v2.10 — Visual & UX polish ✅ shipped 2026-09-02

**Goal:** notes_017 (Lynne, UI/UX audit against v2.8) proposes a token-based
visual pass — matched pane typography, better diff contrast, a dismissible
notice banner, a Working… progress indicator, dialog Escape/positioning, and
Claude/Ollama-labelled backend selection instead of raw `anthropic`/`ollama`
ids. Pure visual/UX changes — no prompt or content-generation surface is
touched, so [[mark_meaning_preservation_priority]] doesn't apply here the way
it will for v2.11's three-tone work. Cherry-picked from notes_017's full
proposal for value-to-risk; the note's own priority order (§5) is followed.

1. Match pane typography, padding and background between Original and
   Revised (notes_017 §1.2 / §2.2/3.3) — the single biggest "doesn't look
   like one app" tell.
2. Diff tag colour/contrast pass — background fills, not just foreground ink,
   and a slightly brighter deleted-red (notes_017 §1.3/2.3/3.3) since the
   current AA-only red is a tight pair on a dim panel.
3. Dismissible notice/ambiguity banner replacing the disabled `CTkTextbox`
   (notes_017 §1.6/2.7/3.5) — adds a Dismiss control and fixes the
   selection-blocked-on-some-CTk-versions issue.
4. Working… progress bar + Process-button pulse (notes_017 §1.5/2.6/3.4) so a
   long Ollama call doesn't look frozen.
5. Dialog Escape binding, `WM_DELETE_WINDOW`, and same-monitor-as-parent
   positioning for `TonePickerDialog`/`SettingsDialog` (notes_017 §1.7/2.8/3.6);
   Settings body wrapped in a `CTkScrollableFrame` so 150% DPI still reaches
   Save.
6. Claude/Ollama labels in the Settings backend selector, mapped back to the
   internal `anthropic`/`ollama` ids (notes_017 §1.7/2.8).

Deliberately **not** carried into v2.10: the two-row-toolbar-wrap-at-920px
change (notes_017 §1.4/2.4/3.7) — real value is marginal at the app's actual
920px minimum width today, revisit only if Mark resizes down that far in
practice; character-level diff tokenisation, which notes_017 itself
recommends against (§1.3/§5, word-level already matches how a copy-editor
scans a British spelling change).

### Acceptance checklist
- [x] Both panes render at the same face/size/padding. Verified against the
      real widget tree: `original_box.cget("fg_color"/"text_color")` and
      `revised_box.cget("background"/"foreground"/"font")` all match the
      shared `PANE_BG`/`PANE_FG`/`PANE_FONT` tokens exactly.
- [x] Diff insertions/deletions use a background fill plus foreground ink,
      not colour-only. Verified: `revised_box.tag_cget("changed"/"deleted",
      "foreground"/"background")` match `DIFF_INS_FG`/`DIFF_INS_BG`/
      `DIFF_DEL_FG`/`DIFF_DEL_BG` exactly.
- [x] The notice banner has a working Dismiss button; list text is a
      selectable `CTkLabel`, not a disabled `CTkTextbox`. Verified against
      the real `_show_ambiguities()`: the banner attaches/detaches from the
      packer correctly for a populated list, an empty list, and a simulated
      Dismiss click (`winfo_manager()` used as the pack-state probe rather
      than `winfo_ismapped()`, which reads false for any widget under a
      root that was never `mainloop()`-mapped — a known artefact of this
      project's construct-without-mainloop testing style, not a real
      packing failure; confirmed both ways report identically once the app
      actually runs).
- [x] A busy Process call shows visible motion: an indeterminate
      `CTkProgressBar` plus a colour-pulsing Process button, not just a
      static "Working…" label. Verified against the real `_set_busy()`/
      `_pulse_process()`: the progress bar attaches/detaches with busy
      state, the pulse job is scheduled while busy and cancelled when not,
      and the Process button's colour actually changes on a simulated tick.
- [x] Escape closes both `TonePickerDialog` and `SettingsDialog` (confirmed
      a real `<Escape>` binding exists on each via the live objects); both
      also position via `position_over_parent()` on `after_idle`. Real
      multi-monitor positioning wasn't hand-verified (single-monitor
      session) — the centring maths itself was exercised via the same
      binding test, not just read.
- [x] Settings remains fully reachable at a reduced height: geometry
      520×640 (down from 780 tall), `resizable(False, True)`, `minsize(480,
      420)`, and the Save/Cancel row is packed on the dialog itself
      (`side="bottom"`) before the scrollable body, so it never scrolls
      away regardless of content height.
- [x] Settings shows "Claude"/"Ollama" in the backend selector while the
      saved config still stores `anthropic`/`ollama`. Verified end-to-end
      against the real dialog and a real `_save()` call through a temp
      config path: display defaults to "Claude" for a stored `"anthropic"`
      value, switching the segmented button to "Ollama" correctly disables
      the API key field, and the file written by `_save()` contains the
      internal id `"ollama"`, never the display label.
- [x] `ast.parse()` clean; full v2.9 regression suite plus a dedicated
      28-check live-object test for every v2.10 change (listed above) all
      pass; rebuilt packaged `.exe` confirmed `FileVersion`/`ProductVersion`
      `2.10.0.0`, launched for real, alive and `Responding: True` after an
      8-second soak. Real `scriptorium_config.json` confirmed untouched
      (unchanged mtime) throughout.

---

## v2.11 — Three-tone picker ✅ shipped 2026-09-02

**Goal:** notes_016 §2.3/3.4 — raise `TONE_PICKER_LIMIT` to
`MAX_SELECTED_TONES` (3, already supported by the data model per v2.4's
deliberately conservative rollout), add the `Neutral`/`Persuasive` conflict
pair, and a dominant/supporting/accent prompt hierarchy with an explicit
fidelity-first precedence ladder. **Subject to
[[mark_meaning_preservation_priority]]**: this directly touches prompt
construction, so it needed the same live-model calibration discipline v2.4
used for two-tone — and, as with v2.4's Persuasive+Confident finding, the
first calibration pass found real embellishment bugs that were then fixed
and re-verified rather than shipped as-is.

1. `TONE_PICKER_LIMIT = MAX_SELECTED_TONES` (was hard-coded to 2).
2. `TONE_CONFLICTS` gains `frozenset({"Neutral", "Persuasive"})`; previously-
   legal pairs (Friendly+Formal, Direct+Diplomatic, Confident+Empathetic)
   confirmed to remain legal, per notes_016's own reasoning that these are
   blendable rather than truly contradictory.
3. `build_tone_instruction()` rewritten for three tiers: single-tone keeps
   the plain "target tone" phrasing unchanged; two-tone keeps the existing
   dominant/supporting phrasing unchanged; three-tone adds "...and X only
   as a light accent" plus an explicit precedence ladder ("factual fidelity
   and meaning; the selected editing mode; dominant; supporting; accent")
   and an instruction to weaken or drop the accent tone entirely rather than
   let it change content, certainty or scope.
4. `TonePickerDialog`'s explanatory label updated to describe the third tier
   as "a light accent — not an equal third voice."

### Live-model calibration (Ollama, against `scriptorium_config.json`'s
free local backend — no Claude API spend incurred)

Ran `call_ollama()`/`mask_placeholders()`/`restore_placeholders()`/
`build_system_prompt()` end to end (not mocked) against three of
notes_016 §2.3's own suggested calibration cases: Formal+
Concise+Diplomatic on a tense client email, Confident+Direct+Friendly on an
update containing hedged uncertainty, and Neutral+Detailed+Constructive on
a technical incident summary containing names, numbers, negation and a
`[CustomerName]` placeholder. **Originally attempted against `llama3.1:8b`**
(the model v2.4's calibration used, deliberately stronger than a 1B model)
**but this session's machine could not load it** — repeated
"client connection closed / llm server not responding" cycles in the real
Ollama server log, consistent with the box's ~4 GiB free RAM against the
model's ~4.7 GiB weight+buffer footprint. Switched to `llama3.2:3b`
(available locally, loads comfortably) rather than keep retrying a load
that wasn't going to succeed on this hardware.

**First pass found three real, concrete embellishment bugs** — the same
failure mode as v2.4's Persuasive+Confident finding, not hypothetical:
1. Formal+Concise+Diplomatic added *"I want to assure you that I am
   committed to finding a solution"* to a message that only offered to
   discuss the situation — an invented commitment, explicitly forbidden by
   the guard clause already in place, but the model added it anyway.
2. Confident+Direct+Friendly turned *"seems to be going okay so far"* into
   *"progressing as expected"* — replacing a hedge with confirmatory
   wording, directly against Confident's own "without overstating
   certainty" instruction, plus a loss of the source's explicit "haven't
   fully checked yet" / "not 100% sure yet" caveats.
3. Neutral+Detailed+Constructive (Neutral as the *dominant* tone here)
   added *"Fortunately"* before "no data was lost" — an unearned emotional
   interjection, directly against Neutral's own "unembellished... over
   strong emotional... colouring" instruction.

**Fixed, not just reported** (mirroring v2.4's response to its own finding):
- `TONE_INSTRUCTIONS["Neutral"]` now explicitly names forbidden editorial
  interjections ("fortunately", "unfortunately", "importantly").
- `TONE_INSTRUCTIONS["Confident"]` now explicitly forbids replacing a hedge
  word (seems/might/may/could/appears) with confirmatory wording (is/will/
  as expected) unless the source itself already states that certainty.
- The shared closing guard in `build_tone_instruction()` now names
  "reassurances or offers of help that are not already stated in the
  source" as forbidden, with the exact failing example as a concrete
  illustration ("do not add 'I am committed to finding a solution'...").

**Re-ran all three cases after the fix, then the trickiest one
(Confident+Direct+Friendly) twice more** — five real backend calls total
across this pass, eight over the whole session. All five post-fix runs came
back clean: no invented commitments, no hedge-word-to-confirmation swaps
(the model consistently chose "appears"/"appears to be", from the newly
allowed-hedge-words list, not a coincidence), no unearned emotional
interjections. Placeholder round-trip, negation ("not fully
confirmed"/"established"), and all numbers/times (14:32, 8%, 14:47, 1%,
14:52, v2.3.1) survived every run intact. Minor, not-worth-chasing residue
observed and accepted (matching v2.4's own judgement call not to chase
zero residual risk on a small local model): "Friday" was twice generalised
to "the end of this week" — a mild loss of precision, not a fabrication or
contradiction — and one run added "sharp decline" to describe an 8%→<1%
error-rate drop, a characterisation the actual numbers support rather than
an invented fact.

### Acceptance checklist
- [x] Picker permits exactly three tones and shows deterministic selection
      order; a fourth is refused via the non-blocking status-label flash
      added in v2.10. Verified against the real `TonePickerDialog`.
- [x] `Neutral`+`Persuasive` conflicts in any position, including embedded
      in a three-item list; `Concise`+`Detailed` and `Casual`+`Formal`
      still conflict as before; `Friendly`+`Formal`, `Direct`+`Diplomatic`
      and `Confident`+`Empathetic` remain legal. Verified against the real
      `validate_tones()`.
- [x] Single- and two-tone phrasing is byte-identical to pre-v2.11 output
      (no accent/precedence-ladder language leaks into fewer than three
      tones). Verified against the real `build_tone_instruction()`.
- [x] A real three-tone combination changes wording/register only — no new
      facts, invented commitments, or overstated certainty — checked
      specifically against combinations touching Confident and Neutral,
      per this session's own findings. **Tested against Ollama
      (llama3.2:3b)**, not Claude (no live spend incurred; see calibration
      write-up above for why 3b rather than 4.4's 8b this session). Three
      real embellishment bugs found on the first pass, fixed, and
      confirmed absent across five further real backend calls.
- [x] `ast.parse()` clean; full non-live-model regression suite (config,
      presets, role/tone table membership, four-tone-over-limit rejection)
      still passes.

---

## v2.12 — Persisted user presets ✅ shipped 2026-09-02

**Goal:** notes_016 §2.2/3.3 — let a user save the current Mode/Strength/
Role/Tone combination under a name, alongside the three built-in presets,
without touching the prompt or content-generation surface at all (pure
config/UI feature, [[mark_meaning_preservation_priority]] doesn't apply the
way it did to v2.11).

1. `user_presets` config key (default `{}`); `normalise_preset()` validates
   one preset dict against the canonical `MODES`/`STRENGTHS`/`ROLES`/
   `validate_tones()` tables (an old preset naming a role/tone this version
   no longer recognises is dropped wholesale, not partially applied);
   `normalise_user_presets()` validates the whole stored mapping — names
   trimmed, capped at `MAX_PRESET_NAME_LENGTH` (48) and `MAX_USER_PRESETS`
   (30), compared case-insensitively, a name colliding with a built-in
   preset or the `PRESET_MANAGER_LABEL` dropped rather than silently
   shadowing the built-in. Wired into `normalise_config()`.
2. `preset_menu_names(cfg)` (built-ins, then user presets, then the manager
   command) and `resolve_preset(cfg, name)` (built-ins first, then user)
   replace the toolbar's direct `WRITING_PRESETS` reads.
3. `PresetManagerDialog` (new `CTkToplevel`, alongside `TonePickerDialog`/
   `SettingsDialog`): shows the live toolbar state as a summary, saves it
   under a name, or deletes an existing user preset. Uses the same
   `bind_dialog_chrome()`/`position_over_parent()` helpers v2.10 added
   rather than reintroducing an un-dismissable/badly-positioned dialog.
4. `_apply_writing_preset()` routes the manager-label entry to
   `_open_preset_manager()` instead of applying anything;
   `_save_current_preset()`/`_delete_user_preset()`/`_write_user_presets()`
   persist through the same candidate-copy-then-`save_config(force=True)`
   pattern `SettingsDialog._save()` already established, so a failed write
   can't leave the in-memory preset list ahead of disk.

**One deliberate deviation from notes_016's own snippet**, decided during
implementation rather than asked about: the note's `PresetManagerDialog`
routes both the "replace an existing preset?" confirmation and save
failures through `messagebox` calls issued from the *application* method
(`_save_current_preset`), not the dialog. Since `PresetManagerDialog`
already holds the input grab (`grab_set()`) by the time that runs, a
confirmation dialog parented on the *main window* instead of the currently-
grabbed `PresetManagerDialog` is the wrong owner for it — cosmetically
survivable in Tk, but not correct. Restructured so the overwrite
confirmation happens in `PresetManagerDialog._save()` itself (which has
the right `self` to parent it on) before delegating to the app for
validation and persistence; `_save_current_preset()` returns `None` on
success or a message string on failure, shown inline via a status label
rather than a second blocking messagebox stacked on top of an already-
modal dialog — consistent with v2.10's move away from unnecessary blocking
confirmations (the tone-picker limit flash).

### Acceptance checklist
- [x] Loading a config with a missing/malformed/wrong-type `user_presets`
      value (absent key, a list, a dict with an invalid role/mode, a
      conflicting tone pair, a non-dict entry) normalises to a safe result
      rather than crashing. Verified against the real `normalise_preset()`/
      `normalise_user_presets()`/`normalise_config()`.
- [x] A user preset named the same (case-insensitively) as a built-in
      preset or "Manage presets…" is dropped on load, never shadows the
      built-in. Verified directly.
- [x] Saving, overwriting (case-insensitive match, original casing
      preserved, not duplicated), and deleting all persist to the actual
      config file on disk, not just in-memory `self.cfg` — verified via a
      real `_save_current_preset()`/`_delete_user_preset()` call against a
      temp `CONFIG_PATH`, reading the file back after each step.
- [x] The 31st preset and a 49-character name are both rejected with an
      inline message, dialog stays open. Verified against the real
      `MAX_USER_PRESETS`/`MAX_PRESET_NAME_LENGTH` constants.
- [x] A simulated `save_config()` failure leaves `self.cfg` and the on-disk
      file unchanged, and returns an error message rather than silently
      losing the preset. Verified by patching `save_config` to return
      `False`.
- [x] Applying a user preset sets exactly the four documented controls and
      remains hand-editable afterwards, same contract as a built-in preset.
      Verified against the real `_apply_writing_preset()`.
- [x] The overwrite confirmation is parented on `PresetManagerDialog`, not
      the main window (see "deliberate deviation" above) — verified by
      asserting the actual `parent=` kwarg passed to `messagebox.askyesno`;
      declining it leaves the dialog open and nothing is written.
- [x] `ast.parse()` clean; full v2.9/v2.10/v2.11 regression suites re-run
      together, all still pass; a real `Scriptorium()` construct/destroy
      cycle clean. Packaged `.exe` rebuilt, `FileVersion`/`ProductVersion`
      confirmed `2.12.0.0`, launched for real, alive and `Responding: True`.
      Real `scriptorium_config.json` confirmed untouched (unchanged mtime)
      throughout — every persistence test used a temp `CONFIG_PATH`.

---

## v2.13 — Backend retry transport ✅ shipped 2026-09-02

**Goal:** notes_016 §2.5/3.6 — a shared retry seam beneath both
`call_anthropic()` and `call_ollama()` for genuinely transient failures
(dropped connections, a handful of server-side "try again" HTTP statuses),
bounded so it can't retry forever or hide a real, non-transient error.
Moderate risk (touches the request path both backends share) but no
Win32/ctypes involved — pure Python stdlib.

1. `_request_json_with_retries()` — takes a `request_factory` callable (not
   a pre-built `Request`, since a POST body already sent by a failed
   attempt can't be replayed) and opens a fresh request per attempt.
   `MAX_REQUEST_ATTEMPTS = 3` (two retries), `BASE_RETRY_DELAY = 0.75`s
   exponential backoff with up to 250ms jitter, capped at
   `MAX_RETRY_DELAY = 10`s; `Retry-After` (numeric seconds or an HTTP-date)
   honoured and capped at `MAX_RETRY_AFTER = 30`s when present, overriding
   the exponential schedule.
2. Retried: `urllib.error.URLError`, `TimeoutError`, `ConnectionError`,
   `http.client.HTTPException`, and HTTP 429/500/502/503/504/529 for Claude
   or 429/500/502/503/504 for Ollama (Ollama's 404 — an unpulled model — is
   deliberately excluded: retrying the identical request would fail
   identically every time). `HTTPError` checked before the more general
   `URLError` it subclasses. Not retried: any other HTTP status (auth,
   malformed request, missing model), and a 200 response that isn't valid
   JSON — retrying an identical request wouldn't fix a body that will
   never parse.
3. `call_anthropic()`/`call_ollama()` refactored so the raw
   urlopen/HTTPError/URLError/TimeoutError handling moves into the shared
   helper; each backend's own JSON-body construction and response
   interpretation (`_payload_object()`, `stop_reason` check for Claude,
   `_extract_json()`) is unchanged. Both gain an `on_retry=None` parameter;
   `run_backend()` forwards it to whichever backend is configured.
4. `Scriptorium._on_retry_progress(request_id, message)` shows a retry
   status via the existing `_refresh_status(extra=...)` mechanism (same
   pattern as the existing "contacting the model…" busy note), but only
   while `request_id` still matches the live `self._request_id` **and**
   `self.busy` — deliberately does *not* go through `_claim_request()`,
   since this is a progress update mid-request, not its completion.
   `process()`'s worker wires it in via the existing `_post_to_ui()`
   cross-thread hop.
5. Anthropic's `request-id` response header, when present, is appended to
   the final error message so a real support case is traceable.

**One stale-docstring fix along the way**: `run_backend()`'s own docstring
still claimed "`load_config()` already normalises 'backend' to
'anthropic'/'ollama'" — true before v2.9's Suspicion S1 fix, false after
it (that fix deliberately stopped clamping `backend`, precisely so this
function's `else` branch is reachable). Corrected while already touching
this function rather than left to rot further.

### Acceptance checklist
- [x] `_retry_after_seconds()` parses a numeric value and an HTTP-date,
      clamps a negative value to 0 and an oversized one to
      `MAX_RETRY_AFTER`, and returns `None` for garbage or a missing
      header. `_retry_delay()` uses `Retry-After` when present, otherwise
      increasing bounded exponential backoff.
- [x] Fault-injected 429/500/502/503/504/529 (Claude) and 429/500/502/503/504
      (Ollama) via a monkeypatched `urllib.request.urlopen`: recovers within
      `MAX_REQUEST_ATTEMPTS` when a later attempt would succeed; exhausts
      all attempts and raises a specific `BackendError` (never an uncaught
      exception) when it wouldn't. Verified against the real
      `_request_json_with_retries()`, not a reimplementation.
- [x] A non-transient status (401 tested) fails immediately on the first
      attempt, no sleep, no retry.
- [x] Simulated connection reset (`URLError`) and persistent `TimeoutError`
      both retried, both eventually raise a `BackendError` carrying the
      caller-supplied `unavailable_hint` when they don't recover.
- [x] A 200 response that isn't valid JSON is not retried — confirmed only
      one `urlopen` attempt occurs.
- [x] `request-id` response header surfaces in the final error message when
      present.
- [x] `call_anthropic()`/`call_ollama()`/`run_backend()` all correctly
      forward `on_retry`; an invalid backend string still raises
      `BackendError` regardless. Verified end to end, including one real
      (not mocked) `call_ollama()` round-trip against a live local Ollama
      instance to confirm the refactor didn't change real request/response
      handling, only the retry wrapper around it.
- [x] `Scriptorium._on_retry_progress()` updates the status bar only when
      `request_id` matches the current request *and* the app is still
      busy; a stale request_id or a no-longer-busy state is silently
      ignored (confirmed both cases directly, not just the happy path).
- [x] `ast.parse()` clean; full v2.9–v2.12 regression suites re-run
      together, all still pass; a real `Scriptorium()` construct/destroy
      cycle clean. Packaged `.exe` rebuilt, `FileVersion`/`ProductVersion`
      confirmed `2.13.0.0`, launched for real, alive and `Responding: True`.
      Real `scriptorium_config.json` confirmed untouched throughout.

**Not attempted this session** (would need genuinely dropping/throttling a
live connection, not just monkeypatching `urlopen`): a real DNS-failure or
mid-transfer connection-reset scenario against the actual network stack.
The fault-injection coverage above exercises the same code paths those
scenarios would hit (`URLError`/`ConnectionError`/`http.client.HTTPException`
all funnel through the identical retry branch), so this is judged
sufficient rather than a gap requiring a follow-up session — flagged here
for transparency rather than silently assumed equivalent.

---

## v2.14 — Hand-testing fixes: action-bar/status-bar visibility, button layout, autostart ✅ shipped 2026-09-02

**Goal:** three issues Mark found hand-testing v2.13 (screenshot `01.jpg` on
the Desktop, plus a direct question about autostart), none from the notes
backlog. Session opened with an instruction to start v2.15's drag-and-drop
work; that was paused in favour of this hand-testing pass, per the v2.7→v2.8
precedent.

1. **Action bar and status bar were being pushed off-window at the app's own
   default size** — `01.jpg` showed only the toolbar and the Original/
   Suggested panes; both action-bar rows and the status bar were entirely
   absent, not just visually different. Root-caused, not guessed at: a
   throwaway diagnostic build (`Scriptorium()` constructed directly against
   an isolated temp config, `winfo_reqheight()`/`winfo_manager()` read from
   the real widget tree) showed the panes frame's own natural minimum height
   (852px — driven mostly by `revised_box`, a plain `tk.Text` that has never
   had an explicit `height=` set, so it defaults to Tk's built-in 24 text
   rows) exceeds the 760px the default `1180x760` window actually has left
   after the 48px toolbar. `pack()`'s cavity is carved in packing order
   regardless of `side`: the panes frame was packed (and its `expand=True,
   fill="both"` honoured) *before* the action bar/status bar in `__init__`,
   so it claimed the entire remaining cavity for itself the moment it was
   packed, leaving literally nothing for the widgets packed after it —
   confirmed directly: `bar`/`bar2`/`status` all showed `manager="pack"` but
   `winfo_ismapped()` False and an actual height of 1px. This was not a new
   regression introduced by any single version; nothing in v2.9-v2.13's own
   verification ever checked *vertical* fit (v2.8's own check, when the
   action bar was first split into two rows, measured only button-row
   *widths* against the window width — never whether the two rows plus the
   status bar fit *underneath* the panes' own minimum height). Fixed by
   building the action bar and status bar into one `_bottom_frame`, packed
   to `side="bottom"` *before* `_build_panes()` runs, so their combined
   112px is always reserved first regardless of how tall the panes would
   like to be; the panes still fill whatever is left via their existing
   internal grid row-weight (compressing gracefully to ~590-600px instead of
   their 852px wish, exactly as they already did at 702px before this fix,
   just more so) rather than ever swallowing a sibling. The on-demand
   ambiguity banner (`notice_frame`) was reparented onto `_bottom_frame` too,
   since `_show_ambiguities()`'s `pack(before=self.status)` needs a shared
   master.
2. **Button rearrangement, Mark's explicit instruction mid-session**: Clear/
   Import/Export moved from row 2 onto row 1 (right-aligned, after Undo);
   row 2 now holds only Paste/Copy. Verified against the real widget tree:
   row 1's eleven buttons request 1124px against 1156px available at the
   default 1180px window width (fits, 32px to spare) — noted as tighter than
   before and likely to crowd if the window is resized down toward its
   920px `minsize`, same class of issue v2.8 fixed for the original
   single-row layout, not re-solved here since it wasn't asked for.
3. **"No longer starting with Windows minimised"**: investigated rather than
   assumed. Directly tested the *real* packaged `.exe` against Mark's
   *actual* saved config (`start_minimised`/`minimise_to_tray`/
   `start_with_windows` all already `true`) — it correctly launched with no
   visible window at all (`MainWindowHandle: 0` on both the bootloader and
   child process, confirmed via a full `EnumWindows` scan finding nothing
   titled "Scriptorium"). The app-level minimise-to-tray code is not broken.
   What was actually missing: `HKCU\...\Run` had **no `Scriptorium` value at
   all** — confirmed unambiguously (`Get-ItemProperty -Name Scriptorium`
   returned null; the full key's other ~8 entries listed fine). A config
   value of `start_with_windows: true` does not itself create this registry
   entry — only `set_autostart(True)`, called from `SettingsDialog._save()`,
   does that — so autostart was not actually wired up on this machine
   regardless of app version, meaning nothing would launch Scriptorium at
   logon at all, not "launches but shows a window instead of hiding". Fixed,
   with Mark's explicit go-ahead, by writing the exact command line
   `set_autostart(True)` would produce for the frozen case
   (`"C:\Scriptorium\dist\Scriptorium.exe" --minimised`) directly to the real
   registry, then verified for real: launching that exact command line as a
   subprocess produced a `Scriptorium.exe` process with `MainWindowHandle: 0`
   and `Responding: True` — genuinely starts withdrawn to tray, matching the
   v2.5 verification precedent.

### Acceptance checklist
- [x] Both action-bar rows and the status bar are visible at the app's
      default `1180x760` geometry. Verified against the real widget tree
      before the fix (`bar`/`bar2`/`status` all `manager="pack"`, actual
      height 1px, `winfo_ismapped()` False — reproduced the bug on demand)
      and after (`_bottom_frame` gets its full 112px request; `process_btn`
      and `status` both confirmed mapped at sane on-screen y-coordinates).
      Also confirmed visually: a real windowed instance captured via
      `PrintWindow` (bypassing this project's usual UI-automation gap) shows
      the toolbar, both panes, both action-bar rows and the status bar all
      present and correctly positioned.
- [x] Row 1 now ends with Clear/Import/Export after Undo; row 2 holds only
      Paste/Copy. Verified against the real widget tree (button texts and
      order read directly from each row's children) and that row 1 still
      fits the default window width with margin (1124px of 1156px
      available).
- [x] The ambiguity banner still attaches/detaches correctly after being
      reparented onto `_bottom_frame`. Verified via `_show_ambiguities()`
      called for real with a populated list then an empty one:
      `winfo_manager()` reports `"pack"` then `""` with no `TclError` from
      the `before=self.status` reference (this project's own documented
      `winfo_ismapped()`-without-`mainloop()` artefact means that probe
      alone reads False regardless; `winfo_manager()` is the reliable one,
      per the v2.10 precedent).
- [x] Real packaged `.exe` rebuilt (`FileVersion`/`ProductVersion` confirmed
      `2.14.0.0`), launched for real both normally and via the literal
      registered autostart command line; both confirmed alive and
      `Responding: True`, the latter with no visible window. Real
      `scriptorium_config.json` (holds the live API key) confirmed
      byte-identical (unchanged mtime) throughout — every layout/geometry
      test used an isolated temp config; only the registry write (explicitly
      approved) touched real machine state.

---

## v2.15 — Explorer drag-and-drop ✅ shipped 2026-09-02

**Goal:** notes_016 §2.1/3.2 (Mark/Codex) — unlike notes_014/015's incomplete
`DragAcceptFiles`-only proposal (deferred after v2.7, see "Deferred" below),
this note supplies the full `WM_DROPFILES` `WNDPROC` subclass needed to
actually retrieve a dropped path, not just register interest in one. The
highest platform risk in the backlog, per this project's own history (a bad
`WNDPROC` can hang or crash the whole app, not just one feature) — Mark gave
an explicit go-ahead to start it after the v2.14 hand-testing detour.
Implemented essentially as the note specified (a reviewed design, not
improvised fresh, precisely because of that risk); adapted only to the
current file's structure and to preserve `import_file()`'s exact existing
error-message wording rather than the note's own slightly different phrasing.

1. **Native `WM_DROPFILES` bridge** — subclasses the toplevel's own window
   procedure (`SetWindowLongPtrW(GWLP_WNDPROC)`), retaining both the Python
   callback and the original procedure on the instance (`_drop_hwnd`,
   `_drop_wndproc`, `_drop_old_wndproc`) and forwarding every other message
   through `CallWindowProcW` unchanged. On `WM_DROPFILES`: hit-tests the drop
   point against `self.original_box` (accepting it or any Tk/CustomTkinter
   descendant), extracts every dropped path via `DragQueryFileW`, and always
   calls `DragFinish()` in a `finally` block before deferring all Tk/file
   work to `after_idle()` — no Tk mutation happens inside the Win32 callback
   itself. Installed via `self.after_idle(self._enable_file_drops)` scheduled
   at the end of `__init__` (`wm_frame()` is only reliable once Tk has
   realised the top-level); torn down via `_disable_file_drops()`, called
   from `_quit_app()` before `self.destroy()` so the subclass is always
   removed and the callback reference released while the window still exists.
   Installation failure (e.g. a locked-down `SetWindowLongPtrW`) is non-fatal
   and reported via the status bar — Import continues to work regardless.
2. **Shared loader** — `import_file()` split into `_read_document_path()`
   (path → text, extension-agnostic, unraised errors bubble up — preserves
   `import_file()`'s existing "All files" dialog behaviour exactly, since it
   has always accepted whatever the user explicitly picks) and
   `_load_file_path()` (the existing undo/reject/insert/status sequence plus
   every existing error dialog, unchanged in wording). Both the file dialog
   and a completed drop now go through the identical path. Drops are
   deliberately narrower than the dialog: `_handle_dropped_paths()` rejects
   anything but a single `.txt`/`.md`/`.docx` file before ever calling the
   shared loader, since a drop is a much lower-friction action than
   deliberately choosing a file in a dialog — this does not change what the
   Import dialog itself accepts.
3. **Deliberately not enabling `ChangeWindowMessageFilterEx`** — dragging from
   an unelevated Explorer into an elevated Scriptorium is blocked by Windows
   integrity isolation by design; Scriptorium should run unelevated rather
   than widening the accepted cross-integrity message surface to work around
   that.

### Acceptance checklist
- [x] A real drop lands the file's actual content in Original, indistinguishable
      from Import. Verified against a real `DROPFILES` structure with a real
      temp `.txt` file's path, sent via `SendMessageW()` to the live,
      already-subclassed `_drop_hwnd`: the actual installed window procedure
      ran end-to-end, the real file's exact content landed in `original_box`,
      and the status bar correctly showed the new word/character count. (This
      first pass tested same-process only — see the "found and fixed after
      the initial push" note below for why that mattered.)
- [x] The window remains fully responsive after subclassing. Verified: `self.title(...)`
      calls before and after the `SendMessageW` both succeeded with no error,
      confirming `CallWindowProcW` forwarding doesn't break ordinary window
      behaviour.
- [x] Teardown removes the subclass cleanly before the window is destroyed.
      Verified against the real `_quit_app()` (not `destroy()` called
      directly): `_drop_hwnd`/`_drop_old_wndproc`/`_drop_wndproc` all
      confirmed `None` immediately after `_quit_app()` runs and before
      `self.destroy()` completes it; no exception, no hang, clean process
      exit.
- [x] A drop outside Original is ignored (status message only, no file
      touched); an unsupported extension, a directory-shaped path, more than
      one file, and zero files are all rejected with the correct dialog/status
      and leave `original_box` untouched. Verified against the real
      `_handle_dropped_paths()`/`_point_is_over_original()` for all five
      cases, `messagebox.showerror`/`showinfo` patched to non-blocking
      recorders so a real modal couldn't hang the test.
- [x] `_load_file_path()`'s error handling is unchanged from the pre-refactor
      `import_file()`: a missing file (`OSError`), a `.docx` needing
      `python-docx`, and a genuinely bad encoding all produce the exact same
      dialogs as before, with `original_box` left untouched on every failure
      path. Verified directly, including a real missing-file `OSError`
      surfacing its exact message text.
- [x] `ast.parse()` clean; real packaged `.exe` rebuilt, launched for real
      against the live config, no startup crash from the new ctypes
      declarations. Real `scriptorium_config.json` confirmed byte-identical
      throughout — every drag-and-drop test used an isolated temp config.

**Found and fixed after the initial push — a real fatal crash, not a
cosmetic bug.** Mark asked for a hand-test pass across v2.14/v2.15 before
starting v2.16, which is what actually caught this: the acceptance checklist
above was verified with `SendMessageW` called *from within the same process*
as the target window (a Python script importing `scriptorium` and calling
`SendMessageW` on its own window). That is not equivalent to a genuine
cross-process drop, and it did not exercise the actual bug. Sending a real
`WM_DROPFILES` from a **separate** process (PowerShell, standing in for
Explorer) reproducibly killed the target process outright — reproduced five
times running, against both the packaged `.exe` and a plain source run, with
a completely clean process list beforehand each time (ruling out any
leftover-process confound):
```
Fatal Python error: PyEval_RestoreThread: the function must be called with
the GIL held, but the GIL is released (the current Python thread state is
NULL)
```
— always on the *single-instance restore-listener* background thread
(`_watch()`, blocked in an unrelated `WaitForSingleObject`), a thread with no
direct connection to drag-and-drop at all. **Root cause**: the original
`_capture_file_drop()` (both this note's own snippet and the first cut
shipped here) called `self.after_idle(...)` — and, in an intermediate
attempt, `winfo_containing()` for hit-testing — *synchronously inside the
native window procedure*. Windows dispatches even a same-machine
`WM_DROPFILES` through Tcl's own Windows notifier, so the window procedure
runs nested inside Tcl's C-level message pump; calling back into the
interpreter from there — even via something as innocuous-looking as
scheduling a callback — is a form of re-entrancy Tcl does not expect, and it
corrupts interpreter state that only surfaces as a crash somewhere else
moments later. This is a flaw in the reviewed design's own reference
implementation, not something introduced by adapting it here. **Fix**:
`_capture_file_drop()` now touches *only* ctypes/Win32 state and a plain
Python list (`self._pending_drop_events`); a new `_poll_dropped_files()`,
scheduled via an ordinary `self.after(100, ...)` call *from outside* the
window procedure (never nested inside it) and re-arming itself each cycle,
is the only thing that ever calls back into Tk for a drop. Re-verified
against a completely clean process each time: the crash no longer reproduces
across repeated real cross-process drops (including ones with a bad point),
survives an idle control run, and the same-process happy-path test above
still passes unchanged against the new code.

**One verification gap deliberately left open, flagged rather than
papered over**: constructing a fully faithful synthetic cross-process drop
turned out to be harder than expected. A hand-rolled `HDROP` built via plain
`GlobalAlloc` in an external process and sent with a raw `SendMessageW`
consistently fails inside `DragQueryPoint`/`DragQueryFileW` with
`ERROR_INVALID_HANDLE` (6) — because in modern per-process-heap Windows, a
`GlobalAlloc(GMEM_MOVEABLE)` handle is only meaningful within the process
that allocated it. A genuine Explorer drop works because Explorer's OLE-based
drag source and the OS's own `DragAcceptFiles` compatibility shim handle the
cross-process hand-off (re-allocating a target-process-local `HDROP`) before
`WM_DROPFILES` is ever delivered — infrastructure a hand-rolled test message
from an unrelated process bypasses entirely, which is *why* it hits this
error rather than a defect in Scriptorium's own code. Net effect: the crash
fix is verified with high confidence (many repeated real cross-process
message deliveries, including this exact failure path, none of them crash);
the underlying hit-test/file-load logic is verified with high confidence
(same-process test, unaffected by this gap); what is **not** independently
verified is a genuine OS-mediated Explorer→Scriptorium drop landing content
correctly end to end. That specific step needs a person: drag one real
`.txt`/`.md`/`.docx` file from an actual Explorer window onto Original.
Everything the tooling here could reach has been exercised; this last step
could not be simulated without either a real drag or reverse-engineering
the OLE compatibility shim's own re-marshalling, neither of which was worth
doing versus just asking for the one manual check.

Rebuilt as `2.15.1.0` (`filevers`/`FileVersion`/`ProductVersion` in
`version_info.txt`) specifically so this corrected build is distinguishable
from the original `2.15.0.0` that shipped with the crash — `APP_VERSION` in
`scriptorium.py` stays the display string `"2.15"`, this was a fix to the
same feature, not a new one.

**A second, unrelated bug found by Mark's own real Explorer drag-and-drop
hand-test**: dragging a real file worked correctly (closing the one
verification gap noted above), but Mark also reported the toolbar's
"⚙ Settings" button was positioned off-screen at the app's default window
size — only reachable by manually widening the window (screenshot
`wider.jpg`). Root cause was the *same class* of bug as v2.14's action-bar
fix, just on the toolbar row instead of the bottom rows: `_build_toolbar()`
used a `grid` layout with an empty weighted spacer column (`column 10,
weight=1`) to push the Settings button to column 11, the far right — but the
toolbar's own content (Mode through Preset, columns 0–9, including their
`padx` spacing) already totals roughly 1159px, leaving only ~21px of the
default 1180px width for the spacer to absorb before Settings needs room of
its own; in practice the button's ~134px (including its own `padx`) pushed
the row's true total past 1180px, and grid — like `pack` — does not shrink
content to fit, it lets the excess extend past the frame's visible bounds.
Not introduced by v2.14/v2.15 — latent since whichever of v2.4 (Tone)/v2.12
(Preset) first pushed the toolbar's own content that wide, never caught
because nothing had checked toolbar-row width the way v2.8 once checked
button-row width (and only for buttons, not the whole row including labels
and menus).

**Fixed per Mark's own suggested placement**: removed the Settings button
and the now-pointless spacer column from `_build_toolbar()` entirely
(toolbar now totals ~1159px of the 1180px available, fitting with margin to
spare); added it to `bar2` (row 2 of the bottom action bar), right-aligned
via `pack(side="right")`, so it sits directly beneath "Export…" — exactly as
requested. Verified against the real widget tree (toolbar's summed child
`reqwidth` plus each column's `padx`, confirming the row now fits;
`open_settings()` called for real, confirming the dialog still opens
correctly from its new location) and visually via a real `PrintWindow`
screenshot at the default `1180x760` geometry, showing "⚙ Settings" now
directly under "Export…" as intended.

Rebuilt as `2.15.2.0`.

**Deferred to v2.16**: notes_016 §2.4/3.5's Markdown diff export and rich
`CF_HTML` clipboard diff (the note's other raw-Win32 item, a separate
`GlobalAlloc`/clipboard transaction unrelated to `WM_DROPFILES`) — split out
rather than bundled with drag-and-drop, per this project's own established
pattern of one focused, independently-verifiable release per risk/theme
rather than grab-bagging two different raw-Win32 features together.

---

## v2.16 — Rich `CF_HTML` clipboard diff ✅ shipped 2026-09-02 (as build 2.21)

**Goal:** notes_016 §2.4/3.5 — a fenced unified Markdown diff export plus an
HTML clipboard format (with a plain-text fallback) for "Copy rich diff",
useful when pasting into Word/Outlook. The other raw-Win32 item in the
backlog (manual `GlobalAlloc`/clipboard transaction, `CF_HTML` header byte
offsets), so carries meaningful platform risk of its own even though it
doesn't touch the same `WNDPROC`-subclassing surface as v2.15.

**Shipped last, as `APP_VERSION`/build `2.21`, not `2.16`** — v2.17-v2.20
(a separate, later feature review's proposals) were implemented and shipped
first while this stayed scoped, so `2.16` was already behind by the time
Mark asked for it; the section keeps its original number for continuity
with the rest of this document, but the actual display version and
`version_info.txt` reflect real shipping order. Implemented essentially as
notes_016 specified — adapted only to the current file's structure, and
deliberately **not** implementing that note's own `text_metrics()` (word/
character/reading-time centralisation): v2.17 already shipped an
overlapping reading-time-plus-readability-grade feature in
`_refresh_status()`, and adding a second, differently-worded reading-time
estimate on top would just be two numbers disagreeing on screen for no
benefit.

1. **Markdown diff export** — `build_markdown_diff()`/`_safe_markdown_fence()`
   (near `summarise_diff()`), producing a `# Scriptorium revision diff`
   document with a dynamically-sized backtick fence (longer than any run
   already inside the diff body, so source text containing its own
   ` ```password``` `-style fence can't terminate the block early) wrapping
   a `difflib.unified_diff()` of `_result_source` vs the revision — the
   exact snapshot the revision was generated from, not a possibly-edited
   live Original. `export_diff_file()` (beside `export_file()`) writes it
   to a user-chosen `.md` path, gated behind the same stale-revision
   confirmation every other revision-touching action already uses.
2. **Rich HTML clipboard** — `build_html_diff()` (reusing the exact same
   `_tokenise()`/`SequenceMatcher` opcodes as `render_diff()`/
   `summarise_diff()`, so it never disagrees with what the diff pane or the
   copy-summary text already show) renders red-strikethrough deletions and
   green-bold insertions as one HTML fragment. `_build_cf_html()` wraps it
   in the documented Windows "HTML Format" header (`Version:1.0`/
   `StartHTML`/`EndHTML`/`StartFragment`/`EndFragment`, **byte** offsets
   into the UTF-8-encoded document, not Python character indexes —
   confirmed the hard way to matter, see below). `_global_clipboard_memory()`/
   `set_html_clipboard()` publish it via `GlobalAlloc(GMEM_MOVEABLE)` +
   `RegisterClipboardFormatW("HTML Format")` + `OpenClipboard`/
   `EmptyClipboard`/`SetClipboardData`/`CloseClipboard`, publishing the rich
   HTML and a `CF_UNICODETEXT` plain-text fallback (the clean revised text)
   in the same transaction, with correct ownership bookkeeping (a handle is
   only freed if `SetClipboardData` did *not* already take ownership of it
   — freeing a handle Windows now owns, or leaking one it doesn't, would
   both be real bugs). `copy_rich_diff()` (beside `copy_change_summary()`)
   wires it to a new "Copy rich diff" button.
3. **Two new buttons**, both added to the bottom action bar's *second* row
   (`bar2`) rather than the first — row 1 already sits at 1040px of ~1156
   available after v2.14/v2.15.2's own additions, while row 2 had ample
   headroom (a real measurement showed 340px of ~1156 before this, 560px
   after adding both — still comfortable). "Copy rich diff" grouped with
   Paste/Copy/History (left side); "Export diff…" placed beside Settings
   (right side, packed so Settings stays the true rightmost button).

### Acceptance checklist
- [x] **CF_HTML byte-offset arithmetic verified directly against the
      encoded byte array, not Python indexes** — per this note's own
      testing-checklist warning (§3, "Verify CF_HTML byte offsets against
      the encoded byte array"). Two real cases: a pure-ASCII fragment, and
      a deliberately non-ASCII one (é, £, em dash, curly quotes — each 2-3
      UTF-8 bytes but 1 Python character, exactly the shape of input that
      would silently corrupt a character-index-based implementation).
      Extracted `cf_html_bytes[StartFragment:EndFragment]` matched the
      built fragment's own UTF-8 encoding byte-for-byte in both cases, and
      decoded back to valid UTF-8 without error (a boundary bug would
      likely split a multi-byte sequence).
- [x] **Verified with a genuinely independent, cross-process reader — not
      the same ctypes code checking itself** — per the exact lesson v2.15's
      crash taught about anything meant to cross a process boundary. A real
      `copy_rich_diff()` call set the live clipboard; a *separate*
      PowerShell process using .NET's `System.Windows.Forms.Clipboard` API
      (a completely different technology stack from the ctypes writer) read
      it back: `UnicodeText`/plain text held exactly the clean revised
      text; `HTML Format` was present, correctly matched by name, and its
      decoded header/fragment content was byte-perfect and exactly the
      expected `<del>`/`<strong>`-styled HTML — confirmed a genuinely
      independent consumer parses this correctly, not just our own writer.
- [x] The Markdown fence-escaping edge case (source content containing its
      own triple-backtick run) produces a fence strictly longer than the
      longest run inside the body, verified against real output, not just
      inspected.
- [x] `copy_rich_diff()`/`export_diff_file()`'s "nothing to copy/export yet"
      guards fire correctly with no revision present; a real revision
      produces a real clipboard write and a real `.md` file with correct
      content, verified against a real `Scriptorium()`.
- [x] Both new buttons fit their row with wide margin (row 2 at 560px of
      ~1156 available); row 1 is untouched at 1040px. Verified against the
      real widget tree, and visually via a real `PrintWindow` screenshot.
- [x] `ast.parse()` clean; a full construct/destroy cycle against a real
      `Scriptorium()` completes with no exception. Real packaged `.exe`
      rebuilt (`FileVersion`/`ProductVersion` `2.21.0.0`), launched for real
      against the live config, alive and `Responding: True`. Real
      `scriptorium_config.json` confirmed byte-identical throughout.

---

## v2.17 — Readability metrics + keyboard-shortcut reference ✅ shipped 2026-09-02

**Goal:** the first two of five proposals from notes_019 (a fresh feature
review, distinct from notes_016 — see that note for the other three and the
reasoning behind each). Bundled together since both are the lowest-risk
tier notes_019 identified: pure UI additions, no prompt/model surface
touched, so [[mark_meaning_preservation_priority]] doesn't apply to either.
Ships ahead of v2.16 in version order — v2.16 (the rich clipboard diff) is
still scoped but not started; this pair was simply ready first and carries
none of its platform risk.

1. **Readability and reading-time metrics** (notes_019 §2.1) — `_count_syllables()`/
   `reading_metrics()` (module level, near `summarise_diff()`) compute a
   Flesch Reading Ease grade label and a 200wpm reading-time estimate from
   the Original text already in memory; no new dependency (a vowel-group
   syllable heuristic stands in for the syllable counter the standard
   library doesn't have). Wired into `_refresh_status()`, appended to the
   existing word/character count line, only once Original has at least 20
   words — below that a score is not meaningful and would look precise
   without being so.
2. **Keyboard-shortcut reference dialog** (notes_019 §2.2) — `ShortcutsDialog`,
   following the existing `TonePickerDialog`/`SettingsDialog` pattern
   (`bind_dialog_chrome()`/`position_over_parent()`), lists the eight
   bindings `_bind_shortcuts()` already registers (Ctrl+Enter, Ctrl+I,
   Ctrl+S, Ctrl+Shift+A, Esc, Ctrl+Shift+C, Ctrl+Shift+M, Ctrl+Z) plus
   itself (F1). None of these were discoverable anywhere in the running
   app before this.

### Acceptance checklist
- [x] `reading_metrics()` returns a plausibly-different label for an easy
      vs. a deliberately dense/polysyllabic real sample, `None` for empty
      text, and does not raise on a two-word input. Verified directly
      against the real function.
- [x] The status bar shows no readability/reading-time text below 20 words,
      and shows it (`"<label> · <time>"`) at or above that floor. Verified
      against a real `Scriptorium()`/`original_box`/`_refresh_status()`
      cycle at both word counts.
- [x] `_show_shortcuts()` (called directly and via a real `<F1>`
      `event_generate`) opens exactly one `ShortcutsDialog` titled "Keyboard
      shortcuts"; closing it and re-triggering opens exactly one again (no
      duplicate/leaked toplevels). Verified against the real widget tree.
- [x] `ast.parse()` clean; a full construct/destroy cycle against a real
      `Scriptorium()` completes with no exception. Real packaged `.exe`
      rebuilt (`FileVersion`/`ProductVersion` `2.17.0.0`), launched for real
      against the live config, alive and `Responding: True`. Real
      `scriptorium_config.json` confirmed byte-identical throughout — every
      test used an isolated temp config.

---

## v2.18 — User-defined house-style avoid-list ✅ shipped 2026-09-02

**Goal:** notes_019 §2.3 — a third proposal, higher risk than v2.17's pair
since it touches prompt construction: words or phrases the user never wants
to see, folded into the system prompt the same way Role and Tone already
are. Per this project's own standing rule (and notes_019's own explicit
flag), implemented then calibrated against a live model before being
considered done — design alone was never treated as sufficient.

1. **Config schema** — `DEFAULT_CONFIG["house_style_avoid"] = []`;
   `normalise_house_style_avoid()` (mirrors `normalise_user_presets()`'s
   discipline) strips, de-duplicates case-insensitively, and caps entries
   at `MAX_HOUSE_STYLE_TERMS` (20) and length at `MAX_HOUSE_STYLE_TERM_LENGTH`
   (40 chars) — small enough to stay a clearly bounded instruction, not an
   open-ended rules engine. Wired into `normalise_config()`.
2. **Prompt integration** — `build_avoid_instruction()` (mirrors
   `build_tone_instruction()`'s shape and closing-guard pattern);
   `build_system_prompt()` gained an `avoid_words` parameter, folded into
   the `# Task` section alongside `tone_line`. `process()`'s call site
   passes `self.cfg.get("house_style_avoid", [])` through.
3. **Settings UI** — a "House style" section: an entry + Add button, and a
   scrollable list of current terms each with a Remove button, following
   the same working-copy-then-`_save()` pattern every other Settings
   control already uses.

**Live-model calibration — caught a real embellishment bug, then confirmed
the fix**, same discipline as v2.4/v2.11: four real cases run against
`call_ollama()` (`llama3.2:3b`), deliberately including one designed to be
load-bearing (a source sentence whose banned term — "synergy" — sits inside
the clause carrying the actual causal claim, so a naive rephrase has
somewhere to lose content). First pass: three of four cases clean, but the
"synergy" case turned "the synergy between the marketing and sales teams
increased revenue" into "...enhanced overall performance, leading to
increased revenue" — a new claim ("enhanced overall performance") not in
the source, invented as a bridge for the rephrase. The original guard text
only forbade *deleting* content to avoid a banned term; it said nothing
about *adding* a new claim while working around one. Fixed by naming the
exact failure as a worked example in `build_avoid_instruction()`'s guard
(the real sentence pair from this test, not an abstract description) rather
than a generic "don't embellish" restatement — re-ran the fixed version 3x
on the same case (matching v2.4's own repeat-testing discipline for its
trickiest finding) plus all three other cases once more: every run clean,
no added claims, no dropped facts, banned terms genuinely absent from every
revision. The one "missing content" flag automated checking raised on the
"leverage" case was confirmed to be the test script's own overly literal
substring match against a legitimate paraphrase ("current customer ties"
for "existing customer relationships") — Paraphrase mode is supposed to
reword, not preserve exact phrasing; the underlying fact was intact and the
model itself flagged the one genuinely softer phrase ("secure a decision"
for "close this deal") as an ambiguity worth a second look, exactly the
self-aware behaviour this feature depends on.

### Acceptance checklist
- [x] `normalise_house_style_avoid()` strips/de-duplicates/caps correctly
      against valid, malformed, oversized and over-length-limit inputs, and
      degrades a non-list value to `[]` rather than raising. Verified
      directly.
- [x] `build_avoid_instruction()` names every configured term and includes
      the anti-deletion and anti-embellishment guard text; an empty list
      produces an empty string (no prompt change when the feature isn't
      used). `build_system_prompt()` correctly folds it in only when
      `avoid_words` is non-empty. Verified directly.
- [x] The Settings UI's Add/Remove/Save cycle round-trips correctly against
      a real `SettingsDialog`: adding two terms, removing one, attempting a
      case-insensitive duplicate (silently ignored), then Save — both
      `self.cfg` and the real file on disk hold exactly the expected final
      list. Verified against a real temp config path.
- [x] **Live-model calibration** (see above): 4 initial cases + 3 repeats of
      the trickiest one, all against real `call_ollama()` calls — no
      content loss, no invented claims, banned terms genuinely absent,
      after one real fix to the guard wording based on an actual finding,
      not assumed safe from the design alone.
- [x] `ast.parse()` clean; a full construct/destroy cycle against a real
      `Scriptorium()` completes with no exception. Real packaged `.exe`
      rebuilt (`FileVersion`/`ProductVersion` `2.18.0.0`), launched for real
      against the live config, alive and `Responding: True`. Real
      `scriptorium_config.json` confirmed byte-identical throughout — every
      test (including calibration) used an isolated temp config; Ollama
      calls never touch `CONFIG_PATH`.

---

## v2.19 — Headless batch/CLI mode ✅ shipped 2026-09-02

**Goal:** notes_019 §2.4 — point Scriptorium at a folder of documents and a
Mode/Strength/Role/Tone combination, get suggested revisions and diffs back
for each, no GUI. Aimed at a different use case than the interactive app:
someone with many documents wanting one combination applied to all of them.

1. **Shared loader lifted to module level** — `read_document_path()` (near
   `write_docx()`) is the exact logic `Scriptorium._read_document_path()`
   already had, moved out since it never touched `self`; the method is now
   a one-line delegate so the GUI's Import/drop paths and batch mode share
   identical encoding fallback behaviour.
2. **`_run_batch_mode()`** (before `main()`) — `argparse`-driven:
   `--batch INPUT_DIR --out OUTPUT_DIR [--mode] [--strength] [--role]
   [--tones a,b] [--backend]`. Loads the existing config via `load_config()`
   for anything not overridden on the command line (API key, models,
   `house_style_avoid` all apply exactly as in the GUI); an invalid
   role/tone combination is rejected the same way the GUI rejects one
   (`validate_tones()`, the same `ROLES` check), never silently clamped.
   Synchronous, no worker thread or Tk — there is no window to keep
   responsive. For each supported file (`.txt`/`.md`/`.docx`, alphabetical):
   masks placeholders exactly as `process()` does, calls the same
   `build_system_prompt()`/`run_backend()`, restores placeholders, then
   writes `<name>.revised.<ext>` and `<name>.diff.txt` (from
   `summarise_diff()` plus any ambiguities/note) into `OUTPUT_DIR` — **never
   overwrites the input**, and never "accepts" anything automatically; the
   two-file output is this mode's equivalent of the GUI's Original/
   Suggested-revision split, so reviewing before acting on it is still the
   only path, just via two files instead of an Accept button. One bad file
   is logged and skipped, not fatal to the rest of the run. A
   `batch_log.txt` is written into `OUTPUT_DIR` alongside `print()`,
   specifically because `print()` is invisible in the packaged `.exe`
   (`console=False`) — the same lesson v2.9's tray-icon-failure fix and
   v2.9's unreadable-config surfacing already learned, applied here before
   it could repeat as a fresh "silent failure" bug in a new feature.
3. **Single-instance mutex deliberately skipped for `--batch`** — checked in
   `main()` before `_claim_single_instance()` is ever called. Product
   decision, made rather than deferred: a headless batch run and an
   interactive GUI session share no state a mutex is meant to protect (no
   window, no tray icon, nothing a second launch needs warning away from),
   so treating them as "the same instance" would only block a batch run
   from working alongside an already-open GUI session for no real benefit.

### Acceptance checklist
- [x] A real batch run (2 files + 1 deliberately empty file, real
      `call_ollama()`) correctly skips the empty file, produces
      `<name>.revised.<ext>`/`<name>.diff.txt` for the other two with
      accurate content and diff summaries, writes a complete
      `batch_log.txt`, exits `0`, and leaves every input file
      byte-identical (`md5sum` before/after). Verified for real, not
      mocked.
- [x] Bad inputs are rejected with a clear message and exit code `1`
      *before* any backend call: a non-existent input directory, an
      unrecognised `--role`, and a genuinely conflicting `--tones` pair
      (the same `validate_tones()` rejection the GUI shows). Verified
      directly against `_run_batch_mode()`.
- [x] `--batch` works identically from source (`python scriptorium.py
      --batch ...`) and the packaged, console-less `.exe` — the real
      packaged build was run against a real file and produced correct
      output and a readable `batch_log.txt` despite `console=False`
      making `print()` alone invisible. (The one real-world hitch hit
      during this check — Ollama taking noticeably longer than usual
      because the model had been idled out of memory and needed
      reloading — is normal Ollama behaviour, not a Scriptorium bug.)
- [x] A normal GUI launch (no `--batch` in `sys.argv`) is provably
      unaffected: `argparse` is never invoked unless `--batch` is present,
      confirmed by a real `Scriptorium()` construct/destroy cycle after
      this change, identical to every prior such check this session.
- [x] `ast.parse()` clean. Real packaged `.exe` rebuilt (`FileVersion`/
      `ProductVersion` `2.19.0.0`). Real `scriptorium_config.json`
      confirmed byte-identical throughout — every test used an isolated
      temp config or explicit `--backend ollama` override, never the real
      config's own `anthropic` default.

---

## v2.20 — In-session revision history ✅ shipped 2026-09-02

**Goal:** notes_019 §2.5 — the fifth and last approved proposal, explicitly
revisiting an idea notes_003/005/006 all proposed and every session since
kept ranking something else above, never because it was unwanted.
Deliberately constrained from the outset to stay inside this project's
existing "nothing persists except via Export" privacy principle (confirmed
after a real incident during v2.5 testing) — the note this scoped from was
explicit that relaxing that constraint would be a separate, bigger
conversation, not a natural extension of this feature.

1. **`self._revision_log`** (initialised in `__init__`, alongside
   `undo_stack`) — a plain in-memory list, **never written to
   `scriptorium_config.json` or any other file**, cleared implicitly at
   process exit exactly like `undo_stack` is. `_remember_for_history()`
   appends one entry per completed revision from inside `_on_success()`
   (time, mode, strength, role, tones, original, revised), capped at 50
   the same way `_remember_for_undo()` caps `undo_stack`.
2. **`HistoryDialog`** (next to `PresetManagerDialog`) — lists entries most
   recent first, each with a timestamp/settings summary and a text preview,
   a "View" button per row.
3. **`_restore_from_history()`** — loads a past entry back into Original/
   Suggested revision *and* restores the Mode/Strength/Role/Tone controls
   that produced it (a complete return to that moment, not just a text
   preview), through `_remember_for_undo()` and `render_diff()` exactly as
   a fresh `process()` result would, via the existing, already-validated
   `_set_selected_tones()` rather than touching `self.selected_tones`
   directly. Accept/Reject/Copy/Undo all behave identically afterwards —
   this is a way back to an earlier moment, never a silent re-application
   of one.
4. **"History" button** added to the bottom action bar's second row
   (`bar2`, next to Paste/Copy) — row 2 had ample width margin (340px of
   ~1156 available with all four buttons, per a real measurement), unlike
   row 1's tighter budget after v2.14/v2.15.2's own additions.

### Acceptance checklist
- [x] Two real `process()` calls (real `call_ollama()`, different Mode/
      Strength each time) correctly append two entries with accurate
      metadata; a direct 60-append stress check confirms the cap holds at
      exactly 50 with the oldest 10 correctly dropped and order preserved.
      Verified against a real `Scriptorium()`.
- [x] `HistoryDialog` opens with the real log and both rows populated
      correctly; restoring the *oldest* entry (not just re-showing the
      most recent, which would be a much weaker test) correctly restores
      Original's text, Mode, Strength, and `last_result`, and grows
      `undo_stack` by one — verified against real widget state, not
      assumed from the code.
- [x] The real `scriptorium_config.json`'s mtime is provably unchanged
      across the entire test (two real backend calls, a restore, cap
      stress-test) — the in-memory-only constraint actually holds, not
      just claimed.
- [x] Bottom action bar's second row (now 4 buttons) still fits with wide
      margin (340px of ~1156 available); the normal `Scriptorium()`
      construct/destroy cycle remains clean.
- [x] `ast.parse()` clean. Real packaged `.exe` rebuilt (`FileVersion`/
      `ProductVersion` `2.20.0.0`), launched for real against the live
      config, alive and `Responding: True`.

**One real debugging detour worth recording**: an early, more elaborate
test harness (nested nested `after()`-based polling alongside the worker
thread's own callback scheduling) made a real `process()` call look
permanently stuck ("busy" never clearing), which briefly looked like a
serious pre-existing threading bug in `process()`'s worker-thread/
`_post_to_ui()` pipeline — notable because that exact pipeline had never
actually been exercised end-to-end by an automated test in this project
before now; every prior session's `process()` verification was either a
real human clicking the real button, or a direct `call_ollama()` call that
bypasses the threading entirely. A simpler, isolated single-call test
immediately showed the real pipeline completing correctly in ~4 seconds —
the elaborate harness had its own scheduling bug, not the app. Recorded so
a future session reaches for the simple version of this test first.

---

## v2.22 — Tray/start-up lifecycle gating ✅ shipped 2026-09-03

**Goal:** notes_020 (Mark) — a real hand-testing diagnosis, not a note-backlog
proposal. Two observed symptoms on Windows 11 (an ordinary launch sometimes
jumping straight to the tray; "Start minimised" not reliably taking effect)
traced to one root cause: `<Unmap>` firing with an iconic state while Tk is
still settling the window's initial Win32 placement, *before* any user
action, plus deciding hidden-vs-visible from inside `__init__` and calling
`withdraw()` before the window had ever been mapped — unreliable on Windows
11, which can simply ignore a pre-map withdraw. No prompt or data-model
surface touched; pure lifecycle/window-state.

1. **`_window_ready` gate on `_on_minimize()`** — `<Unmap>` is now ignored
   entirely until armed. `_on_mapped()` (bound to `<Map>`) schedules
   `_arm_tray_minimise()` 300ms after the *first* real Map, giving Windows
   11's initial-placement noise a window to settle in before a genuine
   minimise is trusted.
2. **`_apply_launch_visibility()`** replaces the old immediate
   `wants_minimised` check/`withdraw()` call in `__init__`. Scheduled via
   `after_idle` so it runs against a window Tk has actually placed, not
   mid-construction; the hidden branch itself withdraws via one more
   `after(50, ...)` tick rather than inline, per Mark's own note ("a
   withdraw-before-map is ignored on Windows 11"). The existing safety net
   is preserved exactly: hidden only when `_wants_start_minimised()` *and*
   `minimise_to_tray` *and* `TRAY_AVAILABLE` all hold, so a start-minimised
   config with tray unavailable/disabled still falls back to a normal
   visible launch rather than trapping the user.
3. **`_autostart_command()`/`set_autostart()` gain a `start_minimised`
   parameter** — `--minimised` is now only appended to the registered Run
   command when the user's "Start minimised to tray" setting is actually
   on, not unconditionally on every autostart launch as before. Threaded
   through from `SettingsDialog._save()`'s existing `set_autostart()` call.

### Acceptance checklist
- [x] A synthetic iconic `<Unmap>` fired before `_window_ready` is armed
      does not tray-minimise; the identical event fired after arming does
      (real `pystray.Icon` created, `state()` becomes `"withdrawn"`).
      Verified against a real `Scriptorium()`, a real `iconify()` call (not
      a synthetic event object), gated and then armed.
- [x] `start_minimised: True` + `minimise_to_tray: True` genuinely launches
      hidden (real `mainloop()` run, `state()` ends `"withdrawn"`, a real
      tray icon exists) — not just "doesn't crash". `--minimised` on argv
      forces the same outcome independent of the config flag.
- [x] `start_minimised: True` + `minimise_to_tray: False` still launches
      visible (the pre-existing "don't trap the user" safety net holds
      through the new gating).
- [x] An ordinary default-config launch is visually unaffected: `state()`
      ends `"normal"`, no tray icon.
- [x] `_autostart_command(True)` ends in `--minimised`; `_autostart_command(False)`
      does not. `set_autostart()` writes both forms correctly to the real
      `HKCU\...\Run` entry (read back via `winreg`) and the entry was
      removed afterwards, restoring the machine to its pre-test (absent)
      state.
- [x] `ast.parse()` clean. Real packaged `.exe` rebuilt (`FileVersion`/
      `ProductVersion` `2.22.0.0`), launched for real against the live
      config, alive and `Responding: True`. Real `scriptorium_config.json`
      confirmed untouched (unchanged mtime) throughout.

**One testing-environment finding, not a product defect**: this session's
automated `EnumWindows`/`IsWindowVisible` checks against the real packaged
`.exe` reported the window as not visible even for an ordinary launch that
Tk's own `state()` correctly reported as `"normal"` — and, as a control, the
identical check also failed to find a completely unrelated, freshly-launched
plain `tk.Tk()` test window. This confirms the false reading is a limitation
of this automation channel's cross-session window enumeration (same
underlying category as this project's already-documented UI-automation gaps
for this app — see [[scriptorium_testing_gotchas]] items 4/5), not a real
visibility bug; Tk's own `state()`/`winfo_viewable()` under a real
`mainloop()`, used for every acceptance check above, remains the correct
source of truth and is unaffected by this gap.

**Also found and fixed during hand-verification, not in the note**: a
genuinely unrelated real modal — `_maybe_show_privacy_notice()` — blocks
`__init__` on a fresh `backend: "anthropic"`/no-`privacy_ack` config, since
`messagebox.showinfo()`'s `tkwait window` blocks regardless of whether
`mainloop()` has been entered yet. Confirmed present identically on the
unmodified v2.21 baseline (`git stash` control test), so this is pre-existing
behaviour correctly requiring a real click, not a defect this release
introduced or needed to fix — noted here only so a future session's test
configs set `privacy_ack: True` (or `backend: "ollama"`) up front rather than
re-diagnosing an apparent "hang" from scratch.

---

## v2.23 — Drop-replacement safety, preset repair notice, export/reading-time/clipboard polish ✅ shipped 2026-09-03

**Goal:** notes_021 (Codex, second-generation hardening pass against v2.21 —
see "notes_021 delivery plan" below for the full five-area review and why
each area was scoped the way it was) — the note's own recommended "Ship 2"
bundle: everything it judged low-risk UI/integrity polish, landed together.
No prompt or content-generation surface touched.

1. **Explorer-drop replacement confirmation** (§2.1/3.1). `_load_file_path()`
   gains `confirm_replace=False`; reads the document first (so a corrupt or
   unsupported file never triggers a pointless question), then asks once
   only when Original already holds non-whitespace text. The Explorer-drop
   call site passes `confirm_replace=True`; `import_file()`'s existing
   no-confirm behaviour is unchanged, since choosing a file there is
   already a deliberate act.
2. **Preset-repair visibility** (§2.2/3.2). `normalise_user_presets()`/
   `normalise_config()`/`load_config()` gain an optional, capped
   (5 messages + an omitted count) issues collector, populated only when
   `load_config()` reads a real file from disk — internal re-normalisation
   before a save stays silent. `_maybe_warn_config_repairs()` (beside
   `_maybe_warn_unreadable_config()`) explains what was dropped and why, so
   a later Settings/preset save can no longer silently erase a malformed
   entry with no explanation the user ever saw.
3. **Immediate tone-conflict feedback** (§2.3/3.3, the one small piece of
   the fidelity-audit proposal shipped now — the audit itself is separate,
   see below). `tone_conflict_message()` split out of `validate_tones()`;
   `TonePickerDialog._toggle_tone()` calls it right after tentatively
   appending a tone and reverts immediately with the same message
   `_apply()`'s final `validate_tones()` call would have shown — one source
   of truth, feedback moved earlier.
4. **Annotated Markdown as a second diff-export format** (§2.4/3.4).
   `build_annotated_markdown_diff()` (same `_tokenise()`/`SequenceMatcher`
   contract as the visible diff and rich clipboard) plus a small
   `DiffExportFormatDialog` opened from Export diff, offering "Unified
   diff" (unchanged default) or "Annotated prose" (`<del>`/`<strong>` in a
   single `<pre>` block, `html.escape()`d against literal source markup).
5. **Reading-time boundary fix** (§2.4/3.4). `reading_metrics()` now
   returns fractional minutes instead of `round()`-ing them (ties-to-even
   was rounding 201–299 words down to a flat 1); `_refresh_status()` shows
   "under a minute" only below 1.0 and `math.ceil()` otherwise — a full 200
   words now correctly reads "~1 min read" rather than "under a minute".
6. **Clipboard-contention retry** (§2.4/3.4). `_open_clipboard_with_retries()`
   makes up to 5 bounded, increasing-wait attempts (worst case 0.20s) before
   `set_html_clipboard()` raises — `OpenClipboard` commonly fails
   transiently since clipboard ownership is global to the desktop.

### Acceptance checklist
- [x] A drop over populated Original asks once; declining leaves Original,
      undo stack and any in-flight request untouched; accepting loads
      normally. A drop over empty Original, and every `import_file()` call,
      never prompts. Verified against a real `Scriptorium()`, all four
      cases, including a genuine file read from disk.
- [x] A config with five-plus malformed preset entries (non-string name,
      blank name, overlong name, reserved-name collision, invalid mode)
      shows a capped warning naming up to 5 of them plus an omitted count,
      keeps the one valid entry, and leaves `self.cfg["user_presets"]`
      correct; a clean config shows no warning. Verified against real
      `normalise_user_presets()`/`load_config()`/a real `Scriptorium()`
      construction with `messagebox.showwarning` observed directly.
- [x] Ticking a conflicting tone in a real `TonePickerDialog` reverts it
      immediately with the exact conflict message; a legal second tone
      still applies normally.
- [x] `export_diff_file()` offers the format choice before the save
      dialogue; both "unified" and "annotated" produce the correct
      document; cancelling the format choice skips the save dialogue
      entirely rather than falling through to a default. Verified
      end-to-end against a real `Scriptorium()`, both formats' actual file
      contents inspected.
- [x] `reading_metrics()` returns `< 1` for 199 and exactly `1.0` for 200
      words (displaying "~1 min read", correctly no longer "under a
      minute" — the actual bug); 201/399/400/401 words all ceiling to the
      expected whole-minute label.
- [x] `build_annotated_markdown_diff()` HTML-escapes literal `<`/`>`/`&` in
      the source and correctly marks insertions/deletions.
- [x] A real `set_html_clipboard()` call round-trips through a genuinely
      independent reader (raw `ctypes` `CF_UNICODETEXT` read, not this
      project's own writer code); `_open_clipboard_with_retries()` recovers
      from real, deliberately induced clipboard contention from another
      thread holding `OpenClipboard` briefly.
- [x] `ast.parse()` clean; quick regression pass (`DEFAULT_CONFIG` round
      trip, `ROLES`/`TONES` membership, four-tone-over-limit rejection) and
      a real `Scriptorium()` construct/destroy cycle all still pass.
      Packaged `.exe` rebuilt (`FileVersion`/`ProductVersion` `2.23.0.0`),
      launched for real, alive and `Responding: True`. Real
      `scriptorium_config.json` confirmed untouched throughout.

**notes_021 delivery plan (context for this and the versions after it)**:
Codex's review found all five originally-requested architecture areas
already fully shipped in v2.21 and proposed a second-generation hardening
pass instead, in this recommended order: (1) notes_020's lifecycle defect
first (v2.22, above); (2) this low-risk UI/integrity bundle (v2.23); (3) a
deterministic, advisory protected-content fidelity audit, calibrated before
being trusted; (4) request-scoped cancellation for the retry transport,
fault-injection tested; (5) visible streaming, explicitly deferred pending
two product decisions the note itself flags as still open. Areas 3–4 are
scoped as their own future versions rather than bundled here, matching the
note's own reasoning that fidelity-audit correctness and cancellation
correctness each deserve isolated verification; area 5 stays out of scope
until those product decisions are actually made.

---

## v2.24 — Protected-content fidelity audit ✅ shipped 2026-09-03

**Goal:** notes_021 §2.3B/3.3 — the fidelity-audit half of the note's
tone-conflict-and-audit proposal (the conflict-feedback half already
shipped in v2.23). A deterministic, local, advisory-only check: the system
prompt already tells the model never to alter numbers, URLs, quoted
material, paths etc., but a prompt instruction cannot *guarantee* that —
this is a second, independent check that doesn't rely on the model
following instructions correctly. **Subject to
[[mark_meaning_preservation_priority]]** in spirit (it exists specifically
to catch the failure mode that priority is about), though unlike v2.4/
v2.11/v2.18 it adds no prompt text of its own — it audits the completed
revision after the fact rather than trying to prevent the problem via
wording.

1. **`audit_revision_fidelity(original, revised)`** compares exact
   multisets (`Counter`, so a duplicate figure needs a matching duplicate)
   of five categories — numbers/amounts/percentages, URLs, email addresses,
   Windows paths, quoted passages — before and after. A genuinely missing
   or newly-introduced item in a category produces one warning naming it;
   reordering within a category is never flagged.
2. **Wired into `_on_success()`** immediately after placeholder restoration
   and before the stale-source check, auditing the fully restored text the
   user actually sees and exports (not the masked model response) — so a
   warning always names a real value, never a `⟦PH0⟧`-style sentinel.
   Warnings feed the existing `_show_ambiguities()` banner alongside the
   model's own ambiguity list and the British-letter-conventions check —
   never a blocking dialog, never a rewrite, never disables Accept.
3. **Deliberately conservative regex boundaries** — a URL/path/quote match
   trims trailing sentence punctuation (`.`, `,` etc.) rather than
   swallowing it, mirroring the existing URL pattern's own approach, so "at
   the end of a sentence." doesn't get misread as part of the value.

### Acceptance checklist
- [x] Fourteen deterministic cases (clean paragraph; unchanged vs. changed
      number/currency/percentage; a duplicated figure dropped to one
      occurrence; date-shaped numeric tokens unchanged; a URL/path/quote
      unchanged despite trailing sentence punctuation; URL, email, path and
      quote each genuinely changed; two Windows-path mentions and a
      multi-category inventory both unchanged but reordered) all produce
      exactly the expected warning set, no more and no less. Verified
      against the real `audit_revision_fidelity()`.
- [x] A real `_on_success()` call with a genuinely changed protected number
      surfaces the exact expected warning text in the live ambiguity
      banner; a clean revision with no protected-content change shows no
      such warning. Verified against a real `Scriptorium()`.
- [x] `ast.parse()` clean; quick regression pass and a real `Scriptorium()`
      construct/destroy cycle both still pass. Packaged `.exe` rebuilt
      (`FileVersion`/`ProductVersion` `2.24.0.0`), launched for real, alive
      and `Responding: True`. Real `scriptorium_config.json` confirmed
      untouched throughout.

**One real regex bug found and fixed while writing the deterministic test
cases above, not shipped as originally drafted from the note's own
snippet**: the Windows-path pattern's body character class
(`[^\r\n<>:\"|?*]+`) is permissive enough to include plain spaces, so two
path mentions on the same line — exactly the "reordered but unchanged"
scenario this audit must not flag — matched as one run spanning from the
first path clear through the connecting prose to the second path,
producing a spurious warning. Fixed by (a) also excluding whitespace from
the body class, and (b) splitting the pattern into a permissive body plus a
stricter final-character class that excludes trailing sentence punctuation
— the same shape the URL pattern already used, applied here for the same
reason once the first fix's whitespace exclusion made a genuinely
punctuation-adjacent path visible as a separate case. Re-ran the full
deterministic suite clean afterwards; recorded here since it's exactly the
kind of "looks correct against the note's own listed cases but fails one
of them for real" finding this project's methodology exists to catch.

**Not done this session, noted rather than silently skipped**: no live
Claude/Ollama round-trip was run against this specific feature. Unlike
v2.4/v2.11/v2.18's tone/prompt calibration, `audit_revision_fidelity()` is
a pure post-hoc function with no model involvement in its own logic, and
its integration into `_on_success()` was verified directly with a
synthetic `result` dict shaped exactly like a real backend response —
judged sufficient given the fourteen-case deterministic suite already
covers every scenario notes_021's own verification gate lists. A future
session running a real corpus through both backends (as the note's
"Calibration and verification gate" section suggests) would still be
worthwhile for tuning false-positive *rates* in practice, not for
correctness.

---

## Deferred / explicitly out of scope for v2.1–v2.13

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
- `anthropic-workspace-id` header — **resolved 2026-09-01, no code change.**
  Discovered while hand-testing v2.4: `call_anthropic()` never sent this
  header, and Mark's identity-linked (personal, unscoped/"multi-workspace")
  API key needs one (`HTTP 400`). Confirmed for real this session, against
  the live API with the actual configured key: the error is genuine —
  `"anthropic-workspace-id is required when authenticating with an
  identity-linked API key"` — and `call_anthropic()` already sends the
  correct three standard headers (`x-api-key`, `anthropic-version`,
  `content-type`); nothing was missing on Scriptorium's side beyond this one
  optional header. Per Anthropic's current docs
  (`manage-claude/authentication`, `manage-claude/workspaces`), the Console
  deliberately never lists the Default Workspace's own ID in Settings →
  Workspaces — which is why a prior session found no usable value there —
  but a **workspace-scoped key never needs the header at all**. Mark chose
  that fix over adding header-sending code: create a new Console API key
  scoped to a specific workspace (Settings → API keys → Create key → set
  Linked account to yourself → choose a workspace instead of leaving it
  unscoped) and swap it into Scriptorium's Settings. No `scriptorium.py`
  change needed; this is an account-configuration action, not a code defect.
  Was pre-existing and unrelated to v2.4 — would have affected a v2.3
  single-tone request identically.
- **Explorer drag-and-drop onto the Original pane** (notes_014 §3.1,
  notes_015 Feature 3) — not implemented. Both notes' own snippets stop at
  `DragAcceptFiles(hwnd, True)` and explicitly defer the actual
  `WM_DROPFILES` handling to "the usual follow-up". `DragAcceptFiles` alone
  does not deliver drops to a Tk app — without a `WndProc` subclass to
  intercept `WM_DROPFILES` and read the dropped path via `DragQueryFileW`,
  it would be dead code that looks like a feature but does nothing when a
  file is actually dropped. Revisit as its own properly-scoped session
  (real Win32 message-loop subclassing, needs hand-testing) rather than
  guessing at it inside v2.7. **Superseded, then shipped 2026-09-02**:
  notes_016 supplied the missing `WM_DROPFILES` subclass; implemented and
  verified as v2.15 above.

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
| notes_010 | 29 Aug | Grok | v2.0 | Closed by v2.1–v2.3; S1/S2 suspicions resolved (dismissed) in v2.6 |
| notes_011 | 31 Aug | ChatGPT / Codex | v2.0 | Closed by v2.1–v2.3, v2.5; S1/S2 resolved in v2.6 |
| notes_012 | 31 Aug | Lynne | v2.0 (delta) | Closed by v2.2–v2.3, v2.5 |
| notes_013 | 31 Aug | Mark / Codex | v2.3 | Closed by v2.4 |
| notes_014 | 1 Sep | Gale | v2.5 (delta) | Closed by v2.6 (icon/single-instance) and v2.7 (always-on-top, change summary); drag-and-drop deferred, superseded by notes_016 (see "Deferred") |
| notes_015 | 1 Sep | Antigravity | v2.5 (delta) | Closed by v2.6; its S1 "Confirmed" and S2 "Addressed" verdicts did not hold up against live re-testing — see v2.6 write-up |
| notes_016 | 1 Sep | Mark / Codex | v2.9+ (architecture) | Three-tone picker closed by v2.11 (found and fixed real embellishment bugs); user presets closed by v2.12 (one deliberate dialog-ownership deviation); retry transport closed by v2.13 (one stale-docstring fix noticed and corrected along the way); Explorer drag-and-drop closed by v2.15 (verified with a real synthetic WM_DROPFILES message end-to-end); rich CF_HTML clipboard diff scoped as v2.16, not yet implemented |
| notes_017 | 1 Sep | Lynne | v2.8 (delta) | Closed by v2.10 (typography/contrast, notice banner, busy motion, dialog chrome, backend labels; toolbar-wrap and character-level diffs deliberately not carried in, see v2.10 write-up) |
| notes_018 | 1 Sep | Zoe | v2.8 (delta) | Closed by v2.9 (Bugs 1–2/S2, 3–7, S1); S3 deliberately not fixed (informational only, see v2.9 write-up) |
| notes_020 | 2 Sep | Mark | v2.22 (hand-test diagnosis) | Closed by v2.22 |
| notes_021 | 2 Sep | Codex | v2.21+ (hardening) | Confirmed all five originally-requested areas already shipped by build 2.21; §2.1/2.2/2.3 closed by v2.23 (conflict feedback) + v2.24 (fidelity audit); §2.4 closed by v2.23; §2.5's cancellable retry transport not yet implemented (see v2.23's "notes_021 delivery plan"); §2.5's streaming groundwork explicitly deferred pending two open product decisions |

`scriptorium_notes_001.txt`, a near-duplicate of notes_014 written under
`AGENTS.md`'s (now-abandoned) `scriptorium_notes_[N].txt` draft-path
convention, was removed 2026-09-02 as pure archive clutter now that
notes_014's own findings are fully closed (v2.6/v2.7) — its one point of
divergence from notes_014 (`Scriptorium-256.ico` vs. notes_014's mistaken
`-128.ico`) carries no remaining information the implementation doesn't
already reflect. notes_016/017/018 also had to be renumbered on arrival:
all three independently computed "next available note number" as 001/002
against an empty view of `00_Drafts`, colliding with the historical archive
names in `01_Active`; renamed to 016–018 to continue this table's sequence.

All confirmed still-open as of 2026-08-31 by direct inspection of
`scriptorium.py` (v2.0, 1,297 lines): no `normalise_config`, no
`TimeoutError` handling, no `PRESETS`/`WRITING_PRESETS`, no
`<<Modified>>`/`KeyRelease` binding, no `accept_btn`, no `secrets` import,
no `_payload_object`/`_post_to_ui`/`_remember_for_undo`, and HEAD is missing
`scriptorium.spec` and `icon/`.
