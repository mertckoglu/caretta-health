"""Pydantic models for the Caretta REST API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.indicators import INDICATORS
from app.core.thresholds import DEFAULT_ENVIRONMENT, ENVIRONMENTS


class ReadingIn(BaseModel):
    astronaut_id: str = Field(..., min_length=1, max_length=32, examples=["CDR"])
    indicator: str = Field(..., examples=["heart_rate"])
    value: float = Field(..., examples=[64])
    ts: datetime | None = None
    environment: str = DEFAULT_ENVIRONMENT
    note: str | None = Field(None, max_length=500)

    @field_validator("indicator")
    @classmethod
    def _known_indicator(cls, v: str) -> str:
        if v not in INDICATORS:
            raise ValueError(f"unknown indicator, expected one of {sorted(INDICATORS)}")
        return v

    @field_validator("environment")
    @classmethod
    def _known_env(cls, v: str) -> str:
        if v not in ENVIRONMENTS:
            raise ValueError(f"unknown environment, expected one of {sorted(ENVIRONMENTS)}")
        return v


class ReadingOut(BaseModel):
    id: int
    astronaut_id: str
    ts: datetime
    indicator: str
    value: float
    environment: str
    note: str | None = None
    status: str


class IndicatorInfo(BaseModel):
    key: str
    name: str
    unit: str
    min_valid: float
    max_valid: float
    how_to_measure: str
    why_it_matters: str
    hazards: list[str]
    region: str
    thresholds: dict[str, list[tuple[float, float | None]]]  # None = no upper limit


class IndicatorStatusOut(BaseModel):
    indicator: str
    value: float | None
    status: str
    ts: str | None = None


class TrendAlertOut(BaseModel):
    indicator: str
    status: str
    title: str
    message: str


class RecommendationOut(BaseModel):
    indicator: str
    status: str
    title: str
    actions: list[str]
    contact: str
    escalate: bool


class StatusReport(BaseModel):
    astronaut_id: str
    environment: str
    overall: str
    escalate: bool
    escalation_reasons: list[str]
    indicators: list[IndicatorStatusOut]
    regions: dict[str, str]
    alerts: list[TrendAlertOut]
    recommendations: list[RecommendationOut]
    cumulative_dose_msv: float


class SimulateRequest(BaseModel):
    astronaut_id: str = Field("CDR", min_length=1, max_length=32)
    days: int = Field(30, ge=1, le=365)
    environment: str = DEFAULT_ENVIRONMENT
    seed: int = 42
    replace: bool = True

    @field_validator("environment")
    @classmethod
    def _known_env(cls, v: str) -> str:
        if v not in ENVIRONMENTS:
            raise ValueError(f"unknown environment, expected one of {sorted(ENVIRONMENTS)}")
        return v


class SimulateResult(BaseModel):
    astronaut_id: str
    inserted: int
