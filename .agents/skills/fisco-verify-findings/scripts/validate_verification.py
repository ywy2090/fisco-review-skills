#!/usr/bin/env python3
"""Deterministic structural gates for fisco-verify-findings artifacts.

The point of these gates is that a verdict nobody can re-run is an opinion, not
a verification. So the checker does not judge whether a conclusion is *right*;
it judges whether the artifact actually carries the evidence it claims to, and
whether each verdict's obligation was met:

  * every ``git show <rev>:<path>[:<lines>]`` citation — in item evidence,
    sub-claim evidence, reachability evidence, resolution evidence and
    historical evidence — resolves to a frozen revision, an existing blob and a
    line range inside it. This is the repo's number-one review failure: line
    numbers that drifted off the revision;
  * the artifact's ``pin.head``/``pin.base`` really exist in ``--repo``, so a
    fabricated pin cannot silently pass every citation check;
  * CONFIRMED / REFUTED / STALE / UNREPRODUCIBLE each satisfy their own
    evidence obligation, and an item whose stated mechanism was refuted can no
    longer be reported as plain CONFIRMED;
  * a repro that mutates the code under test must be a labelled, restored
    mutation probe rather than an unrecorded edit.

These gates check that evidence is *present and pointed at the right revision*.
They cannot check that a quoted line says what the author says it says, nor that
a pasted log came from the command beside it — a human or a downstream handler
still has to spot-check content. Pass `--repo` to activate every revision-path
gate; without it the artifact is only shape-checked.

Usage:
    python3 validate_verification.py <artifact.json> [--repo <git-repo>] [--json]
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


SCHEMA_VERSION = 1

VERDICTS = {
    "confirmed",
    "confirmed_symptom_mechanism_differs",
    "refuted",
    "stale",
    "unreproducible",
    "undecidable",
}
SUB_CLAIMS = ("location", "mechanism", "impact", "premise")
SUB_VERDICTS = {"confirmed", "refuted", "undecidable", "not_claimed"}
RECOMMENDATIONS = {"fix", "reject_with_reason", "defer", "needs_human", "hardening"}
SOURCES = {
    "pr_comment",
    "review_artifact",
    "review_handoff",
    "self_review",
    "issue_comment",
    "report_md",
    "advisory",
}
TIERS = {"static", "unit_test", "integration"}
CLAIM_KINDS = {"structural", "behavioural"}
PIN_PLACEHOLDERS = {"$PIN", "$REVIEW_PIN", "$VERIFY_PIN", "$HEAD_OID", "<pin>", "<PIN>"}
BASE_PLACEHOLDERS = {"$VERIFY_BASE_PIN", "$BASE_OID", "$REVIEW_BASE_PIN", "<base>"}
HEX = re.compile(r"^[0-9a-f]{40}$")
SHORT_HEX = re.compile(r"^[0-9a-f]{7,39}$")
PIN_RELATED_KEYS = (
    "id",
    "source_ref",
    "claim_verbatim",
    "verdict",
    "evidence",
    "reachability",
    "repro",
    "falsification_attempts",
    "boundary",
    "residual_risk",
    "recommendation",
)
CITATION = re.compile(r"git\s+show\s+([^\s:]+):(\S+)")
SNIPPET = re.compile(r"`([^`]{8,})`")
SHELL_LIKE = re.compile(r"(^|\s)(git|cmake|ctest|bash|sh|ninja|find|rg|grep|nm|objdump|python3?|\./)\b")


def normalized(text):
    return re.sub(r"\s+", "", text or "")


def is_oid(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value):
    return isinstance(value, list) and any(nonempty_text(x) for x in value)


def nonempty_objects(value):
    return isinstance(value, list) and any(
        isinstance(x, dict) and any(v for v in x.values()) for x in value
    )


def require_keys(value, keys, where, errors):
    if not isinstance(value, dict):
        errors.append(f"{where}: expected object")
        return False
    for key in keys:
        if key not in value:
            errors.append(f"{where}: missing {key}")
    return True


class PinChecker:
    """Resolves git citations against the artifact's frozen revisions."""

    def __init__(self, repo, pin_head, pin_base):
        self.repo = repo
        self.pin_head = pin_head
        self.pin_base = pin_base
        self._cache = {}
        self.accepted = {rev: label for rev, label in ((pin_head, "head"), (pin_base, "base")) if is_oid(rev)}

    def _git(self, *args):
        key = args
        if key not in self._cache:
            self._cache[key] = subprocess.run(
                ["git", "-C", self.repo, *args], capture_output=True, text=True, check=False
            )
        return self._cache[key]

    def commit_exists(self, rev):
        if self.repo is None or not rev:
            return None
        return self._git("cat-file", "-e", f"{rev}^{{commit}}").returncode == 0

    def resolve_rev(self, rev, where, errors):
        """Map a citation revision onto an accepted frozen ref, or reject it."""
        if rev in PIN_PLACEHOLDERS:
            return self.pin_head
        if rev in BASE_PLACEHOLDERS:
            return self.pin_base
        if rev in self.accepted:
            return rev
        if SHORT_HEX.fullmatch(rev) and any(
            is_oid(accepted) and accepted.startswith(rev) for accepted in self.accepted
        ):
            # A prefix is only acceptable when it resolves unambiguously to one of
            # this artifact's frozen revisions; git's own disambiguation can
            # otherwise read a different commit than the artifact claims.
            if self.repo is None:
                return rev
            result = self._git("rev-parse", "--verify", f"{rev}^{{commit}}")
            if "ambiguous" in (result.stderr or ""):
                errors.append(
                    f"{where}: citation revision {rev!r} resolves ambiguously — name the "
                    "full 40-character OID"
                )
                return None
            if result.returncode == 0 and result.stdout.strip() in self.accepted:
                return rev
        return self._pin_mismatch(rev, where, errors)

    def _pin_mismatch(self, rev, where, errors):
        known = ", ".join(sorted(self.accepted.values())) or "the pin"
        errors.append(
            f"{where}: citation revision {rev!r} is neither the pinned head "
            f"{self._short(self.pin_head)} nor the pinned base — evidence must be read at "
            f"a frozen revision of this artifact ({known}), not at a mutable branch or a "
            "foreign commit"
        )
        return None

    @staticmethod
    def _short(oid):
        return oid[:12] if isinstance(oid, str) else oid

    def blob_at(self, rev, path):
        key = ("type", rev, path)
        if key not in self._cache:
            result = self._git("cat-file", "-t", f"{rev}:{path}")
            self._cache[key] = result.stdout.strip() if result.returncode == 0 else None
        return self._cache[key]

    def line_count(self, rev, path):
        key = ("lines", rev, path)
        if key not in self._cache:
            result = self._git("show", f"{rev}:{path}")
            self._cache[key] = None if result.returncode else len(result.stdout.splitlines())
        return self._cache[key]

    def text_at(self, rev, path):
        key = ("text", rev, path)
        if key not in self._cache:
            result = self._git("show", f"{rev}:{path}")
            self._cache[key] = None if result.returncode else result.stdout
        return self._cache[key]


def check_quoted_snippets(entries, where, errors, pins):
    """Gate: backticked code in an evidence entry must exist at the cited revision.

    A citation proves *where* the author looked; it does not prove that the line
    beside it says what they say it says. When an entry quotes code in backticks
    and cites a location, the quote has to be findable there (compared with
    whitespace removed, so a quote that spans two source lines still matches).
    Shell commands and variable interpolations are skipped — those are steps,
    not quoted source.
    """
    for index, entry in enumerate(entries if isinstance(entries, list) else []):
        if not isinstance(entry, str):
            continue
        snippets = [
            snippet for snippet in SNIPPET.findall(entry)
            if not SHELL_LIKE.search(snippet) and not re.search(r"\$[A-Z_]+|\$\{", snippet)
        ]
        if not snippets:
            continue
        citations = parse_citations(entry)
        if not citations or pins.repo is None:
            continue
        rev, path, start, end = citations[0]
        if rev in PIN_PLACEHOLDERS:
            rev = pins.pin_head
        elif rev in BASE_PLACEHOLDERS:
            rev = pins.pin_base
        text = pins.text_at(rev, path)
        if text is None:
            continue  # the path/rev gate already reported this
        if start is not None:
            lines = text.splitlines()
            if end > len(lines):
                continue  # the line-range gate already reported this
            text = "\n".join(lines[start - 1 : end])
        haystack = normalized(text)
        if not any(normalized(snippet) in haystack for snippet in snippets):
            errors.append(
                f"{where}[{index}]: none of the quoted snippets appears at "
                f"{path}:{start or 'file'}@{pins._short(rev)} — the quote must be the code "
                "actually read there, not a plausible reconstruction"
            )


def parse_citations(text):
    """Return every (rev, path, start, end) `git show` citation in a string."""
    if not isinstance(text, str):
        return []
    found = []
    for match in CITATION.finditer(text):
        rev, rest = match.group(1), match.group(2)
        start = end = None
        tail = re.search(r":(\d+)(?:-(\d+))?$", rest)
        if tail:
            path = rest[: tail.start()]
            start = int(tail.group(1))
            end = int(tail.group(2)) if tail.group(2) else start
        else:
            path = rest
        if not path or "*" in path or path.startswith("/") or ".." in path.split("/"):
            continue
        found.append((rev, path, start, end))
    return found


def locator_is_readable(entry):
    """A non-`git show` evidence entry must say where the fact is read from."""
    if not isinstance(entry, str):
        return False
    patterns = (
        r"git grep",
        r"git log",
        r"git rev-parse",
        r"git merge-base",
        r"git cat-file",
        r"ctest\b",
        r"--run_test",
        r"--gtest",
        r"boost",
        r"\btest\b",
        r"\bbuild\b",
        r"\brun\b",
        r"\bline \d+",
        r"\d+:\d+",
        r"https?://",
        r"\bissue #?\d+",
        r"\bcomment \d+",
        r"\bpath\b",
    )
    return any(re.search(pattern, entry, re.I) for pattern in patterns)


def check_citations(entries, where, errors, pins, require_one=False):
    """Gate: every citation in the given evidence entries resolves."""
    checked = 0
    for index, entry in enumerate(entries if isinstance(entries, list) else []):
        citations = parse_citations(entry)
        if not citations:
            if not locator_is_readable(entry):
                errors.append(
                    f"{where}[{index}]: expected either a `git show <pin>:<path>` citation or "
                    "a locator saying where the fact is read from"
                )
            continue
        for rev, path, start, end in citations:
            checked += 1
            resolved = pins.resolve_rev(rev, f"{where}[{index}]", errors)
            if resolved is None or pins.repo is None:
                continue
            kind = pins.blob_at(resolved, path)
            if kind is None:
                errors.append(
                    f"{where}[{index}]: path {path!r} does not exist at {rev} "
                    "— stale or mistyped locator"
                )
                continue
            if kind != "blob":
                errors.append(
                    f"{where}[{index}]: {path!r} is a {kind} at {rev}, not a file "
                    "— line ranges need a blob"
                )
                continue
            if start is None:
                continue
            total = pins.line_count(resolved, path)
            if total is not None and (start < 1 or end > total or end < start):
                errors.append(
                    f"{where}[{index}]: line range {start}-{end} is outside {path!r} at "
                    f"{rev} (file has {total} lines)"
                )
    if require_one and checked == 0:
        errors.append(
            f"{where}: needs at least one `git show <pin>:<path>` citation — a bare claim "
            "is not resolution evidence"
        )
    return checked


def check_subclaims(item, where, errors, pins):
    """Gate: a refuted sub-claim must not be followed by a plain CONFIRMED verdict."""
    subclaims = item.get("subclaims")
    if not isinstance(subclaims, dict):
        errors.append(f"{where}.subclaims: expected object with per-sub-claim verdicts")
        return
    for name in SUB_CLAIMS:
        claim = subclaims.get(name)
        if claim is None:
            errors.append(f"{where}.subclaims.{name}: missing (use null only with a reason)")
            continue
        if not isinstance(claim, dict):
            errors.append(
                f"{where}.subclaims.{name}: expected an object "
                '{"text": ..., "verdict": ..., "evidence": [...]}'
            )
            continue
        verdict = claim.get("verdict")
        if verdict not in SUB_VERDICTS:
            errors.append(f"{where}.subclaims.{name}: unknown verdict {verdict!r}")
            continue
        if verdict == "not_claimed" and not nonempty_text(claim.get("note")):
            errors.append(
                f"{where}.subclaims.{name}: not_claimed requires a note saying the "
                "finding never made this claim"
            )
        if verdict != "not_claimed":
            entries = claim.get("evidence")
            if not nonempty_list(entries):
                errors.append(f"{where}.subclaims.{name}: verdict {verdict} needs evidence")
            else:
                check_citations(entries, f"{where}.subclaims.{name}.evidence", errors, pins)
                check_quoted_snippets(entries, f"{where}.subclaims.{name}.evidence", errors, pins)

    verdict = item.get("verdict")
    refuted = [
        name for name in SUB_CLAIMS
        if isinstance(subclaims.get(name), dict)
        and subclaims[name].get("verdict") == "refuted"
    ]
    if refuted and verdict == "confirmed":
        errors.append(
            f"{where}: verdict=confirmed but sub-claims {refuted} were refuted — "
            "use confirmed_symptom_mechanism_differs or refuted"
        )
    if verdict == "confirmed" and isinstance(subclaims.get("premise"), dict):
        if subclaims["premise"].get("verdict") == "undecidable":
            errors.append(
                f"{where}: verdict=confirmed with an undecidable premise — the finding "
                "as stated is not established; degrade to undecidable, or record "
                'premise={"verdict": "not_claimed"} with a note if the finding never '
                "rested on external behaviour"
            )
    if verdict == "stale" and isinstance(subclaims.get("mechanism"), dict):
        if subclaims["mechanism"].get("verdict") == "confirmed":
            errors.append(
                f"{where}.subclaims.mechanism: confirmed at the pin with verdict=stale — "
                "sub-claims are judged at the pin, where the repair already landed; the "
                "pre-fix state belongs in historical_evidence"
            )


def check_repro(item, where, errors, pins):
    repro = item.get("repro")
    verdict = item.get("verdict")
    if repro is None:
        if verdict in {"confirmed", "confirmed_symptom_mechanism_differs", "refuted"}:
            errors.append(
                f"{where}: verdict={verdict} requires a repro (command, expected, "
                "observed) — code reading yields a hypothesis, not a verification"
            )
        return
    if not isinstance(repro, dict):
        errors.append(f"{where}.repro: expected object or null")
        return
    require_keys(
        repro,
        ("tier", "claim_kind", "command", "expected", "observed"),
        f"{where}.repro",
        errors,
    )
    if repro.get("tier") not in TIERS:
        errors.append(f"{where}.repro: unknown tier {repro.get('tier')!r}")
    claim_kind = repro.get("claim_kind")
    if claim_kind not in CLAIM_KINDS:
        errors.append(
            f"{where}.repro.claim_kind: must be 'structural' or 'behavioural' — it is what "
            "decides whether a build is needed at all"
        )
    elif claim_kind == "behavioural" and repro.get("tier") == "static":
        errors.append(
            f"{where}.repro: a behavioural claim cannot be settled by static reading "
            "(tier=static) — run the behaviour, or reclassify and say why"
        )
    for key in ("command", "observed"):
        if not nonempty_text(repro.get(key)):
            errors.append(f"{where}.repro.{key}: must be non-empty")
    if not isinstance(repro.get("expected"), (str, list)) or not repro.get("expected"):
        errors.append(f"{where}.repro.expected: must state what the claimed behaviour predicts")
    if "exit_code" not in repro:
        errors.append(
            f"{where}.repro.exit_code: record the exit code (use null only for a static check)"
        )
    elif repro["exit_code"] is not None and not isinstance(repro["exit_code"], int):
        errors.append(f"{where}.repro.exit_code: must be an integer or null")
    if repro.get("modifies_production_code") not in (True, False):
        errors.append(
            f"{where}.repro.modifies_production_code: must be an explicit boolean "
            "(a repro that edits the code under test is a mutation probe)"
        )
    elif repro["modifies_production_code"]:
        if item.get("mutation_probe") is None:
            errors.append(
                f"{where}: repro edits production code but no mutation_probe is recorded"
            )
        if not nonempty_text(repro.get("worktree")):
            errors.append(
                f"{where}.repro.worktree: an edit-based repro must name the isolated "
                "worktree it ran in"
            )


def check_falsification(item, where, errors):
    verdict = item.get("verdict")
    attempts = item.get("falsification_attempts")
    if verdict in {"unreproducible", "refuted"} and not nonempty_objects(attempts):
        errors.append(
            f"{where}: verdict={verdict} requires falsification_attempts — record what "
            "you tried and what happened, so a third party can tell 'not true' from "
            "'I could not make it fire'"
        )
    if not isinstance(attempts, list):
        return
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            errors.append(f"{where}.falsification_attempts[{index}]: expected object")
            continue
        require_keys(attempt, ("attempt", "result"), f"{where}.falsification_attempts[{index}]", errors)
        if not nonempty_text(attempt.get("result")):
            errors.append(f"{where}.falsification_attempts[{index}].result: must be non-empty")


def check_mutation_probe(item, where, errors):
    probe = item.get("mutation_probe")
    if probe is None:
        return
    if not isinstance(probe, dict):
        errors.append(f"{where}.mutation_probe: expected object or null")
        return
    require_keys(
        probe,
        ("file", "diff", "symptom_disappeared", "restored", "post_restore_diff_empty"),
        f"{where}.mutation_probe",
        errors,
    )
    if not nonempty_text(probe.get("file")):
        errors.append(f"{where}.mutation_probe.file: must name the file the probe edited")
    if not nonempty_text(probe.get("diff")):
        errors.append(f"{where}.mutation_probe.diff: keep the probe diff in the report")
    if probe.get("symptom_disappeared") not in (True, False):
        errors.append(f"{where}.mutation_probe.symptom_disappeared: must be a boolean")
    if probe.get("restored") is not True or probe.get("post_restore_diff_empty") is not True:
        errors.append(
            f"{where}.mutation_probe: the probe must be restored and the tree must be "
            "clean afterwards (restored=true, post_restore_diff_empty=true)"
        )


def check_reachability(item, where, errors, pins):
    reachability = item.get("reachability")
    if not isinstance(reachability, dict):
        errors.append(f"{where}.reachability: expected object")
        return
    if reachability.get("on_live_path") not in (True, False):
        errors.append(f"{where}.reachability.on_live_path: must be an explicit boolean")
    if not nonempty_text(reachability.get("scope_note")):
        errors.append(
            f"{where}.reachability.scope_note: state whether the defect is on a live "
            "production path, wired-only-for-tests, or dead — and what that implies"
        )
    if reachability.get("on_live_path") is True:
        entries = reachability.get("evidence")
        if not nonempty_list(entries):
            errors.append(
                f"{where}.reachability.evidence: on_live_path=true needs caller evidence "
                "(e.g. a `git grep` result at the pin)"
            )
        else:
            check_citations(entries, f"{where}.reachability.evidence", errors, pins)
            check_quoted_snippets(entries, f"{where}.reachability.evidence", errors, pins)


def check_verdict_obligations(item, where, errors, pins):
    verdict = item.get("verdict")
    recommendation = item.get("recommendation")
    if recommendation not in RECOMMENDATIONS:
        errors.append(f"{where}.recommendation: unknown value {recommendation!r}")
    elif verdict in {"unreproducible", "refuted", "stale", "undecidable"} and recommendation == "fix":
        errors.append(
            f"{where}: verdict={verdict} cannot recommend fix — an unshown, refuted or "
            "already-repaired finding is a hardening item (recommendation=hardening), a "
            "reply, or a human decision"
        )
    if verdict == "stale":
        fixed_at = item.get("fixed_at")
        if not is_oid(fixed_at):
            errors.append(f"{where}.fixed_at: stale requires the repair commit as a 40-hex OID")
        elif pins.repo is not None:
            if pins.commit_exists(fixed_at) is False:
                errors.append(f"{where}.fixed_at: {fixed_at[:12]} is not a commit in --repo")
            elif is_oid(pins.pin_head) and pins.commit_exists(pins.pin_head):
                ancestor = pins._git("merge-base", "--is-ancestor", fixed_at, pins.pin_head)
                if ancestor.returncode != 0:
                    errors.append(
                        f"{where}.fixed_at: {fixed_at[:12]} is not an ancestor of the pinned "
                        "head — a repair that is not in the pin's history did not repair the pin"
                    )
        resolution = item.get("resolution_evidence")
        if not nonempty_list(resolution):
            errors.append(
                f"{where}.resolution_evidence: stale requires positive evidence that the "
                "repair is present at the pin (not merely that the line moved)"
            )
        else:
            check_citations(
                resolution, f"{where}.resolution_evidence", errors, pins, require_one=True
            )
            check_quoted_snippets(resolution, f"{where}.resolution_evidence", errors, pins)
    if verdict == "undecidable" and not nonempty_list(item.get("missing_inputs")):
        errors.append(
            f"{where}.missing_inputs: undecidable must name the missing input that would settle it"
        )
    if verdict == "confirmed_symptom_mechanism_differs":
        if not nonempty_list(item.get("mechanism_correction")):
            errors.append(
                f"{where}.mechanism_correction: say what the real mechanism is — the "
                "reviewer's stated cause is what the next round re-reads"
            )
    if not nonempty_text(item.get("boundary")):
        errors.append(
            f"{where}.boundary: state what the reproduction does NOT cover (platform, "
            "build type, config flags, consensus mode, fixture corpus)"
        )
    if not nonempty_text(item.get("residual_risk")):
        errors.append(f"{where}.residual_risk: state the uncertainty that remains")


def check_historical_citations(item, where, errors, pins):
    """`stale` may cite the pre-fix revision; nothing else may leave the pin."""
    entries = item.get("historical_evidence", [])
    verdict = item.get("verdict")
    if entries and verdict != "stale":
        errors.append(
            f"{where}.historical_evidence: only verdict=stale may cite a revision other "
            "than the pin — other verdicts must show the symptom at the pin itself"
        )
    if verdict == "stale" and not nonempty_list(entries):
        errors.append(
            f"{where}.historical_evidence: stale must show the defect *was* there at an "
            "earlier revision (cite it); 'the line moved' alone is not staleness"
        )
    if not isinstance(entries, list):
        return
    check_quoted_snippets(entries, f"{where}.historical_evidence", errors, pins)
    for index, entry in enumerate(entries):
        citations = parse_citations(entry)
        if not citations:
            if not locator_is_readable(entry):
                errors.append(
                    f"{where}.historical_evidence[{index}]: expected a `git show <rev>:<path>` "
                    "citation or a located fact"
                )
            continue
        for rev, path, _start, _end in citations:
            if rev in PIN_PLACEHOLDERS or (is_oid(pins.pin_head) and rev == pins.pin_head):
                errors.append(
                    f"{where}.historical_evidence[{index}]: cites the pin itself as the "
                    "pre-fix revision — the pre-fix state must be read before the repair"
                )
                continue
            if pins.repo is None:
                continue
            if pins.commit_exists(rev) is False:
                errors.append(
                    f"{where}.historical_evidence[{index}]: revision {rev!r} does not resolve "
                    "in --repo — the pre-fix citation must itself be checkable"
                )
                continue
            if pins.blob_at(rev, path) is None:
                errors.append(
                    f"{where}.historical_evidence[{index}]: path {path!r} does not exist at "
                    f"{rev}"
                )
                continue
            fixed_at = item.get("fixed_at")
            if is_oid(fixed_at) and pins.commit_exists(fixed_at) is not False:
                if pins._git("merge-base", "--is-ancestor", rev, fixed_at).returncode != 0:
                    # A rebased or force-pushed branch can make the pre-fix revision
                    # unreachable from the repair; that is legitimate but must not be
                    # silent, or a stale verdict could hang off an unrelated revision.
                    if not nonempty_text(item.get("historical_evidence_note")):
                        errors.append(
                            f"{where}.historical_evidence_note: {rev[:12]} is not an ancestor "
                            f"of the repair {fixed_at[:12]} (rebased or divergent lineage); "
                            "state in one line how the pre-fix state and the repair relate"
                        )


def validate_item(item, index, errors, pins):
    where = f"items[{index}]"
    if not require_keys(item, PIN_RELATED_KEYS, where, errors):
        return
    if not nonempty_text(item.get("id")):
        errors.append(f"{where}.id: must be non-empty")
    if not nonempty_text(item.get("source_ref")):
        errors.append(
            f"{where}.source_ref: name the comment id / URL / artifact path+index the "
            "claim came from — verdicts must be traceable to a source"
        )
    claim = item.get("claim_verbatim")
    if not isinstance(claim, str) or len(claim.strip()) < 20:
        errors.append(
            f"{where}.claim_verbatim: quote the claim as written (min 20 chars) — a "
            "paraphrase can quietly repair a false finding before it is judged"
        )
    if item.get("verdict") not in VERDICTS:
        errors.append(f"{where}.verdict: unknown value {item.get('verdict')!r}")
    entries = item.get("evidence")
    if not nonempty_list(entries):
        errors.append(f"{where}.evidence: must be a non-empty array of cited facts")
    else:
        check_citations(entries, f"{where}.evidence", errors, pins)
        check_quoted_snippets(entries, f"{where}.evidence", errors, pins)
    check_subclaims(item, where, errors, pins)
    check_repro(item, where, errors, pins)
    check_falsification(item, where, errors)
    check_mutation_probe(item, where, errors)
    check_reachability(item, where, errors, pins)
    check_verdict_obligations(item, where, errors, pins)
    check_historical_citations(item, where, errors, pins)


def validate(data, repo=None):
    errors = []
    if not isinstance(data, dict):
        return ["artifact: expected a JSON object"]
    require_keys(data, ("schema_version", "pin", "source", "items"), "artifact", errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"artifact.schema_version: expected {SCHEMA_VERSION}, got {data.get('schema_version')!r}"
        )
    if data.get("source") not in SOURCES:
        errors.append(f"artifact.source: unknown value {data.get('source')!r}")
    pin = data.get("pin")
    pins = PinChecker(
        repo,
        pin.get("head") if isinstance(pin, dict) else None,
        pin.get("base") if isinstance(pin, dict) else None,
    )
    if not isinstance(pin, dict):
        errors.append("artifact.pin: expected object")
    else:
        require_keys(pin, ("head", "base", "verified_at"), "artifact.pin", errors)
        if not is_oid(pin.get("head")):
            errors.append("artifact.pin.head: must be a 40-character lowercase hex OID")
        if not is_oid(pin.get("base")):
            errors.append("artifact.pin.base: must be a 40-character lowercase hex OID")
        if not nonempty_text(pin.get("verified_at")):
            errors.append("artifact.pin.verified_at: must be non-empty")
        if not nonempty_text(pin.get("ref")):
            errors.append(
                "artifact.pin.ref: name the immutable ref the evidence was read from "
                "(e.g. refs/verify/pr-<N>/head-<oid>)"
            )
        if repo is not None and is_oid(pin.get("head")) and pins.commit_exists(pin["head"]) is False:
            errors.append(
                "artifact.pin.head: not found in --repo — the pinned revision must exist in "
                "the repository the evidence was read from"
            )
            # Every citation below would now fail for the wrong reason; degrade to
            # shape checking so the author sees one actionable error, not a cascade.
            pins.repo = None
    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("artifact.items: must be a non-empty array")
        return errors
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}]: expected object")
            continue
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id.strip() in seen:
            errors.append(f"items[{index}].id: duplicate id {item_id!r}")
        if isinstance(item_id, str):
            seen.add(item_id.strip())
        validate_item(item, index, errors, pins)
    totals = data.get("totals")
    if totals is not None:
        if not isinstance(totals, dict):
            errors.append("artifact.totals: expected an object mapping verdict -> count")
        else:
            counts = {verdict: 0 for verdict in VERDICTS}
            for item in items:
                if isinstance(item, dict) and item.get("verdict") in VERDICTS:
                    counts[item["verdict"]] += 1
            for verdict, claimed in totals.items():
                if verdict not in VERDICTS:
                    errors.append(f"artifact.totals: unknown verdict key {verdict!r}")
                elif claimed != counts[verdict]:
                    errors.append(
                        f"artifact.totals.{verdict}: claims {claimed} but items contain "
                        f"{counts[verdict]}"
                    )
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", help="path to verification_<PR>.json")
    parser.add_argument(
        "--repo",
        default=None,
        help="git repository used to resolve `git show` citations; without it only the "
        "shape of the artifact is checked (revision/path/line gates are inactive)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args(argv)

    path = Path(args.artifact)
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"❌ cannot read artifact: {error}", file=sys.stderr)
        return 2

    errors = validate(data, repo=args.repo)
    mode = "repo-checked" if args.repo else "shape-only (run with --repo to check citations)"
    if args.json:
        print(json.dumps({"ok": not errors, "mode": mode, "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        print(f"❌ verification artifact failed {len(errors)} gate(s) [{mode}]:", file=sys.stderr)
        for error in errors:
            print(f"   - {error}", file=sys.stderr)
    else:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        print(f"✅ verification artifact valid [{mode}] (sha256:{digest})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
