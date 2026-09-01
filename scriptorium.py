#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scriptorium — a British English writing assistant for Windows 11
================================================================

A lightweight desktop utility that rewords, corrects, and clarifies text
while honouring the author's original intent. Three modes:

    * Paraphrase — reword while preserving meaning and tone
    * Correct    — fix grammar, spelling, punctuation and usage (British English)
    * Clarify    — improve readability and structure without adding new claims

Design principles
-----------------
    * The output is always a *suggested revision*. Nothing is applied silently;
      you review, accept, reject, copy or undo.
    * British English is enforced by the model prompt (organise, colour,
      licence/license, -ise endings, etc.).
    * Names, numbers, quotations, URLs and technical terms are left untouched.
    * If the model spots genuine ambiguity it flags it rather than guessing.
    * An optional writing role (Software Developer, Academic, and so on) steers
      vocabulary and register without ever adding facts or bending the rules.
    * Placeholders such as [Name], {{Date}} or {amount} are masked before the
      text is sent and restored afterwards, so they are never reworded.
    * Two backends: the Claude API (best quality, text leaves your machine) or
      a local Ollama model (fully private, nothing leaves your machine).

Dependencies
------------
    pip install customtkinter

    The API call uses only the Python standard library (urllib), so no extra
    HTTP package is required. The Anthropic SDK is not needed.

    Optional: install python-docx to import from and export to Word (.docx)
    files (`pip install python-docx`). Plain text and Markdown work without it.

Author: built with Mark, August 2026. Version 2.6.
"""

import os
import sys
import re
import json
import secrets
import threading
import difflib
import winreg
import ctypes
import urllib.request
import urllib.error

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# Tray support is optional — the app works exactly as before without it, just
# with "minimise to tray" unavailable (Settings explains why and disables the
# checkbox rather than letting it silently do nothing). No new dependency is
# required to run Scriptorium at all; this only matters if minimise_to_tray
# is turned on.
try:
    import pystray
    from PIL import Image as PILImage
    TRAY_AVAILABLE = True
except ImportError:
    pystray = None
    PILImage = None
    TRAY_AVAILABLE = False


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #

APP_NAME = "Scriptorium"
APP_VERSION = "2.6"

def _config_dir():
    """Return the folder that holds scriptorium_config.json.

    Running from source: next to this script, unchanged, so an existing config
    keeps working. Running as a packaged .exe (PyInstaller sets sys.frozen): a
    per-user Scriptorium folder under %LOCALAPPDATA%, because a frozen app's own
    directory can be temporary (a one-file build) or read-only.

    If %LOCALAPPDATA%\\Scriptorium can't be created (permissions, a missing
    LOCALAPPDATA, disk trouble), fall back to the same dedicated "Scriptorium"
    subfolder name under the user's home directory instead of a bare loose
    file directly in it — a loose file is easy to mistake for a stray
    document, and a later launch where %LOCALAPPDATA% works again would
    otherwise silently stop finding it, making settings appear to reset.
    Only if even that fails (an all-but-unreachable case) does this fall back
    to the bare home directory, matching the previous last-resort behaviour.
    """
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(__file__))

    for base in (os.environ.get("LOCALAPPDATA"), os.path.expanduser("~")):
        if not base:
            continue
        target = os.path.join(base, "Scriptorium")
        try:
            os.makedirs(target, exist_ok=True)
            return target
        except OSError:
            continue
    return os.path.expanduser("~")


CONFIG_PATH = os.path.join(_config_dir(), "scriptorium_config.json")


def find_source_config_candidate():
    """Return a plausible pre-existing source-mode config path, or None.

    Only meaningful when running frozen (see _config_dir()): the packaged
    .exe and `python scriptorium.py` use different config locations by
    design, so a user trying the standalone build after using the source
    version would otherwise lose their API key and preferences with no
    explanation. A config file sitting next to the running .exe is the one
    place such a user would plausibly have left one — copying the .exe
    into an existing checkout, or trying it from the same folder they had
    been running the script from. Nothing wider is searched.
    """
    if not getattr(sys, "frozen", False):
        return None
    candidate = os.path.join(os.path.dirname(sys.executable),
                             "scriptorium_config.json")
    if (os.path.isfile(candidate)
            and os.path.abspath(candidate) != os.path.abspath(CONFIG_PATH)):
        return candidate
    return None


def resource_path(relative_path):
    """Resolve a bundled read-only resource (e.g. the tray icon image).

    Distinct from _config_dir(): that one finds a writable per-user folder
    for scriptorium_config.json. This finds a bundled, read-only asset
    shipped alongside the code — next to the script when running from
    source, or under PyInstaller's onefile extraction folder (sys._MEIPASS)
    when frozen, per scriptorium.spec's `datas` entry for icon/.
    """
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


_MUTEX_NAME = "Local\\ScriptoriumSingleInstance"
_RESTORE_EVENT_NAME = "Local\\ScriptoriumRestore"
_mutex_handle = None
_ERROR_ALREADY_EXISTS = 183
_INFINITE = 0xFFFFFFFF


def _claim_single_instance():
    """Return True if this process now owns the single-instance mutex.

    False means another Scriptorium is already running. The handle is kept
    at module level so it lives for the process lifetime rather than being
    released early by garbage collection.
    """
    global _mutex_handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex_handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    return ctypes.get_last_error() != _ERROR_ALREADY_EXISTS


def _signal_existing_instance():
    """Ask the already-running instance to show itself."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenEventW(0x0002, False, _RESTORE_EVENT_NAME)  # EVENT_MODIFY_STATE
    if handle:
        kernel32.SetEvent(handle)
        kernel32.CloseHandle(handle)


def _autostart_command():
    """Return the command line that should launch Scriptorium at logon.

    Frozen: the .exe itself (already windowed, console=False). From source:
    pythonw.exe (not python.exe) so no console flashes, falling back to
    python.exe if pythonw.exe isn't found beside the running interpreter.
    Either way, --minimised tells __init__ to start withdrawn to tray
    rather than showing the window on every logon.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimised'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    interpreter = pythonw if os.path.isfile(pythonw) else sys.executable
    script = os.path.abspath(__file__)
    return f'"{interpreter}" "{script}" --minimised'


_AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_AUTOSTART_VALUE = "Scriptorium"


def set_autostart(enabled):
    """Add or remove the HKCU Run entry that starts Scriptorium at logon.

    Returns True on success, False on a registry error (e.g. an unusually
    locked-down HKCU) so the caller can tell the user rather than silently
    claim the setting took effect.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, _AUTOSTART_VALUE, 0, winreg.REG_SZ,
                                  _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, _AUTOSTART_VALUE)
                except FileNotFoundError:
                    pass  # already absent -- disabling is still a success
        return True
    except OSError as exc:
        print(f"[warning] could not update the Windows startup entry: {exc}")
        return False


# Current Claude model IDs (verified against the Claude Platform docs).
# Sonnet 4.6 is a strong, economical default for editing work; Haiku is the
# cheapest/fastest; Opus 4.8 is the most capable if you want it.
ANTHROPIC_MODELS = [
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-8",
]
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"

MODES = ["Paraphrase", "Correct", "Clarify"]
STRENGTHS = ["Light", "Standard", "Substantial"]

# Tones are data-driven, bounded instructions rather than bare labels, so the
# model is told exactly what latitude a tone gives it instead of guessing —
# this matters most for a tone that could otherwise be misread as licence to
# add content (Detailed, Persuasive) rather than just adjust register. TONES
# is derived from this table so the two structures can never drift apart.
# Curated deliberately short: each entry covers a distinct stylistic
# dimension (register, detail, interpersonal manner, force, purpose) rather
# than padding the picker with near-synonyms.
TONE_INSTRUCTIONS = {
    "Formal": (
        "use measured, correctly registered professional language; avoid "
        "contractions and colloquialisms without becoming stiff or archaic"
    ),
    "Neutral": (
        "keep the register even and impartial, favouring plain, unembellished "
        "wording over strong emotional or persuasive colouring"
    ),
    "Casual": (
        "use relaxed, natural phrasing and contractions where appropriate, "
        "without becoming careless, slang-heavy or overly familiar"
    ),
    "Friendly": (
        "use warm, approachable and courteous phrasing without becoming "
        "overfamiliar"
    ),
    "Diplomatic": (
        "use tactful, measured language that acknowledges differing positions "
        "and avoids unnecessary confrontation"
    ),
    "Empathetic": (
        "acknowledge the reader's likely concerns or perspective where the "
        "source supports doing so, without inventing feelings or circumstances"
    ),
    "Direct": (
        "state the central point promptly and unambiguously, avoiding hedging "
        "that is not required by the source"
    ),
    "Confident": (
        "use assured and composed phrasing without overstating certainty or "
        "strengthening the source's claims"
    ),
    "Concise": (
        "remove avoidable repetition and wordiness while retaining every "
        "substantive point"
    ),
    "Detailed": (
        "retain and organise the available detail clearly; do not invent "
        "supporting facts, examples or explanations"
    ),
    "Constructive": (
        "frame criticism or difficulty around improvement and practical next "
        "steps that are already implied by the source, not new ones"
    ),
    "Persuasive": (
        "present the source's existing reasoning compellingly and emphasise "
        "its strongest supported points; do not add evaluative or "
        "promotional adjectives (such as 'cutting-edge', 'remarkable', "
        "'ingenious') that are not already in the source, and do not "
        "loosen or tighten the scope of an existing factual or "
        "quantitative claim (e.g. turning 'lasts three months' into 'up "
        "to three months')"
    ),
}
TONES = ["(keep original)", *TONE_INSTRUCTIONS]

# Up to MAX_SELECTED_TONES may be combined, ordered with the first as
# dominant and the rest as supporting characteristics (see
# build_tone_instruction()). The toolbar picker is deliberately capped
# lower, at TONE_PICKER_LIMIT, until a two-tone combination has actually
# been checked against real output for injected content — raising it to
# MAX_SELECTED_TONES is then a one-line change, not a redesign.
MAX_SELECTED_TONES = 3
TONE_PICKER_LIMIT = 2

TONE_CONFLICTS = {
    frozenset({"Concise", "Detailed"}): (
        "'Concise' and 'Detailed' pull the revision in opposite directions. "
        "Choose the one that best reflects the intended result."
    ),
    frozenset({"Casual", "Formal"}): (
        "'Casual' and 'Formal' are opposite registers. Choose the one that "
        "best reflects the intended result."
    ),
}


def validate_tones(tones):
    """Return a normalised, ordered, conflict-free tone list.

    Order is preserved because the first entry is treated as dominant.
    Duplicate, blank and "(keep original)" entries are dropped silently; an
    unrecognised name is also dropped rather than raising, so a config from
    an older or newer version of this file degrades gracefully instead of
    crashing. This is the sole validation boundary for config loading,
    preset application, the tone-picker dialogue and prompt construction —
    no other method keeps its own copy of these rules.
    """
    normalised = []
    for tone in tones:
        if tone in ("", "(keep original)") or tone in normalised:
            continue
        if tone not in TONE_INSTRUCTIONS:
            continue
        normalised.append(tone)

    if len(normalised) > MAX_SELECTED_TONES:
        raise ValueError(f"Choose no more than {MAX_SELECTED_TONES} tones.")

    selected = set(normalised)
    for pair, message in TONE_CONFLICTS.items():
        if pair.issubset(selected):
            raise ValueError(message)

    return normalised


# Writing roles are data-driven *contexts*, not model personas. Each one steers
# vocabulary, register and rhythm only — it never licenses adding facts or
# jargon. Role, mode, strength and tone are independent knobs that stack.
# Several plausible additions (Blogger, Content Creator, Writer, Creative
# Professional, Designer/Graphic Designer, Educator/Teacher, Business
# Professional, Copywriter, Novelist/Story Writer, Product Manager) were
# deliberately left out: each overlaps heavily with an existing role or with
# another candidate, and a longer menu that mostly repeats itself would
# suggest more precision than it delivers.
ROLES = [
    "(none)",
    "Creative",
    "Software Developer",
    "Engineer",
    "Executive",
    "Project Manager",
    "Client Relations",
    "Academic",
    "Technical Writer",
    "Journalist",
    "Legal & Compliance",
    "Lawyer",
]

ROLE_INSTRUCTIONS = {
    "Creative": (
        "favour vivid, engaging phrasing and a lively narrative rhythm, with "
        "active voice and evocative word choice where the material suits it."
    ),
    "Software Developer": (
        "favour precise, unambiguous technical language and a logical, concise "
        "structure; keep existing terminology exact and cut waffle and "
        "corporate buzzwords."
    ),
    "Engineer": (
        "favour precise constraints, causal reasoning and measurable language "
        "in an orderly problem-then-solution structure; never state a "
        "technical conclusion the source does not already support."
    ),
    "Executive": (
        "favour a decisive, authoritative, outcome-focused register that is "
        "polite but direct, foregrounding decisions and clear next steps."
    ),
    "Project Manager": (
        "favour clear scope, ownership, dependencies, milestones and risks, "
        "ending on unambiguous next actions rather than open questions."
    ),
    "Client Relations": (
        "favour a warm, empathetic and reassuring register that stays courteous "
        "and solution-focused, gently de-escalating where the tone is tense."
    ),
    "Academic": (
        "favour a formal, objective and measured register with careful hedging "
        "(indicates, suggests) and orderly, well-signposted transitions."
    ),
    "Technical Writer": (
        "favour unambiguous terminology, task-focused organisation and "
        "consistent labelling for a reader following instructions or "
        "documentation, not necessarily a technical specialist."
    ),
    "Journalist": (
        "favour clear attribution, factual restraint and a strong information "
        "hierarchy; keep wording neutral unless the source is explicitly "
        "opinionated, and never add or imply a source or corroboration that "
        "is not already present."
    ),
    "Legal & Compliance": (
        "favour cautious, precise and tightly bounded phrasing that avoids "
        "accidental commitments, absolutes and ambiguous obligations."
    ),
    "Lawyer": (
        "favour precise, qualified and logically bounded drafting language "
        "that keeps existing legal terminology exact; never introduce a legal "
        "interpretation, obligation or conclusion the source does not "
        "already contain — this is not legal advice."
    ),
}


# Named presets are a convenience layer over the four existing toolbar knobs
# (Mode, Strength, Role, Tone) — nothing new to persist, no change to the
# prompt or response schema. Applying one is a one-off copy: every knob
# stays independently editable afterwards, and "(none)" is a deliberate
# no-op so the menu can sit at a neutral value without resetting anything.
WRITING_PRESETS = {
    "(none)": None,
    "Formal letter": {
        "mode": "Correct", "strength": "Standard",
        "role": "Executive", "tones": ["Formal"],
    },
    "Client reply": {
        "mode": "Clarify", "strength": "Standard",
        "role": "Client Relations", "tones": ["Diplomatic"],
    },
    "Technical note": {
        "mode": "Clarify", "strength": "Light",
        "role": "Software Developer", "tones": ["Concise"],
    },
}


DEFAULT_CONFIG = {
    "backend": "anthropic",          # "anthropic" or "ollama"
    "anthropic_api_key": "",         # left blank -> falls back to env var
    "anthropic_model": DEFAULT_ANTHROPIC_MODEL,
    "ollama_model": DEFAULT_OLLAMA_MODEL,
    "privacy_ack": False,            # whether the cloud-privacy notice was shown
    "import_prompt_shown": False,    # whether the source->frozen import offer was shown
    "minimise_to_tray": False,       # hide to the system tray instead of closing
    "start_with_windows": False,     # HKCU Run entry launching --minimised at logon
    "start_minimised": False,        # start withdrawn to tray even without --minimised
    "protect_placeholders": True,    # mask [Name], {{Date}} etc. during editing
    "check_letter_conventions": True,  # advisory salutation/sign-off check
    "default_mode": "Paraphrase",      # toolbar knobs applied at startup
    "default_strength": "Substantial",
    "default_role": "Academic",
    "default_tones": ["Concise"],
    "default_diff_view": "Inline",
}


def normalise_tone_config(cfg):
    """Migrate and validate the configured default tone selection.

    A config written by an older version stores a single "default_tone"
    string; this folds it into the current "default_tones" list so an
    existing installation keeps working with no visible change, then drops
    the legacy key so the two representations cannot drift apart.

    The legacy key, if present, is checked BEFORE "default_tones" rather
    than as a fallback for a missing/malformed list. load_config() always
    seeds its working dict from DEFAULT_CONFIG (which already supplies
    "default_tones": ["Concise"]) before merging in the loaded file, so an
    old file containing only "default_tone" would otherwise always find
    "default_tones" already present as a valid list and never actually
    reach the legacy branch — silently discarding the user's real stored
    tone in favour of the default instead of migrating it.
    """
    clean = dict(cfg)
    if "default_tone" in clean:
        legacy = clean.get("default_tone", "(keep original)")
        stored = [] if legacy == "(keep original)" else [legacy]
    else:
        stored = clean.get("default_tones")
        if isinstance(stored, str):
            stored = [stored]
        elif not isinstance(stored, list):
            stored = []

    try:
        clean["default_tones"] = validate_tones(stored)
    except ValueError:
        clean["default_tones"] = ["Concise"]

    clean.pop("default_tone", None)
    return clean


def normalise_config(cfg):
    """Return a copy of cfg with constrained settings restored to safe values.

    A hand-edited or stale config file can contain an out-of-range enum (an
    old default_mode, an unrecognised backend) or a stringy boolean
    ("false" is truthy under bool()). Left unchecked, that either crashes the
    worker thread with a KeyError or — for "backend" specifically — makes the
    status bar and the actual HTTP dispatch disagree about whether text
    leaves the machine. Free-form fields (the API key, model tags) are left
    untouched.
    """
    clean = dict(cfg)
    choices = {
        "backend": ("anthropic", "ollama"),
        "default_mode": tuple(MODES),
        "default_strength": tuple(STRENGTHS),
        "default_role": tuple(ROLES),
        "default_diff_view": ("Clean", "Inline"),
    }
    for key, allowed in choices.items():
        if clean.get(key) not in allowed:
            clean[key] = DEFAULT_CONFIG[key]

    for key in ("privacy_ack", "protect_placeholders",
                "check_letter_conventions", "import_prompt_shown",
                "minimise_to_tray", "start_with_windows", "start_minimised"):
        value = clean.get(key, DEFAULT_CONFIG[key])
        if isinstance(value, str):
            clean[key] = value.strip().lower() in ("1", "true", "yes", "on")
        elif not isinstance(value, bool):
            clean[key] = DEFAULT_CONFIG[key]
        else:
            clean[key] = value

    clean = normalise_tone_config(clean)
    return clean


def load_config():
    """Load scriptorium_config.json, falling back to DEFAULT_CONFIG.

    A missing file is normal (first run). A file that exists but cannot be
    parsed, or that is valid JSON but not an object, sets load_config.unreadable
    True so callers can refuse to overwrite it — that is how a hand-edited API
    key in a malformed file would otherwise be silently lost. Whatever is
    returned has already been through normalise_config(), so every caller can
    trust default_mode/backend/etc. are one of the supported values.
    """
    load_config.unreadable = False
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except FileNotFoundError:
        return normalise_config(cfg)
    except (json.JSONDecodeError, OSError) as exc:
        load_config.unreadable = True
        print(f"[warning] could not read config: {exc}")
        return normalise_config(cfg)
    if not isinstance(loaded, dict):
        load_config.unreadable = True
        print("[warning] config file is not a JSON object; using defaults.")
        return normalise_config(cfg)
    cfg.update(loaded)
    return normalise_config(cfg)


def save_config(cfg, *, force=False):
    """Persist configuration atomically, without clobbering a bad file.

    The JSON is written to a sibling temporary file and flushed to disk, then
    os.replace() swaps it into place in a single atomic step, so an interrupted
    write can never leave a half-written config (and lose the API key inside).
    The Settings dialog passes force=True so the user can deliberately recover
    from a damaged file; automatic saves (such as the privacy-notice flag) do
    not, so a broken file is never silently replaced.

    Returns True on a confirmed write, False otherwise, so a caller (notably
    SettingsDialog) can tell the user their changes were not actually saved
    instead of reporting success regardless.
    """
    if getattr(load_config, "unreadable", False) and not force:
        print("[warning] refusing to overwrite an unreadable config file")
        return False
    tmp_path = f"{CONFIG_PATH}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, CONFIG_PATH)
        load_config.unreadable = False
        return True
    except (OSError, TypeError, ValueError) as exc:
        print(f"[warning] could not save config: {exc}")
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


# --------------------------------------------------------------------------- #
#  Prompt construction
# --------------------------------------------------------------------------- #

MODE_INSTRUCTIONS = {
    "Paraphrase": (
        "Reword the text so it expresses the same meaning in different words. "
        "Preserve the author's tone and register unless a target tone is given. "
        "Keep roughly the same length and level of detail."
    ),
    "Correct": (
        "Fix only genuine errors of grammar, spelling, punctuation and usage. "
        "Make the minimum number of changes. Do NOT reword or restyle sentences "
        "that are already correct; leave correct wording exactly as it is."
    ),
    "Clarify": (
        "Improve readability, flow and sentence structure. Untangle convoluted "
        "phrasing and break up over-long sentences where it helps. Do NOT add "
        "any new assertions and do NOT remove substantive content."
    ),
}

STRENGTH_INSTRUCTIONS = {
    "Light": "Edit conservatively: change as little as possible.",
    "Standard": "Edit with a balanced hand: fix what needs fixing, no more.",
    "Substantial": ("Edit thoroughly within the mode's remit, but still add no "
                    "new facts and preserve the original meaning."),
}


def build_tone_instruction(tones):
    """Return a bounded prompt instruction for an ordered tone combination.

    The first tone is dominant; later tones refine it rather than competing
    equally. Every instruction stays subordinate to meaning preservation —
    tone may reshape wording, rhythm and presentation only, never content.
    """
    tones = validate_tones(tones)
    if not tones:
        return ""

    descriptions = [f"  - {tone}: {TONE_INSTRUCTIONS[tone]}." for tone in tones]

    if len(tones) == 1:
        relationship = f"Use {tones[0]} as the target tone."
    else:
        supporting = ", ".join(tones[1:])
        relationship = (
            f"Use {tones[0]} as the dominant tone. Blend in {supporting} as "
            f"supporting characteristics. If they compete, {tones[0]} takes "
            "priority.")

    return (
        "\n- Tone guidance:\n"
        f"  {relationship}\n" + "\n".join(descriptions) +
        "\n  Tone guidance may affect wording, rhythm and presentation only. "
        "It must not introduce facts, evaluative or promotional language "
        "(such as superlatives or marketing adjectives) absent from the "
        "source, invent feelings, create commitments, change the certainty "
        "or scope of an existing claim, or alter the author's intended "
        "meaning.")


def build_system_prompt(mode, strength, tones, role="(none)",
                        protect_tokens=False):
    """Assemble the system prompt that governs a single rewrite."""
    protect_line = ""
    if protect_tokens:
        protect_line = ("\n- The text contains protected tokens shaped like "
                        "⟦PH0⟧, ⟦PH1⟧ and so on. Reproduce every such "
                        "token exactly and unchanged, in a sensible position; "
                        "never translate, reword, renumber or drop them.")

    role_line = ""
    if role and role != "(none)" and role in ROLE_INSTRUCTIONS:
        role_line = (f"\n- Writing role: {ROLE_INSTRUCTIONS[role]} Apply this to "
                     "vocabulary, register and sentence rhythm only; never add "
                     "facts, technical claims or jargon that are not already "
                     "present or clearly implied in the source.")

    tone_line = build_tone_instruction(tones)

    return f"""You are a meticulous British English copy-editor with decades of \
experience in professional publishing.

# Task
{MODE_INSTRUCTIONS[mode]}
{STRENGTH_INSTRUCTIONS[strength]}{role_line}{tone_line}

# Non-negotiable rules
- Write in British English throughout: use -ise not -ize (organise, realise), \
"colour", "favour", "centre", "licence" (noun) vs "license" (verb), "practice" \
(noun) vs "practise" (verb), "programme" (except computer program), single \
quotation marks for speech where natural, and British date/number conventions.
- Do NOT introduce new facts, claims, figures or examples.
- Do NOT alter proper nouns, personal names, numbers, dates, monetary amounts, \
material inside quotation marks, code, file paths, URLs or technical terminology.
- Preserve the author's voice and intent. You are suggesting a revision, not \
rewriting to your own taste.
- If a passage is genuinely ambiguous — such that improving it would require you \
to guess the intended meaning — make the smallest safe edit and record the \
ambiguity instead of guessing.
- If the text needs no change, return it unchanged.{protect_line}

# Output format
Respond with a SINGLE valid JSON object and nothing else — no markdown, no code \
fences, no commentary. The object must have exactly these keys:
{{
  "revised": "<the full revised text>",
  "ambiguities": ["<short note on each genuine ambiguity, or empty list>"],
  "note": "<one short sentence on what you changed, or empty string>"
}}
Ensure the JSON is valid: escape any double quotes and newlines inside strings."""


# --------------------------------------------------------------------------- #
#  Backends
# --------------------------------------------------------------------------- #

class BackendError(Exception):
    """Raised for any backend/network/parse failure, with a friendly message."""


def _payload_object(payload, label):
    """Return payload if it is a JSON object, otherwise raise BackendError.

    A successful HTTP response can still decode to a non-object JSON root
    (a list, a bare string, null) if the provider or a proxy in front of it
    misbehaves. Without this check, the .get() calls that follow raise a
    raw AttributeError instead of the specific BackendError the rest of the
    app expects to catch.
    """
    if not isinstance(payload, dict):
        raise BackendError(f"{label} returned an unexpected response shape.")
    return payload


def _extract_json(text):
    """Pull a JSON object out of a model response, tolerating stray fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    # Parse the reply, tolerating chatter before OR after the JSON object by
    # falling back to the outermost braces, then reject a body we cannot use.
    def _loads(candidate):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    data = _loads(text)
    if data is None:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            data = _loads(text[start:end + 1])
    if data is None:
        raise BackendError(
            "The model did not return valid JSON. Try again, or lower the "
            "editing strength.")
    if not isinstance(data, dict):
        raise BackendError("The model response was not a JSON object.")

    # Coerce every field to the type the rest of the app relies on, so a model
    # that returns a list for "revised" or null for "ambiguities" fails loudly
    # here instead of crashing silently in the UI callback later.
    revised = data.get("revised")
    if isinstance(revised, list):
        revised = "\n\n".join(str(part) for part in revised)
    elif revised is None:
        raise BackendError("The model response was missing the 'revised' field.")
    elif not isinstance(revised, str):
        revised = str(revised)
    if not revised.strip():
        raise BackendError("The model returned an empty revision.")
    data["revised"] = revised

    ambiguities = data.get("ambiguities")
    if isinstance(ambiguities, list):
        ambiguities = [str(a).strip() for a in ambiguities
                       if a is not None and str(a).strip() not in ("", "None")]
    elif ambiguities is None or str(ambiguities).strip() in ("", "None"):
        ambiguities = []
    else:
        ambiguities = [str(ambiguities).strip()]
    data["ambiguities"] = ambiguities

    note = data.get("note")
    data["note"] = (str(note).strip()
                    if note is not None and str(note).strip() not in ("", "None")
                    else "")
    return data


def call_anthropic(system_prompt, user_text, cfg):
    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise BackendError(
            "No Claude API key set. Open Settings and paste your key, or set the "
            "ANTHROPIC_API_KEY environment variable.\n\nNote: this is a pay-as-you-"
            "go API key from console.anthropic.com — it is separate from a "
            "Claude.ai subscription."
        )
    body = json.dumps({
        "model": cfg.get("anthropic_model", DEFAULT_ANTHROPIC_MODEL),
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_text}],
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_URL, data=body, method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise BackendError(f"Claude API error {exc.code}.\n\n{detail}")
    except urllib.error.URLError as exc:
        raise BackendError(f"Network error reaching the Claude API: {exc.reason}")
    except TimeoutError:
        raise BackendError(
            "The request to Claude timed out. Try a shorter passage, or "
            "check your network connection.")
    except json.JSONDecodeError as exc:
        raise BackendError(
            "The Claude API returned a non-JSON body.\n\n"
            f"(Parser detail: {exc})")

    payload = _payload_object(payload, "The Claude API")
    if payload.get("stop_reason") == "max_tokens":
        raise BackendError(
            "Claude stopped because the reply hit the token limit. Try a "
            "shorter passage, or process the text in sections.")

    content = payload.get("content")
    if not isinstance(content, list):
        raise BackendError("The Claude API response did not contain a content list.")

    # Concatenate all text blocks in the response.
    text = "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
        and isinstance(block.get("text", ""), str)
    )
    if not text:
        raise BackendError("The Claude API returned no text content.")
    return _extract_json(text)


def call_ollama(system_prompt, user_text, cfg):
    body = json.dumps({
        "model": cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL),
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL, data=body, method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # HTTPError is a subclass of URLError, so it must be caught first — e.g.
        # a 404 when the named model has not been pulled.
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise BackendError(f"Ollama returned an error ({exc.code}).\n\n{detail}")
    except urllib.error.URLError as exc:
        raise BackendError(
            "Could not reach Ollama at localhost:11434. Is it running? "
            f"Start it with 'ollama serve' and pull a model first.\n\n({exc.reason})"
        )
    except TimeoutError:
        raise BackendError(
            "Ollama timed out. Try a shorter passage, or a smaller/faster "
            "model.")
    except json.JSONDecodeError as exc:
        raise BackendError(
            "Ollama returned a non-JSON body.\n\n"
            f"(Parser detail: {exc})")

    payload = _payload_object(payload, "Ollama")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise BackendError("Ollama returned no message object.")
    text = message.get("content")
    if not isinstance(text, str) or not text.strip():
        raise BackendError("Ollama returned no text content.")
    return _extract_json(text)


def run_backend(system_prompt, user_text, cfg):
    """Dispatch to the configured backend. An unrecognised value is an error,
    not a silent fall-through to Claude — load_config() already normalises
    "backend" to "anthropic"/"ollama", so reaching the else branch here means
    cfg was built or edited some other way, and defaulting to the cloud
    backend would let the status bar's privacy claim disagree with what
    actually happens to the text.
    """
    backend = cfg.get("backend")
    if backend == "ollama":
        return call_ollama(system_prompt, user_text, cfg)
    if backend == "anthropic":
        return call_anthropic(system_prompt, user_text, cfg)
    raise BackendError(
        f"Unrecognised backend {backend!r}. Open Settings and choose "
        "Claude or Ollama.")


def list_ollama_models(timeout=3):
    """Return the model tags Ollama has locally, or [] if it cannot be reached.

    Queries Ollama's /api/tags endpoint so Settings can offer exactly what is
    installed (in whatever directory OLLAMA_MODELS points at) rather than
    relying on the tag being typed exactly right.
    """
    try:
        req = urllib.request.Request(OLLAMA_TAGS_URL, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    raw = payload.get("models") or []
    if not isinstance(raw, list):
        return []
    names = []
    for item in raw:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model") or ""
        elif isinstance(item, str):
            name = item
        else:
            name = ""
        if name:
            names.append(name)
    return sorted(names)


# --------------------------------------------------------------------------- #
#  Word (.docx) document I/O — optional, needs python-docx
# --------------------------------------------------------------------------- #
# Import/export fall back to plain text when python-docx is absent; these two
# helpers are only reached for .docx paths, and the import is done lazily so the
# app still runs without the package. Formatting is not preserved — Scriptorium
# works in plain text — so a document round-trips as its paragraph text.

def read_docx(path):
    """Return the paragraph text of a .docx file joined by newlines.

    Raises ImportError if python-docx is not installed (the caller turns that
    into a friendly 'pip install python-docx' message).
    """
    from docx import Document  # optional dependency, imported on demand
    document = Document(path)
    return "\n".join(p.text for p in document.paragraphs)


def write_docx(path, text):
    """Write text to a .docx file, one paragraph per line (blank lines kept)."""
    from docx import Document  # optional dependency, imported on demand
    document = Document()
    for line in text.split("\n"):
        document.add_paragraph(line)
    document.save(path)


# --------------------------------------------------------------------------- #
#  Word-level diff highlighting
# --------------------------------------------------------------------------- #

def _tokenise(text):
    """Split into words, punctuation and whitespace so we can rebuild exactly."""
    return re.findall(r"\w+|[^\w\s]|\s+", text, flags=re.UNICODE)


def render_diff(text_widget, original, revised, inline=False):
    """Insert `revised` into a tk.Text, highlighting the changes.

    Clean view (inline=False): show only the revised text, with inserted or
    replaced words tagged 'changed' (green). Inline view (inline=True): also
    show the deleted or replaced original words, struck through in red, so it
    is clear what was removed. Either way the accepted/exported text is always
    the clean revision — the strikethrough is a display aid only.
    """
    text_widget.configure(state="normal")
    text_widget.delete("1.0", "end")

    a, b = _tokenise(original), _tokenise(revised)
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            text_widget.insert("end", "".join(b[j1:j2]))
        elif tag == "insert":
            text_widget.insert("end", "".join(b[j1:j2]), "changed")
        elif tag == "delete":
            if inline:
                text_widget.insert("end", "".join(a[i1:i2]), "deleted")
        elif tag == "replace":
            if inline:
                text_widget.insert("end", "".join(a[i1:i2]), "deleted")
            text_widget.insert("end", "".join(b[j1:j2]), "changed")

    text_widget.configure(state="disabled")


# --------------------------------------------------------------------------- #
#  Placeholder protection
# --------------------------------------------------------------------------- #
# Masking beats trusting the prompt: swap each placeholder for an opaque
# sentinel the model won't touch, then restore the originals afterwards and
# check none went astray. Mode, strength, role and tone still shape the prose
# around them as normal.

# Mathematical white square brackets — visually distinct and virtually never
# seen in ordinary prose, so the sentinel survives the round trip intact.
_PH_OPEN, _PH_CLOSE = "⟦", "⟧"  # the sentinel brackets

# Ordered longest-first so {{...}} is matched before {...}. Angle brackets are
# deliberately conservative (a single bare word) to avoid grabbing HTML or code
# such as <div> attributes or <a href="...">.
_PLACEHOLDER_PATTERNS = [
    r"\{\{[^{}\n]+\}\}",                   # {{Date}}, {{ recipient }}
    r"\[[A-Za-z][^\[\]\n]{0,80}\](?!\()",  # [Name], not [1] or [text](url)
    r"\{[^{}\n]+\}",                       # {amount}
    r"<[A-Za-z][A-Za-z0-9 _\-]*>",         # <Date>
]
_PLACEHOLDER_RE = re.compile("|".join(_PLACEHOLDER_PATTERNS))


def mask_placeholders(text):
    """Swap placeholders for opaque, per-call sentinels.

    Returns (masked_text, mapping), where mapping is an ordered list of
    (sentinel, original) pairs — one per occurrence, so a placeholder used
    several times is tracked independently each time.

    A short random nonce is mixed into every sentinel so that source text
    which already contains something shaped like ⟦PH0⟧ — e.g. a raw
    sentinel left behind by a previous failed run — cannot collide with a
    freshly generated one. Without the nonce, restore_placeholders() cannot
    tell the two apart and corrupts the text (confirmed in
    notes/01_Active/notes_012.txt, Bug A).
    """
    nonce = secrets.token_hex(3)
    mapping = []

    def _swap(match):
        sentinel = f"{_PH_OPEN}PH{nonce}_{len(mapping)}{_PH_CLOSE}"
        mapping.append((sentinel, match.group(0)))
        return sentinel

    return _PLACEHOLDER_RE.sub(_swap, text), mapping


def restore_placeholders(text, mapping):
    """Put the original placeholders back.

    Returns (restored_text, warnings). A warning is recorded if the model
    dropped a token or emitted it more than once, so the user is told rather
    than silently losing a placeholder.
    """
    warnings = []
    for sentinel, original in mapping:
        count = text.count(sentinel)
        if count == 0:
            warnings.append(
                f"The placeholder {original} is missing from the revision — the "
                "model appears to have dropped it. Re-run, or paste it back in "
                "by hand.")
            continue
        text = text.replace(sentinel, original)
        if count > 1:
            warnings.append(
                f"The placeholder {original} appeared {count} times in the "
                "revision; all occurrences were restored.")
    return text, warnings


# --------------------------------------------------------------------------- #
#  British letter conventions (advisory only)
# --------------------------------------------------------------------------- #
# A light, non-destructive check. If a letter opens with an impersonal or a
# named salutation, the sign-off should match British convention (faithfully
# vs sincerely). We flag only a clear, present mismatch — never rewrite — and
# stay silent on anything that is not obviously a formal letter (match reports,
# notes, informal messages), so it never nags in the wrong context.

_SALUTATION_RE = re.compile(r"^\s*Dear\b", re.IGNORECASE)
_IMPERSONAL_RE = re.compile(
    r"^\s*Dear\s+(Sir\s+or\s+Madam|Sir\s*/\s*Madam|Sirs|Sir|Madam)\s*,?\s*$",
    re.IGNORECASE)
_INFORMAL_RE = re.compile(
    r"^\s*Dear\s+(all|everyone|team|friends|colleagues|both)\b", re.IGNORECASE)
_FAITHFULLY_RE = re.compile(r"\bYours\s+faithfully\b", re.IGNORECASE)
_SINCERELY_RE = re.compile(r"\bYours\s+sincerely\b", re.IGNORECASE)


def audit_letter_conventions(text):
    """Advisory check on British salutation/sign-off pairing.

    Returns a single short advisory string if the opening and closing clearly
    clash with convention, otherwise None. Never modifies the text. Silent
    unless the text both opens with 'Dear ...' and contains a 'Yours ...'
    sign-off, so non-letters are left entirely alone.
    """
    stripped = text.strip()
    if not stripped:
        return None
    first_line = stripped.splitlines()[0]
    if not _SALUTATION_RE.match(first_line):
        return None

    has_faithfully = bool(_FAITHFULLY_RE.search(text))
    has_sincerely = bool(_SINCERELY_RE.search(text))
    if not (has_faithfully or has_sincerely):
        return None

    if _IMPERSONAL_RE.match(first_line):
        if has_sincerely and not has_faithfully:
            return ("British letter convention: an impersonal opening such as "
                    "'Dear Sir or Madam' conventionally closes with 'Yours "
                    "faithfully', not 'Yours sincerely'.")
        return None

    if _INFORMAL_RE.match(first_line):
        return None

    # Otherwise a named recipient ('Dear Mr Smith', 'Dear Jane').
    if has_faithfully and not has_sincerely:
        return ("British letter convention: a named recipient such as 'Dear Mr "
                "Smith' conventionally closes with 'Yours sincerely', not 'Yours "
                "faithfully'.")
    return None


# --------------------------------------------------------------------------- #
#  Tone picker dialog
# --------------------------------------------------------------------------- #
# CustomTkinter has no built-in multi-select menu, and a permanently visible
# row of tone checkboxes would overcrowd the toolbar, so the toolbar shows one
# button summarising the current selection and opens this on demand instead.

class TonePickerDialog(ctk.CTkToplevel):
    """An ordered picker for up to TONE_PICKER_LIMIT compatible writing tones."""

    def __init__(self, master, selected, on_apply):
        super().__init__(master)
        self.on_apply = on_apply
        self.selected_order = list(validate_tones(selected))
        self.variables = {}

        self.title("Choose tones")
        self.geometry("420x540")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(
            self, text=f"Choose up to {TONE_PICKER_LIMIT} tones",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            self,
            text=("The first tone selected is dominant; a second tone "
                  "supports it rather than competing equally."),
            wraplength=380, justify="left", text_color="gray65",
        ).pack(anchor="w", padx=18, pady=(0, 10))

        tone_frame = ctk.CTkScrollableFrame(self, height=350)
        tone_frame.pack(fill="both", expand=True, padx=16, pady=4)

        for tone in TONE_INSTRUCTIONS:
            variable = tk.BooleanVar(value=tone in self.selected_order)
            self.variables[tone] = variable
            ctk.CTkCheckBox(
                tone_frame, text=tone, variable=variable,
                command=lambda name=tone: self._toggle_tone(name),
            ).pack(anchor="w", padx=8, pady=5)

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray65")
        self.status_label.pack(anchor="w", padx=18, pady=(4, 0))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=14)

        ctk.CTkButton(buttons, text="Clear", width=90, fg_color="gray30",
                      command=self._clear).pack(side="left")
        ctk.CTkButton(buttons, text="Cancel", width=90, fg_color="gray30",
                      command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Apply", width=90,
                      command=self._apply).pack(side="right")

        self._refresh_status()

    def _toggle_tone(self, tone):
        """Track selection order and enforce the picker's soft limit."""
        if self.variables[tone].get():
            if tone not in self.selected_order:
                if len(self.selected_order) >= TONE_PICKER_LIMIT:
                    self.variables[tone].set(False)
                    messagebox.showinfo(
                        "Tone limit",
                        f"Choose no more than {TONE_PICKER_LIMIT} tones.",
                        parent=self)
                    return
                self.selected_order.append(tone)
        elif tone in self.selected_order:
            self.selected_order.remove(tone)
        self._refresh_status()

    def _refresh_status(self):
        """Show the current count and dominant-first tone order."""
        count = len(self.selected_order)
        description = (" → ".join(self.selected_order) if self.selected_order
                       else "original tone will be preserved")
        self.status_label.configure(
            text=f"{count} of {TONE_PICKER_LIMIT} selected: {description}")

    def _clear(self):
        self.selected_order.clear()
        for variable in self.variables.values():
            variable.set(False)
        self._refresh_status()

    def _apply(self):
        """Validate the selection (conflicts included) and hand it back."""
        try:
            tones = validate_tones(self.selected_order)
        except ValueError as exc:
            messagebox.showwarning("Incompatible tones", str(exc), parent=self)
            return
        self.on_apply(tones)
        self.destroy()


# --------------------------------------------------------------------------- #
#  Settings dialog
# --------------------------------------------------------------------------- #

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, cfg, on_save):
        super().__init__(master)
        self.cfg = cfg
        self.on_save = on_save

        self.title("Settings")
        self.geometry("520x740")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()  # modal

        pad = {"padx": 16, "pady": (10, 0)}

        ctk.CTkLabel(self, text="Backend", font=ctk.CTkFont(weight="bold")
                     ).pack(anchor="w", **pad)
        self.backend_var = ctk.StringVar(value=cfg.get("backend", "anthropic"))
        seg = ctk.CTkSegmentedButton(
            self, values=["anthropic", "ollama"], variable=self.backend_var,
            command=lambda _=None: self._refresh_state())
        seg.pack(fill="x", padx=16, pady=(2, 4))

        ctk.CTkLabel(self, text="Claude API key (pay-as-you-go, from "
                     "console.anthropic.com)").pack(anchor="w", **pad)
        self.key_entry = ctk.CTkEntry(self, show="*", width=480)
        self.key_entry.insert(0, cfg.get("anthropic_api_key", ""))
        self.key_entry.pack(padx=16, pady=(2, 0))
        ctk.CTkLabel(self, text="Stored in plain text in the config file. "
                     "Leave blank to use the ANTHROPIC_API_KEY env variable.",
                     text_color="gray60",
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)

        ctk.CTkLabel(self, text="Claude model").pack(anchor="w", **pad)
        self.model_var = ctk.StringVar(
            value=cfg.get("anthropic_model", DEFAULT_ANTHROPIC_MODEL))
        ctk.CTkOptionMenu(self, values=ANTHROPIC_MODELS,
                          variable=self.model_var).pack(fill="x", padx=16, pady=(2, 0))

        ctk.CTkLabel(self, text="Local Ollama model — type a tag, or Detect "
                     "what Ollama has installed").pack(anchor="w", **pad)
        ollama_row = ctk.CTkFrame(self, fg_color="transparent")
        ollama_row.pack(fill="x", padx=16, pady=(2, 0))
        current_model = cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL)
        self.ollama_combo = ctk.CTkComboBox(ollama_row, width=360,
                                            values=[current_model])
        self.ollama_combo.set(current_model)
        self.ollama_combo.pack(side="left")
        self.detect_btn = ctk.CTkButton(ollama_row, text="Detect", width=110,
                                        command=self._detect_models)
        self.detect_btn.pack(side="left", padx=(8, 0))
        self.ollama_status = ctk.CTkLabel(self, text="", text_color="gray60",
                                          font=ctk.CTkFont(size=11))
        self.ollama_status.pack(anchor="w", padx=16)

        self.protect_var = tk.BooleanVar(
            value=cfg.get("protect_placeholders", True))
        ctk.CTkCheckBox(
            self, variable=self.protect_var,
            text="Protect placeholders — mask [Name], {{Date}}, {amount}, "
                 "<Date> while editing").pack(anchor="w", padx=16, pady=(16, 0))

        self.letters_var = tk.BooleanVar(
            value=cfg.get("check_letter_conventions", True))
        ctk.CTkCheckBox(
            self, variable=self.letters_var,
            text="Check British letter conventions — flag salutation / "
                 "sign-off mismatches (advisory)").pack(anchor="w", padx=16, pady=(10, 0))

        ctk.CTkLabel(self, text="Startup & window behaviour",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", **pad)

        self.tray_var = tk.BooleanVar(
            value=cfg.get("minimise_to_tray", False) and TRAY_AVAILABLE)
        ctk.CTkCheckBox(
            self, variable=self.tray_var,
            state="normal" if TRAY_AVAILABLE else "disabled",
            text="Minimise to tray instead of closing",
            command=self._refresh_tray_dependent_state
        ).pack(anchor="w", padx=16, pady=(2, 0))
        if not TRAY_AVAILABLE:
            ctk.CTkLabel(
                self, text="Needs the optional pystray and Pillow packages: "
                          "pip install pystray pillow",
                text_color="gray60",
                font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)

        self.autostart_var = tk.BooleanVar(
            value=cfg.get("start_with_windows", False))
        ctk.CTkCheckBox(
            self, variable=self.autostart_var,
            text="Start with Windows").pack(anchor="w", padx=16, pady=(10, 0))

        self.start_minimised_var = tk.BooleanVar(
            value=cfg.get("start_minimised", False) and TRAY_AVAILABLE)
        self.start_minimised_check = ctk.CTkCheckBox(
            self, variable=self.start_minimised_var,
            text="Start minimised to tray")
        self.start_minimised_check.pack(anchor="w", padx=16, pady=(10, 0))
        self._refresh_tray_dependent_state()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=18, side="bottom")
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="gray30",
                      command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Save", width=100,
                      command=self._save).pack(side="right")

        self._refresh_state()

    def _detect_models(self):
        """Ask Ollama which models are installed, without freezing Settings.

        list_ollama_models() opens a socket (timeout=3) — running it directly
        on the Tk thread used to freeze the modal Settings dialog for up to
        three seconds. The HTTP call now runs on a daemon thread; only the
        widget update at the end touches Tk, via self.after().
        """
        self.detect_btn.configure(state="disabled")
        self.ollama_status.configure(text="Detecting…")

        def worker():
            models = list_ollama_models()
            try:
                self.after(0, self._finish_model_detection, models)
            except (tk.TclError, RuntimeError):
                pass  # the Settings dialog closed before detection finished

        threading.Thread(target=worker, daemon=True).start()

    def _finish_model_detection(self, models):
        """Apply a completed Ollama model list on Tk's event thread."""
        if not self.winfo_exists():
            return
        self._refresh_state()
        if not models:
            self.ollama_status.configure(
                text="No response from Ollama at localhost:11434 — is "
                     "'ollama serve' running?")
            return
        current = self.ollama_combo.get().strip()
        values = models if (current in models or not current) else [current] + models
        self.ollama_combo.configure(values=values)
        self.ollama_status.configure(text=f"Found {len(models)} model(s).")

    def _refresh_state(self):
        cloud = self.backend_var.get() == "anthropic"
        self.key_entry.configure(state="normal" if cloud else "disabled")
        self.ollama_combo.configure(state="disabled" if cloud else "normal")
        self.detect_btn.configure(state="disabled" if cloud else "normal")

    def _refresh_tray_dependent_state(self):
        """Start-minimised only makes sense once tray is on and available.

        Force-clears the variable when disabling it, so a stale True value
        from a config with tray off can't be saved back out unintentionally
        just because the checkbox was left ticked from an earlier state.
        """
        enabled = TRAY_AVAILABLE and bool(self.tray_var.get())
        self.start_minimised_check.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.start_minimised_var.set(False)

    def _save(self):
        """Validate and persist settings, keeping the dialog open on failure.

        Builds a candidate dict rather than mutating self.cfg directly, so a
        failed write leaves the caller's in-memory config exactly as it was
        instead of the app believing changes are live when nothing was
        actually saved to disk.
        """
        candidate = dict(self.cfg)
        candidate.update({
            "backend": self.backend_var.get(),
            "anthropic_api_key": self.key_entry.get().strip(),
            "anthropic_model": self.model_var.get(),
            "ollama_model": (
                self.ollama_combo.get().strip() or DEFAULT_OLLAMA_MODEL),
            "protect_placeholders": bool(self.protect_var.get()),
            "check_letter_conventions": bool(self.letters_var.get()),
            "minimise_to_tray": bool(self.tray_var.get()),
            "start_with_windows": bool(self.autostart_var.get()),
            "start_minimised": bool(self.start_minimised_var.get()),
        })
        candidate = normalise_config(candidate)
        if not save_config(candidate, force=True):
            messagebox.showerror(
                "Settings not saved",
                "Scriptorium could not write its configuration file. Your "
                "changes have not been applied — check that the file is not "
                "read-only or open elsewhere, then try again.",
                parent=self)
            return

        if not set_autostart(candidate["start_with_windows"]):
            messagebox.showwarning(
                "Startup entry not updated",
                "Settings were saved, but Scriptorium could not update the "
                "Windows startup registry entry. \"Start with Windows\" may "
                "not reflect this change.",
                parent=self)

        self.cfg.clear()
        self.cfg.update(candidate)
        self.on_save()
        self.destroy()


# --------------------------------------------------------------------------- #
#  Main application
# --------------------------------------------------------------------------- #

class Scriptorium(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.undo_stack = []
        self.last_result = None
        self.busy = False
        self._request_id = 0          # bumped on every Process and every cancel
        self._result_source = ""      # the text last_result was generated from
        self.selected_tones = list(self.cfg.get("default_tones", ["Concise"]))
        self.tray_icon = None         # the live pystray.Icon, only while hidden to tray
        self._start_restore_listener()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} — British English writing assistant")
        self.geometry("1180x760")
        self.minsize(920, 600)
        self._apply_window_icon()
        self.after(200, self._apply_window_icon)

        self._build_toolbar()
        self._build_panes()
        self._build_actionbar()
        self._build_statusbar()

        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._maybe_offer_config_migration()
        self._maybe_warn_unreadable_config()
        self._maybe_show_privacy_notice()
        self._refresh_status()

        # Only ever start hidden if the tray is genuinely available -- a
        # start-minimised launch with no working tray would trap the user
        # with no way to reach an invisible window.
        wants_minimised = "--minimised" in sys.argv[1:] or self.cfg.get("start_minimised")
        if wants_minimised and self.cfg.get("minimise_to_tray") and TRAY_AVAILABLE:
            self._minimise_to_tray()

    # -- layout ------------------------------------------------------------- #

    def _apply_window_icon(self):
        """Set the title-bar/taskbar icon from the bundled .ico.

        CustomTkinter can overwrite Tk's icon after construction, so __init__
        calls this once immediately and once after a short delay. A missing
        file or a Tcl error must not prevent the app from opening.
        """
        ico = resource_path(os.path.join("icon", "Scriptorium-256.ico"))
        if not os.path.isfile(ico):
            return
        try:
            self.iconbitmap(ico)
        except (tk.TclError, OSError):
            pass

    def _bind_shortcuts(self):
        """Register keyboard access to common editing and review actions.

        Process/Import/Export already had direct bindings; Accept, Reject,
        Copy revision and Undo did not. Deliberately does not touch
        Ctrl+C/Ctrl+V — those must keep working for ordinary text selection
        inside the Original textbox.
        """
        bindings = {
            "<Control-Return>": self.process,
            "<Control-i>": self.import_file,
            "<Control-s>": self.export_file,
            "<Control-Shift-A>": self.accept,
            "<Escape>": self.reject,
            "<Control-Shift-C>": self.copy_revision,
            "<Control-z>": self.undo,
        }
        for sequence, action in bindings.items():
            self.bind(sequence, lambda _event, command=action: command())

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, corner_radius=0)
        bar.pack(fill="x", side="top")

        ctk.CTkLabel(bar, text="Mode").grid(row=0, column=0, padx=(14, 4), pady=10)
        self.mode_var = ctk.StringVar(
            value=self.cfg.get("default_mode", "Paraphrase"))
        ctk.CTkSegmentedButton(bar, values=MODES, variable=self.mode_var
                               ).grid(row=0, column=1, padx=4, pady=10)

        ctk.CTkLabel(bar, text="Strength").grid(row=0, column=2, padx=(20, 4))
        self.strength_var = ctk.StringVar(
            value=self.cfg.get("default_strength", "Substantial"))
        ctk.CTkSegmentedButton(bar, values=STRENGTHS, variable=self.strength_var
                               ).grid(row=0, column=3, padx=4)

        ctk.CTkLabel(bar, text="Role").grid(row=0, column=4, padx=(20, 4))
        self.role_var = ctk.StringVar(
            value=self.cfg.get("default_role", "Academic"))
        ctk.CTkOptionMenu(bar, values=ROLES, variable=self.role_var, width=170
                          ).grid(row=0, column=5, padx=4)

        ctk.CTkLabel(bar, text="Tone").grid(row=0, column=6, padx=(20, 4))
        self.tone_button = ctk.CTkButton(
            bar, text="", width=150, fg_color="gray30",
            command=self._open_tone_picker)
        self.tone_button.grid(row=0, column=7, padx=4)
        self._refresh_tone_button()

        ctk.CTkLabel(bar, text="Preset").grid(row=0, column=8, padx=(20, 4))
        self.preset_var = ctk.StringVar(value="(none)")
        ctk.CTkOptionMenu(
            bar, values=list(WRITING_PRESETS), variable=self.preset_var,
            width=145, command=self._apply_writing_preset,
        ).grid(row=0, column=9, padx=4)

        ctk.CTkButton(bar, text="⚙ Settings", width=100, fg_color="gray30",
                      command=self.open_settings).grid(row=0, column=11, padx=(20, 14))
        bar.grid_columnconfigure(10, weight=1)

    def _apply_writing_preset(self, name):
        """Populate the existing Mode/Strength/Role/Tone knobs from a preset.

        Every knob stays independently editable afterwards — this only ever
        performs a one-off copy onto controls that already exist.
        """
        preset = WRITING_PRESETS.get(name)
        if not preset:
            return
        self.mode_var.set(preset["mode"])
        self.strength_var.set(preset["strength"])
        self.role_var.set(preset["role"])
        self._set_selected_tones(preset.get("tones", []))
        self._refresh_status(f"preset applied: {name}")

    def _open_tone_picker(self):
        """Open the compact multi-tone selection dialogue."""
        TonePickerDialog(self, selected=self.selected_tones,
                         on_apply=self._set_selected_tones)

    def _set_selected_tones(self, tones):
        """Apply a validated, ordered tone selection to the current session."""
        self.selected_tones = validate_tones(tones)
        self._refresh_tone_button()

    def _refresh_tone_button(self):
        """Show the current tone combination without overcrowding the toolbar."""
        if not self.selected_tones:
            label = "(keep original)"
        else:
            label = " + ".join(self.selected_tones)
        if len(label) > 24:
            label = f"{self.selected_tones[0]} +{len(self.selected_tones) - 1}"
        self.tone_button.configure(text=label)

    def _build_panes(self):
        panes = ctk.CTkFrame(self, fg_color="transparent")
        panes.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        panes.grid_columnconfigure(0, weight=1, uniform="col")
        panes.grid_columnconfigure(1, weight=1, uniform="col")
        panes.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(panes, text="Original", anchor="w",
                     font=ctk.CTkFont(weight="bold")
                     ).grid(row=0, column=0, sticky="w", padx=4)
        rev_header = ctk.CTkFrame(panes, fg_color="transparent")
        rev_header.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(rev_header, text="Suggested revision", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.diff_view_var = ctk.StringVar(
            value=self.cfg.get("default_diff_view", "Inline"))
        ctk.CTkSegmentedButton(
            rev_header, values=["Clean", "Inline"], variable=self.diff_view_var,
            command=self._on_diff_view_change, width=160).pack(side="right")

        # Original: editable CTk textbox.
        self.original_box = ctk.CTkTextbox(panes, wrap="word",
                                           font=ctk.CTkFont(size=14))
        self.original_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=4)
        # <<Modified>> covers every kind of change (typing, cut, paste,
        # undo) so the live word/character count in _refresh_status()
        # never falls out of sync with what is actually on screen.
        self.original_box.bind("<<Modified>>", self._on_original_modified)
        self.original_box.edit_modified(False)

        # Revised: a themed tk.Text so we can apply diff tags reliably.
        revised_frame = ctk.CTkFrame(panes)
        revised_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=4)
        revised_frame.grid_rowconfigure(0, weight=1)
        revised_frame.grid_columnconfigure(0, weight=1)

        self.revised_box = tk.Text(
            revised_frame, wrap="word", bd=0, padx=10, pady=10,
            font=("Segoe UI", 12), background="#1d1e1e", foreground="#dce4ee",
            insertbackground="#dce4ee", relief="flat", state="disabled",
            highlightthickness=0)
        self.revised_box.grid(row=0, column=0, sticky="nsew")
        scroll = ctk.CTkScrollbar(revised_frame, command=self.revised_box.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.revised_box.configure(yscrollcommand=scroll.set)
        self.revised_box.tag_config("changed", foreground="#4ec9b0")
        self.revised_box.tag_config("deleted", foreground="#e06c75", overstrike=1)

        # Ambiguity strip (hidden until there is something to show).
        self.ambiguity_box = ctk.CTkTextbox(self, height=64, wrap="word",
                                            fg_color="#3a2f1a",
                                            font=ctk.CTkFont(size=12))
        # packed on demand in _show_ambiguities()

    def _build_actionbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)

        self.process_btn = ctk.CTkButton(bar, text="Process", width=100,
                                         command=self.process)
        self.process_btn.pack(side="left")

        self.softer_btn = ctk.CTkButton(
            bar, text="− Softer", width=80, fg_color="gray30",
            command=lambda: self._nudge_strength(-1))
        self.softer_btn.pack(side="left", padx=(8, 4))
        self.stronger_btn = ctk.CTkButton(
            bar, text="+ Stronger", width=90, fg_color="gray30",
            command=lambda: self._nudge_strength(1))
        self.stronger_btn.pack(side="left", padx=4)

        self.accept_btn = ctk.CTkButton(
            bar, text="Accept →", width=110, fg_color="#2f7d4f",
            hover_color="#276a43", command=self.accept)
        self.accept_btn.pack(side="left", padx=(12, 4))
        ctk.CTkButton(bar, text="Reject", width=90, fg_color="gray30",
                      command=self.reject).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Copy revision", width=120, fg_color="gray30",
                      command=self.copy_revision).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Undo", width=80, fg_color="gray30",
                      command=self.undo).pack(side="left", padx=4)

        ctk.CTkButton(bar, text="Export…", width=90, fg_color="gray30",
                      command=self.export_file).pack(side="right", padx=(4, 0))
        ctk.CTkButton(bar, text="Import…", width=90, fg_color="gray30",
                      command=self.import_file).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Clear", width=80, fg_color="gray30",
                      command=self.clear_all).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Copy", width=80, fg_color="gray30",
                      command=self.copy_original).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Paste", width=80, fg_color="gray30",
                      command=self.paste_original).pack(side="right", padx=4)

    def _build_statusbar(self):
        self.status = ctk.CTkLabel(self, text="", anchor="w",
                                   text_color="gray65",
                                   font=ctk.CTkFont(size=12))
        self.status.pack(fill="x", padx=16, pady=(0, 8))

    # -- helpers ------------------------------------------------------------ #

    def _on_original_modified(self, _event=None):
        """Refresh the live word/character count after any Original edit.

        Tk's modified flag latches "true" and stops firing <<Modified>> again
        until it is explicitly cleared, so every handler run resets it.
        """
        if not self.original_box.edit_modified():
            return
        self.original_box.edit_modified(False)
        self._refresh_status()

    def _refresh_status(self, extra=""):
        backend = self.cfg.get("backend", "anthropic")
        if backend == "anthropic":
            where = f"Claude · {self.cfg.get('anthropic_model')}"
            privacy = "text is sent to Anthropic"
        else:
            where = f"Ollama · {self.cfg.get('ollama_model')} (local)"
            privacy = "stays on this machine"
        original = self.original_box.get("1.0", "end-1c")
        chars = len(original)
        words = len(original.split()) if original.strip() else 0
        msg = (f"Backend: {where}  —  {privacy}   |   "
               f"{words} words, {chars} characters")
        if self.last_result:
            revised = self.last_result["revised"]
            r_words = len(revised.split()) if revised.strip() else 0
            # Compare against the text the revision was actually generated
            # from, not the live buffer — Original may have been edited
            # since Process ran, while last_result is still on display.
            src = self._result_source if self._result_source else original
            src_words = len(src.split()) if src.strip() else 0
            delta = r_words - src_words
            sign = f"+{delta}" if delta >= 0 else str(delta)
            msg += f"   |   revision {r_words} words ({sign})"
        if extra:
            msg += f"   |   {extra}"
        self.status.configure(text=msg)

    def _maybe_warn_unreadable_config(self):
        """Tell the user their config file could not be read.

        load_config() already refuses to overwrite an unreadable file (so
        nothing is lost), but that refusal is otherwise reported with
        print() only — invisible in the packaged .exe, which has no console
        (scriptorium.spec sets console=False). Without this, an API key
        sitting in a slightly damaged file just looks like it vanished.
        """
        if getattr(load_config, "unreadable", False):
            messagebox.showwarning(
                "Configuration could not be read",
                "scriptorium_config.json exists but could not be parsed, so "
                "Scriptorium started with default settings instead.\n\n"
                "The existing file has been left untouched — nothing has "
                "been overwritten. Open Settings and click Save to write a "
                "fresh copy, or repair the JSON by hand.",
                parent=self)

    def _maybe_offer_config_migration(self):
        """Offer to import an existing source-mode config, once, when frozen.

        Mirrors _maybe_show_privacy_notice()'s one-time-flag pattern: gated
        on import_prompt_shown rather than on whether a frozen config file
        happens to exist yet, since Settings or the privacy notice could
        already have created one for unrelated reasons. The source file
        itself is only ever read, never written — declining, or there being
        no candidate at all, leaves it completely untouched.
        """
        if not getattr(sys, "frozen", False) or self.cfg.get("import_prompt_shown"):
            return
        self.cfg["import_prompt_shown"] = True
        save_config(self.cfg)

        candidate = find_source_config_candidate()
        if not candidate:
            return
        if not messagebox.askyesno(
                "Import existing settings?",
                "Scriptorium found an existing configuration from the "
                f"source version at:\n\n{candidate}\n\n"
                "Import its API key and preferences into this standalone "
                "version? That file will not be changed either way.",
                parent=self):
            return
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                imported = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror(
                "Import failed",
                f"Could not read the existing configuration.\n\n{exc}")
            return
        if not isinstance(imported, dict):
            messagebox.showerror(
                "Import failed",
                "The existing configuration file is not a valid settings file.")
            return
        merged = dict(self.cfg)
        merged.update(imported)
        merged["import_prompt_shown"] = True
        merged = normalise_config(merged)
        if not save_config(merged, force=True):
            messagebox.showerror(
                "Import failed",
                "The existing settings were read, but could not be saved "
                "to this version's configuration file.")
            return
        self.cfg.clear()
        self.cfg.update(merged)
        # The toolbar's Mode/Strength/Role/Tone/diff-view controls were
        # already built from the pre-import config; apply the imported
        # values to them now rather than waiting for a restart.
        self.mode_var.set(merged.get("default_mode", self.mode_var.get()))
        self.strength_var.set(merged.get("default_strength", self.strength_var.get()))
        self.role_var.set(merged.get("default_role", self.role_var.get()))
        self._set_selected_tones(merged.get("default_tones", self.selected_tones))
        self.diff_view_var.set(merged.get("default_diff_view", self.diff_view_var.get()))
        self._refresh_status("settings imported")

    def _maybe_show_privacy_notice(self):
        if self.cfg.get("backend") == "anthropic" and not self.cfg.get("privacy_ack"):
            messagebox.showinfo(
                "Privacy notice",
                "You are using the Claude API backend. The text you process is "
                "sent over the internet to Anthropic for rewriting.\n\n"
                "If you would rather keep everything on this machine, switch to "
                "the local Ollama backend in Settings.\n\n"
                "This notice won't appear again.")
            self.cfg["privacy_ack"] = True
            save_config(self.cfg)

    def _show_ambiguities(self, items):
        if items:
            self.ambiguity_box.pack(fill="x", padx=12, pady=(0, 4),
                                    before=self.status)
            self.ambiguity_box.configure(state="normal")
            self.ambiguity_box.delete("1.0", "end")
            self.ambiguity_box.insert(
                "end", "⚠ Ambiguities flagged (not silently changed):\n" +
                "\n".join(f"  • {a}" for a in items))
            self.ambiguity_box.configure(state="disabled")
        else:
            self.ambiguity_box.pack_forget()

    # -- actions ------------------------------------------------------------ #

    def _set_busy(self, flag):
        """Disable Process and Accept for the life of one backend call.

        Accept used to stay clickable while a newer Process request was in
        flight: clicking it applied the OLD revision and then, via
        accept()'s call to reject(), silently cancelled the request that was
        still running — with no warning that anything had been discarded.
        Disabling Accept alongside Process closes that gap.
        """
        self.busy = flag
        self.process_btn.configure(
            text="Working…" if flag else "Process",
            state="disabled" if flag else "normal")
        self.accept_btn.configure(state="disabled" if flag else "normal")
        self.softer_btn.configure(state="disabled" if flag else "normal")
        self.stronger_btn.configure(state="disabled" if flag else "normal")

    def _nudge_strength(self, delta):
        """Move Strength one notch (Softer/Stronger) and immediately re-run.

        Clamped at the ends of STRENGTHS rather than wrapping — clicking
        Softer already at "Light" just re-runs at "Light" again.
        """
        if self.busy:
            return
        index = STRENGTHS.index(self.strength_var.get())
        index = max(0, min(len(STRENGTHS) - 1, index + delta))
        self.strength_var.set(STRENGTHS[index])
        self.process()

    def _claim_request(self, request_id):
        """Return True if this callback still owns the UI.

        Late results from a cancelled or superseded request are dropped. Busy is
        only cleared when this request is still the current one; cancellers
        (Reject, window close) clear busy themselves so Process cannot stick on
        'Working…'.
        """
        if not self.winfo_exists():
            return False
        if request_id != self._request_id:
            return False
        self._set_busy(False)
        return True

    def _invalidate_inflight(self):
        """Drop any in-flight Process callback and re-enable the button."""
        self._request_id += 1
        if self.busy:
            self._set_busy(False)

    def _remember_for_undo(self, text, limit=50):
        """Store one distinct document snapshot in a bounded undo history.

        Without a cap, a long session of repeated Paste/Clear/Accept/Import
        grows undo_stack forever. Skipping a snapshot identical to the last
        one also stops Clear-on-an-already-empty-pane (and similar no-ops)
        from adding a pointless Undo step.
        """
        if self.undo_stack and self.undo_stack[-1] == text:
            return
        self.undo_stack.append(text)
        if len(self.undo_stack) > limit:
            del self.undo_stack[:-limit]

    def _post_to_ui(self, callback, *args):
        """Queue a UI callback from a worker thread; do nothing if the window
        is already gone.

        _claim_request()'s winfo_exists() guard only runs once a callback is
        actually delivered — it cannot stop self.after() itself from being
        called against an already-destroyed Tcl interpreter if the app is
        closed while a request is still in flight. That raises tk.TclError
        on the worker thread, which is otherwise unhandled. A worker thread
        can also reach this call before __init__ has reached mainloop() (e.g.
        the restore-listener thread firing very early); Tk raises RuntimeError
        ("main thread is not in main loop") rather than TclError in that case.
        """
        try:
            if self.winfo_exists():
                self.after(0, callback, *args)
        except (tk.TclError, RuntimeError):
            pass

    def process(self):
        """Send the current text to the backend on a worker thread."""
        if self.busy:
            return
        original = self.original_box.get("1.0", "end-1c")
        if not original.strip():
            self._refresh_status("nothing to process")
            return

        # Protect placeholders by masking them before the model sees the text;
        # they are restored (and checked) in _on_success.
        if self.cfg.get("protect_placeholders", True):
            masked, ph_map = mask_placeholders(original)
        else:
            masked, ph_map = original, []

        # Stamp this request so a superseded or cancelled result can be ignored.
        self._request_id += 1
        request_id = self._request_id
        self._set_busy(True)
        busy_note = "contacting the model…"
        if ph_map:
            busy_note = f"protecting {len(ph_map)} placeholder(s), contacting the model…"
        self._refresh_status(busy_note)

        try:
            system_prompt = build_system_prompt(
                self.mode_var.get(), self.strength_var.get(),
                tuple(self.selected_tones), self.role_var.get(),
                protect_tokens=bool(ph_map))
        except ValueError as exc:
            # Defence-in-depth: self.selected_tones is only ever set through
            # _set_selected_tones()/config normalisation, both of which
            # already validate it, so this should not trigger in practice —
            # but raising here, mid-_set_busy(True), would otherwise strand
            # Process on "Working…" with no way to recover.
            self._set_busy(False)
            messagebox.showerror("Could not process", str(exc))
            return
        cfg_snapshot = dict(self.cfg)  # Settings changes mid-request affect the next one only

        def worker():
            try:
                result = run_backend(system_prompt, masked, cfg_snapshot)
            except BackendError as exc:
                self._post_to_ui(self._on_error, request_id, str(exc))
            except Exception as exc:  # noqa: BLE001 — surface anything unexpected
                self._post_to_ui(
                    self._on_error, request_id, f"Unexpected error: {exc}")
            else:
                self._post_to_ui(
                    self._on_success, request_id, original, ph_map, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, request_id, original, ph_map, result):
        if not self._claim_request(request_id):
            return

        # Restore protected placeholders before anything is shown, stored or
        # exported, so the diff and the accepted text carry the real values.
        warnings = []
        if ph_map:
            result["revised"], warnings = restore_placeholders(
                result["revised"], ph_map)

        # If the source changed while we were working, this revision is for the
        # OLDER text — say so rather than pretend it matches what is on screen.
        if self.original_box.get("1.0", "end-1c") != original:
            warnings.append(
                "The original text changed while this was processing, so this "
                "revision reflects the earlier text. Review it carefully before "
                "accepting.")

        # Advisory-only British letter check (never rewrites the text).
        if self.cfg.get("check_letter_conventions", True):
            advisory = audit_letter_conventions(result["revised"])
            if advisory:
                warnings.append(advisory)

        self.last_result = result
        self._result_source = original
        render_diff(self.revised_box, original, result["revised"],
                    inline=(self.diff_view_var.get() == "Inline"))
        self._show_ambiguities(list(result.get("ambiguities", [])) + warnings)

        note = result.get("note", "")
        if ph_map and not warnings:
            note = (note + "  " if note else "") + f"{len(ph_map)} placeholder(s) preserved"
        self._refresh_status(note or "done")

    def _on_error(self, request_id, message):
        if not self._claim_request(request_id):
            return
        self._refresh_status("error")
        messagebox.showerror("Could not process", message)

    def _revision_is_stale(self):
        """True if the original box no longer matches the live revision."""
        return self.original_box.get("1.0", "end-1c") != self._result_source

    def _on_diff_view_change(self, _value=None):
        """Re-render the current revision when the Clean/Inline toggle changes."""
        if self.last_result:
            render_diff(self.revised_box, self._result_source,
                        self.last_result["revised"],
                        inline=(self.diff_view_var.get() == "Inline"))

    def accept(self):
        """Replace the original with the accepted revision (chains edits)."""
        if not self.last_result:
            return
        if self.busy:
            self._refresh_status(
                "wait for the current request to finish, or press Reject")
            return
        if self._revision_is_stale() and not messagebox.askyesno(
                "Revision may be out of date",
                "The original text changed after this revision was generated. "
                "Accept it anyway and overwrite the current text?"):
            return
        self._remember_for_undo(self.original_box.get("1.0", "end-1c"))
        self.original_box.delete("1.0", "end")
        self.original_box.insert("1.0", self.last_result["revised"])
        self.reject()  # clear the revision pane now it has been folded in
        self._refresh_status("revision accepted")

    def reject(self):
        """Clear the revision pane and drop any in-flight request."""
        self._invalidate_inflight()
        self.revised_box.configure(state="normal")
        self.revised_box.delete("1.0", "end")
        self.revised_box.configure(state="disabled")
        self.last_result = None
        self._result_source = ""
        self._show_ambiguities([])
        self._refresh_status("revision cleared")

    def copy_revision(self):
        if not self.last_result:
            return
        if self._revision_is_stale() and not messagebox.askyesno(
                "Revision may be out of date",
                "The original text changed after this revision was generated. "
                "Copy it anyway?"):
            return
        self.clipboard_clear()
        self.clipboard_append(self.last_result["revised"])
        self._refresh_status("revision copied to clipboard")

    def copy_original(self):
        """Copy the whole Original pane to the clipboard (no revision involved)."""
        text = self.original_box.get("1.0", "end-1c")
        if not text:
            self._refresh_status("nothing to copy")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._refresh_status("original copied to clipboard")

    def paste_original(self):
        """Insert clipboard text into the Original pane.

        An empty or non-text clipboard is reported rather than raising. The
        existing content is pushed onto the undo stack first, so Undo restores
        it; a selection is replaced, otherwise the text lands at the caret.
        """
        try:
            incoming = self.clipboard_get()
        except tk.TclError:
            self._refresh_status("clipboard is empty")
            return
        if not incoming:
            self._refresh_status("clipboard is empty")
            return
        self._remember_for_undo(self.original_box.get("1.0", "end-1c"))
        try:
            sel_start = self.original_box.index("sel.first")
            self.original_box.delete("sel.first", "sel.last")
            self.original_box.mark_set("insert", sel_start)
        except tk.TclError:
            pass  # no selection — insert at the caret
        self.original_box.insert("insert", incoming)
        self._refresh_status("pasted from clipboard")

    def undo(self):
        if not self.undo_stack:
            self._refresh_status("nothing to undo")
            return
        self.reject()
        self.original_box.delete("1.0", "end")
        self.original_box.insert("1.0", self.undo_stack.pop())
        self._refresh_status("undo")

    def clear_all(self):
        self._remember_for_undo(self.original_box.get("1.0", "end-1c"))
        self.original_box.delete("1.0", "end")
        self.reject()
        self._refresh_status("cleared")

    def import_file(self):
        path = filedialog.askopenfilename(
            title="Import text",
            filetypes=[("Text, Markdown and Word", "*.txt *.md *.docx"),
                       ("All files", "*.*")])
        if not path:
            return
        if path.lower().endswith(".docx"):
            try:
                content = read_docx(path)
            except ImportError:
                messagebox.showerror(
                    "Import failed",
                    "Reading Word files needs the python-docx package.\n\n"
                    "Install it with:  pip install python-docx")
                return
            except Exception as exc:  # noqa: BLE001 — bad/locked/corrupt .docx
                messagebox.showerror("Import failed",
                                     f"Could not read the Word file.\n\n{exc}")
                return
        else:
            try:
                # utf-8-sig handles both a BOM-prefixed and a plain UTF-8
                # file, stripping the BOM either way instead of leaving a
                # stray ﻿ in the text sent to the backend.
                with open(path, "r", encoding="utf-8-sig") as fh:
                    content = fh.read()
            except UnicodeDecodeError:
                try:
                    with open(path, "r", encoding="cp1252") as fh:
                        content = fh.read()
                except (OSError, UnicodeDecodeError) as exc:
                    messagebox.showerror(
                        "Import failed",
                        "The file encoding could not be read. Save it as "
                        f"UTF-8 and try again.\n\n({exc})")
                    return
            except OSError as exc:
                messagebox.showerror("Import failed", str(exc))
                return
        self._remember_for_undo(self.original_box.get("1.0", "end-1c"))
        self.reject()
        self.original_box.delete("1.0", "end")
        self.original_box.insert("1.0", content)
        self._refresh_status(f"imported {os.path.basename(path)}")

    def export_file(self):
        if self.last_result and self._revision_is_stale() and not messagebox.askyesno(
                "Revision may be out of date",
                "The original text changed after this revision was generated. "
                "Export it anyway?"):
            return
        text = (self.last_result["revised"] if self.last_result
                else self.original_box.get("1.0", "end-1c"))
        if not text.strip():
            return
        path = filedialog.asksaveasfilename(
            title="Export text", defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md"),
                       ("Word document", "*.docx")])
        if not path:
            return
        try:
            if path.lower().endswith(".docx"):
                write_docx(path, text)
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
        except ImportError:
            messagebox.showerror(
                "Export failed",
                "Saving Word files needs the python-docx package.\n\n"
                "Install it with:  pip install python-docx")
            return
        except ValueError as exc:
            # python-docx raises ValueError for ASCII control characters
            # other than tab/LF/CR — common in text pasted from a PDF.
            messagebox.showerror(
                "Export failed",
                "The text contains a character that cannot be stored in a "
                f"Word document. Try exporting as .txt instead.\n\n{exc}")
            return
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self._refresh_status(f"exported {os.path.basename(path)}")

    def open_settings(self):
        SettingsDialog(self, self.cfg, on_save=self._after_settings)

    def _after_settings(self):
        self._maybe_show_privacy_notice()
        self._refresh_status("settings saved")

    def _start_restore_listener(self):
        """Watch the named restore event so a second launch can wake us up.

        Runs on a daemon thread; the actual window operations happen back on
        the Tk thread via _post_to_ui(), same as every other worker-thread
        callback in this app.
        """
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._restore_event = kernel32.CreateEventW(None, True, False, _RESTORE_EVENT_NAME)

        def _watch():
            while True:
                kernel32.WaitForSingleObject(self._restore_event, _INFINITE)
                kernel32.ResetEvent(self._restore_event)
                try:
                    self._post_to_ui(self._bring_to_front)
                except Exception:
                    # Never let an unexpected error kill this daemon thread --
                    # that would silently disable the restore mechanism for
                    # the rest of the process's life.
                    pass

        threading.Thread(target=_watch, daemon=True).start()

    def _bring_to_front(self):
        """Show the window whether it is visible, minimised, or in the tray."""
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self._finish_tray_restore()
            return
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self):
        """Minimise to tray if that's enabled and actually available.

        Falls through to a normal quit otherwise -- including when
        minimise_to_tray is turned on in config but pystray/Pillow aren't
        installed, so a stale setting can never trap the user with no way
        to reach the window (Alt+F4 always works unless tray genuinely
        took over).
        """
        if self.cfg.get("minimise_to_tray") and TRAY_AVAILABLE:
            self._minimise_to_tray()
            return
        self._quit_app()

    def _quit_app(self):
        """Invalidate in-flight callbacks and actually end the process."""
        self.tray_icon = None
        self._invalidate_inflight()
        self.destroy()

    def _minimise_to_tray(self):
        """Withdraw the window and show a tray icon in its place.

        The icon exists only while the window is hidden: restoring it (via
        its default action or the "Show Scriptorium" menu item) or quitting
        from it tears the icon back down first. There is never a stray icon
        left once the window is visible again, and never an icon thread
        running when it isn't needed.
        """
        if self.tray_icon is not None:
            return  # already minimised
        # 96px preferred for the tray's small canvas; 256px as a fallback.
        # Pillow reads .ico natively, so no separate .png asset is needed.
        icon_dir = resource_path("icon")
        image = None
        for name in ("Scriptorium-96.ico", "Scriptorium-256.ico"):
            candidate = os.path.join(icon_dir, name)
            if os.path.isfile(candidate):
                try:
                    image = PILImage.open(candidate)
                    break
                except OSError:
                    continue
        if image is None:
            # Fail safe: keep the window open rather than vanish with no
            # visible icon and no way back.
            print("[warning] could not load a tray icon from icon/ directory")
            return
        menu = pystray.Menu(
            pystray.MenuItem("Show Scriptorium", self._tray_restore, default=True),
            pystray.MenuItem("Quit", self._tray_quit),
        )
        self.tray_icon = pystray.Icon("Scriptorium", image, "Scriptorium", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.withdraw()

    def _tray_restore(self, icon, _item):
        """Tray callback -- runs on pystray's own thread, not Tk's."""
        icon.stop()
        self._post_to_ui(self._finish_tray_restore)

    def _finish_tray_restore(self):
        self.tray_icon = None
        self.deiconify()
        self.lift()
        self.focus_force()

    def _tray_quit(self, icon, _item):
        """Tray Quit -- runs on pystray's own thread, not Tk's."""
        icon.stop()
        self._post_to_ui(self._quit_app)


def main():
    if not _claim_single_instance():
        _signal_existing_instance()
        return
    app = Scriptorium()
    app.mainloop()


if __name__ == "__main__":
    main()
