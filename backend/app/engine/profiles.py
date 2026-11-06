"""Dated, validated rule data selection, independent of model recommendations."""

import json
from datetime import date
from pathlib import Path
from pydantic import BaseModel, model_validator
from app.schemas.analysis import Profile, ProfileRequest, Rule

RULES_FILE = Path(__file__).resolve().parents[3] / "rules" / "food_grocery.json"


class RuleSet(BaseModel):
    id: str
    version: str
    category: str
    effective_from: date
    effective_to: date | None = None
    review_status: str
    rules: list[Rule]

    @model_validator(mode="after")
    def unique_versions(self):
        for index, rule in enumerate(self.rules):
            if rule.effective_to and rule.effective_to <= rule.effective_from:
                raise ValueError("Rule end date must follow start date")
            for other in self.rules[:index]:
                if rule.id == other.id and set(rule.origins) & set(other.origins):
                    if rule.effective_from < (other.effective_to or date.max) and other.effective_from < (rule.effective_to or date.max):
                        raise ValueError("Overlapping rule versions")
        return self


def load_rules() -> RuleSet:
    return RuleSet.model_validate(json.loads(RULES_FILE.read_text()))


def select_profile(request: ProfileRequest, ruleset: RuleSet | None = None) -> Profile:
    data = ruleset or load_rules()
    if request.category != data.category:
        return Profile(status="unsupported", inputs=request, reason="MVP rule data covers food_grocery only.")
    if request.as_of < data.effective_from or (data.effective_to and request.as_of >= data.effective_to):
        return Profile(status="unsupported", inputs=request, reason="No profile data for this date.")
    if request.origin == "unknown":
        return Profile(status="review_required", inputs=request, reason="Confirm domestic or imported origin before profile selection.")
    rules = [r for r in data.rules if request.origin in r.origins and r.effective_from <= request.as_of
             and (r.effective_to is None or request.as_of < r.effective_to)]
    return Profile(status="selected", id=data.id, version=data.version, inputs=request, rules=rules,
        reason=f"Selected by category, declared origin and date. Rule data review status: {data.review_status}.")
