#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.31 (E1, selection-scoped processing) live calibration harness.

Runs tests/calibration_corpus.py's fixed twelve cases through a real
backend, several times each, and classifies every run. This is the "model
behaviour" half of calibration (notes_025): meaning preservation cannot be
trusted from plausible prompt design alone (see the
mark_meaning_preservation_priority pattern -- confirmed real bugs at v2.4,
v2.11, v2.18 and, blocking shipment outright, v2.31 itself), so this must
be checked against real model output, not merely reasoned about.

Costs real time and money and its pass/fail determination is partially
subjective (a live model is not deterministic) -- this is deliberately NOT
part of the regression suite and never gates CI. See
test_calibration_e1_deterministic.py for the mechanical layer that does.

Reuses the exact pipeline _begin_processing()/_on_success() call, in the
same order, rather than re-implementing any prompt or splice logic:

    make_processing_scope -> mask_placeholders -> build_system_prompt ->
    run_backend -> restore_placeholders -> assemble_scoped_revision ->
    audit_revision_fidelity

scriptorium_config.json is only ever read, never written: this script
snapshots it into an isolated cfg dict, overrides "backend" from the
--backend flag, and asserts the file's own mtime is unchanged at the end
(the v2.18/v2.19 calibration discipline).

Usage:
    python tests/calibration_e1.py --backend claude --repeats 3
    python tests/calibration_e1.py --backend ollama
    python tests/calibration_e1.py --backend both --repeats 5

Every run's verbatim model output is written to
tests/results/calibration_e1_<backend>_<timestamp>.json and committed, so a
rerun produces a diff against real history instead of the 2026-09-07 run's
own scratch-only results having to be reconstructed from a write-up.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scriptorium  # noqa: E402 -- import must follow the sys.path fix-up above
from calibration_corpus import CASES, KNOWN_PROBLEM_CASES  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# User-facing --backend value -> the internal cfg["backend"] string
# run_backend() actually dispatches on.
BACKEND_CFG_VALUE = {"claude": "anthropic", "ollama": "ollama"}


# --------------------------------------------------------------------------- #
#  Isolated configuration -- read-only snapshot, backend overridden locally
# --------------------------------------------------------------------------- #

def _config_fingerprint(path):
    """A cheap, sufficient proof the file was not touched: its mtime, or
    None if it does not exist. Compared before/after the whole run."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def snapshot_config(backend_flag, ollama_model=None):
    """Return an isolated cfg dict derived from the real config file, with
    only "backend" (and, optionally, "ollama_model") overridden from CLI
    flags. load_config() already returns a fresh dict (never the module's
    own state), so mutating it here cannot touch the file on disk -- this
    script never calls save_config().

    ollama_model exists because the model actually configured in
    scriptorium_config.json is free-form and may not be the model this
    machine's calibration is meant to be judged against (confirmed usable,
    RAM-appropriate, etc. -- see scriptorium_testing_gotchas memory);
    --ollama-model lets a caller pin that explicitly without editing the
    live config.
    """
    cfg = scriptorium.load_config()
    cfg["backend"] = BACKEND_CFG_VALUE[backend_flag]
    if ollama_model and backend_flag == "ollama":
        cfg["ollama_model"] = ollama_model
    return cfg


# --------------------------------------------------------------------------- #
#  One case, one run, through the real pipeline
# --------------------------------------------------------------------------- #

def run_one_case(case, cfg):
    """Run exactly one corpus case once, in _begin_processing()/
    _on_success() order. Returns a plain, JSON-serialisable record with the
    verbatim model output and everything needed to classify the run.
    """
    record = {
        "case": case["name"], "category": case["category"],
        "mode": case["mode"], "strength": case["strength"],
        "role": case["role"], "tones": list(case["tones"]),
        "known_problem": case["known_problem"],
        "backend": cfg.get("backend"),
        "model": (cfg.get("anthropic_model") if cfg.get("backend") == "anthropic"
                  else cfg.get("ollama_model")),
    }

    scope = scriptorium.make_processing_scope(
        case["full_original"], selected=case["selected"],
        prefix=case["prefix"], suffix=case["suffix"])

    if cfg.get("protect_placeholders", True):
        masked, ph_map = scriptorium.mask_placeholders(scope["request_text"])
    else:
        masked, ph_map = scope["request_text"], []

    system_prompt = scriptorium.build_system_prompt(
        case["mode"], case["strength"], case["tones"], case["role"],
        protect_tokens=bool(ph_map),
        avoid_words=tuple(cfg.get("house_style_avoid", [])))

    try:
        result = scriptorium.run_backend(system_prompt, masked, cfg)
    except scriptorium.BackendError as exc:
        record["backend_error"] = str(exc)
        return record
    except Exception as exc:  # noqa: BLE001 -- one bad case must not kill the run
        record["backend_error"] = f"Unexpected error: {exc}"
        return record

    record["raw_model_output"] = dict(result)  # verbatim, before restoration

    if ph_map:
        revised_selection, placeholder_warnings = scriptorium.restore_placeholders(
            result["revised"], ph_map)
    else:
        revised_selection, placeholder_warnings = result["revised"], []

    assembled = scriptorium.assemble_scoped_revision(scope, revised_selection)
    fidelity_warnings = scriptorium.audit_revision_fidelity(
        case["full_original"], assembled)

    prefix, suffix = scope["prefix"], scope["suffix"]
    exterior_prefix_ok = assembled[:len(prefix)] == prefix
    exterior_suffix_ok = assembled[-len(suffix):] == suffix if suffix else True

    record.update({
        "revised_selection_text": revised_selection,
        "assembled_revision": assembled,
        "placeholder_warnings": placeholder_warnings,
        "fidelity_warnings": fidelity_warnings,
        "exterior_prefix_ok": exterior_prefix_ok,
        "exterior_suffix_ok": exterior_suffix_ok,
        "missing_protected_tokens": [
            token for token in case["protected_tokens"]
            if token not in assembled],
        "forbidden_hits": [
            phrase for phrase in case["forbidden_content"]
            if phrase in assembled],
    })
    return record


# --------------------------------------------------------------------------- #
#  Classification: PASS / DRIFT / FAIL / REVIEW
# --------------------------------------------------------------------------- #
# A live model's pass/fail is inherently partly subjective (notes_025's own
# framing) -- this is a best-effort automatic classifier over what can
# actually be checked mechanically, not a claim of full judgement. REVIEW
# always wins for an already-correct/genuinely-ambiguous case (per its own
# category, correctness there is a human call, not a heuristic one), FAIL
# is reserved for a mechanical break or a documented invented-content
# signature, and DRIFT covers every other fidelity concern.

def classify(case, record):
    if "backend_error" in record:
        return "FAIL"
    if not record["exterior_prefix_ok"] or not record["exterior_suffix_ok"]:
        return "FAIL"
    if record["forbidden_hits"]:
        return "FAIL"
    if case["already_correct"] or case["genuinely_ambiguous"]:
        return "REVIEW"
    if (record["fidelity_warnings"] or record["placeholder_warnings"]
            or record["missing_protected_tokens"]):
        return "DRIFT"
    return "PASS"


# --------------------------------------------------------------------------- #
#  Known-problem-case-specific recurrence checks (2026-09-07 recap)
# --------------------------------------------------------------------------- #

def _trailing_comma_recurred(case, record):
    """True if the model's own returned selection text no longer ends with
    the trailing comma the original selection ended with."""
    if "backend_error" in record:
        return None
    return not record["revised_selection_text"].rstrip().endswith(",")


def _smart_quote_recurred(case, record):
    if "backend_error" in record:
        return None
    text = record["revised_selection_text"]
    return any(phrase in text for phrase in case["forbidden_content"])


def _hallucination_recurred(case, record):
    if "backend_error" in record:
        return None
    text = record["revised_selection_text"]
    return any(phrase in text for phrase in case["forbidden_content"])


KNOWN_PROBLEM_CHECKS = {
    "mid_sentence_trailing_comma_known_drift": _trailing_comma_recurred,
    "quotation_straight_quotes_known_drift": _smart_quote_recurred,
    "markdown_list_item_short_imperative_known_hallucination":
        _hallucination_recurred,
}


# --------------------------------------------------------------------------- #
#  Driving a whole suite, reporting, and the committed results file
# --------------------------------------------------------------------------- #

def run_backend_suite(backend_flag, repeats, cases, ollama_model=None):
    cfg = snapshot_config(backend_flag, ollama_model=ollama_model)
    records = []
    for case in cases:
        for run_index in range(1, repeats + 1):
            record = run_one_case(case, cfg)
            record["run"] = run_index
            record["verdict"] = classify(case, record)
            records.append(record)
            print(f"  [{backend_flag}] {case['name']:<55} "
                  f"run {run_index}/{repeats}: {record['verdict']}")
    return records


def write_results_file(backend_flag, records):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = os.path.join(
        RESULTS_DIR, f"calibration_e1_{backend_flag}_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({
            "backend": backend_flag,
            "generated_at": timestamp,
            "app_version": scriptorium.APP_VERSION,
            "records": records,
        }, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to {path}")
    return path


def print_table(backend_flag, records):
    print(f"\n--- {backend_flag}: per-case x per-run verdicts ---")
    by_case = {}
    for rec in records:
        by_case.setdefault(rec["case"], []).append(rec)
    name_width = max((len(name) for name in by_case), default=0) + 2
    for name, runs in by_case.items():
        runs_sorted = sorted(runs, key=lambda r: r["run"])
        cells = "  ".join(f"run{r['run']}={r['verdict']}" for r in runs_sorted)
        print(f"  {name:<{name_width}} {cells}")


def _console_safe(text, limit=70):
    """A short, console-encoding-safe excerpt for the printed table.

    The committed JSON keeps the real UTF-8 text; this is display only --
    Windows console codepages can't render every character a small model
    emits (curly quotes, mangled sentinel brackets), and the exact-phrase
    KNOWN_PROBLEM_CHECKS below are necessarily narrow (they can only catch
    a literal repeat of 2026-09-07's specific wording, not a differently-
    worded recurrence of the same failure *mode*) -- printing the actual
    text lets a human catch what a narrow string match would miss.
    """
    excerpt = text[:limit] + ("..." if len(text) > limit else "")
    return excerpt.encode("ascii", "replace").decode("ascii")


def print_known_problem_verdicts(all_results):
    print("\n=== Known-problem case verdicts (2026-09-07 Ollama run recap) ===")
    for case in KNOWN_PROBLEM_CASES:
        print(f"\n{case['name']}")
        print(f"  category: {case['category']}")
        print(f"  originally: {case['known_problem']}")
        check = KNOWN_PROBLEM_CHECKS.get(case["name"])
        for backend_flag, records in all_results.items():
            case_records = [r for r in records if r["case"] == case["name"]]
            verdicts = [r["verdict"] for r in case_records]
            print(f"  {backend_flag}: verdicts={verdicts}")
            for rec in case_records:
                exact_match = check(case, rec) if check is not None else None
                text = rec.get("revised_selection_text")
                excerpt = _console_safe(text) if text is not None else \
                    f"(backend_error: {rec.get('backend_error')})"
                print(f"    run {rec['run']}: exact_repeat_of_2026-09-07="
                      f"{exact_match!r}  output={excerpt!r}")


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tests/calibration_e1.py",
        description="v2.31 (E1) live calibration harness -- costs real "
                    "time/money, never part of CI.")
    parser.add_argument("--backend", choices=("claude", "ollama", "both"),
                        default="both")
    parser.add_argument("--repeats", type=int, default=3,
                        help="Times to run every case (default 3 -- a "
                             "probabilistic system cannot be judged on one "
                             "run).")
    parser.add_argument("--ollama-model", default=None,
                        help="Override cfg['ollama_model'] for this run only "
                             "(the live scriptorium_config.json is never "
                             "written). Ignored for --backend claude.")
    args = parser.parse_args(argv)

    if args.repeats < 1:
        print("error: --repeats must be at least 1", file=sys.stderr)
        return 1

    if getattr(scriptorium.load_config, "unreadable", False):
        print(
            "error: scriptorium_config.json could not be read; refusing to "
            "calibrate against silently-defaulted settings.", file=sys.stderr)
        return 1

    before_fingerprint = _config_fingerprint(scriptorium.CONFIG_PATH)

    backends = (["claude", "ollama"] if args.backend == "both"
                else [args.backend])

    all_results = {}
    for backend_flag in backends:
        print(f"\n=== Running {len(CASES)} case(s) x {args.repeats} "
              f"repeat(s) against {backend_flag} ===")
        records = run_backend_suite(
            backend_flag, args.repeats, CASES, ollama_model=args.ollama_model)
        all_results[backend_flag] = records
        write_results_file(backend_flag, records)
        print_table(backend_flag, records)

    print_known_problem_verdicts(all_results)

    after_fingerprint = _config_fingerprint(scriptorium.CONFIG_PATH)
    assert before_fingerprint == after_fingerprint, (
        "scriptorium_config.json changed during this run -- this harness "
        "must never write to it.")
    print("\nscriptorium_config.json untouched (mtime unchanged).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
