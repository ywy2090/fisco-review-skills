import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_verification.py")


def base_item(**overrides):
    item = {
        "id": "F1",
        "source_ref": "PR #5549 review comment 12345",
        "claim_verbatim": "Non-empty accessList blanket-rejected: legitimate EIP-2930 txs can never land",
        "subclaims": {
            "location": {"text": "OpstackExecutor.h:479-485", "verdict": "confirmed", "evidence": ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — mismatch check"]},
            "mechanism": {"text": "mirror vs envelope list compared for equality", "verdict": "confirmed", "evidence": ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485"]},
            "impact": {"text": "op-geth-legal blocks rejected", "verdict": "confirmed", "evidence": ["test opstack-executor-tests/OpAccessList.Vectors fails"]},
            "premise": {"text": "op-geth accepts matching lists", "verdict": "confirmed", "evidence": ["test opstack-executor-tests/OpAccessList.Vectors fails"]},
        },
        "verdict": "confirmed",
        "evidence": ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — `// bind the envelope's own accessList (element-wise)`"],
        "reachability": {"on_live_path": True, "evidence": ["git grep -n isAccessListConsistent $PIN -- opstack-executor"], "scope_note": "reached from OpBlockExecute.cpp:192 on the block validation path"},
        "repro": {
            "tier": "unit_test",
            "claim_kind": "behavioural",
            "command": "cd build && ctest -R OpstackExecutorTests --output-on-failure",
            "expected": "block with matching accessList accepted",
            "observed": "OpstackExecutorTests/... FAILED: INVALID for matching list",
            "exit_code": 1,
            "modifies_production_code": False,
            "worktree": None,
        },
        "falsification_attempts": [
            {"attempt": "look for an upstream guard that rejects the tx earlier", "result": "no guard: OpBlockExecute calls the check unconditionally"},
        ],
        "mutation_probe": None,
        "boundary": "single-node, MinSizeRel, accessList path only; no OP-mainnet replay",
        "residual_risk": "none identified beyond the boundary above",
        "recommendation": "fix",
    }
    item.update(overrides)
    return item


def artifact(**overrides):
    data = {
        "schema_version": 1,
        "pin": {"head": "a" * 40, "base": "b" * 40, "ref": "refs/verify/pr-5549/head-aaaa", "verified_at": "2026-09-10T12:00:00Z"},
        "source": "pr_comment",
        "items": [base_item()],
    }
    data.update(overrides)
    return data


def run(data, repo=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as stream:
        json.dump(data, stream)
        path = stream.name
    command = ["python3", str(SCRIPT), path]
    if repo:
        command.extend(["--repo", repo])
    return subprocess.run(command, capture_output=True, text=True, check=False)


class PinRepository:
    """A throwaway repo whose history has a pre-fix commit and a pinned head."""

    def __init__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.root, check=True)
        target = self.root / "opstack-executor" / "OpstackExecutor.h"
        target.parent.mkdir(parents=True)
        target.write_text("\n".join(f"// line {n}" for n in range(1, 501)) + "\n")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "pre-fix"], cwd=self.root, check=True)
        self.parent = self._rev("HEAD")
        target.write_text(
            "\n".join(
                "// bind the envelope's own accessList (element-wise)" if n == 482 else f"// line {n}"
                for n in range(1, 501)
            )
            + "\n"
        )
        subprocess.run(["git", "commit", "-qam", "fix"], cwd=self.root, check=True)
        self.head = self._rev("HEAD")

    def _rev(self, ref):
        return subprocess.run(
            ["git", "rev-parse", ref], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout.strip()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.cleanup()
        return False

    def cleanup(self):
        self.dir.cleanup()


class StructuralGateTest(unittest.TestCase):
    def assert_fails(self, data, needle, repo=None):
        result = run(data, repo=repo)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(needle, result.stderr, result.stderr)
        return result

    def test_valid_artifact_passes(self):
        result = run(artifact())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid", result.stdout)

    def test_requires_pin_oid(self):
        data = artifact(pin={"head": "deadbeef", "base": "b" * 40, "ref": "refs/x", "verified_at": "now"})
        self.assert_fails(data, "pin.head")

    def test_requires_immutable_ref(self):
        data = artifact(pin={"head": "a" * 40, "base": "b" * 40, "verified_at": "now"})
        self.assert_fails(data, "pin.ref")

    def test_unknown_verdict_rejected(self):
        data = artifact(items=[base_item(verdict="probably_true")])
        self.assert_fails(data, "unknown value")

    def test_confirmed_without_repro_rejected(self):
        data = artifact(items=[base_item(repro=None)])
        self.assert_fails(data, "requires a repro")

    def test_repro_observed_must_be_non_empty(self):
        item = base_item()
        item["repro"]["observed"] = "  "
        self.assert_fails(artifact(items=[item]), "repro.observed")

    def test_refuted_requires_positive_counter_evidence(self):
        item = base_item(
            verdict="refuted",
            recommendation="reject_with_reason",
            falsification_attempts=[],
            subclaims={name: {"text": "x", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1 — guarded upstream"]} for name in ("location", "mechanism", "impact", "premise")},
        )
        self.assert_fails(artifact(items=[item]), "falsification_attempts")

    def test_refuted_cannot_recommend_fix(self):
        item = base_item(verdict="refuted", recommendation="fix")
        self.assert_fails(artifact(items=[item]), "refuted cannot recommend fix")

    def test_unreproducible_cannot_recommend_fix(self):
        item = base_item(
            verdict="unreproducible",
            recommendation="fix",
            falsification_attempts=[{"attempt": "ran the suite", "result": "green"}],
        )
        self.assert_fails(artifact(items=[item]), "cannot recommend fix")

    def test_unreproducible_with_hardening_passes(self):
        item = base_item(
            verdict="unreproducible",
            recommendation="hardening",
            falsification_attempts=[{"attempt": "ran with 8-byte nonce", "result": "no failure observed"}],
        )
        result = run(artifact(items=[item]))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_attempt_without_result_rejected(self):
        item = base_item(
            verdict="unreproducible",
            recommendation="hardening",
            falsification_attempts=[{"attempt": "ran the suite"}],
        )
        self.assert_fails(artifact(items=[item]), "result")

    def test_stale_requires_repair_commit_and_resolution_evidence(self):
        item = base_item(verdict="stale", recommendation="defer")
        self.assert_fails(artifact(items=[item]), "fixed_at")

    def test_stale_with_repair_commit_passes(self):
        item = base_item(
            verdict="stale",
            recommendation="defer",
            fixed_at="c" * 40,
            resolution_evidence=["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — equality compare removed"],
            historical_evidence=["git show " + "1" * 40 + ":opstack-executor/OpstackExecutor.h:482 — blanket reject"],
        )
        item["subclaims"]["mechanism"] = {"text": "stated cause", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1"]}
        result = run(artifact(items=[item]))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stale_mechanism_must_be_refuted_at_pin(self):
        item = base_item(
            verdict="stale",
            recommendation="defer",
            fixed_at="c" * 40,
            resolution_evidence=["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — compare removed"],
            historical_evidence=["git show " + "1" * 40 + ":opstack-executor/OpstackExecutor.h:482 — blanket reject"],
        )
        self.assert_fails(artifact(items=[item]), "judged at the pin")

    def test_stale_requires_pre_fix_citation(self):
        item = base_item(
            verdict="stale",
            recommendation="defer",
            fixed_at="c" * 40,
            resolution_evidence=["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — compare removed"],
        )
        self.assert_fails(artifact(items=[item]), "historical_evidence")

    def test_only_stale_may_cite_foreign_revision(self):
        item = base_item(historical_evidence=["git show 1" + "1" * 39 + ":a.h:1 — old code"])
        self.assert_fails(artifact(items=[item]), "only verdict=stale")

    def test_refuted_mechanism_forbids_plain_confirmed(self):
        item = base_item()
        item["subclaims"]["mechanism"] = {"text": "stated cause", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1"]}
        self.assert_fails(artifact(items=[item]), "confirmed_symptom_mechanism_differs")

    def test_symptom_mechanism_differs_requires_correction(self):
        item = base_item(verdict="confirmed_symptom_mechanism_differs")
        item["subclaims"]["mechanism"] = {"text": "stated cause", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1"]}
        self.assert_fails(artifact(items=[item]), "mechanism_correction")

    def test_undecidable_requires_missing_inputs(self):
        item = base_item(verdict="undecidable", recommendation="needs_human")
        self.assert_fails(artifact(items=[item]), "missing_inputs")

    def test_subclaim_needs_evidence_and_not_claimed_note(self):
        item = base_item()
        item["subclaims"]["impact"] = {"text": "x", "verdict": "confirmed", "evidence": []}
        self.assert_fails(artifact(items=[item]), "needs evidence")
        item["subclaims"]["impact"] = {"text": "x", "verdict": "not_claimed"}
        self.assert_fails(artifact(items=[item]), "not_claimed requires a note")

    def test_mismatched_location_verdict_is_normalised(self):
        item = base_item()
        item["subclaims"]["impact"] = {"text": "x", "verdict": "unknown"}
        self.assert_fails(artifact(items=[item]), "unknown verdict")

    def test_mutation_repro_requires_probe_and_worktree(self):
        item = base_item()
        item["repro"]["modifies_production_code"] = True
        self.assert_fails(artifact(items=[item]), "mutation_probe")

    def test_mutation_probe_must_be_restored(self):
        item = base_item()
        item["repro"]["modifies_production_code"] = True
        item["repro"]["worktree"] = "/tmp/repro"
        item["mutation_probe"] = {"file": "a.h", "diff": "-x\n+y", "symptom_disappeared": True, "restored": False, "post_restore_diff_empty": False}
        self.assert_fails(artifact(items=[item]), "restored and the tree must be clean")

    def test_repro_needs_explicit_mutation_flag(self):
        item = base_item()
        del item["repro"]["modifies_production_code"]
        self.assert_fails(artifact(items=[item]), "modifies_production_code")

    def test_reachability_needs_scope_note_and_caller_evidence(self):
        item = base_item()
        item["reachability"] = {"on_live_path": True, "scope_note": "", "evidence": []}
        self.assert_fails(artifact(items=[item]), "scope_note")

    def test_boundary_and_residual_risk_required(self):
        item = base_item(boundary="  ")
        self.assert_fails(artifact(items=[item]), "boundary")

    def test_verbatim_claim_cannot_be_a_stub(self):
        item = base_item(claim_verbatim="accessList bug")
        self.assert_fails(artifact(items=[item]), "claim_verbatim")

    def test_source_ref_required(self):
        item = base_item(source_ref="")
        self.assert_fails(artifact(items=[item]), "source_ref")

    def test_duplicate_ids_rejected(self):
        data = artifact(items=[base_item(), base_item()])
        self.assert_fails(data, "duplicate id")

    def test_totals_must_match_items(self):
        data = artifact(totals={"confirmed": 3})
        self.assert_fails(data, "claims 3")

    def test_evidence_must_be_cited_or_located(self):
        item = base_item(evidence=["the code looks wrong"])
        self.assert_fails(artifact(items=[item]), "evidence[0]")

    def test_invalid_json_is_a_hard_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as stream:
            stream.write("{not json")
            path = stream.name
        result = subprocess.run(["python3", str(SCRIPT), path], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


class RegressionTest(unittest.TestCase):
    """Cases that previously slipped through the gates (found in adversarial review)."""

    def assert_fails(self, data, needle, repo=None):
        result = run(data, repo=repo)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(needle, result.stderr, result.stderr)

    # -- citations that were never parsed or checked ------------------------

    def test_documented_verify_pin_variable_is_accepted(self):
        """repro-recipes.md tells the agent to cite $VERIFY_PIN."""
        item = base_item(
            evidence=["git show $VERIFY_PIN:opstack-executor/OpstackExecutor.h:479-485 — check"],
        )
        result = run(artifact(items=[item]))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_second_citation_in_one_evidence_string_is_checked(self):
        item = base_item(
            evidence=[
                "git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — main claim, "
                "corroborated by git show origin/release-3.18.0:other/File.h:1"
            ]
        )
        self.assert_fails(artifact(items=[item]), "neither the pinned head")

    def test_subclaim_evidence_citations_are_checked(self):
        item = base_item()
        item["subclaims"]["location"]["evidence"] = ["git show deadbeefdeadbeefdeadbeefdeadbeefdeadbeef:a.h:1 — x"]
        self.assert_fails(artifact(items=[item]), "subclaims.location.evidence")

    def test_reachability_evidence_citations_are_checked(self):
        item = base_item()
        item["reachability"]["evidence"] = ["git show 1111111111111111111111111111111111111111:a.h:1 — x"]
        self.assert_fails(artifact(items=[item]), "reachability.evidence")

    def test_resolution_evidence_needs_a_real_citation(self):
        item = base_item(
            verdict="stale",
            recommendation="defer",
            fixed_at="c" * 40,
            resolution_evidence=["whatever we saw"],
            historical_evidence=["git show " + "1" * 40 + ":opstack-executor/OpstackExecutor.h:482 — reject"],
        )
        item["subclaims"]["mechanism"] = {"text": "x", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1"]}
        self.assert_fails(artifact(items=[item]), "at least one `git show")

    def test_historical_evidence_cannot_cite_the_pin(self):
        item = base_item(
            verdict="stale",
            recommendation="defer",
            fixed_at="c" * 40,
            resolution_evidence=["git show $PIN:opstack-executor/OpstackExecutor.h:742-750 — bind"],
            historical_evidence=["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — pre-fix"],
        )
        item["subclaims"]["mechanism"] = {"text": "x", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1"]}
        self.assert_fails(artifact(items=[item]), "cites the pin itself")

    # -- pin / fixed_at are now anchored in the repo -------------------------

    def test_citation_revision_is_resolved_unambiguously(self):
        """A short prefix that git disambiguates elsewhere must not pass silently."""
        with PinRepository() as repo:
            item = base_item(
                evidence=[f"git show {repo.head[:7]}:opstack-executor/OpstackExecutor.h:479-485 — x"]
            )
            data = artifact(pin={"head": repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"}, items=[item])
            result = run(data, repo=repo.dir.name)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_pin_head_must_exist_in_repo(self):
        with PinRepository() as repo:
            data = artifact(pin={"head": "9" * 40, "base": "8" * 40, "ref": "refs/verify/x", "verified_at": "now"})
            self.assert_fails(data, "pin.head: not found", repo=repo.dir.name)

    def test_fixed_at_must_be_a_commit_and_an_ancestor(self):
        with PinRepository() as repo:
            item = base_item(
                verdict="stale",
                recommendation="defer",
                fixed_at="7" * 40,
                resolution_evidence=[f"git show $PIN:opstack-executor/OpstackExecutor.h:1 — x"],
                historical_evidence=[f"git show {repo.parent}:opstack-executor/OpstackExecutor.h:1 — x"],
            )
            item["subclaims"]["mechanism"] = {"text": "x", "verdict": "refuted", "evidence": ["git show $PIN:a.h:1"]}
            data = artifact(pin={"head": repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"}, items=[item])
            self.assert_fails(data, "fixed_at", repo=repo.dir.name)

    def test_directory_citation_is_rejected(self):
        with PinRepository() as repo:
            item = base_item(
                evidence=["git show $PIN:opstack-executor:1-2 — directory listing"]
            )
            data = artifact(pin={"head": repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"}, items=[item])
            self.assert_fails(data, "not a file", repo=repo.dir.name)

    # -- remaining structural evasions --------------------------------------

    def test_totals_must_be_complete_and_well_typed(self):
        self.assert_fails(artifact(totals={"refuted": 99}), "claims 99")
        self.assert_fails(artifact(totals={"bogus": 1}), "unknown verdict key")
        self.assert_fails(artifact(totals="all confirmed"), "expected an object")

    def test_undecidable_cannot_recommend_fix(self):
        item = base_item(verdict="undecidable", recommendation="fix", missing_inputs=["op-geth reference behaviour"])
        self.assert_fails(artifact(items=[item]), "cannot recommend fix")

    def test_behavioural_claim_cannot_be_settled_statically(self):
        item = base_item()
        item["repro"]["tier"] = "static"
        item["repro"]["claim_kind"] = "behavioural"
        self.assert_fails(artifact(items=[item]), "cannot be settled by static reading")

    def test_claim_kind_is_required(self):
        item = base_item()
        del item["repro"]["claim_kind"]
        self.assert_fails(artifact(items=[item]), "claim_kind")

    def test_exit_code_is_required(self):
        item = base_item()
        del item["repro"]["exit_code"]
        self.assert_fails(artifact(items=[item]), "exit_code")

    def test_non_object_subclaim_is_a_gate_error_not_a_crash(self):
        for bad in ([], 42):
            item = base_item()
            item["subclaims"]["location"] = bad
            result = run(artifact(items=[item]))
            self.assertEqual(result.returncode, 1)
            self.assertIn("expected an object", result.stderr)

    def test_whitespace_only_fields_are_rejected(self):
        for field in ("id", "source_ref"):
            item = base_item(**{field: "   "})
            self.assert_fails(artifact(items=[item]), field)

    def test_non_citation_locator_must_say_where_the_fact_comes_from(self):
        item = base_item(evidence=["https://github.com/FISCO-BCOS/FISCO-BCOS/issues/1234 is the tracking issue"])
        result = run(artifact(items=[item]))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invented_code_quote_is_rejected(self):
        """A citation proves where the author looked, not that the line says what they claim."""
        with PinRepository() as repo:
            item = base_item(
                evidence=[
                    "git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — "
                    "`if (!accessList.empty() && !mirrorAccessList.empty())` blanket reject"
                ]
            )
            data = artifact(
                pin={"head": repo.head, "base": repo.parent, "ref": "refs/verify/x", "verified_at": "now"},
                items=[item],
            )
            self.assert_fails(data, "none of the quoted snippets appears", repo=repo.dir.name)

    def test_shell_snippet_is_not_treated_as_quoted_source(self):
        with PinRepository() as repo:
            item = base_item(
                evidence=[
                    "git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — read with "
                    "`git show $PIN:opstack-executor/OpstackExecutor.h | nl -ba`"
                ]
            )
            data = artifact(
                pin={"head": repo.head, "base": repo.parent, "ref": "refs/verify/x", "verified_at": "now"},
                items=[item],
            )
            result = run(data, repo=repo.dir.name)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_shape_only_mode_is_announced(self):
        result = run(artifact())
        self.assertIn("shape-only", result.stdout, result.stdout)


class PinCitationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = PinRepository()

    @classmethod
    def tearDownClass(cls):
        cls.repo.cleanup()

    def pinned(self, **overrides):
        pin = {
            "head": self.repo.head,
            "base": "b" * 40,
            "ref": f"refs/verify/pr-5549/head-{self.repo.head[:12]}",
            "verified_at": "2026-09-10T12:00:00Z",
        }
        pin.update(overrides)
        return artifact(pin=pin, **({} if "items" not in overrides else {"items": overrides.pop("items")}))

    def test_citation_at_pin_passes(self):
        data = artifact(pin={"head": self.repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"})
        result = run(data, repo=self.repo.dir.name)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_citation_from_foreign_revision_rejected(self):
        data = artifact(pin={"head": self.repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"})
        data["items"][0]["evidence"] = ["git show f" + "f" * 39 + ":opstack-executor/OpstackExecutor.h:1 — claim"]
        result = run(data, repo=self.repo.dir.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn("neither the pinned head", result.stderr)

    def test_branch_name_citation_rejected(self):
        data = artifact(pin={"head": self.repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"})
        data["items"][0]["evidence"] = ["git show origin/release-3.18.0:opstack-executor/OpstackExecutor.h:1 — claim"]
        result = run(data, repo=self.repo.dir.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn("neither the pinned head", result.stderr)

    def test_missing_path_at_pin_rejected(self):
        data = artifact(pin={"head": self.repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"})
        data["items"][0]["evidence"] = ["git show $PIN:opstack-executor/Gone.h:10 — claim"]
        result = run(data, repo=self.repo.dir.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stderr)

    def test_line_range_beyond_file_rejected(self):
        data = artifact(pin={"head": self.repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"})
        data["items"][0]["evidence"] = ["git show $PIN:opstack-executor/OpstackExecutor.h:900-910 — claim"]
        result = run(data, repo=self.repo.dir.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside", result.stderr)

    def test_line_range_inside_file_passes(self):
        data = artifact(pin={"head": self.repo.head, "base": "b" * 40, "ref": "refs/verify/x", "verified_at": "now"})
        data["items"][0]["evidence"] = ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — claim"]
        data["items"][0]["subclaims"]["location"]["evidence"] = ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — claim"]
        data["items"][0]["subclaims"]["mechanism"]["evidence"] = ["git show $PIN:opstack-executor/OpstackExecutor.h:479-485 — claim"]
        result = run(data, repo=self.repo.dir.name)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
