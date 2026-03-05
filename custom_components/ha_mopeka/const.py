"""Constants for the Mopeka BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DOMAIN = "ha_mopeka"

CONF_MEDIUM_TYPE = "medium_type"
CONF_TANK_TYPE = "tank_type"
CONF_CUSTOM_TANK_HEIGHT_MM = "custom_tank_height_mm"

MANUFACTURER_ID = 0x0059
SERVICE_UUID = "0000fee5-0000-1000-8000-00805f9b34fb"

DATA_HEALTH_TIMEOUT_SECONDS = 120
OFFLINE_TIMEOUT_SECONDS = 30 * 60

# Sensor dead-zone floor for propane vertical tanks (Mopeka empirical constant).
# Readings at or below this level represent an empty tank.
PROPANE_MIN_OFFSET_MM = 38.1

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


class TankShape(str, Enum):
    """Tank shape — determines which percentage formula is applied.

    VERTICAL_CYLINDER:
        Upright propane/gas bottles. Uses Mopeka's linear formula with a
        dead-zone offset at the bottom (PROPANE_MIN_OFFSET_MM).
        height_mm = calibrated usable sensor range (empirical, matches official app).

    HORIZONTAL_CYLINDER:
        Permanently-mounted horizontal propane/gas tanks (RV, residential).
        Uses a cubic-polynomial approximation of the circular-segment fill
        formula (matches official Mopeka app).
        height_mm = tank interior diameter.

    RECTANGULAR:
        Fresh/grey/black water tanks and other non-cylindrical vessels.
        Pure linear fill with no dead-zone offset.
        height_mm = usable interior depth.
    """

    VERTICAL_CYLINDER = "vertical_cylinder"
    HORIZONTAL_CYLINDER = "horizontal_cylinder"
    RECTANGULAR = "rectangular"


_VERT = TankShape.VERTICAL_CYLINDER
_HORIZ = TankShape.HORIZONTAL_CYLINDER
_RECT = TankShape.RECTANGULAR

# Tank-type keys whose height is user-supplied via the custom_dimensions config step.
CUSTOM_TANK_KEYS: frozenset[str] = frozenset({"custom", "custom_horizontal", "custom_rectangular"})


@dataclass(frozen=True)
class TankSpec:
    """Tank specification for percentage calculation.

    height_mm semantics differ by shape — see TankShape docstring.
    min_offset_mm is only used by VERTICAL_CYLINDER (propane dead-zone).
    """

    id: str
    name: str
    shape: TankShape
    height_mm: float
    min_offset_mm: float = PROPANE_MIN_OFFSET_MM


TANK_SPECS: dict[str, TankSpec] = {
    # ── North America: vertical propane ──────────────────────────────────────
    # height values are Mopeka's empirically calibrated sensor ranges
    # (10 / 15 / 20 / 32 inch fill depths respectively)
    "20lb_v":    TankSpec("20lb_v",    "20 lb Vertical",          _VERT,   254.0),
    "30lb_v":    TankSpec("30lb_v",    "30 lb Vertical",          _VERT,   381.0),
    "40lb_v":    TankSpec("40lb_v",    "40 lb Vertical",          _VERT,   508.0),
    "100lb_v":   TankSpec("100lb_v",   "100 lb Vertical",         _VERT,   812.8),
    # 120-gal vertical: max sensor range = 80% of 48 in physical height (Mopeka note)
    "120gal_v":  TankSpec("120gal_v",  "120 gal Vertical",        _VERT,   974.0),
    # ── North America: horizontal propane ────────────────────────────────────
    # height = interior diameter (used in circular-segment formula)
    "120gal_h":  TankSpec("120gal_h",  "120 gal Horizontal",      _HORIZ,  609.6,  min_offset_mm=0.0),
    "150gal_h":  TankSpec("150gal_h",  "150 gal Horizontal",      _HORIZ,  609.6,  min_offset_mm=0.0),
    "250gal_h":  TankSpec("250gal_h",  "250 gal Horizontal",      _HORIZ,  762.0,  min_offset_mm=0.0),
    "500gal_h":  TankSpec("500gal_h",  "500 gal Horizontal",      _HORIZ,  939.8,  min_offset_mm=0.0),
    "1000gal_h": TankSpec("1000gal_h", "1000 gal Horizontal",     _HORIZ, 1041.4,  min_offset_mm=0.0),
    # ── Europe: vertical propane (approximate heights) ───────────────────────
    "europe_6kg":  TankSpec("europe_6kg",  "6 kg Vertical (EU)",  _VERT,   340.0),
    "europe_11kg": TankSpec("europe_11kg", "11 kg Vertical (EU)", _VERT,   390.0),
    "europe_14kg": TankSpec("europe_14kg", "14 kg Vertical (EU)", _VERT,   430.0),
    # ── Custom: user supplies height via config flow ──────────────────────────
    "custom":            TankSpec("custom",            "Custom Vertical Cylinder",   _VERT,  300.0),
    "custom_horizontal": TankSpec("custom_horizontal", "Custom Horizontal Cylinder", _HORIZ, 600.0,  min_offset_mm=0.0),
    "custom_rectangular": TankSpec("custom_rectangular", "Custom Rectangular",       _RECT,  300.0,  min_offset_mm=0.0),
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


def calculate_tank_percentage(
    tank_type: str,
    measured_depth_mm: float,
    custom_height_mm: float | None = None,
) -> float:
    """Calculate tank fill percentage.

    For custom tank types, custom_height_mm overrides the placeholder height
    stored in TANK_SPECS.
    """
    spec = TANK_SPECS.get(tank_type, TANK_SPECS["20lb_v"])
    height_mm = (
        custom_height_mm
        if (tank_type in CUSTOM_TANK_KEYS and custom_height_mm is not None and custom_height_mm > 0)
        else spec.height_mm
    )
    if spec.shape is TankShape.VERTICAL_CYLINDER:
        return _calculate_vertical_cylinder(measured_depth_mm, height_mm, spec.min_offset_mm)
    if spec.shape is TankShape.HORIZONTAL_CYLINDER:
        return _calculate_horizontal_cylinder(measured_depth_mm, height_mm)
    return _calculate_rectangular(measured_depth_mm, height_mm)


def _calculate_vertical_cylinder(fill_depth_mm: float, height_mm: float, min_offset_mm: float) -> float:
    """Mopeka linear formula for vertical cylindrical tanks.

    Matches the official Mopeka app's getPercentFromHeight for vertical tanks.
    fill_depth_mm below min_offset_mm is treated as 0% (sensor dead zone).
    """
    if height_mm <= min_offset_mm:
        return 100.0  # degenerate / unconfigured spec
    pct = 100.0 * (fill_depth_mm - min_offset_mm) / (height_mm - min_offset_mm)
    return max(0.0, min(100.0, pct))


def _calculate_horizontal_cylinder(fill_depth_mm: float, diameter_mm: float) -> float:
    """Circular-segment fill percentage for horizontal cylindrical tanks.

    Uses the cubic-polynomial approximation from the official Mopeka app:
        f(t) = -1.16533*t³ + 1.7615*t² + 0.40923*t
    where t = fill_depth / diameter. Accurate to <0.5% vs the exact integral.
    """
    if fill_depth_mm <= 0.0:
        return 0.0
    if fill_depth_mm >= diameter_mm:
        return 100.0
    t = fill_depth_mm / diameter_mm
    pct = 100.0 * (-1.16533 * t * t * t + 1.7615 * t * t + 0.40923 * t)
    return max(0.0, min(100.0, pct))


def _calculate_rectangular(fill_depth_mm: float, height_mm: float) -> float:
    """Linear fill percentage for rectangular tanks (water, liquid)."""
    if height_mm <= 0.0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * fill_depth_mm / height_mm))
