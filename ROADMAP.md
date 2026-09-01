# Scriptorium Roadmap

**Read this file, `MEMORY.md`, and `AGENTS.md` at the start of every session.**
When Mark says "lets get started", that is the cue to open these three files
before doing anything else.

Current shipped version: **2.7** (always-on-top toggle, copyable change
summary — on top of v2.6's bug-diagnosis fixes). No unimplemented release is
currently scoped; drag-and-drop import remains deliberately deferred, see
"Deferred" below.

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

## Deferred / explicitly out of scope for v2.1–v2.7

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
- **Explorer drag-and-drop onto the Original pane** (notes_014 §3.1,
  notes_015 Feature 3) — not implemented. Both notes' own snippets stop at
  `DragAcceptFiles(hwnd, True)` and explicitly defer the actual
  `WM_DROPFILES` handling to "the usual follow-up". `DragAcceptFiles` alone
  does not deliver drops to a Tk app — without a `WndProc` subclass to
  intercept `WM_DROPFILES` and read the dropped path via `DragQueryFileW`,
  it would be dead code that looks like a feature but does nothing when a
  file is actually dropped. Revisit as its own properly-scoped session
  (real Win32 message-loop subclassing, needs hand-testing) rather than
  guessing at it inside v2.7.

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
| notes_014 | 1 Sep | Gale | v2.5 (delta) | Closed by v2.6 (icon/single-instance) and v2.7 (always-on-top, change summary); drag-and-drop deferred (see "Deferred") |
| notes_015 | 1 Sep | Antigravity | v2.5 (delta) | Closed by v2.6; its S1 "Confirmed" and S2 "Addressed" verdicts did not hold up against live re-testing — see v2.6 write-up |

A duplicate of notes_014's content also landed at
`notes/00_Drafts/scriptorium_notes_001.txt` under `AGENTS.md`'s newer
draft-path convention — same author/date, not reprocessed separately, left
in place rather than deleted unasked.

All confirmed still-open as of 2026-08-31 by direct inspection of
`scriptorium.py` (v2.0, 1,297 lines): no `normalise_config`, no
`TimeoutError` handling, no `PRESETS`/`WRITING_PRESETS`, no
`<<Modified>>`/`KeyRelease` binding, no `accept_btn`, no `secrets` import,
no `_payload_object`/`_post_to_ui`/`_remember_for_undo`, and HEAD is missing
`scriptorium.spec` and `icon/`.
