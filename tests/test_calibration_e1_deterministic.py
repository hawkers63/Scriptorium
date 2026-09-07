"""Mechanical (no live model) regression tests for v2.31's calibration corpus.

Drives every case in calibration_corpus.py through the real
make_processing_scope()/assemble_scoped_revision() -- deterministic and
network-free -- and asserts the guarantees the splice mechanism exists to
provide: every byte outside the selection survives unchanged, boundary
whitespace is never duplicated or dropped, protected tokens travel through
placeholder masking intact, and make_processing_scope() rejects a
mismatched or whitespace-only selection.

One test additionally pins the tail of the sequence a live harness must
replay by hand (restore_placeholders -> assemble_scoped_revision) to what a
real Scriptorium._on_success() does with an identical stubbed backend
response, for the same reason notes_025 calls out: a harness that replays
this sequence instead of calling one shared function could quietly drift
from the real thing.

No network access, no live model -- part of the regular regression suite.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scriptorium  # noqa: E402 -- import must follow the sys.path fix-up above

from calibration_corpus import CASES, CASES_BY_NAME  # noqa: E402


def _scope_for(case):
    return scriptorium.make_processing_scope(
        case["full_original"], selected=case["selected"],
        prefix=case["prefix"], suffix=case["suffix"])


# --------------------------------------------------------------------------- #
#  Corpus x make_processing_scope()/assemble_scoped_revision()
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_scope_reconstructs_full_original(case):
    scope = _scope_for(case)
    assert scope["kind"] == "selection"
    assert scope["request_text"] == case["selected"]
    assert scope["prefix"] + scope["request_text"] + scope["suffix"] == \
        case["full_original"]
    assert scope["full_original"] == case["full_original"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_assemble_scoped_revision_round_trips_unchanged_selection(case):
    """Feeding the selection back verbatim must reproduce the original
    exactly -- the baseline every real model response is judged against."""
    scope = _scope_for(case)
    assembled = scriptorium.assemble_scoped_revision(scope, case["selected"])
    assert assembled == case["full_original"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_assemble_scoped_revision_exterior_bytes_untouched(case):
    """Whatever a 'model' returns, prefix/suffix in the assembled text stay
    byte-identical to what was captured locally -- never sent, never
    touched, regardless of what comes back for the selection."""
    scope = _scope_for(case)
    stubbed_revision = f">>> STUBBED MODEL OUTPUT for {case['name']} <<<"
    assembled = scriptorium.assemble_scoped_revision(scope, stubbed_revision)

    prefix, suffix = scope["prefix"], scope["suffix"]
    assert assembled[:len(prefix)] == prefix
    if suffix:
        assert assembled[-len(suffix):] == suffix
        interior = assembled[len(prefix):-len(suffix)]
    else:
        interior = assembled[len(prefix):]
    assert interior == stubbed_revision


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_assemble_scoped_revision_boundary_whitespace_is_clean(case):
    """assemble_scoped_revision() must be pure concatenation -- no implicit
    strip()/normalise step that could silently absorb or duplicate
    whitespace at the splice point. (A regex being too permissive at a
    boundary is exactly the bug class scriptorium_testing_gotchas memory
    #16 found for the fidelity audit's Windows-path pattern; this guards
    the splice function itself against the same class of mistake.)"""
    scope = _scope_for(case)
    padded_stub = "  " + case["selected"] + "  "  # deliberately pad both edges
    assembled = scriptorium.assemble_scoped_revision(scope, padded_stub)
    # Exact concatenation, nothing added or removed anywhere else.
    assert assembled == scope["prefix"] + padded_stub + scope["suffix"]


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["protected_tokens"]],
    ids=[c["name"] for c in CASES if c["protected_tokens"]])
def test_protected_tokens_survive_a_faithful_stub(case):
    """A stub that echoes the selection back unchanged must still carry
    every protected token through assembly -- sanity-checks the corpus data
    itself; a live-model failure to preserve one of these for real is
    exactly what calibration_e1.py checks against a real backend."""
    scope = _scope_for(case)
    assembled = scriptorium.assemble_scoped_revision(scope, case["selected"])
    for token in case["protected_tokens"]:
        assert token in assembled


def test_make_processing_scope_full_document_kind():
    """A full-document request (no selection) behaves exactly as it did
    before selection-scoped processing existed."""
    text = "Two sentences. Both are sent to the model whole."
    scope = scriptorium.make_processing_scope(text)
    assert scope["kind"] == "full"
    assert scope["request_text"] == text
    assert scope["prefix"] == ""
    assert scope["suffix"] == ""
    assert scriptorium.assemble_scoped_revision(scope, "REPLACED") == "REPLACED"


def test_make_processing_scope_rejects_mismatched_selection():
    case = CASES_BY_NAME["mid_sentence_leading_punctuation"]
    with pytest.raises(ValueError, match="no longer matches Original"):
        scriptorium.make_processing_scope(
            case["full_original"], selected=case["selected"] + " ",
            prefix=case["prefix"], suffix=case["suffix"])


def test_make_processing_scope_rejects_whitespace_only_selection():
    prefix, selected, suffix = "Prefix text.", "   ", " Suffix text."
    full = prefix + selected + suffix
    with pytest.raises(ValueError, match="containing text"):
        scriptorium.make_processing_scope(
            full, selected=selected, prefix=prefix, suffix=suffix)


def test_make_processing_scope_rejects_non_string_input():
    with pytest.raises(TypeError):
        scriptorium.make_processing_scope(
            "abc", selected=123, prefix="", suffix="abc")


# --------------------------------------------------------------------------- #
#  Placeholder masking through the same scope/assembly pipeline
# --------------------------------------------------------------------------- #

def test_placeholder_mask_restore_round_trip_for_all_four_shapes():
    case = CASES_BY_NAME["windows_path_and_all_placeholder_shapes"]
    scope = _scope_for(case)

    masked, ph_map = scriptorium.mask_placeholders(scope["request_text"])
    assert len(ph_map) == 4  # {{Date}}, [Name], {amount}, <Date>
    for shape in ("{{Date}}", "[Name]", "{amount}", "<Date>"):
        assert shape not in masked
    assert "C:\\Users\\Reports\\Q1.docx" in masked  # not a placeholder shape

    restored, warnings = scriptorium.restore_placeholders(masked, ph_map)
    assert warnings == []
    assert restored == scope["request_text"]

    assembled = scriptorium.assemble_scoped_revision(scope, restored)
    assert assembled == case["full_original"]
    for token in case["protected_tokens"]:
        assert token in assembled


def test_restore_placeholders_warns_on_a_dropped_sentinel():
    case = CASES_BY_NAME["windows_path_and_all_placeholder_shapes"]
    scope = _scope_for(case)
    masked, ph_map = scriptorium.mask_placeholders(scope["request_text"])

    damaged = masked.replace(ph_map[0][0], "", 1)  # simulate a dropped token
    restored, warnings = scriptorium.restore_placeholders(damaged, ph_map)
    assert len(warnings) == 1
    assert ph_map[0][1] in warnings[0]


# --------------------------------------------------------------------------- #
#  Harness/GUI drift guard -- pin a hand-replayed sequence to a real
#  _on_success() result for a fixed stubbed response.
# --------------------------------------------------------------------------- #

def _build_isolated_app(tmp_path, monkeypatch):
    """Construct a real Scriptorium() against an isolated config file.

    Never touches the real scriptorium_config.json (this project's standing
    testing rule: always patch CONFIG_PATH, never test against the live
    one -- see project_v24_status/scriptorium_testing_gotchas memory).
    backend="ollama" avoids _maybe_show_privacy_notice()'s blocking
    messagebox for a config with no privacy_ack (gotcha #14) -- nothing in
    this test calls a live backend either way.
    """
    cfg_path = tmp_path / "scriptorium_config.json"
    cfg_path.write_text(json.dumps({
        "backend": "ollama",
        "default_mode": "Correct",
        "default_strength": "Standard",
        "default_role": "(none)",
        "default_tones": [],
        "protect_placeholders": True,
        "check_letter_conventions": True,
    }), encoding="utf-8")
    monkeypatch.setattr(scriptorium, "CONFIG_PATH", str(cfg_path))
    return scriptorium.Scriptorium()


def test_harness_replica_matches_a_real_on_success(tmp_path, monkeypatch):
    """The exact drift risk notes_025 flags: a harness that replays
    restore_placeholders() -> assemble_scoped_revision() by hand, instead of
    calling one shared function, could quietly diverge from what
    _on_success() actually does with an identical stubbed backend response.
    Pin the two together so any future change to either path breaks this
    test rather than silently disagreeing at calibration time.

    Only one Scriptorium() instance is constructed in this whole file,
    never alongside another -- CustomTkinter's global appearance-mode/DPI
    state interferes across multiple live instances in one process
    (scriptorium_testing_gotchas memory gotcha #1).
    """
    case = CASES_BY_NAME["windows_path_and_all_placeholder_shapes"]
    scope = _scope_for(case)

    app = _build_isolated_app(tmp_path, monkeypatch)
    try:
        app.original_box.delete("1.0", "end")
        app.original_box.insert("1.0", case["full_original"])

        if app.cfg.get("protect_placeholders", True):
            masked, ph_map = scriptorium.mask_placeholders(scope["request_text"])
        else:
            masked, ph_map = scope["request_text"], []

        request_context = scriptorium.build_request_context(
            case["mode"], case["strength"], case["role"], case["tones"],
            app.cfg, scope=scope["kind"])

        # A fixed stubbed backend response: echoes the masked text back
        # unchanged (i.e. "nothing needed changing").
        gui_result = {"revised": masked, "ambiguities": [], "note": ""}
        app._on_success(
            app._request_id, scope, ph_map, gui_result, request_context)
        gui_revised = app.last_result["revised"]

        # The harness's own hand-replica of the sequence's tail, from a
        # fresh copy of the SAME stubbed response and the SAME ph_map/scope
        # -- never by calling mask_placeholders() a second time, since it
        # mints a fresh random nonce on every call and a second call's
        # sentinels would not match ph_map at all.
        harness_result = {"revised": masked, "ambiguities": [], "note": ""}
        restored, _warnings = scriptorium.restore_placeholders(
            harness_result["revised"], ph_map)
        harness_revised = scriptorium.assemble_scoped_revision(scope, restored)

        assert harness_revised == gui_revised
        assert harness_revised == case["full_original"]
    finally:
        app.destroy()
