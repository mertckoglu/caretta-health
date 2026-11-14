"""Evaluates health indicators and produces a health status.

Threshold values are illustrative/educational only; for real medical use they
must be replaced with protocols approved by the flight surgeon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from math import inf
from typing import Mapping, Optional

Range = tuple[float, float]


class Level(IntEnum):
    """Severity level. Comparable numerically (CRITICAL > WARNING)."""

    NORMAL = 0
    WATCH = 1
    WARNING = 2
    CRITICAL = 3


@dataclass(frozen=True)
class Bands:
    """Nested ranges. The level is that of the first range containing the value (bounds inclusive)."""

    category: str
    normal: Range
    watch: Range
    warning: Range
    # Anything outside the warning range is CRITICAL.


THRESHOLDS: dict[str, Bands] = {
    "heart_rate": Bands("cardiovascular", (50, 90), (45, 100), (40, 120)),
    "systolic_bp": Bands("cardiovascular", (90, 130), (85, 140), (80, 160)),
    "diastolic_bp": Bands("cardiovascular", (60, 85), (55, 90), (50, 100)),
    "spo2": Bands("cardiovascular", (95, inf), (93, inf), (90, inf)),
    "body_temp": Bands("immune", (36.1, 37.5), (35.8, 37.9), (35.0, 38.5)),
    "daily_exercise_min": Bands("musculoskeletal", (30, inf), (15, inf), (5, inf)),
    "sleep_hours": Bands("behavioral", (6.5, inf), (5.5, inf), (4.0, inf)),
    "mood": Bands("behavioral", (3, inf), (2.5, inf), (1.5, inf)),  # 1-5 scale
    "stress": Bands("behavioral", (-inf, 5), (-inf, 6.5), (-inf, 8)),  # 0-10 scale
    "daily_radiation_msv": Bands("radiation", (-inf, 1.0), (-inf, 1.5), (-inf, 3.0)),
}


@dataclass(frozen=True)
class MetricStatus:
    name: str
    value: float
    level: Level
    category: str
    direction: Optional[str] = None  # "low", "high", or None (if normal)


@dataclass
class HealthStatus:
    metrics: dict[str, MetricStatus] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)

    @property
    def overall(self) -> Level:
        if not self.metrics:
            return Level.NORMAL
        return max(m.level for m in self.metrics.values())

    def by_category(self) -> dict[str, Level]:
        """Worst level for each category (cardiovascular, immune, ...)."""
        result: dict[str, Level] = {}
        for m in self.metrics.values():
            result[m.category] = max(result.get(m.category, Level.NORMAL), m.level)
        return result

    def abnormal(self) -> list[MetricStatus]:
        """Non-NORMAL metrics, most severe first."""
        items = [m for m in self.metrics.values() if m.level > Level.NORMAL]
        return sorted(items, key=lambda m: (-m.level, m.name))


def _inside(value: float, rng: Range) -> bool:
    return rng[0] <= value <= rng[1]


def evaluate_metric(name: str, value: float) -> MetricStatus:
    """Evaluate a single indicator. Raises KeyError for an unknown name."""
    if value is None or value != value:  # None or NaN
        raise ValueError(f"{name}: invalid value")
    bands = THRESHOLDS[name]

    if _inside(value, bands.normal):
        level = Level.NORMAL
    elif _inside(value, bands.watch):
        level = Level.WATCH
    elif _inside(value, bands.warning):
        level = Level.WARNING
    else:
        level = Level.CRITICAL

    direction = None
    if level != Level.NORMAL:
        direction = "low" if value < bands.normal[0] else "high"
    return MetricStatus(name, value, level, bands.category, direction)


def evaluate_all(readings: Mapping[str, float]) -> HealthStatus:
    """Evaluate a dict of readings (e.g. {"heart_rate": 72}) in one go.

    Unknown keys do not raise; they are added to `unknown`.
    Metrics whose value is None (not measured) are skipped.
    """
    status = HealthStatus()
    for name, value in readings.items():
        if name not in THRESHOLDS:
            status.unknown.append(name)
            continue
        if value is None:
            continue
        status.metrics[name] = evaluate_metric(name, value)
    return status