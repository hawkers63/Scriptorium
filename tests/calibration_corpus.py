"""Fixed twelve-case corpus for v2.31 (E1, selection-scoped processing) calibration.

Shared by two test layers (notes_025):

- test_calibration_e1_deterministic.py drives every case through the real
  make_processing_scope()/assemble_scoped_revision() against a stubbed
  backend response -- mechanical only, no live model.
- calibration_e1.py drives every case through the real pipeline
  (make_processing_scope -> mask_placeholders -> build_system_prompt ->
  run_backend -> restore_placeholders -> assemble_scoped_revision ->
  audit_revision_fidelity) against a live backend.

Both layers must judge the same selections, so the corpus lives here once.
See ROADMAP.md's v2.31 section for the category list this corpus covers and
the full write-up of the 2026-09-07 run three of these cases reconstruct
verbatim.

Each case is a plain dict:
  name               unique slug
  category           human-readable category label (every ROADMAP v2.31
                      category is covered at least once)
  full_original       the complete Original text
  prefix/selected/suffix
                      the exact split; prefix + selected + suffix must equal
                      full_original character-for-character (this is
                      verified by make_processing_scope() itself in the
                      deterministic test, not duplicated here)
  mode/strength/role/tones
                      the request parameters make_processing_scope()'s
                      result is processed under -- varied across cases so
                      the corpus exercises more than one mode/strength/role/
                      tone combination, per the ROADMAP note's own
                      requirement
  protected_tokens    substrings expected to survive verbatim in the
                      assembled revision (proper nouns, dates, money, a
                      quotation, placeholder originals, URLs/emails/paths).
                      Checked byte-for-byte; a miss is advisory (DRIFT), not
                      an automatic hard failure, since a legitimate rewrite
                      can occasionally reword around one.
  forbidden_content    substrings that must NOT appear in the revision --
                      concrete, documented hallucination/invention
                      signatures where one is known (case 9's exact
                      hallucinated phrases from the 2026-09-07 run);
                      empty where nothing specific is yet known.
  already_correct     True if the selection needs no edit at all -- the
                      system prompt's own "if the text needs no change,
                      return it unchanged" rule is what is under test.
  genuinely_ambiguous True if resolving the passage properly would require
                      guessing missing context -- the model is expected to
                      flag this as an ambiguity, not invent a resolution.
  known_problem       None, or a short description of which 2026-09-07
                      failure/drift this case reconstructs verbatim.
"""

CASES = [
    {
        "name": "mid_sentence_leading_punctuation",
        "category": "mid-sentence selection, leading punctuation boundary",
        "full_original": (
            "The quarterly report was late, and the team worked through the "
            "weekend to finsh it before the board meeting on Friday."
        ),
        "prefix": "The quarterly report was late, ",
        "selected": (
            "and the team worked through the weekend to finsh it before the "
            "board meeting on Friday."
        ),
        "suffix": "",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": ("Friday",),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "mid_sentence_trailing_comma_known_drift",
        "category": "mid-sentence selection ending in a comma",
        "full_original": (
            "The contract must be signed by the client no later then 12 March "
            "2026, otherwise the offer will lapse automatically."
        ),
        "prefix": "The contract must be signed by the client ",
        "selected": "no later then 12 March 2026,",
        "suffix": " otherwise the offer will lapse automatically.",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        # The trailing comma itself is the point of this case (see
        # known_problem below) -- without it here, the 2026-09-07 drift
        # silently classifies as PASS instead of DRIFT (confirmed: the live
        # 2026-09-07 rerun reproduced the exact drop in 3/3 runs and this
        # gap let it through uncaught until spotted by hand).
        "protected_tokens": ("12 March 2026,",),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": (
            "2026-09-07 Ollama (llama3.2:3b) run: dropped the trailing comma "
            "at the selection boundary ('...12 March 2026,' -> '...12 March "
            "2026'), leaving a small grammatical seam once spliced into the "
            "fixed suffix. Not caught by audit_revision_fidelity() (no bare-"
            "comma check exists), so this is exactly the kind of boundary "
            "drift the live harness's own trailing-character check exists to "
            "catch."
        ),
    },
    {
        "name": "pronoun_antecedent_outside_selection",
        "category": "pronoun antecedent outside the selection",
        "full_original": (
            "Sarah finished the annual budget report last night. She had "
            "checked every figure twice before submitting it to the finance "
            "director."
        ),
        "prefix": "Sarah finished the annual budget report last night. ",
        "selected": (
            "She had checked every figure twice before submitting it to the "
            "finance director."
        ),
        "suffix": "",
        "mode": "Paraphrase",
        "strength": "Light",
        "role": "Executive",
        "tones": ("Concise",),
        "protected_tokens": ("finance director",),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "negation_modality_hedges",
        "category": "negation, modality and hedges",
        "full_original": (
            "The results might not fully explain the delay. It is possible "
            "that additional factors were involved, although this has not "
            "yet been confirmed."
        ),
        "prefix": "The results might not fully explain the delay. ",
        "selected": (
            "It is possible that additional factors were involved, although "
            "this has not yet been confirmed."
        ),
        "suffix": "",
        "mode": "Clarify",
        "strength": "Light",
        "role": "Academic",
        "tones": ("Neutral",),
        "protected_tokens": ("might not", "has not yet been confirmed"),
        # A hedge word swapped for confirmatory language is a real, previously
        # confirmed failure mode (v2.11 calibration) -- see
        # mark_meaning_preservation_priority memory.
        "forbidden_content": (
            "is certain", "definitely confirmed", "has now been confirmed",
        ),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "quantities_dates_money_percentages",
        "category": "quantities, dates, money and percentages",
        "full_original": (
            "Revenue grew by 12.5% to \u00a34,750,000 in the year ending 31 "
            "March 2026, up form \u00a34,220,000 the previous year."
        ),
        "prefix": (
            "Revenue grew by 12.5% to \u00a34,750,000 in the year ending 31 "
            "March 2026, "
        ),
        "selected": "up form \u00a34,220,000 the previous year.",
        "suffix": "",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": ("\u00a34,220,000",),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "quotation_straight_quotes_known_drift",
        "category": "quotation containing straight quotation marks",
        "full_original": (
            "The site engineer confirmed that \"the foundations remain "
            "sound,\" even dough cracking was visible on the north wall."
        ),
        "prefix": "The site engineer confirmed that ",
        "selected": (
            "\"the foundations remain sound,\" even dough cracking was "
            "visible on the north wall."
        ),
        "suffix": "",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": ("\"the foundations remain sound,\"",),
        "forbidden_content": (
            "\u201cthe foundations remain sound,\u201d",
            "\u201cthe foundations remain sound,\"",
            "\"the foundations remain sound,\u201d",
        ),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": (
            "2026-09-07 Ollama (llama3.2:3b) run: straight quotation marks "
            "around 'the foundations remain sound,' were silently replaced "
            "with smart/curly quotes -- caught by "
            "audit_revision_fidelity()'s protected-quote check, but still a "
            "real loss of exact punctuation fidelity inside supposedly-"
            "protected content."
        ),
    },
    {
        "name": "url_and_email",
        "category": "URL and email address together",
        "full_original": (
            "For further details, visit https://www.example.co.uk/reports or "
            "email compliance@example.co.uk before teh deadline."
        ),
        "prefix": "For further details, visit ",
        "selected": (
            "https://www.example.co.uk/reports or email "
            "compliance@example.co.uk before teh deadline."
        ),
        "suffix": "",
        "mode": "Correct",
        "strength": "Standard",
        "role": "Technical Writer",
        "tones": (),
        "protected_tokens": (
            "https://www.example.co.uk/reports", "compliance@example.co.uk",
        ),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "windows_path_and_all_placeholder_shapes",
        "category": "Windows path with all four placeholder shapes",
        "full_original": (
            "Please save the completed form as C:\\Users\\Reports\\Q1.docx "
            "and send it too [Name] together with the {{Date}} and {amount} "
            "shown on the <Date> cover sheet."
        ),
        "prefix": "Please save the completed form as ",
        "selected": (
            "C:\\Users\\Reports\\Q1.docx and send it too [Name] together "
            "with the {{Date}} and {amount} shown on the <Date> cover sheet."
        ),
        "suffix": "",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": (
            "C:\\Users\\Reports\\Q1.docx", "[Name]", "{{Date}}", "{amount}",
            "<Date>",
        ),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "markdown_list_item_short_imperative_known_hallucination",
        "category": "Markdown list item, short imperative fragment",
        "full_original": (
            "## Pre-submission checklist\n"
            "- Check the cover page for the correct reference number.\n"
            "- Review the middle item carefully for errors.\n"
            "- Confirm the signature block is complete.\n"
        ),
        "prefix": (
            "## Pre-submission checklist\n"
            "- Check the cover page for the correct reference number.\n"
            "- "
        ),
        "selected": "Review the middle item carefully for errors.",
        "suffix": "\n- Confirm the signature block is complete.\n",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": ("Review the middle item carefully for errors.",),
        # The exact off-topic phrases the 2026-09-07 Ollama run hallucinated
        # for this identical selection (ROADMAP.md v2.31 write-up).
        "forbidden_content": ("licence holders", "programme events"),
        "already_correct": True,
        "genuinely_ambiguous": False,
        "known_problem": (
            "2026-09-07 Ollama (llama3.2:3b) run: this exact short, "
            "imperative-phrased, already-correct selection returned entirely "
            "unrelated hallucinated content about 'licence holders' and "
            "'programme events' rather than a revision of the given text -- "
            "the one real, severe failure this calibration gate exists to "
            "catch. See ROADMAP.md's v2.31 section and the "
            "mark_meaning_preservation_priority memory."
        ),
    },
    {
        "name": "markdown_heading_blank_line_boundaries",
        "category": "Markdown heading with blank-line boundaries",
        "full_original": (
            "Introduction\n\n"
            "## Projct Overview\n\n"
            "This section summarises the scope and timeline for "
            "stakeholders.\n"
        ),
        "prefix": "Introduction\n\n",
        "selected": "## Projct Overview\n\n",
        "suffix": (
            "This section summarises the scope and timeline for "
            "stakeholders.\n"
        ),
        "mode": "Correct",
        "strength": "Light",
        "role": "(none)",
        "tones": (),
        "protected_tokens": ("Overview",),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "already_correct_selection",
        "category": "already-correct selection",
        "full_original": (
            "The meeting has been rescheduled to Thursday at 10 a.m. in the "
            "main conference room."
        ),
        "prefix": "The meeting has been rescheduled to ",
        "selected": "Thursday at 10 a.m. in the main conference room.",
        "suffix": "",
        "mode": "Correct",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": (
            "Thursday at 10 a.m. in the main conference room.",
        ),
        "forbidden_content": (),
        "already_correct": True,
        "genuinely_ambiguous": False,
        "known_problem": None,
    },
    {
        "name": "genuinely_ambiguous_fragment",
        "category": "genuinely ambiguous fragment",
        "full_original": (
            "The quarterly review meeting ran long. The manager told the "
            "client that her presentation had inspired the new strategy, and "
            "she was delighted with the result. Everyone left in good "
            "spirits."
        ),
        "prefix": "The quarterly review meeting ran long. ",
        "selected": (
            "The manager told the client that her presentation had inspired "
            "the new strategy, and she was delighted with the result."
        ),
        "suffix": " Everyone left in good spirits.",
        "mode": "Clarify",
        "strength": "Standard",
        "role": "(none)",
        "tones": (),
        "protected_tokens": (),
        "forbidden_content": (),
        "already_correct": False,
        "genuinely_ambiguous": True,
        "known_problem": None,
    },
]

CASES_BY_NAME = {case["name"]: case for case in CASES}

KNOWN_PROBLEM_CASES = [case for case in CASES if case["known_problem"]]
