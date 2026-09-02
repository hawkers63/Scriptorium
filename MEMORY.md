# Scriptorium — Session Memory

Incremental log of what happened in each Claude Code CLI session, newest
first. Read this alongside `ROADMAP.md` at the start of every session (cue:
Mark saying "lets get started").

---

## 2026-09-02 (continued) — v2.17: readability metrics + keyboard-shortcut dialog (notes_019, items 1-2)

Mark reviewed notes_019 (the fresh feature review Claude wrote as the
enhancement-architect role, distinct from notes_016) and approved all five
proposals: "Please proceed with the development of the five new features."
Implementing in the risk order the note itself proposed, as separate
versioned releases per this project's own standing convention rather than
one grab-bag change.

**v2.17 bundles the two lowest-risk items** (both pure UI, no prompt/model
surface touched): Flesch-Reading-Ease-derived readability grade + reading
time in the status bar (only shown at 20+ words, since fewer can't produce
a meaningful score), and an F1-triggered `ShortcutsDialog` listing the eight
keyboard bindings `_bind_shortcuts()` already registers but that were
previously undiscoverable anywhere in the running app. Full task detail and
acceptance evidence in `ROADMAP.md`'s v2.17 section.

Ships ahead of v2.16 (the still-unstarted rich clipboard diff) in version
number — v2.17 was simply ready first and carries none of v2.16's raw-Win32
risk. `ROADMAP.md`'s "Current shipped version" line updated to 2.17,
v2.18-v2.20+ noted as the remaining approved notes_019 items now in
progress.

**Verification**: `ast.parse()` clean; `reading_metrics()` checked directly
against real easy/hard/empty/short text samples; a real `Scriptorium()`
confirmed the status bar shows no metric below the 20-word floor and shows
one above it; `_show_shortcuts()` (both called directly and via a real
`<F1>` `event_generate`) confirmed to open exactly one `ShortcutsDialog`,
no duplicates on repeat triggers. Real packaged `.exe` rebuilt
(`FileVersion`/`ProductVersion` `2.17.0.0`), launched for real against the
live config, alive and `Responding: True`. Real `scriptorium_config.json`
confirmed byte-identical throughout.

Continuing straight into the remaining three notes_019 items in the same
session.

---

## 2026-09-02 (continued) — v2.15.2: real hand-test confirms drag-and-drop; fixed a second, unrelated toolbar bug it also caught

Mark did the one manual check flagged as needing a person: dragging a real
file from Explorer onto Original. **It worked correctly** — closes out the
one open verification gap from the v2.15.1 crash fix (the `GlobalAlloc`
cross-process limitation noted there was specific to synthetic testing, not
a real defect; a genuine Explorer drop goes through the OS's own OLE
compatibility shim and works as designed).

While hand-testing, Mark also found a second, **unrelated** bug: the
toolbar's "⚙ Settings" button was positioned off-screen at the app's default
window size, only reachable by manually widening the window (his own
screenshot, `wider.jpg`, showed this directly). Full technical detail is in
`ROADMAP.md`'s v2.15 section; worth noting here that this is the *same class*
of bug as v2.14's action-bar fix (content wider than the window, no session
had ever checked), just on the toolbar row and pre-dating both v2.14 and
v2.15 entirely — latent since whichever of v2.4/v2.12 first grew the
toolbar's own content past the point where a weighted spacer column plus a
button could still fit in 1180px. **Fixed per Mark's own suggested
placement**: moved from a grid column pushed to the toolbar's far right, into
`bar2` (row 2 of the bottom action bar), right-aligned so it sits directly
beneath "Export…". Verified against the real widget tree (toolbar now totals
~1159px of 1180px available) and a real screenshot showing the new
placement.

Shipped as **2.15.2.0** (display string `APP_VERSION` stays `"2.15"`, same
reasoning as 2.15.1 — this is a fix within the v2.15 release, not a new
feature). Not yet pushed at time of writing — pending Mark's go-ahead, same
convention as every prior release.

---

## 2026-09-02 (continued) — v2.15 hand-testing: found and fixed a real crash the initial push missed

Mark's next instruction after the v2.14/v2.15 push-and-pause was "hand-test
v2.14/v2.15 on the real exe before v2.16" — exactly the right call, since it
caught something the shipped v2.15 (below) did not: a **genuine fatal crash**
on a real cross-process drop, not a cosmetic issue. Full technical detail and
the fix are in `ROADMAP.md`'s v2.15 section (the "Found and fixed after the
initial push" note); the process worth recording here since it's a real
lesson about this project's own verification discipline, not just the bug:

**The v2.15 acceptance checklist's own "verified end-to-end" claim was true
but incomplete** — it tested `SendMessageW` called *from within the same
process* as the target window, which is not a genuine cross-process drop and
did not exercise the actual failure mode. Hand-testing against the real
packaged `.exe`, sending a real `WM_DROPFILES` from a genuinely separate
process (PowerShell, standing in for Explorer), reproducibly killed the
target process with `Fatal Python error: PyEval_RestoreThread: ... GIL is
released ... thread state is NULL` — every single time, five times running,
each against a completely clean process list (ruling out a leftover-process
confound before concluding it was real). The crash surfaced on the
*single-instance restore-listener* thread (`_watch()`), which has nothing to
do with drag-and-drop directly — a classic "corruption manifests somewhere
else" native-level bug, which is exactly why it took a systematic
clean-room reproduction (kill everything, launch one instance, confirm it's
alone, *then* drop) rather than a quick read of the traceback to actually
pin down.

**Root cause, and why it's notable**: `_capture_file_drop()` — both in
notes_016's own reference snippet and the version shipped here — called back
into Tk (`self.after_idle(...)`, and in one intermediate attempt
`winfo_containing()` directly) *synchronously from inside the native window
procedure*. This is a flaw in the **reviewed design itself**, not something
introduced while adapting it — worth remembering next time a "reviewed,
not improvised" design is trusted for a high-risk Win32 feature: reviewed
still means verify the actual runtime behaviour, especially anything
involving Tcl/Tk re-entrancy, which is exactly the kind of thing a design
review on paper is least likely to catch.

**Fix**: the window procedure now touches only ctypes/Win32 state plus a
plain Python list; a new `_poll_dropped_files()`, scheduled via an ordinary
`self.after(100, ...)` call made from *outside* the window procedure (never
nested inside it), is the only thing that ever calls back into Tk for a
drop. Re-verified clean across repeated real cross-process drops (including
deliberately bad ones) with zero crashes, plus a 15-second idle control run
and the original same-process happy-path test, both still passing.

**A genuine, disclosed verification gap, not swept under the rug**: chasing
this down further surfaced a second, more fundamental limit —
a hand-rolled `HDROP` built via `GlobalAlloc` in an external test process and
delivered via a raw `SendMessageW` cannot actually be read by the target
(`ERROR_INVALID_HANDLE`), because `GlobalAlloc` handles are process-private
in modern Windows; a real Explorer drop only works because the OS's own
OLE/`DragAcceptFiles` compatibility shim re-allocates the `HDROP` inside the
target process before delivery, which a synthetic cross-process message
bypasses entirely. This means the crash fix and the hit-test/file-load logic
are both verified with high confidence, but a genuine OS-mediated
Explorer-to-Scriptorium drop landing content correctly has **not** been
independently confirmed — flagged explicitly in `ROADMAP.md` as needing a
real person to drag one real file, rather than claimed as done on the
strength of everything-but-that being green.

Patched build rebuilt as **2.15.1.0** (`version_info.txt` only —
`APP_VERSION` stays the display string `"2.15"`, since this fixes the same
feature rather than shipping a new one) specifically so it's distinguishable
from the original `2.15.0.0` that was pushed with the crash still in it.
`ROADMAP.md`'s v2.15 section updated in place with the incident, the fix, and
the disclosed gap; not a new dated section, since this is the same release
being corrected, not a new one.

---

## 2026-09-02 (continued) — v2.15: Explorer drag-and-drop, verified with a real synthetic WM_DROPFILES message

Continued from v2.14 in the same session. Mark's original instruction for
the session ("start v2.14 drag-and-drop") had been paused for the v2.14
hand-testing detour; after v2.14 shipped and pushed, Mark gave an explicit
go-ahead to start this — the first time this project's own "confirm risk
appetite before the raw-Win32 items" checkpoint has actually been exercised
rather than deferred (see [[project_v24_status]]). Full task list and
acceptance evidence in `ROADMAP.md`'s v2.15 section; worth expanding on here:

**Implemented essentially as notes_016 §2.1/3.2 specified, not improvised
fresh** — deliberately, given this is flagged (correctly) as the highest
single-bug blast radius in the whole backlog: a bad `WNDPROC` can hang or
crash the whole app, not just one feature. Adapted only to the current
file's structure (line numbers had drifted six versions since the note was
written) and to preserve `import_file()`'s exact existing error-message
wording rather than the note's own slightly different phrasing — a
deliberate "smallest safe change" call, not an oversight: the note's own
`_read_document_path()`/`_load_file_path()` split was followed, but the
shared loader's exception handling was written to reproduce the pre-existing
dialogs byte-for-byte rather than adopt the note's rewording.

**Verification leaned on a genuinely synthetic-but-real `WM_DROPFILES`
message, not a mocked call** — this was the one place in the whole session
worth the extra rigor. Built a real `DROPFILES` structure in `GlobalAlloc`'d
memory (test-harness-only Win32 code — `GlobalAlloc`/`GlobalLock`/
`ScreenToClient`/`SendMessageW`, none of it shipped in `scriptorium.py`
itself) containing a real temp `.txt` file's path, computed the correct
client-relative drop point via `ScreenToClient()` against `original_box`'s
actual on-screen centre, then called `SendMessageW()` directly against the
live, already-subclassed `_drop_hwnd` — exercising the real installed
window procedure end-to-end (proving `SetWindowLongPtrW` genuinely replaced
it and `_capture_file_drop`/`_handle_dropped_paths`/`_load_file_path` all
fire correctly), not a direct Python call standing in for that plumbing.
Result: `SendMessageW` returned `0` (the handler's own return value,
confirming real interception rather than fallthrough to the original
procedure), the real file's exact content landed in `original_box`, and the
status bar updated correctly. Followed up with two more targeted checks:
teardown (`_quit_app()`, not `destroy()` directly — confirmed
`_drop_hwnd`/`_drop_old_wndproc`/`_drop_wndproc` all reset to `None` and no
crash/hang before the window is actually destroyed) and five edge cases
(drop outside Original, unsupported extension, directory, multiple files,
zero files — all correctly rejected with `original_box` left untouched,
`messagebox` patched to non-blocking recorders so a real modal couldn't hang
the test).

**Also implemented, low-risk**: `_load_file_path()`/`_read_document_path()`
now shared between the Import dialog and a completed drop — the dialog's own
long-standing "accept whatever the user explicitly picks" behaviour is
unchanged; only the new drop path gets the narrower `.txt`/`.md`/`.docx`
extension gate notes_016 called for, applied in `_handle_dropped_paths()`
rather than the shared reader, specifically so it doesn't retroactively
tighten the existing dialog's behaviour.

**Verification**: `ast.parse()` clean; real packaged `.exe` rebuilt,
`FileVersion`/`ProductVersion` confirmed `2.15.0.0`, launched for real
against the live config (both bootloader and child process alive,
`Responding: True`, correctly hidden per `start_minimised` — no crash from
the new ctypes declarations at import time). Real `scriptorium_config.json`
confirmed byte-identical throughout — every test used an isolated temp
config. Every diagnostic process cleaned up afterwards, same discipline as
v2.14.

`ROADMAP.md` restructured: v2.15 is its own shipped section (drag-and-drop
only); the remaining notes_016 item (rich `CF_HTML` clipboard diff) split
out as its own **v2.16**, not bundled with drag-and-drop, per this project's
established one-focused-release-per-risk/theme pattern; "Current shipped
version" updated to 2.15.

---

## 2026-09-02 (new session) — v2.14: action-bar/status-bar visibility, button rearrangement, autostart

Mark opened with "start v2.14 drag-and-drop", then immediately shared a
hand-testing screenshot (`01.jpg`) instead: the app no longer starts
minimised with Windows, and the two-row action bar plus the status bar from
v2.8 onward were entirely missing — only the toolbar and the Original/
Suggested panes showed. Per the v2.7→v2.8 precedent, paused the planned
v2.15 (renumbered from v2.14+) Win32 work and ran a hand-testing fix pass
instead. Full detail and acceptance evidence in `ROADMAP.md`'s v2.14 section;
the two things worth expanding on here:

**The missing action bar/status bar was a real, root-caused `pack()` bug, not
a cosmetic regression** — confirmed by constructing the real `Scriptorium()`
against an isolated temp config and reading `winfo_reqheight()`/
`winfo_manager()` directly off the live widget tree. The panes frame's own
natural minimum height (852px, driven by `revised_box` — a plain `tk.Text`
that has never had an explicit `height=`, so it defaults to Tk's built-in 24
rows) exceeds the 760px the default `1180x760` window has left after the
48px toolbar. `pack()` carves its cavity in packing order regardless of
`side`: since the panes frame (built by `_build_panes()`, `expand=True,
fill="both"`) was packed *before* the action bar/status bar in `__init__`, it
claimed the entire remaining cavity for itself the instant it was packed,
leaving the later-packed `bar`/`bar2`/`status` with `manager="pack"` but an
actual height of 1px and `winfo_ismapped()` False. **Not a new regression
from any single version** — v2.8's own verification, when the action bar was
first split into two rows, checked only button-row *widths* against the
window width, never whether the two rows plus the status bar fit
*vertically* underneath the panes' own minimum height; no session since
(v2.9-v2.13) ever re-checked this either, all relying on "process constructs
and stays alive" checks rather than a real layout screenshot. Fixed by
building the action bar and status bar into one `_bottom_frame`, packed
`side="bottom"` *before* `_build_panes()` runs, so its combined 112px is
always reserved first; the panes still compress via their own existing grid
row-weight to fill whatever's left (~590-600px instead of their 852px wish),
exactly as they were already doing at 702px before this fix, just more so.
The on-demand ambiguity banner (`notice_frame`) was reparented onto
`_bottom_frame` too, since `_show_ambiguities()`'s `pack(before=self.status)`
needs a shared master — verified this doesn't raise and still
attaches/detaches correctly (`winfo_manager()` `"pack"` then `""`).
Screenshotted for real afterwards via `PrintWindow` (this project's usual
UI-automation gap doesn't block a raw window capture): toolbar, both panes,
both action-bar rows and the status bar all visible and correctly
positioned. Mark separately asked, mid-session, to move Clear/Import/Export
from row 2 onto row 1 (right-aligned after Undo), leaving row 2 as
Paste/Copy only — done; row 1 now requests 1124px of 1156px available at the
default window width (fits, but tighter than before — flagged in
`ROADMAP.md` as likely to crowd if resized down toward the 920px `minsize`,
not pre-emptively fixed since it wasn't asked for).

**"No longer starting with Windows minimised" was a real but different bug
than it looked like — the app-level code wasn't broken, autostart itself
was never wired up on this machine.** Directly tested the real packaged
`.exe` against Mark's actual saved config (`start_minimised`/
`minimise_to_tray`/`start_with_windows` all already `true` in it): launched
with no visible window at all, confirmed via a full `EnumWindows` scan
finding nothing titled "Scriptorium" and both the bootloader and child
process showing `MainWindowHandle: 0`. Then checked `HKCU\...\Run` directly
and found **no `Scriptorium` value there at all** (confirmed unambiguously —
`Get-ItemProperty -Name Scriptorium` returned null while the key's other
~8 entries listed fine). A `true` value in the config JSON does not itself
create this registry entry; only `set_autostart(True)`, called from
`SettingsDialog._save()`, does — so nothing was actually launching
Scriptorium at logon at all, on any version, not "launches but fails to
minimise". With Mark's explicit go-ahead ("yes please do"), wrote the exact
command line `set_autostart(True)` would produce for the frozen case
(`"C:\Scriptorium\dist\Scriptorium.exe" --minimised`) directly to the real
registry, then verified for real by launching that exact command line as a
subprocess: produced a `Scriptorium.exe` process with `MainWindowHandle: 0`,
`Responding: True` — genuinely starts withdrawn to tray now, matching the
v2.5 verification precedent. Root cause of how the registry entry went
missing wasn't established (no direct evidence either way) — noted as
possibly never actually saved through Settings on this install, or removed
by one of the cleanup tools already implicated in this project's v2.8
`_MEI...` incident, but not chased further since Mark didn't ask for that.

**Verification**: `ast.parse()` clean; real `.exe` rebuilt via
`pyinstaller scriptorium.spec`, `FileVersion`/`ProductVersion` confirmed
`2.14.0.0`. Real `scriptorium_config.json` confirmed byte-identical
(unchanged mtime) throughout every layout test (all used an isolated temp
config); the only real-machine state touched was the explicitly-approved
registry write. Every diagnostic `Scriptorium.exe`/`python` process launched
during testing was cleaned up afterwards (`Stop-Process -Force` plus the
resulting orphaned `_MEI######` extraction folder removed, same expected
onefile-forced-kill artefact as prior sessions).

`ROADMAP.md` restructured: new v2.14 section (this work) inserted ahead of
the renumbered v2.15+ (the two raw-Win32 items, formerly labelled v2.14+ as
a placeholder); "Current shipped version" updated to 2.14. Committed and
pushed after explicit confirmation.

Mark then gave an explicit go-ahead to resume the session's original
instruction (drag-and-drop, now v2.15) in the same round of questions that
approved the v2.14 push — see the entry above for that work.

---

## 2026-09-02 — Three new review notes triaged; v2.9 (bug-fix pass) implemented

Mark opened the session with three new notes already sitting in
`notes/00_Drafts/` (notes_016 Mark/Codex architecture proposals, notes_017
Lynne UI/UX audit, notes_018 Zoe bug hunt) and delegated the scoping
decision entirely ("decide which items to implement and which to defer ...
your decisions have my full support").

**First, a repo-hygiene fix, not part of the review content itself**: all
three notes had independently computed "next available note number" as
001/002 (against an apparently-empty view of `00_Drafts`), colliding with
the historical archive filenames in `notes/01_Active/`. The working tree
already had the fix half-done (uncommitted renames to notes_017/018) from
before this session started; committed it as a clean `git mv`-equivalent
rename, plus removing `scriptorium_notes_001.txt` (a near-duplicate of the
already-fully-closed notes_014, pure clutter at this point).

**Scoping decision**: rather than one grab-bag release, split the three
notes' very different content into staged versions:
- **v2.9** (this session, done): every concrete bug notes_018 found —
  correctness fixes only, no visual or prompt-generation surface touched.
- **v2.10** (scoped in `ROADMAP.md`, not yet implemented): notes_017's
  visual/UX polish — pure appearance, [[mark_meaning_preservation_priority]]
  doesn't apply.
- **v2.11+** (scoped, not yet implemented): notes_016's five proposals,
  sequenced by risk — three-tone picker first (small, but touches the
  prompt so needs the same live-model calibration discipline as v2.4),
  then user presets, then the retry transport, then the two raw-Win32 items
  (drag-and-drop `WNDPROC` subclassing, hand-rolled `CF_HTML` clipboard)
  last, since this project's history shows Win32-level features carry the
  highest single-bug blast radius and need the most hand-testing.

**v2.9 implemented and verified** (full detail and acceptance evidence in
`ROADMAP.md`'s v2.9 section); the two non-obvious parts:

**Bug 3 (the one worth flagging specially)**: the v2.8 "fix" for the
`_MEI.../base_library.zip` temp-dir crash computed `runtime_tmpdir` with
`os.environ.get("LOCALAPPDATA", ...)` *inside `scriptorium.spec`* — which
runs at PyInstaller *build* time, baking the builder's own account path
into the bootloader. Confirmed by scanning the rebuilt `.exe`'s bytes: the
old spec would have embedded an already-expanded `C:\Users\<builder>\...`
path; the fix (a literal `r"%LOCALAPPDATA%\Scriptorium\runtime"` string) is
now confirmed present unexpanded in the binary, letting PyInstaller's own
bootloader do the per-user expansion at run time as documented. Rebuilt,
launched for real, extracted to the correct per-user path, survived a
15-second soak. True cross-account portability wasn't exercised (would need
a second Windows account), but the binary-level confirmation is the direct
fix for the root cause, not just a claim.

**Suspicion S1, treated as a real fix rather than deferred**: notes_018
flagged (as a "product decision, not a confirmed defect") that
`normalise_config()`'s generic enum-clamp loop included `"backend"`,
silently rewriting a mistyped value (e.g. `"Ollama"`) to `"anthropic"`
*before* `run_backend()`'s own fail-closed check — added in v2.1
specifically to stop the status bar and actual HTTP dispatch from
disagreeing about whether text leaves the machine — ever saw it.
`run_backend()`'s own docstring already admitted this dead-code situation.
Given v2.1's precedent already settled the underlying product question
("never silently fail open to the cloud"), judged this a regression rather
than a genuinely open discretionary choice and fixed it: `backend` is no
longer clamped, so an invalid stored value now surfaces as a real
`BackendError` instead of a silent cloud switch; a genuinely missing key
still defaults to `"anthropic"` as before.

**Also fixed**: `always_on_top` added to the boolean-normalisation list
(Bug 1); `_kernel32()` helper adds proper `HANDLE`/`BOOL`/`DWORD`
argtypes/restype and NULL-handle checks to the mutex/restore-event code,
closing both Bug 2 and Suspicion S2 (64-bit `HANDLE` truncation) together;
`load_config()` now reads `utf-8-sig` so a BOM-prefixed config isn't
rejected as unreadable (Bug 6); `scriptorium_config.example.json` gained
the missing `always_on_top` key (Bug 7); tray-icon load failure now shows a
`messagebox.showwarning` instead of a `print()` invisible in the packaged
`.exe` (Bug 5, partial — only the tray-icon case, the note's two
"optional" automatic-save-warning cases were left alone). Suspicion S3
(Reject doesn't abort the in-flight HTTP call) deliberately left as-is —
the note itself says it's informational, and the actual requirement (no
stale result reaches the UI) is already met by the existing request-id
mechanism.

**Verification**: `ast.parse()` clean; a real isolated test script exercised
every fix against the actual functions (stringy-boolean clamp, mistyped
vs. missing vs. valid backend + `run_backend()`'s real raise, a real
BOM-prefixed temp config through the real `load_config()`, a stubbed-NULL
`CreateMutexW` through the real `_claim_single_instance()`); full regression
pass (WRITING_PRESETS validity, `DEFAULT_CONFIG` round-trip, `ROLES`/`TONES`
membership, `validate_tones`) all still pass; a real `Scriptorium()`
constructed and destroyed cleanly from source with no exception (bypassing
the single-instance mutex deliberately, see incident below, rather than
going through `main()`); the tray-icon-failure path verified by patching
`resource_path()` to a nonexistent directory and recording
`messagebox.showwarning` calls against the real `_minimise_to_tray()`. The
real `scriptorium_config.json` (holds the live API key) confirmed
byte-identical (same mtime) throughout — nothing this session touched it.

**Incident, handled correctly**: a stray `Scriptorium.exe` (v2.8, both
bootloader and child process, same PID-confusion pattern as
[[scriptorium_testing_gotchas]]) was already running before the rebuild
step, predating this session. Asked Mark before closing it (nothing
persists except via Export) — confirmed, closed cleanly, rebuild and
real-launch verification proceeded without incident.

`ROADMAP.md` updated: v2.9 section with full acceptance evidence, v2.10 and
v2.11+ scoped (not started), "Current shipped version" line updated to 2.9,
source-notes table extended for notes_016/017/018, the drag-and-drop
"Deferred" entry marked superseded by notes_016's complete proposal.

Continued straight into v2.10 the same session — see the entry below.

---

## 2026-09-02 (continued) — v2.10 (notes_017 visual/UX polish) implemented

Moved straight from v2.9 into v2.10 in the same session (Mark: "We will see
how much ground we can cover in this session"). All six cherry-picked
notes_017 items implemented and verified (full list and acceptance evidence
in `ROADMAP.md`'s v2.10 section); the two worth expanding on here:

**Testing this without any GUI automation available** (the long-standing
gap for this Tk app) leaned harder than usual on `winfo_manager()` rather
than `winfo_ismapped()` as the pack-state probe: constructing `Scriptorium()`
directly (to dodge the single-instance mutex, same technique used in v2.9)
never calls `mainloop()`, so the root itself is never actually mapped to a
screen, and `winfo_ismapped()` reads `False` for every descendant
regardless of real `pack()`/`pack_forget()` state — a test-harness artefact
discovered while writing the check, not a fix to the app. `winfo_manager()`
(`"pack"` vs. `""`) reports the packer registration directly and isn't
fooled by the unmapped root, so it became the reliable probe for the notice
banner and the Working… progress bar both attaching/detaching correctly.

**Backend labels needed a translation layer, not just a relabel**: swapping
`CTkSegmentedButton`'s `values=["anthropic","ollama"]` for
`["Claude","Ollama"]` would have made `backend_var` *store* the display
label directly — which, after v2.9's S1 fix removed the enforced
`anthropic`/`ollama` enum-clamp from `normalise_config()`, would have sent
a literal `"Claude"` straight to `run_backend()` and raised a spurious
`BackendError` on every single Settings save. Added `BACKEND_LABELS`/
`BACKEND_IDS` as an explicit two-way mapping instead: the segmented button
shows/edits the label, `_refresh_state()` and `_save()` both translate
through `BACKEND_IDS` back to the internal id, and the stored config
never sees anything but `"anthropic"`/`"ollama"`. Verified end-to-end
through a real `_save()` call against a temp config path, not just read:
confirmed the file on disk holds `"ollama"`, not `"Ollama"`.

Also implemented: pane typography/background match (`PANE_BG`/`PANE_FG`/
`PANE_FONT` tokens shared by both `original_box` and `revised_box`); diff
tag background fills (`DIFF_INS_BG`/`DIFF_DEL_BG`) alongside the existing
foreground colours (`DIFF_INS_FG`/`DIFF_DEL_FG`, the deleted-red also
brightened from the old tight-AA `#e06c75` to `#ffa0a8`); the ambiguity
strip replaced by a proper `notice_frame`/`notice_label`/Dismiss-button
combo (`_show_ambiguities()` rewritten around it); an indeterminate
`CTkProgressBar` plus a Process-button colour pulse driven from `_set_busy()`
or a long call now shows visible motion instead of only a static label;
`bind_dialog_chrome()`/`position_over_parent()` shared helpers wired into
both `TonePickerDialog` and `SettingsDialog` for `<Escape>` +
`WM_DELETE_WINDOW` + same-monitor centring; `SettingsDialog` rebuilt around
a `CTkScrollableFrame` body with the Save/Cancel row pinned outside it via
`side="bottom"`, geometry shrunk from a fixed 780px-tall non-resizable
dialog to 520×640 with `resizable(False, True)` and a 480×420 floor, so it
no longer clips at 150% DPI or the app's own 600px minimum height; the tone
picker's blocking "Tone limit" `messagebox.showinfo` replaced with a
2-second `status_label` flash so hitting the cap no longer interrupts the
picker with a modal for something already shown live.

**Deliberately left out of v2.10**, per the note's own risk/value framing:
the two-row-toolbar-wrap-at-920px change (marginal value at the app's
actual 920px minimum, revisit only if Mark resizes down that far in
practice) and character-level diff tokenisation (notes_017 itself
recommends against it — word-level already matches how a copy-editor scans
a British spelling change).

**Verification**: `ast.parse()` clean; the full v2.9 regression/bug-fix
suite re-run and still passing; a dedicated 28-check script built the real
`Scriptorium`/`SettingsDialog`/`TonePickerDialog` objects and asserted
directly against widget state (colours, fonts, tag configs, pack-manager
state, `<Escape>` bindings, the real `_save()` round-trip) rather than
trusting the code by inspection. Packaged `.exe` rebuilt a second time this
session (now carrying both v2.9 and v2.10): `FileVersion`/`ProductVersion`
confirmed `2.10.0.0`, launched for real, alive and `Responding: True` after
an 8-second soak. Real `scriptorium_config.json` confirmed byte-identical
(unchanged mtime) after every test in both v2.9 and v2.10 — nothing this
session ever touched it.

`ROADMAP.md`'s v2.10 section marked shipped with full acceptance evidence;
"Current shipped version" updated to 2.10; notes_017's source-notes-table
row marked closed.

Continued straight into v2.11 the same session — see the entry below.

---

## 2026-09-02 (continued) — v2.11 (three-tone picker); found and fixed real embellishment bugs via calibration

Continued from v2.10 in the same session, per Mark's earlier go-ahead to
use Ollama (free, local) for calibration rather than spend against the
real Claude API. Full detail and the complete calibration write-up is in
`ROADMAP.md`'s v2.11 section; the two things worth recording here that
aren't obvious from a diff:

**Ollama on this machine could not load `llama3.1:8b`** (the model v2.4's
calibration used) — repeated real server-log cycles of "client connection
closed before llama-server finished loading" / "llm server not
responding", consistent with the box reporting only ~4 GiB free RAM
against the model's ~4.7 GiB weight+buffer footprint (confirmed via the
real `ollama serve` stderr log, not guessed). Killed the stalled attempt
after ~10 minutes of retry cycling rather than let it hang indefinitely,
and switched to `llama3.2:3b` (already pulled locally, loads comfortably)
— a real, still-meaningfully-capable model, not a toy 1B one, so the
calibration signal is still worth trusting, just not identical to v2.4's
choice. Worth remembering for next time Ollama calibration is needed on
this machine: default to `llama3.2:3b`, not `llama3.1:8b`, unless more RAM
is free.

**The calibration process worked exactly as intended — it caught real
bugs, not just confirmed the design.** First pass (3 of notes_016 §2.3's
own suggested test cases, run through the real `call_ollama()`/
`mask_placeholders()`/`build_system_prompt()` pipeline, not mocked) found
three concrete embellishment failures, the same class of bug as v2.4's
Persuasive+Confident finding:
1. Formal+Concise+Diplomatic invented a commitment ("I am committed to
   finding a solution") in a message that only offered to discuss
   something — despite the guard clause already explicitly forbidding
   "create commitments". The model did it anyway; the guard needed a
   concrete example, not just the abstract rule, to actually hold.
2. Confident+Direct+Friendly swapped a hedge word for confirmatory
   language ("seems" → "as expected"), directly overstating certainty
   against Confident's own instruction, and lost the source's explicit
   "haven't fully checked yet" / "not 100% sure yet" caveats in the same
   pass.
3. Neutral+Detailed+Constructive (Neutral as the *dominant* tone) added
   "Fortunately" before "no data was lost" — an unearned emotional
   interjection against Neutral's own explicit "unembellished... over
   strong emotional... colouring" instruction.

Fixed with targeted, concrete additions rather than vague tightening:
`TONE_INSTRUCTIONS["Neutral"]` now names forbidden interjections directly
("fortunately", "unfortunately", "importantly");
`TONE_INSTRUCTIONS["Confident"]` now names the specific hedge→confirmation
swap pattern and lists the allowed hedge words explicitly (seems/might/
may/could/appears); the shared closing guard in `build_tone_instruction()`
now includes the actual failing sentence as a worked example of a
forbidden invented commitment. Re-ran all three cases post-fix, then the
trickiest one (Confident+Direct+Friendly, since certainty-overstatement
was the subtlest of the three bugs) twice more for a 3x check matching
v2.4's own discipline — five real backend calls, all clean: no invented
commitments, no hedge-word swaps (the model consistently landed on
"appears"/"appears to be" from the newly-named allowed list, not a
coincidence), no unearned interjections, every number/time/negation/
placeholder round-tripped intact. This is a cleaner result than v2.4's own
Persuasive fix, which still had a residual issue 2 of 3 times — accepted
without further iteration, same reasoning v2.4 used: diminishing returns
on a small local model, and Scriptorium's actual backstop is the user
reviewing the diff before Accept, not the prompt alone.

Also implemented (code-only, no live-model risk): `TONE_PICKER_LIMIT`
raised to `MAX_SELECTED_TONES` (3); `TONE_CONFLICTS` gained the
`Neutral`/`Persuasive` pair, confirmed not to falsely trigger on the
previously-legal pairs notes_016 named (Friendly+Formal, Direct+
Diplomatic, Confident+Empathetic); `TonePickerDialog`'s label updated to
describe the third slot as "a light accent — not an equal third voice."

**Verification**: `ast.parse()` clean; a dedicated logic-test script
covers the new limit, the new conflict pair (including embedded in a
three-item list), the preserved legal pairs, and the exact dominant/
supporting/accent phrasing at each tone count; full v2.9/v2.10 regression
suites re-run together and all still pass; a real `Scriptorium()`
construct/destroy cycle confirmed clean; packaged `.exe` rebuilt,
`FileVersion`/`ProductVersion` confirmed `2.11.0.0`, launched for real,
alive and `Responding: True`. Real `scriptorium_config.json` confirmed
untouched (unchanged mtime) throughout — the calibration ran entirely
against Ollama with a temp/inline config, never the live file. Ollama
stopped and its runtime folder cleaned up after testing, same as v2.4's
session-end discipline.

`ROADMAP.md` restructured: v2.11 is now its own shipped section (three-tone
picker only); the other four notes_016 proposals renumbered to v2.12+;
"Current shipped version" updated to 2.11; `README.md`'s tone-control
bullet updated for three tones and the new conflict pair.

Mark then explicitly approved pushing and continuing in the same message
("push it and continue with presets"). Continued straight into v2.12 — see
the entry below.

---

## 2026-09-02 (continued) — v2.12 (persisted user presets) implemented

Continued from v2.11 in the same session on Mark's explicit "push it and
continue with presets". Full task list and acceptance evidence in
`ROADMAP.md`'s v2.12 section; the one thing worth expanding on here since
it's a real design decision, not just an implementation detail:

**Deviated from notes_016's own `PresetManagerDialog` snippet on dialog
ownership, decided in-session rather than asked about.** The note's version
issues the "replace an existing preset?" confirmation and save-failure
messages from the *application* method (`_save_current_preset`), called as
`PresetManagerDialog`'s `on_save` callback. But `PresetManagerDialog`
already holds `grab_set()` by the time that runs — a `messagebox.askyesno`
parented on the main window instead of the currently-grabbed dialog is the
wrong owner for it. Restructured so the overwrite confirmation happens
inside `PresetManagerDialog._save()` itself (which has the correct `self`
to parent it on), before delegating to the app for validation/persistence;
`_save_current_preset()` now returns `None` on success or a message string
on failure, shown inline via a status label rather than a second blocking
messagebox stacked on an already-modal dialog. Verified this was a real
concern, not a theoretical one, and that the fix actually works: a test
asserts the exact `parent=` kwarg passed to the mocked
`messagebox.askyesno` call is the dialog instance, not the main window, and
that a real confirm-then-overwrite cycle updates the existing entry in
place (preserving original casing, not creating a duplicate) while a
declined confirmation leaves the dialog open with nothing written.

**Also implemented** exactly as notes_016 specified, no other deviations:
`normalise_preset()`/`normalise_user_presets()` (validated against the same
canonical `MODES`/`STRENGTHS`/`ROLES`/`validate_tones()` tables everything
else uses; reserved-name and length/count caps enforced case-insensitively);
`preset_menu_names()`/`resolve_preset()` replacing the toolbar's direct
`WRITING_PRESETS` reads; `PresetManagerDialog` (reusing v2.10's
`bind_dialog_chrome()`/`position_over_parent()` helpers rather than
reintroducing an undismissable/badly-positioned dialog);
`_write_user_presets()` following `SettingsDialog._save()`'s existing
candidate-copy-then-`save_config(force=True)`-then-commit-to-`self.cfg`
pattern, so a failed write can't leave the in-memory preset list ahead of
disk.

**Verification**: `ast.parse()` clean; over 40 checks across two scripts —
pure logic (`normalise_preset`/`normalise_user_presets` against valid,
malformed, oversized, reserved-name and over-limit inputs) and real-object
(a real `Scriptorium()`, `_save_current_preset()`/`_delete_user_preset()`
exercised against a temp `CONFIG_PATH` with the file re-read after each
step to confirm actual disk persistence, not just in-memory state; a
simulated `save_config()` failure confirmed to leave both `self.cfg` and
disk unchanged; the manager-label toolbar entry confirmed to open the
dialog via a mocked `PresetManagerDialog` rather than silently no-op'ing).
Full v2.9/v2.10/v2.11 regression suites re-run together, all still pass.
Packaged `.exe` rebuilt, `FileVersion`/`ProductVersion` confirmed
`2.12.0.0`, launched for real, alive and `Responding: True`. Real
`scriptorium_config.json` confirmed untouched (unchanged mtime) — every
persistence test used a temp path.

`ROADMAP.md` restructured again: v2.12 is its own shipped section (user
presets only); the remaining three notes_016 proposals renumbered to
v2.13+; "Current shipped version" updated to 2.12; `README.md` gained its
first-ever preset feature bullet (built-in presets existed since v2.3 but
were apparently never documented).

Mark then explicitly approved pushing and continuing with retry transport
in the same message. Continued straight into v2.13 — see the entry below.

---

## 2026-09-02 (continued) — v2.13 (backend retry transport) implemented

Continued from v2.12 in the same session on Mark's "continue with retry
transport". Full task list and acceptance evidence in `ROADMAP.md`'s v2.13
section; two things worth recording here:

**Found and fixed a genuinely stale docstring while implementing this**,
not from a review note: `run_backend()`'s docstring still claimed
"load_config() already normalises 'backend' to 'anthropic'/'ollama'" —
true before this session's own v2.9 Suspicion S1 fix, false after it (that
fix deliberately *stopped* clamping `backend`, specifically so this
function's `else` branch becomes reachable for a genuinely invalid stored
value). Would have been touched regardless since this session added the
`on_retry` parameter to the same function; corrected the stale claim while
already there rather than leaving it to keep misleading the next reader.

**Followed notes_016's own suggested verification approach almost exactly**:
fault-inject via a monkeypatched `urllib.request.urlopen`, not a live flaky
connection (the note's own matrix suggests exactly this: "Fault-inject 429
with numeric and HTTP-date Retry-After headers", "Simulate DNS failure,
connection reset, timeout and truncated response"). Wrote two isolated test
scripts (retry-delay/HTTP-date math and the transport's control flow in
one; `call_anthropic`/`call_ollama`/`run_backend`/`_on_retry_progress`
integration in the other) covering: immediate success, recovery after N
transient failures, exhausting all attempts on a persistent transient
failure, a non-transient status (401) failing with zero retries, both
`Retry-After` forms (numeric and HTTP-date, including clamping an
out-of-range value), a non-JSON 200 body correctly *not* retried (retrying
an identical malformed body would just fail identically again), the
`request-id` response header surfacing in the final error, and
`_on_retry_progress()`'s stale-request/not-busy guard. Then, matching this
project's own "verify against real objects, not just mocks" discipline
elsewhere, ran one actual (not mocked) `call_ollama()` round-trip against a
live local Ollama instance to confirm the refactored transport didn't
silently change real request/response handling — it hadn't; same clean
result as before, `retries needed: 0`.

**Explicitly not attempted, flagged rather than silently assumed
equivalent**: a genuine dropped/throttled network connection against the
real OS network stack (as opposed to a monkeypatched `urlopen` raising the
same exception types). Judged the fault-injection coverage sufficient
since `URLError`/`ConnectionError`/`http.client.HTTPException` all funnel
through the identical retry branch regardless of what triggered them, so
recreating the trigger itself wouldn't exercise any code path the mocked
tests don't already cover — but recorded as a known testing-depth
limitation in `ROADMAP.md` rather than left implicit.

**Verification**: `ast.parse()` clean; 27 fault-injection checks + 9
integration checks, all pass; full v2.9–v2.12 regression suites re-run
together, all still pass; a real `Scriptorium()` construct/destroy cycle
clean. Packaged `.exe` rebuilt, `FileVersion`/`ProductVersion` confirmed
`2.13.0.0`, launched for real, alive and `Responding: True`. Real
`scriptorium_config.json` confirmed untouched throughout (unchanged mtime)
— the one real Ollama call didn't touch it either, since `call_ollama()`
takes `cfg` as a plain dict, never reads or writes `CONFIG_PATH` itself.
Ollama started for the smoke test, stopped again immediately after.

`ROADMAP.md` restructured again: v2.13 is its own shipped section (retry
transport only); the remaining two notes_016 proposals (both raw-Win32)
renumbered to v2.14+; "Current shipped version" updated to 2.13.

Next session: v2.14+ — both remaining items are raw-Win32 (window-procedure
subclassing for Explorer drag-and-drop, hand-rolled `CF_HTML` clipboard
transfer for the rich diff copy) and, per this project's own history, need
the most hand-testing and carry the highest single-bug blast radius of
anything left in the backlog. Worth explicitly confirming with Mark how
much of this session's remaining budget/appetite he wants to spend on that
risk level before diving in, rather than assuming the same "keep going"
default that carried v2.9 through v2.13. Fully scoped in `ROADMAP.md`
either way, nothing implemented yet.

---

## 2026-09-01 (continued) — v2.8: hand-testing fixes (layout, tray lifecycle, clipboard, packaging)

Mark hand-tested v2.7 (screenshots `1.jpg`/`2.jpg` on the Desktop) and found
four issues, none from the notes backlog. All four fixed, verified against
real objects, and committed as v2.8. Full task list and acceptance evidence
in `ROADMAP.md`'s v2.8 section; the notable parts not obvious from the diff:

**Action bar overflow** — thirteen buttons on one row overran the window by
about 45px and overlapped in the middle; the "Copy" button rendering as an
unreadable sliver next to Undo was that overlap, not a rendering bug in Copy
itself. Split into two rows. Mark's own suggested fix was to relocate or
remove "Copy summary" (mistaking it for a duplicate of "Copy") — kept both,
since they copy different things (original text vs. a diff summary), and
explained the distinction; the two-row layout resolves the crowding without
losing either.

**Minimise/close semantics swapped, confirmed with Mark mid-session**: his
first message read "direct minimisation to the taskbar" for what the
minimise button should do, which read ambiguously against the same message's
very next paragraph, which was unambiguously about the *system tray* for the
close button. Reasoned through it live (documented in-session) before
touching code, then Mark sent an explicit correction confirming
"system tray" was intended, not "taskbar" — validating that read before any
code was written. Net change: minimise button -> straight to tray (new
`_on_minimize`, bound to `<Unmap>`, filtered to the window itself + an
`iconic` state check so it doesn't fire on the many
unrelated-widget/withdraw()-of-itself `<Unmap>` events); close button (X)
-> always fully quits via `_quit_app()`, which now also tears down any live
tray icon defensively. Settings checkbox label corrected to match ("Send to
the system tray when minimised") — the old label ("...instead of closing")
described the pre-fix behaviour.

**Root cause of "Network error reaching the Claude API: [Errno 2] No such
file or directory: ...\_MEI#####\base_library.zip"** — this only reproduces
against the packaged `.exe` (`_MEI...` is PyInstaller onefile's `%TEMP%`
extraction folder; Python lazily pulls some stdlib modules from
`base_library.zip` there on first use, e.g. the first network request, not
at startup). Traced to a real, named cause rather than left as a guess:
Mark volunteered `C:\Users\Administrator\Desktop\Work Files\
Clean-Temps-and-Caches.bat` mid-session, which was read in full. Its own
comments/echo claim "Does NOT touch ... Scriptorium", but the skip check
only matches when the *directory being cleared* has "\Scriptorium" in its
own path; it calls `robocopy /MIR` (mirror from an empty folder) against
`%TEMP%` itself, which doesn't match that check, and `/MIR` recursively
wipes everything nested inside — including any live `_MEI*` folder,
Scriptorium's or not. Mark also named three installed always-there cleanup
tools (Privacy Eraser, Wise Care 365, WinTools.net) as other suspects;
checked for live processes/services/scheduled tasks for all three — none
were active, so they weren't the proximate cause this session, though the
fix protects against that whole class of tool regardless of which one
someday runs. Fix: `scriptorium.spec`'s `runtime_tmpdir` now points at
`%LOCALAPPDATA%\Scriptorium\runtime` — the same directory already used for
the app's own config, and the one his own script's exclusion logic already
expects to leave alone. No `scriptorium.py` change needed. Did **not** edit
Mark's personal `.bat` file — out of repo scope, and he didn't ask for that;
mentioned the gap in the exclusion logic in the session summary in case he
wants it fixed separately.

**Verification, all against real objects/builds, not mocked:**
- Action bar: built the real widget tree, grouped buttons by parent frame,
  measured `winfo_reqwidth()` sums against the actual 1156px available width
  — both rows fit with large margin (780px and 420px respectively).
- Minimise/tray/close: drove the real `Scriptorium`/`pystray.Icon` objects
  via `iconify()` (fires the real `<Unmap>` path, not a direct method call)
  with `minimise_to_tray` both on and off, confirmed window `state()` and
  `tray_icon` at each step, confirmed `_on_close()` tears down a live tray
  icon and destroys the window.
- Right-click menus: called `_copy_text_selection`/`_paste_at_click`
  directly against real `CTkTextbox`/`tk.Text` widgets with real selections
  and real clipboard content, including confirming Copy works on the
  disabled (read-only) `revised_box` — Tk's `state=disabled` blocks editing,
  not selection/copy, which is why this worked without touching that state.
- Packaging: real `pyinstaller scriptorium.spec` rebuild (2.8.0.0 confirmed
  via `.VersionInfo`), real launch, confirmed the extraction folder lands at
  `%LOCALAPPDATA%\Scriptorium\runtime\_MEI######` and not under `%TEMP%`,
  survived a 20+ second soak with the process idle and responsive. One
  false alarm caught and resolved mid-session: an early `Get-ChildItem`
  check on the runtime folder came back empty twice in a row (read at the
  time as possible evidence of an even-more-aggressive cleaner reaching
  into `%LOCALAPPDATA%`), but a longer soak plus a repeat check showed the
  folder present and stable throughout — concluded this was a transient
  read (most likely Defender's real-time scan of the freshly-extracted
  folder momentarily interfering with enumeration), not a real deletion;
  didn't let the alarm stand without re-verifying. Real
  `scriptorium_config.json` confirmed byte-identical before and after (this
  test never touched Settings) — same discipline as the v2.5 incident.
- Test process cleanup: `CloseMainWindow()` did not work on this Tk window
  (consistent with this project's known UI-automation gap — confirmed
  again, not re-litigated from scratch); used `Stop-Process -Force` instead
  and removed the orphaned `_MEI######` folder a forced kill leaves behind
  (expected onefile behaviour regardless of location, not a regression).

`ROADMAP.md`'s "Current shipped version" line updated to 2.8; `README.md`'s
feature bullets updated for the corrected tray/close semantics and the new
right-click/Copy-summary/Paste mentions.

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
