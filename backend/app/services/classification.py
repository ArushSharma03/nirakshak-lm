"""Summarize implemented checks without treating OCR gaps as package defects."""

from app.schemas.analysis import Analysis, ScreeningClassification


def classify(analysis: Analysis) -> ScreeningClassification:
    if analysis.profile.status != "selected" or not analysis.checks:
        return ScreeningClassification(reason=analysis.profile.reason or "Run declaration checks first.")
    checks = [c for c in analysis.checks.results if c.status != "not_applicable"]
    stable_fields = {f.field for f in analysis.fields if f.status == "observed"}
    complete_views = {view for view, result in analysis.views.items()
                      if any(run.provider == "xiaomi" and run.status == "ok" for run in result.ocr)}
    conflicts = {f.field for f in analysis.fields if f.status == "conflict"}
    for check in checks:
        if (check.status == "fail" and check.field in stable_fields
                and check.field in {"net_quantity", "mrp", "date"}
                and check.kind in {"completeness", "units"}
                and check.evidence and all(c.view in complete_views for c in check.evidence)):
            return ScreeningClassification(outcome="Potential Non-Compliance",
                reason=f"{check.field.replace('_', ' ').capitalize()}: {check.reason}")
    if checks and not conflicts and complete_views == set(analysis.views) and all(c.status == "pass" for c in checks):
        return ScreeningClassification(outcome="Compliant within Implemented Checks",
            reason="All applicable implemented checks passed for the supplied evidence.")
    return ScreeningClassification(reason="One or more checks need review. Verify conflicting, missing or unreadable declarations on the package.")
