# Scriptorium

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Proprietary | All Rights Reserved](https://img.shields.io/badge/license-Proprietary%20%7C%20All%20Rights%20Reserved-red)](LICENSE)
[![CI](https://github.com/hawkers63/Scriptorium/actions/workflows/ci.yml/badge.svg)](https://github.com/hawkers63/Scriptorium/actions/workflows/ci.yml)

A lightweight **British English writing assistant** for Windows 11. Scriptorium
rewords, corrects, and clarifies text while honouring the author's original
intent. Every result is a *suggested* revision — nothing is applied silently;
you review each change and accept, reject, copy or undo it.

Built in Python with a native-style CustomTkinter interface.

---

## Features

- **Three editing modes**
  - **Paraphrase** — reword while preserving meaning and tone.
  - **Correct** — fix grammar, spelling, punctuation and usage, making the
    minimum changes necessary.
  - **Clarify** — improve readability and structure without adding new claims.
- **Adjustable strength** — Light, Standard, or Substantial.
- **Optional tone control** — choose up to three of twelve tones (Formal,
  Neutral, Casual, Friendly, Diplomatic, Empathetic, Direct, Confident,
  Concise, Detailed, Constructive, Persuasive) via a compact picker. The
  first tone chosen is dominant, the second supports it, and a third is
  only a light accent that's weakened or dropped rather than allowed to
  change content, certainty or scope. Each tone is a bounded, data-driven
  instruction rather than a bare label, so it can only reshape wording and
  register — never invent facts, evidence or detail. Genuinely
  contradictory pairs (e.g. Concise + Detailed, Neutral + Persuasive) are
  refused with an explanation.
- **Writing roles** — an optional context (Creative, Software Developer,
  Engineer, Executive, Project Manager, Client Relations, Academic,
  Technical Writer, Journalist, Legal & Compliance, Lawyer) that steers
  vocabulary and register without ever adding facts, technical conclusions
  or legal interpretation the source doesn't already contain. Role, mode,
  strength and tone are independent controls that stack.
- **Placeholder protection** — placeholders like `[Name]`, `{{Date}}`,
  `{amount}` and `<Date>` are masked before the text is sent and restored
  afterwards, so they are never reworded; if the model drops one, you are
  warned. Toggle it in Settings.
- **Side-by-side diff** — the revision sits beside the original with changed
  words highlighted, with a Clean / Inline toggle; the inline view also shows
  deleted words struck through in red.
- **Review controls** — Accept, Reject, Copy revision, Copy summary, Undo,
  plus Copy/Paste for the Original pane and Import/Export. Text in both
  panes can also be selected and copied (or, for Original, pasted into) via
  right-click.
- **Softer / Stronger** — one-click re-run at the next strength notch down or
  up, instead of changing Strength and pressing Process separately.
- **Writing presets** — a few built-in Mode/Strength/Role/Tone combinations
  (Formal letter, Client reply, Technical note), plus your own: save the
  current toolbar controls under a name via the Preset menu's "Manage
  presets…" command, or delete one later. Applying a preset is always a
  one-off copy — every control stays independently editable afterwards.
- **Minimise to tray, start with Windows** (optional) — the minimise button
  sends the window straight to the system tray instead of the taskbar; the
  close button always quits completely, tray icon included. A "Start with
  Windows" option launches it minimised at logon. Needs the optional
  `pystray` and `Pillow` packages — Settings explains and disables the
  checkbox if they aren't installed, and the app works exactly the same
  without them.
- **Import and export** — plain text and Markdown always; Word `.docx` files
  too when the optional `python-docx` package is installed.
- **British English throughout** — `organise`, `colour`, `licence`/`license`,
  `-ise` endings, and so on.
- **British letter conventions (advisory)** — flags when a salutation and
  sign-off do not match UK convention (impersonal → 'Yours faithfully', named
  → 'Yours sincerely'), without ever rewriting your text. Toggle in Settings.
- **Meaning-preservation safeguards** — names, numbers, quotations, URLs and
  technical terms are left untouched, and genuine ambiguities are flagged
  rather than silently resolved.
- **Two backends**
  - **Claude API** — best rewriting quality; text is sent to Anthropic.
  - **Local Ollama** — fully private; nothing leaves your machine.

---

## Screenshots

See [`docs/screenshots/README.md`](docs/screenshots/README.md).

![Main window](docs/screenshots/main-window.png)

*Main window — Original and Suggested revision panes with mode, strength, role, tone and preset controls.*

![Open menus](docs/screenshots/open-menus.png)

*Toolbar menus open — Role list (and other selectors) for steering register.*

![Settings](docs/screenshots/settings.png)

*Settings — Claude or Ollama backend, placeholder protection, British letter conventions, house style.*

## Requirements

- Windows 11 with Python 3.10 or newer.
- One dependency:

  ```
  pip install -r requirements.txt
  ```

  That installs `customtkinter`, the only required package. Two optional
  extras add features but aren't required to run Scriptorium at all:

  ```
  pip install python-docx        # Word (.docx) import/export
  pip install pystray pillow     # minimise to tray / start with Windows
  ```

---

## Running

```
python scriptorium.py
```

or double-click **Scriptorium.bat**.

On first launch, open **Settings (the gear icon)** and either paste a Claude API
key or switch the backend to Ollama.

---

## Configuration

Settings are stored in `scriptorium_config.json`, created next to the script on
first run. **This file is deliberately excluded from Git** (see `.gitignore`)
because it holds your API key in plain text.

To set up a fresh copy, duplicate the template and add your own key:

```
copy scriptorium_config.example.json scriptorium_config.json
```

Alternatively, leave the key blank in the config and set the
`ANTHROPIC_API_KEY` environment variable instead — the app reads that as a
fallback.

> The Claude API key is a pay-as-you-go key from `console.anthropic.com`. It is
> separate from a Claude.ai subscription.

### Using the local Ollama backend

1. Install [Ollama](https://ollama.com) and pull a model, for example
   `ollama pull llama3.1:8b`.
2. In Settings, switch the backend to **ollama**, then either type the model
   tag or press **Detect** to list the models Ollama currently has installed.
3. With Ollama running, all processing stays on your machine.

To keep the (large) model files on another drive, set the `OLLAMA_MODELS`
environment variable to that folder (for example `D:\\Ollama_Models`) before
starting Ollama.

---

## Building a standalone `.exe`

Package Scriptorium into a single Windows executable that needs no separate
Python install:

```
pip install pyinstaller
pyinstaller scriptorium.spec
```

The build produces `dist\\Scriptorium.exe`. The equivalent one-off command,
without the spec file, is:

```
pyinstaller --onefile --windowed --collect-all customtkinter --name Scriptorium scriptorium.py
```

When run as the packaged `.exe`, settings (including your API key) are stored
under `%LOCALAPPDATA%\\Scriptorium` rather than next to the script.

---

## Roadmap

- Further robustness and polish (from ongoing review) — see `ROADMAP.md`.

---

## Copyright

© 2026 Mark Hawksworth. All rights reserved.

Scriptorium is a private, proprietary work. There is no public licence.
You may not copy, modify, redistribute, or create derivative works
without Mark Hawksworth's prior written consent. Access to the private
GitHub repository is not a grant of those rights.

See `LICENSE`, `COPYRIGHT.md`, and `SECURITY.md`.
