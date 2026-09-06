# Security

Scriptorium is a private, personal project. Please do not file public
security issues.

## What to protect

- The Anthropic API key in `scriptorium_config.json` (never committed).
- The `ANTHROPIC_API_KEY` environment variable, if used.
- This private GitHub repository and any clone of `C:\\Scriptorium`.

## Reporting

Contact the owner directly (GitHub: hawkers63). Do not open a public
issue that contains a key, a config dump, or a path that would expose
one.

## Agent rules

No Grok Bot may print, commit, push, or quote the contents of
`scriptorium_config.json`, other than to confirm that the file exists
and that the `anthropic_api_key` field is present or empty.
