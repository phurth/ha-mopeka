"""Constants for the Mopeka BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

DOMAIN = "ha_mopeka"

CONF_MEDIUM_TYPE = "medium_type"
CONF_TANK_TYPE = "tank_type"
CONF_MINIMUM_QUALITY = "minimum_quality"

MANUFACTURER_ID = 0x0059
SERVICE_UUID = "0000fee5-0000-1000-8000-00805f9b34fb"

DATA_HEALTH_TIMEOUT_SECONDS = 120
OFFLINE_TIMEOUT_SECONDS = 30 * 60

QUALITY_THRESHOLDS = (0, 20, 50, 80)

SYNC_BYTE_TO_MODEL: dict[int, str] = {
    0x03: "Pro Plus (M1015)",
    0x04: "Pro Check (M1017)",
    0x05: "Pro 200",
    0x08: "Pro H2O",
    0x09: "Pro H2O Plus",
    0x0A: "Lippert BottleCheck",
    0x0B: "TD40",
    0x0C: "TD200",
}


class MediumType(str, Enum):
    """Supported medium types for compensation."""

    PROPANE = "propane"
    AIR = "air"
    FRESH_WATER = "fresh_water"
    WASTE_WATER = "waste_water"
    BLACK_WATER = "black_water"
    LIVE_WELL = "live_well"
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    LNG = "lng"
    OIL = "oil"
    HYDRAULIC_OIL = "hydraulic_oil"
    CUSTOM = "custom"


class TankOrientation(str, Enum):
    """Tank orientation."""

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


@dataclass(frozen=True)
class TankSpec:
    """Tank geometry specification."""

    id: str
    name: str
    orientation: TankOrientation
    overall_length_mm: float
    overall_diameter_mm: float
    wall_thickness_mm: float = 3.175

    @property
    def internal_diameter_mm(self) -> float:
        return self.overall_diameter_mm - (2 * self.wall_thickness_mm)

    @property
    def radius_mm(self) -> float:
        return self.internal_diameter_mm / 2.0

    @property
    def side_length_mm(self) -> float:
        if self.orientation is TankOrientation.VERTICAL:
            return self.overall_length_mm - (self.internal_diameter_mm / 2.0)
        return self.overall_length_mm - self.overall_diameter_mm


TANK_SPECS: dict[str, TankSpec] = {
    "20lb_v": TankSpec("20lb_v", "20lb Vertical", TankOrientation.VERTICAL, 316.0, 304.8),
    "30lb_v": TankSpec("30lb_v", "30lb Vertical", TankOrientation.VERTICAL, 422.0, 304.8),
    "40lb_v": TankSpec("40lb_v", "40lb Vertical", TankOrientation.VERTICAL, 457.0, 304.8),
    "250gal_h": TankSpec("250gal_h", "250 Gallon Horizontal", TankOrientation.HORIZONTAL, 2387.6, 762.0),
    "500gal_h": TankSpec("500gal_h", "500 Gallon Horizontal", TankOrientation.HORIZONTAL, 3022.6, 952.5),
    "1000gal_h": TankSpec("1000gal_h", "1000 Gallon Horizontal", TankOrientation.HORIZONTAL, 4877.5, 1041.4),
    "europe_6kg": TankSpec("europe_6kg", "6kg European Vertical", TankOrientation.VERTICAL, 340.0, 240.0),
    "europe_11kg": TankSpec("europe_11kg", "11kg European Vertical", TankOrientation.VERTICAL, 390.0, 290.0),
    "europe_14kg": TankSpec("europe_14kg", "14kg European Vertical", TankOrientation.VERTICAL, 430.0, 290.0),
    "custom": TankSpec("custom", "Custom Tank", TankOrientation.VERTICAL, 300.0, 300.0),
}


COMPENSATION_COEFFICIENTS: dict[MediumType, tuple[float, float, float]] = {
    MediumType.PROPANE: (0.573045, -0.002822, -0.00000535),
    MediumType.AIR: (0.153096, 0.000327, -0.000000294),
    MediumType.FRESH_WATER: (0.600592, 0.003124, -0.00001368),
    MediumType.WASTE_WATER: (0.600592, 0.003124, -0.00001368),
    MediumType.LIVE_WELL: (0.600592, 0.003124, -0.00001368),
    MediumType.BLACK_WATER: (0.600592, 0.003124, -0.00001368),
    MediumType.GASOLINE: (0.7373417462, -0.001978229885, 0.00000202162),
    MediumType.DIESEL: (0.7373417462, -0.001978229885, 0.00000202162),
    MediumType.LNG: (0.7373417462, -0.001978229885, 0.00000202162),
    MediumType.OIL: (0.7373417462, -0.001978229885, 0.00000202162),
    MediumType.HYDRAULIC_OIL: (0.7373417462, -0.001978229885, 0.00000202162),
    MediumType.CUSTOM: (0.573045, -0.002822, -0.00000535),
}


def apply_temperature_compensation(distance_raw_mm: int, temp_raw: int, medium_type: MediumType) -> int:
    """Apply medium-specific temperature compensation to distance."""
    c0, c1, c2 = COMPENSATION_COEFFICIENTS[medium_type]
    factor = c0 + (c1 * temp_raw) + (c2 * temp_raw * temp_raw)
    return int(distance_raw_mm * factor)


def calculate_tank_percentage(tank_type: str, measured_depth_mm: float) -> float:
    """Calculate tank percentage using geometry formulas from Android plugin."""
    spec = TANK_SPECS.get(tank_type, TANK_SPECS["20lb_v"])
    fill_depth = measured_depth_mm - spec.wall_thickness_mm
    if fill_depth < 0:
        return 0.0
    radius = spec.radius_mm
    side_length = spec.side_length_mm
    if spec.orientation is TankOrientation.VERTICAL:
        return _calculate_vertical(fill_depth, radius, side_length)
    return _calculate_horizontal(fill_depth, radius, side_length)


def _calculate_vertical(fill_depth: float, radius: float, side_length: float) -> float:
    pi = math.pi
    ellipsoid_a = radius
    ellipsoid_b = radius
    ellipsoid_c = radius / 2.0
    tank_height = side_length + ellipsoid_c
    if fill_depth > tank_height:
        return 100.0
    hemi_ellipsoid_volume = (2.0 / 3.0) * pi * ellipsoid_a * ellipsoid_b * ellipsoid_c
    cylinder_volume = side_length * pi * radius * radius
    max_volume = 2 * hemi_ellipsoid_volume + cylinder_volume

    if 0.0 <= fill_depth <= ellipsoid_c:
        fill_volume = pi * ellipsoid_a * ellipsoid_b * (
            (2.0 / 3.0 * ellipsoid_c)
            - ellipsoid_c
            + fill_depth
            + ((ellipsoid_c - fill_depth) ** 3 / (3.0 * ellipsoid_c * ellipsoid_c))
        )
    elif ellipsoid_c <= fill_depth <= (ellipsoid_c + side_length):
        fill_volume = hemi_ellipsoid_volume + (fill_depth - ellipsoid_c) * pi * radius * radius
    elif (ellipsoid_c + side_length) <= fill_depth <= tank_height:
        top_depth = tank_height - fill_depth
        fill_volume = max_volume - (
            pi
            * ellipsoid_a
            * ellipsoid_b
            * (
                (2.0 / 3.0 * ellipsoid_c)
                - ellipsoid_c
                + top_depth
                + ((ellipsoid_c - top_depth) ** 3 / (3.0 * ellipsoid_c * ellipsoid_c))
            )
        )
    else:
        return 0.0
    if fill_volume < 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * fill_volume / max_volume))


def _calculate_horizontal(fill_depth: float, radius: float, side_length: float) -> float:
    pi = math.pi
    if fill_depth > 2 * radius:
        return 100.0
    if fill_depth < 0:
        return 0.0
    spherical_volume = (4.0 / 3.0) * pi * radius * radius * radius
    cylinder_volume = side_length * pi * radius * radius
    max_volume = spherical_volume + cylinder_volume

    fill_spherical = (pi / 3.0) * fill_depth * fill_depth * (3 * radius - fill_depth)
    fill_cylinder = side_length * (
        radius * radius * math.acos((radius - fill_depth) / radius)
        - (radius - fill_depth)
        * math.sqrt(max(0.0, 2 * radius * fill_depth - fill_depth * fill_depth))
    )
    fill_volume = fill_spherical + fill_cylinder
    return max(0.0, min(100.0, 100.0 * fill_volume / max_volume))
