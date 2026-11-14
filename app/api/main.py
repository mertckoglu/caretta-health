"""Caretta REST API.

Lets wearables, onboard medical devices or the ground segment push readings
and pull an assessment. Run with::

    uvicorn app.api.main:app --reload

Interactive docs at http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.api import db
from app.api.schemas import (
    IndicatorInfo,
    ReadingIn,
    ReadingOut,
    RecommendationOut,
    SimulateRequest,
    SimulateResult,
    StatusReport,
)
from app.core.indicators import HAZARDS, INDICATORS, REGIONS
from app.core.recommend import downlink_report, recommendations_for
from app.core.simulate import simulate_mission
from app.core.status import (
    cumulative_dose,
    detect_trends,
    evaluate_latest,
    needs_flight_surgeon,
    overall_status,
    region_status,
)
from app.core.thresholds import DEFAULT_ENVIRONMENT, ENVIRONMENTS, classify, get_thresholds


def _finite(x: float) -> float | None:
    return None if math.isinf(x) else x


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(
        title="Caretta API",
        version="1.0.0",
        description="Astronaut self-assessment: readings in, traffic-light status and guidance out.",
    )

    def get_conn() -> Iterator[sqlite3.Connection]:
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _env(environment: str) -> str:
        if environment not in ENVIRONMENTS:
            raise HTTPException(422, f"unknown environment {environment!r}")
        return environment

    def _build_report(conn, astronaut_id: str, environment: str, days: int):
        since = datetime.now() - timedelta(days=days)
        df = db.fetch_readings(conn, astronaut_id, since=since, environment=environment)
        if df.empty:
            raise HTTPException(
                404, f"no readings for astronaut {astronaut_id!r} in {environment!r} in the last {days} days"
            )
        statuses = evaluate_latest(df, environment)
        alerts = detect_trends(df, environment)
        recs = recommendations_for(statuses, alerts, environment)
        return df, statuses, alerts, recs

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "service": "caretta", "time": datetime.now().isoformat(timespec="seconds")}

    @app.get("/environments", tags=["reference"])
    def environments() -> dict:
        return ENVIRONMENTS

    @app.get("/hazards", tags=["reference"])
    def hazards() -> dict:
        return HAZARDS

    @app.get("/regions", tags=["reference"])
    def regions() -> dict:
        return REGIONS

    @app.get("/indicators", response_model=list[IndicatorInfo], tags=["reference"])
    def indicators(environment: str = DEFAULT_ENVIRONMENT) -> list[IndicatorInfo]:
        _env(environment)
        out = []
        for ind in INDICATORS.values():
            th = get_thresholds(ind.key, environment)
            out.append(
                IndicatorInfo(
                    key=ind.key,
                    name=ind.name,
                    unit=ind.unit,
                    min_valid=ind.min_valid,
                    max_valid=ind.max_valid,
                    how_to_measure=ind.how_to_measure,
                    why_it_matters=ind.why_it_matters,
                    hazards=list(ind.hazards),
                    region=ind.region,
                    thresholds={k: [(lo, _finite(hi)) for lo, hi in v] for k, v in th.items()},
                )
            )
        return out

    @app.post("/readings", response_model=ReadingOut, status_code=201, tags=["readings"])
    def add_reading(reading: ReadingIn, conn=Depends(get_conn)) -> ReadingOut:
        try:
            rid = db.insert_reading(
                conn,
                reading.astronaut_id,
                reading.indicator,
                reading.value,
                reading.ts,
                reading.environment,
                reading.note,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        row = conn.execute("SELECT * FROM readings WHERE id = ?", (rid,)).fetchone()
        return ReadingOut(**dict(row), status=classify(row["indicator"], row["value"], row["environment"]))

    @app.get("/readings", response_model=list[ReadingOut], tags=["readings"])
    def list_readings(
        astronaut_id: str | None = None,
        indicator: str | None = None,
        environment: str | None = None,
        days: int = Query(30, ge=1, le=3650),
        conn=Depends(get_conn),
    ) -> list[ReadingOut]:
        df = db.fetch_readings(conn, astronaut_id, datetime.now() - timedelta(days=days), indicator, environment)
        return [
            ReadingOut(
                **{**r, "note": r["note"] if isinstance(r["note"], str) else None},
                status=classify(r["indicator"], r["value"], r["environment"]),
            )
            for r in df.to_dict("records")
        ]

    @app.delete("/readings/{reading_id}", status_code=204, tags=["readings"])
    def remove_reading(reading_id: int, conn=Depends(get_conn)) -> None:
        if not db.delete_reading(conn, reading_id):
            raise HTTPException(404, "reading not found")

    @app.get("/astronauts", tags=["readings"])
    def astronauts(environment: str | None = None, conn=Depends(get_conn)) -> list[str]:
        return db.list_astronauts(conn, environment)

    @app.get("/status/{astronaut_id}", response_model=StatusReport, tags=["assessment"])
    def status(
        astronaut_id: str,
        environment: str = DEFAULT_ENVIRONMENT,
        days: int = Query(30, ge=1, le=3650),
        conn=Depends(get_conn),
    ) -> StatusReport:
        _env(environment)
        df, statuses, alerts, recs = _build_report(conn, astronaut_id, environment, days)
        escalate, reasons = needs_flight_surgeon(statuses, alerts)
        return StatusReport(
            astronaut_id=astronaut_id,
            environment=environment,
            overall=overall_status(statuses, alerts),
            escalate=escalate,
            escalation_reasons=reasons,
            indicators=[s.to_dict() for s in statuses.values()],
            regions=region_status(statuses, alerts),
            alerts=[a.to_dict() for a in alerts],
            recommendations=[r.to_dict() for r in recs],
            cumulative_dose_msv=round(cumulative_dose(df), 2),
        )

    @app.get("/recommendations/{astronaut_id}", response_model=list[RecommendationOut], tags=["assessment"])
    def recommendations(
        astronaut_id: str, environment: str = DEFAULT_ENVIRONMENT, conn=Depends(get_conn)
    ) -> list[RecommendationOut]:
        _env(environment)
        _, _, _, recs = _build_report(conn, astronaut_id, environment, 30)
        return [RecommendationOut(**r.to_dict()) for r in recs]

    @app.get("/report/{astronaut_id}", response_class=PlainTextResponse, tags=["assessment"])
    def report(astronaut_id: str, environment: str = DEFAULT_ENVIRONMENT, conn=Depends(get_conn)) -> str:
        _env(environment)
        df, statuses, alerts, recs = _build_report(conn, astronaut_id, environment, 30)
        return downlink_report(astronaut_id, environment, statuses, alerts, recs, cumulative_dose(df))

    @app.post("/simulate", response_model=SimulateResult, status_code=201, tags=["demo"])
    def simulate(req: SimulateRequest, conn=Depends(get_conn)) -> SimulateResult:
        if req.replace:
            db.delete_astronaut(conn, req.astronaut_id, req.environment)
        df = simulate_mission(req.days, req.astronaut_id, req.environment, req.seed)
        return SimulateResult(astronaut_id=req.astronaut_id, inserted=db.insert_dataframe(conn, df))

    return app


app = create_app()
