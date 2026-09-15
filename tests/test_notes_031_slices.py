"""Mechanical (no live model, no GUI) regression tests for the six slices
notes_031 proposed and this session implemented: A (empty-pane import hint),
B (preset-match clearing), C (tone reorder), D1 (bounded role wording +
precedence rule; D2/D3 remain calibration-gated behind FALSE flags), E
(clean rich copy + reading estimates) and F (Retry-After policy).

Consistent with this suite's existing boundary (see pytest.ini): no Tk/
CustomTkinter widget is created here. The trace-wired preset-comparison
methods (_queue_preset_check/_check_preset_match) and the TonePickerDialog
reorder controls were exercised manually against real Tk widgets during
implementation; only their pure logic (preset_control_signature,
move_selected_tone) is covered by this file.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scriptorium  # noqa: E402 -- import must follow the sys.path fix-up above


# --------------------------------------------------------------------------- #
#  A -- original_heading_text()
# --------------------------------------------------------------------------- #

def test_original_heading_empty_with_drop_available():
    assert (scriptorium.original_heading_text("", True)
            == "Original · drop a file or paste text")


def test_original_heading_empty_without_drop_available():
    assert (scriptorium.original_heading_text("", False)
            == "Original · paste text or use Import…")


def test_original_heading_non_empty_ignores_drop_state():
    assert scriptorium.original_heading_text("hello", True) == "Original"
    assert scriptorium.original_heading_text("hello", False) == "Original"


def test_original_heading_any_non_empty_buffer_hides_hint():
    # Guidance is for an empty editor, not content detection -- a single
    # space still counts as "not empty" for this purpose.
    assert scriptorium.original_heading_text(" ", True) == "Original"


# --------------------------------------------------------------------------- #
#  B -- preset_control_signature()
# --------------------------------------------------------------------------- #

def test_preset_control_signature_none_for_invalid_preset():
    assert scriptorium.preset_control_signature(None) is None
    assert scriptorium.preset_control_signature({"mode": "bogus"}) is None


def test_preset_control_signature_equal_for_identical_controls():
    preset = {"mode": "Paraphrase", "strength": "Light", "role": "Academic",
              "tones": ["Concise"], "voice": None}
    assert (scriptorium.preset_control_signature(preset)
            == scriptorium.preset_control_signature(dict(preset)))


def test_preset_control_signature_differs_on_strength():
    base = {"mode": "Paraphrase", "strength": "Light", "role": "Academic",
            "tones": ["Concise"], "voice": None}
    changed = dict(base, strength="Substantial")
    assert (scriptorium.preset_control_signature(base)
            != scriptorium.preset_control_signature(changed))


def test_preset_control_signature_differs_on_tone_order():
    # Formal->Concise and Concise->Formal carry different emphasis --
    # comparing tone sets instead of ordered tuples would be wrong.
    base = {"mode": "Paraphrase", "strength": "Light", "role": "(none)",
            "tones": ["Formal", "Concise"], "voice": None}
    reordered = dict(base, tones=["Concise", "Formal"])
    assert (scriptorium.preset_control_signature(base)
            != scriptorium.preset_control_signature(reordered))


def test_preset_control_signature_includes_legacy_voice_reference():
    base = {"mode": "Paraphrase", "strength": "Light", "role": "(none)",
            "tones": [], "voice": None}
    with_voice = dict(base, voice="Author brief")
    assert (scriptorium.preset_control_signature(base)
            != scriptorium.preset_control_signature(with_voice))


# --------------------------------------------------------------------------- #
#  C -- move_selected_tone()
# --------------------------------------------------------------------------- #

def test_move_selected_tone_earlier():
    order = ["Formal", "Concise", "Diplomatic"]
    assert (scriptorium.move_selected_tone(order, "Diplomatic", -1)
            == ["Formal", "Diplomatic", "Concise"])


def test_move_selected_tone_later():
    order = ["Formal", "Concise", "Diplomatic"]
    assert (scriptorium.move_selected_tone(order, "Formal", 1)
            == ["Concise", "Formal", "Diplomatic"])


def test_move_selected_tone_at_edge_is_a_no_op():
    order = ["Formal", "Concise", "Diplomatic"]
    assert scriptorium.move_selected_tone(order, "Formal", -1) == order
    assert scriptorium.move_selected_tone(order, "Diplomatic", 1) == order


def test_move_selected_tone_never_toggles_membership():
    order = ["Formal", "Concise"]
    moved = scriptorium.move_selected_tone(order, "Concise", -1)
    assert set(moved) == set(order)
    assert len(moved) == len(order)


def test_move_selected_tone_missing_tone_is_a_no_op():
    assert scriptorium.move_selected_tone(["Formal"], "Concise", 1) == ["Formal"]


def test_move_selected_tone_empty_selection():
    assert scriptorium.move_selected_tone([], "Formal", 1) == []


def test_move_selected_tone_rejects_bad_step():
    with pytest.raises(ValueError):
        scriptorium.move_selected_tone(["Formal", "Concise"], "Formal", 2)


def test_move_selected_tone_rejects_hard_conflict_result():
    # validate_tones() remains the sole authority; a reorder can never
    # smuggle an already-invalid combination through.
    with pytest.raises(ValueError):
        scriptorium.move_selected_tone(["Concise", "Detailed"], "Detailed", -1)


# --------------------------------------------------------------------------- #
#  E1 -- build_clean_revision_html()
# --------------------------------------------------------------------------- #

def test_build_clean_revision_html_escapes_and_breaks_lines():
    out = scriptorium.build_clean_revision_html("Line one\r\nLine <two>\nLine three")
    assert "<br>" in out
    assert "&lt;two&gt;" in out
    assert "<del" not in out and "<strong" not in out  # no review marks


def test_build_clean_revision_html_non_ascii_round_trips_as_text():
    out = scriptorium.build_clean_revision_html("Price: £5 — café")
    assert "£5" in out and "café" in out


# --------------------------------------------------------------------------- #
#  E2 -- review_reading_estimate()
# --------------------------------------------------------------------------- #

def test_review_reading_estimate_below_word_floor():
    estimate = scriptorium.review_reading_estimate("just a few words here")
    assert "reading estimate not shown below 20 words" in estimate


def test_review_reading_estimate_200_words_is_about_one_minute():
    text = " ".join(["word"] * 200)
    assert "about 1 min read" in scriptorium.review_reading_estimate(text)


def test_review_reading_estimate_201_words_is_about_two_minutes():
    text = " ".join(["word"] * 201)
    assert "about 2 min read" in scriptorium.review_reading_estimate(text)


def test_review_reading_estimate_under_200_words_shown_as_under_a_minute():
    text = " ".join(["word"] * 100)
    assert "under a minute" in scriptorium.review_reading_estimate(text)


def test_review_reading_estimate_includes_word_and_character_counts():
    estimate = scriptorium.review_reading_estimate(" ".join(["word"] * 25))
    assert "25 words" in estimate
    assert "characters" in estimate


# --------------------------------------------------------------------------- #
#  F -- _retry_after_seconds() / _retry_delay()
# --------------------------------------------------------------------------- #

def test_retry_after_seconds_parses_plain_integer():
    assert scriptorium._retry_after_seconds({"Retry-After": "120"}) == 120.0


def test_retry_after_seconds_no_longer_shortens_a_long_delay():
    # Historically this clamped to MAX_RETRY_AFTER (30.0); the policy now
    # keeps the parser honest and lets _retry_delay() decide what to do.
    assert scriptorium._retry_after_seconds({"Retry-After": "120"}) != 30.0


def test_retry_after_seconds_rejects_negative_and_fractional_numeric_strings():
    assert scriptorium._retry_after_seconds({"Retry-After": "-5"}) is None
    assert scriptorium._retry_after_seconds({"Retry-After": "5.5"}) is None


def test_retry_after_seconds_rejects_non_finite_and_malformed_text():
    assert scriptorium._retry_after_seconds({"Retry-After": "nan"}) is None
    assert scriptorium._retry_after_seconds({"Retry-After": "inf"}) is None
    assert scriptorium._retry_after_seconds({"Retry-After": "not-a-date"}) is None
    assert scriptorium._retry_after_seconds({"Retry-After": "x" * 200}) is None


def test_retry_after_seconds_missing_or_empty_header():
    assert scriptorium._retry_after_seconds({}) is None
    assert scriptorium._retry_after_seconds(None) is None
    assert scriptorium._retry_after_seconds({"Retry-After": ""}) is None


def test_retry_after_seconds_past_http_date_is_zero():
    assert (scriptorium._retry_after_seconds(
        {"Retry-After": "Mon, 01 Jan 1990 00:00:00 GMT"}) == 0.0)


def test_retry_delay_within_budget_returns_the_wait():
    assert scriptorium._retry_delay(0, {"Retry-After": "30"}) == 30.0
    assert scriptorium._retry_delay(0, {"Retry-After": "0"}) == 0.0


def test_retry_delay_beyond_budget_stops_the_request():
    with pytest.raises(scriptorium.BackendError, match="120"):
        scriptorium._retry_delay(0, {"Retry-After": "120"})


def test_retry_delay_without_header_falls_back_to_bounded_backoff():
    delay = scriptorium._retry_delay(0)
    assert 0 <= delay <= scriptorium.MAX_RETRY_DELAY


# --------------------------------------------------------------------------- #
#  D1 -- bounded role wording + precedence rule
# --------------------------------------------------------------------------- #

def test_build_system_prompt_includes_role_mode_precedence():
    prompt = scriptorium.build_system_prompt(
        "Paraphrase", "Standard", [], role="(none)")
    assert "preserve meaning and protected content first" in prompt


def test_executive_role_preserves_unresolved_questions():
    instruction = scriptorium.ROLE_INSTRUCTIONS["Executive"]
    assert "never" in instruction
    assert "invent a decision" in instruction


def test_project_manager_role_keeps_questions_as_questions():
    instruction = scriptorium.ROLE_INSTRUCTIONS["Project Manager"]
    assert "Keep questions as questions" in instruction


def test_client_relations_role_does_not_default_to_reassurance():
    instruction = scriptorium.ROLE_INSTRUCTIONS["Client Relations"]
    assert "never add them merely to make the reply warmer" in instruction


# --------------------------------------------------------------------------- #
#  D2/D3 -- calibration-gated candidates remain off by default
# --------------------------------------------------------------------------- #

def test_correspondence_role_disabled_by_default():
    assert scriptorium.ENABLE_CORRESPONDENCE_ROLE is False
    assert "Personal Correspondence" not in scriptorium.ROLES
    assert "Personal Correspondence" not in scriptorium.ROLE_INSTRUCTIONS


def test_firm_tone_disabled_by_default():
    assert scriptorium.ENABLE_FIRM_TONE is False
    assert "Firm" not in scriptorium.TONE_INSTRUCTIONS
    assert "Firm" not in scriptorium.TONES
