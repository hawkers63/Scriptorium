# Scriptorium

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
- **Optional tone control** — choose up to two of twelve tones (Formal,
  Neutral, Casual, Friendly, Diplomatic, Empathetic, Direct, Confident,
  Concise, Detailed, Constructive, Persuasive) via a compact picker. The
  first tone chosen is dominant; a second is blended in as a supporting
  characteristic. Each tone is a bounded, data-driven instruction rather than
  a bare label, so it can only reshape wording and register — never invent
  facts, evidence or detail. Genuinely contradictory pairs (e.g. Concise +
  Detailed) are refused with an explanation.
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
- **Review controls** — Accept, Reject, Copy, Undo, plus Import and Export.
- **Import and export** — plain text and Markdown always; Word `.docx` files
  too when the optional `python-docx` package is installed.
- **British English throughout** — `organise`, `colour`, `licence`/`license`,
  `-ise` endings, and so on.
- **British letter conventions (advisory)** — flags when a salutation and
  sign-off do not match UK convention (impersonal → ‘Yours faithfully’, named
  → ‘Yours sincerely’), without ever rewriting your text. Toggle in Settings.
- **Meaning-preservation safeguards** — names, numbers, quotations, URLs and
  technical terms are left untouched, and genuine ambiguities are flagged
  rather than silently resolved.
- **Two backends**
  - **Claude API** — best rewriting quality; text is sent to Anthropic.
  - **Local Ollama** — fully private; nothing leaves your machine.

---

## Requirements

- Windows 11 with Python 3.10 or newer.
- One dependency:

  ```
  pip install -r requirements.txt
  ```

  That installs `customtkinter`, the only required package. For Word `.docx`
  import/export, also install the optional extra:

  ```
  pip install python-docx
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
environment variable to that folder (for example `D:\Ollama_Models`) before
starting Ollama.

---

## Building a standalone `.exe`

Package Scriptorium into a single Windows executable that needs no separate
Python install:

```
pip install pyinstaller
pyinstaller scriptorium.spec
```

The build produces `dist\Scriptorium.exe`. The equivalent one-off command,
without the spec file, is:

```
pyinstaller --onefile --windowed --collect-all customtkinter --name Scriptorium scriptorium.py
```

When run as the packaged `.exe`, settings (including your API key) are stored
under `%LOCALAPPDATA%\Scriptorium` rather than next to the script.

---

## Roadmap

- Further robustness and polish (from ongoing review).
- Optional minimise-to-tray and start-with-Windows, deferred until it can be
  tested on a real Windows session.

---

## Licence

Personal project by Mark. All rights reserved unless a licence file is added.
