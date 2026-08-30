from __future__ import annotations

from andes_context_os.internal_context import (
    ContextSelection,
    ContextSensitivity,
    InternalContextCatalog,
    InternalContextRecord,
    InternalContextSnapshot,
    MatchReason,
)
from andes_context_os.research import ResearchIntent, TerritorialScope

NO_MATCH_MESSAGE = "no internal context matched the current intent and territorial scope"
RESTRICTED_OMISSION_MESSAGE = "restricted internal context was omitted"


def _scope_refs(scope: TerritorialScope) -> frozenset[str]:
    refs = {f"country:{country}" for country in scope.countries}
    refs.update(
        f"admin:{unit.country_code}:{unit.admin_level}:{unit.official_code}"
        for unit in scope.admin_units
        if unit.official_code is not None
    )
    refs.update(f"project:{ref}" for ref in scope.project_refs)
    refs.update(f"corridor:{ref}" for ref in scope.corridor_refs)
    refs.update(f"segment:{ref}" for ref in scope.segment_refs)
    if scope.geometry_ref is not None:
        refs.add(f"geometry:{scope.geometry_ref}")
    return frozenset(refs)


def _match_reasons(
    record: InternalContextRecord,
    intent: ResearchIntent,
    scope_refs: frozenset[str],
) -> tuple[MatchReason, ...]:
    reasons: list[MatchReason] = []
    if intent.domain in record.domains:
        reasons.append(MatchReason.DOMAIN_MATCH)
    if intent.activity in record.activities:
        reasons.append(MatchReason.ACTIVITY_MATCH)
    if set(record.territory_refs) & scope_refs:
        reasons.append(MatchReason.TERRITORY_MATCH)
    return tuple(sorted(reasons, key=lambda item: item.value))


def _eligible(record: InternalContextRecord, reasons: tuple[MatchReason, ...]) -> bool:
    reason_set = set(reasons)
    territory_match = MatchReason.TERRITORY_MATCH in reason_set
    territorial_gate = not record.territory_refs or territory_match
    semantic_gate = (
        bool(reason_set & {MatchReason.DOMAIN_MATCH, MatchReason.ACTIVITY_MATCH})
        if record.domains or record.activities
        else territory_match
    )
    return territorial_gate and semantic_gate


class InternalContextAdapter:
    def snapshot(
        self,
        intent: ResearchIntent,
        scope: TerritorialScope,
        catalog: InternalContextCatalog,
        *,
        generated_at: str,
    ) -> InternalContextSnapshot:
        scope_refs = _scope_refs(scope)
        selections: list[ContextSelection] = []
        restricted_omitted = False
        for item in catalog.records:
            reasons = _match_reasons(item, intent, scope_refs)
            if not _eligible(item, reasons):
                continue
            if item.sensitivity is ContextSensitivity.RESTRICTED:
                restricted_omitted = True
                continue
            selections.append(ContextSelection.from_record(item, reasons))

        missing: list[str] = []
        if not selections:
            missing.append(NO_MATCH_MESSAGE)
        if restricted_omitted:
            missing.append(RESTRICTED_OMISSION_MESSAGE)

        return InternalContextSnapshot.build(
            generated_at=generated_at,
            research_intent_id=intent.intent_id,
            question_profile_ref=intent.question_profile_ref,
            territorial_scope_id=scope.scope_id,
            selections=tuple(selections),
            missing_context=tuple(missing),
        )
