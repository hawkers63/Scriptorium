"""Mechanical (no live model) regression tests for the voice profile and
two-pass plumbing notes_030 proposed (v2.33 schema/prompt block; v2.34
preset.voice field, derive-brief helpers, two-pass mode list) ahead of any
live calibration pass. No network access, no live model.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scriptorium  # noqa: E402 -- import must follow the sys.path fix-up above


# --------------------------------------------------------------------------- #
#  normalise_voice_profile()
# --------------------------------------------------------------------------- #

def test_normalise_voice_profile_rejects_non_dict():
    assert scriptorium.normalise_voice_profile("not a dict") is None
    assert scriptorium.normalise_voice_profile(None) is None


def test_normalise_voice_profile_rejects_empty_profile():
    assert scriptorium.normalise_voice_profile({}) is None
    assert scriptorium.normalise_voice_profile({"samples": [], "style_brief": ""}) is None


def test_normalise_voice_profile_keeps_brief_only():
    profile = scriptorium.normalise_voice_profile({"style_brief": "Short, direct sentences."})
    assert profile is not None
    assert profile["style_brief"] == "Short, direct sentences."
    assert profile["samples"] == []
    assert profile["preferred"] is None


def test_normalise_voice_profile_caps_samples_and_length():
    long_sample = "x" * (scriptorium.MAX_SAMPLE_CHARS + 500)
    samples = [f"sample {i}" for i in range(scriptorium.MAX_VOICE_SAMPLES + 5)]
    samples.append(long_sample)
    profile = scriptorium.normalise_voice_profile({"samples": samples})
    assert len(profile["samples"]) == scriptorium.MAX_VOICE_SAMPLES
    assert all(len(s) <= scriptorium.MAX_SAMPLE_CHARS for s in profile["samples"])


def test_normalise_voice_profile_caps_style_brief_length():
    profile = scriptorium.normalise_voice_profile(
        {"style_brief": "y" * (scriptorium.MAX_STYLE_BRIEF_CHARS + 200)})
    assert len(profile["style_brief"]) == scriptorium.MAX_STYLE_BRIEF_CHARS


def test_normalise_voice_profile_accepts_single_string_sample():
    profile = scriptorium.normalise_voice_profile({"samples": "just one sample"})
    assert profile["samples"] == ["just one sample"]


def test_normalise_voice_profile_drops_invalid_preferred():
    profile = scriptorium.normalise_voice_profile({
        "style_brief": "Formal register.",
        "preferred": {"mode": "NotAMode", "strength": "Standard",
                      "role": "Academic", "tones": []},
    })
    assert profile["preferred"] is None


def test_normalise_voice_profile_keeps_valid_preferred():
    preferred = {"mode": "Paraphrase", "strength": "Substantial",
                 "role": "Academic", "tones": ["Concise"]}
    profile = scriptorium.normalise_voice_profile({"preferred": preferred})
    assert profile["preferred"] == preferred


def test_normalise_voice_profile_caps_avoid_extra():
    words = [f"word{i}" for i in range(scriptorium.MAX_VOICE_AVOID + 10)]
    profile = scriptorium.normalise_voice_profile({
        "style_brief": "brief", "avoid_extra": words})
    assert len(profile["avoid_extra"]) <= scriptorium.MAX_VOICE_AVOID


# --------------------------------------------------------------------------- #
#  normalise_voice_profiles()
# --------------------------------------------------------------------------- #

def test_normalise_voice_profiles_rejects_non_dict():
    assert scriptorium.normalise_voice_profiles([]) == {}


def test_normalise_voice_profiles_drops_reserved_names():
    value = {"(none)": {"style_brief": "x"},
             scriptorium.PRESET_MANAGER_LABEL: {"style_brief": "y"},
             "Mark": {"style_brief": "z"}}
    cleaned = scriptorium.normalise_voice_profiles(value)
    assert list(cleaned) == ["Mark"]


def test_normalise_voice_profiles_caps_profile_count():
    value = {f"Voice{i}": {"style_brief": f"brief {i}"}
             for i in range(scriptorium.MAX_VOICE_PROFILES + 5)}
    cleaned = scriptorium.normalise_voice_profiles(value)
    assert len(cleaned) == scriptorium.MAX_VOICE_PROFILES


def test_normalise_voice_profiles_only_first_active_wins():
    value = {"A": {"style_brief": "a", "active": True},
              "B": {"style_brief": "b", "active": True}}
    cleaned = scriptorium.normalise_voice_profiles(value)
    actives = [name for name, p in cleaned.items() if p["active"]]
    assert actives == ["A"]


def test_normalise_voice_profiles_drops_malformed_entries_silently_by_default():
    value = {"Good": {"style_brief": "fine"}, "Bad": "not a dict", 5: {"style_brief": "x"}}
    cleaned = scriptorium.normalise_voice_profiles(value)
    assert list(cleaned) == ["Good"]


# --------------------------------------------------------------------------- #
#  resolve_active_voice_profile()
# --------------------------------------------------------------------------- #

def test_resolve_active_voice_profile_none_when_unset():
    cfg = {"voice_profiles": {}, "active_voice": None}
    assert scriptorium.resolve_active_voice_profile(cfg) is None


def test_resolve_active_voice_profile_returns_named_profile():
    profile = {"style_brief": "brief", "samples": [], "avoid_extra": [], "preferred": None}
    cfg = {"voice_profiles": {"Mark": profile}, "active_voice": "Mark"}
    assert scriptorium.resolve_active_voice_profile(cfg) is profile


def test_resolve_active_voice_profile_missing_name_returns_none():
    cfg = {"voice_profiles": {}, "active_voice": "Ghost"}
    assert scriptorium.resolve_active_voice_profile(cfg) is None


# --------------------------------------------------------------------------- #
#  build_voice_instruction()
# --------------------------------------------------------------------------- #

def test_build_voice_instruction_empty_when_no_profile():
    assert scriptorium.build_voice_instruction(None, "Paraphrase") == ""


def test_build_voice_instruction_empty_when_profile_has_nothing_to_say():
    assert scriptorium.build_voice_instruction(
        {"style_brief": "", "avoid_extra": []}, "Paraphrase") == ""


def test_build_voice_instruction_blocked_in_correct_mode_by_default():
    assert scriptorium.APPLY_VOICE_IN_CORRECT is False
    profile = {"style_brief": "Terse, formal.", "avoid_extra": []}
    assert scriptorium.build_voice_instruction(profile, "Correct") == ""


def test_build_voice_instruction_present_for_paraphrase():
    profile = {"style_brief": "Terse, formal, favours short sentences.",
               "avoid_extra": ["utilise"]}
    line = scriptorium.build_voice_instruction(profile, "Paraphrase")
    assert "Terse, formal, favours short sentences." in line
    assert '"utilise"' in line
    assert "must not add facts" in line


def test_build_voice_instruction_never_inlines_samples():
    profile = {"style_brief": "brief text",
               "samples": ["a private sample sentence nobody else should see"],
               "avoid_extra": []}
    line = scriptorium.build_voice_instruction(profile, "Paraphrase")
    assert "private sample sentence" not in line


# --------------------------------------------------------------------------- #
#  build_system_prompt() integration
# --------------------------------------------------------------------------- #

def test_build_system_prompt_without_voice_profile_is_unchanged_shape():
    prompt = scriptorium.build_system_prompt(
        "Paraphrase", "Standard", [], role="(none)")
    assert "Author voice" not in prompt


def test_build_system_prompt_includes_voice_block_when_given():
    profile = {"style_brief": "Prefers short, direct sentences.", "avoid_extra": []}
    prompt = scriptorium.build_system_prompt(
        "Paraphrase", "Standard", [], role="(none)", voice_profile=profile)
    assert "Author voice" in prompt
    assert "Prefers short, direct sentences." in prompt


def test_build_system_prompt_correct_mode_ignores_voice_profile_by_default():
    profile = {"style_brief": "Prefers short, direct sentences.", "avoid_extra": []}
    prompt = scriptorium.build_system_prompt(
        "Correct", "Standard", [], role="(none)", voice_profile=profile)
    assert "Author voice" not in prompt


def test_build_system_prompt_correct_mode_includes_spelling_addendum():
    prompt = scriptorium.build_system_prompt("Correct", "Standard", [], role="(none)")
    assert "Spelling checklist" in prompt
    assert "organise/realise" in prompt


def test_build_system_prompt_non_correct_mode_excludes_spelling_addendum():
    prompt = scriptorium.build_system_prompt("Paraphrase", "Standard", [], role="(none)")
    assert "Spelling checklist" not in prompt


# --------------------------------------------------------------------------- #
#  normalise_config() wiring
# --------------------------------------------------------------------------- #

def test_normalise_config_defaults_voice_profiles_empty():
    clean = scriptorium.normalise_config(dict(scriptorium.DEFAULT_CONFIG))
    assert clean["voice_profiles"] == {}
    assert clean["active_voice"] is None


def test_normalise_config_derives_active_voice_from_flagged_profile():
    cfg = dict(scriptorium.DEFAULT_CONFIG)
    cfg["voice_profiles"] = {"Mark": {"style_brief": "brief", "active": True}}
    cfg["active_voice"] = None
    clean = scriptorium.normalise_config(cfg)
    assert clean["active_voice"] == "Mark"


def test_normalise_config_drops_active_voice_referencing_missing_profile():
    cfg = dict(scriptorium.DEFAULT_CONFIG)
    cfg["voice_profiles"] = {}
    cfg["active_voice"] = "Ghost"
    clean = scriptorium.normalise_config(cfg)
    assert clean["active_voice"] is None


def test_normalise_config_two_pass_defaults_false_and_coerces_strings():
    clean = scriptorium.normalise_config(dict(scriptorium.DEFAULT_CONFIG))
    assert clean["two_pass_correct_then_style"] is False

    cfg = dict(scriptorium.DEFAULT_CONFIG)
    cfg["two_pass_correct_then_style"] = "true"
    assert scriptorium.normalise_config(cfg)["two_pass_correct_then_style"] is True


# --------------------------------------------------------------------------- #
#  normalise_user_presets() -- preset.voice field (v2.34, notes_030 §2.3)
# --------------------------------------------------------------------------- #

def test_normalise_user_presets_keeps_valid_voice_reference():
    profiles = {"Mark": {"style_brief": "brief"}}
    presets = {"Letter": {"mode": "Correct", "strength": "Standard",
                          "role": "Academic", "tones": [], "voice": "Mark"}}
    clean = scriptorium.normalise_user_presets(presets, voice_profiles=profiles)
    assert clean["Letter"]["voice"] == "Mark"


def test_normalise_user_presets_drops_dangling_voice_reference():
    presets = {"Letter": {"mode": "Correct", "strength": "Standard",
                          "role": "Academic", "tones": [], "voice": "Ghost"}}
    clean = scriptorium.normalise_user_presets(presets, voice_profiles={})
    assert clean["Letter"]["voice"] is None


def test_normalise_user_presets_no_voice_profiles_known_drops_silently():
    presets = {"Letter": {"mode": "Correct", "strength": "Standard",
                          "role": "Academic", "tones": []}}
    clean = scriptorium.normalise_user_presets(presets)
    assert clean["Letter"]["voice"] is None


def test_normalise_config_end_to_end_preset_voice_survives():
    cfg = dict(scriptorium.DEFAULT_CONFIG)
    cfg["voice_profiles"] = {"Mark": {"style_brief": "brief"}}
    cfg["user_presets"] = {
        "Letter": {"mode": "Correct", "strength": "Standard",
                  "role": "Academic", "tones": [], "voice": "Mark"}}
    clean = scriptorium.normalise_config(cfg)
    assert clean["user_presets"]["Letter"]["voice"] == "Mark"


# --------------------------------------------------------------------------- #
#  import_preset_pack() -- must not clear an untouched preset's own voice
# --------------------------------------------------------------------------- #

def test_import_preset_pack_preserves_existing_presets_voice(tmp_path):
    voice_profiles = {"Mark": {"style_brief": "brief"}}
    existing = {"Letter": {"mode": "Correct", "strength": "Standard",
                          "role": "Academic", "tones": [], "voice": "Mark"}}
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(json.dumps({
        "format": scriptorium.PRESET_PACK_FORMAT,
        "version": scriptorium.PRESET_PACK_VERSION,
        "presets": {"Other": {"mode": "Clarify", "strength": "Light",
                              "role": "(none)", "tones": []}},
    }), encoding="utf-8")

    merged, messages = scriptorium.import_preset_pack(
        str(pack_path), existing, voice_profiles=voice_profiles)
    assert not messages
    assert merged["Letter"]["voice"] == "Mark"
    assert merged["Other"]["voice"] is None


def test_import_preset_pack_without_voice_profiles_clears_existing_voice():
    """Documents the pre-fix behaviour so a future caller cannot reintroduce
    it silently: omitting voice_profiles is only safe when the caller has
    no voice-bearing presets to preserve."""
    existing = {"Letter": {"mode": "Correct", "strength": "Standard",
                          "role": "Academic", "tones": [], "voice": "Mark"}}
    merged = scriptorium.normalise_user_presets(existing)
    assert merged["Letter"]["voice"] is None


# --------------------------------------------------------------------------- #
#  resolve_voice_profile() / resolve_active_voice_profile()
# --------------------------------------------------------------------------- #

def test_resolve_voice_profile_returns_named_profile():
    profile = {"style_brief": "brief"}
    cfg = {"voice_profiles": {"Mark": profile}}
    assert scriptorium.resolve_voice_profile(cfg, "Mark") is profile


def test_resolve_voice_profile_none_for_non_string_name():
    cfg = {"voice_profiles": {"Mark": {"style_brief": "brief"}}}
    assert scriptorium.resolve_voice_profile(cfg, None) is None


def test_resolve_active_voice_profile_reads_cfg_active_voice():
    profile = {"style_brief": "brief"}
    cfg = {"voice_profiles": {"Mark": profile}, "active_voice": "Mark"}
    assert scriptorium.resolve_active_voice_profile(cfg) is profile


# --------------------------------------------------------------------------- #
#  TWO_PASS_ELIGIBLE_MODES (v2.34, notes_030 §2.2 B2)
# --------------------------------------------------------------------------- #

def test_two_pass_eligible_modes_is_paraphrase_and_clarify_only():
    assert set(scriptorium.TWO_PASS_ELIGIBLE_MODES) == {"Paraphrase", "Clarify"}
    assert "Correct" not in scriptorium.TWO_PASS_ELIGIBLE_MODES


# --------------------------------------------------------------------------- #
#  _extract_style_brief() -- derive-brief's plain-text reply parser
# --------------------------------------------------------------------------- #

def test_extract_style_brief_strips_code_fence():
    text = "```\nShort, direct sentences.\n```"
    assert scriptorium._extract_style_brief(text) == "Short, direct sentences."


def test_extract_style_brief_strips_surrounding_quotes():
    assert scriptorium._extract_style_brief('"A terse, formal register."') == \
        "A terse, formal register."


def test_extract_style_brief_caps_length():
    long_text = "x" * (scriptorium.MAX_STYLE_BRIEF_CHARS + 100)
    result = scriptorium._extract_style_brief(long_text)
    assert len(result) == scriptorium.MAX_STYLE_BRIEF_CHARS


def test_extract_style_brief_rejects_empty():
    with pytest.raises(scriptorium.BackendError):
        scriptorium._extract_style_brief("   ")


# --------------------------------------------------------------------------- #
#  _samples_from_text() / _samples_to_text() -- VoiceProfileDialog's parser
# --------------------------------------------------------------------------- #

def test_samples_round_trip():
    samples = ["First sample, one paragraph.", "Second sample here."]
    text = scriptorium._samples_to_text(samples)
    assert scriptorium._samples_from_text(text) == samples


def test_samples_from_text_drops_blank_entries():
    text = "First.\n---\n\n---\nSecond."
    assert scriptorium._samples_from_text(text) == ["First.", "Second."]


def test_samples_from_text_caps_count_and_length():
    samples = [f"sample {i}" for i in range(scriptorium.MAX_VOICE_SAMPLES + 3)]
    text = "\n---\n".join(samples)
    result = scriptorium._samples_from_text(text)
    assert len(result) == scriptorium.MAX_VOICE_SAMPLES

    long_text = "x" * (scriptorium.MAX_SAMPLE_CHARS + 50)
    result = scriptorium._samples_from_text(long_text)
    assert len(result[0]) == scriptorium.MAX_SAMPLE_CHARS


# --------------------------------------------------------------------------- #
#  derive_voice_brief() -- validation only; no live backend call is made
# --------------------------------------------------------------------------- #

def test_derive_voice_brief_rejects_no_samples():
    with pytest.raises(ValueError):
        scriptorium.derive_voice_brief([], {"backend": "anthropic"})


def test_derive_voice_brief_rejects_blank_only_samples():
    with pytest.raises(ValueError):
        scriptorium.derive_voice_brief(["   ", ""], {"backend": "anthropic"})
