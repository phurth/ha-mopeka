"""Mopeka data model."""

from __future__ import annotations

from dataclasses import dataclass
import time

from .const import MediumType


@dataclass(slots=True)
class MopekaSensorData:
    """Parsed data from a Mopeka advertisement."""

    mac_address: str
    model_id: int
    model_name: str
    battery_percent: int
    distance_raw_mm: int
    compensated_distance_mm: int
    temperature_c: int
    quality_percent: int
    quality_raw: int
    accelerometer_x: int
    accelerometer_y: int
    tank_level_percent: float
    medium_type: MediumType
    tank_type: str
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()
