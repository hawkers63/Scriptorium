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
- **Optional tone control** — Formal, Neutral, Friendly, Concise, Confident,
  Diplomatic.
- **Writing roles** — an optional context (Creative, Software Developer,
  Executive, Client Relations, Academic, Legal & Compliance) that steers
  vocabulary and register without ever adding facts or bending the rules.
  Role, mode, strength and tone are independent controls that stack.
- **Side-by-side diff** — the revision sits beside the original with changed
  words highlighted.
- **Review controls** — Accept, Reject, Copy, Undo, plus Import and Export.
- **British English throughout** — `organise`, `colour`, `licence`/`license`,
  `-ise` endings, and so on.
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
2. In Settings, switch the backend to **ollama** and name your model.
3. With Ollama running, all processing stays on your machine.

---

## Roadmap

- `.docx` import/export via `python-docx`.
- Placeholder protection for letter templates (`[Name]`, `{{Date}}`).
- British letter conventions (salutation and sign-off normalisation).
- Inline deletion display in the diff view.
- PyInstaller packaging into a standalone `.exe`.

---

## Licence

Personal project by Mark. All rights reserved unless a licence file is added.
