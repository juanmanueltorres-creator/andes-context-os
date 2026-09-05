from __future__ import annotations

from dataclasses import dataclass

from andes_context_os.common import CONTRACT_VERSION, require_text
from andes_context_os.handoffs import SOURCE_FRESHNESS, QuestionResearchHandoff
from andes_context_os.research import ResearchActivity, ResearchDomain, ResearchIntent


@dataclass(frozen=True, slots=True)
class ResearchIntentPreview:
    source_question_ref: str
    source_decision_ref: str
    source_decision_fingerprint: str
    source_freshness: str
    question_raw: str
    question_canonical: str
    question_profile_ref: str | None
    domain: ResearchDomain
    activity: ResearchActivity
    goal: str
    constraints: tuple[str, ...]
    territory_hint: str | None
    territorial_scope_required: bool


def _optional_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    return require_text(value, field)


def preview_research_intent(
    handoff: QuestionResearchHandoff,
    *,
    domain: ResearchDomain,
    activity: ResearchActivity,
    goal: str,
    territory_hint: str | None = None,
) -> ResearchIntentPreview:
    if not isinstance(handoff, QuestionResearchHandoff):
        raise TypeError("handoff must be a QuestionResearchHandoff")
    if not isinstance(domain, ResearchDomain):
        raise TypeError("domain must be a ResearchDomain")
    if not isinstance(activity, ResearchActivity):
        raise TypeError("activity must be a ResearchActivity")

    return ResearchIntentPreview(
        source_question_ref=handoff.source.question_id,
        source_decision_ref=handoff.source.decision_id,
        source_decision_fingerprint=handoff.source.decision_fingerprint,
        source_freshness=SOURCE_FRESHNESS,
        question_raw=handoff.question.raw,
        question_canonical=handoff.question.canonical,
        question_profile_ref=handoff.source.question_profile_ref,
        domain=domain,
        activity=activity,
        goal=require_text(goal, "goal"),
        constraints=handoff.constraints,
        territory_hint=_optional_text(territory_hint, "territory_hint"),
        territorial_scope_required=True,
    )


def build_research_intent(
    preview: ResearchIntentPreview,
    *,
    intent_id: str,
    created_at: str,
) -> ResearchIntent:
    if not isinstance(preview, ResearchIntentPreview):
        raise TypeError("preview must be a ResearchIntentPreview")

    return ResearchIntent.from_dict(
        {
            "contract_version": CONTRACT_VERSION,
            "intent_id": intent_id,
            "question_raw": preview.question_raw,
            "question_canonical": preview.question_canonical,
            "question_profile_ref": preview.question_profile_ref,
            "domain": preview.domain.value,
            "activity": preview.activity.value,
            "goal": preview.goal,
            "constraints": list(preview.constraints),
            "territory_hint": preview.territory_hint,
            "created_at": created_at,
        }
    )
