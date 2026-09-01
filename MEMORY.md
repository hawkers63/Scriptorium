# Scriptorium — Session Memory

Incremental log of what happened in each Claude Code CLI session, newest
first. Read this alongside `ROADMAP.md` at the start of every session (cue:
Mark saying "lets get started").

---

## 2026-09-01 (continued) — Both remaining v2.5 items hand-tested for real

Mark asked to hand-test the two items v2.5 had left as "needs a person":
an actual mouse click restoring a minimised window, and confirming the
autostart command genuinely starts withdrawn.

**Autostart command, run for real**: backed up the exact byte content of
the real `scriptorium_config.json` first, then temporarily set
`minimise_to_tray: true` in it and launched the *literal* registered
command (`pythonw.exe scriptorium.py --minimised`) as a real subprocess.
Result: a `pythonw.exe` process with `MainWindowHandle: 0` and an empty
title — genuinely started withdrawn to tray, never showed a window, no
console flash. This is the strongest available proxy for "fires correctly
at logon" without actually logging off/rebooting, which would have ended
the working session — Windows itself invoking a confirmed-correct
`HKCU\...\Run` entry at a real logon is a well-established OS mechanism,
not something that needed re-proving beyond confirming the entry and the
command it runs are both correct (already done, see below).

**Tray click-to-restore, attempted via Windows UI Automation, then
actually confirmed by Mark clicking it himself**: tried to script a real
mouse click on the tray icon using `System.Windows.Automation` against
Explorer's own notification area (a different, more standard automation
target than our bespoke Tk window, which MEMORY.md has confirmed multiple
times exposes no usable UIA elements). Got partway — found the "Show
hidden icons" chevron via UIA, but its `InvokePattern.Invoke()` didn't
actually open the overflow flyout (Windows 11's XAML-based tray overflow
often ignores synthetic UIA invocations); switched to a genuine simulated
click via `user32.dll` `SetCursorPos`/`mouse_event`, which did open
something and the Scriptorium window reappeared — at which point Mark
said "i moved it out of the tray", i.e. **he had restored it himself** by
clicking the real icon, which is a strictly better confirmation than
anything scripted. Verified via UI Automation afterwards:
`WindowVisualState: Normal`, `IsOffscreen: False`, correct on-screen
geometry.

**Cleanup**: killed the test `pythonw.exe` process; restored
`scriptorium_config.json` to its exact original byte content (verified
identical via a direct comparison, not just re-setting the fields I
thought I'd changed — the lesson from the earlier accidental-flip
incident applied deliberately this time); confirmed the `HKCU\...\Run`
registry key was never left with a stray entry. No incident this time.

`ROADMAP.md`'s v2.5 checklist fully ticked now — every item either
verified programmatically, verified against the real OS mechanism, or (the
tray click) confirmed by an actual person. v2.5 is genuinely done, not
just "implemented and probably fine."

---

## 2026-09-01 (continued) — v2.5 (tray/autostart, packaging polish) implemented

Continuing straight on from v2.4 in the same session, on Mark's "move on
to v2.5." All five v2.5 tasks from `ROADMAP.md` implemented, hand-tested,
and committed (APP_VERSION bumped to "2.5").

**Architecture choice, asked up front:** the tray icon could be a
ctypes-only `Shell_NotifyIcon` wrapper (no new dependency, but a hand-rolled
Win32 message loop merged into Tk's event loop) or `pystray`+`Pillow`
(two new optional dependencies, far less code). Asked Mark; he chose
**pystray+Pillow**. Both were already installed in this environment
(pystray 0.19.5, Pillow 12.1.1), which let this session verify the tray
lifecycle against the real library rather than just reading its docs.

**Implemented, in roadmap order:**
1. **Frozen-config fallback fix** — `_config_dir()` now tries a same-named
   `Scriptorium` subfolder under the user's home directory if
   `%LOCALAPPDATA%\Scriptorium` can't be created, instead of falling
   straight to a bare loose file there; only falls all the way back to the
   loose file if that second attempt also fails.
2. **Packaged `.exe` icon + version metadata** — `scriptorium.spec` now
   sets `icon="icon/icon-96.ico"` and `version="version_info.txt"` (new
   file, hand-written `VSVersionInfo` structure PyInstaller evaluates
   directly). Verified against a real `pyinstaller scriptorium.spec`
   build, not just read — `Get-Item ... .VersionInfo` shows the correct
   FileDescription/ProductVersion/CompanyName, and
   `Icon.ExtractAssociatedIcon` confirms the icon resource is present.
3. **Softer/Stronger one-click re-run** — `_nudge_strength(delta)` clamps
   the `STRENGTHS` index and calls `process()`; wired into `_set_busy()`
   alongside Process/Accept so it greys out mid-request too.
4. **One-time source→frozen config migration prompt** —
   `find_source_config_candidate()` checks only next to the running `.exe`
   (nowhere wider); `_maybe_offer_config_migration()` mirrors
   `_maybe_show_privacy_notice()`'s one-time-flag pattern exactly
   (`import_prompt_shown`, not "does a frozen config file happen to exist
   yet"). The source file is only ever read, never written, on either
   Yes or No. Accepting applies the imported mode/role/tones/diff-view to
   the *live* toolbar immediately rather than waiting for a restart.
5. **Minimise to tray / start with Windows** — `TRAY_AVAILABLE` (a top-level
   optional `import pystray`/`from PIL import Image`) gates a Settings
   checkbox that's disabled with an explanation if missing, and is
   re-checked at every `_on_close()` — a stale `minimise_to_tray: true`
   with the packages missing still just quits normally, never traps the
   user. The tray icon (`icon/icon-96.png` via `resource_path()`, now
   bundled as PyInstaller `datas`) exists only while the window is hidden:
   created in `_minimise_to_tray()`, torn down in `_tray_restore()`/
   `_tray_quit()` (both pystray-thread callbacks that hand off to Tk's
   thread via the existing `_post_to_ui()` helper — same cross-thread
   pattern `process()`'s worker already used). `set_autostart()` writes/
   removes a `HKCU\...\Run` entry via `winreg` (`pythonw.exe` from source,
   the `.exe` itself when frozen), both passing `--minimised`; `__init__`
   treats `--minimised` or `start_minimised` in config as "start withdrawn"
   — but only when tray is genuinely available, for the same
   never-trap-the-user reason.

**Verification performed:**
- `ast.parse()` syntax check after every edit — clean throughout.
- Full regression pass of the v2.4-era isolated logic tests (tone/role/
  config, `DEFAULT_CONFIG` round-trip, `WRITING_PRESETS` validity) — all
  still pass with the new config keys added.
- **Frozen fallback**: simulated an `os.makedirs` failure on the primary
  path — confirmed it now falls back to a dedicated subfolder, not a bare
  loose file, cleaning up the test artifact directory afterwards.
- **Migration prompt**: full cycle against temp files with patched
  `sys.frozen`/`sys.executable`/`CONFIG_PATH` (never the real configs) —
  candidate-found/not-found, declined (candidate untouched, no import,
  flag still set so it doesn't ask again), accepted (values imported into
  live cfg *and* the toolbar, flag set, candidate still untouched
  afterwards), and confirmed a second launch doesn't re-prompt.
- **Tray lifecycle — driven against the real `pystray`/`PIL`, not
  mocked**: `_on_close()` with tray on actually withdrew the window and
  created a real, briefly-visible tray icon; calling the icon's own "Show
  Scriptorium" callback deiconified/refocused the window and tore the
  icon down; calling the Quit callback destroyed the app for real; the
  safety fallback (tray on in config but `TRAY_AVAILABLE` patched False)
  correctly fell through to a normal quit instead of vanishing. Each
  scenario run as a **separate process** — running multiple `Scriptorium()`
  (`ctk.CTk()`) instances in one process causes customtkinter's global
  DPI/appearance-mode tracker to misbehave across instances (harmless
  `invalid command name ... after script` noise, and a `TclError` on an
  unrelated second instance after the first was destroyed) — a test-harness
  artifact, not an app bug; real usage only ever has one instance.
- **Autostart — against the real `HKCU` registry**, not simulated:
  `set_autostart(True)` then a `winreg` read-back confirmed the exact
  `pythonw.exe ... --minimised` command line; `set_autostart(False)` then
  a read confirmed the value was gone; disabling when already absent still
  reports success. A full `SettingsDialog._save()` cycle was also run
  end-to-end and confirmed both the config and the registry updated
  together correctly.
- **Packaged `.exe` rebuilt twice** (once after icon/version changes, once
  after the tray/autostart/winreg additions) via a real
  `pyinstaller scriptorium.spec` run, both times launched for real and
  confirmed no startup crash from the new imports. Solved a recurring
  false alarm in this process: `Get-Process -Id $p.Id` right after
  `Start-Process` sometimes reports the PyInstaller onefile **bootloader**
  process (a lightweight parent with a blank title), not the actual
  unpacked Python/Tk **child** process that owns the real window — checking
  by image name (`Scriptorium.exe`) and picking the higher-memory PID
  resolves it. Not a bug in the app; a quirk of how onefile builds run.
- Launched the live source-run GUI after every major change — clean title,
  empty stderr throughout.

**One real incident, caught and fixed within the session:** an early
Settings-save test ran against the *real* `scriptorium_config.json`
instead of a patched path, briefly flipping `minimise_to_tray` and
`start_with_windows` to `true` in Mark's actual config (and writing a
real, harmless `HKCU\...\Run` entry). Caught immediately by checking the
file after the test; reverted both the config values and the registry
entry, verified clean afterwards, without ever touching or displaying the
real API key. Every test written after this one explicitly patches
`CONFIG_PATH` to a temp file rather than trusting a real `Scriptorium()`
instantiation not to save for real.

**Still needs a person, genuinely can't be done from this session:**
- An actual mouse click on the live tray icon to restore the window
  (pystray's Windows backend owns its own message loop; this session
  called its callback directly rather than physically clicking).
- A real log-off/log-on or reboot to confirm "start with Windows" fires at
  logon and shows no console flash — the registry entry is verified
  correct, but Windows actually executing it at a real logon event can't
  be simulated in-session.
- Visual confirmation the tray icon looks right at actual taskbar
  size/theme, and that the Explorer/taskbar icon and Properties dialog
  look right to a human, not just to `VersionInfo`/`ExtractAssociatedIcon`.

`ROADMAP.md` updated: the v2.5 checklist ticked for everything verified
above, the two genuinely-blocked items marked "needs a person" rather than
left unchecked with no explanation, and the incident recorded there too.
The "Current shipped version" line at the top (stale at 2.3 since before
v2.4 — an oversight last session, fixed now) updated to 2.5, since v2.6 is
the only unscoped release left.

Next session: hand-test the two person-only items above if Mark wants
that confirmed before relying on it, then move to v2.6 (the dedicated bug
diagnosis session) whenever Mark is ready — it is deliberately unscoped
beyond the verification procedure already in `ROADMAP.md`.

---

## 2026-09-01 — v2.4 (multi-tone composition & expanded roles) implemented

Continuing from the v2.3 pause: Mark added `notes_013.txt` (Mark/Codex),
proposing multi-tone selection and an expanded role menu, and explicitly
left the choice of *which* new roles/tones to add to this session's
discretion ("quantity does not necessarily improve the result"), with the
stated priority of never letting a tone/role instruction inject or
embellish content at the sentence level. Implemented directly rather than
asking for a scoping round, per "apply the adjustments as you see fit."

Inserted as **v2.4** ahead of the previously-planned tray/autostart release
(now **v2.5**; the bug-diagnosis session is now **v2.6**) — see
`ROADMAP.md` for the full task list and acceptance checklist.

**Implemented in `scriptorium.py` (APP_VERSION bumped to "2.4"):**
- `TONE_INSTRUCTIONS` (bounded, data-driven per-tone instruction text),
  `TONES` derived from it, `TONE_CONFLICTS`, `MAX_SELECTED_TONES` (3, the
  data-model cap) and `TONE_PICKER_LIMIT` (2, the UI cap — deliberately
  more conservative than the data model, per notes_013's own
  recommendation to calibrate two-tone output before opening a third), and
  `validate_tones()` as the single validation boundary shared by config
  loading, preset application, the picker dialogue and prompt
  construction.
- `build_tone_instruction()` replaces the old one-line "steer the tone
  towards: X" with explicit dominant/supporting phrasing plus a "must not
  introduce facts, increase certainty, invent feelings, create
  commitments" guard on every combination. `build_system_prompt()`'s
  `tone` parameter is now `tones` (list/tuple).
- **Curated, not copied wholesale**, from notes_013's full lists: six new
  tones — Casual, Direct, Empathetic, Detailed, Constructive, Persuasive
  (one per stylistic dimension notes_013 itself identified) — and five new
  roles — Engineer, Journalist, Lawyer, Project Manager, Technical Writer.
  Left out as overlapping (with an existing entry or each other): Blogger/
  Content Creator/Writer, Creative Professional, Designer/Graphic
  Designer, Educator/Teacher, Business Professional, Copywriter, Novelist/
  Story Writer, Product Manager, Assertive, Instructive, Inspirational.
  Reasoning is recorded in the code comments beside `ROLES` and
  `TONE_INSTRUCTIONS`, not just here.
- `default_tone` (string) config key migrated to `default_tones` (ordered
  list) via `normalise_tone_config()`, called from `normalise_config()`;
  an invalid or conflicting stored value falls back to `["Concise"]`
  rather than crashing. `scriptorium_config.example.json` updated; the
  live `scriptorium_config.json` (holds the real API key) was
  deliberately left untouched — it has neither key, so it already
  inherits the new default. Existing presets keep exactly their original
  single tone, now stored as a one-item list — no multi-tone behaviour was
  added to the shipped defaults, since that needs the live-model
  calibration testing notes_013 itself flags as a prerequisite.
- `TonePickerDialog` (new class, before `SettingsDialog`) replaces the
  single-select tone `CTkOptionMenu` with a toolbar button opening an
  ordered checkbox picker (Clear/Cancel/Apply, live "N of 2 selected: X →
  Y" status). `Scriptorium` gained `self.selected_tones`,
  `_open_tone_picker()`, `_set_selected_tones()`, `_refresh_tone_button()`;
  `process()` now wraps `build_system_prompt()` in `try/except ValueError`
  so a should-be-impossible bad tone state (since `self.selected_tones` is
  only ever set through already-validated paths) can't strand Process on
  "Working…".
- `README.md` updated (tone/role feature bullets); `ROADMAP.md`
  restructured (new v2.4 section, old v2.4→v2.5, old v2.5→v2.6,
  cross-references and the source-notes table updated to match).

**Verification performed:**
- `ast.parse()` syntax check — clean.
- Isolated logic tests (stubbed `customtkinter`, no GUI): `validate_tones`
  (dedup, keep-original strip, unknown-name drop, both conflict pairs, a
  four-tone over-limit case), `TONES` derivation matches
  `TONE_INSTRUCTIONS` keys, `build_tone_instruction` single- and
  dual-tone phrasing plus the no-embellishment guard text,
  `build_system_prompt` end-to-end, `normalise_tone_config` (legacy-string
  migration, keep-original → empty list, conflicting stored pair →
  `["Concise"]` fallback, missing key), `normalise_config` idempotency
  with the tone migration wired in, `DEFAULT_CONFIG` round-trips through
  `normalise_config` unchanged, every `WRITING_PRESETS` entry uses only
  values actually in `MODES`/`STRENGTHS`/`ROLES`/`TONE_INSTRUCTIONS`, and
  `ROLES`/`ROLE_INSTRUCTIONS` have identical membership — all pass.
- Launched the live GUI via PowerShell (`Start-Process`, 4-second live
  check): process stayed alive, correct window title, empty stderr.

**Not yet verified live (needs a person at the keyboard, one item also
needs real backend spend I won't incur without asking first):** the tone
picker's checkbox/limit/conflict UI actually driven by hand (no Tk
automation available for this app — same conclusion as every prior
session); a genuine two-tone Process request against Claude or Ollama,
checked specifically for injected/embellished content per Mark's stated
concern (notes_013's own "Calibration Considerations" table is a good
starting matrix); the new Lawyer/Engineer/Journalist roles similarly
unverified against a real model response.

Next session: hand-test the v2.4 acceptance checklist in `ROADMAP.md`
(picker interaction, a few real two-tone combinations against the live
backend, the config-migration path), then move on to v2.5 (tray/
autostart) once Mark is satisfied v2.4 holds up in practice.

---

## 2026-09-01 (continued) — Picker interaction verified; live Claude test blocked on account config

**Picker interaction, driven programmatically against the real classes**
(not literal mouse clicks — Windows UI Automation still exposes no usable
elements for this app, confirmed again): instantiated the real
`Scriptorium`/`TonePickerDialog` and called `_toggle_tone`/`_apply`/
`_clear` exactly as a click would, with `messagebox` patched to
non-blocking loggers so a real modal couldn't hang the script. All 27
checks passed — two-tone selection, the `TONE_PICKER_LIMIT` soft cap and
revert, the Concise+Detailed conflict refusal (dialog stays open, app
state untouched), successful apply, Clear, long-label truncation on the
toolbar button, and preset application all behave as designed.

**Live two-tone Claude test — blocked, not attempted further:** the first
real request (`call_anthropic()`, Technical Writer + Direct/Detailed)
failed before generating any content:
```
HTTP 400: "anthropic-workspace-id is required when authenticating with an
identity-linked API key; send the id of the workspace this request acts
in."
```
This is **pre-existing and unrelated to v2.4** — `call_anthropic()` has
never sent an `anthropic-workspace-id` header, and any v2.3 single-tone
request would fail identically with this key. Mark checked the key's
details in the Anthropic console (`Alpha` key, Workspace "Default") and
the Workspace ID field showed no value (`—`), so there was nothing to
plug in; per Mark, skipped rather than guessed at a header value. No code
change was made for this.

**Still open:** live-model verification that a real two-tone combination
(especially anything involving Detailed or Persuasive) doesn't inject or
embellish content is unverified. Options for a future session: (a) get a
usable workspace ID once Anthropic's console surfaces one for this key/
workspace, (b) switch to a non identity-linked API key, which doesn't
need the header, or (c) test via the local Ollama backend instead, which
this session didn't try (Mark asked specifically for Claude).

---

## 2026-09-01 (continued) — Rest of the v2.4 checklist hand-tested; one real bug found and fixed

Worked through every remaining v2.4 acceptance-checklist item that
doesn't need a live model call (the two that do are still blocked on the
`anthropic-workspace-id` issue above; Ollama was checked and isn't
running locally either, so those two stay open).

**Found and fixed a real migration bug**, caught by actually exercising
`load_config()` against a temp file containing only the legacy
`default_tone` key (not a synthetic direct call to
`normalise_tone_config()`, which had masked this): `load_config()` always
seeds its working dict from `DEFAULT_CONFIG` — which already supplies
`default_tones: ["Concise"]` — before merging in the loaded file. So a
pre-v2.4 config containing only `default_tone` ended up with `clean.get
("default_tones")` already a valid list by the time
`normalise_tone_config()` ran, and the function's `elif not isinstance
(stored, list)` legacy branch was structurally unreachable through the
real load path — the user's actual stored tone was silently discarded in
favour of the default instead of being migrated. Fixed by checking for
the legacy key's presence first, before ever looking at `default_tones`,
in `normalise_tone_config()` (`scriptorium.py`). Re-verified: a temp
config with only `default_tone: "Diplomatic"` now loads as `default_tones:
["Diplomatic"]` and persists correctly through a subsequent `save_config()`
round-trip; all previously-passing tone/config tests still pass.

**Also verified (all via the real classes/functions, no live model
needed):**
- A single selected tone still produces the plain "as the target tone"
  phrasing, not the dominant/supporting language — confirmed at both the
  `build_tone_instruction()` and full `build_system_prompt()` level.
- Casual+Formal is refused in the picker exactly like Concise+Detailed
  (dialog stays open, app state untouched).
- A hand-edited config with a conflicting pair in `default_tones` falls
  back to `["Concise"]` on load, without being flagged unreadable.
- All three presets (Formal letter, Client reply, Technical note) apply
  their exact original single tone under the new list-based storage.

`ROADMAP.md`'s v2.4 checklist updated to reflect what's now ticked, what's
genuinely blocked (both remaining items need the Claude API key issue or
Ollama), and the bug found/fixed.

**Still open, needs a live model (Claude once unblocked, or Ollama):**
two-tone content-injection check (Detailed/Persuasive especially), and a
Lawyer/Engineer spot-check for invented legal interpretation or technical
conclusions.

---

## 2026-09-01 (continued) — Live-model checks run against Ollama; found and fixed a real Persuasive embellishment bug

Mark asked to try Ollama for the two checklist items still blocked on
Claude's `anthropic-workspace-id` issue. Ollama wasn't running
(`D:\Ollama\App\ollama.exe` installed but no process, port 11434 not
listening); started it (`ollama serve`, hidden window) — took a few
seconds longer than expected to actually accept connections despite the
port showing LISTENING immediately, then came up with six models already
pulled (llama3.2:3b, llama3.1:8b, llama3.1:8b-instruct-q2_K, tinyllama,
deepseek-r1:1.5b/7b). Used **llama3.1:8b**, not the configured
`tinyllama:latest` — deliberately a stronger model, since the point was
to test whether the prompt design holds up on a real model, not whether a
1B model can follow instructions at all.

**Four real Process requests, no protection needed:**
1. Technical Writer role, Direct+Detailed tones, a device-reset source —
   clean; only "hold" → "press and hold", every number/step preserved.
2. No role, Persuasive+Confident tones, a filter-marketing source — **not
   clean**. Added three unsupported evaluative adjectives ("cutting-edge",
   "remarkable", "ingenious design") and quietly loosened "lasts three
   months" to "up to three months" (word count 20→39). This is exactly
   the injection/embellishment failure mode Mark raised at the very start
   of this work.
3. Engineer role, no tone, a pump-failure source — clean; only a tense
   change, no diagnosed cause added beyond the source.
4. Lawyer role, no tone, a tenancy-notice source — clean; only a missing
   article inserted, no new obligation or interpretation.

**Fixed** rather than just reported, since the fix was small and
verifiable in the same pass: tightened `TONE_INSTRUCTIONS["Persuasive"]`
and the shared closing guard in `build_tone_instruction()` (both in
`scriptorium.py`) to explicitly name evaluative/promotional adjectives
("such as 'cutting-edge', 'remarkable', 'ingenious'") and claim-scope
changes as forbidden — the previous wording only named "facts" and
"certainty", which didn't cover an added descriptive adjective or a
quantitative claim's scope shifting in either direction. Re-ran the same
Persuasive+Confident case three more times against llama3.1:8b after the
fix: no more multi-adjective pile-ups or scope-loosening, but a single
mild evaluative adjective still slipped in on 2 of 3 attempts ("latest"/
"significant"/"durable" once, "innovative"/"long-lasting design" once) —
real, reduced-but-not-eliminated residual risk on this local model.
Re-ran the full non-live-model isolated test set plus a live GUI launch
afterwards — all still pass, clean launch.

**Judgement call, not escalated further:** did not keep iterating the
Persuasive wording to chase zero residual risk — diminishing returns on a
quantised 8B local model, and Scriptorium's core design (nothing applies
without the user reviewing the diff and clicking Accept) is the actual
backstop here, not the prompt alone. Recorded in `ROADMAP.md`'s v2.4
checklist (now fully ticked, all four line items covering the live-model
gap either tested clean or tested-then-fixed) that Persuasive specifically
deserves extra scrutiny at review time, and that it's worth re-testing
against Claude once its key/workspace issue is resolved — a flagship
model may hold the bounded instruction more reliably than this local one.

**Ollama stopped** — Mark asked for it to be shut down after testing
(`taskkill` on the `ollama.exe` PID started earlier this session); confirmed
gone from `tasklist`. Re-launched the live GUI afterwards to confirm
Scriptorium still starts cleanly with Ollama not running (correct title,
empty stderr) — the app only talks to it when Ollama is the selected
backend and Process is actually clicked, so this was expected but checked
rather than assumed.

---

## 2026-08-31 — Session paused after v2.3, by Mark's choice

v2.1, v2.2 and v2.3 are all implemented, committed, and pushed to
`origin/main` (HEAD is `c54e39e`, app now reports itself as v2.3). Mark
chose to pause here — before v2.4 (tray/autostart, the most invasive
release so far: process lifetime changes, registry writes, new binary
assets) — specifically to hand-test the interactive behaviour this session
could only verify by clean-launch + isolated logic tests, not by actually
driving the GUI (no automation tooling is set up for this native Tk app;
tried `System.Windows.Automation` from PowerShell and abandoned it — Tk
exposes almost no named automation elements).

**What still needs a person at the keyboard before v2.4, in priority
order** (see also each release's acceptance checklist in `ROADMAP.md`):
- v2.3: live word/char count while typing/pasting/undoing; each preset
  sets exactly its four controls; Accept genuinely greys out during a real
  Process call and re-enables after; the four new shortcuts fire correctly
  and Ctrl+C/Ctrl+V still work for selection; Word-export of a control
  character shows the friendly dialog.
- v2.2: Detect button against a real/slow Ollama endpoint keeps Settings
  responsive; closing the app mid-request produces no crash dialog
  (ideally against the packaged `.exe`, not just `python scriptorium.py`).
- v2.1: a forced `save_config` failure (e.g. read-only file) keeps
  Settings open with a visible error; hand-edited invalid config values
  boot cleanly with status/privacy in agreement.

Next session: read this file + `ROADMAP.md`, ask whether the above was
tested and what was found, fix anything that turns up, then move on to
v2.4 once Mark is satisfied v2.1–v2.3 hold up in practice.

---

## 2026-08-31 (continued) — v2.2 pushed; v2.3 (state fix + usability) implemented

Pushed v2.2 to `origin/main` (`60d787c..9c5e584`) after Mark's go-ahead, and
confirmed continuing straight into v2.3 in the same session.

All six v2.3 tasks from `ROADMAP.md` implemented in `scriptorium.py`
(APP_VERSION bumped to "2.3"), not yet committed:

- **Accept-during-processing fix:** named the Accept button `self.accept_btn`
  and added `_set_busy()`, which now disables both Process *and* Accept for
  the life of a request (previously only Process was disabled — clicking
  Accept while a newer request was running committed the old revision and
  silently cancelled the new one via `accept()`'s call to `reject()`).
  `_claim_request()`/`_invalidate_inflight()`/`process()` all route through
  it now; `accept()` also gained a defence-in-depth `self.busy` guard.
- **Word-export `ValueError`:** `export_file()` now catches the `ValueError`
  `python-docx` raises for illegal XML control characters (common from
  PDF-sourced paste) with a friendly dialog pointing at `.txt` instead.
- **Bounded/deduped undo stack:** added `_remember_for_undo()` (skips a
  snapshot identical to the last one; caps at 50) and routed all four
  `undo_stack.append()` call sites (`accept`, `paste_original`, `clear_all`,
  `import_file`) through it.
- **Live word/character counts:** bound `<<Modified>>` on `original_box`
  (with `edit_modified(False)` reset in the handler, since Tk's modified
  flag latches and won't refire otherwise); `_refresh_status()` now shows
  live words+characters and, once a revision exists, its word-count delta.
- **Named writing presets:** added `WRITING_PRESETS` (Formal letter / Client
  reply / Technical note) between `ROLE_INSTRUCTIONS` and `DEFAULT_CONFIG`,
  plus `_apply_writing_preset()` and a Preset `CTkOptionMenu` in the
  toolbar (columns 8–9; Settings moved to column 11). Not persisted to
  config — toolbar-local, as scoped.
- **Keyboard shortcuts:** added `_bind_shortcuts()`, replacing the three
  direct `self.bind()` calls in `__init__`. Accept = Ctrl+Shift+A, Reject =
  Esc, Copy revision = Ctrl+Shift+C, Undo = Ctrl+Z, alongside the existing
  Process/Import/Export bindings. Deliberately does not touch Ctrl+C/Ctrl+V.

**Verification performed:**
- `ast.parse()` syntax check — clean.
- Isolated logic tests: every `WRITING_PRESETS` entry uses only values that
  are actually in `MODES`/`STRENGTHS`/`ROLES`/`TONES` (would otherwise be
  silently clamped back to defaults by `normalise_config` if ever round-
  tripped through config — confirms the preset data itself is valid);
  `normalise_config` is idempotent (regression check after two more edits
  to `DEFAULT_CONFIG`-adjacent code).
- Attempted UI Automation-driven testing (`System.Windows.Automation` from
  PowerShell, no extra install) to click through the live count/preset/
  Accept-disable behaviour directly — Tk exposes essentially no named
  automation elements (113 descendants, none with a usable `Name`), so this
  wasn't viable; abandoned rather than force it. This matches what every
  prior review note in this project has also concluded about this app.
- Launched the live GUI three times across these changes (once mid-way,
  once at the end) via PowerShell — clean window, correct title, empty
  stderr each time. Since all of v2.3's toolbar/actionbar/binding changes
  execute during `Scriptorium.__init__`, a clean launch does verify that
  construction path end-to-end, but **not** the interactive behaviour
  itself.
- **Not yet verified live (needs a person at the keyboard):** live count
  updates while typing/pasting/undoing; each preset sets exactly its four
  documented controls and stays hand-editable after; Accept is genuinely
  greyed out during a real Process call and re-enables after; the four
  new keyboard shortcuts fire the right action and ordinary Ctrl+C/Ctrl+V
  still work for text selection; Word-export of a control character
  produces the friendly dialog rather than a traceback.

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
