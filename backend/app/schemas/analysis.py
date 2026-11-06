"""Evidence contracts use original-image pixel coordinates throughout."""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

View = Literal["front", "rear", "side"]
FieldName = Literal["generic_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin"]


class Box(BaseModel):
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(gt=0)
    y1: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("Bounding box must have positive width and height")
        return self


class OCRWord(BaseModel):
    text: str
    box: Box
    confidence: float = Field(ge=0, le=1)


class OCRLine(BaseModel):
    text: str
    box: Box | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    words: list[OCRWord] = Field(default_factory=list)


class OCRResult(BaseModel):
    provider: str
    model: str
    status: Literal["ok", "unavailable", "failed"]
    lines: list[OCRLine] = Field(default_factory=list)
    message: str = ""


class Calibration(BaseModel):
    status: Literal["available", "unavailable"]
    reason: str
    marker_mm: float = 50
    pixels_per_mm: float | None = None
    homography: list[list[float]] | None = None


class Candidate(BaseModel):
    field: FieldName
    value: str
    view: View
    provider: str
    source_text: str
    box: Box | None = None
    confidence: float | None = None
    height_mm: float | None = None


class FusedField(BaseModel):
    field: FieldName
    status: Literal["observed", "conflict", "missing"]
    value: str | None = None
    evidence: list[Candidate] = Field(default_factory=list)
    reason: str


class ProfileRequest(BaseModel):
    category: Literal["food_grocery", "beverage", "personal_care", "household"]
    origin: Literal["domestic", "imported", "unknown"] = "unknown"
    as_of: date


class Rule(BaseModel):
    id: str
    version: str
    citation: str
    field: FieldName
    requirement: str
    effective_from: date
    effective_to: date | None = None
    origins: list[Literal["domestic", "imported"]]
    source_url: str


class Profile(BaseModel):
    status: Literal["selected", "review_required", "unsupported"]
    id: str | None = None
    version: str | None = None
    reason: str
    inputs: ProfileRequest
    rules: list[Rule] = Field(default_factory=list)
    advisory: str = "Profile selection only. Declarations have not been legally verified."


class AnalysisRequest(BaseModel):
    origin: Literal["domestic", "imported", "unknown"] = "unknown"
    as_of: date
    coplanar_views: list[View] = Field(default_factory=list)
    use_jev: bool = False


class DecisionAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]


class DecisionResult(BaseModel):
    status: Literal["ok", "unavailable", "failed", "not_needed"]
    model: str
    answers: dict[str, DecisionAnswer] = Field(default_factory=dict)
    message: str
    usage: dict[str, int] = Field(default_factory=dict)


class ViewAnalysis(BaseModel):
    file_hash: str
    calibration: Calibration
    ocr: list[OCRResult]


class Analysis(BaseModel):
    version: str = "1.0.0"
    views: dict[View, ViewAnalysis]
    fields: list[FusedField]
    profile: Profile
    warnings: list[str]
    decision: DecisionResult
