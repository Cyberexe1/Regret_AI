"""DynamoDB-backed decision storage.

Single-table design. Key layout:

- Decision item:      PK=DECISION#<id>          SK=METADATA
                       GSI1PK=USER#<user_id>     GSI1SK=DECISION#<created_at>#<id>
- Child entities live under the same decision partition, e.g.:
                       PK=DECISION#<id>          SK=ASSUMPTION#<assumption_id>
                       PK=DECISION#<id>          SK=BLINDSPOT#<blindspot_id>
                       PK=DECISION#<id>          SK=EVIDENCE_FINDING#<finding_id>
                       PK=DECISION#<id>          SK=CHALLENGE#<challenge_id>
                       PK=DECISION#<id>          SK=REGRET_SCENARIO#<scenario_id>
                       PK=DECISION#<id>          SK=SCENARIO#<scenario_id>
                       PK=DECISION#<id>          SK=THRESHOLD#<threshold_id>
                       PK=DECISION#<id>          SK=EXPERIMENT#<experiment_id>
                       GSI2PK=EXPERIMENT#<experiment_id>  GSI2SK=EXPERIMENT#<experiment_id>

  EVIDENCE_FINDING is the Evidence Agent's analysis of a source, kept
  separate from the source itself (`SK=EVIDENCE#<evidence_id>`, owned by
  `EvidenceRepository`) - persisting a finding never overwrites the
  original uploaded evidence record. CHALLENGE (Devil's Advocate) and
  REGRET_SCENARIO (Regret Simulator) follow the same "separate analysis
  entity, never overwrite an earlier stage's output" pattern. EXPERIMENT
  additionally gets a GSI2 entry (shared with `EvidenceRepository`'s own
  GSI2 usage, distinguished by key prefix) so it can be looked up by its
  own id alone via `get_experiment_by_id` - see
  `GET /api/v1/experiments/{experiment_id}`.

Putting every entity that belongs to a decision under the `DECISION#<id>`
partition means "get everything about this decision" is a single Query on
PK, with no scan. Listing a user's decisions instead goes through GSI1,
which is the only access pattern that needs to fan out across decisions
rather than within one.

Evidence and analysis runs have their own repository files
(`evidence_repository.py`, `analysis_repository.py`) per the spec, but
follow the exact same partitioning scheme.
"""

import base64
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Attr, Key

from app.repositories.dynamodb import DynamoDBGateway
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionStatus, DecisionUpdate
from app.schemas.decision_resources import (
    Assumption,
    AssumptionSource,
    Blindspot,
    BlindspotEvidenceStatus,
    Challenge,
    DecisionAssessment,
    EvidenceStatus,
    Experiment,
    ExperimentOutcome,
    ExperimentStatus,
    ExternalEvidence,
    ReEvaluation,
    Scenario,
    Threshold,
)
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import ExperimentResult as StoredExperimentResult
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario

_METADATA_SK = "METADATA"


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _user_gsi1pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _decision_gsi1sk(created_at: str, decision_id: UUID | str) -> str:
    return f"DECISION#{created_at}#{decision_id}"


def _experiment_gsi2pk(experiment_id: UUID | str) -> str:
    """GSI2 key so an experiment can be resolved by its own id alone -
    mirrors `app.repositories.evidence_repository._evidence_gsi2pk`. Both
    entity types share the same GSI2 index (see `create_table_if_not_exists`
    in `app.repositories.dynamodb`); their key values never collide because
    each is prefixed with its own entity tag ('EVIDENCE#'/'EXPERIMENT#')."""
    return f"EXPERIMENT#{experiment_id}"


def _encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    if not last_evaluated_key:
        return None
    raw = json.dumps(last_evaluated_key, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
    return json.loads(raw)


class DecisionRepository:
    """CRUD + query operations for decisions and their child entities."""

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    # --- Decision CRUD -------------------------------------------------------

    def create(self, user_id: str, payload: DecisionCreate) -> DecisionResponse:
        decision_id = uuid4()
        now = datetime.now(UTC).isoformat()

        item = {
            "PK": _decision_pk(decision_id),
            "SK": _METADATA_SK,
            "entity_type": "DECISION",
            "GSI1PK": _user_gsi1pk(user_id),
            "GSI1SK": _decision_gsi1sk(now, decision_id),
            "id": str(decision_id),
            "user_id": user_id,
            "title": payload.title,
            "description": payload.description,
            "desired_outcome": payload.desired_outcome,
            "budget": payload.budget,
            "currency": payload.currency,
            "timeline": payload.timeline,
            "location": payload.location,
            "risk_tolerance": payload.risk_tolerance,
            "beliefs": payload.beliefs,
            "status": DecisionStatus.DRAFT.value,
            "created_at": now,
            "updated_at": now,
        }
        # A decision id is freshly generated, so this should never collide -
        # the condition exists purely as a safety net against a UUID clash.
        self._gateway.put_item(item, condition=Attr("PK").not_exists())
        return self.to_response(item)

    def get(self, decision_id: UUID) -> DecisionResponse | None:
        item = self._gateway.get_item({"PK": _decision_pk(decision_id), "SK": _METADATA_SK})
        return self.to_response(item) if item is not None else None

    def get_raw(self, decision_id: UUID) -> dict[str, Any] | None:
        """Internal variant that also exposes `user_id`, for ownership checks."""
        return self._gateway.get_item({"PK": _decision_pk(decision_id), "SK": _METADATA_SK})

    def list_for_user(
        self, user_id: str, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[DecisionResponse], str | None]:
        items, last_evaluated_key = self._gateway.query(
            key_condition=Key("GSI1PK").eq(_user_gsi1pk(user_id)),
            index_name="GSI1",
            limit=limit,
            exclusive_start_key=_decode_cursor(cursor),
            scan_index_forward=False,  # newest first
        )
        return [self.to_response(item) for item in items], _encode_cursor(last_evaluated_key)

    def update(self, decision_id: UUID, payload: DecisionUpdate) -> DecisionResponse:
        now = datetime.now(UTC).isoformat()
        fields = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})

        set_clauses = ["updated_at = :updated_at"]
        values: dict[str, Any] = {":updated_at": now}
        names: dict[str, str] = {}

        for field_name, value in fields.items():
            placeholder = f":{field_name}"
            name_placeholder = f"#{field_name}"
            set_clauses.append(f"{name_placeholder} = {placeholder}")
            values[placeholder] = value.value if isinstance(value, DecisionStatus) else value
            names[name_placeholder] = field_name

        update_expression = "SET " + ", ".join(set_clauses)

        condition = Attr("PK").exists()
        if payload.expected_updated_at is not None:
            condition = condition & Attr("updated_at").eq(payload.expected_updated_at.isoformat())

        updated = self._gateway.update_item(
            key={"PK": _decision_pk(decision_id), "SK": _METADATA_SK},
            update_expression=update_expression,
            expression_attribute_values=values,
            expression_attribute_names=names or None,
            condition=condition,
        )
        return self.to_response(updated)

    def delete(self, decision_id: UUID) -> None:
        self._gateway.delete_item(
            key={"PK": _decision_pk(decision_id), "SK": _METADATA_SK},
            condition=Attr("PK").exists(),
        )

    # --- Child entity writes ---------------------------------------------------

    def create_assumptions(
        self, decision_id: UUID, findings: list[dict[str, Any]]
    ) -> list[Assumption]:
        """Persist assumption findings for a decision.

        Takes plain dicts (statement/source/importance/confidence/
        evidence_status/dependency/failure_consequence) rather than the
        agent's own `AssumptionFinding` model, so this repository has no
        dependency on `app.agents` - the orchestrator is responsible for
        converting an agent's structured output into this shape before
        calling here.
        """
        now = datetime.now(UTC).isoformat()
        created: list[Assumption] = []

        for finding in findings:
            assumption_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"ASSUMPTION#{assumption_id}",
                "entity_type": "ASSUMPTION",
                "id": str(assumption_id),
                "decision_id": str(decision_id),
                "statement": finding["statement"],
                "source": AssumptionSource(finding["source"]).value,
                "importance": finding.get("importance"),
                "confidence": finding.get("confidence"),
                "evidence_status": EvidenceStatus(finding["evidence_status"]).value,
                "dependency": finding.get("dependency"),
                "failure_consequence": finding.get("failure_consequence"),
                "reason": finding.get("reason"),
                "created_at": now,
                "updated_at": now,
            }
            self._gateway.put_item(item)
            created.append(Assumption.model_validate(_strip_keys(item)))

        return created

    def create_blindspots(
        self, decision_id: UUID, findings: list[dict[str, Any]]
    ) -> list[Blindspot]:
        """Persist blindspot findings for a decision.

        Takes plain dicts (question/category/importance/confidence/
        evidence_status/related_assumption_ids/why_it_matters/
        evidence_gap) rather than the agent's own `BlindspotFinding` model,
        for the same reason as `create_assumptions`: this repository has no
        dependency on `app.agents`. The orchestrator converts the agent's
        structured output into this shape first.
        """
        now = datetime.now(UTC).isoformat()
        created: list[Blindspot] = []

        for finding in findings:
            blindspot_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"BLINDSPOT#{blindspot_id}",
                "entity_type": "BLINDSPOT",
                "id": str(blindspot_id),
                "decision_id": str(decision_id),
                "question": finding["question"],
                "category": finding.get("category"),
                "importance": finding.get("importance"),
                "confidence": finding.get("confidence"),
                "evidence_status": BlindspotEvidenceStatus(finding["evidence_status"]).value,
                "related_assumption_ids": finding.get("related_assumption_ids", []),
                "why_it_matters": finding.get("why_it_matters"),
                "evidence_gap": finding.get("evidence_gap"),
                "created_at": now,
            }
            self._gateway.put_item(item)
            created.append(Blindspot.model_validate(_strip_keys(item)))

        return created

    def create_evidence_findings(
        self, decision_id: UUID, findings: list[dict[str, Any]]
    ) -> list[StoredEvidenceFinding]:
        """Persist evidence findings for a decision.

        Stored under `SK=EVIDENCE_FINDING#<finding_id>` - a separate key
        space from the original `SK=EVIDENCE#<evidence_id>` records (see
        `EvidenceRepository`), so the Evidence Agent's analysis of a source
        never overwrites the source itself. Takes plain dicts (evidence_id/
        claim/support_level/credibility/related_assumption_ids/
        related_blindspot_ids/explanation/excerpt) for the same reason as
        `create_assumptions` and `create_blindspots`.
        """
        now = datetime.now(UTC).isoformat()
        created: list[StoredEvidenceFinding] = []

        for finding in findings:
            finding_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"EVIDENCE_FINDING#{finding_id}",
                "entity_type": "EVIDENCE_FINDING",
                "id": str(finding_id),
                "decision_id": str(decision_id),
                "evidence_id": finding["evidence_id"],
                "claim": finding["claim"],
                "support_level": finding.get("support_level"),
                "credibility": finding.get("credibility"),
                "related_assumption_ids": finding.get("related_assumption_ids", []),
                "related_blindspot_ids": finding.get("related_blindspot_ids", []),
                "explanation": finding.get("explanation"),
                "excerpt": finding.get("excerpt"),
                "created_at": now,
            }
            self._gateway.put_item(item)
            created.append(StoredEvidenceFinding.model_validate(_strip_keys(item)))

        return created

    def create_challenges(
        self, decision_id: UUID, challenges: list[dict[str, Any]]
    ) -> list[Challenge]:
        """Persist Devil's Advocate challenges for a decision.

        Takes plain dicts (claim/attack/severity/confidence/
        related_assumption_ids/related_blindspot_ids/
        related_evidence_finding_ids/failure_mechanism/evidence_basis)
        rather than the agent's own `Challenge` model, for the same reason
        as `create_assumptions`/`create_blindspots`: this repository has no
        dependency on `app.agents`. The orchestrator converts the agent's
        structured output into this shape first.
        """
        now = datetime.now(UTC).isoformat()
        created: list[Challenge] = []

        for challenge in challenges:
            challenge_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"CHALLENGE#{challenge_id}",
                "entity_type": "CHALLENGE",
                "id": str(challenge_id),
                "decision_id": str(decision_id),
                "claim": challenge["claim"],
                "attack": challenge["attack"],
                "severity": challenge.get("severity"),
                "confidence": challenge.get("confidence"),
                "related_assumption_ids": challenge.get("related_assumption_ids", []),
                "related_blindspot_ids": challenge.get("related_blindspot_ids", []),
                "related_evidence_finding_ids": challenge.get("related_evidence_finding_ids", []),
                "failure_mechanism": challenge.get("failure_mechanism"),
                "evidence_basis": challenge.get("evidence_basis"),
                "created_at": now,
            }
            self._gateway.put_item(item)
            created.append(Challenge.model_validate(_strip_keys(item)))

        return created

    def create_regret_scenarios(
        self, decision_id: UUID, scenarios: list[dict[str, Any]]
    ) -> list[StoredRegretScenario]:
        """Persist Regret Simulator scenarios for a decision.

        Takes plain dicts (title/failure_condition/probability_band/impact/
        regret_level/trigger_variable/trigger_direction/
        provisional_threshold/consequence/related_assumption_ids/
        related_challenge_ids/evidence_basis) rather than the agent's own
        `RegretScenario` model, for the same reason as the other
        `create_*` methods. The agent's own response-scoped `id` (used only
        to let `highest_risk_scenario_id` self-reference a sibling scenario
        within one response) is intentionally NOT carried over - a fresh,
        real, persisted id is assigned here instead.
        """
        now = datetime.now(UTC).isoformat()
        created: list[StoredRegretScenario] = []

        for scenario in scenarios:
            scenario_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"REGRET_SCENARIO#{scenario_id}",
                "entity_type": "REGRET_SCENARIO",
                "id": str(scenario_id),
                "decision_id": str(decision_id),
                "title": scenario["title"],
                "failure_condition": scenario["failure_condition"],
                "probability_band": scenario.get("probability_band"),
                "impact": scenario.get("impact"),
                "regret_level": scenario.get("regret_level"),
                "trigger_variable": scenario.get("trigger_variable"),
                "trigger_direction": scenario.get("trigger_direction"),
                "provisional_threshold": scenario.get("provisional_threshold"),
                "consequence": scenario.get("consequence"),
                "related_assumption_ids": scenario.get("related_assumption_ids", []),
                "related_challenge_ids": scenario.get("related_challenge_ids", []),
                "evidence_basis": scenario.get("evidence_basis"),
                "created_at": now,
            }
            self._gateway.put_item(item)
            created.append(StoredRegretScenario.model_validate(_strip_keys(item)))

        return created

    def create_thresholds(
        self, decision_id: UUID, thresholds: list[dict[str, Any]]
    ) -> list[Threshold]:
        """Persist Threshold Engine thresholds for a decision.

        Takes plain dicts (variable/threshold_type/direction/
        threshold_value/lower_bound/upper_bound/unit/confidence/
        derivation/consequence/related_regret_scenario_ids/
        related_assumption_ids/evidence_basis/validation_status/
        calculation_formula/calculation_inputs/calculation_provenance)
        rather than the agent's own `Threshold` model, for the same reason
        as the other `create_*` methods. The agent's own response-scoped
        `id` (used only to let `primary_threshold_id` self-reference a
        sibling threshold within one response) is intentionally NOT
        carried over - a fresh, real, persisted id is assigned here
        instead, exactly like `create_regret_scenarios`.
        """
        now = datetime.now(UTC).isoformat()
        created: list[Threshold] = []

        for threshold in thresholds:
            threshold_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"THRESHOLD#{threshold_id}",
                "entity_type": "THRESHOLD",
                "id": str(threshold_id),
                "decision_id": str(decision_id),
                "variable": threshold["variable"],
                "threshold_type": threshold.get("threshold_type"),
                "direction": threshold.get("direction"),
                "threshold_value": threshold.get("threshold_value"),
                "lower_bound": threshold.get("lower_bound"),
                "upper_bound": threshold.get("upper_bound"),
                "unit": threshold.get("unit"),
                "confidence": threshold.get("confidence"),
                "derivation": threshold.get("derivation"),
                "consequence": threshold.get("consequence"),
                "related_regret_scenario_ids": threshold.get("related_regret_scenario_ids", []),
                "related_assumption_ids": threshold.get("related_assumption_ids", []),
                "evidence_basis": threshold.get("evidence_basis"),
                "validation_status": threshold.get("validation_status"),
                "calculation_formula": threshold.get("calculation_formula"),
                "calculation_inputs": threshold.get("calculation_inputs"),
                "calculation_provenance": threshold.get("calculation_provenance"),
                "created_at": now,
            }
            self._gateway.put_item(item)
            created.append(Threshold.model_validate(_strip_keys(item)))

        return created

    def create_experiments(
        self, decision_id: UUID, experiments: list[dict[str, Any]]
    ) -> list[Experiment]:
        """Persist Experiment Planner experiments for a decision.

        Takes plain dicts (title/objective/hypothesis/target_threshold_id/
        variable_to_test/experiment_type/steps/success_criteria/
        failure_criteria/duration_days/estimated_cost/currency/
        evidence_to_collect/decision_rule/expected_information_gain/
        confidence/feasibility/reversibility/related_assumption_ids/
        related_regret_scenario_ids) rather than the agent's own
        `Experiment` model, for the same reason as the other `create_*`
        methods. The agent's own response-scoped `id` (used only to let
        `recommended_experiment_id` self-reference a sibling experiment
        within one response) is intentionally NOT carried over - a fresh,
        real, persisted id is assigned here instead, exactly like
        `create_thresholds`.

        Every experiment gets a `GSI2PK`/`GSI2SK` entry (the same index
        `EvidenceRepository.get_by_id` uses for evidence) so
        `get_experiment_by_id` can resolve an experiment by its own id
        alone, without knowing its parent decision - see
        `GET /api/v1/experiments/{experiment_id}`.
        """
        now = datetime.now(UTC).isoformat()
        created: list[Experiment] = []

        for experiment in experiments:
            experiment_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"EXPERIMENT#{experiment_id}",
                "entity_type": "EXPERIMENT",
                "GSI2PK": _experiment_gsi2pk(experiment_id),
                "GSI2SK": _experiment_gsi2pk(experiment_id),
                "id": str(experiment_id),
                "decision_id": str(decision_id),
                "title": experiment["title"],
                "objective": experiment.get("objective"),
                "hypothesis": experiment["hypothesis"],
                "target_threshold_id": experiment.get("target_threshold_id"),
                "variable_to_test": experiment.get("variable_to_test"),
                "experiment_type": experiment.get("experiment_type"),
                "steps": experiment.get("steps", []),
                "success_criteria": experiment.get("success_criteria", []),
                "failure_criteria": experiment.get("failure_criteria", []),
                "duration_days": experiment.get("duration_days"),
                "estimated_cost": experiment.get("estimated_cost"),
                "currency": experiment.get("currency"),
                "evidence_to_collect": experiment.get("evidence_to_collect", []),
                "decision_rule": experiment.get("decision_rule"),
                "expected_information_gain": experiment.get("expected_information_gain"),
                "confidence": experiment.get("confidence"),
                "feasibility": experiment.get("feasibility"),
                "reversibility": experiment.get("reversibility"),
                "related_assumption_ids": experiment.get("related_assumption_ids", []),
                "related_regret_scenario_ids": experiment.get("related_regret_scenario_ids", []),
                "status": ExperimentStatus(
                    experiment.get("status", ExperimentStatus.RECOMMENDED.value)
                ).value,
                "created_at": now,
                "updated_at": now,
            }
            self._gateway.put_item(item)
            created.append(Experiment.model_validate(_strip_keys(item)))

        return created

    def create_experiment_result(
        self, decision_id: UUID, experiment_id: UUID, result: dict[str, Any]
    ) -> StoredExperimentResult:
        """Persist the user-observed outcome of running an experiment.

        Takes a plain dict (outcome/summary/observations/measured_values/
        evidence_ids/notes/completed_at) rather than the wire
        `ExperimentResultCreate` model, for the same reason as the other
        `create_*` methods: this repository has no dependency on request
        schemas. The service layer is responsible for validating
        `evidence_ids` against real evidence before calling here. Stored
        under `SK=EXPERIMENT_RESULT#<experiment_id>#<result_id>` so all
        results for one experiment sort together, while still being
        listable decision-wide via a shared prefix scan.
        """
        now = datetime.now(UTC).isoformat()
        result_id = uuid4()
        item = {
            "PK": _decision_pk(decision_id),
            "SK": f"EXPERIMENT_RESULT#{experiment_id}#{result_id}",
            "entity_type": "EXPERIMENT_RESULT",
            "id": str(result_id),
            "decision_id": str(decision_id),
            "experiment_id": str(experiment_id),
            "outcome": ExperimentOutcome(result["outcome"]).value,
            "summary": result["summary"],
            "observations": result.get("observations", []),
            "measured_values": result.get("measured_values", {}),
            "evidence_ids": result.get("evidence_ids", []),
            "notes": result.get("notes"),
            "completed_at": result.get("completed_at") or now,
        }
        self._gateway.put_item(item)
        return StoredExperimentResult.model_validate(_strip_keys(item))

    def list_experiment_results(
        self, decision_id: UUID, experiment_id: UUID | None = None
    ) -> list[StoredExperimentResult]:
        """List experiment results for a decision, optionally scoped to one experiment."""
        prefix = (
            f"EXPERIMENT_RESULT#{experiment_id}#" if experiment_id is not None
            else "EXPERIMENT_RESULT#"
        )
        items = self._query_children(decision_id, prefix)
        return [StoredExperimentResult.model_validate(_strip_keys(item)) for item in items]

    def create_reevaluation(self, decision_id: UUID, reevaluation: dict[str, Any]) -> ReEvaluation:
        """Persist a re-evaluation record for a decision.

        Takes a plain dict rather than the agent-facing `ReEvaluation`
        model directly, for the same reason as the other `create_*`
        methods. Never overwrites the `AnalysisRun`, `Threshold`,
        `Assumption`, or `RegretScenario` records it references by id -
        this is always a new, additional entity, preserving the decision's
        full re-evaluation history. Stored under `SK=REEVALUATION#<id>`.
        """
        now = datetime.now(UTC).isoformat()
        reevaluation_id = uuid4()
        item = {
            "PK": _decision_pk(decision_id),
            "SK": f"REEVALUATION#{reevaluation_id}",
            "entity_type": "REEVALUATION",
            "id": str(reevaluation_id),
            "decision_id": str(decision_id),
            "experiment_id": reevaluation["experiment_id"],
            "experiment_result_id": reevaluation["experiment_result_id"],
            "previous_assessment": reevaluation["previous_assessment"],
            "new_assessment": reevaluation["new_assessment"],
            "threshold_comparisons": reevaluation.get("threshold_comparisons", []),
            "assumption_reevaluations": reevaluation.get("assumption_reevaluations", []),
            "regret_scenario_reevaluations": reevaluation.get(
                "regret_scenario_reevaluations", []
            ),
            "decision_assessment": DecisionAssessment.model_validate(
                reevaluation["decision_assessment"]
            ).model_dump(mode="json"),
            "changed_thresholds": reevaluation.get("changed_thresholds", []),
            "changed_assumptions": reevaluation.get("changed_assumptions", []),
            "changed_regret_scenarios": reevaluation.get("changed_regret_scenarios", []),
            "key_learning": reevaluation["key_learning"],
            "recommended_next_step": reevaluation["recommended_next_step"],
            "created_at": now,
        }
        self._gateway.put_item(item)
        return ReEvaluation.model_validate(_strip_keys(item))

    def list_reevaluations(self, decision_id: UUID) -> list[ReEvaluation]:
        """List every re-evaluation ever produced for a decision, oldest first.

        Nothing here is ever deleted or overwritten - this is the
        decision's full learning history (`Analysis -> Experiment ->
        Result -> Re-evaluation -> ...`), reconstructable end to end.
        """
        items = self._query_children(decision_id, "REEVALUATION#")
        return [ReEvaluation.model_validate(_strip_keys(item)) for item in items]

    def create_external_evidence(
        self, decision_id: UUID, findings: list[dict[str, Any]]
    ) -> list[ExternalEvidence]:
        """Persist Research Agent findings for a decision.

        Takes plain dicts (research_result_id/claim/source_url/
        source_name/support_level/credibility/related_assumption_ids/
        related_blindspot_ids/related_threshold_ids/explanation/excerpt/
        published_at/retrieved_at) rather than the agent's own
        `ExternalEvidence` model, for the same reason as the other
        `create_*` methods. Stored under
        `SK=EXTERNAL_EVIDENCE#<evidence_id>` - a distinct key space from
        user-uploaded `SK=EVIDENCE#<evidence_id>` records, so external
        research is never confused with, and never overwrites, evidence
        the user actually provided.
        """
        now = datetime.now(UTC).isoformat()
        created: list[ExternalEvidence] = []

        for finding in findings:
            evidence_id = uuid4()
            item = {
                "PK": _decision_pk(decision_id),
                "SK": f"EXTERNAL_EVIDENCE#{evidence_id}",
                "entity_type": "EXTERNAL_EVIDENCE",
                "id": str(evidence_id),
                "decision_id": str(decision_id),
                "research_result_id": finding["research_result_id"],
                "claim": finding["claim"],
                "source_url": finding["source_url"],
                "source_name": finding["source_name"],
                "support_level": finding.get("support_level"),
                "credibility": finding.get("credibility"),
                "related_assumption_ids": finding.get("related_assumption_ids", []),
                "related_blindspot_ids": finding.get("related_blindspot_ids", []),
                "related_threshold_ids": finding.get("related_threshold_ids", []),
                "explanation": finding.get("explanation"),
                "excerpt": finding.get("excerpt"),
                "published_at": finding.get("published_at"),
                "retrieved_at": finding["retrieved_at"],
                "created_at": now,
            }
            self._gateway.put_item(item)
            created.append(ExternalEvidence.model_validate(_strip_keys(item)))

        return created

    def list_external_evidence(self, decision_id: UUID) -> list[ExternalEvidence]:
        items = self._query_children(decision_id, "EXTERNAL_EVIDENCE#")
        return [ExternalEvidence.model_validate(_strip_keys(item)) for item in items]

    def get_experiment_by_id(self, experiment_id: UUID) -> Experiment | None:
        """Look up an experiment by its own id alone, without knowing its decision.

        Mirrors `EvidenceRepository.get_by_id` exactly - a bounded Query
        against GSI2, never a table-wide Scan.
        """
        items, _ = self._gateway.query(
            key_condition=Key("GSI2PK").eq(_experiment_gsi2pk(experiment_id)),
            index_name="GSI2",
            limit=1,
        )
        return Experiment.model_validate(_strip_keys(items[0])) if items else None

    def update_experiment_status(
        self,
        decision_id: UUID,
        experiment_id: UUID,
        status: ExperimentStatus,
        require_not_completed: bool = False,
    ) -> Experiment:
        """Transition an experiment's lifecycle status.

        The Experiment Planner always creates experiments as RECOMMENDED;
        this is the only path that moves one through
        PLANNED/ACTIVE/COMPLETED/CANCELLED afterward.

        `require_not_completed=True` adds a conditional-write guard so two
        concurrent "submit a result for this experiment" requests can't
        both succeed in marking it `completed` - the second one loses the
        race and raises `ConflictError` (see `DynamoDBGateway._run`),
        which `ReEvaluationService` turns into a clear rejection rather
        than silently producing two `ReEvaluation` records for the same
        experiment. Not used for other transitions (PLANNED/ACTIVE/
        CANCELLED), where a duplicate update is harmless.
        """
        now = datetime.now(UTC).isoformat()
        condition = Attr("PK").exists()
        if require_not_completed:
            condition = condition & Attr("status").ne(ExperimentStatus.COMPLETED.value)
        updated = self._gateway.update_item(
            key={"PK": _decision_pk(decision_id), "SK": f"EXPERIMENT#{experiment_id}"},
            update_expression="SET #status = :status, updated_at = :updated_at",
            expression_attribute_values={":status": status.value, ":updated_at": now},
            expression_attribute_names={"#status": "status"},
            condition=condition,
        )
        return Experiment.model_validate(_strip_keys(updated))

    # --- Child entity reads ---------------------------------------------------
    # None of these are exposed through public routes yet; they exist so the
    # future analysis pipeline has somewhere concrete to read from once it
    # starts writing blindspots/scenarios/thresholds/experiments.

    def list_assumptions(self, decision_id: UUID) -> list[Assumption]:
        items = self._query_children(decision_id, "ASSUMPTION#")
        return [Assumption.model_validate(_strip_keys(item)) for item in items]

    def list_blindspots(self, decision_id: UUID) -> list[Blindspot]:
        items = self._query_children(decision_id, "BLINDSPOT#")
        return [Blindspot.model_validate(_strip_keys(item)) for item in items]

    def list_evidence_findings(self, decision_id: UUID) -> list[StoredEvidenceFinding]:
        items = self._query_children(decision_id, "EVIDENCE_FINDING#")
        return [StoredEvidenceFinding.model_validate(_strip_keys(item)) for item in items]

    def list_challenges(self, decision_id: UUID) -> list[Challenge]:
        items = self._query_children(decision_id, "CHALLENGE#")
        return [Challenge.model_validate(_strip_keys(item)) for item in items]

    def list_regret_scenarios(self, decision_id: UUID) -> list[StoredRegretScenario]:
        items = self._query_children(decision_id, "REGRET_SCENARIO#")
        return [StoredRegretScenario.model_validate(_strip_keys(item)) for item in items]

    def list_scenarios(self, decision_id: UUID) -> list[Scenario]:
        items = self._query_children(decision_id, "SCENARIO#")
        return [Scenario.model_validate(_strip_keys(item)) for item in items]

    def list_thresholds(self, decision_id: UUID) -> list[Threshold]:
        items = self._query_children(decision_id, "THRESHOLD#")
        return [Threshold.model_validate(_strip_keys(item)) for item in items]

    def list_experiments(self, decision_id: UUID) -> list[Experiment]:
        items = self._query_children(decision_id, "EXPERIMENT#")
        return [Experiment.model_validate(_strip_keys(item)) for item in items]

    def _query_children(self, decision_id: UUID, sk_prefix: str) -> list[dict[str, Any]]:
        items, _ = self._gateway.query(
            key_condition=Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with(sk_prefix)
        )
        return items

    @staticmethod
    def to_response(item: dict[str, Any]) -> DecisionResponse:
        return DecisionResponse(
            id=item["id"],
            title=item["title"],
            description=item["description"],
            desired_outcome=item.get("desired_outcome"),
            budget=item.get("budget"),
            currency=item.get("currency"),
            timeline=item.get("timeline"),
            location=item.get("location"),
            risk_tolerance=item.get("risk_tolerance"),
            beliefs=item.get("beliefs"),
            status=item["status"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    """Drop DynamoDB key/index attributes before validating into a schema."""
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "entity_type"}
    }
